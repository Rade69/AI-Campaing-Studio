"""Unit tests for the S2-G3 HTTP fetcher (redirect + size limits).

Uses a fake ``requests.Session`` so no real socket is opened; the live
adapter/socket-level enforcement is covered by ``test_ssrf_e2e.py``.
"""

from __future__ import annotations

from ai_campaign_studio.infrastructure.web_ingestion.http_fetcher import HttpFetcher
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)


def _policy() -> UrlSafetyPolicy:
    return UrlSafetyPolicy(dns_resolver=lambda host: ("93.184.216.34",))


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        headers: dict[str, str] | None = None,
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self._content = content
        self.iter_content_called = False
        self.closed = False

    def iter_content(self, chunk_size: int):  # noqa: ANN201 - generator
        self.iter_content_called = True
        yield self._content

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = responses
        self.get_calls: list[tuple[str, dict[str, object]]] = []
        self.mounted: list[tuple[str, object]] = []

    def mount(self, prefix: str, adapter: object) -> None:
        self.mounted.append((prefix, adapter))

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.get_calls.append((url, kwargs))
        return self._responses.pop(0)


def test_redirect_to_private_ip_is_blocked() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=302,
                headers={"Location": "http://127.0.0.1/"},
            )
        ]
    )
    fetcher = HttpFetcher(policy=_policy(), session=session)

    result = fetcher.fetch("http://example.com/start")

    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert result.final_url == "http://127.0.0.1/"
    # The redirect target was rejected BEFORE any second connection.
    assert len(session.get_calls) == 1


def test_redirect_to_imds_is_blocked() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=302,
                headers={"Location": "http://169.254.169.254/latest/meta-data/"},
            )
        ]
    )
    fetcher = HttpFetcher(policy=_policy(), session=session)

    result = fetcher.fetch("http://example.com/start")
    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert len(session.get_calls) == 1


def test_redirect_chain_to_public_is_followed() -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=301, headers={"Location": "/final"}),
            FakeResponse(status_code=200, content=b"hello"),
        ]
    )
    fetcher = HttpFetcher(policy=_policy(), session=session)

    result = fetcher.fetch("http://example.com/start")

    assert result.error is None
    assert result.content == b"hello"
    assert result.final_url == "http://example.com/final"
    assert result.status_code == 200
    assert len(session.get_calls) == 2


def test_content_length_over_limit_rejected_before_buffering() -> None:
    response = FakeResponse(
        status_code=200,
        headers={"Content-Length": "9999999"},  # 9 MB > 5 MiB default
        content=b"x" * 100,
    )
    session = FakeSession([response])
    fetcher = HttpFetcher(policy=_policy(), session=session)

    result = fetcher.fetch("http://example.com/")

    assert result.error == "too_large"
    # Body was never read into memory (checked via the header first).
    assert response.iter_content_called is False


def test_streaming_chunk_limit_aborts_when_header_lies() -> None:
    # No Content-Length header → the streaming path must still cap the body.
    response = FakeResponse(status_code=200, content=b"x" * (6 * 1024 * 1024))
    session = FakeSession([response])
    fetcher = HttpFetcher(policy=_policy(), session=session)

    result = fetcher.fetch("http://example.com/")
    assert result.error == "too_large"
    assert response.iter_content_called is True


def test_direct_unsafe_url_is_rejected_without_any_get() -> None:
    session = FakeSession([])
    fetcher = HttpFetcher(policy=_policy(), session=session)

    result = fetcher.fetch("http://127.0.0.1/")
    assert result.error is not None
    assert result.error.startswith("unsafe:")
    assert session.get_calls == []


def test_too_many_redirects_is_rejected() -> None:
    session = FakeSession(
        [
            FakeResponse(status_code=302, headers={"Location": "http://example.com/1"}),
            FakeResponse(status_code=302, headers={"Location": "http://example.com/2"}),
        ]
    )
    fetcher = HttpFetcher(policy=_policy(), session=session, max_redirects=1)

    result = fetcher.fetch("http://example.com/0")
    assert result.error == "too_many_redirects"

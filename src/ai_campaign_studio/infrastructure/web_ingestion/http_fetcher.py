"""HTTP fetcher (S2-G3).

Owns fetching one URL over ``requests`` with SSRF enforcement on every hop:
each URL (initial and every redirect target) is validated by
``UrlSafetyPolicy`` BEFORE any connection is opened; redirects are followed
manually (``allow_redirects=False``) so no hop can be skipped; and the
response body is capped by ``Content-Length`` (checked before buffering) plus
a streaming chunk limit (defense-in-depth if the header lies). Does NOT own
robots/sitemap/crawl-budget policy — those are separate modules that call
this fetcher through ``HttpFetcherPort``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from urllib.parse import urljoin

import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]

from ai_campaign_studio.infrastructure.web_ingestion.errors import (
    FetchError,
    UnsafeUrlError,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)
from ai_campaign_studio.ports.web_ingestion import FetchResult

DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MiB
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_RETRIES = 3
_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_CHUNK_SIZE = 8192


class SafeHttpAdapter(HTTPAdapter):
    """Re-validates every request URL through ``UrlSafetyPolicy`` immediately
    before urllib3 opens a connection. This is defense-in-depth: ``HttpFetcher``
    already validates each hop, but this guard covers ANY caller of the mounted
    session and runs right at the connection boundary (canonical plan §6.1)."""

    def __init__(
        self, policy: UrlSafetyPolicy, *args: object, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)
        self._policy = policy

    def send(
        self, request: requests.PreparedRequest, **kwargs: object
    ) -> requests.Response:
        decision = self._policy.validate_url(request.url or "")
        if not decision.allowed:
            raise UnsafeUrlError(decision.reason)
        return super().send(request, **kwargs)


class HttpFetcher:
    """``HttpFetcherPort`` implementation with per-hop SSRF validation."""

    def __init__(
        self,
        *,
        policy: UrlSafetyPolicy | None = None,
        timeout: tuple[float, float] = (5.0, 10.0),
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = 0.5,
        sleeper: Callable[[float], None] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._policy = policy or UrlSafetyPolicy()
        self._timeout = timeout
        self._max_response_bytes = max_response_bytes
        self._max_redirects = max_redirects
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._sleeper = sleeper if sleeper is not None else time.sleep

        self._session = session if session is not None else requests.Session()
        adapter = SafeHttpAdapter(self._policy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def fetch(self, url: str) -> FetchResult:
        return self._fetch_hop(url, url, 0)

    def _fetch_hop(self, original_url: str, current: str, hops: int) -> FetchResult:
        decision = self._policy.validate_url(current)
        if not decision.allowed:
            return FetchResult(
                url=original_url,
                final_url=current,
                status_code=0,
                error=f"unsafe:{decision.reason}",
            )

        try:
            response = self._get_with_retry(current)
        except UnsafeUrlError as exc:
            return FetchResult(
                url=original_url,
                final_url=current,
                status_code=0,
                error=f"unsafe:{exc}",
            )
        except FetchError as exc:
            return FetchResult(
                url=original_url,
                final_url=current,
                status_code=0,
                error=str(exc),
            )

        with response:
            if response.status_code in _REDIRECT_STATUS_CODES:
                location = response.headers.get("Location")
                if location:
                    next_url = urljoin(current, location)
                    if hops >= self._max_redirects:
                        return FetchResult(
                            url=original_url,
                            final_url=next_url,
                            status_code=response.status_code,
                            error="too_many_redirects",
                        )
                    return self._fetch_hop(original_url, next_url, hops + 1)
                # Redirect status without a Location — treat as a final
                # (empty) result; there is no body to stream.
                return FetchResult(
                    url=original_url,
                    final_url=current,
                    status_code=response.status_code,
                    content=b"",
                    content_type=response.headers.get("Content-Type"),
                )

            # Content-Length must be checked BEFORE buffering the body.
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    if int(content_length.strip()) > self._max_response_bytes:
                        return FetchResult(
                            url=original_url,
                            final_url=current,
                            status_code=response.status_code,
                            error="too_large",
                        )
                except ValueError:
                    pass

            body = bytearray()
            too_large = False
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                if chunk:
                    body.extend(chunk)
                    if len(body) > self._max_response_bytes:
                        too_large = True
                        break

            if too_large:
                return FetchResult(
                    url=original_url,
                    final_url=current,
                    status_code=response.status_code,
                    error="too_large",
                )

            return FetchResult(
                url=original_url,
                final_url=current,
                status_code=response.status_code,
                content=bytes(body),
                content_type=response.headers.get("Content-Type"),
            )

    def _get_with_retry(self, url: str) -> requests.Response:
        """Transport-level retry with exponential backoff (max 3 attempts).

        Only connection/timeout errors are retried — HTTP status codes are
        returned to the caller as responses, and SSRF rejections never reach
        the socket (the policy rejects them first).
        """
        last_exc: requests.RequestException | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return self._session.get(
                    url,
                    allow_redirects=False,
                    stream=True,
                    timeout=self._timeout,
                )
            except UnsafeUrlError:
                raise
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    self._sleeper(self._retry_backoff * (2 ** attempt))
        raise FetchError(f"fetch_error:{type(last_exc).__name__}") from last_exc


__all__ = [
    "DEFAULT_MAX_REDIRECTS",
    "DEFAULT_MAX_RESPONSE_BYTES",
    "HttpFetcher",
    "SafeHttpAdapter",
]

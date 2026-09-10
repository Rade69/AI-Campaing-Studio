"""Shared fixtures for S2-G3 web-ingestion unit tests.

The ``fake_fetcher`` fixture is a ``HttpFetcherPort`` stub that returns
pre-mapped ``FetchResult``s (an unmapped URL returns a network-error result so
tests fail loudly instead of silently succeeding). Kept as a fixture (not a
shared importable module) because this repo's test packages are imported with
``--import-mode=importlib`` and tests import only from ``ai_campaign_studio.*``.
"""

from __future__ import annotations

import pytest

from ai_campaign_studio.ports.web_ingestion import FetchResult


class FakeFetcher:
    """``HttpFetcherPort`` stub."""

    def __init__(self, responses: dict[str, FetchResult] | None = None) -> None:
        self._responses: dict[str, FetchResult] = dict(responses or {})
        self.calls: list[str] = []

    def set(self, url: str, result: FetchResult) -> None:
        self._responses[url] = result

    def set_ok(
        self,
        url: str,
        content: bytes,
        *,
        status_code: int = 200,
        content_type: str = "text/plain",
    ) -> None:
        self._responses[url] = FetchResult(
            url=url,
            final_url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
        )

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        if url in self._responses:
            return self._responses[url]
        return FetchResult(
            url=url,
            final_url=url,
            status_code=0,
            error="unmapped_fetch",
        )


@pytest.fixture()
def fake_fetcher() -> FakeFetcher:
    return FakeFetcher()

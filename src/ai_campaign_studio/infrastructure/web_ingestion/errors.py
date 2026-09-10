"""Web ingestion errors (S2-G3).

Owns the specific exception types raised by the web-ingestion modules. A
specific type per failure class (never a bare ``Exception``) is what lets the
S2-G6 orchestration record ``CrawlTarget.last_error`` and decide retry/skip
without swallowing unrelated bugs.
"""

from __future__ import annotations


class UnsafeUrlError(ValueError):
    """A URL (or a redirect target) failed SSRF/URL-safety validation."""


class FetchError(ValueError):
    """A fetch could not complete (network, size, redirect budget)."""


class RobotsUnreachableError(FetchError):
    """robots.txt could not be fetched (network or 5xx) — treat as disallow."""


class SitemapParseError(ValueError):
    """A sitemap.xml could not be fetched or parsed as XML."""


__all__ = [
    "FetchError",
    "RobotsUnreachableError",
    "SitemapParseError",
    "UnsafeUrlError",
]

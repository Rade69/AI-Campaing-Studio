"""robots.txt reader (S2-G3) — RFC 9309.

Owns fetching and caching a host's ``/robots.txt`` (cache TTL ≤ 24h) and
answering ``can_fetch``/``sitemaps`` via Protego. RFC 9309 fallbacks: a
network-error/5xx robots.txt is UNREACHABLE → treat as disallow; a 4xx
robots.txt is UNAVAILABLE → treat as allow (no rules); a malformed body is
parsed tolerantly by Protego (invalid lines ignored, not fatal). Does not
crawl — it only reads rules for ``http_fetcher``/``domain_discovery``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit

from protego import Protego

from ai_campaign_studio.ports.web_ingestion import HttpFetcherPort

_DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h (RFC 9309 cache ceiling)


def robots_url_for(url: str) -> str:
    """Return the ``<scheme>://<host>[:port]/robots.txt`` URL for ``url``."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parts.port is not None:
        netloc = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme.lower(), netloc, "/robots.txt", "", ""))


class RobotsReader:
    """Cached RFC 9309 robots.txt policy reader."""

    def __init__(
        self,
        fetcher: HttpFetcherPort,
        *,
        user_agent: str = "AI-Campaign-Studio",
        cache_ttl_seconds: float = _DEFAULT_CACHE_TTL_SECONDS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._user_agent = user_agent
        self._cache_ttl = cache_ttl_seconds
        self._clock = clock if clock is not None else time.monotonic
        # origin -> (fetched_at, parser-or-None). None parser = unreachable.
        self._cache: dict[str, tuple[float, Protego | None]] = {}

    def can_fetch(self, url: str) -> bool:
        """True if crawling ``url`` is allowed (unreachable robots → False)."""
        parser = self._parser_for(url)
        if parser is None:
            return False
        return bool(parser.can_fetch(url, self._user_agent))

    def sitemaps(self, url: str) -> tuple[str, ...]:
        """Sitemap URLs declared by the host's robots.txt (empty if unknown)."""
        parser = self._parser_for(url)
        if parser is None:
            return ()
        return tuple(parser.sitemaps)

    def _parser_for(self, url: str) -> Protego | None:
        origin = robots_url_for(url)
        now = self._clock()
        cached = self._cache.get(origin)
        if cached is not None and now - cached[0] < self._cache_ttl:
            return cached[1]
        parser = self._fetch_and_parse(origin)
        self._cache[origin] = (now, parser)
        return parser

    def _fetch_and_parse(self, robots_url: str) -> Protego | None:
        result = self._fetcher.fetch(robots_url)
        # Network error / fetch failure → unreachable → disallow (None marker).
        if result.error or result.status_code == 0:
            return None
        if 400 <= result.status_code < 500:
            # RFC 9309: 4xx means "no robots.txt" (unavailable) → allow all,
            # EXCEPT 429 (rate limited) which is treated as unreachable.
            if result.status_code == 429:
                return None
            return Protego.parse("")
        if result.status_code >= 500:
            # RFC 9309: 5xx → unreachable → assume complete disallow.
            return None
        content = result.content or b""
        try:
            text = content.decode("utf-8", errors="replace")
            return Protego.parse(text)
        except Exception:
            # Malformed beyond Protego's tolerance → treat as no rules.
            return Protego.parse("")


__all__ = ["RobotsReader", "robots_url_for"]

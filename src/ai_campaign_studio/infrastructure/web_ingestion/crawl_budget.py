"""Crawl budget (S2-G3).

Owns the per-domain crawl caps: a hard URL-count ceiling (default 1000 per
domain) and a politeness delay (default ≥1s between requests to the same
host). ``sleeper``/``clock`` are injectable so politeness timing is testable
without real sleeps. Does not fetch or decide WHAT to crawl — it only gates
count/delay for ``domain_discovery``/the S2-G6 pipeline.
"""

from __future__ import annotations

import time
from collections.abc import Callable

DEFAULT_MAX_URLS_PER_DOMAIN = 1000
DEFAULT_POLITENESS_SECONDS = 1.0


class CrawlBudget:
    """Per-domain URL count + politeness throttle."""

    def __init__(
        self,
        *,
        max_urls_per_domain: int = DEFAULT_MAX_URLS_PER_DOMAIN,
        politeness_seconds: float = DEFAULT_POLITENESS_SECONDS,
        sleeper: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if max_urls_per_domain < 0:
            raise ValueError("max_urls_per_domain must be >= 0")
        if politeness_seconds < 0:
            raise ValueError("politeness_seconds must be >= 0")
        self._max_urls_per_domain = max_urls_per_domain
        self._politeness_seconds = politeness_seconds
        self._sleeper = sleeper if sleeper is not None else time.sleep
        self._clock = clock if clock is not None else time.monotonic
        self._counts: dict[str, int] = {}
        self._last_request: dict[str, float] = {}

    def can_crawl(self, domain: str) -> bool:
        """True while the per-domain URL ceiling has not been reached."""
        return self._counts.get(domain, 0) < self._max_urls_per_domain

    def wait_politeness(self, domain: str) -> float:
        """Sleep until ``politeness_seconds`` elapsed since the previous request
        to ``domain``; return the number of seconds actually slept."""
        now = self._clock()
        last = self._last_request.get(domain)
        slept = 0.0
        if last is not None:
            remaining = self._politeness_seconds - (now - last)
            if remaining > 0:
                self._sleeper(remaining)
                slept = remaining
                now = self._clock()
        self._last_request[domain] = now
        return slept

    def record_fetch(self, domain: str) -> None:
        """Record one completed fetch for ``domain`` (count + last-request)."""
        self._counts[domain] = self._counts.get(domain, 0) + 1
        self._last_request[domain] = self._clock()

    def count(self, domain: str) -> int:
        """Fetches recorded so far for ``domain``."""
        return self._counts.get(domain, 0)

    def reset(self, domain: str | None = None) -> None:
        """Reset counters (one domain, or everything when ``domain`` is None)."""
        if domain is None:
            self._counts.clear()
            self._last_request.clear()
        else:
            self._counts.pop(domain, None)
            self._last_request.pop(domain, None)


__all__ = ["CrawlBudget", "DEFAULT_MAX_URLS_PER_DOMAIN", "DEFAULT_POLITENESS_SECONDS"]

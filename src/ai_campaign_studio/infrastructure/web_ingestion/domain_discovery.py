"""Domain discovery (S2-G3).

Owns turning one start URL into a crawl-queue candidate list:
normalize → robots.txt (sitemap declarations + rules) → sitemap.xml →
(optionally) ``<a href>`` links on the start page, capped by the crawl budget
and a hard ``max_urls`` ceiling. EVERY candidate is re-normalized and passed
through ``url_safety_policy`` and ``robots_reader`` BEFORE it is added — an
unsafe URL never reaches the queue. Does not persist the queue (the S2-G6
pipeline registers candidates through ``IngestionRepositoryPort``).
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from ai_campaign_studio.infrastructure.web_ingestion.crawl_budget import CrawlBudget
from ai_campaign_studio.infrastructure.web_ingestion.errors import SitemapParseError
from ai_campaign_studio.infrastructure.web_ingestion.robots_reader import RobotsReader
from ai_campaign_studio.infrastructure.web_ingestion.sitemap_reader import (
    SitemapEntry,
    SitemapReader,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_normalizer import normalize_url
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)
from ai_campaign_studio.ports.web_ingestion import HttpFetcherPort

_LOGGER = logging.getLogger(__name__)

_DEFAULT_MAX_URLS = 5000  # hard security ceiling, canonical plan §6.4


def _host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


class _LinkExtractor(HTMLParser):
    """Collect ``<a href>`` targets from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for key, value in attrs:
                if key.lower() == "href" and value:
                    self.links.append(value)


class DomainDiscovery:
    """robots.txt + sitemap.xml + start-page links → crawl candidate tuple."""

    def __init__(
        self,
        *,
        fetcher: HttpFetcherPort,
        robots: RobotsReader,
        sitemaps: SitemapReader,
        policy: UrlSafetyPolicy,
        budget: CrawlBudget | None = None,
        max_urls: int = _DEFAULT_MAX_URLS,
    ) -> None:
        self._fetcher = fetcher
        self._robots = robots
        self._sitemaps = sitemaps
        self._policy = policy
        self._budget = budget
        self._max_urls = max_urls

    def discover(self, start_url: str) -> tuple[str, ...]:
        candidates: list[str] = []
        seen: set[str] = set()

        start = self._normalize(start_url)
        if start is not None and self._policy_allows(start):
            candidates.append(start)
            seen.add(start)
        if start is None:
            return ()

        # 1. sitemap URLs declared by robots.txt.
        for sitemap_url in self._robots.sitemaps(start):
            for entry in self._safe_sitemap_entries(sitemap_url):
                self._add_candidate(entry.loc, candidates, seen)

        # 2. conventional /sitemap.xml on the same origin.
        origin = _origin_of(start)
        for entry in self._safe_sitemap_entries(origin + "/sitemap.xml"):
            self._add_candidate(entry.loc, candidates, seen)

        # 3. (optional) <a> links on the start page.
        result = self._fetcher.fetch(start)
        if result.content:
            for link in self._extract_links(result.content, start):
                self._add_candidate(link, candidates, seen)

        return tuple(candidates)

    def _safe_sitemap_entries(
        self, sitemap_url: str
    ) -> tuple[SitemapEntry, ...]:
        """``SitemapReader.list_entries`` with malformed content downgraded.

        Some sites answer a missing ``/sitemap.xml`` with a 200 HTML page
        (their normal catch-all/SPA route) instead of a 404 — ``SitemapReader``
        correctly raises ``SitemapParseError`` for that per its documented
        contract (a genuinely malformed sitemap is not the same as an absent
        one). Before this fix that exception propagated all the way out of
        ``discover()`` unhandled, which meant a single bad ``/sitemap.xml``
        killed discovery of the WHOLE domain — even the seed URL itself was
        lost, though it had already been queued a few lines above. Reproduced
        live against a real site (kingdomdoo.com/en/) whose ``/sitemap.xml``
        returns its homepage HTML with status 200. Treated the same as an
        absent sitemap: log and continue with whatever other signals exist
        (robots-declared sitemaps, on-page links, the seed URL itself).
        """
        try:
            return self._sitemaps.list_entries(sitemap_url)
        except SitemapParseError as exc:
            _LOGGER.warning("sitemap_parse_failed url=%s error=%s", sitemap_url, exc)
            return ()

    def _add_candidate(
        self, url: str, candidates: list[str], seen: set[str]
    ) -> None:
        if len(candidates) >= self._max_urls:
            return
        normalized = self._normalize(url)
        if normalized is None or normalized in seen:
            return
        if not self._policy_allows(normalized):
            return
        if not self._robots.can_fetch(normalized):
            return
        domain = _host_of(normalized)
        if self._budget is not None and not self._budget.can_crawl(domain):
            return
        seen.add(normalized)
        candidates.append(normalized)

    def _policy_allows(self, url: str) -> bool:
        return self._policy.validate_url(url).allowed

    @staticmethod
    def _normalize(url: str) -> str | None:
        try:
            return normalize_url(url)
        except ValueError:
            return None

    @staticmethod
    def _extract_links(html: bytes, base_url: str) -> list[str]:
        parser = _LinkExtractor()
        parser.feed(html.decode("utf-8", errors="replace"))
        parser.close()
        return [urljoin(base_url, link) for link in parser.links]


def _origin_of(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parts.port is not None:
        netloc = f"{host}:{parts.port}"
    return f"{parts.scheme.lower()}://{netloc}"


__all__ = ["DomainDiscovery"]

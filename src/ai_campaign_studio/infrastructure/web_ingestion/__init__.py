"""Web ingestion infrastructure (S2-G3).

Owns the HTTP fetch + discovery layer of Website/Brand ingestion:
``url_safety_policy`` (SSRF guard, canonical plan §6), ``http_fetcher``
(requests + per-hop SSRF validation), ``robots_reader`` (RFC 9309),
``sitemap_reader``, ``url_normalizer``, ``crawl_budget`` and
``domain_discovery``. No port is added here — the adapters implement the
existing S2-G1 ports in ``ports/web_ingestion.py`` (``HttpFetcherPort``,
``SitemapReaderPort``). Does not persist anything: the S2-G6 pipeline is the
only caller that feeds the returned candidates into
``IngestionRepositoryPort``.
"""

from ai_campaign_studio.infrastructure.web_ingestion.crawl_budget import CrawlBudget
from ai_campaign_studio.infrastructure.web_ingestion.domain_discovery import (
    DomainDiscovery,
)
from ai_campaign_studio.infrastructure.web_ingestion.errors import (
    FetchError,
    RobotsUnreachableError,
    SitemapParseError,
    UnsafeUrlError,
)
from ai_campaign_studio.infrastructure.web_ingestion.http_fetcher import HttpFetcher
from ai_campaign_studio.infrastructure.web_ingestion.robots_reader import RobotsReader
from ai_campaign_studio.infrastructure.web_ingestion.sitemap_reader import (
    SitemapEntry,
    SitemapReader,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_classifier import (
    UrlClassifier,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_normalizer import (
    normalize_url,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    SafetyDecision,
    UrlSafetyPolicy,
)

__all__ = [
    "CrawlBudget",
    "DomainDiscovery",
    "FetchError",
    "HttpFetcher",
    "RobotsReader",
    "RobotsUnreachableError",
    "SafetyDecision",
    "SitemapEntry",
    "SitemapParseError",
    "SitemapReader",
    "UnsafeUrlError",
    "UrlClassifier",
    "UrlSafetyPolicy",
    "normalize_url",
]

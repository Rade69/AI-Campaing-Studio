"""Unit tests for the S2-G3 domain discovery (safety filtering of candidates)."""

from __future__ import annotations

from ai_campaign_studio.infrastructure.web_ingestion.crawl_budget import CrawlBudget
from ai_campaign_studio.infrastructure.web_ingestion.domain_discovery import (
    DomainDiscovery,
)
from ai_campaign_studio.infrastructure.web_ingestion.robots_reader import RobotsReader
from ai_campaign_studio.infrastructure.web_ingestion.sitemap_reader import (
    SitemapReader,
)
from ai_campaign_studio.infrastructure.web_ingestion.url_safety_policy import (
    UrlSafetyPolicy,
)
from ai_campaign_studio.ports.web_ingestion import FetchResult

_PUBLIC_IP = ("93.184.216.34",)


def _policy() -> UrlSafetyPolicy:
    return UrlSafetyPolicy(dns_resolver=lambda host: _PUBLIC_IP)


def _build_discovery(fetcher, *, budget: CrawlBudget | None = None) -> DomainDiscovery:
    return DomainDiscovery(
        fetcher=fetcher,
        robots=RobotsReader(fetcher, user_agent="test-bot"),
        sitemaps=SitemapReader(fetcher),
        policy=_policy(),
        budget=budget,
    )


def _set(
    fake_fetcher, url: str, content: bytes, *, content_type: str | None = None
) -> None:
    fake_fetcher.set(
        url,
        FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content=content,
            content_type=content_type,
        ),
    )


def test_discover_filters_unsafe_candidates_before_adding(fake_fetcher) -> None:
    start_html = (
        b'<html><body><a href="/contact">Contact</a>'
        b'<a href="http://10.0.0.1/x">bad</a></body></html>'
    )
    sitemap_xml = (
        b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>http://example.com/about</loc></url>"
        b"<url><loc>http://127.0.0.1/</loc></url>"
        b"</urlset>"
    )
    _set(fake_fetcher, "http://example.com/", start_html, content_type="text/html")
    _set(
        fake_fetcher,
        "http://example.com/robots.txt",
        b"User-agent: *\nDisallow:\n",
        content_type="text/plain",
    )
    _set(
        fake_fetcher,
        "http://example.com/sitemap.xml",
        sitemap_xml,
        content_type="application/xml",
    )

    discovery = _build_discovery(fake_fetcher)
    result = discovery.discover("http://example.com/")

    assert result == (
        "http://example.com/",
        "http://example.com/about",
        "http://example.com/contact",
    )
    # Neither the private sitemap URL nor the private <a> link leaked through.
    assert all("127.0.0.1" not in u and "10.0.0.1" not in u for u in result)


def test_discover_deduplicates_and_respects_budget(fake_fetcher) -> None:
    sitemap_xml = (
        b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>http://example.com/about</loc></url>"
        b"</urlset>"
    )
    start_html = b'<html><body><a href="/about">About again</a></body></html>'
    _set(fake_fetcher, "http://example.com/", start_html)
    _set(fake_fetcher, "http://example.com/robots.txt", b"User-agent: *\nDisallow:\n")
    _set(fake_fetcher, "http://example.com/sitemap.xml", sitemap_xml)

    # Budget allows only 2 URLs per domain → start + about (about deduped).
    discovery = _build_discovery(
        fake_fetcher, budget=CrawlBudget(max_urls_per_domain=2)
    )
    result = discovery.discover("http://example.com/")

    assert result == ("http://example.com/", "http://example.com/about")

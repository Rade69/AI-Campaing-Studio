"""Unit tests for the S2-G3 sitemap.xml reader."""

from __future__ import annotations

import pytest

from ai_campaign_studio.infrastructure.web_ingestion.errors import SitemapParseError
from ai_campaign_studio.infrastructure.web_ingestion.sitemap_reader import SitemapReader
from ai_campaign_studio.ports.web_ingestion import FetchResult

SITEMAP_URL = "https://example.com/sitemap.xml"

_VALID = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc><lastmod>2026-01-01</lastmod></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/pricing</loc><lastmod>2026-02-02</lastmod></url>
</urlset>
"""

_EMPTY = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>
"""

_MALFORMED = b"<urlset><url><loc>https://example.com/</url>"


def _set_sitemap(fake_fetcher, content: bytes, *, status_code: int = 200) -> None:
    fake_fetcher.set(
        SITEMAP_URL,
        FetchResult(
            url=SITEMAP_URL,
            final_url=SITEMAP_URL,
            status_code=status_code,
            content=content,
            content_type="application/xml",
        ),
    )


def test_valid_sitemap_extracts_loc_and_lastmod(fake_fetcher) -> None:
    _set_sitemap(fake_fetcher, _VALID)
    reader = SitemapReader(fake_fetcher)
    assert reader.list_urls(SITEMAP_URL) == (
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/pricing",
    )
    entries = reader.list_entries(SITEMAP_URL)
    assert entries[0].lastmod == "2026-01-01"
    assert entries[1].lastmod is None
    assert entries[2].lastmod == "2026-02-02"


def test_empty_sitemap_returns_empty_tuple(fake_fetcher) -> None:
    _set_sitemap(fake_fetcher, _EMPTY)
    reader = SitemapReader(fake_fetcher)
    assert reader.list_urls(SITEMAP_URL) == ()


def test_malformed_xml_raises_sitemap_parse_error(fake_fetcher) -> None:
    _set_sitemap(fake_fetcher, _MALFORMED)
    reader = SitemapReader(fake_fetcher)
    with pytest.raises(SitemapParseError):
        reader.list_urls(SITEMAP_URL)


def test_absent_sitemap_returns_empty_tuple(fake_fetcher) -> None:
    fake_fetcher.set(
        SITEMAP_URL,
        FetchResult(
            url=SITEMAP_URL,
            final_url=SITEMAP_URL,
            status_code=404,
            content=b"",
        ),
    )
    reader = SitemapReader(fake_fetcher)
    assert reader.list_urls(SITEMAP_URL) == ()


def test_max_urls_caps_output(fake_fetcher) -> None:
    body = (
        b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + b"".join(
            f"<url><loc>https://example.com/p{i}</loc></url>".encode()
            for i in range(10)
        )
        + b"</urlset>"
    )
    _set_sitemap(fake_fetcher, body)
    reader = SitemapReader(fake_fetcher, max_urls=3)
    assert reader.list_urls(SITEMAP_URL) == (
        "https://example.com/p0",
        "https://example.com/p1",
        "https://example.com/p2",
    )

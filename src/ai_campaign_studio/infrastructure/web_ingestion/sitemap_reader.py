"""Sitemap reader (S2-G3).

Owns fetching a ``sitemap.xml`` and extracting ``<url><loc>`` entries (with
``<lastmod>`` when present), namespace-tolerantly. Validates XML structure: a
malformed body raises ``SitemapParseError``; an empty/absent sitemap yields an
empty tuple (a missing sitemap is not fatal to discovery). Does not recurse
into sitemap index files and does not follow the listed URLs — it only lists
them for ``domain_discovery`` (which re-validates each candidate).
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

from ai_campaign_studio.infrastructure.web_ingestion.errors import SitemapParseError
from ai_campaign_studio.ports.web_ingestion import HttpFetcherPort

_DEFAULT_MAX_URLS = 5000  # hard security ceiling, canonical plan §6.4


@dataclass(frozen=True)
class SitemapEntry:
    """One ``<url>`` entry from a sitemap."""

    loc: str
    lastmod: str | None = None


class SitemapReader:
    """XML sitemap parser over ``HttpFetcherPort``."""

    def __init__(
        self,
        fetcher: HttpFetcherPort,
        *,
        max_urls: int = _DEFAULT_MAX_URLS,
    ) -> None:
        self._fetcher = fetcher
        self._max_urls = max_urls

    def list_urls(self, sitemap_url: str) -> tuple[str, ...]:
        """``SitemapReaderPort.list_urls`` — the extracted ``<loc>`` URLs."""
        return tuple(entry.loc for entry in self.list_entries(sitemap_url))

    def list_entries(self, sitemap_url: str) -> tuple[SitemapEntry, ...]:
        result = self._fetcher.fetch(sitemap_url)
        # Absent/unfetchable sitemap → empty, not fatal.
        if result.error or result.status_code != 200:
            return ()
        content = result.content or b""
        if content.strip() == b"":
            return ()
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise SitemapParseError(
                f"malformed sitemap XML at {sitemap_url!r}: {exc}"
            ) from exc

        entries: list[SitemapEntry] = []
        for element in root.iter():
            if not element.tag.rsplit("}", 1)[-1] == "url":
                continue
            loc: str | None = None
            lastmod: str | None = None
            for child in element:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag == "loc":
                    loc = (child.text or "").strip()
                elif tag == "lastmod":
                    lastmod = (child.text or "").strip()
            if loc:
                entries.append(SitemapEntry(loc=loc, lastmod=lastmod or None))
                if len(entries) >= self._max_urls:
                    break
        return tuple(entries)


__all__ = ["SitemapEntry", "SitemapReader"]

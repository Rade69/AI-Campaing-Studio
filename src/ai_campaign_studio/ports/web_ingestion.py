"""Web ingestion ports (S2-G1).

Owns the framework-neutral ``Protocol`` contracts for Website/Brand
ingestion, plus the small transport data shapes they exchange. ALL signatures
are SYNCHRONOUS (``def``, never ``async def``) — canonical plan §5 decision,
fixed in ACS-S2-001: the whole application is thread-pool synchronous
(``JobManager``/``ThreadPoolExecutor``/SQLite), and the SSRF guard is
implemented on the synchronous ``requests`` + custom ``HTTPAdapter`` layer
(S2-G3), not aiohttp.

``SourceChunk`` is the DOMAIN entity (with ``id`` + ``snapshot_id``); the
extractor ports below return the lightweight ``ExtractedChunk`` shape
(locator + text only) because id/snapshot assignment happens later in the
S2-G6 pipeline once the ``SourceSnapshot`` is persisted. No implementation
lives here — adapters land in S2-G3/G4/G5/G9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai_campaign_studio.domain.brand.value_objects import VisualIdentity
from ai_campaign_studio.domain.ingestion.enums import PageType


@dataclass(frozen=True)
class FetchResult:
    """Transport result of one HTTP fetch (NOT persistence).

    ``content`` is the raw body bytes (``None`` when the fetch failed);
    ``final_url`` is the URL after any redirects (S2-G3 SSRF validation must
    inspect every hop, so the final URL is part of the contract).
    """

    url: str
    final_url: str
    status_code: int
    content: bytes | None = None
    content_type: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ExtractedChunk:
    """A locator-precise fragment returned by an extractor.

    ``id``/``snapshot_id`` are deliberately NOT here — the S2-G6 pipeline
    assigns them when it materialises the domain ``SourceChunk`` entity from
    this fragment.
    """

    locator_type: str
    locator: str
    text: str


@dataclass(frozen=True)
class ContentExtractionResult:
    """Boilerplate-stripped main content plus its locator-precise chunks."""

    text: str
    chunks: tuple[ExtractedChunk, ...] = ()


@runtime_checkable
class HttpFetcherPort(Protocol):
    """Fetch one URL and return the raw transport result."""

    def fetch(self, url: str) -> FetchResult: ...


@runtime_checkable
class SitemapReaderPort(Protocol):
    """Read/parse a sitemap.xml and return the discovered URL list."""

    def list_urls(self, sitemap_url: str) -> tuple[str, ...]: ...


@runtime_checkable
class UrlClassifierPort(Protocol):
    """Deterministic page classification (canonical plan §8).

    URL-signal-based classification (path, extension, host) — never an LLM
    call. Content-signal refinement (title/H1/breadcrumb/schema.org) belongs
    to the S2-G4 extractors, not this port.
    """

    def classify(self, url: str) -> PageType: ...


@runtime_checkable
class MainContentExtractorPort(Protocol):
    """Extract boilerplate-stripped main content + chunks from one HTML doc."""

    def extract(self, html: str, base_url: str) -> ContentExtractionResult: ...


@runtime_checkable
class VisualIdentityExtractorPort(Protocol):
    """Extract visual-identity signals into the existing ``VisualIdentity`` VO."""

    def extract(self, html: str, base_url: str) -> VisualIdentity: ...


@runtime_checkable
class DocumentExtractorPort(Protocol):
    """Extract PDF/DOCX/XLSX into the SAME chunk model as web content
    (one provenance chain, canonical plan §10 S2-G9)."""

    def extract(self, file_path: str) -> ContentExtractionResult: ...


__all__ = [
    "ContentExtractionResult",
    "DocumentExtractorPort",
    "ExtractedChunk",
    "FetchResult",
    "HttpFetcherPort",
    "MainContentExtractorPort",
    "SitemapReaderPort",
    "UrlClassifierPort",
    "VisualIdentityExtractorPort",
]

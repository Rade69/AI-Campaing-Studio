"""Ingestion-pipeline dependency contracts (S2-G6).

Owns the small structural interfaces the S2-G6 orchestration needs but that do
NOT exist as ports in ``ports/`` (S2-G1 only defined ``HttpFetcherPort``,
``SitemapReaderPort``, ``UrlClassifierPort``, ``MainContentExtractorPort``,
``VisualIdentityExtractorPort``, ``DocumentExtractorPort`` — the latter two
shapes do not match the actual G4/G9 implementations). Declaring them here
keeps the use-case free of any ``infrastructure`` import (application layer
boundary, ``tests/architecture/test_import_boundaries.py``); the concrete G3/
G4/G9 objects are injected by the caller.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from ai_campaign_studio.domain.common.ids import IngestionRunId, SourceSnapshotId
from ai_campaign_studio.domain.ingestion.entities import SourceChunk


@runtime_checkable
class DiscoveryDependency(Protocol):
    """The one method G6 uses from G3 ``DomainDiscovery``."""

    def discover(self, start_url: str) -> tuple[str, ...]: ...


@runtime_checkable
class CrawlBudgetDependency(Protocol):
    """The three methods G6 uses from G3 ``CrawlBudget``."""

    def can_crawl(self, domain: str) -> bool: ...

    def wait_politeness(self, domain: str) -> float: ...

    def record_fetch(self, domain: str) -> None: ...


# G4 ``MainContentExtractor.extract(html, base_url) -> str``.
ContentExtractCallable = Callable[[str, str], str]
# G4 ``BoilerplateFilter.filter(text) -> str``.
BoilerplateFilterCallable = Callable[[str], str]
# G4 ``Deduplicator.deduplicate(chunks) -> chunks``.
DeduplicatorCallable = Callable[[tuple[SourceChunk, ...]], tuple[SourceChunk, ...]]
# G9 ``PdfSource/DocxSource/XlsxSource.extract(path, run_id, snapshot_id)``.
DocumentExtractCallable = Callable[
    [str, IngestionRunId, SourceSnapshotId], tuple[SourceChunk, ...]
]


__all__ = [
    "BoilerplateFilterCallable",
    "ContentExtractCallable",
    "CrawlBudgetDependency",
    "DeduplicatorCallable",
    "DiscoveryDependency",
    "DocumentExtractCallable",
]

"""Ingestion domain entities (S2-G1).

Owns the immutable provenance/run value objects for Website/Brand ingestion:
``SourceSnapshot`` (immutable snapshot of one fetched page/document),
``SourceChunk`` (locator-precise fragment inside a snapshot), ``IngestionRun``
(one ingestion attempt for one brand) and ``IngestionCheckpoint`` (last
completed phase of a run). Plain frozen dataclasses, same style as
``domain/performance/entities.py``. No persistence, no orchestration — S2-G2
gives these their first SQLite table, S2-G6 the pipeline.

Provenance chain (G-WI-EVIDENCE, canonical plan §11): every ``FactCandidate``
must be traceable back to an immutable ``SourceSnapshot`` via
``SourceReference.snapshot_id`` (and, when locator-precise,
``chunk_id`` → ``SourceChunk``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    BrandId,
    CrawlTargetId,
    IngestionCheckpointId,
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionPhase,
    IngestionRunStatus,
    PageType,
)


@dataclass(frozen=True)
class SourceSnapshot:
    """Immutable snapshot of ONE fetched page/document at one point in time.

    ``content_hash`` is the only in-memory evidence of the raw content (a
    stable digest); the RAW bytes are deliberately NOT inlined here — they are
    referenced via ``raw_content_ref`` so a large HTML/PDF body stays out of
    the value object. S2-G2 decides the concrete storage/ref scheme.
    """

    id: SourceSnapshotId
    url: str
    fetched_at: datetime
    content_hash: str
    raw_content_ref: str | None = None
    content_type: str | None = None
    status_code: int | None = None


@dataclass(frozen=True)
class SourceChunk:
    """A locator-precise fragment within one ``SourceSnapshot``.

    ``locator_type`` names the reference kind (e.g. ``css_selector``,
    ``heading``, ``paragraph_index``, ``pdf_page``); ``locator`` is the
    machine-precise value inside the snapshot; ``text`` is the small
    extracted fragment (kept inline — chunks are small, and this is what a
    ``FactCandidate``'s evidence points at).
    """

    id: SourceChunkId
    snapshot_id: SourceSnapshotId
    locator_type: str
    locator: str
    text: str


@dataclass(frozen=True)
class IngestionRunStats:
    """Run-level counters. Zero-initialised; S2-G6 decides final semantics."""

    discovered_urls: int = 0
    fetched_pages: int = 0
    extracted_chunks: int = 0
    built_candidates: int = 0
    failed_pages: int = 0


@dataclass(frozen=True)
class IngestionRun:
    """One ingestion attempt for ONE brand."""

    id: IngestionRunId
    brand_id: BrandId
    status: IngestionRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    source_scope: tuple[str, ...] = ()
    stats: IngestionRunStats = IngestionRunStats()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_scope", tuple(self.source_scope))


@dataclass(frozen=True)
class IngestionCheckpoint:
    """The LAST COMPLETED phase of an ``IngestionRun`` (cooperative progress).

    Checkpoints are append-only records; the "current phase" of a run is the
    newest checkpoint. Phase ordering lives in ``IngestionPhase`` — this value
    object does not enforce/advance it (S2-G6 orchestrates that).
    """

    id: IngestionCheckpointId
    run_id: IngestionRunId
    phase: IngestionPhase
    finished_at: datetime


@dataclass(frozen=True)
class CrawlTarget:
    """One lease-queue row for a URL to crawl (canonical plan §7, S2-G2).

    Type-level state machine: ``CrawlTargetState`` holds the queue lifecycle
    (``PENDING → LEASED → FETCHED → EXTRACTED → DONE``, plus retryable and
    terminal states) so S2-G6 orchestrates over typed values, not raw SQL
    rows. ``UNIQUE(run_id, normalized_url)`` idempotency is a persistence
    concern (the adapter's ``register_crawl_targets``), not enforced here.
    """

    id: CrawlTargetId
    run_id: IngestionRunId
    normalized_url: str
    depth: int
    priority: int
    state: CrawlTargetState
    attempts: int
    page_type_hint: PageType | None = None
    lease_until: datetime | None = None
    next_attempt_at: datetime | None = None
    last_error: str | None = None
    snapshot_id: SourceSnapshotId | None = None

"""Website/Brand ingestion domain (S2-G1).

Owns the immutable provenance/run value objects for Slice 2 ingestion
(``SourceSnapshot``/``SourceChunk``/``IngestionRun``/``IngestionCheckpoint``/``CrawlTarget``)
and the pure vocabulary enums (``PageType``/``IngestionRunStatus``/
``IngestionPhase``/``CrawlTargetState``). No persistence, no orchestration, no
I/O — the S2-G2 migration gives these their first SQLite table.
"""

from ai_campaign_studio.domain.ingestion.entities import (
    CrawlTarget,
    IngestionCheckpoint,
    IngestionRun,
    IngestionRunStats,
    SourceChunk,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    CrawlTargetState,
    IngestionPhase,
    IngestionRunStatus,
    PageType,
)

__all__ = [
    "CrawlTarget",
    "CrawlTargetState",
    "IngestionCheckpoint",
    "IngestionPhase",
    "IngestionRun",
    "IngestionRunStats",
    "IngestionRunStatus",
    "PageType",
    "SourceChunk",
    "SourceSnapshot",
]

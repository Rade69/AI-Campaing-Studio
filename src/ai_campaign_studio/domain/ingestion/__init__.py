"""Website/Brand ingestion domain (S2-G1).

Owns the immutable provenance/run value objects for Slice 2 ingestion
(``SourceSnapshot``/``SourceChunk``/``IngestionRun``/``IngestionCheckpoint``)
and the pure vocabulary enums (``PageType``/``IngestionRunStatus``/
``IngestionPhase``). No persistence, no orchestration, no I/O — the S2-G2
migration gives these their first SQLite table.
"""

from ai_campaign_studio.domain.ingestion.entities import (
    IngestionCheckpoint,
    IngestionRun,
    IngestionRunStats,
    SourceChunk,
    SourceSnapshot,
)
from ai_campaign_studio.domain.ingestion.enums import (
    IngestionPhase,
    IngestionRunStatus,
    PageType,
)

__all__ = [
    "IngestionCheckpoint",
    "IngestionPhase",
    "IngestionRun",
    "IngestionRunStats",
    "IngestionRunStatus",
    "PageType",
    "SourceChunk",
    "SourceSnapshot",
]

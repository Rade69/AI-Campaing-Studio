"""Facts domain entities (A3).

Owns the immutable ``SourceReference`` provenance value object and the
immutable versioned ``ApprovedFact`` entity. A new fact version is a new
object — an existing ``ApprovedFact`` is never mutated in place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.common.ids import FactId
from ai_campaign_studio.domain.facts.enums import FactStatus


@dataclass(frozen=True)
class SourceReference:
    """Provenance reference for a fact.

    Even manual fixtures carry a provenance placeholder, e.g.
    ``source_type="fixture"``, ``uri="fixture://dental_clinic_v1"``.
    """

    source_type: str
    uri: str
    snapshot_id: str | None = None
    chunk_id: str | None = None


@dataclass(frozen=True)
class ApprovedFact:
    """An immutable version of an approved fact.

    ``id`` is the version-specific identifier; ``logical_fact_id`` is the
    stable identity shared by every version of the same fact.
    """

    id: FactId
    logical_fact_id: str
    version: int
    content: str
    source_ref: SourceReference
    status: FactStatus
    created_at: datetime
    superseded_by: FactId | None = None
    deleted_at: datetime | None = None

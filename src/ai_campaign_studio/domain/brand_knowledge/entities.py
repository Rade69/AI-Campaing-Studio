"""Brand Knowledge domain entities (BK-G1).

Owns the immutable ``KnowledgeEntry`` and ``BrandKnowledgeSnapshot`` value
objects. ``KnowledgeEntry`` is the structured interpretation of one or more
approved facts; ``BrandKnowledgeSnapshot`` is the ordered, versioned picture
of approved knowledge derived from ONE ``BrandSnapshot`` version. Plain
frozen dataclasses, same style as ``domain/ingestion/entities.py``. No
persistence, no extraction, no orchestration — BK-G2 gives these their first
SQLite table, BK-G3/G4 the classifiers, BK-G7 the snapshot builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_campaign_studio.domain.brand_knowledge.enums import (
    EvidenceType,
    KnowledgeCategory,
    KnowledgeStatus,
)
from ai_campaign_studio.domain.brand_knowledge.policies import assert_field_allowed
from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandKnowledgeSnapshotId,
    BrandSnapshotId,
    FactId,
    KnowledgeEntryId,
)


@dataclass(frozen=True)
class KnowledgeEntry:
    """One structured interpretation of one or more approved facts.

    ``confidence`` is NOT a probability that the fact is true (truth is
    already established via ``ApprovedFact``) — it is how sure the
    classifier is that the fact belongs to THIS category/field. The
    deterministic extractor (future BK-G3) always produces ``1.0``; LLM
    classification (future BK-G4) produces ``0.0``-``1.0``; a human
    manually approved value may be ``None``.
    """

    id: KnowledgeEntryId
    brand_snapshot_id: BrandSnapshotId
    category: KnowledgeCategory
    field: str
    value: str
    evidence_type: EvidenceType
    status: KnowledgeStatus
    source_fact_ids: tuple[FactId, ...]
    confidence: float | None
    conflict_group_id: str | None
    created_at: datetime
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_fact_ids", tuple(self.source_fact_ids))
        if not self.source_fact_ids:
            raise InvariantViolation(
                "KnowledgeEntry.source_fact_ids must not be empty "
                "(plan §4 -- HUMAN_MANUAL exception is a future feature, "
                "not v1)"
            )
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise InvariantViolation(
                f"KnowledgeEntry.confidence must be in [0.0, 1.0] or None, "
                f"got {self.confidence!r}"
            )
        if not self.value.strip():
            raise InvariantViolation("KnowledgeEntry.value must not be empty")
        assert_field_allowed(self.category, self.field)


@dataclass(frozen=True)
class BrandKnowledgeSnapshot:
    """Ordered, versioned picture of APPROVED knowledge for one brand.

    This does NOT replace the existing ``BrandSnapshot``
    (voice/audiences/services/visual_identity/restrictions/approved_fact_ids)
    — it is a derived extension: ``brand_snapshot_id`` points at the EXACT
    ``BrandSnapshot`` version this knowledge was derived from. Two different
    ``BrandSnapshot`` versions MAY yield two different Brand Knowledge
    snapshots; mixing facts from multiple ``BrandSnapshot`` versions into ONE
    Knowledge Snapshot is deliberately unsupported in v1 (a future use-case
    design, not this task). Do NOT modify the existing
    ``domain/brand/entities.py::BrandSnapshot`` to reference this new layer.

    A snapshot contains ONLY ``APPROVED`` entries (not ``PROPOSED``/
    ``REJECTED``/``CONFLICT``) — that invariant is enforced by the use-case
    that builds it (future BK-G7), NOT by this entity: it is a pure structure
    and does not know where its ``approved_entry_ids`` came from (same
    principle as ``IngestionRun``/``CrawlTarget`` validating only structure,
    not content).
    """

    id: BrandKnowledgeSnapshotId
    brand_snapshot_id: BrandSnapshotId
    version: int
    approved_entry_ids: tuple[KnowledgeEntryId, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "approved_entry_ids", tuple(self.approved_entry_ids)
        )

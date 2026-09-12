"""Unit tests for Brand Knowledge entities (BK-G1)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.brand_knowledge.entities import (
    BrandKnowledgeSnapshot,
    KnowledgeEntry,
)
from ai_campaign_studio.domain.brand_knowledge.enums import (
    EvidenceType,
    KnowledgeCategory,
    KnowledgeStatus,
)
from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandKnowledgeSnapshotId,
    BrandSnapshotId,
    FactId,
    KnowledgeEntryId,
)

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _entry(
    *,
    category: KnowledgeCategory = KnowledgeCategory.COMPANY,
    field: str = "name",
    value: str = "ACME",
    source_fact_ids: tuple[FactId, ...] = (FactId("fact-1"),),
    confidence: float | None = 1.0,
    status: KnowledgeStatus = KnowledgeStatus.PROPOSED,
    evidence_type: EvidenceType = EvidenceType.EXPLICIT,
) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeEntryId("entry-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        category=category,
        field=field,
        value=value,
        evidence_type=evidence_type,
        status=status,
        source_fact_ids=source_fact_ids,
        confidence=confidence,
        conflict_group_id=None,
        created_at=_CREATED_AT,
    )


def test_knowledge_entry_is_frozen() -> None:
    entry = _entry()
    with pytest.raises(FrozenInstanceError):
        entry.value = "changed"
    with pytest.raises(FrozenInstanceError):
        entry.status = KnowledgeStatus.APPROVED


def test_knowledge_entry_round_trip() -> None:
    entry = _entry()
    assert entry.id == KnowledgeEntryId("entry-1")
    assert entry.brand_snapshot_id == BrandSnapshotId("snap-1")
    assert entry.category is KnowledgeCategory.COMPANY
    assert entry.field == "name"
    assert entry.value == "ACME"
    assert entry.evidence_type is EvidenceType.EXPLICIT
    assert entry.status is KnowledgeStatus.PROPOSED
    assert entry.source_fact_ids == (FactId("fact-1"),)
    assert entry.confidence == 1.0
    assert entry.conflict_group_id is None
    assert entry.reviewed_at is None


def test_knowledge_entry_coerces_source_fact_ids_to_tuple() -> None:
    entry = _entry(source_fact_ids=[FactId("fact-1"), FactId("fact-2")])
    assert isinstance(entry.source_fact_ids, tuple)
    assert entry.source_fact_ids == (FactId("fact-1"), FactId("fact-2"))


def test_knowledge_entry_rejects_empty_source_fact_ids() -> None:
    with pytest.raises(InvariantViolation):
        _entry(source_fact_ids=())


def test_knowledge_entry_rejects_confidence_out_of_range() -> None:
    for bad in (-0.1, 1.1):
        with pytest.raises(InvariantViolation):
            _entry(confidence=bad)


def test_knowledge_entry_accepts_confidence_boundaries_and_none() -> None:
    assert _entry(confidence=0.0).confidence == 0.0
    assert _entry(confidence=1.0).confidence == 1.0
    assert _entry(confidence=None).confidence is None


def test_knowledge_entry_rejects_empty_value() -> None:
    with pytest.raises(InvariantViolation):
        _entry(value="")
    with pytest.raises(InvariantViolation):
        _entry(value="   ")


@pytest.mark.parametrize(
    ("category", "valid_field", "invalid_field"),
    [
        (KnowledgeCategory.COMPANY, "name", "nope"),
        (KnowledgeCategory.OFFERING, "service", "email"),
        (KnowledgeCategory.AUDIENCE, "target_segment", "price"),
        (KnowledgeCategory.DIFFERENTIATOR, "advantage", "phone"),
        (KnowledgeCategory.PRICING, "price", "tone"),
        (KnowledgeCategory.CONTACT, "email", "mission"),
        (KnowledgeCategory.BRAND_VOICE, "tone", "service"),
        (KnowledgeCategory.TRUST, "testimonial", "website"),
    ],
)
def test_knowledge_entry_field_allowed_per_category(
    category: KnowledgeCategory,
    valid_field: str,
    invalid_field: str,
) -> None:
    assert _entry(category=category, field=valid_field).field == valid_field
    with pytest.raises(InvariantViolation):
        _entry(category=category, field=invalid_field)


def _snapshot(
    approved_entry_ids: tuple[KnowledgeEntryId, ...] = (
        KnowledgeEntryId("entry-1"),
    ),
) -> BrandKnowledgeSnapshot:
    return BrandKnowledgeSnapshot(
        id=BrandKnowledgeSnapshotId("bks-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        version=1,
        approved_entry_ids=approved_entry_ids,
        created_at=_CREATED_AT,
    )


def test_brand_knowledge_snapshot_is_frozen() -> None:
    snap = _snapshot()
    with pytest.raises(FrozenInstanceError):
        snap.version = 2
    with pytest.raises(FrozenInstanceError):
        snap.approved_entry_ids = ()


def test_brand_knowledge_snapshot_coerces_approved_entry_ids_to_tuple() -> None:
    snap = _snapshot(
        approved_entry_ids=[KnowledgeEntryId("a"), KnowledgeEntryId("b")]
    )
    assert isinstance(snap.approved_entry_ids, tuple)
    assert snap.approved_entry_ids == (KnowledgeEntryId("a"), KnowledgeEntryId("b"))

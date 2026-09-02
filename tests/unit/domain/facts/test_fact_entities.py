"""Unit tests for facts entities (A3)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.ids import FactId
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _fact() -> ApprovedFact:
    return ApprovedFact(
        id=FactId("fact-1"),
        logical_fact_id="logical-1",
        version=1,
        content="We offer implantology.",
        source_ref=SourceReference(
            source_type="fixture", uri="fixture://dental_clinic_v1"
        ),
        status=FactStatus.APPROVED,
        created_at=_CREATED_AT,
    )


def test_source_reference_defaults() -> None:
    ref = SourceReference(source_type="fixture", uri="fixture://x")
    assert ref.snapshot_id is None
    assert ref.chunk_id is None


def test_source_reference_is_frozen() -> None:
    ref = SourceReference(source_type="fixture", uri="fixture://x")
    with pytest.raises(FrozenInstanceError):
        ref.uri = "changed"


def test_approved_fact_is_frozen() -> None:
    fact = _fact()
    with pytest.raises(FrozenInstanceError):
        fact.content = "changed"
    with pytest.raises(FrozenInstanceError):
        fact.status = FactStatus.SUPERSEDED


def test_approved_fact_optional_fields_default_to_none() -> None:
    fact = _fact()
    assert fact.superseded_by is None
    assert fact.deleted_at is None


def test_approved_fact_round_trip() -> None:
    fact = _fact()
    assert fact.id == FactId("fact-1")
    assert fact.logical_fact_id == "logical-1"
    assert fact.version == 1
    assert fact.content == "We offer implantology."
    assert fact.source_ref.source_type == "fixture"
    assert fact.source_ref.uri == "fixture://dental_clinic_v1"
    assert fact.status is FactStatus.APPROVED

"""Unit tests for facts entities (A3)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.ids import (
    FactCandidateId,
    FactId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.facts.entities import (
    ApprovedFact,
    FactCandidate,
    SourceReference,
)
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


def _candidate() -> FactCandidate:
    return FactCandidate(
        id=FactCandidateId("cand-1"),
        snapshot_id=SourceSnapshotId("snap-1"),
        content="We offer implantology.",
        created_at=_CREATED_AT,
    )


def test_fact_candidate_defaults_to_proposed() -> None:
    candidate = _candidate()
    assert candidate.status is FactStatus.PROPOSED
    assert candidate.chunk_id is None


def test_fact_candidate_is_frozen() -> None:
    candidate = _candidate()
    with pytest.raises(FrozenInstanceError):
        candidate.content = "changed"
    with pytest.raises(FrozenInstanceError):
        candidate.status = FactStatus.APPROVED


def test_fact_candidate_provenance_is_typed() -> None:
    """G-WI-EVIDENCE on the type level: provenance fields are typed IDs,
    not bare ``str``."""
    candidate = FactCandidate(
        id=FactCandidateId("cand-1"),
        snapshot_id=SourceSnapshotId("snap-1"),
        content="text",
        created_at=_CREATED_AT,
        chunk_id=SourceChunkId("chunk-1"),
    )
    assert candidate.snapshot_id == SourceSnapshotId("snap-1")
    assert candidate.chunk_id == SourceChunkId("chunk-1")

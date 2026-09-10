"""Unit tests for facts policies (A3)."""

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.errors import InvariantViolation
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
from ai_campaign_studio.domain.facts.policies import (
    assert_candidate_proposed,
    assert_fact_usable,
    build_approved_fact_from_candidate,
    create_next_fact_version,
    is_candidate_proposed,
    is_fact_usable,
)
from ai_campaign_studio.domain.ingestion.entities import SourceSnapshot

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _fact(
    status: FactStatus = FactStatus.APPROVED,
    version: int = 1,
    content: str = "old text",
    superseded_by: FactId | None = None,
) -> ApprovedFact:
    return ApprovedFact(
        id=FactId("fact-1"),
        logical_fact_id="logical-1",
        version=version,
        content=content,
        source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
        status=status,
        created_at=_CREATED_AT,
        superseded_by=superseded_by,
    )


def test_is_fact_usable_per_status() -> None:
    assert is_fact_usable(_fact(status=FactStatus.APPROVED)) is True
    assert is_fact_usable(_fact(status=FactStatus.SUPERSEDED)) is False
    assert is_fact_usable(_fact(status=FactStatus.SOFT_DELETED)) is False


def test_assert_fact_usable_raises_for_unusable() -> None:
    assert_fact_usable(_fact(status=FactStatus.APPROVED))  # no raise
    with pytest.raises(InvariantViolation):
        assert_fact_usable(_fact(status=FactStatus.SUPERSEDED))
    with pytest.raises(InvariantViolation):
        assert_fact_usable(_fact(status=FactStatus.SOFT_DELETED))


def test_create_next_fact_version_returns_new_approved() -> None:
    previous = _fact(version=3, content="old text")
    new_ref = SourceReference(source_type="fixture", uri="fixture://x")

    new_fact = create_next_fact_version(previous, "new text", new_ref)

    assert new_fact is not previous
    assert new_fact.id != previous.id
    assert new_fact.version == 4
    assert new_fact.content == "new text"
    assert new_fact.status is FactStatus.APPROVED
    assert new_fact.logical_fact_id == previous.logical_fact_id


def test_create_next_fact_version_does_not_mutate_previous() -> None:
    previous = _fact(
        status=FactStatus.APPROVED,
        version=1,
        content="old text",
        superseded_by=None,
    )
    before = (
        previous.id,
        previous.logical_fact_id,
        previous.version,
        previous.content,
        previous.status,
        previous.superseded_by,
    )

    create_next_fact_version(previous, "new text", previous.source_ref)

    after = (
        previous.id,
        previous.logical_fact_id,
        previous.version,
        previous.content,
        previous.status,
        previous.superseded_by,
    )
    assert after == before


def _candidate(status: FactStatus = FactStatus.PROPOSED) -> FactCandidate:
    return FactCandidate(
        id=FactCandidateId("cand-1"),
        snapshot_id=SourceSnapshotId("snap-1"),
        content="proposed text",
        created_at=_CREATED_AT,
        status=status,
    )


def test_is_candidate_proposed() -> None:
    assert is_candidate_proposed(_candidate()) is True
    # Any non-PROPOSED status (a future REJECTED, for example) is not eligible.
    assert is_candidate_proposed(_candidate(status=FactStatus.APPROVED)) is False


def test_assert_candidate_proposed_raises_for_non_proposed() -> None:
    assert_candidate_proposed(_candidate())  # no raise
    with pytest.raises(InvariantViolation):
        assert_candidate_proposed(_candidate(status=FactStatus.APPROVED))


def _snapshot(url: str = "https://example.ba/clanak") -> SourceSnapshot:
    return SourceSnapshot(
        id=SourceSnapshotId("snap-1"),
        url=url,
        fetched_at=_CREATED_AT,
        content_hash="hash",
    )


def test_build_approved_fact_from_candidate_is_version_one_approved() -> None:
    fact = build_approved_fact_from_candidate(_candidate(), _snapshot())

    assert fact.version == 1
    assert fact.status is FactStatus.APPROVED
    assert fact.content == "proposed text"
    assert fact.superseded_by is None
    assert fact.deleted_at is None


def test_build_approved_fact_from_candidate_has_fresh_logical_id() -> None:
    candidate = _candidate()
    fact = build_approved_fact_from_candidate(candidate, _snapshot())

    assert fact.logical_fact_id
    assert fact.logical_fact_id != candidate.id
    assert fact.id != candidate.id


def test_build_approved_fact_from_candidate_source_ref_points_at_snapshot() -> None:
    candidate = _candidate()
    snapshot = _snapshot(url="https://klix.ba/vijesti/x")

    fact = build_approved_fact_from_candidate(candidate, snapshot)

    assert fact.source_ref.source_type == "web_ingestion"
    assert fact.source_ref.uri == "https://klix.ba/vijesti/x"
    assert fact.source_ref.snapshot_id == str(candidate.snapshot_id)
    assert fact.source_ref.chunk_id is None


def test_build_approved_fact_from_candidate_carries_chunk_id_when_present() -> None:
    candidate = FactCandidate(
        id=FactCandidateId("cand-2"),
        snapshot_id=SourceSnapshotId("snap-1"),
        content="text",
        created_at=_CREATED_AT,
        chunk_id=SourceChunkId("chunk-9"),
    )

    fact = build_approved_fact_from_candidate(candidate, _snapshot())

    assert fact.source_ref.chunk_id == "chunk-9"


def test_build_approved_fact_does_not_mutate_candidate() -> None:
    candidate = _candidate()
    before = (
        candidate.id,
        candidate.snapshot_id,
        candidate.content,
        candidate.status,
        candidate.chunk_id,
    )

    build_approved_fact_from_candidate(candidate, _snapshot())

    after = (
        candidate.id,
        candidate.snapshot_id,
        candidate.content,
        candidate.status,
        candidate.chunk_id,
    )
    assert after == before

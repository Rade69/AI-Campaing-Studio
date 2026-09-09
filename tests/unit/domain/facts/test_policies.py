"""Unit tests for facts policies (A3)."""

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    FactCandidateId,
    FactId,
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
    create_next_fact_version,
    is_candidate_proposed,
    is_fact_usable,
)

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

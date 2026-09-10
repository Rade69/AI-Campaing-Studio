"""Unit tests for ApproveFactCandidate / RejectFactCandidate (S2-G7a)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_campaign_studio.application.ingestion import (
    ApproveFactCandidate,
    RejectFactCandidate,
)
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import FactCandidateId, SourceSnapshotId
from ai_campaign_studio.domain.facts.entities import FactCandidate
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.ingestion.entities import SourceSnapshot

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
_CAND_ID = FactCandidateId("cand-1")


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.entered = 0
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        self.entered += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:  # noqa: ANN001
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeIngestionRepo:
    def __init__(self, candidates=(), snapshots=()) -> None:  # noqa: ANN001
        self.candidates = {c.id: c for c in candidates}
        self.snapshots = {s.id: s for s in snapshots}
        self.save_candidate_calls = 0

    def get_fact_candidate(self, candidate_id):  # noqa: ANN001
        return self.candidates.get(candidate_id)

    def save_fact_candidate(self, candidate) -> None:  # noqa: ANN001
        self.candidates[candidate.id] = candidate
        self.save_candidate_calls += 1

    def get_source_snapshot(self, snapshot_id):  # noqa: ANN001
        return self.snapshots.get(snapshot_id)


class _FakeFactRepo:
    def __init__(self) -> None:
        self.facts: dict = {}
        self.save_calls = 0

    def save_fact(self, fact) -> None:  # noqa: ANN001
        self.facts[fact.id] = fact
        self.save_calls += 1


def _candidate(status: FactStatus = FactStatus.PROPOSED) -> FactCandidate:
    return FactCandidate(
        id=_CAND_ID,
        snapshot_id=SourceSnapshotId("snap-1"),
        content="proposed text",
        created_at=_CREATED_AT,
        status=status,
    )


def _snapshot() -> SourceSnapshot:
    return SourceSnapshot(
        id=SourceSnapshotId("snap-1"),
        url="https://example.ba/clanak",
        fetched_at=_CREATED_AT,
        content_hash="hash",
    )


def test_approve_creates_and_persists_fact_and_marks_candidate() -> None:
    ingestion = _FakeIngestionRepo([_candidate()], [_snapshot()])
    fact_repo = _FakeFactRepo()
    uow = _FakeUnitOfWork()

    fact = ApproveFactCandidate(ingestion, fact_repo, uow).execute(_CAND_ID)

    assert fact.status is FactStatus.APPROVED
    assert fact.version == 1
    assert fact.id in fact_repo.facts
    assert ingestion.candidates[_CAND_ID].status is FactStatus.APPROVED
    assert uow.committed is True
    assert uow.entered == 1


def test_approve_missing_candidate_raises_entity_not_found() -> None:
    ingestion = _FakeIngestionRepo([], [_snapshot()])
    fact_repo = _FakeFactRepo()
    uow = _FakeUnitOfWork()

    with pytest.raises(EntityNotFound):
        ApproveFactCandidate(ingestion, fact_repo, uow).execute(
            FactCandidateId("missing")
        )

    assert fact_repo.save_calls == 0
    assert uow.entered == 0


def test_approve_non_proposed_raises_and_writes_nothing() -> None:
    ingestion = _FakeIngestionRepo(
        [_candidate(status=FactStatus.APPROVED)], [_snapshot()]
    )
    fact_repo = _FakeFactRepo()
    uow = _FakeUnitOfWork()

    with pytest.raises(InvariantViolation):
        ApproveFactCandidate(ingestion, fact_repo, uow).execute(_CAND_ID)

    assert fact_repo.save_calls == 0
    assert ingestion.save_candidate_calls == 0
    assert uow.entered == 0
    assert ingestion.candidates[_CAND_ID].status is FactStatus.APPROVED


def test_approve_missing_snapshot_raises_entity_not_found() -> None:
    ingestion = _FakeIngestionRepo([_candidate()], [])
    fact_repo = _FakeFactRepo()
    uow = _FakeUnitOfWork()

    with pytest.raises(EntityNotFound):
        ApproveFactCandidate(ingestion, fact_repo, uow).execute(_CAND_ID)

    assert fact_repo.save_calls == 0
    assert uow.entered == 0


def test_approve_does_not_mutate_original_candidate_object() -> None:
    original = _candidate()
    ingestion = _FakeIngestionRepo([original], [_snapshot()])
    fact_repo = _FakeFactRepo()
    uow = _FakeUnitOfWork()

    ApproveFactCandidate(ingestion, fact_repo, uow).execute(_CAND_ID)

    assert original.status is FactStatus.PROPOSED  # frozen, untouched
    persisted = ingestion.candidates[_CAND_ID]
    assert persisted is not original
    assert persisted.status is FactStatus.APPROVED


def test_reject_marks_candidate_rejected_and_never_creates_fact() -> None:
    ingestion = _FakeIngestionRepo([_candidate()], [_snapshot()])
    uow = _FakeUnitOfWork()

    RejectFactCandidate(ingestion, uow).execute(_CAND_ID)

    assert ingestion.candidates[_CAND_ID].status is FactStatus.REJECTED
    assert uow.committed is True


def test_reject_missing_candidate_raises_entity_not_found() -> None:
    ingestion = _FakeIngestionRepo([], [_snapshot()])
    uow = _FakeUnitOfWork()

    with pytest.raises(EntityNotFound):
        RejectFactCandidate(ingestion, uow).execute(FactCandidateId("missing"))

    assert uow.entered == 0


def test_reject_non_proposed_raises_and_writes_nothing() -> None:
    ingestion = _FakeIngestionRepo(
        [_candidate(status=FactStatus.REJECTED)], [_snapshot()]
    )
    uow = _FakeUnitOfWork()

    with pytest.raises(InvariantViolation):
        RejectFactCandidate(ingestion, uow).execute(_CAND_ID)

    assert ingestion.save_candidate_calls == 0
    assert uow.entered == 0


def test_reject_accepts_reason_without_persisting_it() -> None:
    # ``reason`` is accepted for API stability; FactCandidate has no field for it.
    ingestion = _FakeIngestionRepo([_candidate()], [_snapshot()])
    uow = _FakeUnitOfWork()

    RejectFactCandidate(ingestion, uow).execute(_CAND_ID, reason="duplicate")

    persisted = ingestion.candidates[_CAND_ID]
    assert persisted.status is FactStatus.REJECTED
    assert not hasattr(persisted, "reason")

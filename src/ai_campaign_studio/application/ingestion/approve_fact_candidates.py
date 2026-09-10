"""Approve/Reject FactCandidate use-cases (S2-G7a).

Owns the human-review step of the fact-first pipeline (canonical plan §2/§11):
``ApproveFactCandidate`` turns a PROPOSED ``FactCandidate`` into a NEW
``ApprovedFact`` and persists the fact plus the candidate's new APPROVED status
ATOMICALLY; ``RejectFactCandidate`` marks the candidate REJECTED. The candidate
is never mutated in place (frozen dataclass + ``dataclasses.replace``), and a
non-PROPOSED candidate always raises — double approve/reject must fail, never
silently no-op (provenance invariant).

Does NOT link the fact to a ``BrandSnapshot`` — that is S2-G7b's separate
``assemble_brand_snapshot`` operation (v1 boundary, not an oversight). Does NOT
build candidates (S2-G6 pipeline).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ai_campaign_studio.domain.common.errors import EntityNotFound
from ai_campaign_studio.domain.common.ids import FactCandidateId
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.facts.policies import (
    assert_candidate_proposed,
    build_approved_fact_from_candidate,
)
from ai_campaign_studio.ports.repositories import (
    FactRepositoryPort,
    IngestionRepositoryPort,
)


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-cases need."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class ApproveFactCandidate:
    """Approve a PROPOSED candidate into a new ``ApprovedFact`` (atomic)."""

    def __init__(
        self,
        ingestion_repo: IngestionRepositoryPort,
        fact_repo: FactRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._ingestion_repo = ingestion_repo
        self._fact_repo = fact_repo
        self._unit_of_work = unit_of_work

    def execute(self, candidate_id: FactCandidateId) -> ApprovedFact:
        """Create and persist an ``ApprovedFact`` for a PROPOSED candidate.

        Raises ``EntityNotFound`` if the candidate or its snapshot is missing,
        and ``InvariantViolation`` (via ``assert_candidate_proposed``) if the
        candidate is not PROPOSED. On any raise nothing is written.
        """
        candidate = self._ingestion_repo.get_fact_candidate(candidate_id)
        if candidate is None:
            raise EntityNotFound(f"fact candidate {candidate_id} not found")

        assert_candidate_proposed(candidate)

        snapshot = self._ingestion_repo.get_source_snapshot(candidate.snapshot_id)
        if snapshot is None:
            raise EntityNotFound(
                f"source snapshot {candidate.snapshot_id} not found"
            )

        approved_fact = build_approved_fact_from_candidate(candidate, snapshot)
        approved_candidate = replace(candidate, status=FactStatus.APPROVED)

        with self._unit_of_work:
            self._fact_repo.save_fact(approved_fact)
            self._ingestion_repo.save_fact_candidate(approved_candidate)
            self._unit_of_work.commit()

        return approved_fact


class RejectFactCandidate:
    """Mark a PROPOSED candidate REJECTED (never creates an ``ApprovedFact``)."""

    def __init__(
        self,
        ingestion_repo: IngestionRepositoryPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._ingestion_repo = ingestion_repo
        self._unit_of_work = unit_of_work

    def execute(
        self, candidate_id: FactCandidateId, reason: str | None = None
    ) -> None:
        """Persist the candidate with ``status=REJECTED``.

        Raises ``EntityNotFound`` if the candidate is missing and
        ``InvariantViolation`` if it is not PROPOSED (double reject /
        reject-after-approve must fail).

        ``reason`` is accepted for API stability (the S2-G7b bridge may pass
        one) but is NOT persisted: ``FactCandidate`` has no field for it, and
        adding one is a ``domain/facts/entities.py`` change outside this task's
        ``allowed_paths`` (see OUT_OF_SCOPE_FINDING in the evidence report).
        """
        candidate = self._ingestion_repo.get_fact_candidate(candidate_id)
        if candidate is None:
            raise EntityNotFound(f"fact candidate {candidate_id} not found")

        assert_candidate_proposed(candidate)

        rejected_candidate = replace(candidate, status=FactStatus.REJECTED)

        with self._unit_of_work:
            self._ingestion_repo.save_fact_candidate(rejected_candidate)
            self._unit_of_work.commit()


__all__ = ["ApproveFactCandidate", "RejectFactCandidate"]

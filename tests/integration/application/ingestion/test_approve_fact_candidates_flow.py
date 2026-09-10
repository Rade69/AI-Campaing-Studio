"""Integration tests for the S2-G7a approve/reject flow on real SQLite.

Proves G-WI-EVIDENCE at the DATA level: an approved fact traces back to the
immutable ``SourceSnapshot`` it came from, not just at the type level (S2-G1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.application.ingestion import (
    ApproveFactCandidate,
    RejectFactCandidate,
)
from ai_campaign_studio.domain.common.errors import InvariantViolation
from ai_campaign_studio.domain.common.ids import FactCandidateId, SourceSnapshotId
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.facts.entities import FactCandidate
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.domain.ingestion.entities import SourceSnapshot
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteFactRepository,
    SqliteIngestionRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CAND_ID = FactCandidateId("cand-1")


def _setup_db(tmp_path: Path):  # noqa: ANN202
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _seed(
    ingestion_repo: SqliteIngestionRepository,
    status: FactStatus = FactStatus.PROPOSED,
) -> None:
    ingestion_repo.save_source_snapshot(
        SourceSnapshot(
            id=SourceSnapshotId("snap-1"),
            url="https://klix.ba/vijesti/primjer",
            fetched_at=utc_now(),
            content_hash="hash-1",
        )
    )
    ingestion_repo.save_fact_candidate(
        FactCandidate(
            id=_CAND_ID,
            snapshot_id=SourceSnapshotId("snap-1"),
            content="Klix je objavio vijest o događaju.",
            created_at=utc_now(),
            status=status,
        )
    )


def test_approve_creates_approved_fact_traceable_to_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    ingestion = SqliteIngestionRepository(connection)
    facts = SqliteFactRepository(connection)
    uow = SqliteUnitOfWork(connection)
    _seed(ingestion)

    fact = ApproveFactCandidate(ingestion, facts, uow).execute(_CAND_ID)

    # G-WI-EVIDENCE at the DATA level.
    assert fact.source_ref.uri == "https://klix.ba/vijesti/primjer"
    assert fact.source_ref.snapshot_id == "snap-1"
    assert fact.source_ref.source_type == "web_ingestion"
    assert fact.status is FactStatus.APPROVED
    assert fact.version == 1

    assert facts.get_fact(fact.id) == fact
    persisted_candidate = ingestion.get_fact_candidate(_CAND_ID)
    assert persisted_candidate is not None
    assert persisted_candidate.status is FactStatus.APPROVED
    connection.close()


def test_approve_does_not_link_fact_to_any_brand_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    ingestion = SqliteIngestionRepository(connection)
    facts = SqliteFactRepository(connection)
    uow = SqliteUnitOfWork(connection)
    _seed(ingestion)

    ApproveFactCandidate(ingestion, facts, uow).execute(_CAND_ID)

    # Deliberate v1 boundary (§2): G7a creates a free-floating ApprovedFact;
    # brand-snapshot linkage is S2-G7b's assemble_brand_snapshot.
    count = connection.execute(
        "SELECT COUNT(*) FROM brand_snapshot_facts"
    ).fetchone()[0]
    assert count == 0
    connection.close()


def test_approve_non_proposed_raises_and_persists_nothing(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    ingestion = SqliteIngestionRepository(connection)
    facts = SqliteFactRepository(connection)
    uow = SqliteUnitOfWork(connection)
    _seed(ingestion, status=FactStatus.APPROVED)

    with pytest.raises(InvariantViolation):
        ApproveFactCandidate(ingestion, facts, uow).execute(_CAND_ID)

    assert connection.execute(
        "SELECT COUNT(*) FROM approved_facts"
    ).fetchone()[0] == 0
    candidate = ingestion.get_fact_candidate(_CAND_ID)
    assert candidate is not None
    assert candidate.status is FactStatus.APPROVED  # unchanged
    connection.close()


def test_approve_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    ingestion = SqliteIngestionRepository(connection)
    facts = SqliteFactRepository(connection)
    uow = SqliteUnitOfWork(connection)
    _seed(ingestion)

    class _FailingIngestionRepo:
        """``save_fact`` succeeds, ``save_fact_candidate`` raises mid-write."""

        def __init__(self, inner: SqliteIngestionRepository) -> None:
            self._inner = inner

        def get_fact_candidate(self, candidate_id):  # noqa: ANN001
            return self._inner.get_fact_candidate(candidate_id)

        def get_source_snapshot(self, snapshot_id):  # noqa: ANN001
            return self._inner.get_source_snapshot(snapshot_id)

        def save_fact_candidate(self, candidate) -> None:  # noqa: ANN001
            raise RuntimeError("simulated mid-write failure")

    with pytest.raises(RuntimeError):
        ApproveFactCandidate(_FailingIngestionRepo(ingestion), facts, uow).execute(
            _CAND_ID
        )

    # save_fact was written, then save_fact_candidate raised -> whole txn rolled
    # back, so NEITHER write survived.
    assert connection.execute(
        "SELECT COUNT(*) FROM approved_facts"
    ).fetchone()[0] == 0
    candidate = ingestion.get_fact_candidate(_CAND_ID)
    assert candidate is not None
    assert candidate.status is FactStatus.PROPOSED
    connection.close()


def test_reject_persists_rejected_and_creates_no_fact(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    ingestion = SqliteIngestionRepository(connection)
    uow = SqliteUnitOfWork(connection)
    _seed(ingestion)

    RejectFactCandidate(ingestion, uow).execute(_CAND_ID, reason="not verifiable")

    candidate = ingestion.get_fact_candidate(_CAND_ID)
    assert candidate is not None
    assert candidate.status is FactStatus.REJECTED
    assert connection.execute(
        "SELECT COUNT(*) FROM approved_facts"
    ).fetchone()[0] == 0
    connection.close()

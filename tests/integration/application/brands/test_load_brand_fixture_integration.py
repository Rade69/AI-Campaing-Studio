"""Integration tests for LoadBrandFixture (A6) on a real SQLite DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteFactRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.repositories import FactRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


def _setup_db(tmp_path: Path):
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _table_counts(connection) -> dict[str, int]:
    tables = ("brands", "brand_snapshots", "approved_facts", "brand_snapshot_facts")
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }


class _FailingFactRepository:
    """Wraps a real FactRepository but raises on the N-th save_fact call."""

    def __init__(self, inner: FactRepositoryPort, fail_on: int) -> None:
        self._inner = inner
        self._fail_on = fail_on
        self._calls = 0

    def save_fact(self, fact) -> None:  # noqa: ANN001
        self._calls += 1
        if self._calls == self._fail_on:
            raise RuntimeError("simulated mid-load failure")
        self._inner.save_fact(fact)

    def get_fact(self, fact_id):  # noqa: ANN001
        return self._inner.get_fact(fact_id)

    def list_snapshot_facts(self, snapshot_id):  # noqa: ANN001
        return self._inner.list_snapshot_facts(snapshot_id)


def test_load_persists_brand_facts_and_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    uow = SqliteUnitOfWork(connection)
    use_case = LoadBrandFixture(brand_repo, fact_repo, uow)

    snapshot = use_case.execute(_FIXTURE_PATH)

    # Read back through the ports.
    assert brand_repo.get_snapshot(snapshot.id) == snapshot
    facts = fact_repo.list_snapshot_facts(snapshot.id)
    assert len(facts) == 3
    assert tuple(fact.id for fact in facts) == snapshot.approved_fact_ids

    connection.close()


def test_load_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    inner_fact_repo = SqliteFactRepository(connection)
    failing_fact_repo = _FailingFactRepository(inner_fact_repo, fail_on=2)
    uow = SqliteUnitOfWork(connection)
    use_case = LoadBrandFixture(brand_repo, failing_fact_repo, uow)

    with pytest.raises(RuntimeError):
        use_case.execute(_FIXTURE_PATH)

    # Every table must be empty — the whole load rolled back.
    assert _table_counts(connection) == {
        "brands": 0,
        "brand_snapshots": 0,
        "approved_facts": 0,
        "brand_snapshot_facts": 0,
    }
    connection.close()


def test_facts_have_fixture_provenance(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    uow = SqliteUnitOfWork(connection)
    use_case = LoadBrandFixture(brand_repo, fact_repo, uow)

    snapshot = use_case.execute(_FIXTURE_PATH)
    facts = fact_repo.list_snapshot_facts(snapshot.id)

    assert facts
    for fact in facts:
        assert fact.source_ref.uri.startswith("fixture://")
    connection.close()

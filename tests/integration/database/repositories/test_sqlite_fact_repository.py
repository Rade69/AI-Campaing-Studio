"""Integration tests for SqliteFactRepository (A5)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId, FactId
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteFactRepository,
)
from ai_campaign_studio.ports.repositories import FactRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _facts() -> tuple[ApprovedFact, ...]:
    return (
        ApprovedFact(
            id=FactId("fact-1"),
            logical_fact_id="logical-1",
            version=1,
            content="Fact one.",
            source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
            status=FactStatus.APPROVED,
            created_at=_CREATED_AT,
        ),
        ApprovedFact(
            id=FactId("fact-2"),
            logical_fact_id="logical-2",
            version=2,
            content="Fact two (superseded).",
            source_ref=SourceReference(
                source_type="fixture",
                uri="fixture://x",
                snapshot_id="snap-src",
                chunk_id="chunk-1",
            ),
            status=FactStatus.SUPERSEDED,
            created_at=_CREATED_AT,
            superseded_by=FactId("fact-3"),
            deleted_at=datetime(2026, 2, 1, tzinfo=UTC),
        ),
    )


def _snapshot() -> BrandSnapshot:
    return BrandSnapshot(
        id=BrandSnapshotId("snap-1"),
        brand_id=BrandId("brand-1"),
        version=1,
        language="BHS",
        locale="BHS_LATIN",
        script="LATIN",
        voice=BrandVoice(formality="friendly"),
        audiences=[
            Audience(id="a1", name="Adults", description="25-45"),
        ],
        services=[ServiceDefinition(id="s1", name="Implants", description="...")],
        visual_identity=VisualIdentity(),
        restrictions=[Restriction(description="No guarantees.")],
        approved_fact_ids=[FactId("fact-1"), FactId("fact-2")],
        created_at=_CREATED_AT,
    )


def test_repository_is_a_fact_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteFactRepository(connection)
    assert isinstance(repo, FactRepositoryPort)
    connection.close()


def test_round_trip_fact_including_optional_fields(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteFactRepository(connection)

    for fact in _facts():
        repo.save_fact(fact)
        loaded = repo.get_fact(fact.id)
        assert loaded == fact

    connection.close()


def test_get_unknown_fact_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteFactRepository(connection)
    assert repo.get_fact(FactId("missing")) is None
    connection.close()


def test_save_fact_is_idempotent(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteFactRepository(connection)

    fact = _facts()[0]
    repo.save_fact(fact)
    repo.save_fact(fact)  # must not raise

    count = connection.execute(
        "SELECT COUNT(*) FROM approved_facts WHERE id = ?", (fact.id,)
    ).fetchone()[0]
    assert count == 1
    connection.close()


def test_list_snapshot_facts_preserves_order(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    fact_repo = SqliteFactRepository(connection)
    brand_repo = SqliteBrandRepository(connection)

    brand = Brand(id=BrandId("brand-1"), name="BrightSmile", created_at=_CREATED_AT)
    brand_repo.save_brand(brand)
    facts = _facts()
    for fact in facts:
        fact_repo.save_fact(fact)
    brand_repo.save_snapshot(_snapshot())

    loaded = fact_repo.list_snapshot_facts(BrandSnapshotId("snap-1"))
    assert loaded == facts  # same content and same order
    connection.close()

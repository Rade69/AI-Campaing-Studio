"""Integration tests for SqliteBrandRepository (A5)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from ai_campaign_studio.ports.repositories import BrandRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _brand() -> Brand:
    return Brand(id=BrandId("brand-1"), name="BrightSmile", created_at=_CREATED_AT)


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
            version=1,
            content="Fact two.",
            source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
            status=FactStatus.APPROVED,
            created_at=_CREATED_AT,
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
        voice=BrandVoice(
            formality="friendly",
            tone=["warm"],
            preferred_terms=["implant"],
            forbidden_terms=["cheap"],
            regional_vocabulary=["stomatolog"],
            tone_examples=["We care."],
        ),
        audiences=[
            Audience(
                id="a1",
                name="Adults",
                description="25-45",
                needs=["care"],
                objections=["cost"],
            )
        ],
        services=[ServiceDefinition(id="s1", name="Implants", description="...")],
        visual_identity=VisualIdentity(
            logo_path="logo.png",
            primary_colors=["#000000"],
            secondary_colors=["#ffffff"],
            font_families=["Inter"],
            image_style_notes=["clean"],
        ),
        restrictions=[Restriction(description="No medical guarantees.")],
        approved_fact_ids=[FactId("fact-1"), FactId("fact-2")],
        created_at=_CREATED_AT,
    )


def test_repository_is_a_brand_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteBrandRepository(connection)
    assert isinstance(repo, BrandRepositoryPort)
    connection.close()


def test_migrations_apply_cleanly(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    applied = run_migrations(connection, _MIGRATIONS_DIR)
    assert {0, 1} <= set(applied)

    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {
        "brands",
        "brand_snapshots",
        "approved_facts",
        "brand_snapshot_facts",
    } <= tables
    connection.close()


def test_round_trip_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)

    brand = _brand()
    brand_repo.save_brand(brand)
    for fact in _facts():
        fact_repo.save_fact(fact)

    snapshot = _snapshot()
    brand_repo.save_snapshot(snapshot)

    loaded = brand_repo.get_snapshot(BrandSnapshotId("snap-1"))
    assert loaded == snapshot  # dataclass equality covers every field
    connection.close()


def test_save_snapshot_is_idempotent(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)

    brand_repo.save_brand(_brand())
    for fact in _facts():
        fact_repo.save_fact(fact)

    snapshot = _snapshot()
    brand_repo.save_snapshot(snapshot)
    brand_repo.save_snapshot(snapshot)  # must not raise nor duplicate rows

    count = connection.execute(
        "SELECT COUNT(*) FROM brand_snapshot_facts WHERE snapshot_id = ?",
        (snapshot.id,),
    ).fetchone()[0]
    assert count == len(snapshot.approved_fact_ids)
    connection.close()


def test_get_unknown_snapshot_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteBrandRepository(connection)
    assert repo.get_snapshot(BrandSnapshotId("missing")) is None
    connection.close()


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO brand_snapshot_facts (snapshot_id, fact_id, position)"
            " VALUES ('missing-snap', 'missing-fact', 0)"
        )
    connection.close()

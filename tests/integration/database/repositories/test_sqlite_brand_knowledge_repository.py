"""Integration tests for SqliteBrandKnowledgeRepository (BK-G2)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.domain.brand_knowledge.entities import (
    BrandKnowledgeSnapshot,
    KnowledgeEntry,
)
from ai_campaign_studio.domain.brand_knowledge.enums import (
    EvidenceType,
    KnowledgeCategory,
    KnowledgeStatus,
)
from ai_campaign_studio.domain.common.ids import (
    BrandKnowledgeSnapshotId,
    BrandSnapshotId,
    FactId,
    KnowledgeEntryId,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    sqlite_brand_knowledge_repository as brand_knowledge_repo,
)
from ai_campaign_studio.ports.repositories import BrandKnowledgeRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _seed_parents(connection: sqlite3.Connection) -> None:
    """Insert the FK parent rows a brand-knowledge row references.

    ``brand_knowledge_entries`` FK-references ``brand_snapshots``, and
    ``brand_knowledge_entry_facts`` FK-references ``approved_facts`` — both
    parent tables are seeded directly here so the tests stay focused on the
    brand-knowledge repository itself (same style as the existing
    ``test_foreign_keys_are_enforced`` direct-INSERT pattern).
    """
    connection.execute(
        "INSERT INTO brands (id, name, created_at)"
        " VALUES ('brand-1', 'BrightSmile', '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO brand_snapshots (id, brand_id, version, language, locale,"
        " script, voice_json, audiences_json, services_json,"
        " visual_identity_json, restrictions_json, created_at)"
        " VALUES ('snap-1', 'brand-1', 1, 'BHS', 'BHS_LATIN', 'LATIN',"
        " '{}', '[]', '[]', '{}', '[]', '2026-01-01T00:00:00+00:00')"
    )
    for fact_id in ("fact-1", "fact-2"):
        connection.execute(
            "INSERT INTO approved_facts (id, logical_fact_id, version, content,"
            " source_type, source_uri, status, created_at)"
            " VALUES (?, ?, 1, ?, 'fixture', 'fixture://x', 'APPROVED',"
            " '2026-01-01T00:00:00+00:00')",
            (fact_id, f"logical-{fact_id}", f"Fact {fact_id}."),
        )


def _entry(
    *,
    id: str = "entry-1",
    status: KnowledgeStatus = KnowledgeStatus.PROPOSED,
    source_fact_ids: tuple[str, ...] = ("fact-1",),
    confidence: float | None = None,
    conflict_group_id: str | None = None,
    reviewed_at: datetime | None = None,
) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeEntryId(id),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        category=KnowledgeCategory.COMPANY,
        field="name",
        value="BrightSmile",
        evidence_type=EvidenceType.EXPLICIT,
        status=status,
        source_fact_ids=tuple(FactId(f) for f in source_fact_ids),
        confidence=confidence,
        conflict_group_id=conflict_group_id,
        created_at=_CREATED_AT,
        reviewed_at=reviewed_at,
    )


def _knowledge_snapshot(
    *,
    id: str = "bks-1",
    version: int = 1,
    approved_entry_ids: tuple[str, ...] = (),
) -> BrandKnowledgeSnapshot:
    return BrandKnowledgeSnapshot(
        id=BrandKnowledgeSnapshotId(id),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        version=version,
        approved_entry_ids=tuple(
            KnowledgeEntryId(e) for e in approved_entry_ids
        ),
        created_at=_CREATED_AT,
    )


def test_repository_is_a_brand_knowledge_repository_port(
    tmp_path: Path,
) -> None:
    connection = _setup_db(tmp_path)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)
    assert isinstance(repo, BrandKnowledgeRepositoryPort)
    connection.close()


def test_migrations_apply_brand_knowledge_tables(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {
        "brand_knowledge_entries",
        "brand_knowledge_entry_facts",
        "brand_knowledge_snapshots",
        "brand_knowledge_snapshot_entries",
    } <= tables
    connection.close()


def test_round_trip_entry(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    entry = _entry(source_fact_ids=("fact-1", "fact-2"))
    repo.save_entry(entry)

    loaded = repo.get_entry(KnowledgeEntryId("entry-1"))
    assert loaded == entry  # dataclass equality covers every field
    connection.close()


def test_entry_source_fact_ids_order_preserved(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    repo.save_entry(_entry(source_fact_ids=("fact-2", "fact-1")))

    loaded = repo.get_entry(KnowledgeEntryId("entry-1"))
    assert loaded is not None
    assert loaded.source_fact_ids == (FactId("fact-2"), FactId("fact-1"))
    connection.close()


def test_save_entry_is_upsert(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    reviewed_at = datetime(2026, 2, 1, tzinfo=UTC)
    repo.save_entry(_entry(status=KnowledgeStatus.PROPOSED))
    repo.save_entry(
        _entry(status=KnowledgeStatus.APPROVED, reviewed_at=reviewed_at)
    )

    loaded = repo.get_entry(KnowledgeEntryId("entry-1"))
    assert loaded is not None
    assert loaded.status is KnowledgeStatus.APPROVED
    assert loaded.reviewed_at == reviewed_at
    connection.close()


def test_list_entries_for_brand_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    repo.save_entry(_entry(id="entry-1", status=KnowledgeStatus.APPROVED))
    repo.save_entry(_entry(id="entry-2", status=KnowledgeStatus.PROPOSED))

    listed = repo.list_entries_for_brand_snapshot(BrandSnapshotId("snap-1"))
    assert {e.id for e in listed} == {
        KnowledgeEntryId("entry-1"),
        KnowledgeEntryId("entry-2"),
    }
    connection.close()


def test_list_entries_by_status_filters(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    repo.save_entry(_entry(id="entry-1", status=KnowledgeStatus.APPROVED))
    repo.save_entry(_entry(id="entry-2", status=KnowledgeStatus.PROPOSED))
    repo.save_entry(_entry(id="entry-3", status=KnowledgeStatus.REJECTED))

    approved = repo.list_entries_by_status(
        BrandSnapshotId("snap-1"), KnowledgeStatus.APPROVED
    )
    assert {e.id for e in approved} == {KnowledgeEntryId("entry-1")}
    connection.close()


def test_entry_foreign_keys_are_enforced(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO brand_knowledge_entries (id, brand_snapshot_id,"
            " category, field_name, value, evidence_type, status, created_at)"
            " VALUES ('e-x', 'missing-snap', 'COMPANY', 'name', 'x',"
            " 'EXPLICIT', 'PROPOSED', '2026-01-01T00:00:00+00:00')"
        )
    # entry_id must reference a REAL brand_knowledge_entries row here --
    # otherwise this insert would raise on the entry_id FK alone and never
    # actually exercise the fact_id FK (caught via mutation test: removing
    # ``fact_id REFERENCES approved_facts(id)`` from the migration left
    # this assertion passing unchanged when it used a nonexistent
    # entry_id).
    connection.execute(
        "INSERT INTO brand_knowledge_entries (id, brand_snapshot_id,"
        " category, field_name, value, evidence_type, status, created_at)"
        " VALUES ('entry-real', 'snap-1', 'COMPANY', 'name', 'x',"
        " 'EXPLICIT', 'PROPOSED', '2026-01-01T00:00:00+00:00')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO brand_knowledge_entry_facts (entry_id, fact_id,"
            " position) VALUES ('entry-real', 'missing-fact', 0)"
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO brand_knowledge_entry_facts (entry_id, fact_id,"
            " position) VALUES ('missing-entry', 'fact-1', 0)"
        )
    connection.close()


def test_round_trip_knowledge_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    repo.save_entry(_entry(id="entry-1"))
    repo.save_entry(_entry(id="entry-2"))

    snapshot = _knowledge_snapshot(approved_entry_ids=("entry-2", "entry-1"))
    repo.save_knowledge_snapshot(snapshot)

    loaded = repo.get_knowledge_snapshot(BrandKnowledgeSnapshotId("bks-1"))
    assert loaded == snapshot  # dataclass equality covers every field
    assert loaded.approved_entry_ids == (
        KnowledgeEntryId("entry-2"),
        KnowledgeEntryId("entry-1"),
    )
    connection.close()


def test_get_latest_knowledge_snapshot(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    repo.save_knowledge_snapshot(_knowledge_snapshot(id="bks-1", version=1))
    repo.save_knowledge_snapshot(_knowledge_snapshot(id="bks-2", version=2))

    latest = repo.get_latest_knowledge_snapshot(BrandSnapshotId("snap-1"))
    assert latest is not None
    assert latest.id == BrandKnowledgeSnapshotId("bks-2")
    assert latest.version == 2
    connection.close()


def test_knowledge_snapshot_unique_brand_snapshot_version(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    _seed_parents(connection)
    repo = brand_knowledge_repo.SqliteBrandKnowledgeRepository(connection)

    repo.save_knowledge_snapshot(_knowledge_snapshot(id="bks-1", version=1))
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_knowledge_snapshot(_knowledge_snapshot(id="bks-2", version=1))
    connection.close()

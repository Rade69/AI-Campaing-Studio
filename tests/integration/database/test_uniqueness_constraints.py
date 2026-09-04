"""Integration tests for the uniqueness-constraints migration (ACS-F1-023)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "resources" / "migrations"


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    conn = create_connection(tmp_path / "test.db")
    run_migrations(conn, MIGRATIONS_DIR)
    return conn


def _insert_plan_chain(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO campaign_briefs (id, offer, goal, audience_text,"
        " targets_json, content_piece_count, content_language_context,"
        " special_instructions_json, created_at)"
        " VALUES ('brief-1', 'o', 'g', 'a', '[]', 1, 'EN', '[]',"
        " '2026-01-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO campaigns (id, brand_id, brand_snapshot_id, brief_id,"
        " status, created_at)"
        " VALUES ('campaign-1', 'brand-1', 'snap-1', 'brief-1', 'DRAFT',"
        " '2026-01-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO campaign_plans (id, campaign_id, version, status, created_at)"
        " VALUES ('plan-1', 'campaign-1', 1, 'DRAFT', '2026-01-01T00:00:00+00:00')"
    )


def test_migration_applies_unique_indexes(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    applied = [
        row["version"]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    ]
    assert 4 in applied

    revision_indexes = {
        row["name"]
        for row in conn.execute("PRAGMA index_list(revisions)").fetchall()
    }
    item_indexes = {
        row["name"]
        for row in conn.execute("PRAGMA index_list(campaign_items)").fetchall()
    }
    assert "idx_revisions_entity_version" in revision_indexes
    assert "idx_campaign_items_plan_order" in item_indexes
    conn.close()


def test_revisions_duplicate_entity_version_raises(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    insert = (
        "INSERT INTO revisions (id, entity_type, entity_id, version, timestamp,"
        " origin, previous_value, new_value)"
        " VALUES (?, 'ContentPiece', 'post-1', 1, '2026-01-01T00:00:00+00:00',"
        " 'AI', 'null', '{}')"
    )
    conn.execute(insert, ("rev-1",))

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("rev-2",))
    conn.close()


def test_campaign_items_duplicate_plan_order_raises(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    _insert_plan_chain(conn)

    insert = (
        "INSERT INTO campaign_items (id, plan_id, \"order\", role, topic, goal,"
        " target_audience_id, facts_needed_json, status)"
        " VALUES (?, 'plan-1', 1, 'PROBLEM', 'topic', 'goal', NULL, '[]',"
        " 'PLANNED')"
    )
    conn.execute(insert, ("item-1",))

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("item-2",))
    conn.close()

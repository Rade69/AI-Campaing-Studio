"""Integration tests for the migration runner (P0.17)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ai_campaign_studio.domain.common.errors import MigrationError
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "resources" / "migrations"


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_fresh_db_migration_applies_foundation(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    applied = run_migrations(conn, MIGRATIONS_DIR)
    conn.close()

    assert 0 in applied

    conn2 = create_connection(tmp_path / "test.db")
    rows = conn2.execute("SELECT version, name FROM schema_migrations").fetchall()
    conn2.close()
    assert len(rows) >= 1
    assert rows[0]["version"] == 0


def test_idempotency_second_run_applies_nothing(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    first = run_migrations(conn, MIGRATIONS_DIR)
    conn.close()

    conn2 = create_connection(tmp_path / "test.db")
    second = run_migrations(conn2, MIGRATIONS_DIR)
    conn2.close()

    assert 0 in first
    assert second == []


def test_failure_rollback_no_partial_apply(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0000_invalid.sql").write_text(
        "CREATE TABLE partial_table (id INTEGER PRIMARY KEY);\n"
        "THIS IS NOT VALID SQL;",
        encoding="utf-8",
    )

    conn = create_connection(tmp_path / "test.db")
    with pytest.raises(sqlite3.OperationalError):
        run_migrations(conn, migrations_dir)

    assert "partial_table" not in _table_names(conn)
    conn.close()


def test_checksum_mismatch_raises_migration_error(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration_file = migrations_dir / "0000_foundation.sql"
    migration_file.write_text(
        "CREATE TABLE foundation_table (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )

    conn = create_connection(tmp_path / "test.db")
    run_migrations(conn, migrations_dir)
    conn.close()

    migration_file.write_text(
        "CREATE TABLE foundation_table (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE extra_table (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )

    conn2 = create_connection(tmp_path / "test.db")
    with pytest.raises(MigrationError):
        run_migrations(conn2, migrations_dir)
    conn2.close()


def test_provider_configs_has_no_secret_columns(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    run_migrations(conn, MIGRATIONS_DIR)

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(provider_configs)").fetchall()
    }
    conn.close()

    assert {"api_key", "token", "secret"}.isdisjoint(columns)


def test_migration_does_not_rollback_caller_transaction(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0000_foundation.sql").write_text(
        "CREATE TABLE foundation_table (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )

    conn = create_connection(tmp_path / "test.db")
    conn.execute("CREATE TABLE caller_table (id INTEGER PRIMARY KEY)")
    conn.execute("BEGIN")
    conn.execute("INSERT INTO caller_table (id) VALUES (1)")

    with pytest.raises(sqlite3.OperationalError):
        run_migrations(conn, migrations_dir)

    assert conn.execute("SELECT COUNT(*) FROM caller_table").fetchone()[0] == 1
    conn.execute("ROLLBACK")
    conn.close()

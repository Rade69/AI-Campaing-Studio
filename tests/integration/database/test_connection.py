"""Integration tests for SQLite connection factory (P0.16)."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.infrastructure.database.connection import create_connection


def test_connection_select_one_and_reopen(tmp_path: Path) -> None:
    path = tmp_path / "test.db"

    conn = create_connection(path)
    assert conn.execute("SELECT 1").fetchone()[0] == 1
    conn.close()

    conn2 = create_connection(path)
    assert conn2.execute("SELECT 1").fetchone()[0] == 1
    conn2.close()


def test_foreign_keys_enabled(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")

    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_row_factory_is_sqlite_row(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")

    row = conn.execute("SELECT 1 AS value").fetchone()
    assert row["value"] == 1
    conn.close()

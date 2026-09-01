"""Unit tests for SqliteUnitOfWork (P0.18)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork


def _setup_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
    )


def _count_items(connection: sqlite3.Connection) -> int:
    return connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]


def test_commit_persists(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    _setup_table(conn)

    with SqliteUnitOfWork(conn) as uow:
        uow.connection.execute("INSERT INTO items (name) VALUES ('a')")
        uow.commit()

    assert _count_items(conn) == 1
    conn.close()


def test_exception_rolls_back(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    _setup_table(conn)

    with pytest.raises(RuntimeError):
        with SqliteUnitOfWork(conn) as uow:
            uow.connection.execute("INSERT INTO items (name) VALUES ('a')")
            raise RuntimeError("boom")

    assert _count_items(conn) == 0
    conn.close()


def test_no_commit_rolls_back(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    _setup_table(conn)

    with SqliteUnitOfWork(conn) as uow:
        uow.connection.execute("INSERT INTO items (name) VALUES ('a')")

    assert _count_items(conn) == 0
    conn.close()


def test_reuse_after_commit_rolls_back_second_block(tmp_path: Path) -> None:
    conn = create_connection(tmp_path / "test.db")
    _setup_table(conn)
    uow = SqliteUnitOfWork(conn)

    with uow:
        uow.connection.execute("INSERT INTO items (name) VALUES ('a')")
        uow.commit()

    with uow:
        uow.connection.execute("INSERT INTO items (name) VALUES ('b')")

    assert _count_items(conn) == 1
    conn.close()

"""Integration tests for SqliteRevisionRepository (A5, dio 2)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.domain.common.ids import RevisionId
from ai_campaign_studio.domain.content.revisions import Revision, RevisionOrigin
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories.sqlite_revision_repository import (  # noqa: E501
    SqliteRevisionRepository,
)
from ai_campaign_studio.ports.repositories import RevisionRepositoryPort

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def _revision(version: int = 1) -> Revision:
    return Revision(
        id=RevisionId(f"rev-{version}"),
        entity_type="content_piece",
        entity_id="piece-1",
        version=version,
        timestamp=_CREATED_AT,
        origin=RevisionOrigin.AI,
        previous_value="old",
        new_value="new",
        provider="openai",
        model="gpt-x",
        prompt_version="post_generation/v1",
        instruction="Make it warmer",
    )


def test_repository_is_a_revision_repository_port(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteRevisionRepository(connection)
    assert isinstance(repo, RevisionRepositoryPort)
    connection.close()


def test_round_trip_revision(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteRevisionRepository(connection)

    revision = _revision()
    repo.save_revision(revision)

    assert repo.get_revision(RevisionId("rev-1")) == revision
    connection.close()


def test_list_entity_revisions_ordered_by_version(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteRevisionRepository(connection)

    repo.save_revision(_revision(1))
    repo.save_revision(_revision(2))

    result = repo.list_entity_revisions("content_piece", "piece-1")
    assert [r.version for r in result] == [1, 2]
    connection.close()


def test_get_unknown_returns_none(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteRevisionRepository(connection)
    assert repo.get_revision(RevisionId("missing")) is None
    connection.close()

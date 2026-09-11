"""Port method smoke tests for the S2-G7b additions.

Each new repository-port method must work against an EMPTY database: no
crash, and an empty/sentinel result (empty tuple or None). This proves the
SQL read paths are well-formed even before any data exists.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_campaign_studio.domain.common.ids import BrandId
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteFactRepository,
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "resources" / "migrations"


def _empty_db(tmp_path: Path) -> sqlite3.Connection:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


def test_empty_db_new_port_methods_do_not_crash(tmp_path: Path) -> None:
    connection = _empty_db(tmp_path)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)

    assert brand_repo.get_latest_snapshot(BrandId("missing")) is None
    assert fact_repo.list_approved_facts_by_brand(BrandId("missing")) == ()
    assert fact_repo.list_fact_candidates_by_brand(BrandId("missing")) == ()
    assert (
        fact_repo.list_fact_candidates_by_brand(
            BrandId("missing"), statuses=()
        )
        == ()
    )

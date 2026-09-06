"""Unit tests for ``PerformanceImportRow`` persistence (P1.5-G3 dio 2).

Pins the ``save_performance_import_row`` / ``get_performance_import_row`` /
``list_performance_import_rows`` round-trips, JSON serialization (including
BHS Latin diacritics), and the ``distribution_instance_id=None`` contract.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ai_campaign_studio.domain.common.ids import (
    PerformanceImportBatchId,
    PerformanceImportRowId,
)
from ai_campaign_studio.domain.performance.entities import (
    PerformanceImportBatch,
    PerformanceImportRow,
)
from ai_campaign_studio.domain.performance.enums import PerformanceSource
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqlitePerformanceRepository,
)

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[5] / "resources" / "migrations"
)


def _setup_repo(
    tmp_path: Path,
) -> tuple[SqlitePerformanceRepository, sqlite3.Connection]:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    repo = SqlitePerformanceRepository(connection)
    repo.save_performance_import_batch(_batch("b-1"))
    return repo, connection


def _batch(batch_id: str) -> PerformanceImportBatch:
    return PerformanceImportBatch(
        id=PerformanceImportBatchId(batch_id),
        source=PerformanceSource.CSV_IMPORT,
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        row_count=1,
        matched_count=1,
        unmatched_count=0,
        mapping_version="1",
    )


def _row(**overrides: object) -> PerformanceImportRow:
    fields: dict[str, object] = {
        "id": PerformanceImportRowId("row-1"),
        "batch_id": PerformanceImportBatchId("b-1"),
        "row_number": 1,
        "raw_values": {"doseg": "100", "trošak": "12.5", "kampanja": "akcija"},
        "mapped_values": {"reach": "100", "spend": "12.5"},
        "errors": (),
        "distribution_instance_id": None,
    }
    fields.update(overrides)
    return PerformanceImportRow(**fields)  # type: ignore[arg-type]


def test_round_trip_single_row(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    row = _row()
    repo.save_performance_import_row(row)
    assert repo.get_performance_import_row(
        PerformanceImportRowId("row-1")
    ) == row
    connection.close()


def test_get_unknown_row_returns_none(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    assert repo.get_performance_import_row(
        PerformanceImportRowId("missing")
    ) is None
    connection.close()


def test_list_rows_returns_ordered_by_row_number(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    for row_number in (3, 1, 2):
        repo.save_performance_import_row(
            _row(
                id=PerformanceImportRowId(f"row-{row_number}"),
                row_number=row_number,
            )
        )
    rows = repo.list_performance_import_rows(PerformanceImportBatchId("b-1"))
    assert [r.row_number for r in rows] == [1, 2, 3]
    connection.close()


def test_json_round_trip_preserves_bhs_diacritics(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    row = _row(
        raw_values={
            "doseg": "širok",
            "trošak": "12,5",
            "napomena": "čćšđž ČĆŠĐŽ",
        },
        mapped_values={"reach": "širi", "spend": "12.5"},
        errors=("trošak (12,5) nije broj",),
    )
    repo.save_performance_import_row(row)
    loaded = repo.get_performance_import_row(PerformanceImportRowId("row-1"))
    assert loaded is not None
    assert loaded.raw_values == {
        "doseg": "širok",
        "trošak": "12,5",
        "napomena": "čćšđž ČĆŠĐŽ",
    }
    assert loaded.mapped_values == {"reach": "širi", "spend": "12.5"}
    assert loaded.errors == ("trošak (12,5) nije broj",)
    connection.close()


def test_distribution_instance_id_none_round_trip(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    row = _row(distribution_instance_id=None)
    repo.save_performance_import_row(row)
    loaded = repo.get_performance_import_row(PerformanceImportRowId("row-1"))
    assert loaded is not None
    assert loaded.distribution_instance_id is None
    connection.close()


def test_list_is_scoped_to_batch(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    repo.save_performance_import_batch(_batch("b-2"))
    repo.save_performance_import_row(_row(id=PerformanceImportRowId("row-a")))
    repo.save_performance_import_row(
        _row(
            id=PerformanceImportRowId("row-b"),
            batch_id=PerformanceImportBatchId("b-2"),
        )
    )
    assert len(
        repo.list_performance_import_rows(PerformanceImportBatchId("b-1"))
    ) == 1
    assert len(
        repo.list_performance_import_rows(PerformanceImportBatchId("b-2"))
    ) == 1
    connection.close()

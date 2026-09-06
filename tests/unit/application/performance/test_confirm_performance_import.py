"""Unit tests for ConfirmPerformanceImport (P1.5-G3 dio 2)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_campaign_studio.application.performance.confirm_performance_import import (
    ConfirmPerformanceImport,
)
from ai_campaign_studio.domain.common.ids import PerformanceImportBatchId
from ai_campaign_studio.domain.performance.enums import PerformanceSource
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqlitePerformanceRepository,
)
from ai_campaign_studio.ports.repositories import PerformanceRepositoryPort

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "resources" / "migrations"
)


def _setup_repo(
    tmp_path: Path,
) -> tuple[PerformanceRepositoryPort, sqlite3.Connection]:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return SqlitePerformanceRepository(connection), connection


def _write_csv(tmp_path: Path, content: str, name: str = "perf.csv") -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_happy_path_persists_batch_and_all_rows(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach,spend\n"
        "2026-01-01,2026-01-31,100,10.5\n"
        "2026-02-01,2026-02-28,200,20.0\n",
    )

    batch = ConfirmPerformanceImport(repo).execute(path)

    # Round-trip proof via the repo, not just the return value.
    loaded_batch = repo.get_performance_import_batch(batch.id)
    assert loaded_batch == batch
    assert loaded_batch is not None
    assert loaded_batch.source is PerformanceSource.CSV_IMPORT
    assert loaded_batch.row_count == 2
    assert loaded_batch.matched_count == 2
    assert loaded_batch.unmatched_count == 0
    assert loaded_batch.mapping_version == "1"
    assert loaded_batch.source_file_name == "perf.csv"

    rows = repo.list_performance_import_rows(batch.id)
    assert len(rows) == 2
    assert all(r.distribution_instance_id is None for r in rows)
    assert [r.row_number for r in rows] == [1, 2]
    connection.close()


def test_column_overrides_fixes_ambiguous_column(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    # "cost" and "trošak" BOTH alias spend -> ambiguous without an override.
    path = _write_csv(
        tmp_path,
        "cost,trošak,datum_pocetka,datum_kraja,doseg\n"
        "10.5,20.0,2026-01-01,2026-01-31,100\n",
    )

    batch = ConfirmPerformanceImport(repo).execute(
        path, column_overrides={"spend": "cost"}
    )

    rows = repo.list_performance_import_rows(batch.id)
    assert len(rows) == 1
    assert rows[0].mapped_values["spend"] == "10.5"
    # The non-chosen header is NOT lost — it stays in raw_values.
    assert rows[0].raw_values["trošak"] == "20.0"
    assert rows[0].errors == ()
    connection.close()


def test_ambiguous_without_override_leaves_field_unmapped(
    tmp_path: Path,
) -> None:
    repo, connection = _setup_repo(tmp_path)
    path = _write_csv(
        tmp_path,
        "cost,trošak,datum_pocetka,datum_kraja,doseg\n"
        "10.5,20.0,2026-01-01,2026-01-31,100\n",
    )

    batch = ConfirmPerformanceImport(repo).execute(path)

    rows = repo.list_performance_import_rows(batch.id)
    assert len(rows) == 1
    assert "spend" not in rows[0].mapped_values
    connection.close()


def test_invalid_rows_are_still_persisted_nothing_lost(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach\n"
        "2026-01-01,2026-01-31,100\n"
        "garbage,2026-01-31,abc\n"
        "2026-02-01,2026-02-28,200\n",
    )

    batch = ConfirmPerformanceImport(repo).execute(path)

    # 3 input rows -> 3 persisted rows, always.
    assert batch.row_count == 3
    assert batch.matched_count == 2
    assert batch.unmatched_count == 1

    rows = repo.list_performance_import_rows(batch.id)
    assert len(rows) == 3
    assert rows[0].errors == ()
    assert rows[1].errors != ()
    assert rows[2].errors == ()
    # Invalid row still carries its values and errors, never dropped.
    assert rows[1].raw_values["period_start"] == "garbage"
    assert "period_start (garbage) is not a valid date" in rows[1].errors
    connection.close()


def test_platform_code_is_recorded(tmp_path: Path) -> None:
    repo, connection = _setup_repo(tmp_path)
    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach\n"
        "2026-01-01,2026-01-31,100\n",
    )

    batch = ConfirmPerformanceImport(repo).execute(
        path, platform_code="INSTAGRAM"
    )

    loaded = repo.get_performance_import_batch(
        PerformanceImportBatchId(batch.id)
    )
    assert loaded is not None
    assert loaded.platform_code == "INSTAGRAM"
    connection.close()

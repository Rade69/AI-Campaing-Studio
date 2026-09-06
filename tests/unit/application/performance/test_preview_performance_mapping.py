"""Unit tests for PreviewPerformanceMapping (P1.5-G3 dio 2)."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.application.performance.preview_performance_mapping import (
    PreviewPerformanceMapping,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "resources" / "migrations"
)


def _write_csv(tmp_path: Path, content: str) -> str:
    path = tmp_path / "perf.csv"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_ambiguous_column_is_visible_in_summary(tmp_path: Path) -> None:
    # Both "cost" and "trošak" alias the SAME canonical field (spend) in the
    # bundled rules, so the mapping must be reported as ambiguous.
    path = _write_csv(
        tmp_path,
        "cost,trošak,period_start,period_end,reach\n"
        "10.5,20.0,2026-01-01,2026-01-31,100\n",
    )
    result = PreviewPerformanceMapping().execute(path)

    spend = next(c for c in result.columns if c.canonical_field == "spend")
    assert spend.status == "ambiguous"
    assert spend.header is None
    assert set(spend.candidates) == {"cost", "trošak"}


def test_invalid_rows_are_visible_with_errors(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach\n"
        "2026-01-01,2026-01-31,100\n"
        "garbage,2026-01-31,abc\n",
    )
    result = PreviewPerformanceMapping().execute(path)

    assert result.total_rows == 2
    assert result.valid_rows == 1
    assert result.invalid_rows == 1
    assert len(result.invalid_samples) == 1
    sample = result.invalid_samples[0]
    assert sample.row_number == 2
    assert "period_start (garbage) is not a valid date" in sample.errors
    assert "reach (abc) is not a number" in sample.errors


def test_preview_persists_nothing(tmp_path: Path) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach\n"
        "2026-01-01,2026-01-31,100\n",
    )
    PreviewPerformanceMapping().execute(path)

    batches = connection.execute(
        "SELECT COUNT(*) FROM performance_import_batches"
    ).fetchone()[0]
    rows = connection.execute(
        "SELECT COUNT(*) FROM performance_import_rows"
    ).fetchone()[0]
    assert batches == 0
    assert rows == 0
    connection.close()

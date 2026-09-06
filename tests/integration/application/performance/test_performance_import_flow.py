"""Integration test: full CSV import chain (P1.5-G3 dio 2).

Proves the complete ImportPerformanceCsv -> PreviewPerformanceMapping ->
ConfirmPerformanceImport flow over a REAL temp CSV with mixed valid/invalid
rows and BHS + EN headers together (not separately), including the
"nothing is lost" guarantee (input rows == persisted rows).
"""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.application.performance.confirm_performance_import import (
    ConfirmPerformanceImport,
)
from ai_campaign_studio.application.performance.import_performance_csv import (
    ImportPerformanceCsv,
)
from ai_campaign_studio.application.performance.preview_performance_mapping import (
    PreviewPerformanceMapping,
)
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqlitePerformanceRepository,
)

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "resources" / "migrations"
)


def _write_csv(tmp_path: Path) -> str:
    path = tmp_path / "perf.csv"
    # Mixed BHS (datum_pocetka/datum_kraja/doseg) and EN (spend) headers.
    # Row 1 invalid (doseg not a number), row 2 valid.
    path.write_text(
        "datum_pocetka,datum_kraja,doseg,spend\n"
        "2026-01-01,2026-01-31,širok,10.5\n"
        "2026-02-01,2026-02-28,200,20.0\n",
        encoding="utf-8",
    )
    return str(path)


def test_full_chain_with_mixed_bhs_en_and_invalid_rows(
    tmp_path: Path,
) -> None:
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    repo = SqlitePerformanceRepository(connection)

    file_path = _write_csv(tmp_path)

    # 1. Import (read-only).
    matches, parsed_rows = ImportPerformanceCsv().execute(file_path)
    by_field = {m.canonical_field: m for m in matches}
    assert by_field["period_start"].header == "datum_pocetka"
    assert by_field["reach"].header == "doseg"
    assert by_field["spend"].header == "spend"
    assert len(parsed_rows) == 2

    # 2. Preview (persists nothing, shows the invalid row with errors).
    preview = PreviewPerformanceMapping().execute(file_path)
    assert preview.total_rows == 2
    assert preview.valid_rows == 1
    assert preview.invalid_rows == 1
    assert len(preview.invalid_samples) == 1
    assert preview.invalid_samples[0].row_number == 1
    assert "reach (širok) is not a number" in preview.invalid_samples[0].errors

    # 3. Confirm (persists batch + every row, including the invalid one).
    batch = ConfirmPerformanceImport(repo).execute(
        file_path, platform_code="FACEBOOK"
    )

    loaded_batch = repo.get_performance_import_batch(batch.id)
    assert loaded_batch is not None
    assert loaded_batch.row_count == 2
    assert loaded_batch.matched_count == 1
    assert loaded_batch.unmatched_count == 1
    assert loaded_batch.platform_code == "FACEBOOK"

    rows = repo.list_performance_import_rows(batch.id)
    # "Nothing is lost": 2 input rows == 2 persisted rows.
    assert len(rows) == 2
    assert all(r.distribution_instance_id is None for r in rows)

    # BHS diacritics survive the full chain into the persisted row.
    assert rows[0].raw_values["doseg"] == "širok"
    assert rows[0].errors != ()
    assert rows[1].errors == ()
    assert rows[1].mapped_values["reach"] == "200"

    connection.close()

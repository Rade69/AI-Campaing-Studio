"""Unit tests for ImportPerformanceCsv (P1.5-G3 dio 2)."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.application.performance.import_performance_csv import (
    ImportPerformanceCsv,
)


def _write_csv(tmp_path: Path, content: str, name: str = "perf.csv") -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_reads_real_csv_and_maps_and_parses(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach,spend\n"
        "2026-01-01,2026-01-31,100,10.5\n"
        "2026-02-01,2026-02-28,200,20.0\n",
    )
    matches, rows = ImportPerformanceCsv().execute(path)

    by_field = {m.canonical_field: m for m in matches}
    assert by_field["period_start"].status == "matched"
    assert by_field["reach"].header == "reach"
    assert by_field["spend"].header == "spend"

    assert len(rows) == 2
    assert rows[0].errors == ()
    assert rows[0].mapped_values["reach"] == "100"
    assert rows[0].mapped_values["spend"] == "10.5"
    assert rows[1].mapped_values["reach"] == "200"
    assert rows[1].row_number == 2


def test_rules_none_uses_bundled_default_with_bhs_headers(
    tmp_path: Path,
) -> None:
    path = _write_csv(
        tmp_path,
        "datum_pocetka,datum_kraja,doseg,trošak\n"
        "2026-01-01,2026-01-31,100,12.5\n",
    )
    matches, rows = ImportPerformanceCsv().execute(path)

    by_field = {m.canonical_field: m for m in matches}
    assert by_field["period_start"].header == "datum_pocetka"
    assert by_field["reach"].header == "doseg"
    assert by_field["spend"].header == "trošak"
    assert rows[0].errors == ()
    assert rows[0].mapped_values["period_start"] == "2026-01-01"
    assert rows[0].mapped_values["reach"] == "100"


def test_missing_cells_become_empty_strings_not_none(tmp_path: Path) -> None:
    # One row shorter than the header: DictReader's restval defaults to None,
    # which must never leak into ParsedRow (values are typed str).
    path = _write_csv(
        tmp_path,
        "period_start,period_end,reach\n"
        "2026-01-01,2026-01-31\n",
    )
    _, rows = ImportPerformanceCsv().execute(path)
    assert rows[0].raw_values.get("reach") == ""


def test_empty_file_yields_empty_result(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, "")
    matches, rows = ImportPerformanceCsv().execute(path)
    assert rows == ()
    # No headers -> every canonical field is unmatched.
    assert all(m.status == "unmatched" for m in matches)

"""ConfirmPerformanceImport use-case (P1.5-G3 dio 2, Faza 1 v1.5 §18).

Owns the confirmed persistence step of the CSV import chain: re-parses the
file (through ``ImportPerformanceCsv`` — this module never opens a file),
applies optional ``column_overrides`` (canonical field -> user-chosen header)
BEFORE row parsing, then persists ONE ``PerformanceImportBatch`` plus ONE
``PerformanceImportRow`` per input row. Invalid rows are STILL persisted
(nothing is ever dropped). ``distribution_instance_id`` is ``None`` for every
row — the separate matching gate (P1.5-G4) fills it later.

Documented temporary semantics (P1.5-G3 dio 2, reconciled by G4): the batch
``matched_count``/``unmatched_count`` fields were NAMED for future
content-matching counts, but matching does not exist yet, so here
``matched_count`` == number of VALID rows (no ``errors``) and
``unmatched_count`` == number of INVALID rows.
"""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.application.performance.column_mapping import (
    ColumnMatch,
    load_column_aliases,
)
from ai_campaign_studio.application.performance.import_performance_csv import (
    ImportPerformanceCsv,
)
from ai_campaign_studio.application.performance.row_parsing import (
    parse_rows,
)
from ai_campaign_studio.domain.common.ids import (
    PerformanceImportBatchId,
    PerformanceImportRowId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.performance.entities import (
    PerformanceImportBatch,
    PerformanceImportRow,
)
from ai_campaign_studio.domain.performance.enums import PerformanceSource
from ai_campaign_studio.ports.repositories import PerformanceRepositoryPort


class ConfirmPerformanceImport:
    """Parse (with overrides) and persist one CSV import as batch + rows."""

    def __init__(
        self,
        performance_repo: PerformanceRepositoryPort,
        importer: ImportPerformanceCsv | None = None,
    ) -> None:
        self._repo = performance_repo
        self._importer = importer if importer is not None else ImportPerformanceCsv()

    def execute(
        self,
        file_path: str,
        column_overrides: dict[str, str] | None = None,
        platform_code: str | None = None,
    ) -> PerformanceImportBatch:
        """Persist the import and return the created batch.

        ``column_overrides`` maps a canonical field name to the CSV header
        the user manually chose for it (fixing an ``ambiguous``/``unmatched``
        column). The override is applied to the column mapping BEFORE rows are
        parsed, so the corrected header participates in validation.
        """
        rules = load_column_aliases()
        matches, parsed_rows = self._importer.execute(file_path, rules)

        if column_overrides:
            matches = _apply_overrides(matches, column_overrides)
            # Re-parse from the ORIGINAL raw values (already in memory via
            # ParsedRow.raw_values) with the corrected mapping — no second
            # disk read, and no row can be dropped.
            raw_rows = tuple(row.raw_values for row in parsed_rows)
            parsed_rows = parse_rows(raw_rows, matches)

        valid_count = sum(1 for row in parsed_rows if not row.errors)
        invalid_count = len(parsed_rows) - valid_count

        batch = PerformanceImportBatch(
            id=PerformanceImportBatchId(new_id()),
            source=PerformanceSource.CSV_IMPORT,
            imported_at=utc_now(),
            row_count=len(parsed_rows),
            matched_count=valid_count,
            unmatched_count=invalid_count,
            mapping_version=rules.version,
            source_file_name=Path(file_path).name,
            platform_code=platform_code,
        )
        self._repo.save_performance_import_batch(batch)

        for row in parsed_rows:
            self._repo.save_performance_import_row(
                PerformanceImportRow(
                    id=PerformanceImportRowId(new_id()),
                    batch_id=batch.id,
                    row_number=row.row_number,
                    raw_values=row.raw_values,
                    mapped_values=row.mapped_values,
                    errors=row.errors,
                    distribution_instance_id=None,
                )
            )
        return batch


def _apply_overrides(
    matches: tuple[ColumnMatch, ...],
    column_overrides: dict[str, str],
) -> tuple[ColumnMatch, ...]:
    """Rewrite matches so each overridden canonical field maps to the given
    header as a definite ``matched`` match. Fields not in the override dict
    are left untouched; an override for an unknown field is a no-op."""
    return tuple(
        ColumnMatch(
            canonical_field=match.canonical_field,
            header=column_overrides[match.canonical_field],
            status="matched",
            candidates=(column_overrides[match.canonical_field],),
        )
        if match.canonical_field in column_overrides
        else match
        for match in matches
    )

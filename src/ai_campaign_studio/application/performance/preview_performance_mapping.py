"""PreviewPerformanceMapping use-case (P1.5-G3 dio 2, Faza 1 v1.5 §18).

Owns the pre-confirmation summary a user sees BEFORE any row is persisted:
per-field column-mapping status, valid/invalid row counts, and a sample of
invalid rows with their ``errors``. Calls ``ImportPerformanceCsv`` (the only
disk reader) and persists NOTHING. Does NOT match rows to
``DistributionInstance`` (that is P1.5-G4).
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_campaign_studio.application.performance.column_mapping import (
    ColumnAliasRules,
)
from ai_campaign_studio.application.performance.import_performance_csv import (
    ImportPerformanceCsv,
)

# How many invalid rows to include in the preview sample. Kept small so the
# summary stays readable; the full invalid set is still persisted later by
# ConfirmPerformanceImport (nothing is ever dropped).
_DEFAULT_SAMPLE_LIMIT = 5


@dataclass(frozen=True)
class ColumnMappingSummary:
    """Mapping status of ONE canonical field for the preview."""

    canonical_field: str
    header: str | None
    status: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class InvalidRowSample:
    """One invalid row with its readable errors, for the preview."""

    row_number: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class PreviewResult:
    """Full preview summary (columns + counts + invalid samples)."""

    columns: tuple[ColumnMappingSummary, ...]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    invalid_samples: tuple[InvalidRowSample, ...]


class PreviewPerformanceMapping:
    """Build the pre-confirmation mapping/validation summary."""

    def __init__(self, importer: ImportPerformanceCsv | None = None) -> None:
        self._importer = importer if importer is not None else ImportPerformanceCsv()

    def execute(
        self,
        file_path: str,
        rules: ColumnAliasRules | None = None,
        sample_limit: int = _DEFAULT_SAMPLE_LIMIT,
    ) -> PreviewResult:
        """Return the preview for ``file_path`` WITHOUT persisting anything."""
        matches, rows = self._importer.execute(file_path, rules)
        invalid_rows = [row for row in rows if row.errors]
        return PreviewResult(
            columns=tuple(
                ColumnMappingSummary(
                    canonical_field=match.canonical_field,
                    header=match.header,
                    status=match.status,
                    candidates=match.candidates,
                )
                for match in matches
            ),
            total_rows=len(rows),
            valid_rows=len(rows) - len(invalid_rows),
            invalid_rows=len(invalid_rows),
            invalid_samples=tuple(
                InvalidRowSample(row_number=row.row_number, errors=row.errors)
                for row in invalid_rows[:sample_limit]
            ),
        )

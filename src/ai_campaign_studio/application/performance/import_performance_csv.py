"""ImportPerformanceCsv use-case (P1.5-G3 dio 2, Faza 1 v1.5 §18).

Owns the single disk-read step of the CSV import chain: opens one CSV file
(via stdlib ``csv.DictReader``), maps its headers with the dio-1 engine and
parses/validates every row. Returns ``(column_matches, parsed_rows)`` and
persists NOTHING. This is the ONLY module that reads a CSV file from disk —
``PreviewPerformanceMapping`` and ``ConfirmPerformanceImport`` both go
through this use-case instead of opening files themselves. Does NOT match
rows to ``DistributionInstance`` (that is P1.5-G4).
"""

from __future__ import annotations

import csv

from ai_campaign_studio.application.performance.column_mapping import (
    ColumnAliasRules,
    ColumnMatch,
    load_column_aliases,
    map_columns,
)
from ai_campaign_studio.application.performance.row_parsing import (
    ParsedRow,
    parse_rows,
)


class ImportPerformanceCsv:
    """Read + map + parse one CSV file. Pure orchestration, no persistence."""

    def execute(
        self,
        file_path: str,
        rules: ColumnAliasRules | None = None,
    ) -> tuple[tuple[ColumnMatch, ...], tuple[ParsedRow, ...]]:
        """Return the column mapping and the parsed rows for ``file_path``.

        ``rules=None`` loads the bundled default alias set
        (``load_column_aliases()``). The CSV is read with ``encoding=utf-8-sig``
        so a UTF-8 BOM (common from Excel) is stripped, and ``newline=""`` so
        Python handles line endings portably. Missing cells become ``""``
        (never ``None``), keeping every value a ``str``.
        """
        resolved = rules if rules is not None else load_column_aliases()
        with open(file_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            headers = tuple(reader.fieldnames or ())
            raw_rows = tuple(
                {
                    key: ("" if value is None else value)
                    for key, value in row.items()
                }
                for row in reader
            )
        matches = map_columns(headers, resolved)
        parsed_rows = parse_rows(raw_rows, matches)
        return matches, parsed_rows

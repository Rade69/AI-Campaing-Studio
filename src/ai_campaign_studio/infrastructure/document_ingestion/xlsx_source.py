"""XLSX document source parser (S2-G9).

Owns reading a local .xlsx into per-cell ``SourceChunk``s
(``locator_type="xlsx_sheet_cell"``, ``locator="s<SHEET>!r<ROW>c<COL>"``).
Read-only mode (``read_only=True, data_only=True``) keeps large workbooks
streaming; empty cells are skipped; numbers/formulas become ``str(cell.value)``
(formulas are taken as their text, never evaluated).
"""

from __future__ import annotations

import logging

from ai_campaign_studio.domain.common.ids import (
    IngestionRunId,
    SourceChunkId,
    SourceSnapshotId,
)
from ai_campaign_studio.domain.ingestion.entities import SourceChunk
from ai_campaign_studio.infrastructure.document_ingestion.errors import (
    DocumentParseError,
)

logger = logging.getLogger(__name__)


class XlsxSource:
    """Extract text chunks from an .xlsx via openpyxl (one per non-empty cell)."""

    def extract(
        self,
        path: str,
        run_id: IngestionRunId,
        snapshot_id: SourceSnapshotId | None = None,
    ) -> tuple[SourceChunk, ...]:
        if snapshot_id is None:
            raise DocumentParseError(
                "snapshot_id is required — the S2-G6 pipeline must persist the "
                "SourceSnapshot before extracting chunks."
            )
        try:
            from openpyxl import (  # type: ignore[import-not-found,import-untyped]
                load_workbook,
            )
        except ImportError as exc:
            raise DocumentParseError(
                "openpyxl is not installed; install the 'documents' extra."
            ) from exc

        try:
            workbook = load_workbook(  # type: ignore[call-arg]
                path, read_only=True, data_only=True
            )
        except Exception as exc:
            raise DocumentParseError(
                f"Cannot open XLSX (type={type(exc).__name__})"
            ) from exc

        chunks: list[SourceChunk] = []
        try:
            for sheet_name in workbook.sheetnames:  # type: ignore[union-attr]
                worksheet = workbook[sheet_name]  # type: ignore[union-attr]
                for row_index, row in enumerate(
                    worksheet.iter_rows(), start=1  # type: ignore[union-attr]
                ):
                    for column_index, cell in enumerate(row, start=1):
                        if cell.value is None:  # type: ignore[union-attr]
                            continue
                        text = str(cell.value).strip()  # type: ignore[union-attr]
                        if not text:
                            continue
                        locator = f"s{sheet_name}!r{row_index}c{column_index}"
                        chunks.append(
                            SourceChunk(
                                id=SourceChunkId(f"{run_id}:{snapshot_id}:{locator}"),
                                snapshot_id=snapshot_id,
                                locator_type="xlsx_sheet_cell",
                                locator=locator,
                                text=text,
                            )
                        )
            return tuple(chunks)
        finally:
            workbook.close()  # type: ignore[union-attr]


__all__ = ["XlsxSource"]

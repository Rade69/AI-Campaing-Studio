"""Unit tests for XlsxSource (S2-G9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.domain.common.ids import (
    IngestionRunId,
    SourceSnapshotId,
)
from ai_campaign_studio.infrastructure.document_ingestion import (
    DocumentParseError,
    XlsxSource,
)

openpyxl = pytest.importorskip("openpyxl")  # 'documents' extra


def _make_xlsx(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["A1"] = "Header"
    ws["A2"] = 42
    ws["A3"] = None  # empty cell -> skipped
    ws["B2"] = "value"
    wb.save(str(path))


def test_extract_valid_xlsx_per_non_empty_cell(tmp_path: Path) -> None:
    path = tmp_path / "doc.xlsx"
    _make_xlsx(path)

    chunks = XlsxSource().extract(
        str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )

    # A1="Header", A2=42 (numeric -> str), B2="value"; A3 empty -> skipped.
    assert len(chunks) == 3
    assert all(c.snapshot_id == SourceSnapshotId("snap-1") for c in chunks)
    assert all(c.locator_type == "xlsx_sheet_cell" for c in chunks)
    locators = [c.locator for c in chunks]
    assert "sSheet1!r1c1" in locators
    assert "sSheet1!r2c1" in locators
    assert "sSheet1!r2c2" in locators
    texts = {c.locator: c.text for c in chunks}
    assert texts["sSheet1!r1c1"] == "Header"
    assert texts["sSheet1!r2c1"] == "42"  # numeric converted to str
    assert texts["sSheet1!r2c2"] == "value"


def test_extract_corrupted_xlsx_raises_document_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.xlsx"
    path.write_bytes(b"not an xlsx zip")

    with pytest.raises(DocumentParseError):
        XlsxSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )


def test_extract_empty_file_raises_document_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.xlsx"
    path.write_bytes(b"")

    with pytest.raises(DocumentParseError):
        XlsxSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )


def test_extract_missing_snapshot_id_raises(tmp_path: Path) -> None:
    path = tmp_path / "doc.xlsx"
    _make_xlsx(path)

    with pytest.raises(DocumentParseError):
        XlsxSource().extract(str(path), IngestionRunId("run-1"))

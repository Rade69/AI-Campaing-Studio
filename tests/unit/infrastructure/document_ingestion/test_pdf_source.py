"""Unit tests for PdfSource (S2-G9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.domain.common.ids import (
    IngestionRunId,
    SourceSnapshotId,
)
from ai_campaign_studio.infrastructure.document_ingestion import (
    DocumentParseError,
    PdfSource,
)

fitz = pytest.importorskip("fitz")  # PyMuPDF — 'documents' extra


def _make_pdf(path: Path, text_pages: int, blank_pages: int) -> None:
    doc = fitz.open()
    for i in range(text_pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} text content")
    for _ in range(blank_pages):
        doc.new_page()  # no text -> scanned-like page
    doc.save(str(path))
    doc.close()


def test_extract_valid_pdf_two_text_pages_one_blank(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    _make_pdf(path, text_pages=2, blank_pages=1)

    chunks = PdfSource().extract(
        str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )

    assert len(chunks) == 2
    assert all(c.snapshot_id == SourceSnapshotId("snap-1") for c in chunks)
    assert all(c.locator_type == "pdf_page" for c in chunks)
    assert [c.locator for c in chunks] == ["p1", "p2"]
    assert chunks[0].text == "Page 1 text content"
    assert chunks[1].text == "Page 2 text content"
    # Deterministic chunk id from run_id + locator.
    assert chunks[0].id == "run-1:p1"


def test_extract_scanned_pdf_returns_empty_tuple(tmp_path: Path) -> None:
    """D23: an image-only/blank PDF (no extractable text) must NOT raise —
    it returns an empty tuple."""
    path = tmp_path / "scanned.pdf"
    _make_pdf(path, text_pages=0, blank_pages=2)

    chunks = PdfSource().extract(
        str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )
    assert chunks == ()


def test_extract_corrupted_pdf_raises_document_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"not a real pdf header")

    with pytest.raises(DocumentParseError):
        PdfSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )


def test_extract_empty_file_raises_document_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")

    with pytest.raises(DocumentParseError):
        PdfSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )


def test_extract_missing_snapshot_id_raises(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    _make_pdf(path, text_pages=1, blank_pages=0)

    with pytest.raises(DocumentParseError):
        PdfSource().extract(str(path), IngestionRunId("run-1"))

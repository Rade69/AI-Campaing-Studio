"""Unit tests for DocxSource (S2-G9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.domain.common.ids import (
    IngestionRunId,
    SourceSnapshotId,
)
from ai_campaign_studio.infrastructure.document_ingestion import (
    DocumentParseError,
    DocxSource,
)

pytest.importorskip("docx")  # python-docx — 'documents' extra
from docx import Document  # noqa: E402


def _make_docx(path: Path, texts: list[str]) -> None:
    document = Document()
    for text in texts:
        document.add_paragraph(text)
    document.save(str(path))


def test_extract_valid_docx_per_paragraph(tmp_path: Path) -> None:
    path = tmp_path / "doc.docx"
    _make_docx(path, ["First paragraph", "", "Second paragraph"])

    chunks = DocxSource().extract(
        str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )

    # Empty paragraph is skipped; two non-empty paragraphs remain.
    assert len(chunks) == 2
    assert all(c.snapshot_id == SourceSnapshotId("snap-1") for c in chunks)
    assert all(c.locator_type == "docx_para" for c in chunks)
    assert [c.locator for c in chunks] == ["p1", "p3"]
    assert [c.text for c in chunks] == ["First paragraph", "Second paragraph"]


def test_extract_corrupted_docx_raises_document_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.docx"
    path.write_bytes(b"not a docx")

    with pytest.raises(DocumentParseError):
        DocxSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )


def test_extract_empty_file_raises_document_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.docx"
    path.write_bytes(b"")

    with pytest.raises(DocumentParseError):
        DocxSource().extract(
            str(path), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
        )


def test_extract_missing_snapshot_id_raises(tmp_path: Path) -> None:
    path = tmp_path / "doc.docx"
    _make_docx(path, ["text"])

    with pytest.raises(DocumentParseError):
        DocxSource().extract(str(path), IngestionRunId("run-1"))

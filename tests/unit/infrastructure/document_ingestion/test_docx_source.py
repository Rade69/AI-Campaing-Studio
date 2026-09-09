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


def test_extract_two_documents_in_same_run_produce_distinct_ids(
    tmp_path: Path,
) -> None:
    """BF-1 (Codex): distinct chunk ids across two snapshots in one run."""
    path_a = tmp_path / "a.docx"
    path_b = tmp_path / "b.docx"
    _make_docx(path_a, ["document one"])
    _make_docx(path_b, ["document two"])

    chunks_a = DocxSource().extract(
        str(path_a), IngestionRunId("run-1"), SourceSnapshotId("snap-1")
    )
    chunks_b = DocxSource().extract(
        str(path_b), IngestionRunId("run-1"), SourceSnapshotId("snap-2")
    )

    assert chunks_a[0].locator == chunks_b[0].locator == "p1"
    assert chunks_a[0].id == "run-1:snap-1:p1"
    assert chunks_b[0].id == "run-1:snap-2:p1"
    assert chunks_a[0].id != chunks_b[0].id

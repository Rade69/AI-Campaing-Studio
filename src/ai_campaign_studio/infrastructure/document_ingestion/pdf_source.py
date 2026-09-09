"""PDF document source parser (S2-G9).

Owns reading a local PDF into per-page ``SourceChunk``s (one chunk per page,
``locator_type="pdf_page"``, ``locator="p<N>"``). Does NOT own OCR (D23): an
image-only page has no extractable text and is skipped; an image-only PDF
yields an EMPTY tuple, which the caller (S2-G6) maps to
``last_error="scanned_pdf_no_ocr"`` on the ``CrawlTarget``.
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


class PdfSource:
    """Extract text chunks from a PDF via PyMuPDF (one chunk per page)."""

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
            import fitz  # type: ignore[import-not-found,import-untyped]
        except ImportError as exc:
            raise DocumentParseError(
                "PyMuPDF is not installed; install the 'documents' extra."
            ) from exc

        try:
            doc = fitz.open(path)  # type: ignore[union-attr]
        except Exception as exc:
            raise DocumentParseError(
                f"Cannot open PDF (type={type(exc).__name__})"
            ) from exc

        chunks: list[SourceChunk] = []
        try:
            for page_index in range(doc.page_count):  # type: ignore[union-attr]
                page = doc.load_page(page_index)  # type: ignore[union-attr]
                text = page.get_text().strip()  # type: ignore[union-attr]
                if not text:
                    # Likely a scanned/image-only page (D23: no OCR).
                    logger.warning(
                        "pdf_page_has_no_text page=%d", page_index + 1
                    )
                    continue
                locator = f"p{page_index + 1}"
                chunks.append(
                    SourceChunk(
                        id=SourceChunkId(f"{run_id}:{locator}"),
                        snapshot_id=snapshot_id,
                        locator_type="pdf_page",
                        locator=locator,
                        text=text,
                    )
                )
            return tuple(chunks)
        finally:
            doc.close()  # type: ignore[union-attr]


__all__ = ["PdfSource"]

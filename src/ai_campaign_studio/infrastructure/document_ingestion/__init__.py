"""Document source parsers (S2-G9).

Owns the PDF/DOCX/XLSX document source parsers that reduce local documents to
the SAME ``SourceChunk`` model as web ingestion (one provenance chain, §10
S2-G9). Each parser reads a local file path into per-page/per-paragraph/
per-cell chunks; it does NOT extract ``FactCandidate``s (that is the G4/G5
extractor's job) and does NOT persist anything (the G6 pipeline registers the
chunks through ``IngestionRepositoryPort``). No OCR (D23) — an image-only PDF
yields an empty chunk tuple.
"""

from ai_campaign_studio.infrastructure.document_ingestion.docx_source import (
    DocxSource,
)
from ai_campaign_studio.infrastructure.document_ingestion.errors import (
    DocumentParseError,
)
from ai_campaign_studio.infrastructure.document_ingestion.pdf_source import (
    PdfSource,
)
from ai_campaign_studio.infrastructure.document_ingestion.xlsx_source import (
    XlsxSource,
)

__all__ = [
    "DocxSource",
    "DocumentParseError",
    "PdfSource",
    "XlsxSource",
]

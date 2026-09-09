"""Unit tests for the document ingestion parsers (S2-G9)."""

from ai_campaign_studio.infrastructure.document_ingestion import (
    DocumentParseError,
    DocxSource,
    PdfSource,
    XlsxSource,
)


def test_document_parse_error_is_a_value_error() -> None:
    assert issubclass(DocumentParseError, ValueError)


def test_all_three_sources_are_exported() -> None:
    assert PdfSource is not None
    assert DocxSource is not None
    assert XlsxSource is not None

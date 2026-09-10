"""Unit tests for the S2-G6 ingestion use-case boundary and wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.application.ingestion import IngestBrandSources
from ai_campaign_studio.domain.common.ids import BrandId

_PACKAGE_DIR = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "ai_campaign_studio"
    / "application"
    / "ingestion"
)


def _use_case(**overrides: object) -> IngestBrandSources:
    kwargs: dict[str, object] = {
        "repository": None,
        "fetcher": None,
        "classifier": None,
        "discovery": None,
        "budget": None,
        "normalizer": lambda url: url,
        "visual_identity_extractor": None,
        "content_extractor": lambda html, base: "",
        "boilerplate_filter": lambda text: text,
        "deduplicator": lambda chunks: chunks,
        "document_extractors": {},
    }
    kwargs.update(overrides)
    return IngestBrandSources(**kwargs)  # type: ignore[arg-type]


def test_ingestion_package_does_not_import_infrastructure() -> None:
    """Application boundary: no ``infrastructure`` import anywhere here."""
    for path in _PACKAGE_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "ai_campaign_studio.infrastructure" not in source, path.name


def test_build_facts_is_deterministic_no_llm() -> None:
    """No AI provider surface is used by the deterministic candidate builder."""
    source = (_PACKAGE_DIR / "ingest_brand_sources.py").read_text(encoding="utf-8")
    for forbidden in ("AIRequest", "TextGenerationPort", "ai_provider", "openai"):
        assert forbidden not in source


def test_submit_without_job_manager_raises() -> None:
    use_case = _use_case()
    with pytest.raises(RuntimeError):
        use_case.submit(BrandId("brand-1"), ("https://example.com/",))

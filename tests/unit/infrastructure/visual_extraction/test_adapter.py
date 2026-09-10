"""Unit tests for the S2-G5 visual identity adapter (port wiring)."""

from __future__ import annotations

from ai_campaign_studio.domain.brand.value_objects import VisualIdentity
from ai_campaign_studio.infrastructure.visual_extraction import VisualIdentityAdapter
from ai_campaign_studio.ports.web_ingestion import VisualIdentityExtractorPort


def test_adapter_is_runtime_checkable_port() -> None:
    adapter = VisualIdentityAdapter()
    assert isinstance(adapter, VisualIdentityExtractorPort)


def test_adapter_extract_returns_visual_identity() -> None:
    html = (
        '<html><head><meta property="og:image" content="https://example.com/og.png">'
        "</head></html>"
    )
    result = VisualIdentityAdapter().extract(html, "https://example.com/")
    assert isinstance(result, VisualIdentity)
    assert result.logo_path == "https://example.com/og.png"

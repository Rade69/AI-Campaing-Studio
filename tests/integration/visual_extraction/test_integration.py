"""Integration test for S2-G5 visual extraction against a real HTML file."""

from __future__ import annotations

from pathlib import Path

from ai_campaign_studio.infrastructure.visual_extraction import (
    VisualIdentityExtractor,
)


def test_extract_from_html_file_on_disk(tmp_path: Path) -> None:
    html_path = tmp_path / "brand.html"
    html_path.write_text(
        '<html><head>'
        '<base href="https://cdn.example.com/">'
        '<link rel="icon" href="/favicon.png">'
        '<meta property="og:image" content="/logo.png">'
        '<meta property="og:title" content="Example">'
        '<style>:root { --brand: #0af; --accent: #fa0; }</style>'
        "</head></html>",
        encoding="utf-8",
    )

    html = html_path.read_text(encoding="utf-8")
    identity = VisualIdentityExtractor().extract(html, "https://example.com/")

    assert identity.logo_path == "https://cdn.example.com/logo.png"
    assert identity.primary_colors == ("#0af", "#fa0")

"""Unit tests for the S2-G5 asset extractor."""

from __future__ import annotations

from ai_campaign_studio.infrastructure.visual_extraction import AssetExtractor


def test_og_image_and_title_and_description() -> None:
    html = (
        '<html><head>'
        '<meta property="og:image" content="https://example.com/og.png">'
        '<meta property="og:title" content="Brand">'
        '<meta property="og:description" content="Desc">'
        "</head></html>"
    )
    assets = AssetExtractor().extract(html, "https://example.com/")
    assert assets["og_image"] == "https://example.com/og.png"
    assert assets["og_title"] == "Brand"
    assert assets["og_description"] == "Desc"


def test_icon_then_shortcut_icon_then_favicon_fallback() -> None:
    html = '<html><head><link rel="shortcut icon" href="/s.png"></head></html>'
    assert AssetExtractor().extract(html, "https://example.com/")["favicon"] == (
        "https://example.com/s.png"
    )

    html_icon = '<html><head><link rel="icon" href="/i.png"></head></html>'
    assert AssetExtractor().extract(html_icon, "https://example.com/")["favicon"] == (
        "https://example.com/i.png"
    )

    html_none = "<html><head></head></html>"
    assert AssetExtractor().extract(html_none, "https://example.com/")["favicon"] == (
        "https://example.com/favicon.ico"
    )


def test_relative_urls_resolve_against_base_url() -> None:
    html = '<html><head><meta property="og:image" content="/img/og.png"></head></html>'
    assets = AssetExtractor().extract(html, "https://example.com/site/")
    assert assets["og_image"] == "https://example.com/img/og.png"


def test_base_href_overrides_base_url() -> None:
    html = (
        '<html><head><base href="https://cdn.example.com/static/">'
        '<meta property="og:image" content="og.png"></head></html>'
    )
    assets = AssetExtractor().extract(html, "https://example.com/")
    assert assets["og_image"] == "https://cdn.example.com/static/og.png"


def test_twitter_image_and_card() -> None:
    html = (
        '<html><head>'
        '<meta name="twitter:image" content="https://example.com/t.png">'
        '<meta name="twitter:card" content="summary_large_image">'
        "</head></html>"
    )
    assets = AssetExtractor().extract(html, "https://example.com/")
    assert assets["twitter_image"] == "https://example.com/t.png"
    assert assets["twitter_card"] == "summary_large_image"


def test_javascript_and_data_urls_are_rejected() -> None:
    html = (
        '<html><head>'
        '<meta property="og:image" content="javascript:alert(1)">'
        '<link rel="icon" href="data:image/png;base64,AAAA">'
        "</head></html>"
    )
    assets = AssetExtractor().extract(html, "https://example.com/")
    assert "og_image" not in assets
    # data: icon rejected → fallback /favicon.ico.
    assert assets["favicon"] == "https://example.com/favicon.ico"


def test_xss_payload_in_meta_does_not_raise() -> None:
    html = (
        '<html><head>'
        '<meta property="og:image" content="<script>alert(1)</script>">'
        "</head></html>"
    )
    assets = AssetExtractor().extract(html, "https://example.com/")
    assert "og_image" not in assets


def test_multiple_base_href_uses_first() -> None:
    html = (
        '<html><head>'
        '<base href="https://first.example/">'
        '<base href="https://second.example/">'
        '<meta property="og:image" content="a.png">'
        "</head></html>"
    )
    assets = AssetExtractor().extract(html, "https://example.com/")
    assert assets["og_image"] == "https://first.example/a.png"


def test_empty_html_returns_no_assets() -> None:
    assert AssetExtractor().extract("", "https://example.com/") == {}

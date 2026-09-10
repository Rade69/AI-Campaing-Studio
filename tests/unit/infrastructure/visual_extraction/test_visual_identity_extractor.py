"""Unit tests for the S2-G5 visual identity extractor."""

from __future__ import annotations

from ai_campaign_studio.infrastructure.visual_extraction import (
    VisualIdentityExtractor,
)


def test_css_custom_properties_become_primary_colors() -> None:
    html = (
        "<html><head><style>"
        ":root { --brand-color: #abc; --accent: #12345678; }"
        "</style></head></html>"
    )
    identity = VisualIdentityExtractor().extract(html, "https://example.com/")
    assert identity.primary_colors == ("#abc", "#12345678")


def test_host_and_inline_style_and_important() -> None:
    html = (
        "<html><head><style>"
        ":host { --x: #ffffff !important; }"
        ":host-context(.a) { --y: #000; }"
        "</style></head>"
        '<body><div style="--z: #ff0000"></div></body></html>'
    )
    identity = VisualIdentityExtractor().extract(html, "https://example.com/")
    assert identity.primary_colors == ("#ffffff", "#000", "#ff0000")


def test_font_families_extracted() -> None:
    html = (
        '<html><head><style>body { font-family: "Open Sans", Arial, sans-serif; }'
        "</style></head></html>"
    )
    identity = VisualIdentityExtractor().extract(html, "https://example.com/")
    assert identity.font_families == ("Open Sans", "Arial")


def test_logo_priority_og_image_over_twitter_over_favicon() -> None:
    html = (
        '<html><head>'
        '<link rel="icon" href="/fav.png">'
        '<meta name="twitter:image" content="/tw.png">'
        '<meta property="og:image" content="/og.png">'
        "</head></html>"
    )
    identity = VisualIdentityExtractor().extract(html, "https://example.com/")
    assert identity.logo_path == "https://example.com/og.png"


def test_logo_falls_back_to_twitter_then_favicon() -> None:
    html_tw = (
        '<html><head><link rel="icon" href="/fav.png">'
        '<meta name="twitter:image" content="/tw.png"></head></html>'
    )
    tw_identity = VisualIdentityExtractor().extract(html_tw, "https://example.com/")
    assert tw_identity.logo_path == "https://example.com/tw.png"

    html_fav = '<html><head><link rel="icon" href="/fav.png"></head></html>'
    fav_identity = VisualIdentityExtractor().extract(
        html_fav, "https://example.com/"
    )
    assert fav_identity.logo_path == "https://example.com/fav.png"


def test_empty_html_returns_default_identity_no_raise() -> None:
    identity = VisualIdentityExtractor().extract("", "https://example.com/")
    assert identity.logo_path is None
    assert identity.primary_colors == ()
    assert identity.secondary_colors == ()
    assert identity.font_families == ()
    assert identity.image_style_notes == ()


def test_secondary_colors_and_notes_stay_empty() -> None:
    html = '<html><head><style>:root{--c:#123456}</style></head></html>'
    identity = VisualIdentityExtractor().extract(html, "https://example.com/")
    assert identity.secondary_colors == ()
    assert identity.image_style_notes == ()

"""Tests for the Brend screen body renderer.

Mirrors the ACS-GUI-001 ``test_pocetna_ssr.py`` pattern: the body
must be driven by the supplied fixture (changing fixture values must
change the rendered output), all fixture-derived text must round-trip
through ``html.escape``, and the markup must use the V3 CSS classes
(``.tabs``/``.tab``/``.fact``/``.card``/``.section-title``/``.grid``
``.badge``).
"""

from __future__ import annotations

import dataclasses

from ai_campaign_studio.presentation_webview.screens.brend import (
    DEFAULT_FIXTURE,
    ApprovedFact,
    BrandInfo,
    BrandResource,
    BrendFixture,
    VoiceBadge,
    render_body,
)


def test_default_fixture_uses_canonical_brightsmile_brand() -> None:
    """V3_PLAN canonical demo brand = BrightSmile Oral Care."""
    assert DEFAULT_FIXTURE.brand.name == "BrightSmile Oral Care"
    assert DEFAULT_FIXTURE.status_checked is True


def test_default_fixture_has_canonical_facts() -> None:
    codes = [f.code for f in DEFAULT_FIXTURE.facts]
    assert codes == ["F-001", "F-002", "F-003"]
    assert any("alkohol" in f.text for f in DEFAULT_FIXTURE.facts)


def test_default_fixture_has_three_voice_badges() -> None:
    variants = [b.variant for b in DEFAULT_FIXTURE.brand.voice]
    labels = [b.label for b in DEFAULT_FIXTURE.brand.voice]
    assert "info" in variants
    assert "gray" in variants
    assert "Jasan" in labels
    assert "Pouzdan" in labels
    assert "Nenametljiv" in labels


def test_fixtures_are_pure_dataclasses() -> None:
    """No Pydantic in the screen layer; ``frozen=True`` dataclasses only."""
    for cls in (VoiceBadge, BrandInfo, ApprovedFact, BrandResource, BrendFixture):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        if cls is not VoiceBadge:
            assert cls.__dataclass_params__.frozen is True, (
                f"{cls.__name__} must be frozen"
            )


def test_render_body_uses_fixture_values() -> None:
    body = render_body()
    # Brand name appears (HTML-escaped, not raw).
    assert "BrightSmile Oral Care" in body
    # 3 tabs.
    tab_labels = (
        "Osnovni podaci",
        "Odobrene činjenice",
        "Glas brenda",
        "Brend resursi",
    )
    for label in tab_labels:
        assert label in body, f"missing tab label: {label!r}"
    # All 3 fact codes.
    for code in ("F-001", "F-002", "F-003"):
        assert code in body
    # All 3 resource cards.
    for title in ("Logo", "Paleta boja", "Izvori"):
        assert title in body


def test_render_body_uses_canonical_bhs_strings() -> None:
    body = render_body()
    for needle in (
        "Brend",
        "Provjereno i ažurno",
        "Posljednja provjera",
        "Odobrene činjenice",
        "Brend resursi",
        "Primarna publika",
        "Glas brenda",
    ):
        assert needle in body, f"missing BHS string: {needle!r}"


def test_changing_fixture_changes_rendered_body() -> None:
    """Acceptance: fixture change must be reflected in the rendered body."""
    custom = BrendFixture(
        status_checked=False,
        brand=BrandInfo(
            name="Custom Brand",
            description="Custom description",
            primary_audience="Custom audience",
            voice=[VoiceBadge("Brutalan", "danger")],
            last_check_label="1. 1. 2099.",
        ),
        facts=[ApprovedFact("X-999", "Custom fact text")],
        resources=[BrandResource("Ikonica", "PNG")],
        refresh_message="Custom refresh",
    )
    body = render_body(custom)
    assert "Custom Brand" in body
    assert "Custom description" in body
    assert "Custom audience" in body
    assert "Brutalan" in body
    assert "X-999" in body
    assert "Custom fact text" in body
    assert "Ikonica" in body
    # Defaults must NOT leak through.
    assert "BrightSmile" not in body
    assert "F-001" not in body


def test_render_body_uses_v3_css_classes() -> None:
    body = render_body()
    for cls in (
        "tabs",
        "tab active",
        "grid g2",
        "card",
        "fact",
        "section-title",
        "grid g3",
        "statusline",
        "badge info",
        "badge gray",
        "brand-status",
        "tick",
        "field",
        "callout",
        "actions",
    ):
        assert cls in body, f"missing V3 class in body: {cls!r}"


def test_render_body_escapes_xss_in_fixture() -> None:
    """``html.escape`` discipline: arbitrary fixture text must be escaped."""
    nasty = BrendFixture(
        status_checked=True,
        brand=BrandInfo(
            name="<script>alert(1)</script>",
            description="<img onerror=x>",
            primary_audience="<b>x</b>",
            voice=[VoiceBadge("<i>x</i>", "info")],
            last_check_label="<svg>",
        ),
        facts=[ApprovedFact("F-1", "<x>")],
        resources=[BrandResource("<a>", "<hr>")],
        refresh_message="\"quoted\" & <angled>",
    )
    body = render_body(nasty)
    assert "<script>" not in body
    assert "<img onerror" not in body
    assert "<svg>" not in body
    # Quoted/angled payload is escaped but the text characters remain readable.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_render_body_emits_no_remote_assets() -> None:
    body = render_body()
    for forbidden in (
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.tailwindcss.com",
        "unpkg.com",
    ):
        assert forbidden not in body, f"body references remote asset: {forbidden}"


def test_render_body_refresh_uses_toast_stub() -> None:
    """The 'Osvježi podatke' button must be a toast stub, not a real link."""
    body = render_body()
    assert "Osvježi podatke" in body
    # The button has data-action="toast" (no <a href>).
    assert 'data-action="toast"' in body
    # The refresh message from the fixture should appear (escaped).
    assert "Kasnije: pokreni ingestion/review tok." in body

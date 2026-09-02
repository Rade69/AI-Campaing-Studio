"""Tests for the Podešavanja screen body renderer.

Acceptance for ACS-GUI-002: the settings panel mirrors the V3
reference (3 settings tabs with "AI provajderi" active, 6 provider
rows with the same logo initials and status labels, the production-tok
callout). Every "Podesi" button is a ``data-action="toast"`` stub
— the real provider configuration flow goes through a future
``PresentationFacade.configure_provider`` use case.
"""

from __future__ import annotations

import dataclasses
import re

from ai_campaign_studio.presentation_webview.screens.podesavanja import (
    ACTIVE_TAB_INDEX,
    DEFAULT_FIXTURE,
    SETTINGS_TABS,
    PodesavanjaFixture,
    Provider,
    render_body,
)


def test_settings_tabs_constant_matches_v3() -> None:
    assert SETTINGS_TABS == ("Opšte", "Jezik", "AI provajderi")
    assert ACTIVE_TAB_INDEX == 2


def test_default_fixture_has_six_canonical_providers() -> None:
    """V3 reference lists all 6 providers with these exact names."""
    names = [p.display_name for p in DEFAULT_FIXTURE.providers]
    assert names == [
        "OpenAI",
        "Anthropic",
        "Google",
        "DeepSeek",
        "OpenRouter",
        "OpenAI kompatibilan",
    ]


def test_default_fixture_logo_initials_match_v3() -> None:
    initials = [p.logo_initials for p in DEFAULT_FIXTURE.providers]
    assert initials == ["OA", "A", "G", "DS", "OR", "AI"]


def test_default_fixture_status_labels_match_v3() -> None:
    statuses = [p.status_label for p in DEFAULT_FIXTURE.providers]
    # First 5 = "Nije povezano" (per V3); the 6th (OpenAI compat) has
    # the longer "Base URL + API ključ + model ID" detail.
    assert statuses[:5] == ["Nije povezano"] * 5
    assert statuses[5] == "Base URL + API ključ + model ID"


def test_default_fixture_callout_matches_v3() -> None:
    assert "Production tok" in DEFAULT_FIXTURE.callout
    assert "API ključ pripada provajderu, ne modelu" in DEFAULT_FIXTURE.callout


def test_default_fixture_intro_mentions_keyring() -> None:
    assert "OS keyring" in DEFAULT_FIXTURE.intro
    assert "plaintext" in DEFAULT_FIXTURE.intro


def test_fixtures_are_pure_dataclasses() -> None:
    assert dataclasses.is_dataclass(Provider)
    assert dataclasses.is_dataclass(PodesavanjaFixture)
    assert Provider.__dataclass_params__.frozen is True
    assert PodesavanjaFixture.__dataclass_params__.frozen is True


def test_render_body_renders_three_settings_tabs() -> None:
    body = render_body()
    for tab in SETTINGS_TABS:
        assert tab in body, f"missing settings tab: {tab!r}"
    # AI provajderi is the active tab (and only the active one).
    assert body.count("tab active") == 1
    assert "tab active\">AI provajderi</div>" in body


def test_render_body_renders_six_provider_rows() -> None:
    body = render_body()
    for name in (
        "OpenAI",
        "Anthropic",
        "Google",
        "DeepSeek",
        "OpenRouter",
        "OpenAI kompatibilan",
    ):
        assert name in body
    # All 6 logo initials.
    for initials in ("OA", "A", "G", "DS", "OR", "AI"):
        assert f"<div class=\"logo\">{initials}</div>" in body


def test_render_body_podesi_buttons_are_toast_stubs() -> None:
    body = render_body()
    # One "Podesi" per provider.
    assert body.count(">Podesi<") == 6
    # Each is a button[data-action="toast"].
    podesi_buttons = re.findall(
        r'<button class="btn" data-action="toast"[^>]*>Podesi</button>',
        body,
    )
    assert len(podesi_buttons) == 6


def test_render_body_no_anchor_href() -> None:
    body = render_body()
    hrefs = re.findall(r'<a[^>]*\bhref="([^"]+)"', body)
    assert hrefs == [], f"unexpected <a href> in Podešavanja body: {hrefs}"


def test_render_body_uses_v3_classes() -> None:
    body = render_body()
    for needle in (
        "grid",
        "card",
        "tabs",
        "tab active",
        "provider",
        "left",
        "logo",
        "small muted",
        "callout",
    ):
        assert needle in body, f"missing V3 class: {needle!r}"


def test_changing_fixture_changes_rendered_body() -> None:
    custom = PodesavanjaFixture(
        intro="Custom intro",
        providers=[
            Provider(
                code="custom",
                display_name="Custom Provider",
                logo_initials="CP",
                status_label="Connected",
            ),
        ],
        callout="Custom callout",
        podesi_toast="Custom toast",
    )
    body = render_body(custom)
    assert "Custom intro" in body
    assert "Custom Provider" in body
    assert "CP" in body
    assert "Custom callout" in body
    # Default 6 must not leak.
    assert "OpenAI" not in body
    assert "Anthropic" not in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = PodesavanjaFixture(
        intro="<script>x</script>",
        providers=[
            Provider(
                code="x",
                display_name="<img>",
                logo_initials="<svg>",
                status_label="<b>y</b>",
            ),
        ],
        callout="<svg>",
        podesi_toast="\"&<x>",
    )
    body = render_body(nasty)
    assert "<script>" not in body
    assert "<img>" not in body
    assert "<svg>" not in body
    assert "&lt;script&gt;x&lt;/script&gt;" in body


def test_render_body_emits_no_remote_assets() -> None:
    body = render_body()
    for forbidden in (
        "fonts.googleapis.com",
        "cdn.tailwindcss.com",
        "unpkg.com",
    ):
        assert forbidden not in body

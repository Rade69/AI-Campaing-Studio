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
    DEFAULT_LANGUAGE,
    LANGUAGES,
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
    # ACS-GUI-004: tab now carries data-tab-target
    assert (
        'class="tab active" data-action="tab" data-tab-target="panel-provajderi">'
        "AI provajderi</div>" in body
    )


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
        "tabs tabs-vertical",
        "tab active",
        "provider",
        "left",
        "logo",
        "small muted",
        "callout",
    ):
        assert needle in body, f"missing V3 class: {needle!r}"
    # ACS-GUI-004: tab/panel structure markers
    for marker in (
        'data-tabs',
        'data-tab-panel',
        'id="panel-opste"',
        'id="panel-jezik"',
        'id="panel-provajderi"',
    ):
        assert marker in body, f"missing ACS-GUI-004 marker: {marker!r}"


def test_all_three_settings_tabs_have_data_tab_target() -> None:
    body = render_body()
    for panel_id in ("panel-opste", "panel-jezik", "panel-provajderi"):
        assert f'data-tab-target="{panel_id}"' in body, (
            f"missing data-tab-target for {panel_id!r}"
        )


def test_only_default_active_panel_is_visible() -> None:
    """panel-provajderi is default-active (no hidden); Opšte/Jezik start hidden."""
    import re
    body = render_body()
    panel_open_re = re.compile(
        r'<div\b[^>]*data-tab-panel[^>]*id="(panel-[a-z]+)"([^>]*)>'
    )
    panels = {pid: attrs for pid, attrs in panel_open_re.findall(body)}
    assert set(panels) == {
        "panel-opste",
        "panel-jezik",
        "panel-provajderi",
    }, f"unexpected panel ids: {set(panels)}"
    assert "hidden" not in panels["panel-provajderi"], (
        f"panel-provajderi is default-active; attrs: {panels['panel-provajderi']!r}"
    )
    for pid in ("panel-opste", "panel-jezik"):
        assert "hidden" in panels[pid], (
            f"{pid} should start hidden; attrs: {panels[pid]!r}"
        )


def test_settings_tabs_use_tabs_vertical_class_not_inline_style() -> None:
    """The old inline `style="display:block;..."` on the tabs div is gone
    — the layout must be driven by the ``tabs-vertical`` CSS class only.
    """
    body = render_body()
    # The tabs wrapper carries the class
    assert 'class="tabs tabs-vertical"' in body
    # No inline style on the tabs wrapper anymore
    assert 'class="tabs" style=' not in body
    assert 'class="tabs tabs-vertical" style=' not in body


def test_opste_and_jezik_are_placeholder_callouts() -> None:
    """The Opšte panel is a placeholder; the Jezik panel is a real picker."""
    body = render_body()
    # Opšte is still a placeholder callout
    assert "Op\u0161te postavke aplikacije" in body
    # The Jezik panel now contains the language picker (no longer a callout)
    assert "Jezik sadr\u017eaja" in body
    assert "lang-picker" in body


def test_languages_constant_is_locked_order_sr_hr_bs_en() -> None:
    """User-locked order (2026-09-03): Srpski, Hrvatski, Bosanski, Engleski."""
    assert LANGUAGES == (
        ("SR", "Srpski"),
        ("HR", "Hrvatski"),
        ("BS", "Bosanski"),
        ("EN", "Engleski"),
    )
    assert DEFAULT_LANGUAGE == "SR"


def test_language_picker_renders_four_buttons_in_locked_order() -> None:
    body = render_body()
    # 4 rows, each data-action="lang-pick" with the right code + visible name
    for code, name in LANGUAGES:
        marker = (
            f'data-action="lang-pick" data-lang="{code}">'
            f'<span class="lang-name">{name}</span>'
        )
        assert marker in body, f"missing lang row: {code} ({name!r})"
    # Order check: position of each code in the body matches LANGUAGES order
    positions = [body.index(f'data-lang="{c}"') for c, _ in LANGUAGES]
    assert positions == sorted(positions), (
        f"language rows not in locked order, positions: {positions}"
    )


def test_default_language_is_pre_marked_active() -> None:
    body = render_body()
    # SR is DEFAULT_LANGUAGE; its row carries lang-active class + a check mark
    sr_idx = body.index('data-lang="SR"')
    # Back up to the <button ...> opening tag
    open_tag = body[:sr_idx].rsplit("<button", 1)[-1]
    assert 'class="lang-row lang-active"' in open_tag
    # The check mark glyph is present in the SR row
    sr_block_end = body.index("</button>", sr_idx)
    sr_block = body[sr_idx:sr_block_end]
    assert "\u2713" in sr_block
    # No other row carries lang-active or the check glyph
    for code, _ in LANGUAGES:
        if code == "SR":
            continue
        idx = body.index(f'data-lang="{code}"')
        open_tag = body[:idx].rsplit("<button", 1)[-1]
        assert "lang-active" not in open_tag, (
            f"{code} should not be lang-active by default"
        )
        block_end = body.index("</button>", idx)
        block = body[idx:block_end]
        assert "\u2713" not in block, f"{code} should not have a checkmark by default"


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

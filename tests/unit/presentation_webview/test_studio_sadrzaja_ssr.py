"""Tests for the Studio sadržaja (step 4) screen body renderer.

Acceptance for ACS-GUI-003: 4 REAL tab panels (data-tab-target →
data-tab-panel), NOT the cosmetic-only markup from the V3 mokap. Panel
"Sadržaj" is default-active; the other three start hidden. All quick
actions are "Bridge stub: <action>" toast stubs.
"""

from __future__ import annotations

import dataclasses
import re

from ai_campaign_studio.presentation_webview.screens.studio_sadrzaja import (
    DEFAULT_FIXTURE,
    QUICK_ACTIONS,
    TAB_LABELS,
    TAB_PANEL_IDS,
    ApprovedFact,
    StudioSadrzajaFixture,
    render_body,
)


def test_tab_structure_is_locked() -> None:
    assert TAB_LABELS == (
        "Sadržaj",
        "Korištene činjenice",
        "Provjera usklađenosti",
        "Istorija verzija",
    )
    assert TAB_PANEL_IDS == (
        "panel-sadrzaj",
        "panel-cinjenice",
        "panel-usklađenost",
        "panel-istorija",
    )


def test_quick_actions_are_locked_bridge_stubs() -> None:
    assert QUICK_ACTIONS == (
        ("Prepiši", "rewrite_content"),
        ("Skrati", "shorten_content"),
        ("Poboljšaj uvod", "improve_hook"),
        ("Promijeni ton", "change_tone"),
        ("Generiši varijantu", "generate_variant"),
    )


def test_default_fixture_matches_v3_reference() -> None:
    assert DEFAULT_FIXTURE.item_index == 1
    assert DEFAULT_FIXTURE.item_total == 6
    assert DEFAULT_FIXTURE.role == "Problem"
    assert DEFAULT_FIXTURE.platform == "Instagram"
    assert DEFAULT_FIXTURE.format == "Feed 4:5"
    assert DEFAULT_FIXTURE.planned_date == "3. septembar"
    assert DEFAULT_FIXTURE.hook == "Da li svakodnevna rutina može biti jednostavnija?"
    assert DEFAULT_FIXTURE.hook_char_count == 52
    assert DEFAULT_FIXTURE.hook_char_limit == 90
    assert [f.code for f in DEFAULT_FIXTURE.facts] == ["F-001", "F-002"]
    assert len(DEFAULT_FIXTURE.compliance_checks) == 3


def test_fixtures_are_frozen_dataclasses() -> None:
    assert dataclasses.is_dataclass(ApprovedFact)
    assert dataclasses.is_dataclass(StudioSadrzajaFixture)
    assert ApprovedFact.__dataclass_params__.frozen is True
    assert StudioSadrzajaFixture.__dataclass_params__.frozen is True


def test_render_body_uses_real_tab_panel_structure() -> None:
    """The ACS-GUI-004 pattern: every tab targets a panel; 4 panels exist."""
    body = render_body()
    assert 'data-tabs' in body
    assert body.count('data-tab-panel') == 4
    for panel_id in TAB_PANEL_IDS:
        assert f'data-tab-target="{panel_id}"' in body
        assert f'id="{panel_id}"' in body


def test_render_body_only_sadrzaj_panel_is_visible_by_default() -> None:
    body = render_body()
    panel_open_re = re.compile(
        r'<div\b[^>]*data-tab-panel[^>]*id="(panel-[^"]+)"([^>]*)>'
    )
    panels = {pid: attrs for pid, attrs in panel_open_re.findall(body)}
    assert set(panels) == set(TAB_PANEL_IDS)
    assert "hidden" not in panels["panel-sadrzaj"]
    for pid in ("panel-cinjenice", "panel-usklađenost", "panel-istorija"):
        assert "hidden" in panels[pid], f"{pid} should start hidden"


def test_render_body_first_tab_is_default_active() -> None:
    body = render_body()
    assert (
        '<div class="tab active" data-action="tab" '
        'data-tab-target="panel-sadrzaj">Sadržaj</div>'
    ) in body


def test_render_body_renders_meta_card() -> None:
    body = render_body()
    assert "<h3>Stavka 1 / 6</h3>" in body
    for needle in ("Uloga", "Problem", "Platforma", "Instagram", "Format",
                   "Feed 4:5", "Planirano", "3. septembar", "Status"):
        assert needle in body
    assert '<span class="badge warn">Nacrt</span>' in body


def test_render_body_renders_edit_form() -> None:
    body = render_body()
    assert "Uredi sadržaj" in body
    assert "Naslov / Hook" in body
    assert "52 / 90 znakova" in body
    assert "Glavni tekst" in body
    assert "CTA" in body
    assert "Pogledajte dostupne varijante" in body


def test_render_body_quick_actions_are_bridge_stubs() -> None:
    body = render_body()
    for _label, action in QUICK_ACTIONS:
        assert f'data-message="Bridge stub: {action}">' in body
    # Each is a toast button, none is a real link.
    assert body.count('data-action="toast"') >= 5 + 2  # 5 quick + save + send


def test_render_body_save_and_send_are_toast_stubs() -> None:
    body = render_body()
    assert re.search(
        r'<button class="btn" data-action="toast"[^>]*>Sačuvaj nacrt</button>',
        body,
    )
    assert re.search(
        r'<button class="btn" data-action="toast"[^>]*>'
        r"Pošalji na reviziju</button>",
        body,
    )


def test_render_body_pregled_i_izvoz_is_real_forward_link() -> None:
    """Regression: without this, Studio sadržaja was a dead end -- no way
    to reach step 5 / the export screen (Human Owner feedback, 2026-09-03)."""
    body = render_body()
    assert (
        '<a class="btn primary" href="../pregled_izvoz/index.html">'
        "Pregled i izvoz →</a>"
    ) in body


def test_render_body_facts_panel_has_facts() -> None:
    body = render_body()
    assert "<b>F-001</b> Formula ne sadrži alkohol." in body
    assert "<b>F-002</b> Pakovanje sadrži 500 ml." in body


def test_render_body_compliance_panel_has_checks() -> None:
    body = render_body()
    assert body.count('<div class="check"><i>✓</i>') == 3
    assert "Sve faktografske tvrdnje imaju fact reference." in body
    assert "Nema zabranjenih termina." in body
    assert "CTA je prisutan." in body


def test_render_body_history_panel_is_placeholder_callout() -> None:
    body = render_body()
    assert "Istorija verzija" in body
    assert "dostupno u narednoj verziji" in body


def test_render_body_stepper_step_4_active_prior_done() -> None:
    body = render_body()
    assert (
        '<div class="step active"><span class="num">4</span>Studio sadržaja</div>'
        in body
    )
    assert body.count('class="step done"') == 3
    assert (
        '<a class="step done" href="../kalendar/index.html?campaign='
        'Proljetna%20kolekcija"><span class="num">3</span>Kalendar</a>'
    ) in body


def test_changing_fixture_changes_rendered_body() -> None:
    custom = StudioSadrzajaFixture(
        campaign_name="Custom",
        badge_variant="info",
        badge_label="Odobreno",
        item_index=2,
        item_total=8,
        role="Dokaz",
        platform="Facebook",
        format="Karusel",
        planned_date="5. septembar",
        status_variant="ok",
        status_label="Spremno",
        hook="Custom hook",
        hook_char_count=11,
        hook_char_limit=99,
        body_text="Custom body",
        cta="Custom cta",
        preview_label="Pregled · Facebook karusel",
        facts=[ApprovedFact("X-1", "Custom fact")],
        compliance_checks=["Custom check"],
        sacuvaj_nacrt_toast="t1",
        posalji_reviziju_toast="t2",
    )
    body = render_body(custom)
    assert "<h3>Stavka 2 / 8</h3>" in body
    assert "Custom hook" in body
    assert "11 / 99 znakova" in body
    assert "Custom body" in body
    assert "Custom cta" in body
    assert "X-1" in body
    assert "Custom check" in body
    assert "Custom fact" in body
    # Defaults must not leak.
    assert "Stavka 1 / 6" not in body
    assert "F-001" not in body
    assert "Problem" not in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = StudioSadrzajaFixture(
        campaign_name="<x>",
        badge_variant="warn",
        badge_label="<b>x</b>",
        item_index=1,
        item_total=1,
        role="<script>x</script>",
        platform="<i>x</i>",
        format="<i>x</i>",
        planned_date="<svg>",
        status_variant="warn",
        status_label="<b>x</b>",
        hook="<img onerror=x>",
        hook_char_count=1,
        hook_char_limit=1,
        body_text="<script>",
        cta="<b>x</b>",
        preview_label="<x>",
        facts=[ApprovedFact("F-1", "<script>x</script>")],
        compliance_checks=["<img onerror=x>"],
        sacuvaj_nacrt_toast="<svg>",
        posalji_reviziju_toast="<svg>",
    )
    body = render_body(nasty)
    assert "<script>" not in body
    assert "<img onerror" not in body
    assert "<svg>" not in body


def test_render_body_emits_no_remote_assets() -> None:
    body = render_body()
    for forbidden in (
        "fonts.googleapis.com",
        "cdn.tailwindcss.com",
        "unpkg.com",
    ):
        assert forbidden not in body

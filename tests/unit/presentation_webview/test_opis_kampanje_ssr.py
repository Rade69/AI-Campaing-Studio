"""Tests for the Opis kampanje (step 1) screen body renderer.

Acceptance for ACS-GUI-003: the body is fixture-driven, the stepper shows
step 1 active, "Sačuvaj i napravi plan →" is a real link into the next
workflow step, and "Sačuvaj nacrt" stays a toast stub.
"""

from __future__ import annotations

import dataclasses
import re

from ai_campaign_studio.presentation_webview.screens.opis_kampanje import (
    DEFAULT_FIXTURE,
    FORMATS,
    JEZICI_SADRZAJA,
    PLATFORMS,
    OpisKampanjeFixture,
    render_body,
)


def test_default_fixture_matches_v3_reference() -> None:
    assert DEFAULT_FIXTURE.campaign_name == "Proljetna kolekcija"
    assert DEFAULT_FIXTURE.naziv == "Proljetna kolekcija"
    assert DEFAULT_FIXTURE.cilj == "Generisanje interesovanja i upita"
    assert DEFAULT_FIXTURE.kanal == "Društvene mreže"
    assert DEFAULT_FIXTURE.platforma == "Instagram"
    assert DEFAULT_FIXTURE.format == "Feed 4:5"
    assert DEFAULT_FIXTURE.jezik == "SR"
    assert DEFAULT_FIXTURE.badge_label == "Nacrt"
    assert DEFAULT_FIXTURE.badge_variant == "warn"


def test_platform_and_format_option_lists_are_locked() -> None:
    assert PLATFORMS == ("Instagram", "Facebook", "LinkedIn")
    assert FORMATS == ("Feed 4:5", "Kvadrat 1:1", "Priča 9:16")


def test_content_language_option_list_matches_locked_project_decision() -> None:
    """Human Owner decision, 2026-09-03: SR/HR/BS/EN, no NEUTRAL variant,
    no "BHS" prefix on the labels -- and the select must offer all 4, not
    just the currently-selected value (the earlier bug: a collapsed
    single-option ``<select>`` read as "no real choice")."""
    assert JEZICI_SADRZAJA == (
        ("SR", "Srpski"),
        ("HR", "Hrvatski"),
        ("BS", "Bosanski"),
        ("EN", "Engleski"),
    )


def test_fixture_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(OpisKampanjeFixture)
    assert OpisKampanjeFixture.__dataclass_params__.frozen is True


def test_render_body_renders_all_fixture_fields() -> None:
    body = render_body()
    for needle in (
        "Opis kampanje",
        "Naziv kampanje",
        "Proljetna kolekcija",
        "Generisanje interesovanja i upita",
        "Ponuda / proizvod",
        "Ciljna publika",
        "Postojeći i novi kupci, 25–45 godina.",
        "Ciljani kanal",
        "Kanal",
        "Društvene mreže",
        "Platforma",
        "Format",
        "Jezik sadržaja",
        "Srpski",
        "Posebne instrukcije",
        "Opcionalno",
    ):
        assert needle in body, f"missing string: {needle!r}"


def test_render_body_selects_platform_and_format_from_fixture() -> None:
    body = render_body()
    assert "<option selected>Instagram</option>" in body
    assert "<option selected>Feed 4:5</option>" in body
    # The other options render unselected.
    assert "<option>Facebook</option>" in body
    assert "<option>Kvadrat 1:1</option>" in body


def test_render_body_jezik_sadrzaja_is_real_dropdown_with_all_options() -> None:
    """Regression: a real ``<select>`` with all 4 language options (the
    earlier bug: a single-option select with no real choice behind it)."""
    body = render_body()
    assert '<option value="SR" selected>Srpski</option>' in body
    for code, label in (("HR", "Hrvatski"), ("BS", "Bosanski"), ("EN", "Engleski")):
        assert f'<option value="{code}">{label}</option>' in body


def test_render_body_stepper_step_1_active() -> None:
    body = render_body()
    assert (
        '<div class="step active"><span class="num">1</span>Opis kampanje</div>'
        in body
    )
    assert 'class="step done"' not in body


def test_render_body_has_badge_nacrt() -> None:
    body = render_body()
    assert '<span class="badge warn">Nacrt</span>' in body


def test_render_body_sacuvaj_nacrt_is_toast_stub() -> None:
    body = render_body()
    assert re.search(
        r'<button class="btn" data-action="toast"[^>]*>Sačuvaj nacrt</button>',
        body,
    ), '"Sačuvaj nacrt" must be a toast-stub button'


def test_render_body_sacuvaj_i_napravi_plan_is_real_link() -> None:
    body = render_body()
    assert (
        '<a class="btn primary" href="../plan_kampanje/index.html">'
        "Sačuvaj i napravi plan →</a>"
    ) in body


def test_changing_fixture_changes_rendered_body() -> None:
    custom = OpisKampanjeFixture(
        campaign_name="Custom",
        badge_variant="info",
        badge_label="Aktivan",
        naziv="AAA",
        cilj="Cilj X",
        ponuda="Ponuda X",
        publika="Publika X",
        kanal="Email",
        platforma="Facebook",
        format="Kvadrat 1:1",
        jezik="EN",
        instrukcije="Instrukcije X",
        sacuvaj_nacrt_toast="Toast X",
    )
    body = render_body(custom)
    assert "AAA" in body
    assert "Cilj X" in body
    assert "Ponuda X" in body
    assert "Publika X" in body
    assert "Email" in body
    assert '<option selected>Facebook</option>' in body
    assert '<option selected>Kvadrat 1:1</option>' in body
    assert "EN" in body
    assert "Instrukcije X" in body
    assert '<span class="badge info">Aktivan</span>' in body
    # Defaults must not leak.
    assert "Proljetna kolekcija" not in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = OpisKampanjeFixture(
        campaign_name="<script>x</script>",
        badge_variant="warn",
        badge_label="<b>x</b>",
        naziv='"><img onerror=x>',
        cilj="<svg>",
        ponuda="<i>x</i>",
        publika="<b>x</b>",
        kanal="<a>",
        platforma="<x>",
        format="<x>",
        jezik="<x>",
        instrukcije="<script>",
        sacuvaj_nacrt_toast='"quoted"',
    )
    body = render_body(nasty)
    assert "<script>" not in body
    assert "<img onerror" not in body
    assert "<svg>" not in body


def test_render_body_emits_no_remote_assets() -> None:
    body = render_body()
    for forbidden in (
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.tailwindcss.com",
        "unpkg.com",
    ):
        assert forbidden not in body

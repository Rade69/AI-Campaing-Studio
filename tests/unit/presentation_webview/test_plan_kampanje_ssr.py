"""Tests for the Plan kampanje (step 2) screen body renderer.

Acceptance for ACS-GUI-003: 6-row plan table, stepper step 2 active with
step 1 done, "← Opis" and "Odobri plan i nastavi →" as real links (the
latter into Kalendar via ``?campaign=``), "Regeneriši plan" as toast stub.
"""

from __future__ import annotations

import dataclasses
import re

from ai_campaign_studio.presentation_webview.screens.plan_kampanje import (
    DEFAULT_FIXTURE,
    PlanItem,
    PlanKampanjeFixture,
    render_body,
)


def test_default_fixture_has_six_canonical_items() -> None:
    roles = [i.role_label for i in DEFAULT_FIXTURE.items]
    assert roles == [
        "Problem",
        "Edukacija",
        "Dokaz",
        "Prigovor",
        "Ponuda",
        "Akcija",
    ]
    variants = [i.role_variant for i in DEFAULT_FIXTURE.items]
    assert variants == ["danger", "info", "ok", "warn", "info", "ok"]


def test_default_fixture_badge_is_plan_v1() -> None:
    assert DEFAULT_FIXTURE.badge_variant == "info"
    assert DEFAULT_FIXTURE.badge_label == "Plan v1"


def test_fixtures_are_frozen_dataclasses() -> None:
    assert dataclasses.is_dataclass(PlanItem)
    assert dataclasses.is_dataclass(PlanKampanjeFixture)
    assert PlanItem.__dataclass_params__.frozen is True
    assert PlanKampanjeFixture.__dataclass_params__.frozen is True


def test_render_body_emits_six_rows_with_columns() -> None:
    body = render_body()
    for header in ("#", "Uloga", "Tema", "Cilj", "Format", "Status"):
        assert header in body
    rows = re.findall(r"<tr>", body)
    # 1 header row (implicit <tr> in thead) + 6 data rows.
    assert len(rows) == 7
    for role in ("Problem", "Edukacija", "Dokaz", "Prigovor", "Ponuda", "Akcija"):
        assert role in body
    # All statuses are "Planirano".
    assert body.count("Planirano") == 6
    # Role badges carry the correct variants.
    for variant in ("danger", "info", "ok", "warn"):
        assert f'badge {variant}' in body


def test_render_body_stepper_step_2_active_step_1_done() -> None:
    body = render_body()
    assert (
        '<a class="step done" href="../opis_kampanje/index.html">'
        '<span class="num">1</span>Opis kampanje</a>'
    ) in body
    assert (
        '<div class="step active"><span class="num">2</span>Plan kampanje</div>'
        in body
    )


def test_render_body_back_link_is_real() -> None:
    body = render_body()
    assert '<a class="btn" href="../opis_kampanje/index.html">← Opis</a>' in body


def test_render_body_odobri_plan_links_to_kalendar_with_campaign() -> None:
    body = render_body()
    assert (
        '<a class="btn primary" '
        'href="../kalendar/index.html?campaign=Proljetna%20kolekcija">'
        "Odobri plan i nastavi →</a>"
    ) in body


def test_render_body_regenerisi_plan_is_toast_stub() -> None:
    body = render_body()
    assert re.search(
        r'<button class="btn" data-action="toast"[^>]*>Regeneriši plan</button>',
        body,
    ), '"Regeneriši plan" must be a toast-stub button'


def test_changing_fixture_changes_rendered_body() -> None:
    custom = PlanKampanjeFixture(
        campaign_name="Custom Kampanja",
        badge_variant="ok",
        badge_label="Plan v2",
        items=[
            PlanItem(
                index=1,
                role_label="Problem",
                role_variant="danger",
                theme="Custom tema",
                goal="Custom cilj",
                format="Priča 9:16",
                status_label="Spremno",
                status_variant="ok",
            ),
        ],
        regenerisi_toast="Custom toast",
    )
    body = render_body(custom)
    assert "Custom tema" in body
    assert "Custom cilj" in body
    assert "Priča 9:16" in body
    assert '<span class="badge ok">Plan v2</span>' in body
    # Kalendar link carries the custom, url-encoded campaign name.
    assert "campaign=Custom%20Kampanja" in body
    # Defaults must not leak.
    assert "Edukacija" not in body
    assert "Proljetna kolekcija" not in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = PlanKampanjeFixture(
        campaign_name="<x>",
        badge_variant="info",
        badge_label="<b>x</b>",
        items=[
            PlanItem(
                index=1,
                role_label="<script>x</script>",
                role_variant="info",
                theme="<img onerror=x>",
                goal="<svg>",
                format="<i>x</i>",
                status_label="<b>x</b>",
                status_variant="gray",
            ),
        ],
        regenerisi_toast='"quoted"',
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

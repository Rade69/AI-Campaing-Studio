"""Tests for the Pregled i izvoz (step 5) screen body renderer.

Acceptance for ACS-GUI-003: 3-column content-card grid, 2-column quality/
export grid, stepper step 5 active with steps 1–4 done, and both "Odobri
kampanju" and "Izvezi ZIP paket" as toast stubs (real approve/export is
G10+ scope).
"""

from __future__ import annotations

import dataclasses
import re

from ai_campaign_studio.presentation_webview.screens.pregled_izvoz import (
    DEFAULT_FIXTURE,
    ContentPreviewItem,
    ExportRow,
    PregledIzvozFixture,
    render_body,
)


def test_default_fixture_matches_v3_reference() -> None:
    assert len(DEFAULT_FIXTURE.content_items) == 3
    roles = [i.role for i in DEFAULT_FIXTURE.content_items]
    assert roles == ["Problem", "Edukacija", "Dokaz"]
    statuses = [
        (i.status_variant, i.status_label)
        for i in DEFAULT_FIXTURE.content_items
    ]
    assert statuses == [("ok", "Odobreno"), ("ok", "Odobreno"), ("warn", "Za reviziju")]
    assert len(DEFAULT_FIXTURE.quality_checks) == 4
    export_labels = [r.label for r in DEFAULT_FIXTURE.export_rows]
    assert export_labels == ["Tekst objava", "Renderovane slike", "manifest.json"]


def test_fixtures_are_frozen_dataclasses() -> None:
    for cls in (ContentPreviewItem, ExportRow, PregledIzvozFixture):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True


def test_render_body_emits_three_content_cards() -> None:
    body = render_body()
    assert body.count('class="empty-visual">[ Vizual ]</div>') == 3
    assert "<h3 style=\"margin-top:12px\">1 · Problem</h3>" in body
    assert "<h3 style=\"margin-top:12px\">2 · Edukacija</h3>" in body
    assert "<h3 style=\"margin-top:12px\">3 · Dokaz</h3>" in body
    assert (
        "Da li svakodnevna rutina može biti jednostavnija?" in body
    )
    assert body.count('<span class="badge ok">Odobreno</span>') == 2
    assert '<span class="badge warn">Za reviziju</span>' in body


def test_render_body_emits_quality_checks() -> None:
    body = render_body()
    assert "Provjera kvaliteta" in body
    assert body.count('<div class="check"><i>✓</i>') == 4
    for check in (
        "CTA prisutan u svim stavkama.",
        "Nema unsupported fact claims.",
        "Broj znakova je unutar formatnih ograničenja.",
        "Ton je konzistentan sa Brand Snapshotom.",
    ):
        assert check in body


def test_render_body_emits_export_rows_and_zip_button() -> None:
    body = render_body()
    assert "Izvoz paketa" in body
    assert "Predviđeni rezultat za G10" in body
    assert "Tekst objava" in body
    assert '<span class="badge ok">Spremno</span>' in body
    assert '<span class="badge gray">Čeka renderer</span>' in body
    assert '<span class="badge info">Interno</span>' in body
    assert "Izvezi ZIP paket" in body


def test_render_body_odobri_kampanju_is_toast_stub() -> None:
    body = render_body()
    assert re.search(
        r'<button class="btn success" data-action="toast"[^>]*>'
        r"Odobri kampanju</button>",
        body,
    )


def test_render_body_izvezi_zip_is_toast_stub() -> None:
    body = render_body()
    assert re.search(
        r'<button class="btn primary" data-action="toast"[^>]*>'
        r"Izvezi ZIP paket</button>",
        body,
    )


def test_render_body_stepper_step_5_active_all_prior_done() -> None:
    body = render_body()
    assert body.count('class="step done"') == 4
    assert (
        '<div class="step active"><span class="num">5</span>Pregled i izvoz</div>'
        in body
    )
    assert (
        '<a class="step done" href="../studio_sadrzaja/index.html">'
        '<span class="num">4</span>Studio sadržaja</a>'
    ) in body


def test_changing_fixture_changes_rendered_body() -> None:
    custom = PregledIzvozFixture(
        campaign_name="Custom",
        content_items=[
            ContentPreviewItem(
                index=1,
                role="Ponuda",
                headline="Custom headline",
                status_variant="info",
                status_label="Novo",
            ),
        ],
        quality_checks=["Custom check"],
        export_rows=[ExportRow("Custom row", "danger", "Greška")],
        export_intro="Custom intro",
        odobri_toast="t1",
        izvezi_toast="t2",
    )
    body = render_body(custom)
    assert "Custom headline" in body
    assert "<h3 style=\"margin-top:12px\">1 · Ponuda</h3>" in body
    assert "Custom check" in body
    assert "Custom row" in body
    assert '<span class="badge danger">Greška</span>' in body
    assert "Custom intro" in body
    # Defaults must not leak.
    assert "Problem" not in body
    assert "manifest.json" not in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = PregledIzvozFixture(
        campaign_name="<x>",
        content_items=[
            ContentPreviewItem(
                index=1,
                role="<script>x</script>",
                headline="<img onerror=x>",
                status_variant="ok",
                status_label="<b>x</b>",
            ),
        ],
        quality_checks=["<svg>"],
        export_rows=[ExportRow("<i>x</i>", "ok", "<b>x</b>")],
        export_intro="<script>",
        odobri_toast="<svg>",
        izvezi_toast="<svg>",
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

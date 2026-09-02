"""Tests for the Kampanje screen body renderer.

Acceptance for ACS-GUI-002: the campaigns table mirrors the V3
reference (3 rows, same names, same status variants, same planned
counts). Critically — *every* navigation away from this screen lands
on a screen that does not exist yet (Opis / Plan / Studio sadržaja /
Pregled). The "Otvori" affordance and the "+ Nova kampanja" button
must therefore be ``data-action="toast"`` stubs, NOT ``<a href>``
links. A real ``<a href>`` would render as a 404 / dead link in the
pywebview window.
"""

from __future__ import annotations

import dataclasses
import re

from ai_campaign_studio.presentation_webview.screens.kampanje import (
    DEFAULT_FIXTURE,
    Campaign,
    KampanjeFixture,
    render_body,
)


def test_default_fixture_has_three_canonical_campaigns() -> None:
    """V3 reference has exactly 3 rows: Proljetna / Lansiranje / Novi web-sajt."""
    names = [c.name for c in DEFAULT_FIXTURE.campaigns]
    assert names == ["Proljetna kolekcija", "Lansiranje seruma", "Novi web-sajt"]


def test_default_fixture_matches_v3_statuses() -> None:
    by_name = {c.name: c for c in DEFAULT_FIXTURE.campaigns}
    assert by_name["Proljetna kolekcija"].status_variant == "warn"
    assert by_name["Proljetna kolekcija"].status_label == "U pripremi"
    assert by_name["Proljetna kolekcija"].planned_count == 6
    assert by_name["Lansiranje seruma"].status_variant == "info"
    assert by_name["Lansiranje seruma"].status_label == "Planirano"
    assert by_name["Lansiranje seruma"].planned_count == 8
    assert by_name["Novi web-sajt"].status_variant == "ok"
    assert by_name["Novi web-sajt"].status_label == "Odobreno"
    assert by_name["Novi web-sajt"].planned_count == 5


def test_default_fixture_all_brands_are_brightsmile() -> None:
    assert {c.brand for c in DEFAULT_FIXTURE.campaigns} == {"BrightSmile"}


def test_fixtures_are_pure_dataclasses() -> None:
    assert dataclasses.is_dataclass(Campaign)
    assert dataclasses.is_dataclass(KampanjeFixture)
    assert Campaign.__dataclass_params__.frozen is True
    assert KampanjeFixture.__dataclass_params__.frozen is True


def test_render_body_emits_table_with_three_rows() -> None:
    body = render_body()
    # Table headers.
    for header in ("Kampanja", "Brend", "Status", "Planirano", "Zadnja izmjena"):
        assert header in body, f"missing column header: {header!r}"
    # All 3 campaign names.
    for name in ("Proljetna kolekcija", "Lansiranje seruma", "Novi web-sajt"):
        assert name in body
    # All 3 status labels.
    for label in ("U pripremi", "Planirano", "Odobreno"):
        assert label in body
    # Planned counts formatted as "N objava".
    for needle in ("6 objava", "8 objava", "5 objava"):
        assert needle in body, f"missing planned count: {needle!r}"


def test_render_body_uses_v3_table_classes() -> None:
    body = render_body()
    for needle in (
        '<table class="table">',
        "<thead>",
        "<tbody>",
        "right",
        "badge warn",
        "badge info",
        "badge ok",
    ):
        assert needle in body, f"missing V3 class/markup: {needle!r}"


def test_render_body_no_anchor_href_to_nonexistent_screens() -> None:
    """Contract: no ``<a href>`` to the 4 not-yet-built campaign workflow screens.

    The V3 reference had ``<a href="../04_opis_kampanje/index.html">``
    on the first row. In this task that link becomes a
    ``data-action="toast"`` stub on a ``<button>`` — never an
    ``<a href>`` to a page that does not exist in
    ``presentation_webview`` yet.
    """
    body = render_body()
    # No anchors with hrefs at all — every navigation away from this
    # page is a toast stub.
    hrefs = re.findall(r'<a[^>]*\bhref="([^"]+)"', body)
    assert hrefs == [], (
        f"unexpected <a href> in Kampanje body (would 404 in pywebview): {hrefs}"
    )


def test_render_body_otvori_buttons_use_toast_stub() -> None:
    body = render_body()
    # The page renders one "Otvori" per campaign row.
    assert body.count(">Otvori<") == 3
    # Each "Otvori" lives inside a button[data-action="toast"].
    open_buttons = re.findall(
        r'<button class="btn" data-action="toast"[^>]*>Otvori</button>',
        body,
    )
    assert len(open_buttons) == 3, (
        f"expected 3 toast-stub Otvori buttons, got {len(open_buttons)}"
    )


def test_render_body_nova_kampanja_is_toast_stub() -> None:
    body = render_body()
    assert "+ Nova kampanja" in body
    # Primary variant + toast action.
    nova_pattern = (
        r'<button class="btn primary" data-action="toast"[^>]*>'
        r"\+ Nova kampanja</button>"
    )
    assert re.search(nova_pattern, body), (
        '"+ Nova kampanja" must be a primary toast button'
    )


def test_render_body_uses_canonical_bhs_strings() -> None:
    body = render_body()
    for needle in (
        "Kampanje",
        "Kreiraj, nastavi i pregledaj kampanje.",
        "Zadnja izmjena",
    ):
        assert needle in body


def test_changing_fixture_changes_rendered_body() -> None:
    custom = KampanjeFixture(
        campaigns=[
            Campaign(
                name="AAA",
                brand="Brand X",
                status_variant="danger",
                status_label="Blokirano",
                planned_count=1,
                last_modified="Nikad",
            ),
        ],
        new_campaign_toast="Custom toast",
    )
    body = render_body(custom)
    assert "AAA" in body
    assert "Brand X" in body
    assert "Blokirano" in body
    assert "badge danger" in body
    assert "1 objava" in body
    # Default campaigns must not leak.
    assert "Proljetna kolekcija" not in body
    assert "Lansiranje seruma" not in body
    assert "Novi web-sajt" not in body


def test_render_body_escapes_xss_in_fixture() -> None:
    nasty = KampanjeFixture(
        campaigns=[
            Campaign(
                name="<script>x</script>",
                brand="<img>",
                status_variant="info",
                status_label="<b>label</b>",
                planned_count=1,
                last_modified="<svg>",
            ),
        ],
        new_campaign_toast="<x>",
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

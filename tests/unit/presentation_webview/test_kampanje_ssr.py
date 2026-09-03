"""Tests for the Kampanje screen body renderer.

Acceptance for ACS-GUI-002 + ACS-GUI-003: the campaigns table mirrors
the V3 reference (3 rows, same names, same status variants, same planned
counts). As of ACS-GUI-003, "Otvori" is a real ``<a href>`` into the
first campaign-workflow step (``../opis_kampanje/index.html``); only
"+ Nova kampanja" remains a ``data-action="toast"`` stub.
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


def test_render_body_otvori_links_to_opis_kampanje() -> None:
    """ACS-GUI-003: "Otvori" is a real link to the first workflow step.

    Only ``../opis_kampanje/index.html`` (which now exists as a generated
    screen) — no dead hrefs to any other path.
    """
    body = render_body()
    hrefs = re.findall(r'<a[^>]*\bhref="([^"]+)"', body)
    assert hrefs == ["../opis_kampanje/index.html"] * 3, (
        f"unexpected hrefs in Kampanje body: {hrefs}"
    )


def test_render_body_otvori_is_anchor_link() -> None:
    body = render_body()
    # The page renders one "Otvori" per campaign row.
    assert body.count(">Otvori<") == 3
    open_links = re.findall(
        r'<a class="btn" href="../opis_kampanje/index.html">Otvori</a>',
        body,
    )
    assert len(open_links) == 3, (
        f"expected 3 Otvori anchor links, got {len(open_links)}"
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

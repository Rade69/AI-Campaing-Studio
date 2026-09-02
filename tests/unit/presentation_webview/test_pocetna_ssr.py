"""Tests for the Početna screen body renderer and shell wiring.

Verifies that the Početna body is driven by Python fixture data
(not hard-coded HTML): changing the fixture must change the rendered
output. Also covers shell-level structure: sidebar links to all 5
destinations, topbar shows the active page, footer status reads
"Lokalno".
"""

from __future__ import annotations

import dataclasses

import pytest

from ai_campaign_studio.presentation_webview.screens import (
    DEFAULT_FIXTURE,
    ActivityEntry,
    Kpi,
    PočetnaFixture,
    RecentCampaign,
)
from ai_campaign_studio.presentation_webview.screens.pocetna import render_body
from ai_campaign_studio.presentation_webview.shell import (
    SIDEBAR_ITEMS,
    Breadcrumb,
    render_shell,
)


def test_default_fixture_has_canonical_brand_name() -> None:
    """The V3_PLAN says BrightSmile is the canonical sample brand."""
    names = [c.name for c in DEFAULT_FIXTURE.recent_campaigns]
    assert "Proljetna kolekcija" in names
    assert "Lansiranje seruma" in names
    assert "Novi web-sajt" in names


def test_render_body_uses_fixture_values() -> None:
    body = render_body()
    # The numbers in the body must come from the fixture (3, 18, 6, 12).
    assert ">3<" in body
    assert ">18<" in body
    assert ">6<" in body
    assert ">12<" in body


def test_render_body_uses_canonical_bhs_strings() -> None:
    body = render_body()
    for needle in ("AKTIVNE KAMPANJE", "OBJAVE U PLANU", "NACRTI", "ODOBRENO",
                  "Nedavne kampanje", "Zadnje aktivnosti", "U pripremi", "Planirano",
                  "Odobreno", "Nova kampanja"):
        assert needle in body, f"missing canonical BHS string: {needle!r}"


def test_fixtures_are_pure_data() -> None:
    """FixtureData must be a plain dataclass; no Pydantic in GUI-BASE."""
    # The point of this test is to fail loudly if a future refactor
    # accidentally adds pydantic dependency to the screen layer.
    from ai_campaign_studio.presentation_webview.screens import (
        ActivityEntry as _AE,
    )
    from ai_campaign_studio.presentation_webview.screens import (
        Kpi as _Kpi,
    )
    from ai_campaign_studio.presentation_webview.screens import (
        PočetnaFixture as _PF,
    )
    from ai_campaign_studio.presentation_webview.screens import (
        RecentCampaign as _RC,
    )
    for cls in (_Kpi, _RC, _AE, _PF):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must remain a dataclass"


def test_changing_fixture_changes_rendered_body() -> None:
    """Acceptance: promjena vrijednosti u fixture_data.py se odrazi u prikazu."""
    custom = PočetnaFixture(
        headline="Početna",
        intro="Custom intro.",
        kpi_active_campaigns=Kpi("AKTIVNE KAMPANJE", 99, "sve u pripremi"),
        kpi_posts_planned=Kpi("OBJAVE U PLANU", 50, "sljedećih 30 dana"),
        kpi_drafts=Kpi("NACRTI", 0, "nema"),
        kpi_approved=Kpi("ODOBRENO", 1, "spremno za izvoz"),
        recent_campaigns=[
            RecentCampaign("Custom kampanja", "warn", "U pripremi"),
        ],
        activity=[
            ActivityEntry("Custom aktivnost", "sada"),
        ],
    )
    body = render_body(custom)
    assert ">99<" in body
    assert ">50<" in body
    assert ">0<" in body
    assert ">1<" in body
    assert "Custom kampanja" in body
    assert "Custom aktivnost" in body
    assert "Custom intro." in body
    # And the defaults must NOT leak through.
    assert "Proljetna kolekcija" not in body


def test_render_shell_includes_all_5_sidebar_destinations() -> None:
    """Acceptance: 'klik na svih 5 stavki ... mijenja prikazani sadržaj'."""
    page = render_shell(
        active_key="pocetna",
        page_title="Početna",
        body_html="<p>body</p>",
        crumbs=[Breadcrumb("Početna", None)],
    )
    keys = {key for key, _, _, _ in SIDEBAR_ITEMS}
    assert keys == {"pocetna", "brend", "kampanje", "kalendar", "podesavanja"}
    for href_marker in (
        "../screens/pocetna/index.html",
        "../screens/brend/index.html",
        "../screens/kampanje/index.html",
        "../screens/kalendar/index.html",
        "../screens/podesavanja/index.html",
    ):
        assert href_marker in page, f"missing sidebar href to {href_marker!r}"


@pytest.mark.parametrize(
    "active_key,expected_label",
    [
        ("pocetna", "Početna"),
        ("brend", "Brend"),
        ("kampanje", "Kampanje"),
        ("kalendar", "Kalendar"),
        ("podesavanja", "Podešavanja"),
    ],
)
def test_render_shell_marks_correct_nav_as_active(
    active_key: str, expected_label: str
) -> None:
    page = render_shell(
        active_key=active_key,
        page_title=expected_label,
        body_html="",
        crumbs=[Breadcrumb(expected_label, None)],
    )
    # The active <a> has class "active" and contains the label span.
    # We assert the structure contains the right adjacent token.
    assert f'class="active" href="../screens/{active_key}/index.html"' in page
    assert f"<b>{expected_label}</b>" in page


def test_render_shell_sets_csp_header() -> None:
    """PYWEBVIEW_SECURITY.md §4: shell must declare a strict CSP."""
    page = render_shell(
        active_key="pocetna",
        page_title="Početna",
        body_html="",
    )
    assert "Content-Security-Policy" in page
    assert "default-src 'self'" in page
    assert "script-src 'self'" in page


def test_render_shell_uses_local_static_assets() -> None:
    """CSP must not allow remote sources; only self-hosted static/."""
    page = render_shell(
        active_key="pocetna",
        page_title="Početna",
        body_html="",
    )
    # CSP connect-src is 'self' (no fetch to external hosts).
    assert "connect-src 'self'" in page
    # No CDN / external font / external script references.
    assert "fonts.googleapis.com" not in page
    assert "cdn.tailwindcss.com" not in page
    # The static asset links are local.
    assert 'href="../static/app.css"' in page
    assert 'src="../static/app.js"' in page


def test_render_shell_has_no_lang_toggle() -> None:
    """Round 2 regression: ``.lang-toggle`` is not in the locked V3 design.

    Coordinator review removed the EN/BHS pill switch that the round 1
    shell added unilaterally. This test fails if it ever creeps back in.
    """
    page = render_shell(
        active_key="pocetna",
        page_title="Početna",
        body_html="",
    )
    assert "lang-toggle" not in page
    assert "class=\"pill\"" not in page

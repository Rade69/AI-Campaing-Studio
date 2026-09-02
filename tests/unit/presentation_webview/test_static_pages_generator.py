"""Tests for the static-pages generator.

Verifies that :func:`presentation_webview.screens.write_all_pages`
materialises every sidebar screen through the shared shell — i.e. the
4 placeholder screens (Brend / Kampanje / Kalendar / Podešavanja) do
NOT duplicate the shell markup; they all go through
:func:`presentation_webview.shell.render_shell`. This is the DRY
acceptance gate for ACS-GUI-001 round 2.
"""
from __future__ import annotations

import re
from pathlib import Path

from ai_campaign_studio.presentation_webview.screens import write_all_pages
from ai_campaign_studio.presentation_webview.shell import SIDEBAR_ITEMS


def _active_a(html: str) -> str:
    """Return the screen key of the active <a class="active"> in the sidebar."""
    m = re.search(r'class="active" href="\.\./screens/(\w+)/index\.html"', html)
    assert m is not None, "no active sidebar link found in page"
    return m.group(1)


def test_write_all_pages_creates_one_file_per_sidebar_item(tmp_path: Path) -> None:
    pages = write_all_pages(tmp_path)
    assert set(pages) == {key for key, *_ in SIDEBAR_ITEMS}
    for key, path in pages.items():
        assert path.exists(), f"{key} file missing: {path}"
        assert path.parent == tmp_path / "screens" / key
        assert path.name == "index.html"


def test_write_all_pages_mark_correct_active_per_screen(tmp_path: Path) -> None:
    pages = write_all_pages(tmp_path)
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        assert _active_a(html) == key, (
            f"active sidebar mismatch for {key!r}: page has "
            f"{_active_a(html)!r} as active"
        )


def test_write_all_pages_share_one_csp_and_one_static_link(tmp_path: Path) -> None:
    """Every screen must carry the SAME CSP, CSS link, and JS link.

    This is the DRY assertion: if any screen re-implements the shell,
    its CSP / asset links will diverge from the others.
    """
    pages = write_all_pages(tmp_path)
    csps = set()
    css_links = set()
    js_links = set()
    for path in pages.values():
        html = path.read_text(encoding="utf-8")
        csp_m = re.search(r'Content-Security-Policy" content="([^"]+)"', html)
        css_m = re.search(r'href="(\.\./static/app\.css)"', html)
        js_m = re.search(r'src="(\.\./static/app\.js)"', html)
        csps.add(csp_m.group(1))
        css_links.add(css_m.group(1))
        js_links.add(js_m.group(1))
    assert len(csps) == 1, f"CSP diverges across screens: {csps}"
    assert len(css_links) == 1, f"CSS link diverges: {css_links}"
    assert len(js_links) == 1, f"JS link diverges: {js_links}"


def test_write_all_pages_have_no_lang_toggle(tmp_path: Path) -> None:
    """Round 2 fix: ``.lang-toggle`` is not in the locked V3 design.

    No screen, including Početna, may render the EN/BHS pill switch.
    """
    pages = write_all_pages(tmp_path)
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        assert "lang-toggle" not in html, (
            f"{key} page still renders .lang-toggle (regression)"
        )


def test_write_all_pages_emit_no_remote_assets(tmp_path: Path) -> None:
    """CSP says default-src 'self' — no Google Fonts, no CDN, nothing."""
    pages = write_all_pages(tmp_path)
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        for forbidden in (
            "fonts.googleapis.com",
            "fonts.gstatic.com",
            "cdn.tailwindcss.com",
            "unpkg.com",
        ):
            assert forbidden not in html, (
                f"{key} page references remote asset: {forbidden}"
            )


def test_write_all_pages_pocetna_carries_fixture_data(tmp_path: Path) -> None:
    """Početna body is fixture-driven; the values must appear in the file."""
    pages = write_all_pages(tmp_path)
    pocetna = pages["pocetna"].read_text(encoding="utf-8")
    for needle in (
        "AKTIVNE KAMPANJE",
        "OBJAVE U PLANU",
        "NACRTI",
        "ODOBRENO",
        "Proljetna kolekcija",
        "Plan kampanje",
    ):
        assert needle in pocetna, f"Početna missing fixture string: {needle!r}"


def test_write_all_pages_placeholder_screens_carry_only_their_label(
    tmp_path: Path,
) -> None:
    """Each placeholder shows its own h2 + 'ACS-GUI-002' notice — no shell drift."""
    pages = write_all_pages(tmp_path)
    expectations = {
        "brend": "Brend",
        "kampanje": "Kampanje",
        "kalendar": "Kalendar",
        "podesavanja": "Podešavanja",
    }
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        if key == "pocetna":
            continue
        assert f"<h2>{expectations[key]}</h2>" in html, (
            f"{key} page missing h2 label"
        )
        assert "ACS-GUI-002" in html, (
            f"{key} page missing ACS-GUI-002 pointer"
        )

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
from urllib.parse import urljoin, urlsplit
from urllib.request import url2pathname

from ai_campaign_studio.presentation_webview.screens import write_all_pages
from ai_campaign_studio.presentation_webview.screens._static_pages import (
    WORKFLOW_ITEMS,
)
from ai_campaign_studio.presentation_webview.shell import SIDEBAR_ITEMS


def _hrefs_and_srcs(html: str) -> list[str]:
    return re.findall(r'(?:href|src)="([^"]+)"', html)


def test_write_all_pages_relative_links_resolve_to_real_files(
    tmp_path: Path,
) -> None:
    """Every relative href/src in every generated page must resolve to a
    file that actually exists on disk, from the page's own location --
    not just be a plausible-looking string.

    This is the exact class of bug that slipped through round 1 and round
    2 review: render_shell()'s CSS/JS links and SIDEBAR_ITEMS' nav links
    were both written assuming pages live one directory level shallower
    than write_all_pages() actually places them
    (target_dir/screens/{key}/index.html), so every relative link was off
    by one ".." segment. String-only assertions like
    'href="../static/app.css" in page' passed even though the browser
    could never find the file. Resolving against the real filesystem, as
    this test does, is the only way to catch that class of bug.
    """
    pages = write_all_pages(tmp_path)
    checked = 0
    for key, page_path in pages.items():
        html = page_path.read_text(encoding="utf-8")
        base_uri = page_path.resolve().as_uri()
        for link in _hrefs_and_srcs(html):
            if link.startswith("#") or "://" in link:
                continue  # in-page anchors / any future absolute URL
            resolved_uri = urljoin(base_uri, link)
            # A ``?campaign=...`` query param changes the page state, not the
            # file path — resolve only the path portion against the disk.
            resolved_path = Path(url2pathname(urlsplit(resolved_uri).path))
            assert resolved_path.is_file(), (
                f"{key} page ({page_path}) links {link!r}, which resolves "
                f"to {resolved_path}, but that file does not exist"
            )
            checked += 1
    assert checked >= len(pages) * 2, "expected at least CSS+JS link per page"


def test_write_all_pages_materialises_static_assets_on_disk(tmp_path: Path) -> None:
    """Regression: generated pages link static assets relative
    to screens/{key}/index.html -- those files must actually exist in
    target_dir/static/, not just be referenced by path in the HTML string.
    A prior version only asserted the href/src text and missed that the
    files were never copied, so pywebview rendered bare, unstyled HTML.
    """
    write_all_pages(tmp_path)
    css_path = tmp_path / "static" / "app.css"
    js_path = tmp_path / "static" / "app.js"
    logo_path = tmp_path / "static" / "brand-logo.png"
    assert css_path.is_file(), f"missing {css_path}"
    assert js_path.is_file(), f"missing {js_path}"
    assert logo_path.is_file(), f"missing {logo_path}"
    assert css_path.stat().st_size > 0
    assert js_path.stat().st_size > 0
    assert logo_path.stat().st_size > 0


def test_write_all_pages_use_canonical_logo_asset(tmp_path: Path) -> None:
    """Sidebar brand must render the canonical PNG logo, not text recreation."""
    pages = write_all_pages(tmp_path)
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        assert '<img class="brand-logo" src="../../static/brand-logo.png"' in html
        assert "<h1>AI Campaign Studio</h1>" not in html, (
            f"{key} page still renders text instead of the canonical logo asset"
        )


def _active_a(html: str) -> str:
    """Return the screen key of the active <a class="active"> in the sidebar."""
    m = re.search(r'class="active" href="\.\./(\w+)/index\.html"', html)
    assert m is not None, "no active sidebar link found in page"
    return m.group(1)


def test_write_all_pages_creates_one_file_per_screen(tmp_path: Path) -> None:
    pages = write_all_pages(tmp_path)
    expected = {key for key, *_ in SIDEBAR_ITEMS} | {
        key for key, _ in WORKFLOW_ITEMS
    }
    assert set(pages) == expected
    assert len(pages) == 9, (
        f"expected 9 screens (5 sidebar + 4 workflow), got {len(pages)}"
    )
    for key, path in pages.items():
        assert path.exists(), f"{key} file missing: {path}"
        assert path.parent == tmp_path / "screens" / key
        assert path.name == "index.html"


def test_write_all_pages_mark_correct_active_per_screen(tmp_path: Path) -> None:
    pages = write_all_pages(tmp_path)
    workflow_keys = {key for key, _ in WORKFLOW_ITEMS}
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        expected_active = "kampanje" if key in workflow_keys else key
        assert _active_a(html) == expected_active, (
            f"active sidebar mismatch for {key!r}: page has "
            f"{_active_a(html)!r} as active, expected {expected_active!r}"
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
        css_m = re.search(r'href="(\.\./\.\./static/app\.css)"', html)
        js_m = re.search(r'src="(\.\./\.\./static/app\.js)"', html)
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


def test_write_all_pages_screens_carry_real_content(tmp_path: Path) -> None:
    """Each screen shows its own h2 + real fixture-driven content (ACS-GUI-002).

    Superseded the earlier placeholder-only assertion once Brend/Kampanje/
    Kalendar/Podešavanja got their real ``render_body()`` implementations —
    no shell drift, and no screen regresses back to a bare placeholder.
    """
    pages = write_all_pages(tmp_path)
    expectations = {
        "brend": ("Brend", "BrightSmile Oral Care"),
        "kampanje": ("Kampanje", "Proljetna kolekcija"),
        "kalendar": ("Kalendar", "queue/retry"),
        "podesavanja": ("Podešavanja", "AI provajderi"),
        "opis_kampanje": ("Opis kampanje", "Generisanje interesovanja i upita"),
        "plan_kampanje": ("Plan kampanje", "Najčešća frustracija korisnika"),
        "studio_sadrzaja": ("Studio sadržaja", "Uredi sadržaj"),
        "pregled_izvoz": ("Pregled i izvoz", "Izvezi ZIP paket"),
    }
    for key, path in pages.items():
        html = path.read_text(encoding="utf-8")
        if key == "pocetna":
            continue
        h2_label, content_needle = expectations[key]
        assert f"<h2>{h2_label}</h2>" in html, f"{key} page missing h2 label"
        assert content_needle in html, (
            f"{key} page missing real content: {content_needle!r}"
        )

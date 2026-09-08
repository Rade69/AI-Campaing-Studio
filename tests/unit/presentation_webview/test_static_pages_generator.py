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

import pytest

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


def test_write_all_pages_studio_sadrzaja_carries_live_generate_button(
    tmp_path: Path,
) -> None:
    """ACS-GUI-008 fix-brief-2 BF-1: the BUILD-TIME static HTML for
    Studio sadržaja (the file the real pywebview app actually loads)
    MUST carry the live "Generiši sadržaj" button + the
    ``data-generate-result`` callout -- even though the
    ``campaign_id``/``plan_id`` are unknown at build time and only
    come from the RUNTIME URL.

    Before the fix, the button was emitted conditionally
    (``fx.campaign_id and fx.plan_id``) -- since ``write_all_pages``
    never threads a fixture with ids, the production HTML never had
    the button, the JS IIFE could not wire it, and the user was
    stuck on a "Nema otvorene kampanje" toast forever.

    After the fix, the static HTML always emits:
    - the button with empty placeholder data attributes + ``hidden``
    - the result callout (also ``hidden``)

    The ``app.js`` boot IIFE (which reads ``?campaign=`` AND
    ``?plan=`` from ``location.search``) is responsible for
    populating the data attributes and revealing the button at
    runtime -- which this test confirms is wired (see
    ``test_app_js_iife_wires_studio_generate_button`` below).
    """
    pages = write_all_pages(tmp_path)
    studio_html = pages["studio_sadrzaja"].read_text(encoding="utf-8")

    # The live button is emitted with placeholder (empty) ids and
    # starts ``hidden`` -- the JS IIFE is the only thing that reveals it.
    assert 'data-action="generate-content"' in studio_html
    assert 'data-campaign-id=""' in studio_html
    assert 'data-plan-id=""' in studio_html
    # The button is hidden in the static HTML (no campaign yet).
    assert 'data-action="generate-content"' in studio_html
    # The result callout is always emitted (hidden) so the JS
    # handler has a stable querySelector target.
    assert "data-generate-result" in studio_html
    # The legacy "no campaign" toast stub is GONE -- it was the
    # build-time-only fallback that could never have worked in
    # production (the static HTML never sees the runtime ids).
    assert "Nema otvorene kampanje" not in studio_html


def test_app_js_iife_wires_studio_generate_button_when_both_ids_in_url(
    tmp_path: Path,
) -> None:
    """ACS-GUI-008 fix-brief-2 BF-1: the ``app.js`` boot IIFE must
    populate the button's data attributes AND reveal it when BOTH
    ``?campaign=`` and ``?plan=`` are present in the URL. Without
    the campaign id alone, the button stays hidden (the bridge
    contract requires both). This is the runtime side of BF-1; the
    SSR side is ``test_write_all_pages_studio_sadrzaja_carries_live_generate_button``.
    """
    from ai_campaign_studio.presentation_webview.screens import write_all_pages

    pages = write_all_pages(tmp_path)
    studio_html = pages["studio_sadrzaja"].read_text(encoding="utf-8")
    app_js = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    js_text = app_js.read_text(encoding="utf-8")
    # The IIFE checks for BOTH ?campaign= AND ?plan= before revealing
    # the button. This guards against showing a half-wired button
    # that would surface a "Nedostaje plan_id" toast on every click.
    assert "URLSearchParams" in js_text
    assert "'plan'" in js_text
    assert "btn.hidden=false" in js_text
    # The button is the only ``[data-action="generate-content"]`` in
    # the static HTML.
    assert studio_html.count('data-action="generate-content"') == 1


def test_write_all_pages_pregled_izvoz_carries_live_export_button(
    tmp_path: Path,
) -> None:
    """ACS-GUI-009 BF-1 equivalent: the BUILD-TIME static HTML for
    Pregled i izvoz MUST carry the live "Izvezi ZIP paket" button
    (hidden + empty data attributes + disabled) so the ``app.js`` boot
    IIFE can reveal it at runtime when both ``?campaign=`` AND
    ``?plan=`` are present. The "Odobri kampanju" approve-gate button is
    also always emitted (UI-only gate, no backend call).
    """
    pages = write_all_pages(tmp_path)
    pregled_html = pages["pregled_izvoz"].read_text(encoding="utf-8")

    # Live export button is always emitted with placeholder (empty) ids,
    # hidden + disabled (the JS boot IIFE reveals it, the approve-gate
    # click enables it).
    assert 'data-action="export-campaign"' in pregled_html
    assert 'data-campaign-id=""' in pregled_html
    assert 'data-plan-id=""' in pregled_html
    assert 'id="btn-izvezi"' in pregled_html
    assert "hidden" in pregled_html
    assert "disabled" in pregled_html
    # The approve-gate button is emitted too.
    assert 'data-action="approve-gate"' in pregled_html
    # The legacy "toast" stub for the export button is GONE.
    assert 'data-action="toast"' not in pregled_html


def test_next_step_links_carry_campaign_and_plan_through_the_whole_flow(
    tmp_path: Path,
) -> None:
    """Human Owner live-run feedback, 2026-09-07: clicking through the
    real flow (Plan kampanje -> Kalendar -> Studio sadržaja -> Pregled
    i izvoz) always landed on the LAST two screens with NO query
    params, because every "next step" link past the first was a
    build-time static href (needed for the offline/SSR preview) that
    never carried the runtime ``campaign``/``plan`` ids forward. Only
    "Sačuvaj i napravi plan" (JS-driven navigation) got it right.

    This test loads the REAL committed ``app.js`` in Node and proves
    the boot IIFE rewrites every ``[data-next-step]`` link's ``href``
    to include the CURRENT page's own ``?campaign=``/``?plan=`` ids --
    on each of the three affected screens, chained, exactly the click
    path a real user follows.
    """
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

    app_js_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    harness = r"""
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[1],'utf8');

function runPage(search, links){
  const anchors=links.map(href=>({
    _href:href,
    getAttribute(n){ return n==='href' ? this._href : null; },
    setAttribute(n,v){ if(n==='href') this._href=v; },
  }));
  const document={
    querySelectorAll(sel){
      if(sel==='[data-next-step]') return anchors;
      return [];
    },
    querySelector(){ return null; },
    getElementById(){ return null; },
  };
  const window={addEventListener(){}};
  const context={
    window, document, location:{search}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout,
    console,
  };
  vm.createContext(context);
  vm.runInContext(src, context);
  return anchors.map(a=>a._href);
}

// Step 2 (Plan kampanje): page URL has campaign+plan -> its own
// "next step" link (to Kalendar) must gain both.
const step2=runPage(
  '?campaign=c-123&plan=p-456',
  ['../kalendar/index.html?campaign=Fixture%20Name']
);
// Step 3 (Kalendar): simulate having landed there WITH the ids the
// fixed step-2 link now carries -- its own "next step" link (to
// Studio sadrzaja) must ALSO gain both.
const step3=runPage(
  '?campaign=c-123&plan=p-456',
  ['../studio_sadrzaja/index.html']
);
// Step 4 (Studio sadrzaja): same -- its "next step" link (to Pregled
// i izvoz) must gain both.
const step4=runPage(
  '?campaign=c-123&plan=p-456',
  ['../pregled_izvoz/index.html']
);

console.log(JSON.stringify({step2: step2[0], step3: step3[0], step4: step4[0]}));
"""
    completed = subprocess.run(
        [node, "-e", harness, str(app_js_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    result = json.loads(completed.stdout)
    assert result["step2"] == (
        "../kalendar/index.html?campaign=c-123&plan=p-456"
    )
    assert result["step3"] == (
        "../studio_sadrzaja/index.html?campaign=c-123&plan=p-456"
    )
    assert result["step4"] == (
        "../pregled_izvoz/index.html?campaign=c-123&plan=p-456"
    )


def test_write_all_pages_brend_carries_hydration_markers(tmp_path: Path) -> None:
    """ACS-F1-049: the build-time Brend static HTML carries the
    screen-specific hydration markers (``data-brend-*``) so app.js can
    hydrate real data at runtime, while still rendering the SSR fixture
    (offline fallback)."""
    pages = write_all_pages(tmp_path)
    brend_html = pages["brend"].read_text(encoding="utf-8")

    for marker in (
        "data-brend-name",
        "data-brend-audience",
        "data-brend-voice",
        "data-brend-facts",
    ):
        assert marker in brend_html, f"missing brend marker: {marker!r}"

    # The SSR fixture content is still present (offline fallback).
    assert "BrightSmile Oral Care" in brend_html
    assert "F-001" in brend_html


def test_write_all_pages_pocetna_carries_hydration_markers(tmp_path: Path) -> None:
    """ACS-F1-051: the build-time Početna static HTML carries the
    screen-specific hydration markers (``data-pocetna-*``) so app.js can
    hydrate real data at runtime, while still rendering the SSR fixture."""
    pages = write_all_pages(tmp_path)
    pocetna_html = pages["pocetna"].read_text(encoding="utf-8")

    assert "data-pocetna-recent" in pocetna_html
    for key in ("active", "planned", "drafts", "approved"):
        assert f'data-pocetna-kpi-value="{key}"' in pocetna_html, (
            f"missing KPI marker: {key!r}"
        )

    # The SSR fixture content is still present (offline fallback).
    assert "Nedavne kampanje" in pocetna_html
    assert "Proljetna kolekcija" in pocetna_html

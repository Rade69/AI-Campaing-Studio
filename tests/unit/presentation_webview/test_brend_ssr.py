"""Tests for the Brend screen body renderer.

Mirrors the ACS-GUI-001 ``test_pocetna_ssr.py`` pattern: the body
must be driven by the supplied fixture (changing fixture values must
change the rendered output), all fixture-derived text must round-trip
through ``html.escape``, and the markup must use the V3 CSS classes
(``.tabs``/``.tab``/``.fact``/``.card``/``.section-title``/``.grid``
``.badge``).
"""

from __future__ import annotations

import dataclasses

from ai_campaign_studio.presentation_webview.screens.brend import (
    DEFAULT_FIXTURE,
    ApprovedFact,
    BrandInfo,
    BrandResource,
    BrendFixture,
    VoiceBadge,
    render_body,
)


def test_default_fixture_uses_canonical_brightsmile_brand() -> None:
    """V3_PLAN canonical demo brand = BrightSmile Oral Care."""
    assert DEFAULT_FIXTURE.brand.name == "BrightSmile Oral Care"
    assert DEFAULT_FIXTURE.status_checked is True


def test_default_fixture_has_canonical_facts() -> None:
    codes = [f.code for f in DEFAULT_FIXTURE.facts]
    assert codes == ["F-001", "F-002", "F-003"]
    assert any("alkohol" in f.text for f in DEFAULT_FIXTURE.facts)


def test_default_fixture_has_three_voice_badges() -> None:
    variants = [b.variant for b in DEFAULT_FIXTURE.brand.voice]
    labels = [b.label for b in DEFAULT_FIXTURE.brand.voice]
    assert "info" in variants
    assert "gray" in variants
    assert "Jasan" in labels
    assert "Pouzdan" in labels
    assert "Nenametljiv" in labels


def test_fixtures_are_pure_dataclasses() -> None:
    """No Pydantic in the screen layer; ``frozen=True`` dataclasses only."""
    for cls in (VoiceBadge, BrandInfo, ApprovedFact, BrandResource, BrendFixture):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        if cls is not VoiceBadge:
            assert cls.__dataclass_params__.frozen is True, (
                f"{cls.__name__} must be frozen"
            )


def test_render_body_uses_fixture_values() -> None:
    body = render_body()
    # Brand name appears (HTML-escaped, not raw).
    assert "BrightSmile Oral Care" in body
    # 3 tabs.
    tab_labels = (
        "Osnovni podaci",
        "Odobrene činjenice",
        "Glas brenda",
        "Brend resursi",
    )
    for label in tab_labels:
        assert label in body, f"missing tab label: {label!r}"
    # All 3 fact codes.
    for code in ("F-001", "F-002", "F-003"):
        assert code in body
    # All 3 resource cards.
    for title in ("Logo", "Paleta boja", "Izvori"):
        assert title in body


def test_render_body_uses_canonical_bhs_strings() -> None:
    body = render_body()
    for needle in (
        "Brend",
        "Provjereno i ažurno",
        "Posljednja provjera",
        "Odobrene činjenice",
        "Brend resursi",
        "Primarna publika",
        "Glas brenda",
    ):
        assert needle in body, f"missing BHS string: {needle!r}"


def test_changing_fixture_changes_rendered_body() -> None:
    """Acceptance: fixture change must be reflected in the rendered body."""
    custom = BrendFixture(
        status_checked=False,
        brand=BrandInfo(
            name="Custom Brand",
            description="Custom description",
            primary_audience="Custom audience",
            voice=[VoiceBadge("Brutalan", "danger")],
            last_check_label="1. 1. 2099.",
        ),
        facts=[ApprovedFact("X-999", "Custom fact text")],
        resources=[BrandResource("Ikonica", "PNG")],
        refresh_message="Custom refresh",
    )
    body = render_body(custom)
    assert "Custom Brand" in body
    assert "Custom description" in body
    assert "Custom audience" in body
    assert "Brutalan" in body
    assert "X-999" in body
    assert "Custom fact text" in body
    assert "Ikonica" in body
    # Defaults must NOT leak through.
    assert "BrightSmile" not in body
    assert "F-001" not in body


def test_render_body_uses_v3_css_classes() -> None:
    body = render_body()
    for cls in (
        "tabs",
        "tab active",
        "card",
        "fact",
        "section-title",
        "grid g3",
        "statusline",
        "badge info",
        "badge gray",
        "brand-status",
        "tick",
        "field",
        "callout",
        "actions",
    ):
        assert cls in body, f"missing V3 class in body: {cls!r}"
    # ACS-GUI-004: tab/panel structure
    for marker in (
        'data-tabs',
        'data-tab-panel',
        'id="panel-osnovni"',
        'id="panel-cinjenice"',
        'id="panel-glas"',
        'id="panel-resursi"',
    ):
        assert marker in body, f"missing ACS-GUI-004 marker: {marker!r}"


def test_all_four_tabs_have_data_tab_target() -> None:
    """Every tab label carries the matching panel id in data-tab-target."""
    body = render_body()
    for panel_id in (
        "panel-osnovni",
        "panel-cinjenice",
        "panel-glas",
        "panel-resursi",
    ):
        assert f'data-tab-target="{panel_id}"' in body, (
            f"missing data-tab-target for {panel_id!r}"
        )


def test_only_default_active_panel_is_visible() -> None:
    """The default-active panel (panel-osnovni) has no ``hidden`` attr.

    All other panels (``panel-cinjenice``, ``panel-glas``,
    ``panel-resursi``) MUST carry the ``hidden`` attribute so the JS
    starts with exactly one panel visible.
    """
    import re
    body = render_body()
    # Regex: capture the full opening <div ...> of each data-tab-panel
    panel_open_re = re.compile(
        r'<div\b[^>]*data-tab-panel[^>]*id="(panel-[a-z]+)"([^>]*)>'
    )
    panels = {pid: attrs for pid, attrs in panel_open_re.findall(body)}
    assert set(panels) == {
        "panel-osnovni",
        "panel-cinjenice",
        "panel-glas",
        "panel-resursi",
    }, f"unexpected panel ids: {set(panels)}"
    assert "hidden" not in panels["panel-osnovni"], (
        f"panel-osnovni is default-active; attrs: {panels['panel-osnovni']!r}"
    )
    for pid in ("panel-cinjenice", "panel-glas", "panel-resursi"):
        assert "hidden" in panels[pid], (
            f"{pid} should start hidden; attrs: {panels[pid]!r}"
        )


def test_first_tab_is_default_active() -> None:
    """Only the first tab (``Osnovni podaci``) starts with ``active`` class."""
    body = render_body()
    active_open = (
        '<div class="tab active" data-action="tab" '
        'data-tab-target="panel-osnovni">'
    )
    assert active_open in body
    for label in ("Odobrene činjenice", "Glas brenda", "Brend resursi"):
        idx = body.find(label)
        assert idx > 0
        # Look back to nearest <div class="tab" ... opener
        prefix = body[:idx].rsplit("<div", 1)[-1]
        assert "active" not in prefix, (
            f"only the first tab should be active, but {label!r} also is: "
            f"{prefix!r}"
        )


def test_render_body_escapes_xss_in_fixture() -> None:
    """``html.escape`` discipline: arbitrary fixture text must be escaped."""
    nasty = BrendFixture(
        status_checked=True,
        brand=BrandInfo(
            name="<script>alert(1)</script>",
            description="<img onerror=x>",
            primary_audience="<b>x</b>",
            voice=[VoiceBadge("<i>x</i>", "info")],
            last_check_label="<svg>",
        ),
        facts=[ApprovedFact("F-1", "<x>")],
        resources=[BrandResource("<a>", "<hr>")],
        refresh_message="\"quoted\" & <angled>",
    )
    body = render_body(nasty)
    assert "<script>" not in body
    assert "<img onerror" not in body
    assert "<svg>" not in body
    # Quoted/angled payload is escaped but the text characters remain readable.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_render_body_emits_no_remote_assets() -> None:
    body = render_body()
    for forbidden in (
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.tailwindcss.com",
        "unpkg.com",
    ):
        assert forbidden not in body, f"body references remote asset: {forbidden}"


def test_render_body_refresh_uses_toast_stub() -> None:
    """The 'Osvježi podatke' button must be a toast stub, not a real link."""
    body = render_body()
    assert "Osvježi podatke" in body
    # The button has data-action="toast" (no <a href>).
    assert 'data-action="toast"' in body
    # The refresh message from the fixture should appear (escaped).
    assert "Kasnije: pokreni ingestion/review tok." in body


def test_render_body_emits_brand_hydration_markers() -> None:
    """ACS-F1-049: the SSR emits the screen-specific markers that app.js
    targets for real-data hydration (never a generic selector)."""
    body = render_body()
    for marker in (
        'data-brend-name',
        'data-brend-audience',
        'data-brend-voice',
        'data-brend-facts',
    ):
        assert marker in body, f"missing hydration marker: {marker!r}"


def test_app_js_has_brand_hydration_with_escape_and_lifecycle() -> None:
    """ACS-F1-049: app.js hydrates the Brend screen via a screen-specific
    marker, escapes interpolated values, and uses the immediate fast path +
    ``pywebviewready`` fallback (NOT an unconditional call at parse time)."""
    from pathlib import Path

    app_js = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    js_text = app_js.read_text(encoding="utf-8")

    # Screen-specific marker (never a generic selector like table.card).
    assert "data-brend-name" in js_text
    assert "data-brend-audience" in js_text
    assert "data-brend-voice" in js_text
    assert "data-brend-facts" in js_text

    # escapeHtml maps the dangerous chars and is used on interpolated values.
    assert "escapeHtml" in js_text
    assert "&lt;" in js_text and "&gt;" in js_text and "&amp;" in js_text
    assert "escapeHtml(f.code)" in js_text
    assert "escapeHtml(f.text)" in js_text
    assert "escapeHtml(v)" in js_text

    # Read bridge method wired + lifecycle pattern (fast path + pywebviewready).
    assert "get_brand_overview" in js_text
    assert "pywebviewready" in js_text
    assert "loadBrandOverview" in js_text


def test_app_js_brand_hydration_lifecycle_isolation_and_xss() -> None:
    """Execute the committed shared JS against a tiny DOM double.

    Regression coverage for the Codex ACS-F1-046 BF-1/BF-2 precedents,
    applied to Brend from the first version:

    - late pywebview injection hydrates on ``pywebviewready`` EXACTLY once;
    - the immediate fast path hydrates when the API is already present;
    - a non-Brend screen (no ``data-brend-*`` marker) is never touched and the
      bridge method is never called;
    - name/audience go through ``textContent`` (XSS-safe) while voice/fact
      code/fact text go through ``escapeHtml``.

    The assertions fail on all three bad variants Codex described: (1) an
    unconditional call at parse time, (2) a generic selector that reaches a
    foreign screen, (3) raw ``innerHTML`` interpolation without escaping.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

    from pathlib import Path

    app_js_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    harness = r"""
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[1],'utf8');
function el(initial){
  return {
    _text:initial, _html:initial,
    set textContent(v){this._text=v;}, get textContent(){return this._text;},
    set innerHTML(v){this._html=v;}, get innerHTML(){return this._html;}
  };
}
function baseDocument(querySelector){
  return {
    querySelectorAll(){return [];},
    querySelector,
    getElementById(){return null;}
  };
}
function baseWindow(){
  const listeners={};
  return {listeners, window:{addEventListener(n,f){(listeners[n]??=[]).push(f);}}};
}
function brendContext(withApi){
  const {listeners,window}=baseWindow();
  const state={apiCalls:0};
  const nameEl=el('SSR NAME'), audienceEl=el('SSR AUDIENCE'),
        voiceEl=el('SSR VOICE'), factsEl=el('SSR FACTS');
  const document=baseDocument(function(s){
    if(s==='[data-brend-name]') return nameEl;
    if(s==='[data-brend-audience]') return audienceEl;
    if(s==='[data-brend-voice]') return voiceEl;
    if(s==='[data-brend-facts]') return factsEl;
    return null;
  });
  const installApi=()=>{window.pywebview={api:{async get_brand_overview(){
    state.apiCalls+=1;
    return {ok:true,
      brand_name:'<img>',
      primary_audience:'<script>',
      voice:['<b>warm</b>','friendly'],
      facts:[{code:'<i>F-1</i>', text:'<svg>'}]};
  }}};};
  if(withApi) installApi();
  const context={window, document, location:{search:''}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, listeners, state, installApi, nameEl, audienceEl, voiceEl, factsEl};
}
function foreignContext(withApi){
  const {listeners,window}=baseWindow();
  const state={apiCalls:0};
  // A foreign screen has a generic <h3> (which a bad generic selector would
  // hit) but NO data-brend-* marker.
  const h3=el('FOREIGN H3');
  const document=baseDocument(function(s){
    if(s==='[data-brend-name]') return null;
    if(s==='h3') return h3;
    return null;
  });
  const installApi=()=>{window.pywebview={api:{async get_brand_overview(){
    state.apiCalls+=1;
    return {ok:true,brand_name:'X',primary_audience:'Y',voice:[],facts:[]};
  }}};};
  if(withApi) installApi();
  const context={window, document, location:{search:''}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, listeners, state, installApi, h3};
}
(async()=>{
  // 1. Late injection: Brend, API arrives after parse.
  const late=brendContext(false);
  vm.runInContext(src, late.context);
  const readyListeners=(late.listeners.pywebviewready||[]).length;
  late.installApi();
  for(const fn of late.listeners.pywebviewready||[]) await fn();
  await new Promise(r=>setTimeout(r,0));

  // 2. Immediate fast path: Brend, API already present.
  const immediate=brendContext(true);
  vm.runInContext(src, immediate.context);
  await new Promise(r=>setTimeout(r,0));

  // 3. Foreign screen (no data-brend-* marker, API present).
  const foreign=foreignContext(true);
  vm.runInContext(src, foreign.context);
  await new Promise(r=>setTimeout(r,0));

  console.log(JSON.stringify({
    readyListeners,
    lateHydrated: late.nameEl.textContent==='<img>',
    immediateHydrated: immediate.nameEl.textContent==='<img>',
    foreignApiCalls: foreign.state.apiCalls,
    foreignUntouched: foreign.h3.textContent==='FOREIGN H3' &&
      foreign.h3.innerHTML==='FOREIGN H3',
    nameUsesTextContent: late.nameEl.textContent==='<img>' &&
      late.nameEl.innerHTML==='SSR NAME',
    audienceUsesTextContent: late.audienceEl.textContent==='<script>' &&
      late.audienceEl.innerHTML==='SSR AUDIENCE',
    voiceEscaped: late.voiceEl.innerHTML.includes('&lt;b&gt;warm&lt;/b&gt;') &&
      !late.voiceEl.innerHTML.includes('<b>warm</b>'),
    factEscaped: late.factsEl.innerHTML.includes('&lt;i&gt;F-1&lt;/i&gt;') &&
      late.factsEl.innerHTML.includes('&lt;svg') &&
      !/<i>|<svg/.test(late.factsEl.innerHTML),
  }));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    completed = subprocess.run(
        [node, "-e", harness, str(app_js_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    result = json.loads(completed.stdout)
    assert result == {
        "readyListeners": 1,
        "lateHydrated": True,
        "immediateHydrated": True,
        "foreignApiCalls": 0,
        "foreignUntouched": True,
        "nameUsesTextContent": True,
        "audienceUsesTextContent": True,
        "voiceEscaped": True,
        "factEscaped": True,
    }

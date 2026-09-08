"""Tests for the Pregled i izvoz (step 5) screen body renderer.

Acceptance for ACS-GUI-003: 3-column content-card grid, 2-column quality/
export grid, stepper step 5 active with steps 1–4 done. As of ACS-GUI-009,
"Odobri kampanju" is a UI-only gate (``data-action="approve-gate"``) and
"Izvezi ZIP paket" is wired to the real export bridge
(``data-action="export-campaign"``, always emitted hidden + disabled).
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from ai_campaign_studio.presentation_webview.screens.pregled_izvoz import (
    DEFAULT_FIXTURE,
    ContentPerformanceRow,
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


def test_render_body_odobri_kampanju_is_approve_gate() -> None:
    body = render_body()
    assert re.search(
        r'<button class="btn success" data-action="approve-gate"[^>]*>'
        r"Odobri kampanju</button>",
        body,
    )


def test_render_body_izvezi_zip_is_export_campaign() -> None:
    body = render_body()
    assert re.search(
        r'<button id="btn-izvezi" class="btn primary" '
        r'data-action="export-campaign" data-campaign-id="" data-plan-id=""'
        r'[^>]*hidden disabled>'
        r"Izvezi ZIP paket</button>",
        body,
    )


def test_render_body_has_export_result_callout() -> None:
    """A persistent result callout must exist so the export outcome
    (especially the ZIP path) doesn't disappear after the ~2.2s toast
    auto-hides -- the one thing the user most needs to see after
    clicking 'Izvezi ZIP paket' is WHERE it landed."""
    body = render_body()
    assert '<div class="callout" data-export-result hidden></div>' in body


def test_app_js_export_handler_writes_zip_path_to_persistent_callout() -> None:
    """The toast alone is not enough (Human Owner live-run feedback,
    2026-09-07: exported successfully but no visible indication of
    WHERE the ZIP landed). ``exportCampaign()`` must ALSO write the
    result -- including ``zip_path`` -- into the persistent
    ``data-export-result`` callout, not just a self-hiding toast."""
    app_js_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    js_text = app_js_path.read_text(encoding="utf-8")
    assert "document.querySelector('[data-export-result]')" in js_text
    assert "result.zip_path" in js_text
    assert "resultNode.hidden = false" in js_text


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


def test_render_body_emits_performance_hydration_markers() -> None:
    """ACS-F1-053: the SSR emits the screen-specific performance markers
    that app.js targets for real-data hydration."""
    body = render_body()
    assert "data-perf-card" in body
    assert "Učinak kampanje" in body
    assert "Nema podataka o performansama još." in body
    for key in (
        "ctr",
        "cpc",
        "cpm",
        "cpa",
        "roas",
        "conversion-rate",
        "impressions",
        "clicks",
        "spend",
    ):
        assert f'data-perf-value="{key}"' in body, f"missing marker: {key!r}"
    assert "data-perf-count" in body


def test_app_js_campaign_performance_hydration_lifecycle_isolation() -> None:
    """Execute the committed app.js against a tiny DOM double.

    ACS-F1-053: applies the F1-046/049/051 lifecycle/isolation precedent to
    the Campaign Performance card from the first version. Models the
    ``addEventListener`` ``options`` argument and emits ``pywebviewready``
    TWICE, proving exactly-once hydration; verifies the immediate fast path;
    verifies a foreign screen (no ``data-perf-*`` marker) is never touched;
    verifies metric values go through ``textContent`` and ``None`` -> 'N/A'.
    """
    import json
    import shutil
    import subprocess

    import pytest

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
function el(initial){
  return {
    _text:initial, _html:initial, _hidden:false,
    set textContent(v){this._text=v;}, get textContent(){return this._text;},
    set innerHTML(v){this._html=v;}, get innerHTML(){return this._html;},
    set hidden(v){this._hidden=v;}, get hidden(){return this._hidden;},
    dataset:{}
  };
}
function perfValueEl(key){
  const e=el('—'); e.dataset={perfValue:key}; return e;
}
function baseWindow(){
  const listeners={};
  function addEventListener(n,f,opts){
    (listeners[n]??=[]).push({fn:f, once:!!(opts&&opts.once)});
  }
  function emit(n){
    const arr=listeners[n]||[];
    const remaining=[];
    for(const e of arr){
      e.fn();
      if(!e.once) remaining.push(e);
    }
    listeners[n]=remaining;
  }
  return {listeners, emit, window:{addEventListener}};
}
function perfContext(withApi){
  const {listeners,window,emit}=baseWindow();
  const state={apiCalls:0};
  const card=el('');
  const note=el('Nema podataka');
  const values=[
    perfValueEl('ctr'), perfValueEl('cpc'), perfValueEl('cpm'),
    perfValueEl('cpa'), perfValueEl('roas'), perfValueEl('conversion-rate'),
    perfValueEl('impressions'), perfValueEl('clicks'), perfValueEl('spend')
  ];
  const countEl=el('—');
  const document={
    querySelectorAll:function(s){
      if(s==='[data-perf-value]') return values;
      return [];
    },
    querySelector:function(s){
      if(s==='[data-perf-card]') return card;
      if(s==='[data-perf-count]') return countEl;
      if(s==='[data-perf-note]') return note;
      return null;
    },
    getElementById(){return null;}
  };
  const installApi=()=>{window.pywebview={api:{async get_campaign_performance(){
    state.apiCalls+=1;
    return {ok:true, distribution_instance_count:2,
      derived:{ctr:0.034,cpc:null,cpm:200.0,cpa:null,roas:null,conversion_rate:null},
      raw:{impressions:1000,clicks:34,spend:null}};
  }}};};
  if(withApi) installApi();
  const context={window, document, location:{search:'?campaign=c-1'}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, listeners, emit, state, installApi, values, countEl, note};
}
function foreignContext(withApi){
  const {listeners,window}=baseWindow();
  const state={apiCalls:0};
  const h3=el('FOREIGN H3');
  const document={
    querySelectorAll:function(){return [];},
    querySelector:function(s){
      if(s==='h3') return h3;
      return null;
    },
    getElementById(){return null;}
  };
  const installApi=()=>{window.pywebview={api:{async get_campaign_performance(){
    state.apiCalls+=1;
    return {ok:true,distribution_instance_count:1,derived:{},raw:{}};
  }}};};
  if(withApi) installApi();
  const context={window, document, location:{search:''}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, listeners, state, installApi, h3};
}
(async()=>{
  const late=perfContext(false);
  vm.runInContext(src, late.context);
  const readyListeners=(late.listeners.pywebviewready||[]).length;
  late.installApi();
  late.emit('pywebviewready');
  await new Promise(r=>setTimeout(r,0));
  late.emit('pywebviewready');
  await new Promise(r=>setTimeout(r,0));
  const lateApiCalls=late.state.apiCalls;
  const lateListenerCleared=(late.listeners.pywebviewready||[]).length===0;

  const immediate=perfContext(true);
  vm.runInContext(src, immediate.context);
  await new Promise(r=>setTimeout(r,0));

  const foreign=foreignContext(true);
  vm.runInContext(src, foreign.context);
  await new Promise(r=>setTimeout(r,0));

  console.log(JSON.stringify({
    readyListeners,
    lateApiCalls,
    lateListenerCleared,
    lateCtr: late.values[0].textContent==='0.034',
    lateCpcNA: late.values[1].textContent==='N/A',
    lateCount: late.countEl.textContent==='2',
    lateNoteHidden: late.note.hidden===true,
    immediateHydrated: immediate.values[0].textContent==='0.034',
    foreignApiCalls: foreign.state.apiCalls,
    foreignUntouched: foreign.h3.textContent==='FOREIGN H3' &&
      foreign.h3.innerHTML==='FOREIGN H3',
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
        "lateApiCalls": 1,
        "lateListenerCleared": True,
        "lateCtr": True,
        "lateCpcNA": True,
        "lateCount": True,
        "lateNoteHidden": True,
        "immediateHydrated": True,
        "foreignApiCalls": 0,
        "foreignUntouched": True,
    }


def test_render_body_emits_content_performance_markers() -> None:
    """ACS-F1-054: the SSR emits the screen-specific content-performance
    markers (card/table/rows/note) that app.js targets for real-data
    hydration, plus the offline placeholder rows."""
    body = render_body()
    assert "data-content-perf-card" in body
    assert "Učinak po objavi" in body
    assert "data-content-perf-table" in body
    assert "data-content-perf-rows" in body
    assert "data-content-perf-note" in body
    # Offline placeholder rows from DEFAULT_FIXTURE.
    assert "INSTAGRAM/FEED_POST" in body
    assert "FACEBOOK/FEED_POST" in body


def test_render_body_content_performance_empty_fixture_emits_no_data() -> None:
    """ACS-F1-054: an empty fixture renders a 'Nema podataka.' row, not a
    broken empty table."""
    custom = PregledIzvozFixture(
        campaign_name="Custom",
        content_items=[],
        quality_checks=[],
        export_rows=[],
        export_intro="Intro",
        odobri_toast="t1",
        izvezi_toast="t2",
        content_performance_rows=[],
    )
    body = render_body(custom)
    assert 'Nema podataka.' in body
    assert "data-content-perf-rows" in body


def test_render_body_content_performance_escapes_fixture_labels() -> None:
    """ACS-F1-054: SSR placeholder labels go through html.escape (same XSS
    contract as every other user/AI-text field on the screen)."""
    custom = PregledIzvozFixture(
        campaign_name="Custom",
        content_items=[],
        quality_checks=[],
        export_rows=[],
        export_intro="Intro",
        odobri_toast="t1",
        izvezi_toast="t2",
        content_performance_rows=[
            ContentPerformanceRow("<script>x</script>", "—", "—"),
        ],
    )
    body = render_body(custom)
    assert "<script>x</script>" not in body
    assert "&lt;script&gt;x&lt;/script&gt;" in body


def test_app_js_content_performance_hydration_lifecycle_isolation_and_xss() -> None:
    """Execute the committed app.js against a tiny DOM double.

    ACS-F1-054: applies the F1-046/049/051/053 lifecycle/isolation/XSS
    precedent to the per-content-piece performance table from the first
    version. Models the ``addEventListener`` ``options`` argument and emits
    ``pywebviewready`` TWICE, proving exactly-once hydration; verifies the
    immediate fast path; verifies a foreign screen (no
    ``data-content-perf-*`` marker) is never touched; verifies the label
    (AI headline) is HTML-escaped and ``None`` metrics render 'N/A'; and
    verifies ``campaign_id`` is REUSED from the boot IIFE (no re-parse).
    """
    import json
    import shutil
    import subprocess

    import pytest

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
function el(initial){
  return {
    _text:initial, _html:initial, _hidden:false,
    set textContent(v){this._text=v;}, get textContent(){return this._text;},
    set innerHTML(v){this._html=v;}, get innerHTML(){return this._html;},
    set hidden(v){this._hidden=v;}, get hidden(){return this._hidden;},
    dataset:{}
  };
}
function baseWindow(){
  const listeners={};
  function addEventListener(n,f,opts){
    (listeners[n]??=[]).push({fn:f, once:!!(opts&&opts.once)});
  }
  function emit(n){
    const arr=listeners[n]||[];
    const remaining=[];
    for(const e of arr){
      e.fn();
      if(!e.once) remaining.push(e);
    }
    listeners[n]=remaining;
  }
  return {listeners, emit, window:{addEventListener}};
}
function contentPerfContext(withApi){
  const {listeners,window,emit}=baseWindow();
  const state={apiCalls:0};
  const tbody=el('<tr><td colspan="3" class="muted">SSR</td></tr>');
  const table=el('');
  table.querySelector=function(){ return tbody; };
  const note=el('Nema podataka o performansama još.');
  const document={
    querySelectorAll:function(){ return []; },
    querySelector:function(s){
      if(s==='[data-content-perf-table]') return table;
      if(s==='[data-content-perf-note]') return note;
      return null;
    },
    getElementById(){return null;}
  };
  const installApi=()=>{window.pywebview={api:{async get_campaign_content_performance(){
    state.apiCalls+=1;
    return {ok:true, rows:[
      {content_piece_id:'piece-1',
       label:'INSTAGRAM/FEED_POST — <script>x</script>',
       ctr:0.034, cpc:null},
      {content_piece_id:'piece-2', label:'FACEBOOK/FEED_POST', ctr:null, cpc:5.8824}
    ]};
  }}};};
  if(withApi) installApi();
  const context={window, document, location:{search:'?campaign=c-1'}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, listeners, emit, state, installApi, tbody, note};
}
function foreignContext(withApi){
  const {listeners,window}=baseWindow();
  const state={apiCalls:0};
  const h3=el('FOREIGN H3');
  const document={
    querySelectorAll:function(){return [];},
    querySelector:function(s){
      if(s==='h3') return h3;
      return null;
    },
    getElementById(){return null;}
  };
  const installApi=()=>{window.pywebview={api:{async get_campaign_content_performance(){
    state.apiCalls+=1;
    return {ok:true,rows:[]};
  }}};};
  if(withApi) installApi();
  const context={window, document, location:{search:''}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, listeners, state, installApi, h3};
}
(async()=>{
  const late=contentPerfContext(false);
  vm.runInContext(src, late.context);
  const readyListeners=(late.listeners.pywebviewready||[]).length;
  late.installApi();
  late.emit('pywebviewready');
  await new Promise(r=>setTimeout(r,0));
  late.emit('pywebviewready');
  await new Promise(r=>setTimeout(r,0));
  const lateApiCalls=late.state.apiCalls;
  const lateListenerCleared=(late.listeners.pywebviewready||[]).length===0;
  const lateHtml=late.tbody.innerHTML;

  const immediate=contentPerfContext(true);
  vm.runInContext(src, immediate.context);
  await new Promise(r=>setTimeout(r,0));

  const foreign=foreignContext(true);
  vm.runInContext(src, foreign.context);
  await new Promise(r=>setTimeout(r,0));

  console.log(JSON.stringify({
    readyListeners,
    lateApiCalls,
    lateListenerCleared,
    lateHydrated: lateHtml.indexOf('INSTAGRAM/FEED_POST')!==-1 &&
      lateHtml.indexOf('FACEBOOK/FEED_POST')!==-1,
    lateEscaped: lateHtml.indexOf('&lt;script&gt;')!==-1 &&
      lateHtml.indexOf('<script>')===-1,
    lateNA: lateHtml.indexOf('N/A')!==-1,
    lateNoteHidden: late.note.hidden===true,
    immediateHydrated: immediate.tbody.innerHTML.indexOf('FACEBOOK/FEED_POST')!==-1,
    foreignApiCalls: foreign.state.apiCalls,
    foreignUntouched: foreign.h3.textContent==='FOREIGN H3' &&
      foreign.h3.innerHTML==='FOREIGN H3',
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
        "lateApiCalls": 1,
        "lateListenerCleared": True,
        "lateHydrated": True,
        "lateEscaped": True,
        "lateNA": True,
        "lateNoteHidden": True,
        "immediateHydrated": True,
        "foreignApiCalls": 0,
        "foreignUntouched": True,
    }


def test_render_body_emits_import_performance_markers() -> None:
    """ACS-F1-055: the SSR emits the import button + confirm button + the
    persistent result callout (hidden by default), same pattern as the
    export/generate result callouts."""
    body = render_body()
    assert 'data-action="import-performance-csv"' in body
    assert "Uvezi CSV" in body
    assert 'data-action="confirm-performance-import"' in body
    assert "Potvrdi uvoz" in body
    assert '<div class="callout" data-perf-import-result hidden></div>' in body


def test_app_js_import_performance_csv_xss_and_cross_screen_isolation() -> None:
    """Execute the committed app.js against a tiny DOM double.

    ACS-F1-055: the import flow is CLICK-triggered (no pywebviewready
    lifecycle), so this test proves the two things that DO apply here:
    (1) every CSV-originated string (header names, candidates, invalid-row
    errors) is HTML-escaped before entering the result callout, and (2) the
    buttons/result are screen-specific — a foreign screen with a plain
    ``[data-action]`` button never calls the performance bridge.
    """
    import json
    import shutil
    import subprocess

    import pytest

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
function el(initial){
  return {
    _text:initial, _html:initial, _hidden:false, _disabled:false,
    _id:'', style:{}, listeners:{}, dataset:{},
    addEventListener(n,f){ (this.listeners[n]??=[]).push(f); },
    set textContent(v){this._text=v;}, get textContent(){return this._text;},
    set innerHTML(v){this._html=v;}, get innerHTML(){return this._html;},
    set hidden(v){this._hidden=v;}, get hidden(){return this._hidden;},
    set disabled(v){this._disabled=v;}, get disabled(){return this._disabled;},
    set id(v){this._id=v;}, get id(){return this._id;},
  };
}
function baseWindow(){
  const listeners={};
  function addEventListener(n,f,opts){
    (listeners[n]??=[]).push({fn:f, once:!!(opts&&opts.once)});
  }
  return {listeners, window:{addEventListener}};
}
function baseDocument(actions){
  const document={
    querySelectorAll:function(s){
      if(s==='[data-action]') return actions;
      return [];
    },
    querySelector:function(s){ return null; },
    getElementById:function(){ return null; },
    createElement:function(){ return el(''); },
    body:{ appendChild:function(){} },
  };
  return document;
}
function importContext(withApi){
  const {window}=baseWindow();
  const state={previewCalls:0, confirmCalls:0};
  const importBtn=el('Uvezi CSV');
  importBtn.dataset={action:'import-performance-csv'};
  const confirmBtn=el('Potvrdi uvoz');
  confirmBtn.dataset={action:'confirm-performance-import'};
  confirmBtn.hidden=true;
  const resultNode=el(''); resultNode.hidden=true;
  const document=baseDocument([importBtn, confirmBtn]);
  document.querySelector=function(s){
    if(s==='[data-action="confirm-performance-import"]') return confirmBtn;
    if(s==='[data-perf-import-result]') return resultNode;
    return null;
  };
  const installApi=()=>{window.pywebview={api:{
    pick_and_preview_performance_csv: async function(){
      state.previewCalls+=1;
      return {ok:true, cancelled:false, file_path:'/tmp/x.csv',
        total_rows:2, valid_rows:1, invalid_rows:1,
        columns:[
          {canonical_field:'reach', header:'<script>x</script>',
           status:'matched', candidates:['<script>x</script>']},
        ],
        invalid_samples:[
          {row_number:2, errors:['<img src=x onerror=alert(1)> bad']},
        ]};
    },
    confirm_performance_import: async function(payload){
      state.confirmCalls+=1;
      state.lastPayload=payload;
      return {ok:true, batch_id:'b-1', row_count:2, valid_count:2, invalid_count:0,
        matched_count:1, ambiguous_count:0, unmatched_count:1, skipped_count:0};
    },
  }};};
  if(withApi) installApi();
  const context={window, document, location:{search:'?campaign=c-1'}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, importBtn, confirmBtn, resultNode, state};
}
function foreignContext(withApi){
  const {window}=baseWindow();
  const state={apiCalls:0};
  const toastBtn=el('Toast'); toastBtn.dataset={action:'toast', message:'hi'};
  const h3=el('FOREIGN H3');
  const document=baseDocument([toastBtn]);
  document.querySelector=function(s){
    if(s==='h3') return h3;
    return null;
  };
  const installApi=()=>{window.pywebview={api:{
    pick_and_preview_performance_csv: async function(){
      state.apiCalls+=1; return {ok:true,cancelled:true}; },
    confirm_performance_import: async function(){
      state.apiCalls+=1; return {ok:true}; },
  }};};
  if(withApi) installApi();
  const context={window, document, location:{search:''}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  vm.createContext(context);
  return {context, toastBtn, h3, state};
}
(async()=>{
  const ctx=importContext(true);
  vm.runInContext(src, ctx.context);
  // Click "Uvezi CSV" -> preview rendered + confirm button revealed.
  ctx.importBtn.listeners['click'][0]();
  await new Promise(r=>setTimeout(r,0));
  await new Promise(r=>setTimeout(r,0));
  const previewHtml=ctx.resultNode.innerHTML;
  const confirmRevealed=ctx.confirmBtn.hidden===false;
  // Click "Potvrdi uvoz" -> confirm summary rendered.
  ctx.confirmBtn.listeners['click'][0]();
  await new Promise(r=>setTimeout(r,0));
  await new Promise(r=>setTimeout(r,0));
  const confirmHtml=ctx.resultNode.innerHTML;

  const foreign=foreignContext(true);
  vm.runInContext(src, foreign.context);
  foreign.toastBtn.listeners['click'][0]();
  await new Promise(r=>setTimeout(r,0));

  console.log(JSON.stringify({
    previewShown: ctx.resultNode.hidden===false,
    confirmRevealed,
    previewEscaped: previewHtml.indexOf('&lt;script&gt;')!==-1 &&
      previewHtml.indexOf('<script>')===-1 &&
      previewHtml.indexOf('<img')===-1,
    previewHasStatus: previewHtml.indexOf('reach')!==-1,
    confirmOk: confirmHtml.indexOf('Uvezeno: 2 redova')!==-1,
    confirmCampaignId: ctx.state.lastPayload &&
      ctx.state.lastPayload.campaign_id==='c-1',
    confirmUsesPendingFile: ctx.state.lastPayload &&
      ctx.state.lastPayload.file_path==='/tmp/x.csv',
    previewCalls: ctx.state.previewCalls,
    confirmCalls: ctx.state.confirmCalls,
    foreignApiCalls: foreign.state.apiCalls,
    foreignUntouched: foreign.h3.textContent==='FOREIGN H3' &&
      foreign.h3.innerHTML==='FOREIGN H3',
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
        "previewShown": True,
        "confirmRevealed": True,
        "previewEscaped": True,
        "previewHasStatus": True,
        "confirmOk": True,
        "confirmCampaignId": True,
        "confirmUsesPendingFile": True,
        "previewCalls": 1,
        "confirmCalls": 1,
        "foreignApiCalls": 0,
        "foreignUntouched": True,
    }

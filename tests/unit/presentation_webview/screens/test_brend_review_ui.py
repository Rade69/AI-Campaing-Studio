"""Tests for the Brend fact-review panel (S2-G7b).

SSR part asserts the new panel/markers are emitted by ``render_body``. The
Node/VM part executes the committed ``static/app.js`` against a small DOM
double and proves the fact-review hydration: list rendering + XSS escaping,
live counts, assemble-button visibility, and the approve button-click →
bridge call → reload flow.
"""

from __future__ import annotations

from ai_campaign_studio.presentation_webview.screens.brend import render_body


def test_render_body_emits_fact_review_panel() -> None:
    body = render_body()
    assert "Pregled činjenica" in body
    assert 'data-tab-panel id="panel-fact-review"' in body
    assert 'data-fact-review' in body
    assert 'data-fact-review-list' in body
    assert 'data-fact-count-proposed' in body
    assert 'data-fact-count-approved' in body
    assert 'data-fact-count-rejected' in body
    assert 'data-action="assemble-snapshot"' in body


def test_app_js_fact_review_hydration_render_escape_and_click() -> None:
    """Execute the committed shared JS against a tiny DOM double."""
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

    from pathlib import Path

    app_js_path = (
        Path(__file__).resolve().parents[4]
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    harness = r"""
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[1],'utf8');
function el(initial){
  const node={
    _text:initial===undefined?'':String(initial),
    _html:initial===undefined?'':String(initial),
    dataset:{}, listeners:{}, disabled:false, hidden:false, style:{},
    set textContent(v){this._text=v;}, get textContent(){return this._text;},
    set innerHTML(v){this._html=v;}, get innerHTML(){return this._html;},
    addEventListener(n,f){(this.listeners[n]??=[]).push(f);},
    click(){(this.listeners['click']||[]).forEach(f=>f());},
    querySelectorAll(){return [];}
  };
  return node;
}
function baseWindow(){
  const listeners={};
  return {listeners, window:{addEventListener(n,f){(listeners[n]??=[]).push(f);}}};
}
function factReviewContext(withApi){
  const {listeners,window}=baseWindow();
  const state={reviewCalls:0, approveCalls:0, rejectCalls:0, assembleCalls:0};
  const reviewCard=el('card');
  const listEl=el('');
  const proposedEl=el('0'), approvedEl=el('0'), rejectedEl=el('0');
  const assembleBtn=el('');
  const approveBtn=el('');
  approveBtn.dataset.candidateId='cand-x';
  const rejectBtn=el('');
  rejectBtn.dataset.candidateId='cand-x';
  listEl.querySelectorAll=function(sel){
    if(sel==='[data-action="approve-fact"]') return [approveBtn];
    if(sel==='[data-action="reject-fact"]') return [rejectBtn];
    return [];
  };
  const document={
    querySelectorAll(){return [];},
    getElementById(){return null;},
    createElement(){return el('');},
    querySelector(sel){
      if(sel==='[data-fact-review]') return reviewCard;
      if(sel==='[data-fact-review-list]') return listEl;
      if(sel==='[data-fact-count-proposed]') return proposedEl;
      if(sel==='[data-fact-count-approved]') return approvedEl;
      if(sel==='[data-fact-count-rejected]') return rejectedEl;
      if(sel==='[data-action="assemble-snapshot"]') return assembleBtn;
      return null;
    }
  };
  const installApi=()=>{
    window.pywebview={api:{
      async get_ingestion_review(){state.reviewCalls+=1;
        return {ok:true, brand_id:'b-1', approved_count:1, rejected_count:0,
          candidates:[
            {candidate_id:'cand-x', snapshot_id:'snap-1',
             snapshot_url:'https://example.com/<img>',
             content:'<img src=x onerror=alert(1)>',
             chunk_id:null, status:'PROPOSED', created_at:'2026-01-01'},
            {candidate_id:'cand-y', snapshot_id:'snap-1',
             snapshot_url:'https://example.com/', content:'already ok',
             chunk_id:null, status:'APPROVED', created_at:'2026-01-01'}
          ]};
      },
      async approve_fact_candidate(){state.approveCalls+=1;
        return {ok:true, approved_fact_id:'f-1', candidate_id:'cand-x',
          snapshot_url:'https://example.com/', version:1};},
      async reject_fact_candidate(){state.rejectCalls+=1;
        return {ok:true, candidate_id:'cand-x', status:'REJECTED'};},
      async assemble_brand_snapshot(){state.assembleCalls+=1;
        return {ok:true, snapshot_id:'bs-1', brand_id:'b-1', version:2,
          approved_fact_count:1, created_at:'2026-01-01'};}
    }};
  };
  if(withApi) installApi();
  const context={window, document, location:{search:''}, URLSearchParams,
    setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
  // The app.js IIFE also touches document.body via showToast — provide it.
  context.document.body={appendChild(){}};
  vm.createContext(context);
  return {context, listeners, state, installApi, listEl, proposedEl, approvedEl,
    rejectedEl, assembleBtn, approveBtn};
}
(async()=>{
  const c=factReviewContext(false);
  vm.runInContext(src, c.context);
  const readyListeners=(c.listeners.pywebviewready||[]).length;
  c.installApi();
  for(const fn of c.listeners.pywebviewready||[]) await fn();
  await new Promise(r=>setTimeout(r,0));
  const rendered=c.listEl.innerHTML;
  const escaped = rendered.includes('&lt;img src=x onerror=alert(1)&gt;') &&
                  !/<img src=x/.test(rendered);
  const urlEscaped = rendered.includes('&lt;img&gt;') &&
                     !rendered.includes('https://example.com/<img>');
  const approveButtons = (rendered.match(/data-action="approve-fact"/g)||[]).length;
  const countsOk = c.proposedEl.textContent==='1' &&
    c.approvedEl.textContent==='1' && c.rejectedEl.textContent==='0';
  const assembleVisible = c.assembleBtn.hidden===false;

  // Click the dynamically-bound approve button -> bridge call -> reload.
  c.approveBtn.click();
  await new Promise(r=>setTimeout(r,0));
  await new Promise(r=>setTimeout(r,0));

  console.log(JSON.stringify({
    readyListeners,
    reviewCallsAfterLoad: c.state.reviewCalls,
    approveCalls: c.state.approveCalls,
    escaped,
    urlEscaped,
    approveButtons,
    countsOk,
    assembleVisible,
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
        "reviewCallsAfterLoad": 2,  # initial load + reload after approve
        "approveCalls": 1,
        "escaped": True,
        "urlEscaped": True,
        "approveButtons": 1,
        "countsOk": True,
        "assembleVisible": True,
    }

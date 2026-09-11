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


def test_fact_review_candidates_grouped_by_snapshot_url() -> None:
    """ACS-GUI-012: candidates sharing a ``snapshot_url`` render under ONE
    group header (URL shown once, item count shown), not as N flat rows each
    repeating the URL."""
    import json
    import shutil
    import subprocess
    from pathlib import Path

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

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
const listeners={};
const window={addEventListener(n,f){(listeners[n]??=[]).push(f);}};
const reviewCard=el('card');
const listEl=el('');
const proposedEl=el('0'), approvedEl=el('0'), rejectedEl=el('0');
const assembleBtn=el('');
listEl.querySelectorAll=function(){return [];};
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
document.body={appendChild(){}};
window.pywebview={api:{
  async get_ingestion_review(){
    return {ok:true, brand_id:'b-1', approved_count:0, rejected_count:0,
      candidates:[
        {candidate_id:'c1', snapshot_id:'s1',
         snapshot_url:'https://example.com/page-a', content:'Prvi pasus sa A.',
         chunk_id:null, status:'PROPOSED', created_at:'2026-01-01'},
        {candidate_id:'c2', snapshot_id:'s1',
         snapshot_url:'https://example.com/page-a', content:'Drugi pasus sa A.',
         chunk_id:null, status:'PROPOSED', created_at:'2026-01-01'},
        {candidate_id:'c3', snapshot_id:'s2',
         snapshot_url:'https://example.com/page-b', content:'Jedini pasus sa B.',
         chunk_id:null, status:'PROPOSED', created_at:'2026-01-01'}
      ]};
  }
}};
const context={window, document, location:{search:''}, URLSearchParams,
  setInterval(){return 1;}, clearInterval(){}, setTimeout, clearTimeout, console};
vm.createContext(context);
(async()=>{
  vm.runInContext(src, context);
  await new Promise(r=>setTimeout(r,0));
  const html=listEl.innerHTML;
  const urlAOccurrences=(html.match(/page-a/g)||[]).length;
  const urlBOccurrences=(html.match(/page-b/g)||[]).length;
  const groupCount=(html.match(/fact-group-url/g)||[]).length;
  console.log(JSON.stringify({
    groupCount,
    urlAOccurrences,
    urlBOccurrences,
    hasTwoStavke: html.includes('2 stavke'),
    hasOneStavka: html.includes('1 stavka'),
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
    # Each group's URL is emitted a FIXED number of times (data-group-url
    # attribute + title attribute + visible text) regardless of how many
    # items are inside — group A (2 items) and group B (1 item) show the
    # SAME count, proving the URL is per-GROUP, not repeated per-item (if it
    # were, A would show more occurrences than B).
    assert result == {
        "groupCount": 2,
        "urlAOccurrences": 3,
        "urlBOccurrences": 3,
        "hasTwoStavke": True,
        "hasOneStavka": True,
    }


def test_ingestion_scheme_autofix_and_zero_result_toast() -> None:
    """ACS-GUI-015: a bare-domain input ("example.com") gets ``https://``
    prepended before being submitted, and a SUCCEEDED job with
    ``progress_total==0`` (the silent "nothing discovered" case that looked
    like the app was just stuck) now shows an explicit, actionable toast
    instead of the generic "Preuzimanje završeno."."""
    import json
    import shutil
    import subprocess
    from pathlib import Path

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

    app_js_path = (
        Path(__file__).resolve().parents[4]
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    harness = r"""
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[1],'utf8');
function el(){
  return {
    dataset:{}, listeners:{}, disabled:false, hidden:false, value:'',
    style:{width:''},
    classList:{add(){},remove(){},contains(){return false;}},
    _text:'', set textContent(v){this._text=v;}, get textContent(){return this._text;},
    addEventListener(n,f){(this.listeners[n]??=[]).push(f);},
    click(){(this.listeners['click']||[]).forEach(f=>f());},
    querySelectorAll(){return [];}
  };
}
const reviewCard=el();
const listEl=el();
listEl.querySelectorAll=function(){return [];};
const proposedEl=el(), approvedEl=el(), rejectedEl=el();
const urlInput=el(); urlInput.value='example.com';
const startBtn=el();
const statusEl=el(); statusEl.hidden=true;
const progressWrap=el(); progressWrap.hidden=true;
const progressBar=el();
let toastEl=null;
const document={
  querySelectorAll(){return [];},
  getElementById(id){return id==='toast'?toastEl:null;},
  createElement(){const e=el(); return e;},
  querySelector(sel){
    if(sel==='[data-fact-review]') return reviewCard;
    if(sel==='[data-fact-review-list]') return listEl;
    if(sel==='[data-fact-count-proposed]') return proposedEl;
    if(sel==='[data-fact-count-approved]') return approvedEl;
    if(sel==='[data-fact-count-rejected]') return rejectedEl;
    if(sel==='[data-action="assemble-snapshot"]') return el();
    if(sel==='[data-action="start-ingestion"]') return startBtn;
    if(sel==='[data-action="clear-ingestion"]') return null;
    if(sel==='[data-ingest-url]') return urlInput;
    if(sel==='[data-ingestion-status]') return statusEl;
    if(sel==='[data-ingestion-progress]') return progressWrap;
    if(sel==='[data-ingestion-progress-bar]') return progressBar;
    return null;
  }
};
document.body={appendChild(node){ toastEl=node; node.id='toast'; }};
let pollFn=null;
let submittedUrls=null;
const window={
  addEventListener(){},
  confirm(){return true;},
  pywebview:{api:{
    async get_ingestion_review(){return {ok:true, brand_id:'b-1',
      approved_count:0, rejected_count:0, candidates:[]};},
    async start_brand_ingestion(payload){
      submittedUrls=payload.urls;
      return {ok:true, brand_id:'b-1', job_id:'job-1',
        error_code:null, error_message:null};
    },
    async get_job_status(){
      return {status:'SUCCEEDED', phase:'DONE', progress_current:0,
        progress_total:0, message:'fetched=0 extracted=0 candidates=0 failed=0'};
    }
  }}
};
const context={window, document, location:{search:''}, URLSearchParams,
  setInterval(fn){pollFn=fn; return 1;}, clearInterval(){},
  setTimeout, clearTimeout, console};
vm.createContext(context);
(async()=>{
  vm.runInContext(src, context);
  await new Promise(r=>setTimeout(r,0));
  startBtn.click();
  await new Promise(r=>setTimeout(r,0));
  await new Promise(r=>setTimeout(r,0));
  await pollFn();
  console.log(JSON.stringify({
    submittedUrls,
    inputValueAfterSubmit: urlInput.value,
    toastText: toastEl ? toastEl._text : null,
  }));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    completed = subprocess.run(
        [node, "-e", harness, str(app_js_path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    result = json.loads(completed.stdout)
    assert result["submittedUrls"] == ["https://example.com"]
    assert "Nijedna stranica nije pronađena" in result["toastText"]


def test_ingestion_progress_bar_determinate_then_hidden_on_terminal() -> None:
    """ACS-GUI-014: the progress bar goes indeterminate (no total yet) ->
    determinate width once JobState reports progress -> hidden again on a
    terminal status. ``setInterval``/``clearInterval`` are faked so the poll
    callback can be invoked manually instead of waiting on a real timer."""
    import json
    import shutil
    import subprocess
    from pathlib import Path

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

    app_js_path = (
        Path(__file__).resolve().parents[4]
        / "src" / "ai_campaign_studio" / "presentation_webview" / "static"
        / "app.js"
    )
    harness = r"""
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[1],'utf8');
function el(){
  const classes=new Set();
  return {
    dataset:{}, listeners:{}, disabled:false, hidden:false, value:'',
    style:{width:''},
    classList:{
      add(c){classes.add(c);}, remove(c){classes.delete(c);},
      contains(c){return classes.has(c);}
    },
    _text:'', set textContent(v){this._text=v;}, get textContent(){return this._text;},
    addEventListener(n,f){(this.listeners[n]??=[]).push(f);},
    click(){(this.listeners['click']||[]).forEach(f=>f());},
    querySelectorAll(){return [];}
  };
}
const reviewCard=el();
const listEl=el();
listEl.querySelectorAll=function(){return [];};
const proposedEl=el(), approvedEl=el(), rejectedEl=el();
const urlInput=el(); urlInput.value='https://example.com/';
const startBtn=el();
const statusEl=el(); statusEl.hidden=true;
const progressWrap=el(); progressWrap.hidden=true;
const progressBar=el();
const document={
  querySelectorAll(){return [];},
  getElementById(){return null;},
  createElement(){return el();},
  querySelector(sel){
    if(sel==='[data-fact-review]') return reviewCard;
    if(sel==='[data-fact-review-list]') return listEl;
    if(sel==='[data-fact-count-proposed]') return proposedEl;
    if(sel==='[data-fact-count-approved]') return approvedEl;
    if(sel==='[data-fact-count-rejected]') return rejectedEl;
    if(sel==='[data-action="assemble-snapshot"]') return el();
    if(sel==='[data-action="start-ingestion"]') return startBtn;
    if(sel==='[data-action="clear-ingestion"]') return null;
    if(sel==='[data-ingest-url]') return urlInput;
    if(sel==='[data-ingestion-status]') return statusEl;
    if(sel==='[data-ingestion-progress]') return progressWrap;
    if(sel==='[data-ingestion-progress-bar]') return progressBar;
    return null;
  }
};
document.body={appendChild(){}};
let pollFn=null;
let jobStatusCall=0;
const window={
  addEventListener(){},
  confirm(){return true;},
  pywebview:{api:{
    async get_ingestion_review(){return {ok:true, brand_id:'b-1',
      approved_count:0, rejected_count:0, candidates:[]};},
    async start_brand_ingestion(){return {ok:true, brand_id:'b-1', job_id:'job-1',
      error_code:null, error_message:null};},
    async get_job_status(){
      jobStatusCall+=1;
      if(jobStatusCall===1){
        return {status:'RUNNING', phase:'FETCH', progress_current:0,
          progress_total:0, message:''};
      }
      if(jobStatusCall===2){
        return {status:'RUNNING', phase:'FETCH', progress_current:1,
          progress_total:4, message:''};
      }
      return {status:'SUCCEEDED', phase:'DONE', progress_current:4,
        progress_total:4, message:'fetched=4 extracted=6 candidates=6 failed=0'};
    }
  }}
};
const context={window, document, location:{search:''}, URLSearchParams,
  setInterval(fn){pollFn=fn; return 1;}, clearInterval(){},
  setTimeout, clearTimeout, console};
vm.createContext(context);
(async()=>{
  vm.runInContext(src, context);
  await new Promise(r=>setTimeout(r,0));
  startBtn.click();
  // Let the async startIngestion() body run up to the setInterval() call.
  await new Promise(r=>setTimeout(r,0));
  await new Promise(r=>setTimeout(r,0));

  // Tick 1: RUNNING, no total yet -> indeterminate, bar visible.
  await pollFn();
  const afterTick1={
    hidden: progressWrap.hidden,
    indeterminate: progressWrap.classList.contains('indeterminate'),
    width: progressBar.style.width,
  };

  // Tick 2: RUNNING with a real total -> determinate 25%.
  await pollFn();
  const afterTick2={
    hidden: progressWrap.hidden,
    indeterminate: progressWrap.classList.contains('indeterminate'),
    width: progressBar.style.width,
  };

  // Tick 3: SUCCEEDED -> bar hidden again.
  await pollFn();
  const afterTick3={hidden: progressWrap.hidden};

  console.log(JSON.stringify({afterTick1, afterTick2, afterTick3}));
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
        "afterTick1": {"hidden": False, "indeterminate": True, "width": ""},
        "afterTick2": {"hidden": False, "indeterminate": False, "width": "25%"},
        "afterTick3": {"hidden": True},
    }


def test_load_fact_review_shows_safe_toast_on_bridge_throw() -> None:
    result = _run_load_error_harness("throw")
    assert result == {
        "toast": "Učitavanje pregleda činjenica nije uspjelo.",
        "leakedInternalMessage": False,
    }


def test_load_fact_review_shows_error_message_on_failed_dto() -> None:
    result = _run_load_error_harness("dto")
    assert result == {
        "toast": "Brend ne postoji.",
        "leakedInternalMessage": False,
    }


def _run_load_error_harness(mode: str) -> dict[str, object]:
    """Execute the real app.js and return the toast emitted on load failure."""
    import json
    import shutil
    import subprocess
    from pathlib import Path

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable; executable app.js regression skipped")

    app_js_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "ai_campaign_studio"
        / "presentation_webview"
        / "static"
        / "app.js"
    )
    harness = r"""
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[1],'utf8');
const mode=process.argv[2];
let toast=null;
const reviewCard={};
const document={
  querySelectorAll(){return [];},
  querySelector(sel){return sel==='[data-fact-review]'?reviewCard:null;},
  getElementById(id){return id==='toast'?toast:null;},
  createElement(){return {style:{},textContent:'',id:''};},
  body:{appendChild(node){if(node.id==='toast') toast=node;}}
};
const listeners={};
const window={
  addEventListener(name,fn){(listeners[name]??=[]).push(fn);},
  pywebview:{api:{
    async get_ingestion_review(){
      if(mode==='throw') throw new Error('sensitive SQL detail');
      return {ok:false,error_message:'Brend ne postoji.'};
    }
  }}
};
const context={window,document,location:{search:''},URLSearchParams,
  setInterval(){return 1;},clearInterval(){},setTimeout,clearTimeout,console};
vm.createContext(context);
(async()=>{
  vm.runInContext(src,context);
  await new Promise(resolve=>setTimeout(resolve,0));
  const message=toast?toast.textContent:'';
  console.log(JSON.stringify({
    toast:message,
    leakedInternalMessage:message.includes('sensitive SQL detail')
  }));
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    completed = subprocess.run(
        [node, "-e", harness, str(app_js_path), mode],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    return json.loads(completed.stdout)

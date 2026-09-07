
(function(){
  document.querySelectorAll('[data-action]').forEach(el=>el.addEventListener('click',()=>{
    const action=el.dataset.action;
    if(action==='toast') showToast(el.dataset.message||'Akcija je dostupna u produkcijskoj integraciji.');
    if(action==='tab') {
      // Visual: mark the clicked tab as the only active one in its group.
      const group=el.closest('[data-tabs]');
      group.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
      el.classList.add('active');
      // Functional: also show only the matching panel. The clicked tab
      // declares which panel it controls via ``data-tab-target="<id>"``;
      // every panel carries ``data-tab-panel`` and a matching ``id``.
      // The id->target mapping is unique, so a document-wide query is
      // both correct and avoids the brittle "parent of tabs" assumption
      // (works for both Brend's stacked panels and Podešavanja's
      // right-column sibling card layout).
      const target=el.dataset.tabTarget;
      if(target){
        const panels=document.querySelectorAll('[data-tab-panel]');
        panels.forEach(p=>{p.hidden=(p.id!==target);});
      }
    }
    if(action==='save-and-plan') {
      // ACS-GUI-005: real GUI→backend wiring. The button (Opis kampanje
      // screen) is no longer a static link — clicking it gathers the
      // form values, calls the js_api bridge, and on success navigates
      // to the plan screen with ``?campaign=<id>``. Failure surfaces
      // as a toast with the bridge-provided error_message. The button
      // is disabled during the call to prevent double-clicks racing the
      // network; a final ``finally`` re-enables it.
      saveAndPlan(el);
    }
    if(action==='generate-content') {
      // ACS-GUI-008: bulk content generation. The button lives on the
      // Studio sadržaja screen and reads its campaign_id from the
      // data-campaign-id attribute (the same id the previous step's
      // navigate-after-success used to put in the URL). On success the
      // bridge returns ``{ok, generated_count, failed_count, ...}``
      // and the handler updates a ``data-generate-result`` callout in
      // the same card (so the user sees "N of M uspjelo" right under
      // the button) AND shows a toast. ``finally`` always re-enables
      // the button so the user can retry for failed pieces.
      generateContent(el);
    }
  }));
  // Language picker (Podešavanja → Jezik). Each row is a button with
  // ``data-action="lang-pick"`` and ``data-lang="<code>"``. Clicking
  // marks the chosen row as the only ``.lang-active`` inside its
  // enclosing ``.lang-picker`` group and shows a toast. The active
  // class is per-group (not global) so other lang-pickers on the page
  // stay independent.
  document.querySelectorAll('[data-action="lang-pick"]').forEach(el=>el.addEventListener('click',()=>{
    const code=el.dataset.lang;
    const group=el.closest('.lang-picker');
    if(group){
      group.querySelectorAll('.lang-row').forEach(r=>{
        r.classList.remove('lang-active');
        const m=r.querySelector('.lang-mark');
        if(m) m.textContent='';
      });
      el.classList.add('lang-active');
      const m=el.querySelector('.lang-mark');
      if(m) m.textContent='\u2713';
    }
    const name=el.querySelector('.lang-name')?.textContent||code;
    showToast(`Jezik sadržaja: ${name}.`);
  }));

  // --- ACS-GUI-007: provider toggle / save (Podešavanja → AI provajderi) ---
  // The Podesavanja screen renders 5 mappable providers (openai /
  // anthropic / google / deepseek / openrouter) with a real "Podesi"
  // button that reveals a password input + "Sačuvaj" button. Clicking
  // "Podesi" toggles the matching input row; clicking "Sačuvaj" calls
  // ``window.pywebview.api.configure_provider``. The input is always
  // cleared on both success AND failure so the API key never lingers
  // in the DOM after the click.
  document.querySelectorAll('[data-action="provider-toggle"]').forEach(el=>el.addEventListener('click',()=>{
    const code=el.dataset.providerCode;
    if(!code) return;
    const row=document.getElementById(`provider-input-${code}`);
    if(!row) return;
    row.hidden=!row.hidden;
    if(!row.hidden){
      const input=document.getElementById(`provider-key-${code}`);
      if(input) input.focus();
    }
  }));
  document.querySelectorAll('[data-action="provider-save"]').forEach(el=>el.addEventListener('click',async ()=>{
    const code=el.dataset.providerCode;
    if(!code) return;
    const input=document.getElementById(`provider-key-${code}`);
    const row=document.getElementById(`provider-input-${code}`);
    if(!input||!row) return;
    // ACS-GUI-007 BF-2: read the apiKey into a local FIRST, then run
    // the entire flow inside a try/finally that ALWAYS clears the
    // input. The previous version had three separate ``input.value=''``
    // calls plus an early ``return`` for the "bridge not available"
    // case where the input was never cleared — the api_key would stay
    // in the DOM. The try/finally makes that structural-impossible:
    // once we have a non-empty apiKey in scope, the input is guaranteed
    // to be cleared before this handler returns, regardless of which
    // error path runs.
    const apiKey=(input.value||'').trim();
    if(!apiKey){
      showToast('Unesite API ključ.');
      return;
    }
    el.disabled=true;
    let result;
    try{
      if(!window.pywebview||!window.pywebview.api||typeof window.pywebview.api.configure_provider!=='function'){
        showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
        result=null;
      } else {
        result=await window.pywebview.api.configure_provider({provider_code: code, api_key: apiKey});
      }
    }catch(err){
      showToast('Interna greška pri pozivu: '+(err&&err.message?err.message:'nepoznato.'));
      result=null;
    }finally{
      // ALWAYS clear the input once we entered the "user gave us a
      // key" branch. The api_key must not sit in the DOM any longer
      // than the click itself — explicit ask from the contract (Codex
      // adversarial focus on BF-2).
      input.value='';
      el.disabled=false;
    }
    if(result && result.ok){
      showToast(`Provajder ${code} je sačuvan.`);
      // Hide the row on success so the key is gone from view entirely.
      row.hidden=true;
    } else if(result){
      const msg=(result&&result.error_message)||'Spremanje nije uspjelo.';
      showToast(`Provajder ${code}: ${msg}`);
      // Leave the row visible so the user can retry, but the input
      // is already cleared (the typed key is gone, the user types it
      // again from scratch on retry).
    }
  }));

  function showToast(msg){let t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';Object.assign(t.style,{position:'fixed',right:'24px',bottom:'24px',background:'#0f172a',color:'white',padding:'12px 16px',borderRadius:'10px',fontSize:'13px',zIndex:99,boxShadow:'0 10px 30px rgba(0,0,0,.18)'});document.body.appendChild(t)}t.textContent=msg;t.style.display='block';clearTimeout(window.__tt);window.__tt=setTimeout(()=>t.style.display='none',2200)}

// --- ACS-GUI-005: save-and-plan bridge call ---
//
// The Opis kampanje form uses stable id="f-..." hooks (see
// screens/opis_kampanje/__init__.py) so this handler can read each
// field by id. The brief mapping is locked by the contract:
//   - "Ciljani kanal" -> targets[0] with channel="SOCIAL" (the only
//     channel for now)
//   - Platforma -> platform_code via the locked table
//   - Format -> format_code via the locked table (LinkedIn ignores the
//     selected format and always gets PROFESSIONAL_POST)
//   - "Jezik sadržaja" -> content_language_context (free string, passed
//     as-is to the domain)
//   - "Posebne instrukcije" -> special_instructions (1-element list
//     if non-empty, else [])
//   - content_piece_count hardcoded to 3 (no UI field yet)

const _PLATFORM_TO_CODE = {Instagram: 'INSTAGRAM', Facebook: 'FACEBOOK', LinkedIn: 'LINKEDIN'};
const _FORMAT_TO_CODE = {'Feed 4:5': 'FEED_POST', 'Kvadrat 1:1': 'FEED_POST', 'Priča 9:16': 'STORY'};
const _LINKEDIN_FORMAT_CODE = 'PROFESSIONAL_POST';  // LinkedIn has no FEED_POST/STORY in registry

function _val(id) {
  const el = document.getElementById(id);
  return el ? (el.value || '').trim() : '';
}

function _selectVal(id) {
  // <select> elements expose ``.value`` directly; fall back to the
  // first option if the user somehow has no selection.
  const el = document.getElementById(id);
  if (!el) return '';
  return el.value || (el.options && el.options[0] && el.options[0].value) || '';
}

function buildBriefPayload() {
  const platforma = _selectVal('f-platforma');
  const format = _selectVal('f-format');
  // LinkedIn edge case: registry has only PROFESSIONAL_POST/ARTICLE_LINK_POST;
  // the GUI's "Feed 4:5 / Kvadrat 1:1 / Priča 9:16" select doesn't map semantically.
  // Contract locks this: LinkedIn always gets PROFESSIONAL_POST.
  const formatCode = (platforma === 'LinkedIn') ? _LINKEDIN_FORMAT_CODE : (_FORMAT_TO_CODE[format] || '');
  const platformCode = _PLATFORM_TO_CODE[platforma] || '';
  const instrukcije = _val('f-instrukcije');
  return {
    offer: _val('f-ponuda'),
    goal: _selectVal('f-cilj'),
    audience_text: _val('f-publika'),
    targets: [{
      channel: 'SOCIAL',
      platform_code: platformCode,
      format_code: formatCode,
    }],
    content_piece_count: 3,
    content_language_context: _selectVal('f-jezik') || 'SR',
    special_instructions: instrukcije ? [instrukcije] : [],
  };
}

async function saveAndPlan(button) {
  // Re-entrancy guard: disable the button while the call is in flight to
  // prevent double-clicks racing the network. Re-enable in finally so
  // the user can retry on error.
  if (button.disabled) return;
  button.disabled = true;
  const originalLabel = button.textContent;
  button.textContent = 'Generiram plan…';
  try {
    const api = window.pywebview && window.pywebview.api;
    if (!api || typeof api.create_campaign_and_generate_plan !== 'function') {
      showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
      return;
    }
    const payload = buildBriefPayload();
    const result = await api.create_campaign_and_generate_plan(payload);
    if (result && result.ok) {
      const n = result.plan_item_count;
      showToast('Plan generisan (' + n + ' stavki). Preusmjeravam…');
      // Give the toast a brief moment to register visually before
      // navigating; the user gets feedback that the click landed.
      // ACS-GUI-008: also forward ``plan_id`` in the query string so
      // the next screen (Studio sadržaja) can attach it to the
      // ``generate_content`` bridge call without needing a fresh
      // server lookup.
      const planQs = result.plan_id
        ? '&plan=' + encodeURIComponent(result.plan_id)
        : '';
      setTimeout(function() {
        window.location.href = '../plan_kampanje/index.html?campaign='
          + encodeURIComponent(result.campaign_id) + planQs;
      }, 600);
    } else {
      const msg = (result && result.error_message) ? result.error_message : 'Generisanje plana nije uspjelo.';
      showToast(msg);
    }
  } catch (err) {
    // The bridge is contractually required to never raise into JS
    // (PYWEBVIEW_SECURITY §3), but we belt-and-brace against any
    // uncaught exception from the IPC layer itself.
    showToast('Interna greška pri pozivu: ' + (err && err.message ? err.message : 'nepoznato.'));
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

// --- ACS-GUI-008: generate-content bridge call ---
//
// Wired by the Studio sadržaja screen — the "Generiši sadržaj"
// button has ``data-action="generate-content"`` and a
// ``data-campaign-id="<id>"`` attribute.
//
// ACS-F1-047: the bridge now returns a ``job_id`` IMMEDIATELY
// instead of waiting for the AI loop. The handler:
//
// 1. Submits the job via ``generate_campaign_content`` (sync return).
// 2. Starts a ``setInterval`` that polls ``get_job_status(job_id)``
//    every ~1.2s, updating the button label with a live progress
//    counter ("Generišem 3/12…") and the result callout.
// 3. Offers a "Otkaži" affordance while the job is RUNNING — calls
//    ``cancel_job(job_id)``; the manager transitions to CANCELLED
//    and the next poll reads the partial result.
// 4. On terminal status (SUCCEEDED / FAILED / CANCELLED) stops
//    polling, restores the button, and renders the final outcome
//    (counts + error) into the callout + a final toast.
//
// Why a polling loop and not the JobManager event callback
// subscription: pywebview's ``js_api`` surface is request/response;
//    the JS side cannot subscribe to Python events directly. The
//    manager already exposes ``get_state`` exactly for this purpose
//    (P0.20 contract).
//
// The interval is cleared on EVERY terminal transition so a
// transient IPC failure does not leave ``setInterval`` ticking
// forever (review focus §3).
const POLL_INTERVAL_MS = 1200;

async function generateContent(button) {
  if (button.disabled) return;
  const campaignId = (button.dataset.campaignId || '').trim();
  if (!campaignId) {
    showToast('Nedostaje campaign_id. Ponovo pokreni "Sačuvaj i napravi plan".');
    return;
  }
  const planId = (button.dataset.planId || '').trim();
  if (!planId) {
    showToast('Nedostaje plan_id. Ponovo pokreni "Sačuvaj i napravi plan".');
    return;
  }
  const api = window.pywebview && window.pywebview.api;
  if (!api || typeof api.generate_campaign_content !== 'function' ||
      typeof api.get_job_status !== 'function' ||
      typeof api.cancel_job !== 'function') {
    showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
    return;
  }

  const originalLabel = button.textContent;
  const resultNode = document.querySelector('[data-generate-result]');
  button.disabled = true;
  button.textContent = 'Pokrećem…';

  let jobId = null;
  let pollHandle = null;
  function _stopPolling() {
    if (pollHandle !== null) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  }
  function _renderTerminal(state) {
    _stopPolling();
    const status = state && state.status;
    const n = (state && state.generated_count) || 0;
    const f = (state && state.failed_count) || 0;
    const total = (state && state.progress_total) || 0;
    let toastMsg;
    if (status === 'SUCCEEDED') {
      if (n === 0 && f === 0) {
        toastMsg = 'Sadržaj je već generisan.';
      } else if (f === 0) {
        toastMsg = 'Sve objave generisane (' + n + ').';
      } else if (n === 0) {
        toastMsg = 'Generisanje nije uspjelo ni za jednu objavu (' + f + ' pokušaja).';
      } else {
        toastMsg = 'Generisano ' + n + ' od ' + (n + f) + ' objava. Za ' + f + ' neuspjelih pokušaj ponovo.';
      }
    } else if (status === 'CANCELLED') {
      toastMsg = 'Otkazano. Generisano ' + n + ' od ' + total + '.';
    } else {  // FAILED or anything unexpected
      const errMsg = (state && state.error_message) || 'Generisanje sadržaja nije uspjelo.';
      toastMsg = errMsg;
    }
    showToast(toastMsg);
    if (resultNode) {
      resultNode.textContent = toastMsg;
      resultNode.hidden = false;
    }
    button.disabled = false;
    button.textContent = originalLabel;
  }

  try {
    // 1. Submit the job. The bridge returns synchronously with
    //    ``ok=True, job_id=...`` after the sync validation phase.
    const submitResult = await api.generate_campaign_content({
      campaign_id: campaignId,
      plan_id: planId,
    });
    if (!submitResult || !submitResult.ok) {
      // Sync-layer failure: the bridge rejected before starting the
      // job (boundary validation, plan lookup, JobManager shut
      // down). No job_id to poll.
      const msg = (submitResult && submitResult.error_message) ||
        'Generisanje sadržaja nije uspjelo.';
      showToast(msg);
      if (resultNode) {
        resultNode.textContent = 'Greška: ' + msg;
        resultNode.hidden = false;
      }
      button.disabled = false;
      button.textContent = originalLabel;
      return;
    }
    jobId = submitResult.job_id;
    // 2. Start polling for terminal status. One ``setInterval`` is
    //    the single source of truth for both the progress text
    //    and the terminal transition -- the same callback handles
    //    both branches (still running vs terminal) and tears
    //    down the interval + cancel listener on the terminal
    //    branch. ``_renderTerminal`` does the user-visible work
    //    (toast + callout + button restore).
    const _showCancelHint = () => {
      button.textContent = 'Otkaži (generišem…)';
    };
    const _showProgress = (state) => {
      const cur = (state && state.progress_current) || 0;
      const tot = (state && state.progress_total) || 0;
      if (tot > 0) {
        button.textContent = 'Generišem ' + cur + ' / ' + tot + '…';
      } else {
        button.textContent = 'Generiram objave…';
      }
    };
    // Wire the cancel gesture: a second click while RUNNING calls
    // ``cancel_job``. The handler is removed on terminal exit
    // (inside the poll callback) so a final click after
    // SUCCEEDED does NOT re-issue cancel on a finished job.
    const _onClickWhileRunning = () => {
      button.textContent = 'Otkazujem…';
      button.disabled = true;
      api.cancel_job({ job_id: jobId }).catch((err) => {
        showToast('Greška pri otkazivanju: ' +
          (err && err.message ? err.message : 'nepoznato.'));
      });
    };
    const _pollOnce = async () => {
      let state;
      try {
        state = await api.get_job_status({ job_id: jobId });
      } catch (err) {
        // IPC blip: stop polling and surface the error. Leaving
        // ``setInterval`` running forever is the bug review focus
        // §3 explicitly calls out.
        _stopPolling();
        button.removeEventListener('click', _onClickWhileRunning);
        showToast('Greška pri praćenju posla: ' +
          (err && err.message ? err.message : 'nepoznato.'));
        button.disabled = false;
        button.textContent = originalLabel;
        return;
      }
      if (!state) return;
      if (state.status === 'RUNNING' || state.status === 'PENDING' ||
          state.status === 'CANCELLING') {
        _showProgress(state);
        return;
      }
      // Terminal: SUCCEEDED, FAILED, CANCELLED. Tear down the
      // interval AND the cancel listener so a stale click after
      // SUCCEEDED doesn't try to cancel a finished job.
      _stopPolling();
      button.removeEventListener('click', _onClickWhileRunning);
      _renderTerminal(state);
    };
    // First paint: show a "cancel" affordance and start polling.
    _showCancelHint();
    button.addEventListener('click', _onClickWhileRunning);
    pollHandle = setInterval(_pollOnce, POLL_INTERVAL_MS);
  } catch (err) {
    // Belt-and-brace: the bridge contractually never raises, but the
    // IPC layer itself could (network blip, pywebview shutdown).
    _stopPolling();
    showToast('Interna greška pri pozivu: ' +
      (err && err.message ? err.message : 'nepoznato.'));
    if (resultNode) {
      resultNode.textContent = 'Interna greška.';
      resultNode.hidden = false;
    }
    button.disabled = false;
    button.textContent = originalLabel;
  }
}
})();

(function(){
  const params=new URLSearchParams(location.search);
  const campaign=params.get('campaign');
  const plan=params.get('plan');
  if(campaign){
    document.querySelectorAll('[data-campaign-only]').forEach(el=>el.hidden=false);
    document.querySelectorAll('[data-campaign-hide]').forEach(el=>el.hidden=true);
    document.querySelectorAll('[data-campaign-name]').forEach(el=>el.textContent=campaign);
  }
  // ACS-GUI-008 fix-brief-2 BF-1: the live "Generiši sadržaj" button
  // is part of the build-time static HTML, but its data attributes +
  // visibility depend on the RUNTIME URL. When BOTH ``?campaign=`` AND
  // ``?plan=`` are present, populate the data attributes the bridge
  // expects (``data-campaign-id``, ``data-plan-id``) and reveal the
  // button. Otherwise the button stays hidden (the fixture-only
  // preview path). The two are checked together because the bridge
  // contract requires both, and exposing a half-wired button would
  // surface a confusing "Nedostaje plan_id" toast on every click.
  const btn=document.querySelector('[data-action="generate-content"]');
  if(btn && campaign && plan){
    btn.dataset.campaignId=campaign;
    btn.dataset.planId=plan;
    btn.hidden=false;
  }
})();

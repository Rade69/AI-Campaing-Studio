
// Shared runtime state parsed ONCE by the boot IIFE below. Hydration
// IIFEs that need a campaign/plan id (Campaign Performance, Content
// Performance) read these instead of re-parsing ``location.search``
// (Codex F1-053 note — do not duplicate the query-param parsing a third
// time). ``null`` means "no id in this page's URL".
let appCampaignId = null;
let appPlanId = null;

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
    if(action==='approve-gate') {
      // ACS-GUI-009: "Odobri kampanju" is a UI-only gate. The plan is
      // already APPROVED before this screen (see ACS-GUI-008), so this
      // button makes NO backend call — it just enables the "Izvezi ZIP
      // paket" button and shows a confirmation toast.
      approveGate(el);
    }
    if(action==='export-campaign') {
      // ACS-GUI-009: "Izvezi ZIP paket" calls the real export bridge
      // method. The button is revealed at runtime (boot IIFE) and
      // enabled only after the approve-gate click above.
      exportCampaign(el);
    }
    if(action==='import-performance-csv') {
      // ACS-F1-055: "Uvezi CSV" opens the native OS file dialog and
      // shows the read-only mapping preview.
      importPerformanceCsv(el);
    }
    if(action==='confirm-performance-import') {
      // ACS-F1-055: "Potvrdi uvoz" persists + matches the file chosen
      // in the previous step (no second dialog).
      confirmPerformanceImport(el);
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
//
// Re-entrancy: ACS-F1-047 (Codex BF-CODEX-1) found that toggling
// ``button.disabled = true`` blocked the cancel click on a real
// HTML button (browsers do NOT fire ``click`` on a disabled
// button). The re-entrancy guard is now a separate dataset
// marker (``button.dataset.acsJobActive === '1'``) so the button
// can stay ``enabled`` during RUNNING (so the user can actually
// click "Otkaži") WITHOUT triggering a second
// ``generate_campaign_content`` submit via the page-load-time
// delegated listener. See the global ``[data-action]`` delegate
// at the top of this file for the other side of that contract.
const POLL_INTERVAL_MS = 1200;
const JOB_ACTIVE_ATTR = 'acsJobActive';

async function generateContent(button) {
  // Re-entrancy guard: separate from ``.disabled`` because we now
  // leave the button enabled during RUNNING (so the cancel click
  // can fire). The delegated ``[data-action]`` listener at the top
  // of this file ALSO calls ``generateContent(button)`` on the
  // same click, so we MUST reject a second submit here even
  // when the button looks clickable. ``dataset.acsJobActive``
  // is set the moment a job is successfully submitted and cleared
  // in ``_renderTerminal``.
  if (button.dataset[JOB_ACTIVE_ATTR] === '1') return;
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

  // ACS-F1-047 (Codex BF-CODEX-3): set the re-entrancy marker
  // SYNCHRONOUSLY, BEFORE the first ``await``. Two clicks in the
  // same event-loop tick (before the first ``generate_campaign_content``
  // round-trip resolves) would otherwise BOTH pass the guard at
  // line ~300, both submit, and stack two independent pollers
  // + cancel listeners on the same button. With the marker set
  // here, the second click sees ``acsJobActive === '1'`` and
  // returns at the top of the function -- exactly one submit,
  // exactly one poller, exactly one cancel listener. The sync
  // error path below (SUPERSEDED plan, JobManager shut down, etc.)
  // clears the marker on its way out, so a rejected submit does
  // not permanently lock the button.
  button.dataset[JOB_ACTIVE_ATTR] = '1';

  const originalLabel = button.textContent;
  const resultNode = document.querySelector('[data-generate-result]');
  // IMPORTANT: do NOT set ``button.disabled = true`` here. The cancel
  // gesture depends on the user being able to CLICK the button
  // during RUNNING; a disabled HTML button emits no click event.
  // The re-entrancy marker (set above) is what prevents a second
  // ``generate_campaign_content`` submit from the page-load-time
  // delegated listener.
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
    // Clear the re-entrancy marker AND restore the button. The
    // marker is what stops a second ``generateContent`` call; the
    // label is the only visible state. We intentionally do NOT
    // re-disable here -- the next legitimate click (after the
    // job is done) should be able to re-submit.
    delete button.dataset[JOB_ACTIVE_ATTR];
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
      // down). No job_id to poll. Clear the marker so the user can
      // retry -- the marker was set SYNCHRONOUSLY above (BF-CODEX-3
      // fix), so a failed submit does NOT permanently lock the
      // button.
      const msg = (submitResult && submitResult.error_message) ||
        'Generisanje sadržaja nije uspjelo.';
      showToast(msg);
      if (resultNode) {
        resultNode.textContent = 'Greška: ' + msg;
        resultNode.hidden = false;
      }
      delete button.dataset[JOB_ACTIVE_ATTR];
      button.textContent = originalLabel;
      return;
    }
    // 2. The job is now live on the JobManager worker. The
    //    re-entrancy marker is already set (synchronously, before
    //    this await), so the delegated ``[data-action]`` listener
    //    is already a no-op for the duration of this job. The
    //    button itself stays enabled so a real user click can hit
    //    the cancel handler.
    jobId = submitResult.job_id;
    // 3. Start polling for terminal status. One ``setInterval`` is
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
      // Guard against double-cancel clicks: if the button is already
      // in the "Otkazujem…" state, do nothing. The label is the
      // visible signal; ``dataset.acsCancelling`` would also work
      // but the label is already a single source of truth here.
      if (button.textContent === 'Otkazujem…') return;
      button.textContent = 'Otkazujem…';
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
        // Clear re-entrancy marker on this path too -- the job
        // is effectively failed (IPC blip), the user can retry.
        delete button.dataset[JOB_ACTIVE_ATTR];
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
    delete button.dataset[JOB_ACTIVE_ATTR];
    button.textContent = originalLabel;
  }
}

function approveGate(button) {
  // ACS-GUI-009: UI-only gating. No backend call — the plan is already
  // APPROVED before this screen (the content-generation step did it).
  // Clicking "Odobri kampanju" is the user's confirmation that they
  // reviewed the content, so we enable the export button.
  const exportBtn = document.getElementById('btn-izvezi');
  if (exportBtn) exportBtn.disabled = false;
  showToast(button.dataset.message || 'Sadržaj pregledan.');
}

async function exportCampaign(button) {
  // ACS-GUI-009: real export. Reads campaign_id/plan_id from the data
  // attributes the boot IIFE populated from ``?campaign=``/``?plan=``
  // (same boundary as ``generateContent``). Disabled during the call.
  if (button.disabled) return;
  const campaignId = (button.dataset.campaignId || '').trim();
  const planId = (button.dataset.planId || '').trim();
  if (!campaignId || !planId) {
    showToast('Nedostaje campaign_id/plan_id. Ponovo pokreni "Sačuvaj i napravi plan".');
    return;
  }
  button.disabled = true;
  const originalLabel = button.textContent;
  button.textContent = 'Izvozim…';
  let result;
  try {
    const api = window.pywebview && window.pywebview.api;
    if (!api || typeof api.export_campaign_package !== 'function') {
      showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
      result = null;
    } else {
      result = await api.export_campaign_package({
        campaign_id: campaignId,
        plan_id: planId,
      });
    }
  } catch (err) {
    showToast('Interna greška pri pozivu: ' + (err && err.message ? err.message : 'nepoznato.'));
    result = null;
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
  // Persistent callout (like data-generate-result on Studio sadržaja):
  // the toast alone auto-hides after ~2.2s, which is easy to miss --
  // especially the zip_path, the one piece of information the user
  // most needs after export ("gdje se to arhiviralo?"). The callout
  // stays on screen until the next export attempt.
  const resultNode = document.querySelector('[data-export-result]');
  if (result && result.ok) {
    const path = result.zip_path ? ' Sačuvano u: ' + result.zip_path : '';
    const msg = 'Izvoz gotov: ' + result.exported_count + ' objava, ' +
      result.skipped_count + ' preskočeno.' + path;
    showToast(msg);
    if (resultNode) {
      resultNode.textContent = msg;
      resultNode.hidden = false;
    }
  } else if (result) {
    const msg = (result && result.error_message) || 'Izvoz nije uspio.';
    showToast(msg);
    if (resultNode) {
      resultNode.textContent = 'Greška: ' + msg;
      resultNode.hidden = false;
    }
  }
}

// --- ACS-F1-055: Import Performance CSV (write path) ---
//
// "Uvezi CSV" opens the NATIVE OS file dialog via
// ``pick_and_preview_performance_csv``, then renders a READ-ONLY mapping
// preview (per-field status + counts + invalid samples) into the persistent
// ``data-perf-import-result`` callout. "Potvrdi uvoz" then calls
// ``confirm_performance_import`` with the ``file_path`` held in a LOCAL
// variable (``_pendingImportFile``) — the dialog is NOT reopened. The
// ``campaign_id`` is reused from the shared ``appCampaignId`` (boot IIFE).
// Every string that originates in the CSV file (header names, candidates,
// invalid-row errors) goes through ``escapeImportHtml`` — the CSV is a
// user file, same XSS surface as AI-generated text.
let _pendingImportFile = null;

function escapeImportHtml(value){
  return String(value).replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}

function writeImportResult(html){
  const node=document.querySelector('[data-perf-import-result]');
  if(!node) return;
  node.innerHTML=html;
  node.hidden=false;
}

function renderImportPreview(preview){
  const columns=preview.columns||[];
  const colRows=columns.map(function(c){
    const candidates=(c.candidates||[]).map(escapeImportHtml).join(', ');
    const header=c.header?escapeImportHtml(c.header):'—';
    return '<tr><td>'+escapeImportHtml(c.canonical_field)+'</td>'+
      '<td>'+header+'</td>'+
      '<td>'+escapeImportHtml(c.status)+'</td>'+
      '<td>'+candidates+'</td></tr>';
  }).join('');
  const samples=(preview.invalid_samples||[]).map(function(s){
    return '<div class="small muted">Red '+escapeImportHtml(String(s.row_number))+
      ': '+escapeImportHtml((s.errors||[]).join('; '))+'</div>';
  }).join('');
  const colsTable=colRows
    ? '<table><thead><tr><th>Polje</th><th>Header</th><th>Status</th><th>Kandidati</th></tr></thead><tbody>'+colRows+'</tbody></table>'
    : '';
  const samplesBlock=samples
    ? '<p class="small muted">Nevalidni uzorci:</p>'+samples
    : '';
  const hint=(preview.invalid_rows>0)
    ? '<p class="small muted">Ako vidiš ambiguous/unmatched polja, ispravi CSV header i ponovo izaberi fajl.</p>'
    : '';
  const html='<p class="small muted">Pregled: '+escapeImportHtml(String(preview.total_rows))+
    ' redova, '+escapeImportHtml(String(preview.valid_rows))+' validno, '+
    escapeImportHtml(String(preview.invalid_rows))+' nevalidno.</p>'+
    colsTable+samplesBlock+hint;
  writeImportResult(html);
}

async function importPerformanceCsv(button){
  if(button.disabled) return;
  const api=window.pywebview&&window.pywebview.api;
  if(!api||typeof api.pick_and_preview_performance_csv!=='function'){
    showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
    return;
  }
  button.disabled=true;
  const originalLabel=button.textContent;
  button.textContent='Otvaram…';
  let preview;
  try{
    preview=await api.pick_and_preview_performance_csv({});
  }catch(err){
    showToast('Interna greška pri pozivu: '+(err&&err.message?err.message:'nepoznato.'));
    preview=null;
  }finally{
    button.disabled=false;
    button.textContent=originalLabel;
  }
  if(!preview) return;
  if(preview.cancelled) return; // user dismissed the dialog — nothing to do
  if(preview.ok!==true){
    const msg=(preview.error_message)||'Uvoz nije uspio.';
    showToast(msg);
    writeImportResult('Greška: '+escapeImportHtml(msg));
    return;
  }
  _pendingImportFile=preview.file_path;
  renderImportPreview(preview);
  const confirmBtn=document.querySelector('[data-action="confirm-performance-import"]');
  if(confirmBtn) confirmBtn.hidden=false;
}

async function confirmPerformanceImport(button){
  if(button.disabled) return;
  if(!_pendingImportFile){
    showToast('Prvo izaberi CSV fajl.');
    return;
  }
  const campaignId=appCampaignId;
  if(!campaignId){
    showToast('Nedostaje campaign_id. Ponovo pokreni tok kampanje.');
    return;
  }
  const api=window.pywebview&&window.pywebview.api;
  if(!api||typeof api.confirm_performance_import!=='function'){
    showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
    return;
  }
  button.disabled=true;
  const originalLabel=button.textContent;
  button.textContent='Uvozim…';
  let result;
  try{
    result=await api.confirm_performance_import({
      file_path:_pendingImportFile,
      campaign_id:campaignId,
      platform_code:null,
    });
  }catch(err){
    showToast('Interna greška pri pozivu: '+(err&&err.message?err.message:'nepoznato.'));
    result=null;
  }finally{
    button.disabled=false;
    button.textContent=originalLabel;
  }
  if(!result) return;
  if(result.ok!==true){
    const msg=(result.error_message)||'Uvoz nije uspio.';
    showToast(msg);
    writeImportResult('Greška: '+escapeImportHtml(msg));
    return;
  }
  const msg='Uvezeno: '+result.row_count+' redova ('+result.valid_count+' validno, '+
    result.invalid_count+' nevalidno). Poklopljeno: '+result.matched_count+
    ', ambiguous: '+result.ambiguous_count+', nepoklopljeno: '+result.unmatched_count+
    ', preskočeno: '+result.skipped_count+'.';
  showToast(msg);
  writeImportResult(msg);
  _pendingImportFile=null;
  const confirmBtn=document.querySelector('[data-action="confirm-performance-import"]');
  if(confirmBtn) confirmBtn.hidden=true;
}
})();

(function(){
  const params=new URLSearchParams(location.search);
  const campaign=params.get('campaign');
  const plan=params.get('plan');
  appCampaignId = campaign;
  appPlanId = plan;
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
  // ACS-GUI-009 BF-1 equivalent: the live "Izvezi ZIP paket" button is
  // ALWAYS emitted (hidden, empty data attributes) and revealed here when
  // BOTH ``?campaign=`` AND ``?plan=`` are present. It stays ``disabled``
  // until the "Odobri kampanju" approve-gate click enables it.
  const exportBtn=document.querySelector('[data-action="export-campaign"]');
  if(exportBtn && campaign && plan){
    exportBtn.dataset.campaignId=campaign;
    exportBtn.dataset.planId=plan;
    exportBtn.hidden=false;
  }
  // Human Owner live-run feedback, 2026-09-07: the "next step" links
  // on Plan kampanje / Kalendar / Studio sadržaja (build-time static
  // hrefs, needed for the offline/SSR preview) silently dropped
  // ``?campaign=``/``?plan=`` on every hop after the first ("Sačuvaj i
  // napravi plan" is the only step that navigates via JS with the
  // real ids). A user clicking through the real flow therefore always
  // landed on Studio sadržaja / Pregled i izvoz with NO query params,
  // so their live buttons ("Generiši sadržaj" / "Izvezi ZIP paket")
  // never appeared. Every page in the flow marks its own "next step"
  // link with ``data-next-step``; when this page's OWN URL carries
  // both ids, rewrite that link's href to carry them forward too.
  if(campaign && plan){
    document.querySelectorAll('[data-next-step]').forEach(function(a){
      const href=a.getAttribute('href');
      if(!href) return;
      const base=href.split('?')[0];
      a.setAttribute(
        'href',
        base + '?campaign=' + encodeURIComponent(campaign)
          + '&plan=' + encodeURIComponent(plan)
      );
    });
  }
})();

// --- ACS-F1-046: Kampanje lista — read-path hydration ---
//
// The Kampanje screen is SSR-rendered at build time from DEFAULT_FIXTURE
// (see screens/kampanje/__init__.py). At runtime we REPLACE that fixture
// table with REAL data from the first read js_api method
// ``list_campaigns``. The SSR fixture stays as the offline fallback (when
// pywebview is absent, ``loadCampaigns`` returns early and the fixture
// stays visible). Every interpolated value MUST go through ``escapeHtml``
// before entering the DOM — the bridge returns arbitrary user/AI text
// (campaign name comes from the brief's ``offer``), so XSS is a real
// surface and this mirrors the Python ``html.escape`` on the SSR side.
(function(){
  // ``app.js`` is shared by every screen. A page-specific marker prevents
  // this hydration from ever touching Plan kampanje (or any future table).
  const table=document.querySelector('[data-campaigns-table]');
  if(!table) return;

  function escapeHtml(value){
    return String(value).replace(/[&<>"']/g, function(ch){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
  }

  async function loadCampaigns(){
    const api=window.pywebview && window.pywebview.api;
    if(!api || typeof api.list_campaigns !== 'function'){
      // Offline/debug preview (no bridge): keep the SSR fixture as-is.
      return;
    }
    let result;
    try{
      result=await api.list_campaigns({});
    }catch(err){
      // Never break the page; the fixture stays visible.
      return;
    }
    if(!result || result.ok !== true){
      return;
    }
    const campaigns=result.campaigns || [];
    const thead='<thead><tr>' +
      '<th>Kampanja</th><th>Brend</th><th>Status</th>' +
      '<th>Planirano</th><th>Kreirano</th><th></th>' +
      '</tr></thead>';
    if(campaigns.length===0){
      table.innerHTML=thead +
        '<tbody><tr><td colspan="6" class="muted">' +
        'Nema kreiranih kampanja. Napravi prvu preko \'Opis kampanje\'.' +
        '</td></tr></tbody>';
      return;
    }
    const rows=campaigns.map(function(c){
      return '<tr>' +
        '<td><b>'+escapeHtml(c.name)+'</b></td>' +
        '<td>'+escapeHtml(c.brand)+'</td>' +
        '<td>'+escapeHtml(c.status)+'</td>' +
        '<td>'+escapeHtml(String(c.plan_item_count))+'</td>' +
        '<td>'+escapeHtml(c.created_at)+'</td>' +
        '<td class="right"><a class="btn" href="../opis_kampanje/index.html">Otvori</a></td>' +
        '</tr>';
    }).join('');
    table.innerHTML=thead+'<tbody>'+rows+'</tbody>';
  }

  // pywebview injects ``window.pywebview.api`` asynchronously. Keep the
  // immediate fast path for already-ready/debug environments, otherwise
  // wait for the documented readiness event exactly once. Offline browser
  // previews never emit it, so their SSR fixture remains untouched.
  const api=window.pywebview && window.pywebview.api;
  if(api && typeof api.list_campaigns === 'function'){
    loadCampaigns();
  }else{
    window.addEventListener('pywebviewready', loadCampaigns, {once:true});
  }
})();

// --- ACS-F1-049: Brend screen — read-path hydration ---
//
// Same pattern as the Kampanje hydration (ACS-F1-046): SSR renders the
// fixture at build time, and at runtime we replace the brand-info and
// approved-facts panels with REAL data from ``get_brand_overview``. The
// page-specific markers (``data-brend-*``) prevent this from ever touching
// another screen. ``pywebviewready`` + immediate fast path so the data
// arrives after the async bridge injection.
(function(){
  const nameEl=document.querySelector('[data-brend-name]');
  if(!nameEl) return;

  function escapeHtml(value){
    return String(value).replace(/[&<>"']/g, function(ch){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
  }

  async function loadBrandOverview(){
    const api=window.pywebview && window.pywebview.api;
    if(!api || typeof api.get_brand_overview !== 'function'){
      return; // offline/debug preview: keep the SSR fixture
    }
    let result;
    try{
      result=await api.get_brand_overview({});
    }catch(err){
      return;
    }
    if(!result || result.ok !== true){
      return;
    }

    // brand name + audience via ``textContent`` (inherently XSS-safe).
    if(result.brand_name){
      nameEl.textContent=result.brand_name;
    }
    const audienceEl=document.querySelector('[data-brend-audience]');
    if(audienceEl && result.primary_audience){
      audienceEl.textContent=result.primary_audience;
    }
    // voice + facts are HTML lists: escape every interpolated value.
    const voiceEl=document.querySelector('[data-brend-voice]');
    if(voiceEl && result.voice && result.voice.length){
      voiceEl.innerHTML=result.voice.map(function(v){
        return '<span class="badge info">'+escapeHtml(v)+'</span>';
      }).join('');
    }
    const factsEl=document.querySelector('[data-brend-facts]');
    if(factsEl && result.facts){
      if(result.facts.length===0){
        factsEl.innerHTML='<div class="muted">Nema odobrenih činjenica.</div>';
      }else{
        factsEl.innerHTML=result.facts.map(function(f){
          return '<div class="fact"><b>'+escapeHtml(f.code)+'</b> — '+
            escapeHtml(f.text)+'</div>';
        }).join('');
      }
    }
  }

  const api=window.pywebview && window.pywebview.api;
  if(api && typeof api.get_brand_overview === 'function'){
    loadBrandOverview();
  }else{
    window.addEventListener('pywebviewready', loadBrandOverview, {once:true});
  }
})();

// --- ACS-F1-051: Početna (Dashboard) — read-path hydration ---
//
// Same pattern as Kampanje (ACS-F1-046) and Brend (ACS-F1-049). SSR renders
// the fixture at build time; at runtime we replace the 4 KPI counters and the
// "Nedavne kampanje" list with REAL data from ``get_dashboard_overview``. The
// page-specific markers (``data-pocetna-*``) prevent this from touching another
// screen. KPI values are numbers -> ``textContent``; recent campaign names and
// statuses go through ``escapeHtml``. ``pywebviewready`` + immediate fast path.
(function(){
  const recentList=document.querySelector('[data-pocetna-recent]');
  if(!recentList) return;

  function escapeHtml(value){
    return String(value).replace(/[&<>"']/g, function(ch){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
  }

  async function loadDashboardOverview(){
    const api=window.pywebview && window.pywebview.api;
    if(!api || typeof api.get_dashboard_overview !== 'function'){
      return; // offline/debug preview: keep the SSR fixture
    }
    let result;
    try{
      result=await api.get_dashboard_overview({});
    }catch(err){
      return;
    }
    if(!result || result.ok !== true){
      return;
    }

    const kpiMap={
      active: result.active_campaigns,
      planned: result.posts_planned,
      drafts: result.drafts,
      approved: result.approved,
    };
    document.querySelectorAll('[data-pocetna-kpi-value]').forEach(function(el){
      const key=el.dataset.pocetnaKpiValue;
      if(kpiMap[key] !== undefined){
        el.textContent=String(kpiMap[key]);
      }
    });

    if(result.recent_campaigns && result.recent_campaigns.length){
      recentList.innerHTML=result.recent_campaigns.map(function(c){
        return '<div class="row"><b>'+escapeHtml(c.name)+'</b>'+
          '<span class="badge">'+escapeHtml(c.status)+'</span></div>';
      }).join('');
    }else{
      recentList.innerHTML='<div class="muted small">Nema kampanja.</div>';
    }
  }

  const api=window.pywebview && window.pywebview.api;
  if(api && typeof api.get_dashboard_overview === 'function'){
    loadDashboardOverview();
  }else{
    window.addEventListener('pywebviewready', loadDashboardOverview, {once:true});
  }
})();

// --- ACS-F1-053: Pregled i izvoz — "Učinak kampanje" kartica ---
//
// Hidratuje kampanja-performance karticu STVARNIM podacima iz
// ``get_campaign_performance``. Ekran-specifični ``data-perf-*`` markeri
// (nikad generički selector) spriječavaju dodir drugih ekrana; ``campaign_id``
// dolazi iz ``?campaign=`` URL parametra (isti ``URLSearchParams`` obrazac kao
// boot IIFE na vrhu fajla). Brojevi idu kroz ``textContent``; ``None`` ->
// 'N/A' (nikad prazan string). ``pywebviewready`` + immediate fast path.
(function(){
  const card=document.querySelector('[data-perf-card]');
  if(!card) return;
  const campaign=new URLSearchParams(location.search).get('campaign');
  if(!campaign) return;

  function fmt(v){
    if(v===null || v===undefined) return 'N/A';
    return String(v);
  }

  async function loadCampaignPerformance(){
    const api=window.pywebview && window.pywebview.api;
    if(!api || typeof api.get_campaign_performance !== 'function'){
      return; // offline/debug preview: keep the SSR fixture
    }
    let result;
    try{
      result=await api.get_campaign_performance({campaign_id: campaign});
    }catch(err){
      return;
    }
    if(!result || result.ok !== true){
      return;
    }

    const derived=result.derived || {};
    const raw=result.raw || {};
    const map={
      ctr: derived.ctr,
      cpc: derived.cpc,
      cpm: derived.cpm,
      cpa: derived.cpa,
      roas: derived.roas,
      'conversion-rate': derived.conversion_rate,
      impressions: raw.impressions,
      clicks: raw.clicks,
      spend: raw.spend,
    };
    document.querySelectorAll('[data-perf-value]').forEach(function(el){
      const key=el.dataset.perfValue;
      if(Object.prototype.hasOwnProperty.call(map, key)){
        el.textContent=fmt(map[key]);
      }
    });
    const countEl=document.querySelector('[data-perf-count]');
    if(countEl){
      countEl.textContent=String(result.distribution_instance_count);
    }
    if(result.distribution_instance_count > 0){
      const note=document.querySelector('[data-perf-note]');
      if(note) note.hidden=true;
    }
  }

  const api=window.pywebview && window.pywebview.api;
  if(api && typeof api.get_campaign_performance === 'function'){
    loadCampaignPerformance();
  }else{
    window.addEventListener('pywebviewready', loadCampaignPerformance, {once:true});
  }
})();

// --- ACS-F1-054: Pregled i izvoz — "Učinak po objavi" tabela ---
//
// Hidratuje content-piece-level performance tabelu STVARNIM podacima iz
// ``get_campaign_content_performance``. Ekran-specifični
// ``data-content-perf-*`` markeri (nikad generički selector) spriječavaju
// dodir drugih ekrana. ``campaign_id`` se ČITA iz shared ``appCampaignId``
// (parsiran JEDNOM u boot IIFE-u — Codex F1-053 napomena, ne ponavljati
// ``URLSearchParams``). Label (platform/format + AI headline) ide kroz
// ``escapeHtml`` (XSS); CTR/CPC se takođe escape-uju (brojevi su po prirodi
// bezbjedni, ali ostajemo defanzivni — isti obrazac kao Kampanje/Brend);
// ``None`` -> 'N/A' (nikad prazan string).
(function(){
  const table=document.querySelector('[data-content-perf-table]');
  if(!table) return;
  const campaign=appCampaignId;
  if(!campaign) return;

  function escapeHtml(value){
    return String(value).replace(/[&<>"']/g, function(ch){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
  }

  function fmt(v){
    if(v===null || v===undefined) return 'N/A';
    return String(v);
  }

  async function loadContentPerformance(){
    const api=window.pywebview && window.pywebview.api;
    if(!api || typeof api.get_campaign_content_performance !== 'function'){
      return; // offline/debug preview: keep the SSR fixture
    }
    let result;
    try{
      result=await api.get_campaign_content_performance({campaign_id: campaign});
    }catch(err){
      return;
    }
    if(!result || result.ok !== true){
      return;
    }

    const tbody=table.querySelector('[data-content-perf-rows]') ||
      table.querySelector('tbody');
    if(!tbody) return;

    const rows=result.rows || [];
    if(rows.length===0){
      tbody.innerHTML='<tr><td colspan="3" class="muted">Nema podataka.</td></tr>';
    }else{
      tbody.innerHTML=rows.map(function(r){
        return '<tr>' +
          '<td>'+escapeHtml(r.label)+'</td>' +
          '<td>'+escapeHtml(fmt(r.ctr))+'</td>' +
          '<td>'+escapeHtml(fmt(r.cpc))+'</td>' +
          '</tr>';
      }).join('');
    }
    const note=document.querySelector('[data-content-perf-note]');
    if(note && rows.length>0) note.hidden=true;
  }

  const api=window.pywebview && window.pywebview.api;
  if(api && typeof api.get_campaign_content_performance === 'function'){
    loadContentPerformance();
  }else{
    window.addEventListener('pywebviewready', loadContentPerformance, {once:true});
  }
})();

// --- S2-G7b: Brend — Pregled činjenica (fact review) ---
//
// Hydration pattern is the same as Kampanje/Brend: SSR renders the fixture
// ("Učitavanje kandidata…"), and at runtime we replace the list with REAL
// data from ``get_ingestion_review``. Approve/Reject/Assemble buttons call
// the bridge and then RELOAD the list so the counts and row statuses stay
// consistent with the DB. Approve/Reject rows are built DYNAMICALLY, so
// their click handlers are bound after each render (the parse-time
// ``[data-action]`` delegate at the top of this file only sees static
// elements). Every interpolated value goes through ``escapeHtml`` (XSS).
(function(){
  const reviewCard=document.querySelector('[data-fact-review]');
  if(!reviewCard) return;

  function escapeHtml(value){
    return String(value).replace(/[&<>"']/g, function(ch){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
  }

  function showToast(msg){
    let t=document.getElementById('toast');
    if(!t){
      t=document.createElement('div');
      t.id='toast';
      Object.assign(t.style,{position:'fixed',right:'24px',bottom:'24px',
        background:'#0f172a',color:'white',padding:'12px 16px',
        borderRadius:'10px',fontSize:'13px',zIndex:99,
        boxShadow:'0 10px 30px rgba(0,0,0,.18)'});
      document.body.appendChild(t);
    }
    t.textContent=msg;
    t.style.display='block';
    clearTimeout(window.__tt);
    window.__tt=setTimeout(function(){t.style.display='none';},2200);
  }

  function renderCounts(result){
    const candidates=(result && result.candidates) || [];
    let proposed=0, approved=0, rejected=0;
    candidates.forEach(function(c){
      if(c.status==='APPROVED') approved++;
      else if(c.status==='REJECTED') rejected++;
      else proposed++;
    });
    const setText=function(sel,v){
      const el=document.querySelector(sel);
      if(el) el.textContent=String(v);
    };
    setText('[data-fact-count-proposed]', proposed);
    setText('[data-fact-count-approved]', approved);
    setText('[data-fact-count-rejected]', rejected);
    const assembleBtn=document.querySelector('[data-action="assemble-snapshot"]');
    if(assembleBtn) assembleBtn.hidden=(approved===0);
  }

  function bindRowButtons(list){
    list.querySelectorAll('[data-action="approve-fact"]').forEach(function(btn){
      btn.addEventListener('click', function(){ approveFact(btn); });
    });
    list.querySelectorAll('[data-action="reject-fact"]').forEach(function(btn){
      btn.addEventListener('click', function(){ rejectFact(btn); });
    });
  }

  function renderRows(candidates){
    const list=document.querySelector('[data-fact-review-list]');
    if(!list) return;
    if(!candidates || candidates.length===0){
      list.innerHTML='<div class="muted">Nema kandidata za pregled.</div>';
      return;
    }
    list.innerHTML=candidates.map(function(c){
      const proposed=c.status==='PROPOSED';
      const actions=proposed
        ? '<div class="actions">'+
          '<button class="btn" data-action="approve-fact" data-candidate-id="'+escapeHtml(c.candidate_id)+'">Odobri</button>'+
          '<button class="btn" data-action="reject-fact" data-candidate-id="'+escapeHtml(c.candidate_id)+'">Odbij</button>'+
          '</div>'
        : '';
      const badge=c.status==='APPROVED'?'ok':(c.status==='REJECTED'?'danger':'info');
      return '<div class="fact-review-row">'+
        '<div class="small muted">'+escapeHtml(c.snapshot_url)+'</div>'+
        '<div>'+escapeHtml(c.content)+'</div>'+
        '<div class="statusline"><span class="badge '+badge+'">'+escapeHtml(c.status)+'</span></div>'+
        actions+
        '</div>';
    }).join('');
    bindRowButtons(list);
  }

  async function loadFactReview(){
    const api=window.pywebview && window.pywebview.api;
    if(!api || typeof api.get_ingestion_review!=='function') return;
    let result;
    try{
      result=await api.get_ingestion_review({});
    }catch(err){
      showToast('Učitavanje pregleda činjenica nije uspjelo.');
      return;
    }
    if(!result || result.ok!==true){
      const message=result && typeof result.error_message==='string' && result.error_message.trim()
        ? result.error_message
        : 'Učitavanje pregleda činjenica nije uspjelo.';
      showToast(message);
      return;
    }
    renderCounts(result);
    renderRows(result.candidates);
  }

  async function approveFact(button){
    const candidateId=(button.dataset.candidateId||'').trim();
    if(!candidateId){ showToast('Nedostaje candidate_id.'); return; }
    button.disabled=true;
    let result;
    try{
      const api=window.pywebview && window.pywebview.api;
      if(!api || typeof api.approve_fact_candidate!=='function'){
        showToast('Interna greška: bridge nije dostupan.');
        result=null;
      }else{
        result=await api.approve_fact_candidate({candidate_id:candidateId});
      }
    }catch(err){
      showToast('Interna greška pri pozivu: '+(err&&err.message?err.message:'nepoznato.'));
      result=null;
    }finally{
      button.disabled=false;
    }
    if(result && result.ok){
      showToast('Činjenica odobrena.');
      await loadFactReview();
    }else if(result){
      showToast((result.error_message)||'Odobravanje nije uspjelo.');
    }
  }

  async function rejectFact(button){
    const candidateId=(button.dataset.candidateId||'').trim();
    if(!candidateId){ showToast('Nedostaje candidate_id.'); return; }
    button.disabled=true;
    let result;
    try{
      const api=window.pywebview && window.pywebview.api;
      if(!api || typeof api.reject_fact_candidate!=='function'){
        showToast('Interna greška: bridge nije dostupan.');
        result=null;
      }else{
        result=await api.reject_fact_candidate({candidate_id:candidateId});
      }
    }catch(err){
      showToast('Interna greška pri pozivu: '+(err&&err.message?err.message:'nepoznato.'));
      result=null;
    }finally{
      button.disabled=false;
    }
    if(result && result.ok){
      showToast('Činjenica odbijena.');
      await loadFactReview();
    }else if(result){
      showToast((result.error_message)||'Odbijanje nije uspjelo.');
    }
  }

  async function assembleSnapshot(button){
    button.disabled=true;
    let result;
    try{
      const api=window.pywebview && window.pywebview.api;
      if(!api || typeof api.assemble_brand_snapshot!=='function'){
        showToast('Interna greška: bridge nije dostupan.');
        result=null;
      }else{
        result=await api.assemble_brand_snapshot({});
      }
    }catch(err){
      showToast('Interna greška pri pozivu: '+(err&&err.message?err.message:'nepoznato.'));
      result=null;
    }finally{
      button.disabled=false;
    }
    if(result && result.ok){
      showToast('Snimak brenda v'+result.version+' kreiran ('+result.approved_fact_count+' činjenica).');
      await loadFactReview();
    }else if(result){
      showToast((result.error_message)||'Kreiranje snimka nije uspjelo.');
    }
  }

  // Static "Napravi snimak brenda" button: bind directly (the global
  // [data-action] delegate binds a no-op for this action).
  const assembleBtn=document.querySelector('[data-action="assemble-snapshot"]');
  if(assembleBtn){
    assembleBtn.addEventListener('click', function(){ assembleSnapshot(assembleBtn); });
  }

  const api=window.pywebview && window.pywebview.api;
  if(api && typeof api.get_ingestion_review==='function'){
    loadFactReview();
  }else{
    window.addEventListener('pywebviewready', loadFactReview, {once:true});
  }
})();

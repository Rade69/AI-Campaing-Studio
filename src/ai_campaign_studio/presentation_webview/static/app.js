
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
      setTimeout(function() {
        window.location.href = '../plan_kampanje/index.html?campaign=' + encodeURIComponent(result.campaign_id);
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
})();

(function(){
  const campaign=new URLSearchParams(location.search).get('campaign');
  if(!campaign) return;
  document.querySelectorAll('[data-campaign-only]').forEach(el=>el.hidden=false);
  document.querySelectorAll('[data-campaign-hide]').forEach(el=>el.hidden=true);
  document.querySelectorAll('[data-campaign-name]').forEach(el=>el.textContent=campaign);
})();

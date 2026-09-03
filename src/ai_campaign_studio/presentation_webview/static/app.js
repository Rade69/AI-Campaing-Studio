
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
  function showToast(msg){let t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';Object.assign(t.style,{position:'fixed',right:'24px',bottom:'24px',background:'#0f172a',color:'white',padding:'12px 16px',borderRadius:'10px',fontSize:'13px',zIndex:99,boxShadow:'0 10px 30px rgba(0,0,0,.18)'});document.body.appendChild(t)}t.textContent=msg;t.style.display='block';clearTimeout(window.__tt);window.__tt=setTimeout(()=>t.style.display='none',2200)}
})();

(function(){
  const campaign=new URLSearchParams(location.search).get('campaign');
  if(!campaign) return;
  document.querySelectorAll('[data-campaign-only]').forEach(el=>el.hidden=false);
  document.querySelectorAll('[data-campaign-hide]').forEach(el=>el.hidden=true);
  document.querySelectorAll('[data-campaign-name]').forEach(el=>el.textContent=campaign);
})();


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
      // This keeps the markup explicit (no index-based coupling that
      // breaks when sections are reordered) and works for any container
      // shape — Brend's stacked panels and Podešavanja's right-column
      // card both share the same lookup.
      const target=el.dataset.tabTarget;
      if(target){
        // Panels can live anywhere on the page (Brend: stacked
        // siblings of the tabs; Podešavanja: in a SIBLING .card from
        // the grid layout). The id→target mapping is unique, so a
        // document-wide query is both correct and avoids the brittle
        // "parent of tabs" assumption.
        const panels=document.querySelectorAll('[data-tab-panel]');
        panels.forEach(p=>{p.hidden=(p.id!==target);});
      }
    }
  }));
  // Native <select> for language picker — no modal, no fake buttons.
  // The change event fires after the user picks a new option.
  document.querySelectorAll('select[data-action="lang-select"]').forEach(el=>{
    el.addEventListener('change',()=>{
      const lang=el.value;
      const labels={EN:'English',HR:'Hrvatski',SR:'Srpski (latinica)',BS:'Bosanski'};
      showToast(`Jezik sadržaja: ${labels[lang]||lang}.`);
    });
  });
  function showToast(msg){let t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';Object.assign(t.style,{position:'fixed',right:'24px',bottom:'24px',background:'#0f172a',color:'white',padding:'12px 16px',borderRadius:'10px',fontSize:'13px',zIndex:99,boxShadow:'0 10px 30px rgba(0,0,0,.18)'});document.body.appendChild(t)}t.textContent=msg;t.style.display='block';clearTimeout(window.__tt);window.__tt=setTimeout(()=>t.style.display='none',2200)}
})();

(function(){
  const campaign=new URLSearchParams(location.search).get('campaign');
  if(!campaign) return;
  document.querySelectorAll('[data-campaign-only]').forEach(el=>el.hidden=false);
  document.querySelectorAll('[data-campaign-hide]').forEach(el=>el.hidden=true);
  document.querySelectorAll('[data-campaign-name]').forEach(el=>el.textContent=campaign);
})();

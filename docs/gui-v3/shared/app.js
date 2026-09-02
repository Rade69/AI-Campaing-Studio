
(function(){
  document.querySelectorAll('[data-action]').forEach(el=>el.addEventListener('click',()=>{
    const action=el.dataset.action;
    if(action==='toast') showToast(el.dataset.message||'Akcija je dostupna u produkcijskoj integraciji.');
    if(action==='tab') { const group=el.closest('[data-tabs]'); group.querySelectorAll('.tab').forEach(x=>x.classList.remove('active')); el.classList.add('active'); }
  }));
  function showToast(msg){let t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';Object.assign(t.style,{position:'fixed',right:'24px',bottom:'24px',background:'#0f172a',color:'white',padding:'12px 16px',borderRadius:'10px',fontSize:'13px',zIndex:99,boxShadow:'0 10px 30px rgba(0,0,0,.18)'});document.body.appendChild(t)}t.textContent=msg;t.style.display='block';clearTimeout(window.__tt);window.__tt=setTimeout(()=>t.style.display='none',2200)}
})();

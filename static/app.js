'use strict';
window.MT = {
  $: (id)=>document.getElementById(id),
  esc: (v)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  show: (msg)=>{let node=document.getElementById('toast');node.textContent=msg;node.classList.add('show');clearTimeout(window.MT.timer);window.MT.timer=setTimeout(()=>node.classList.remove('show'),4300)},
  // A token belongs to the current server-side session, not to a browser tab.
  // Re-fetch it whenever this tab does not yet know the active session.
  async refreshCsrf(){
    const response=await fetch('/api/me', {credentials:'same-origin',cache:'no-store'});
    if(!response.ok)throw Error('No se pudo validar la sesión. Recarga la página.');
    const session=await response.json();
    window.MT.csrf=session.csrf || null;
    return session;
  },
  async api(path,method='GET',body){
    const mutation=!['GET','HEAD'].includes(method.toUpperCase());
    // New page, another tab or a login change can leave this variable empty.
    if(mutation && !window.MT.csrf)await window.MT.refreshCsrf();
    // Only retry a *recognized* CSRF mismatch; never retry arbitrary HTTP errors.
    for(let attempt=0;attempt<2;attempt++){
      const opts={method,credentials:'same-origin',cache:'no-store',headers:{}};
      if(body!==undefined){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}
      if(mutation && window.MT.csrf)opts.headers['X-CSRF-Token']=window.MT.csrf;
      const response=await fetch(path,opts);
      const obj=await response.json().catch(()=>({error:'Respuesta inválida del servidor'}));
      if(response.ok)return obj;
      if(mutation && response.status===403 && obj.code==='CSRF_INVALID' && attempt===0){
        const session=await window.MT.refreshCsrf();
        if(!session.authenticated){
          throw Error('La sesión terminó. Inicia sesión nuevamente.');
        }
        continue;
      }
      throw Error(obj.error||'Error HTTP '+response.status);
    }
    throw Error('No se pudo validar la sesión; vuelve a ingresar.');
  },
  async who(){return await window.MT.refreshCsrf()},
  statuses:{available:['Disponible','ok'],busy:['Ocupado','warn'],off:['Desconectado','neutral'],pending:['Sin asignar','warn'],offered:['Ofrecido','warn'],accepted:['Aceptado','ok'],inprogress:['En carrera','ok'],done:['Finalizado','neutral'],cancelled:['Cancelado','bad']},
  badge(key){let [txt,cl]=window.MT.statuses[key]||[key,'neutral'];return `<span class="pill ${cl}">${txt}</span>`},
  number(t){return t===null||t===undefined?'Sin marcar':`${Number(t).toFixed(5)}`},
  async config(){return await window.MT.api('/api/config')},
  getMap(elementId,cfg,onclick){
    const el=this.$(elementId);
    if(!window.L){el.querySelector('.mapfallback').textContent='No se pudo cargar Leaflet (se necesita internet para la librería y teselas). Puedes llenar dirección manualmente.';return null}
    const map=L.map(elementId,{zoomControl:true}).setView([9.097,-79.332],12);
    L.tileLayer(cfg.tile_url,{maxZoom:cfg.max_zoom,attribution:cfg.attribution,detectRetina:false}).addTo(map);
    if(onclick)map.on('click',onclick);
    el.classList.add('ready');
    setTimeout(()=>map.invalidateSize(),250);
    return map;
  },
  marker(map,lat,lng,type,title){
    if(!map||lat===null||lat===undefined||lng===null||lng===undefined)return null;
    let icon=L.divIcon({className:'',html:type==='pickup'||type==='dest'?`<div class="point-icon ${type==='dest'?'dest':''}"></div>`:`<div class="driver-icon ${type}">🚕</div>`,iconSize:type==='pickup'||type==='dest'?[25,25]:[34,34],iconAnchor:[12,12]});
    let mk=L.marker([lat,lng],{icon}).addTo(map);
    if(title)mk.bindPopup(title);
    return mk;
  }
};

// Cache only public static assets; no personal data or trips are stored offline.
if ('serviceWorker' in navigator && (location.pathname==='/cliente'||location.pathname==='/conductor')) {
 navigator.serviceWorker.register('/sw.js').catch(()=>{});
}

// Reusable authenticated password-change form; server validates role, current password and CSRF.
const passForm=document.getElementById('change-password-form');
if(passForm)passForm.addEventListener('submit',async e=>{
 e.preventDefault();
 try{
  await window.MT.api('/api/account/password','POST',{
   current_password:document.getElementById('current-pass').value,
   new_password:document.getElementById('new-pass').value
  });
  alert('Contraseña modificada. Inicia sesión de nuevo.');location.href=location.pathname==='/cliente'?'/cliente':'/ingresar';
 }catch(err){window.MT.show(err.message)}
});

'use strict';
window.MTCloud = {
  csrf: null,
  esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));},
  text(id,v){const e=document.getElementById(id);if(e)e.textContent=v;},
  notice(v,bad=false){const e=document.getElementById('notice');if(e){e.className=bad?'error':'gps';e.textContent=v;}}
  ,async me(){const r=await fetch('/api/me',{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error('No se pudo consultar la sesión');const s=await r.json();this.csrf=s.csrf;return s;},
  async api(path,method='GET',body){
    const mutation=method.toUpperCase()!=='GET';
    if(mutation && !this.csrf) await this.me();
    for(let attempt=0;attempt<2;attempt++){
      const headers={}; if(body!==undefined)headers['Content-Type']='application/json';
      if(mutation && this.csrf)headers['X-CSRF-Token']=this.csrf;
      const r=await fetch(path,{method,credentials:'same-origin',cache:'no-store',headers,
                               body:body===undefined?undefined:JSON.stringify(body)});
      const o=await r.json().catch(()=>({error:'Respuesta inválida'}));
      if(r.ok)return o;
      if(mutation && r.status===403 && o.code==='CSRF_INVALID' && attempt===0){
        const s=await this.me();if(!s.authenticated)throw Error('Tu sesión terminó');continue;
      }
      throw Error(o.error||'Error HTTP '+r.status);
    }
    throw Error('No se pudo renovar la sesión');
  },
  async logout(){await this.api('/api/logout','POST',{});location.href='/ingresar.html';},
  status(v){const m={pending:'Pendiente',offered:'Ofrecida',accepted:'Aceptada',inprogress:'En curso',done:'Finalizada',cancelled:'Cancelada'};return m[v]||v;},
  link(lat,lng){if(typeof lat!=='number'||typeof lng!=='number'||!Number.isFinite(lat)||!Number.isFinite(lng))return null;const p=encodeURIComponent(lat+','+lng);return {waze:'https://waze.com/ul?ll='+p+'&navigate=yes',maps:'https://www.google.com/maps/dir/?api=1&destination='+p+'&travelmode=driving'};}
};

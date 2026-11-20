'use strict';(async()=>{
 const M=MTCloud,el=id=>document.getElementById(id);let busy=false,gpsWatch=null,lastSent=0,gpsSending=false,currentDriver=null,allTrips=[],selected=null,lastMapSelection=null;
 const map=MetroMap.make({id:'map-conductor'});
 try{const s=await M.me();if(!s.authenticated||s.user.role!=='driver'){location.replace('/ingresar.html');return;}}
 catch(e){M.notice(e.message,true);return;}
 const actions={offered:[['accept','Aceptar'],['reject','Rechazar']],accepted:[['start','Iniciar carrera']],inprogress:[['complete','Finalizar carrera']]};
 function mapCurrent(){
  const t=allTrips.find(x=>x.id===selected);if(!t){map.clearRoute();lastMapSelection=null;return;}
  const changed=selected!==lastMapSelection;
  if(changed){map.clearRoute();lastMapSelection=selected;}
  const points=[];
  if(MetroMap.good(t.pickup_lat,t.pickup_lng))points.push({lat:t.pickup_lat,lng:t.pickup_lng,name:'Recogida MT-'+t.id,kind:'pickup'});
  if(MetroMap.good(t.dest_lat,t.dest_lng))points.push({lat:t.dest_lat,lng:t.dest_lng,name:'Destino MT-'+t.id,kind:'destination'});
  const loc=currentDriver?.location;if(loc&&MetroMap.good(loc.lat,loc.lng))points.push({lat:loc.lat,lng:loc.lng,name:'Mi GPS real reciente',kind:'driver'});
  map.update(points,changed);
  const next=t.status==='accepted'?{lat:t.pickup_lat,lng:t.pickup_lng}:
    t.status==='inprogress'?{lat:t.dest_lat,lng:t.dest_lng}:null;
  const start=loc&&MetroMap.good(loc.lat,loc.lng)?{lat:loc.lat,lng:loc.lng}:null;
  const a=start||(t.status==='inprogress'&&MetroMap.good(t.pickup_lat,t.pickup_lng)?{lat:t.pickup_lat,lng:t.pickup_lng}:null);
  if(a&&next&&MetroMap.good(next.lat,next.lng))map.route(a,next,{fit:changed});else map.clearRoute();
 }
 async function load(){if(busy)return;busy=true;
  try{const data=await M.api('/api/mine'),d=data.driver;currentDriver=d;allTrips=data.trips;
   el('unit').innerHTML=`<strong>${M.esc(d.unit)} · ${M.esc(d.name)}</strong><p>${M.esc(d.station)} · ${M.esc(d.status)}</p><p>${M.esc(d.vehicle_make||'Vehículo pendiente')} ${M.esc(d.vehicle_model||'')} · ${M.esc(d.plate||'Placa pendiente')}</p><p class="muted">GPS: ${d.gps_recent?M.esc(d.last_location_at):'Sin posición reciente'}</p>`;
   el('trips').innerHTML=data.trips.length?data.trips.map(t=>{
    const pick=t.status==='accepted'?M.link(t.pickup_lat,t.pickup_lng):null;
    const dest=t.status==='inprogress'?M.link(t.dest_lat,t.dest_lng):null;
    const n=pick||dest,lbl=pick?'Recogida':'Destino';
    return `<article class="item"><div class="row between"><b>#MT-${t.id}</b><span class="status">${M.status(t.status)}</span></div><p><b>Pasajero:</b> ${M.esc(t.name)} · <b>Recogida:</b> ${M.esc(t.pickup)}</p><p><b>Destino:</b> ${M.esc(t.destination||'Por confirmar')}</p><p>Referencia: ${M.esc(t.reference||'—')}</p>${n?`<div class="actions"><a target="_blank" rel="noopener noreferrer" href="${n.waze}">Waze a ${lbl}</a><a target="_blank" rel="noopener noreferrer" href="${n.maps}">Google Maps</a></div>`:['accepted','inprogress'].includes(t.status)?'<p class="muted">Sin coordenadas para Waze; confirma con la central.</p>':''}<div class="actions"><button class="button" data-view="${t.id}">Ver puntos y recorrido</button>${(actions[t.status]||[]).map(([a,label])=>`<button class="button ${a==='reject'?'':'primary'}" data-action="${a}" data-trip="${t.id}">${label}</button>`).join('')}</div></article>`;
   }).join(''):'<p class="muted">No tienes carreras asignadas.</p>';
   if(selected&&!allTrips.some(t=>t.id===selected))selected=null;
   if(!selected){const t=allTrips.find(x=>['accepted','inprogress'].includes(x.status));if(t)selected=t.id}
   if(selected)mapCurrent();else{map.clearRoute();map.update([]);lastMapSelection=null;}
  }catch(e){el('trips').innerHTML=`<div class="error">No se cargaron carreras: ${M.esc(e.message)} <button class="button" data-retry="1">Reintentar</button></div>`;M.notice(e.message,true)}finally{busy=false;}}
 el('trips').addEventListener('click',async e=>{
  if(e.target.closest('[data-retry]'))return load();
  const v=e.target.closest('[data-view]');if(v){selected=Number(v.dataset.view);mapCurrent();return;}
  const b=e.target.closest('[data-action]');if(!b)return;
  try{await M.api('/api/trips/action','POST',{action:b.dataset.action,trip_id:Number(b.dataset.trip)});selected=Number(b.dataset.trip);M.notice('Estado actualizado');await load()}catch(err){M.notice(err.message,true)}
 });
 document.querySelectorAll('[data-status]').forEach(b=>b.addEventListener('click',async()=>{try{await M.api('/api/driver/status','POST',{status:b.dataset.status});if(b.dataset.status==='off')await stopGPS();await load()}catch(err){M.notice(err.message,true)}}));
 async function stopGPS(){if(gpsWatch!==null){navigator.geolocation.clearWatch(gpsWatch);gpsWatch=null;}try{await M.api('/api/driver/location/stop','POST',{})}catch(e){}el('gps-status').textContent='GPS detenido. Las posiciones anteriores caducan.';if(currentDriver)delete currentDriver.location;mapCurrent();}
 el('gps-start').addEventListener('click',async()=>{try{const d=(await M.api('/api/mine')).driver;if(d.status==='off'||d.suspended)throw Error('Primero entra en servicio');if(!navigator.geolocation)throw Error('Geolocalización no disponible');if(gpsWatch!==null)return;
  gpsWatch=navigator.geolocation.watchPosition(async p=>{if(gpsSending||Date.now()-lastSent<12000)return;gpsSending=true;try{const o=await M.api('/api/driver/location','POST',{lat:p.coords.latitude,lng:p.coords.longitude,accuracy_m:p.coords.accuracy,consent:true});lastSent=Date.now();if(currentDriver){currentDriver.location={lat:p.coords.latitude,lng:p.coords.longitude,updated_at:o.updated_at,source:'device'}};el('gps-status').textContent=`GPS enviado · precisión ±${Math.round(o.accuracy_m)} m · ${o.updated_at}`;if(selected)mapCurrent();}catch(e){el('gps-status').textContent='Error GPS: '+e.message}finally{gpsSending=false;}},e=>{el('gps-status').textContent='GPS no disponible: '+e.message;stopGPS()},{enableHighAccuracy:true,maximumAge:0,timeout:20000});el('gps-status').textContent='Esperando permiso GPS...';
 }catch(e){M.notice(e.message,true)}});
 el('gps-stop').addEventListener('click',stopGPS);
 async function loadQR(){try{const r=await M.api('/api/driver/referral');const a=document.createElement('a');a.href=r.url||'#';a.textContent=r.url?new URL(r.url,location.origin).href:'QR revocado';a.target='_blank';a.rel='noopener noreferrer';el('qr-box').innerHTML=`${r.qr_url?'<img src="'+M.esc(r.qr_url)+'" alt="Código QR de afiliación" style="width:180px;max-width:100%"><br>':''}<span class="tag">Clientes registrados por mi QR: ${r.count}</span><p class="tiny">En local 127.0.0.1 el QR NO sirve desde otro teléfono; publicar HTTPS antes de compartir.</p>`;el('qr-box').appendChild(a)}catch(e){el('qr-box').textContent='QR no disponible: '+e.message}}
 el('refresh').addEventListener('click',load);el('logout').addEventListener('click',async()=>{await stopGPS();try{await M.logout()}catch(e){M.notice(e.message,true)}});
 await load();await loadQR();setInterval(()=>{if(!document.hidden)load()},9000);
})();

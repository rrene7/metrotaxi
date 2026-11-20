'use strict';(async()=>{
 const M=MTCloud, el=id=>document.getElementById(id);let coords=null,destCoords=null,logged=false,lastTrips=[],selected=null,lastMapSelection=null,trackingActive=false,roadView=false;
 const token=new URLSearchParams(location.search).get('referido')||'';

 const passengerStatuses={pending:'Buscando taxi',offered:'Buscando taxi',accepted:'Taxi confirmado',inprogress:'En viaje',done:'Finalizada',cancelled:'Cancelada'};
 const passengerProgress={pending:'Metro Taxi recibió tu solicitud y está buscando una unidad.',
   offered:'Metro Taxi está buscando una unidad.',
   accepted:'Tu conductor confirmó la carrera y va hacia la recogida.',
   inprogress:'Tu viaje está en curso.',
   done:'Tu viaje ha finalizado.',
   cancelled:'Tu solicitud fue cancelada.'};
 function selectTab(tab){
   document.querySelectorAll('.customer-pane').forEach(node=>node.classList.toggle('hidden',node.id!==tab));
   document.querySelectorAll('[data-customer-tab]').forEach(btn=>btn.classList.toggle('tab-selected',btn.dataset.customerTab===tab));
   if(tab==='customer-active')map.refresh?.();
 }
 document.querySelectorAll('[data-customer-tab]').forEach(btn=>btn.addEventListener('click',()=>selectTab(btn.dataset.customerTab)));

 const map=MetroMap.make({id:'map-cliente',onChoose:(type,lat,lng)=>{
   if(type==='pickup'){coords={pickup_lat:lat,pickup_lng:lng};if(!el('pickup').value)el('pickup').value='Punto marcado en el mapa';M.text('gps-info',`Recogida marcada: ${lat.toFixed(5)}, ${lng.toFixed(5)}. Confirma la referencia.`)}
   else{destCoords={dest_lat:lat,dest_lng:lng};if(!el('dest').value)el('dest').value='Destino marcado en el mapa';M.text('gps-info',`Destino marcado: ${lat.toFixed(5)}, ${lng.toFixed(5)}. Confirma los datos.`)}
   showSelected();
 }});
 async function verifyReferral(){if(!token)return;try{const r=await M.api('/api/referral/'+encodeURIComponent(token));el('referral-info').textContent=`Registro por QR de la unidad ${r.unit} (${r.station}). Tu cuenta y las próximas carreras serán administradas por Metro Taxi.`;el('referral-info').classList.remove('hidden');}catch(_){el('referral-info').textContent='QR no válido o revocado. Puedes registrarte normalmente en Metro Taxi, sin atribución al conductor.';el('referral-info').classList.remove('hidden');}}
 function showSelected(){
  const changed=selected!==lastMapSelection;
  if(changed){map.clearRoute();lastMapSelection=selected;roadView=false;}
  if(selected){const t=lastTrips.find(x=>x.id===selected);
   if(t){const p=[];
    if(MetroMap.good(t.pickup_lat,t.pickup_lng))p.push({lat:t.pickup_lat,lng:t.pickup_lng,kind:'pickup',name:'Recogida MT-'+t.id});
    if(MetroMap.good(t.dest_lat,t.dest_lng))p.push({lat:t.dest_lat,lng:t.dest_lng,kind:'destination',name:'Destino MT-'+t.id});
    if(t.driver?.confirmed && t.driver.location && MetroMap.good(t.driver.location.lat,t.driver.location.lng))p.push({lat:t.driver.location.lat,lng:t.driver.location.lng,kind:'driver',name:t.driver.name,detail:'GPS real reciente '+t.driver.location.updated_at});
    map.update(p,changed);
    if(trackingActive && !roadView){
      const segment=MetroTracking.segment(t,MetroMap.good);
      if(segment){map.route(segment.start,segment.end,{fit:changed});el('tracking-info').textContent=segment.live?'GPS del taxista actualizado: '+t.driver.location.updated_at+'. Línea punteada: distancia directa, no tiempo de llegada.':'Sin GPS reciente del taxista. Se muestra solo el trayecto de referencia entre recogida y destino.';}
      else {map.clearRoute();el('tracking-info').textContent='Esperando ubicación GPS reciente y puntos válidos para el recorrido.';}
    }
    return;}}
  const p=[];if(coords&&MetroMap.good(coords.pickup_lat,coords.pickup_lng))p.push({lat:coords.pickup_lat,lng:coords.pickup_lng,kind:'pickup',name:'Mi recogida marcada'});
  if(destCoords&&MetroMap.good(destCoords.dest_lat,destCoords.dest_lng))p.push({lat:destCoords.dest_lat,lng:destCoords.dest_lng,kind:'destination',name:'Mi destino marcado'});
  map.update(p,p.length>0);
  if(trackingActive){map.clearRoute();el('tracking-info').textContent='Selecciona una carrera activa para iniciar el seguimiento.';}
 }
 async function render(){try{const s=await M.me();logged=s.authenticated&&s.user.role==='customer';el('auth').classList.toggle('hidden',logged);el('account').classList.toggle('hidden',!logged);if(logged){selectTab('customer-active');await load();}else if(s.authenticated)M.notice('Una sesión de personal está abierta. Usa una ventana privada para la cuenta del pasajero.',true)}catch(e){M.notice(e.message,true)}}
 async function load(){if(!logged)return;try{const [data,ms]=await Promise.all([M.api('/api/customer/trips'),M.api('/api/messages')]);lastTrips=data.trips;el('account-label').textContent=data.account.name+' · '+data.account.phone+' · '+(data.account.phone_verified?'Teléfono verificado':'Teléfono no verificado');
  const active=data.trips.filter(t=>!['done','cancelled'].includes(t.status));
  const history=data.trips.filter(t=>['done','cancelled'].includes(t.status));
  if(!active.some(t=>t.id===selected)){selected=active[0]?.id||null;trackingActive=Boolean(selected);roadView=false;}
  el('trips').innerHTML=active.length?active.map(t=>{
   const d=t.driver?.confirmed?t.driver:null;
   const photo=d?.photo_url?`<img class="card-photo" src="${M.esc(d.photo_url)}" alt="Foto del conductor confirmado">`:'<span class="tag">Foto no disponible</span>';
   const driverInfo=d?`<div class="row">${photo}<div><b>🚕 ${M.esc(d.name)} · ${M.esc(d.unit)}</b><p>Placa: ${M.esc(d.plate||'Por registrar')}</p></div></div>`:'';
   const status=passengerStatuses[t.status]||'Actualizando';
   const hasMap=Boolean(d&&MetroMap.good(t.pickup_lat,t.pickup_lng));
   return `<article class="item"><div class="row between"><strong>Carrera #MT-${t.id}</strong><span class="status">${status}</span></div><p class="customer-progress">${M.esc(passengerProgress[t.status]||'Actualizando estado...')}</p><p><b>Recogida:</b> ${M.esc(t.pickup)}</p><p><b>Destino:</b> ${M.esc(t.destination||'Por confirmar')}</p>${driverInfo}<div class="actions">${hasMap?`<button class="button" data-map="${t.id}">Ver mi taxi en el mapa</button>`:''}${['pending','offered'].includes(t.status)?`<button class="button danger" data-cancel="${t.id}">Cancelar</button>`:''}</div></article>`;
  }).join(''):'<p class="muted">No tienes una carrera activa.</p>';
  el('trip-history').innerHTML=history.length?history.map(t=>`<article class="item"><div class="row between"><strong>#MT-${t.id}</strong><span class="status">${passengerStatuses[t.status]||'Finalizada'}</span></div><p>Recogida: ${M.esc(t.pickup)}</p><p>Destino: ${M.esc(t.destination||'No registrado')}</p></article>`).join(''):'<p class="muted">Aún no tienes carreras anteriores.</p>';
  el('messages').innerHTML=ms.messages.length?ms.messages.slice().reverse().map(m=>`<article class="item"><b>${m.sender==='customer'?'Tú':'Central Metro Taxi'}</b><p>${M.esc(m.body)}</p></article>`).join(''):'<p>Sin mensajes.</p>';
  showSelected();
 }catch(e){el('trips').innerHTML=`<div class="error">${M.esc(e.message)} <button class="button" data-retry="1">Reintentar</button></div>`}}
 for(const [form,endpoint,fn] of [
  ['register','/api/customer/register',()=>({name:el('r-name').value,phone:el('r-phone').value,password:el('r-password').value,consent:el('r-consent').checked,referral_token:token})],
  ['login','/api/customer/login',()=>({phone:el('l-phone').value,password:el('l-password').value})]
 ])el(form).addEventListener('submit',async e=>{e.preventDefault();try{await M.api(endpoint,'POST',fn());await render();M.notice('Sesión iniciada')}catch(err){M.notice(err.message,true)}});
 el('gps').addEventListener('click',()=>{if(!navigator.geolocation)return M.notice('GPS no disponible; indica referencia manual',true);M.text('gps-info','Solicitando autorización GPS...');navigator.geolocation.getCurrentPosition(pos=>{coords={pickup_lat:pos.coords.latitude,pickup_lng:pos.coords.longitude,pickup_accuracy_m:pos.coords.accuracy};el('gps-info').textContent=`GPS autorizado · precisión ±${Math.round(pos.coords.accuracy)} m. Verifica la entrada.`;if(!el('pickup').value)el('pickup').value='Mi ubicación actual';showSelected();},err=>{coords=null;M.text('gps-info','GPS no disponible: '+err.message+'. Marca el mapa o usa referencia.')},{enableHighAccuracy:true,timeout:20000,maximumAge:0});});
 el('pick-pickup').addEventListener('click',()=>map.pick('pickup'));
 el('pick-destination').addEventListener('click',()=>map.pick('destination'));
 el('request').addEventListener('submit',async e=>{e.preventDefault();try{const b={station:el('station').value,pickup:el('pickup').value,destination:el('dest').value,reference:el('reference').value,consent:el('trip-consent').checked,...(coords||{}),...(destCoords||{})};const r=await M.api('/api/requests','POST',b);M.notice('Carrera #MT-'+r.id+' enviada a la central');selected=r.id;trackingActive=true;roadView=false;coords=null;destCoords=null;el('request').reset();M.text('gps-info','Sin coordenadas nuevas.');await load()}catch(err){M.notice(err.message,true)}});
 async function showRoute(tid,byRoad=false){
  selected=tid;trackingActive=true;showSelected();
  const t=lastTrips.find(x=>x.id===tid),seg=MetroTracking.segment(t,MetroMap.good);
  if(!seg){M.notice('Faltan dos puntos válidos para el recorrido. Espera GPS reciente del taxista o marca recogida y destino.',true);return;}
  if(byRoad){roadView=true;await map.streetRoute(seg.start,seg.end);el('tracking-info').textContent='Ruta vial calculada una sola vez mediante proveedor externo de pruebas; no es seguimiento GPS continuo.';}
  else {roadView=false;await map.route(seg.start,seg.end,{fit:true});}
 }
 el('trips').addEventListener('click',async e=>{
  if(e.target.closest('[data-retry]'))return load();const a=e.target.closest('[data-map]'),c=e.target.closest('[data-cancel]');
  if(a){selectTab('customer-active');await showRoute(Number(a.dataset.map));el('route-by-road').classList.remove('hidden');return;}
  if(c)try{await M.api('/api/trips/cancel','POST',{trip_id:Number(c.dataset.cancel)});await load();M.notice('Solicitud cancelada')}catch(err){M.notice(err.message,true)}
 });
 el('route-by-road').addEventListener('click',()=>{if(selected)showRoute(selected,true)});
 el('message-form').addEventListener('submit',async e=>{e.preventDefault();try{await M.api('/api/messages','POST',{body:el('message-body').value});el('message-body').value='';M.notice('Mensaje enviado a la central');await load()}catch(err){M.notice(err.message,true)}});
 el('refresh').addEventListener('click',load);el('logout').addEventListener('click',async()=>{try{await M.logout()}catch(e){M.notice(e.message,true)}});
 await verifyReferral();await render();setInterval(()=>{if(logged && !document.hidden)load()},10000);
})();

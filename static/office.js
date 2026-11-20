'use strict';
(async()=>{
 const M=window.MT,$=M.$;
 let role='',config=null,map=null,drivers=[],trips=[],messages=[],incidents=[],stats=null,referrals=null,shifts=[],dispatch=null,driverMarkers=[],pointMarkers=[],selectedId=null,selectedUnit=null,
     pointDraft={pickup_lat:null,pickup_lng:null,dest_lat:null,dest_lng:null};
 try{let me=await M.who();if(!me.authenticated||!['admin','operator'].includes(me.user.role)){location.replace(me.authenticated&&me.user.role==='customer'?'/cliente':me.authenticated&&me.user.role==='driver'?'/conductor':'/ingresar');return}role=me.user.role;$('currentuser').textContent=me.user.username+' · '+(role==='admin'?'Administrador':'Operador');
     config=await M.config();$('provider').textContent=config.tile_url.includes('tile.openstreetmap.org')?'OpenStreetMap (demostración)': 'Proveedor personalizado (revisar licencia y costos)';
     map=M.getMap('officemap',config,e=>{
       if(!selectedTrip())return M.show('Primero elige una carrera del listado');
       const mode=document.querySelector('input[name="pointmode"]:checked').value;
       pointDraft[mode+'_lat']=Math.round(e.latlng.lat*1e7)/1e7;
       pointDraft[mode+'_lng']=Math.round(e.latlng.lng*1e7)/1e7;
       drawMarkers();updatePointText();M.show('Punto marcado en el mapa; guarda para asociarlo al servicio');
     });
 }catch(e){M.show(e.message);return}
 function selectedTrip(){return trips.find(t=>t.id===selectedId)}
 function selectedDriver(){return drivers.find(d=>d.id===selectedUnit)}
 function time(t){try{return t?new Date(t).toLocaleString('es-PA',{dateStyle:'short',timeStyle:'short'}):'Sin registro'}catch{return 'No disponible'}}
 function coords(lat,lng){return lat==null||lng==null?'No marcado':`${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`}
 function renderUnit(){
   const d=selectedDriver();
   if(!d){$('unitdetail').textContent='Selecciona una unidad del listado para consultar su ficha (personal autorizado).';return}
   $('unitdetail').innerHTML=`<h3>🚕 ${M.esc(d.unit)} · ${M.esc(d.name)}</h3><p><b>Sede:</b> ${M.esc(d.station)}</p><p><b>Placa:</b> ${M.esc(d.plate||'Pendiente')}</p><p><b>Vehículo:</b> ${M.esc([d.vehicle_make,d.vehicle_model,d.vehicle_color,d.vehicle_year].filter(Boolean).join(' · ')||'Por registrar')}</p><p><b>Fotografía:</b> ${d.has_photo?'Cargada por administración':'Pendiente de carga'}</p><p><b>Estado:</b> ${M.badge(d.status)} ${d.suspended?M.badge('cancelled'):''}</p><p><b>Ubicación:</b> ${d.lat===null||d.lng===null?'SIN GPS':d.simulated?'SIMULADA · '+coords(d.lat,d.lng):'GPS recibido del dispositivo · '+coords(d.lat,d.lng)}</p><p><b>Última actualización de ubicación:</b> ${M.esc(time(d.updated_at))} (${d.simulated?'simulación, NO GPS real': 'GPS del dispositivo; puede estar desactualizado, verificar hora y precisión'})</p><p><b>Carreras finalizadas en esta prueba:</b> ${d.completed}</p><p><b>Rechazos registrados:</b> ${d.rejected_count||0}</p><p><b>Suspensión:</b> ${d.suspended?'Sí':'No'}</p>`;
 }
 function drawMarkers(){
  if(!map)return;
  driverMarkers.forEach(m=>map.removeLayer(m));pointMarkers.forEach(m=>map.removeLayer(m));driverMarkers=[];pointMarkers=[];
  const station=$('stationfilter').value;
  drivers.filter(d=>station==='all'||d.station===station).forEach(d=>{
   const marker=M.marker(map,d.lat,d.lng,d.status,`${M.esc(d.unit)} · ${M.esc(d.name)} · ${M.esc(d.station)} · ${M.esc(d.status)} (SIMULADO)`);
   if(marker){marker.on('click',()=>{selectedUnit=d.id;renderUnit()});driverMarkers.push(marker)}
  });
  for(let [type,lat,lng] of [['pickup','pickup_lat','pickup_lng'],['dest','dest_lat','dest_lng']]){
   let marker=M.marker(map,pointDraft[lat],pointDraft[lng],type,type==='pickup'?'Punto de recogida':'Punto de destino');
   if(marker)pointMarkers.push(marker)
  }
 }
 function updatePointText(){$('pointtext').textContent=`Recogida: ${coords(pointDraft.pickup_lat,pointDraft.pickup_lng)} · Destino: ${coords(pointDraft.dest_lat,pointDraft.dest_lng)}`}
 function setSelection(id){
  const t=trips.find(x=>x.id===id);if(!t)return;
  selectedId=id;
  pointDraft={pickup_lat:t.pickup_lat,pickup_lng:t.pickup_lng,dest_lat:t.dest_lat,dest_lng:t.dest_lng};
  $('tripdetail').innerHTML=`<h3>#MT-${t.id} · ${M.esc(t.name)} ${M.badge(t.status)}</h3><p><b>Teléfono:</b> ${M.esc(t.phone)} · <b>Sede:</b> ${M.esc(t.station)}</p><p><b>Recogida:</b> ${M.esc(t.pickup)}</p><p><b>Destino:</b> ${M.esc(t.destination||'Por confirmar')}</p><p><b>Provincia / distrito / corregimiento:</b> ${M.esc([t.province,t.district,t.corregimiento].filter(Boolean).join(' / ')||'Sin indicar')}</p><p><b>Pendiente de verificación:</b> ${M.esc(t.location_pending||'No')}</p><p><b>Comunidad / barriada:</b> ${M.esc([t.community,t.barriada].filter(Boolean).join(' / ')||'—')}</p><p><b>Calle / casa:</b> ${M.esc([t.street,t.house].filter(Boolean).join(' / ')||'—')}</p><p><b>Referencia:</b> ${M.esc(t.reference||'—')}</p><p><b>Posición de recogida:</b> ${t.pickup_lat!=null&&t.pickup_lng!=null?M.esc(coords(t.pickup_lat,t.pickup_lng))+' · '+(t.pickup_accuracy_m!=null?'precisión estimada ±'+Number(t.pickup_accuracy_m).toFixed(0)+' m (dato del dispositivo, no verificado)':'punto marcado sin precisión GPS'):'sin coordenadas, confirmar con cliente'}</p><p><b>Canal:</b> ${M.esc(t.channel)}</p><p><b>Tarifa registrada:</b> ${t.price==null?'Pendiente':`B/. ${Number(t.price).toFixed(2)}`} (no representa cobro)</p>`;
  $('fare').value=t.price??'';
  const candidates=drivers.filter(d=>d.station===t.station&&d.status==='available'&&!d.suspended);
  $('driverassign').innerHTML=candidates.length?candidates.map(d=>`<option value="${d.id}">${M.esc(d.unit)} · ${M.esc(d.name)} (disponible)</option>`).join(''):'<option value="">Sin conductores disponibles</option>';
  $('assign').disabled=t.status!=='pending'||!candidates.length;
  $('canceltrip').disabled=['done','cancelled'].includes(t.status);
  updatePointText();drawMarkers();
  if(map&&pointDraft.pickup_lat!==null&&pointDraft.pickup_lng!==null)map.panTo([pointDraft.pickup_lat,pointDraft.pickup_lng]);
  renderTrips();
 }
 function renderTrips(){
  let station=$('stationfilter').value;let filtered=trips.filter(t=>station==='all'||t.station===station);
  $('tripslist').innerHTML=filtered.length?filtered.map(t=>`<article class="item ${selectedId===t.id?'selected':''}"><div class="row between"><strong>#MT-${t.id} · ${M.esc(t.name)}</strong>${M.badge(t.status)}</div><p>📍 ${M.esc(t.pickup)} → ${M.esc(t.destination||'Por confirmar')}</p><p><b>Canal:</b> ${M.esc(t.channel)} · 🏢 ${M.esc(t.station)} · 🚕 ${t.driver_id?M.esc(drivers.find(d=>d.id===t.driver_id)?.unit||'Asignado'):'Sin asignar'} · ${M.esc(time(t.created_at))}</p><button class="btn small" data-trip="${t.id}">${selectedId===t.id?'Seleccionado':'Ver y despachar'}</button></article>`).join(''):'<p class="small">No hay solicitudes para esta sede.</p>';
 }
 function renderDrivers(){
  let station=$('stationfilter').value;let ds=drivers.filter(d=>station==='all'||d.station===station);
  $('driverslist').innerHTML=ds.map(d=>`<article class="item"><div class="row between"><b>${M.esc(d.unit)} · ${M.esc(d.name)}</b>${M.badge(d.status)}</div><p>🏢 ${M.esc(d.station)} · ↩️ Rechazos: ${d.rejected_count||0} · 🕓 ${d.simulated?'GPS simulado':'GPS dispositivo'}: ${M.esc(time(d.updated_at))} · Carreras: ${d.completed}</p><div class="row"><button class="btn small" data-driver="${d.id}">Ficha</button>${role==='admin'?`<button class="btn small" data-suspend="${d.id}" data-value="${d.suspended?0:1}">${d.suspended?'Reactivar':'Suspender'}</button>`:''}</div></article>`).join('')||'<p class="small">Sin taxis</p>';
 }
 function renderMessages(){
   $('messageslist').innerHTML=messages.length?messages.map(m=>`<article class="item"><div class="row between"><b>#${m.id} · ${M.esc(m.name)}</b><span class="pill">${M.esc(time(m.created_at))}</span></div><p><b>Contacto:</b> ${M.esc(m.phone)}</p><p>${M.esc(m.body)}</p><p><b>Respuesta:</b> ${M.esc(m.response||'Pendiente')}</p><button class="btn small" data-reply="${m.id}">Responder al cliente</button></article>`).join(''):'<p class="small">Aún no hay mensajes de clientes.</p>';
 }
 function renderShifts(){
   $('shiftrows').innerHTML=shifts.length?shifts.map(sh=>`<tr><td>${M.esc(sh.unit)}</td><td>${M.esc(sh.station)}</td><td>${M.esc(time(sh.started_at))}</td><td>${sh.ended_at?M.esc(time(sh.ended_at)):'🟢 Turno abierto'}</td></tr>`).join(''):'<tr><td colspan="4">Aún no hay turnos registrados</td></tr>';
 }
 function renderStats(){
   if(!stats)return;
   const a=stats.totals;
   $('operationstats').innerHTML=`<div class="row" style="gap:20px; flex-wrap:wrap"><span><b>${a.total||0}</b> solicitudes</span><span><b>${a.completed||0}</b> finalizadas</span><span><b>${a.pending||0}</b> pendientes</span><span><b>B/. ${Number(a.fares_completed||0).toFixed(2)}</b> tarifas registradas de finalizadas</span></div><p class="tiny">Datos ficticios/acumulados. No es un reporte de dinero recibido.</p>`;
   $('statsdrivers').innerHTML=stats.by_driver.map(d=>`<tr><td>${M.esc(d.unit)}</td><td>${M.esc(d.station)}</td><td>${d.completed_trips}</td><td>${d.rejected_count}</td><td>${Number(d.fares_completed||0).toFixed(2)}</td></tr>`).join('');
 }
 function renderReferrals(){
   if(!referrals)return;
   $('referralcounts').innerHTML=referrals.by_driver.map(d=>`<tr><td>${M.esc(d.unit)}</td><td>${M.esc(d.station)}</td><td>${d.registered}</td><td>${role==='admin'?`<button class="btn small" data-rotate="${d.id}" type="button">Revocar / regenerar QR</button>`:'Solo lectura'}</td></tr>`).join('');
   $('referralcustomers').innerHTML=referrals.customers.length?referrals.customers.map(c=>`<tr><td>${M.esc(time(c.registered_at))}</td><td>${M.esc(c.name)}</td><td>${M.esc(c.phone)}</td><td>${M.esc(c.unit)}</td><td>${c.phone_verified?'Verificado':'Pendiente'}</td></tr>`).join(''):'<tr><td colspan="5">Sin registros QR aún</td></tr>';
 }
 function renderIncidents(){
   const selected=$('incidentdriver').value;
   $('incidentdriver').innerHTML=drivers.map(d=>`<option value="${d.id}">${M.esc(d.unit)} · ${M.esc(d.name)}</option>`).join('');
   if(drivers.some(d=>String(d.id)===selected))$('incidentdriver').value=selected;
   $('incidentslist').innerHTML=incidents.length?incidents.map(i=>`<article class="item"><div class="row between"><b>#${i.id} · ${M.esc(i.unit)} · ${M.esc(i.type.replaceAll('_',' '))}</b><span class="pill ${i.status==='open'?'warn':'ok'}">${i.status==='open'?'Por revisar':'Revisado'}</span></div><p>${M.esc(i.details)}</p><p>Registrado por: ${M.esc(i.actor)} · ${M.esc(time(i.created_at))} ${i.trip_id?' · Carrera #MT-'+i.trip_id:''}</p>${role==='admin'&&i.status==='open'?`<button class="btn small" data-review="${i.id}">Marcar revisado</button>`:''}</article>`).join(''):'<p class="small">No hay incidentes registrados.</p>';
 }
 async function load(){
  try{
   let [fleet,tripResponse,msg,report,incidentReport,referralReport,shiftsReport,dispatchSettings]=await Promise.all([M.api('/api/fleet'),M.api('/api/trips'),M.api('/api/messages'),M.api('/api/stats'),M.api('/api/incidents'),M.api('/api/referrals'),M.api('/api/shifts'),M.api('/api/dispatch/settings')]);
   drivers=fleet.drivers;trips=tripResponse.trips;messages=msg.messages;stats=report;incidents=incidentReport.incidents;referrals=referralReport;shifts=shiftsReport.shifts;dispatch=dispatchSettings;
   let s=$('stationfilter').value,d=drivers.filter(x=>s==='all'||x.station===s),t=trips.filter(x=>s==='all'||x.station===s);
   $('availablecount').textContent=d.filter(x=>x.status==='available'&&!x.suspended).length;
   $('busycount').textContent=d.filter(x=>x.status==='busy').length;
   $('pendingcount').textContent=t.filter(x=>x.status==='pending').length;
   $('donecount').textContent=t.filter(x=>x.status==='done').length;
   $('refreshed').textContent=new Date().toLocaleTimeString('es-PA');
   renderTrips();renderDrivers();refreshPhotoDriverPicker();renderUnit();renderMessages();renderStats();renderIncidents();renderReferrals();renderShifts();drawMarkers();
   $('dispatch-mode').value=dispatch.mode;$('dispatch-mode').disabled=role!=='admin';$('dispatch-save').disabled=role!=='admin';
   $('dispatch-notice').textContent=dispatch.mode==='manual'?'Solo despacho manual. El sistema nunca asignará una carrera automáticamente.':'Automático PILOTO activado: espera al menos 2 minutos sin asignación; usa solo GPS recientes de conductor y recogida explícita. Revisa las carreras en central.';
   if(selectedId&&!selectedTrip()){selectedId=null;$('tripdetail').textContent='Selecciona una carrera'}
  }catch(e){M.show(e.message)}
 }
 $('mapdrawer').addEventListener('toggle',()=>{if(map&&$('mapdrawer').open)setTimeout(()=>map.invalidateSize(),100)});
 function refreshPhotoDriverPicker(){
  const picker=$('driverphoto-select'),previous=picker.value;
  picker.innerHTML=drivers.map(d=>`<option value="${d.id}">${M.esc(d.unit)} · ${M.esc(d.name)}</option>`).join('');
  if(drivers.some(d=>String(d.id)===previous))picker.value=previous;
  showPhotoProfile();
 }
 function showPhotoProfile(){
  const d=drivers.find(v=>v.id===Number($('driverphoto-select').value));if(!d)return;
  $('driverplate').value=d.plate||''; $('vehiclemake').value=d.vehicle_make||'';$('vehiclemodel').value=d.vehicle_model||'';$('vehiclecolor').value=d.vehicle_color||'';$('vehicleyear').value=d.vehicle_year||'';
  const img=$('driverphoto-preview');img.classList.toggle('hide',!d.has_photo);
  if(d.has_photo)img.src=`/api/driver-photo/${d.id}?v=${Date.now()}`;
  else img.removeAttribute('src');
  $('driverphoto-status').textContent=d.has_photo?'Fotografía registrada para '+d.unit+' (solo acceso autorizado).':'No hay foto aprobada para '+d.unit+'.';
 }
 $('driverphoto-select').addEventListener('change',showPhotoProfile);
 $('driverphotof').addEventListener('submit',async e=>{
   e.preventDefault();
   if(role!=='admin')return M.show('Solo administración puede cambiar la ficha');
   const file=$('driverimage').files[0];let base64;
   if(file){
     if(file.size>200000||!['image/png','image/jpeg'].includes(file.type))return M.show('Foto JPG/PNG de máximo 200 KB');
     base64=await new Promise((resolve,reject)=>{
       const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);
     });
   }
   try{await M.api('/api/drivers/profile','POST',{
     driver_id:Number($('driverphoto-select').value),plate:$('driverplate').value,vehicle_make:$('vehiclemake').value,vehicle_model:$('vehiclemodel').value,vehicle_color:$('vehiclecolor').value,vehicle_year:$('vehicleyear').value,
     ...(base64?{photo_base64:base64}:{})});
     $('driverimage').value='';await load();M.show('Ficha del taxista actualizada por la administración');
   }catch(err){M.show(err.message)}
 });
 if(role!=='admin'){$('admin-driver-create').classList.add('hide');$('driver-photos-panel').classList.add('hide');}
 $('tripslist').addEventListener('click',e=>{let b=e.target.closest('[data-trip]');if(b)setSelection(Number(b.dataset.trip))});
 $('driverslist').addEventListener('click',async e=>{
  let b=e.target.closest('button');if(!b)return;
  if(b.dataset.driver){selectedUnit=Number(b.dataset.driver);renderUnit();let d=selectedDriver();if(map&&d&&d.lat!==null&&d.lng!==null)map.panTo([d.lat,d.lng])}
  else if(b.dataset.suspend){if(!confirm('¿Confirmas este cambio de estado?'))return;try{await M.api('/api/drivers/suspend','POST',{driver_id:Number(b.dataset.suspend),suspended:b.dataset.value==='1'});M.show('Acción administrativa registrada');await load()}catch(err){M.show(err.message)}}
 });
 $('messageslist').addEventListener('click',async e=>{
  let b=e.target.closest('button[data-reply]');if(!b)return;
  const msg=messages.find(x=>x.id===Number(b.dataset.reply));const value=prompt('Responder a '+msg.name+' (visible en su hilo privado):',msg.response||'');
  if(value===null||!value.trim())return;
  try{await M.api(`/api/messages/${msg.id}/reply`,'POST',{response:value});await load();M.show('Respuesta guardada en el hilo privado de la app')}catch(err){M.show(err.message)}
 });
 $('referralcounts').addEventListener('click',async e=>{
   const b=e.target.closest('button[data-rotate]');if(!b)return;
   if(!confirm('¿Revocar el QR anterior de esta unidad? Los QR impresos dejarán de funcionar.'))return;
   try{await M.api('/api/referrals/rotate','POST',{driver_id:Number(b.dataset.rotate)});
     await load();M.show('QR anterior revocado. El conductor debe imprimir el nuevo código.')
   }catch(err){M.show(err.message)}
 });
 $('stationfilter').addEventListener('change',()=>{selectedId=null;pointDraft={pickup_lat:null,pickup_lng:null,dest_lat:null,dest_lng:null};$('tripdetail').textContent='Selecciona una carrera';$('driverassign').innerHTML='<option>Selecciona una carrera</option>';updatePointText();load()});
 $('manualtripform').addEventListener('submit',async e=>{
   e.preventDefault();
   const body={name:$('manualname').value,phone:$('manualphone').value,station:$('manualstation').value,
      channel:$('manualchannel').value,pickup:$('manualpickup').value,destination:$('manualdest').value,
      reference:$('manualreference').value,consent:$('manualconsent').checked};
   try{const r=await M.api('/api/trips/manual','POST',body);
      $('manualtripform').reset();$('manualresult').textContent=`Carrera #MT-${r.id} creada. Selecciónala abajo para asignar unidad.`;
      await load();setSelection(r.id);M.show('Carrera registrada por la central');
   }catch(err){M.show(err.message)}
 });
 $('savefare').addEventListener('click',async()=>{
   const t=selectedTrip();if(!t)return M.show('Primero selecciona una carrera');
   try{await M.api('/api/trips/price','POST',{trip_id:t.id,price:$('fare').value});await load();setSelection(t.id);M.show('Tarifa registrada (no es cobro)')}catch(err){M.show(err.message)}
 });
 $('incidentform').addEventListener('submit',async e=>{
   e.preventDefault();
   const body={driver_id:Number($('incidentdriver').value),type:$('incidenttype').value,
      trip_id:$('incidenttrip').value||null,details:$('incidentdetails').value};
   try{await M.api('/api/incidents','POST',body);$('incidentdetails').value='';$('incidenttrip').value='';await load();M.show('Incidente registrado para revisión')}catch(err){M.show(err.message)}
 });
 $('incidentslist').addEventListener('click',async e=>{
   const b=e.target.closest('[data-review]');if(!b)return;
   try{await M.api('/api/incidents/review','POST',{incident_id:Number(b.dataset.review)});await load();M.show('Incidente revisado por administración')}catch(err){M.show(err.message)}
 });
 $('newdriverform').addEventListener('submit',async e=>{
   e.preventDefault();
   const body={unit:$('newdriverunit').value,name:$('newdrivername').value,
      station:$('newdriverstation').value,username:$('newdriveruser').value};
   try{let r=await M.api('/api/drivers/create','POST',body);
      const box=$('newdrivercredentials');box.classList.remove('hide');
      box.innerHTML=`<b>Cuenta creada; guarda los datos ahora. Esta contraseña no volverá a mostrarse.</b><p>Usuario: <code>${M.esc(r.username)}</code></p><p>Contraseña temporal: <code>${M.esc(r.temporary_password)}</code></p><p class="tiny">No guardes esta contraseña en GitHub. En esta demostración aún no existe cambio obligatorio al primer ingreso.</p>`;
      $('newdriverform').reset();await load();M.show('Conductor registrado, inicialmente desconectado');
   }catch(err){M.show(err.message)}
 });
 $('refresh').addEventListener('click',load);
 $('savepoints').addEventListener('click',async()=>{const t=selectedTrip();if(!t)return M.show('Selecciona una carrera');try{await M.api('/api/trips/points','POST',{trip_id:t.id,...pointDraft});await load();M.show('Puntos guardados; ubicación marcada manualmente')}catch(e){M.show(e.message)}});
 $('clearpoints').addEventListener('click',()=>{if(!selectedTrip())return;pointDraft={pickup_lat:null,pickup_lng:null,dest_lat:null,dest_lng:null};drawMarkers();updatePointText();M.show('Borrador de puntos limpiado; pulsa Guardar para aplicar')});
 $('dispatch-save').addEventListener('click',async()=>{
   if(role!=='admin')return M.show('Solo el administrador cambia la modalidad');
   const mode=$('dispatch-mode').value;
   if(mode==='auto_after_120s'&&!confirm('Modo automático piloto: ¿confirmas que únicamente se ofrezcan taxis con GPS reciente tras 2 minutos sin operador?'))return;
   try{await M.api('/api/dispatch/settings','POST',{mode});await load();M.show('Modo de despacho guardado en la central')}
   catch(e){M.show(e.message)}
 });
 $('suggest-drivers').addEventListener('click',async()=>{
   const t=selectedTrip();if(!t)return M.show('Selecciona primero una carrera');
   try{let r=await M.api('/api/dispatch/suggest?trip_id='+t.id);if(!r.candidates.length){$('driver-suggestions').textContent='No hay candidatos con GPS real reciente y precisión aceptable, o falta el punto GPS explícito de recogida. Puedes despachar manualmente.';return}
     $('driver-suggestions').innerHTML='<p class="small">Distancia EN LÍNEA RECTA, NO tiempo estimado de llegada.</p>'+r.candidates.map(d=>`<div class="row between"><span>${M.esc(d.unit)} · ${M.esc(d.name)} · ${d.straight_line_km} km aprox.</span><button type="button" class="btn small" data-pick-driver="${d.driver_id}">Seleccionar</button></div>`).join('');
   }catch(e){M.show(e.message)}
 });
 $('driver-suggestions').addEventListener('click',e=>{const btn=e.target.closest('[data-pick-driver]');if(!btn)return;const select=$('driverassign');select.value=btn.dataset.pickDriver;M.show(select.value? 'Unidad seleccionada; pulsa Asignar manualmente para confirmar':'La unidad ya no está disponible, actualiza la central')});
 $('canceltrip').addEventListener('click',async()=>{
   const t=selectedTrip();if(!t||['done','cancelled'].includes(t.status))return M.show('Selecciona una carrera abierta');
   const reason=prompt('Motivo de cancelación (quedará en la auditoría):');if(reason===null)return;
   if(!confirm('¿Confirmas la cancelación de la carrera #MT-'+t.id+'?'))return;
   try{await M.api('/api/trips/cancel','POST',{trip_id:t.id,reason});await load();setSelection(t.id);M.show('Carrera cancelada; unidad liberada si estaba ocupada')}
   catch(e){M.show(e.message)}
 });
 $('assign').addEventListener('click',async()=>{let t=selectedTrip();let did=Number($('driverassign').value);if(!t||!did)return M.show('Selecciona carrera y conductor');try{await M.api('/api/trips/assign','POST',{trip_id:t.id,driver_id:did});await load();setSelection(t.id);M.show('Carrera ofrecida al conductor elegido; pendiente de aceptación')}catch(e){M.show(e.message)}});
 $('logout').addEventListener('click',async()=>{await M.api('/api/logout','POST',{});location.href='/ingresar'});
 await load();setInterval(load,15000);
})();

'use strict';(async()=>{
 const M=MTCloud, el=id=>document.getElementById(id);let busy=false,units=[],rides=[],messageInbox=[],pointEdit=null,baseMarkers=[];
 function pointsWithPreview(){
   if(!pointEdit?.preview)return baseMarkers;
   return [...baseMarkers,{lat:pointEdit.preview.lat,lng:pointEdit.preview.lng,
      kind:pointEdit.point==='pickup'?'pickup':'destination',name:'Vista previa, pendiente de confirmar'}];
 }
 const map=MetroMap.make({id:'map-central',onChoose:(point,lat,lng)=>{
   if(!pointEdit||pointEdit.point!==point)return;
   pointEdit.preview={lat,lng};pointEdit.method='map_click';
   el('point-lat').value=lat.toFixed(6);el('point-lng').value=lng.toFixed(6);
   el('point-method').textContent='Marcado sobre mapa; confirma con el pasajero antes de guardarlo.';
   map.update(pointsWithPreview());
 }});
 function closePointEditor(){
   pointEdit=null;el('point-editor').classList.add('hidden');map.cancelPick?.();
   map.update(baseMarkers);
 }
 function editPoint(t,point){
   if(!t)return;
   const allowed=point==='pickup'?['pending','offered','accepted']:['pending','offered','accepted','inprogress'];
   if(!allowed.includes(t.status))return M.notice('Esta carrera ya no permite cambiar el punto.',true);
   const latKey=point==='pickup'?'pickup_lat':'dest_lat',lngKey=point==='pickup'?'pickup_lng':'dest_lng';
   pointEdit={tripId:t.id,point,expectedLat:t[latKey],expectedLng:t[lngKey],
     method:'provided_coordinates',preview:null};
   el('point-lat').value=t[latKey]??'';el('point-lng').value=t[lngKey]??'';
   el('point-confirm').checked=false;
   el('point-editor-info').textContent='Carrera MT-'+t.id+' · '+(point==='pickup'?'Recogida':'Destino')+
     '. Verifica el punto con el pasajero. Puedes pulsar el mapa o introducir coordenadas verificadas.';
   el('point-method').textContent='Escribe coordenadas proporcionadas por el pasajero o marca un punto en el mapa.';
   el('point-editor').classList.remove('hidden');map.pick(point);
   el('point-editor').scrollIntoView?.({behavior:'smooth',block:'center'});
 }

 try{const s=await M.me();if(!s.authenticated||!['admin','operator'].includes(s.user.role)){location.replace('/ingresar.html');return;}}
 catch(e){M.notice(e.message,true);return;}
 async function load(){if(busy)return;busy=true;
  try{const [tr,dr,st,ms]=await Promise.all([M.api('/api/trips'),M.api('/api/fleet'),M.api('/api/stats'),M.api('/api/messages')]);
   rides=tr.trips;units=dr.drivers;messageInbox=ms.messages;
   M.text('pending-count',rides.filter(t=>t.status==='pending').length);
   M.text('offered-count',rides.filter(t=>t.status==='offered').length);
   M.text('active-count',rides.filter(t=>['accepted','inprogress'].includes(t.status)).length);
   const markers=[];
   units.forEach(d=>{if(d.location && d.gps_recent)markers.push({name:d.unit+' · '+d.name,detail:d.status+' · GPS real '+d.location.updated_at,
     lat:d.location.lat,lng:d.location.lng,kind:d.status==='available'?'available':d.status==='busy'?'busy':'off'});});
   rides.filter(t=>['pending','offered','accepted','inprogress'].includes(t.status)).forEach(t=>{if(MetroMap.good(t.pickup_lat,t.pickup_lng))markers.push({name:'MT-'+t.id+' · Recogida',detail:t.status+' · '+t.pickup,lat:t.pickup_lat,lng:t.pickup_lng,kind:'pickup'})});
   rides.filter(t=>['pending','offered','accepted','inprogress'].includes(t.status)).forEach(t=>{if(MetroMap.good(t.dest_lat,t.dest_lng))markers.push({name:'MT-'+t.id+' · Destino',detail:t.status+' · '+(t.destination||'Por confirmar'),lat:t.dest_lat,lng:t.dest_lng,kind:'destination'})});
   baseMarkers=markers;map.update(pointsWithPreview());
   el('drivers').innerHTML=units.length?units.map(d=>`<article class="item"><b>${M.esc(d.unit)} · ${M.esc(d.name)}</b><p>${M.esc(d.station)} · ${M.esc(d.status)} · ${d.suspended?'Suspendido':'Habilitado'}</p><p class="muted">${d.gps_recent?'GPS reciente: '+M.esc(d.last_location_at):'Sin GPS reciente; no se dibuja en el mapa'}</p><details><summary>Expediente de vehículo</summary><form data-vehicle="${d.id}" class="field"><label>Placa</label><input name="plate" value="${M.esc(d.plate)}" maxlength="32"><label>Marca</label><input name="vehicle_make" value="${M.esc(d.vehicle_make)}" maxlength="80"><label>Modelo</label><input name="vehicle_model" value="${M.esc(d.vehicle_model)}" maxlength="80"><label>Color</label><input name="vehicle_color" value="${M.esc(d.vehicle_color)}" maxlength="40"><button class="button primary" type="submit">Guardar expediente (administrador)</button></form><p><label>Fotografía JPG/PNG hasta 1 MB (administrador)<input type="file" accept="image/jpeg,image/png" data-photo="${d.id}"></label></p></details></article>`).join(''):'<p>No hay conductores.</p>';
   el('trips').innerHTML=rides.length?rides.map(t=>{
    const options=units.filter(d=>d.station===t.station&&d.status==='available'&&!d.suspended);
    return `<article class="item"><div class="row between"><strong>#MT-${t.id} · ${M.esc(t.name)}</strong><span class="status">${M.status(t.status)}</span></div><p><b>Sede:</b> ${M.esc(t.station)} · <b>Recogida:</b> ${M.esc(t.pickup)}</p><p><b>Destino:</b> ${M.esc(t.destination||'Por confirmar')} · <b>Referencia:</b> ${M.esc(t.reference||'—')}</p><p>Contacto (solo central): ${M.esc(t.phone)}</p><div class="actions"><span class="muted">Recogida: ${t.pickup_lat==null?'Sin coordenadas':'Punto registrado'} · Destino: ${t.dest_lat==null?'Sin coordenadas':'Punto registrado'}</span></div>
<div class="actions">
${['pending','offered','accepted'].includes(t.status)?`<button class="button" data-edit-point="pickup" data-geo-trip="${t.id}">Marcar recogida en mapa</button>`:''}
${['pending','offered','accepted','inprogress'].includes(t.status)?`<button class="button" data-edit-point="destination" data-geo-trip="${t.id}">Marcar destino en mapa</button>`:''}
</div>${t.pickup_lat!=null?`<p>GPS recogida: ${Number(t.pickup_lat).toFixed(5)}, ${Number(t.pickup_lng).toFixed(5)} · <button class="button" data-point="${t.id}">Ver en mapa</button></p>`:'<p class="muted">Sin GPS: confirmar recogida por referencia.</p>'}${t.status==='pending'?`<div class="row"><select aria-label="Asignar conductor" data-select="${t.id}"><option value="">Unidad disponible</option>${options.map(d=>`<option value="${d.id}">${M.esc(d.unit)} · ${M.esc(d.name)}</option>`).join('')}</select><button class="button primary" data-assign="${t.id}">Asignar</button></div>`:''}<div class="row"><label style="min-width:140px">Tarifa registrada (USD)<input data-price="${t.id}" type="number" min="0" max="500" step="0.01" value="${t.price==null?'':t.price}"></label><button class="button" data-save-price="${t.id}">Guardar tarifa</button></div>${['pending','offered','accepted','inprogress'].includes(t.status)?`<button class="button danger" data-cancel="${t.id}">Cancelar en central</button>`:''}</article>`;
   }).join(''):'<p>Sin carreras.</p>';
   el('stats').innerHTML=`<p><strong>${st.total}</strong> carreras registradas. <strong>${st.by_status.done}</strong> terminadas. <strong>${st.by_status.cancelled}</strong> canceladas.</p><div class="grid">${st.by_unit.map(d=>`<div class="item"><b>${M.esc(d.unit)}</b> · ${d.completed} terminadas · USD ${Number(d.revenue_recorded).toFixed(2)} en tarifas registradas</div>`).join('')}</div><p class="muted">${M.esc(st.note)}</p>`;
   el('messages').innerHTML=messageInbox.length?messageInbox.map(m=>`<article class="item"><b>Cliente ID ${m.customer_id}</b> · ${M.esc(m.sender)}<p>${M.esc(m.body)}</p><button class="button" data-reply="${m.customer_id}">Responder</button></article>`).join(''):'<p>Sin mensajes.</p>';
  }catch(e){const msg=M.esc(e.message);el('trips').innerHTML=`<div class="error">${msg} <button data-retry="1" class="button">Reintentar</button></div>`;M.notice('No se pudo actualizar la central: '+e.message,true)}finally{busy=false;}}
 el('trips').addEventListener('click',async e=>{
  if(e.target.closest('[data-retry]'))return load();
  const pick=e.target.closest('[data-edit-point]');
  if(pick){const t=rides.find(x=>x.id===Number(pick.dataset.geoTrip));editPoint(t,pick.dataset.editPoint);return;}
  const a=e.target.closest('[data-assign]'),c=e.target.closest('[data-cancel]'),p=e.target.closest('[data-point]'),price=e.target.closest('[data-save-price]');
  if(p){const t=rides.find(x=>x.id===Number(p.dataset.point));if(t)map.setView(t.pickup_lat,t.pickup_lng);return;}
  if(!a&&!c&&!price)return;
  try{
   if(a){const id=a.dataset.assign,did=el('trips').querySelector(`[data-select="${id}"]`).value;if(!did)throw Error('Selecciona una unidad');await M.api('/api/trips/assign','POST',{trip_id:Number(id),driver_id:Number(did)});M.notice('Carrera ofrecida al conductor');}
   else if(c){if(!confirm('¿Cancelar esta solicitud?'))return;await M.api('/api/trips/cancel','POST',{trip_id:Number(c.dataset.cancel)});M.notice('Carrera cancelada');}
   else {const t=price.dataset.savePrice,v=el('trips').querySelector(`[data-price="${t}"]`).value;if(v==='')throw Error('Indica la tarifa registrada');await M.api('/api/trips/price','POST',{trip_id:Number(t),price:Number(v)});M.notice('Tarifa registrada');}
   await load();
  }catch(err){M.notice(err.message,true)}
 });
 el('drivers').addEventListener('submit',async e=>{const f=e.target.closest('[data-vehicle]');if(!f)return;e.preventDefault();const data=Object.fromEntries(new FormData(f).entries());try{await M.api('/api/drivers/'+f.dataset.vehicle+'/vehicle','PATCH',data);M.notice('Vehículo actualizado');await load()}catch(err){M.notice(err.message,true)}});
 el('drivers').addEventListener('change',async e=>{const f=e.target.closest('[data-photo]');if(!f||!f.files.length)return;const file=f.files[0];try{if(file.size>1000000)throw Error('Fotografía superior a 1 MB');const binary=await file.arrayBuffer(),bytes=new Uint8Array(binary);let text='';for(const ch of bytes)text+=String.fromCharCode(ch);await M.api('/api/drivers/'+f.dataset.photo+'/photo','POST',{mime:file.type,base64:btoa(text)});M.notice('Fotografía guardada por la central')}catch(err){M.notice(err.message,true)}});
 el('messages').addEventListener('click',e=>{const b=e.target.closest('[data-reply]');if(b){el('message-customer-id').value=b.dataset.reply;el('message-body').focus()}});
 el('message-form').addEventListener('submit',async e=>{e.preventDefault();try{await M.api('/api/messages','POST',{customer_id:Number(el('message-customer-id').value),body:el('message-body').value});el('message-body').value='';M.notice('Respuesta enviada al cliente');await load()}catch(err){M.notice(err.message,true)}});
 el('manual-trip').addEventListener('submit',async e=>{e.preventDefault();try{const v={name:el('m-name').value,phone:el('m-phone').value,station:el('m-station').value,pickup:el('m-pickup').value,destination:el('m-dest').value,reference:el('m-ref').value};const r=await M.api('/api/trips/manual','POST',v);M.notice('Carrera #MT-'+r.id+' registrada');el('manual-trip').reset();await load()}catch(err){M.notice(err.message,true)}});

 for(const id of ['point-lat','point-lng'])el(id).addEventListener('input',()=>{
   if(pointEdit){pointEdit.method='provided_coordinates';pointEdit.preview=null;
     el('point-method').textContent='Coordenadas escritas manualmente; confirma con el pasajero antes de guardar.';
     map.update(pointsWithPreview());}
 });
 el('point-cancel').addEventListener('click',closePointEditor);
 el('point-form').addEventListener('submit',async e=>{
   e.preventDefault();
   if(!pointEdit)return;
   const latText=el('point-lat').value.trim(),lngText=el('point-lng').value.trim();
   if(!latText||!lngText)return M.notice('Indica ambas coordenadas.',true);
   const lat=Number(latText),lng=Number(lngText);
   if(!MetroMap.good(lat,lng)||(lat===0&&lng===0))return M.notice('Coordenadas no válidas.',true);
   if(!el('point-confirm').checked)return M.notice('Confirma el punto con el pasajero.',true);
   const pending={trip_id:pointEdit.tripId,point:pointEdit.point,lat,lng,
      expected_lat:pointEdit.expectedLat,expected_lng:pointEdit.expectedLng,
      method:pointEdit.method,confirmed_with_passenger:true};
   try{await M.api('/api/trips/point','POST',pending);
     closePointEditor();await load();
     M.notice('Punto confirmado de MT-'+pending.trip_id+'. El conductor verá el cambio al actualizar su carrera.');
   }catch(err){M.notice(err.message,true);}
 });
 el('map-refresh').addEventListener('click',load);el('refresh').addEventListener('click',load);el('logout').addEventListener('click',async()=>{try{await M.logout()}catch(e){M.notice(e.message,true)}});
 await load();setInterval(()=>{if(!document.hidden)load()},10000);
})();

'use strict';(async()=>{
 const M=MTCloud, el=id=>document.getElementById(id);let busy=false,units=[],rides=[],messageInbox=[];
 const map=MetroMap.make({id:'map-central'});
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
   map.update(markers);
   el('drivers').innerHTML=units.length?units.map(d=>`<article class="item"><b>${M.esc(d.unit)} · ${M.esc(d.name)}</b><p>${M.esc(d.station)} · ${M.esc(d.status)} · ${d.suspended?'Suspendido':'Habilitado'}</p><p class="muted">${d.gps_recent?'GPS reciente: '+M.esc(d.last_location_at):'Sin GPS reciente; no se dibuja en el mapa'}</p><details><summary>Expediente de vehículo</summary><form data-vehicle="${d.id}" class="field"><label>Placa</label><input name="plate" value="${M.esc(d.plate)}" maxlength="32"><label>Marca</label><input name="vehicle_make" value="${M.esc(d.vehicle_make)}" maxlength="80"><label>Modelo</label><input name="vehicle_model" value="${M.esc(d.vehicle_model)}" maxlength="80"><label>Color</label><input name="vehicle_color" value="${M.esc(d.vehicle_color)}" maxlength="40"><button class="button primary" type="submit">Guardar expediente (administrador)</button></form><p><label>Fotografía JPG/PNG hasta 1 MB (administrador)<input type="file" accept="image/jpeg,image/png" data-photo="${d.id}"></label></p></details></article>`).join(''):'<p>No hay conductores.</p>';
   el('trips').innerHTML=rides.length?rides.map(t=>{
    const options=units.filter(d=>d.station===t.station&&d.status==='available'&&!d.suspended);
    return `<article class="item"><div class="row between"><strong>#MT-${t.id} · ${M.esc(t.name)}</strong><span class="status">${M.status(t.status)}</span></div><p><b>Sede:</b> ${M.esc(t.station)} · <b>Recogida:</b> ${M.esc(t.pickup)}</p><p><b>Destino:</b> ${M.esc(t.destination||'Por confirmar')} · <b>Referencia:</b> ${M.esc(t.reference||'—')}</p><p>Contacto (solo central): ${M.esc(t.phone)}</p>${t.pickup_lat!=null?`<p>GPS recogida: ${Number(t.pickup_lat).toFixed(5)}, ${Number(t.pickup_lng).toFixed(5)} · <button class="button" data-point="${t.id}">Ver en mapa</button></p>`:'<p class="muted">Sin GPS: confirmar recogida por referencia.</p>'}${t.status==='pending'?`<div class="row"><select aria-label="Asignar conductor" data-select="${t.id}"><option value="">Unidad disponible</option>${options.map(d=>`<option value="${d.id}">${M.esc(d.unit)} · ${M.esc(d.name)}</option>`).join('')}</select><button class="button primary" data-assign="${t.id}">Asignar</button></div>`:''}<div class="row"><label style="min-width:140px">Tarifa registrada (USD)<input data-price="${t.id}" type="number" min="0" max="500" step="0.01" value="${t.price==null?'':t.price}"></label><button class="button" data-save-price="${t.id}">Guardar tarifa</button></div>${['pending','offered','accepted','inprogress'].includes(t.status)?`<button class="button danger" data-cancel="${t.id}">Cancelar en central</button>`:''}</article>`;
   }).join(''):'<p>Sin carreras.</p>';
   el('stats').innerHTML=`<p><strong>${st.total}</strong> carreras registradas. <strong>${st.by_status.done}</strong> terminadas. <strong>${st.by_status.cancelled}</strong> canceladas.</p><div class="grid">${st.by_unit.map(d=>`<div class="item"><b>${M.esc(d.unit)}</b> · ${d.completed} terminadas · USD ${Number(d.revenue_recorded).toFixed(2)} en tarifas registradas</div>`).join('')}</div><p class="muted">${M.esc(st.note)}</p>`;
   el('messages').innerHTML=messageInbox.length?messageInbox.map(m=>`<article class="item"><b>Cliente ID ${m.customer_id}</b> · ${M.esc(m.sender)}<p>${M.esc(m.body)}</p><button class="button" data-reply="${m.customer_id}">Responder</button></article>`).join(''):'<p>Sin mensajes.</p>';
  }catch(e){const msg=M.esc(e.message);el('trips').innerHTML=`<div class="error">${msg} <button data-retry="1" class="button">Reintentar</button></div>`;M.notice('No se pudo actualizar la central: '+e.message,true)}finally{busy=false;}}
 el('trips').addEventListener('click',async e=>{
  if(e.target.closest('[data-retry]'))return load();
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
 el('map-refresh').addEventListener('click',load);el('refresh').addEventListener('click',load);el('logout').addEventListener('click',async()=>{try{await M.logout()}catch(e){M.notice(e.message,true)}});
 await load();setInterval(()=>{if(!document.hidden)load()},10000);
})();

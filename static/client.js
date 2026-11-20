'use strict';
(async()=>{
 const M=window.MT,$=M.$;
 let config, catalog, map=null, pickmode='pickup', points={pickup:null,dest:null},markers={pickup:null,dest:null},gpsAccuracy=null;
 let customerAuthenticated=false;
 const els=['name','phone','pickup','dest','province','district','corregimiento','pending','station','community','barriada','street','house','reference'];
 function val(id){return $(id).value.trim()}
 function setOptions(id,names,placeholder){$(id).innerHTML='';const first=document.createElement('option');first.textContent=placeholder;first.value='';$(id).append(first);for(let label of names){let opt=document.createElement('option');opt.value=label;opt.textContent=label;$(id).append(opt)}}
 function updateDistrict(){let p=val('province');setOptions('district',Object.keys(catalog.provincias_comarcas[p]||{}),'Selecciona distrito (si está cargado)');updateCorr()}
 function updateCorr(){let p=val('province'),d=val('district');setOptions('corregimiento',(catalog.provincias_comarcas[p]||{})[d]||[],'Selecciona corregimiento (si está cargado)')}
 function drawPoint(type){if(markers[type]&&map){map.removeLayer(markers[type]);markers[type]=null}if(points[type]&&map){markers[type]=M.marker(map,points[type].lat,points[type].lng,type,type==='pickup'?'Recogida seleccionada':'Destino seleccionado')}}
 function showPointText(){$('points').textContent='Recogida: '+(points.pickup?`${M.number(points.pickup.lat)}, ${M.number(points.pickup.lng)}`:'sin marcar')+' · Destino: '+(points.dest?`${M.number(points.dest.lat)}, ${M.number(points.dest.lng)}`:'sin marcar')}
 function setPoint(type,lat,lng){points[type]={lat:Math.round(lat*1e7)/1e7,lng:Math.round(lng*1e7)/1e7};if(type==='pickup')gpsAccuracy=null;drawPoint(type);showPointText()}
 try{
  [config,catalog]=await Promise.all([M.config(),M.api('/api/catalog')]);
  $('cataloginfo').textContent=`Catálogo INEC de ${catalog.fecha_base}; consultado ${catalog.fecha_consulta}. ${catalog.alcance} Si falta un lugar, escríbelo como pendiente de verificación.`;
  setOptions('province',Object.keys(catalog.provincias_comarcas),'Selecciona provincia o comarca');
  $('province').value='Panamá';updateDistrict();$('district').value='Panamá';updateCorr();
  map=M.getMap('clientmap',config,e=>{setPoint(pickmode,e.latlng.lat,e.latlng.lng);M.show('Punto '+(pickmode==='pickup'?'de recogida':'de destino')+' marcado en el mapa')});
  if(config.whatsapp){$('wanotice').textContent='Canal oficial configurado en este servidor: +'+config.whatsapp}else{$('wanotice').textContent='Falta configurar METRO_WHATSAPP_NUMBER con el teléfono REAL de la central. Este botón no abre un número inventado.'}
 }catch(e){M.show('Configuración incompleta: '+e.message)}
 async function refreshCustomerTrips(){
  if(!customerAuthenticated)return;
  try{const r=await M.api('/api/customer/trips');
   $('customer-label').textContent=`✅ ${r.account.name} · ${r.account.phone} · ${r.account.phone_verified?'Teléfono verificado':'Teléfono aún sin verificar (DEMO)'}`;
   $('name').value=r.account.name;$('phone').value=r.account.phone;
   $('name').readOnly=true;$('phone').readOnly=true;
   $('customer-trips').innerHTML=r.trips.length?r.trips.map(t=>{
     const driver=t.driver;
     const picture=driver?.photo_url?`<img class="driver-photo" alt="Foto de ${M.esc(driver.name)}" src="${M.esc(driver.photo_url)}">`:'<div class="driver-placeholder">Foto pendiente de autorización</div>';
     return `<article class="customer-trip"><div class="row between"><strong>Carrera #MT-${t.id}</strong>${M.badge(t.status)}</div>
       <p class="small"><b>Recogida:</b> ${M.esc(t.pickup)} · <b>Destino:</b> ${M.esc(t.destination||'Por confirmar')}</p>
       ${driver?`<div class="driver-identity">${picture}<div><b>Tu taxista: ${M.esc(driver.name)}</b><p class="small">Unidad: ${M.esc(driver.unit)} · Placa: ${M.esc(driver.plate||'Pendiente de registro')}</p>
       <p class="small">Vehículo: ${M.esc([driver.vehicle_make,driver.vehicle_model,driver.vehicle_color,driver.vehicle_year].filter(Boolean).join(' · ')||'Detalles del vehículo pendientes')}</p>
       <p class="tiny">${driver.confirmed?'✅ El taxista aceptó tu carrera.':'⏳ La central ofreció la carrera; pendiente de aceptación del taxista.'}</p>
       ${driver.location?`<p class="small"><b>📍 Última ubicación recibida:</b> ${M.esc(new Date(driver.location.updated_at).toLocaleString('es-PA'))} · precisión aproximada ±${M.esc(driver.location.accuracy_m)} m. <a target="_blank" rel="noopener noreferrer" href="https://www.openstreetmap.org/?mlat=${encodeURIComponent(driver.location.lat)}&mlon=${encodeURIComponent(driver.location.lng)}#map=16/${encodeURIComponent(driver.location.lat)}/${encodeURIComponent(driver.location.lng)}">Ver punto en el mapa</a></p>`:
       `<p class="tiny">${M.esc(driver.location_notice||'GPS del conductor disponible después de aceptar y compartir su ubicación.')}</p>`}</div></div>`:
       '<p class="small">⏳ Esperando que la central asigne una unidad. Aún no hay taxista seleccionado.</p>'}${['pending','offered'].includes(t.status)?`<button type="button" class="btn small" data-cancel-trip="${t.id}">Cancelar mi solicitud</button>`:''}</article>`
   }).join(''):'<p class="small">Aún no tienes carreras asociadas a esta cuenta. Puedes solicitar una ahora.</p>';
  }catch(e){M.show('Error al actualizar tus carreras: '+e.message)}
 }
 $('customer-trips').addEventListener('click',async e=>{
   const b=e.target.closest('[data-cancel-trip]');if(!b)return;
   if(!confirm('¿Cancelar esta solicitud de Metro Taxi?'))return;
   try{await M.api('/api/trips/cancel','POST',{trip_id:Number(b.dataset.cancelTrip),reason:'Cancelada por el pasajero'});await refreshCustomerTrips();M.show('Solicitud cancelada correctamente')}
   catch(err){M.show(err.message)}
 });
 async function updateCustomerSession(){
  const me=await M.who();customerAuthenticated=!!(me.authenticated&&me.user.role==='customer');
  $('customer-session').classList.toggle('hide',!customerAuthenticated);
  $('customer-auth').classList.toggle('hide',customerAuthenticated);
  $('customer-trips-panel').classList.toggle('hide',!customerAuthenticated);
  if(customerAuthenticated)await refreshCustomerTrips();
  else{$('name').readOnly=false;$('phone').readOnly=false;}
 }
 $('customer-register').addEventListener('submit',async e=>{
  e.preventDefault();
  try{await M.api('/api/customer/register','POST',{name:$('account-name').value,phone:$('account-phone').value,
    password:$('account-password').value,consent:$('account-consent').checked});
    await updateCustomerSession();M.show('Cuenta de prueba creada. Ya puedes ver tus carreras nuevas.');
  }catch(err){M.show(err.message)}
 });
 $('customer-login').addEventListener('submit',async e=>{
  e.preventDefault();
  try{await M.api('/api/customer/login','POST',{phone:$('login-phone').value,password:$('login-password').value});
    await updateCustomerSession();M.show('Bienvenido a Metro Taxi.');
  }catch(err){M.show(err.message)}
 });
 $('customer-logout').addEventListener('click',async()=>{
  try{await M.api('/api/logout','POST',{});customerAuthenticated=false;
    $('name').value='';$('phone').value='';await updateCustomerSession();M.show('Sesión cerrada');
  }catch(err){M.show(err.message)}
 });
 try{await updateCustomerSession()}catch(err){M.show(err.message)}
 setInterval(()=>{if(customerAuthenticated)refreshCustomerTrips()},12000);
 $('province').addEventListener('change',updateDistrict);$('district').addEventListener('change',updateCorr);
 $('pointpickup').addEventListener('click',()=>{pickmode='pickup';$('maphelp').textContent='📍 Pulsa el mapa para marcar el punto de recogida. No se calcula por la dirección.';$('clientmap').scrollIntoView({behavior:'smooth',block:'center'})});
 $('pointdest').addEventListener('click',()=>{pickmode='dest';$('maphelp').textContent='🏁 Pulsa el mapa para marcar el destino. No se calcula por el texto de dirección.';$('clientmap').scrollIntoView({behavior:'smooth',block:'center'})});
 $('gps').addEventListener('click',()=>{
  if(!navigator.geolocation){M.show('Geolocalización no disponible en este navegador');return}
  $('gps').disabled=true;$('maphelp').textContent='Solicitando permiso al navegador. La geolocalización solo se usa si tú aceptas.';
  navigator.geolocation.getCurrentPosition(pos=>{
    setPoint('pickup',pos.coords.latitude,pos.coords.longitude);
    gpsAccuracy=Number.isFinite(pos.coords.accuracy)?Math.round(pos.coords.accuracy):null;
    // GPS provides coordinates, not a reverse-geocoded postal address.
    // Allow requesting without inventing a street name; users can add directions separately.
    if(!val('pickup'))$('pickup').value='Ubicación actual enviada por GPS';
    if(map){map.setView([pos.coords.latitude,pos.coords.longitude],16)}
    $('gps').disabled=false;$('maphelp').textContent=`Ubicación GPS capturada con autorización · Precisión informada: ${Math.round(pos.coords.accuracy)} m. Puedes corregir el punto en el mapa.`;
    M.show('Tu ubicación de recogida se marcó en el mapa');
  },err=>{$('gps').disabled=false;$('maphelp').textContent='No se pudo obtener GPS: '+err.message+'. Marca el mapa o escribe referencias manualmente.';M.show('GPS no disponible. Puedes marcar el mapa manualmente.')},
  {enableHighAccuracy:true,timeout:16000,maximumAge:0});
 });
 $('tripform').addEventListener('submit',async e=>{
  e.preventDefault();if(!$('privacy').checked)return M.show('Confirma el permiso de datos para enviar el viaje');
  const obj={};for(let id of els)obj[id==='dest'?'destination':id==='pending'?'location_pending':id]=val(id);
  obj.consent=true;obj.pickup_accuracy_m=gpsAccuracy;
  for(let [type,lat,lon] of [['pickup','pickup_lat','pickup_lng'],['dest','dest_lat','dest_lng']]){
   obj[lat]=points[type]?.lat??null;obj[lon]=points[type]?.lng??null;
  }
  try{
   let r=await M.api('/api/requests','POST',obj);
   $('tripresult').classList.remove('hide');$('tripresult').textContent=`✅ Solicitud #MT-${r.id} registrada. Queda a cargo de la central de Metro Taxi. ESTO ES UNA PRUEBA, NO SE HA ENVIADO UN TAXI.`;
   if(customerAuthenticated)await refreshCustomerTrips();
   M.show('Solicitud de prueba registrada para la piquera');$('tripresult').scrollIntoView({behavior:'smooth',block:'center'});
  }catch(err){M.show(err.message)}
 });
 $('whatsapp').addEventListener('click',()=>{
  if(!config?.whatsapp){M.show('Debes configurar el WhatsApp oficial de Metro Taxi en el servidor.');return}
  const text=`Hola, Metro Taxi. Quisiera solicitar una carrera. Nombre: ${val('name')||'por confirmar'}. Recogida: ${val('pickup')||'por confirmar'}. Referencia: ${val('reference')||'por confirmar'}. ${points.pickup?`Ubicación: https://www.openstreetmap.org/?mlat=${points.pickup.lat}&mlon=${points.pickup.lng}#map=16/${points.pickup.lat}/${points.pickup.lng}`:''}`;
  window.open('https://wa.me/'+config.whatsapp+'?text='+encodeURIComponent(text),'_blank','noopener,noreferrer');
 });
 const savedToken=sessionStorage.getItem('metro_thread');
 async function refreshThread(token){
  try{const r=await M.api('/api/thread/'+token);let t=r.thread;
   $('thread').classList.remove('hide');$('thread').textContent='💬 Tu mensaje: '+t.body+'\n\n🏢 Respuesta de Metro Taxi: '+(t.response||'Pendiente de respuesta. Puedes actualizar la página para revisar.');
   $('thread').style.whiteSpace='pre-wrap';
  }catch{sessionStorage.removeItem('metro_thread')}
 }
 if(savedToken)refreshThread(savedToken);
 $('messageform').addEventListener('submit',async e=>{
  e.preventDefault();
  try{
   const r=await M.api('/api/contact','POST',{name:val('msgname'),phone:val('msgphone'),message:val('msgbody')});
   sessionStorage.setItem('metro_thread',r.token);
   await refreshThread(r.token);M.show('Mensaje guardado en la bandeja de Metro Taxi (demo)');
  }catch(err){M.show(err.message)}
 });
 setInterval(()=>{const token=sessionStorage.getItem('metro_thread');if(token)refreshThread(token)},12000);
})();

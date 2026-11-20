'use strict';
(async()=>{
 const M=window.MT,$=M.$;
 try{let me=await M.who();if(!me.authenticated||me.user.role!=='driver'){location.replace(me.authenticated&&me.user.role==='customer'?'/cliente':me.authenticated?'/central':'/ingresar');return} $('currentuser').textContent=me.user.username;}catch(e){$('drivertrips').textContent='No se pudo verificar tu sesión. Recarga e inicia sesión nuevamente.';M.show(e.message);return}
 let gpsWatch=null,gpsSending=false,lastPositionSentAt=0,seenOffers=new Set(),firstLoad=true;
 const gpsStatus=$('gps-status');
 async function stopGps(showMessage=true){
   if(gpsWatch!==null&&navigator.geolocation)navigator.geolocation.clearWatch(gpsWatch);
   gpsWatch=null;$('gps-start').disabled=false;$('gps-stop').disabled=true;
   try{await M.api('/api/driver/location/stop','POST',{})}catch(_){/* local server may be unreachable; position expires after 120 s */}
   gpsStatus.textContent=showMessage?'GPS detenido a petición del conductor. La central dejará de compartir tu posición; si hay problemas de red caducará tras 120 segundos.':'GPS apagado porque dejaste de estar de servicio.';
 }
 $('gps-start').addEventListener('click',async()=>{
   if(!navigator.geolocation){gpsStatus.textContent='Este teléfono no permite geolocalización desde este navegador.';return}
   try{const r=await M.api('/api/mine');if(r.driver.suspended||r.driver.status==='off')return M.show('Primero ponte de servicio para compartir GPS');}
   catch(err){return M.show(err.message)}
   if(gpsWatch!==null)return;
   $('gps-start').disabled=true;$('gps-stop').disabled=false;
   gpsStatus.textContent='Solicitando permiso de ubicación al dispositivo...';
   gpsWatch=navigator.geolocation.watchPosition(async pos=>{
     const now=Date.now();if(gpsSending||now-lastPositionSentAt<12000)return;
     gpsSending=true;
     try{
       const result=await M.api('/api/driver/location','POST',{lat:pos.coords.latitude,lng:pos.coords.longitude,accuracy_m:pos.coords.accuracy,consent:true});
       lastPositionSentAt=now;
       gpsStatus.textContent=`GPS enviado a Metro Taxi: ${new Date(result.updated_at).toLocaleTimeString('es-PA')} · precisión estimada ±${Math.round(result.accuracy_m)} m. Solo funciona con esta pantalla abierta.`;
     }catch(err){gpsStatus.textContent='No se pudo enviar la ubicación: '+err.message}
     finally{gpsSending=false}
   },error=>{gpsStatus.textContent='GPS no disponible: '+error.message;stopGps(false)},
   {enableHighAccuracy:true,maximumAge:0,timeout:20000});
 });
 $('gps-stop').addEventListener('click',()=>stopGps());
 const actions={offered:[['accept','Aceptar'],['reject','Rechazar']],accepted:[['start','Iniciar carrera']],inprogress:[['complete','Finalizar carrera']]};
 // Navegación autocontenida: si /static/navigation.js falta o está bloqueado,
 // los servicios y los botones de operación deben seguir funcionando.
 function navigationPoint(lat,lng){
   if(typeof lat!=='number'||typeof lng!=='number'||!Number.isFinite(lat)||!Number.isFinite(lng)||lat < -90||lat > 90||lng < -180||lng > 180)return null;
   const point=encodeURIComponent(`${lat},${lng}`);
   return {
     waze:`https://waze.com/ul?ll=${point}&navigate=yes`,
     google:`https://www.google.com/maps/dir/?api=1&destination=${point}&travelmode=driving&dir_action=navigate`
   };
 }
 function driverNavigation(t){
   if(!t||!['accepted','inprogress'].includes(t.status))return '';
   const pickup=navigationPoint(t.pickup_lat,t.pickup_lng);
   const destination=t.status==='inprogress'?navigationPoint(t.dest_lat,t.dest_lng):null;
   let html='<div class="trip-navigation"><p class="trip-navigation-heading">🧭 Navegación de esta carrera</p>';
   if(pickup){
     html+='<p class="small">Punto de recogida registrado por el pasajero. Verifica la referencia antes de salir.</p>';
     if(typeof t.pickup_accuracy_m==='number' && Number.isFinite(t.pickup_accuracy_m))html+=`<p class="small">Precisión GPS informada: ±${Math.round(t.pickup_accuracy_m)} m.</p>`;
     html+=`<div class="row"><a class="btn primary nav-link" target="_blank" rel="noopener noreferrer" href="${pickup.waze}">🚗 Navegar a recogida con Waze</a><a class="btn nav-link" target="_blank" rel="noopener noreferrer" href="${pickup.google}">📍 Google Maps</a></div>`;
   }else{
     html+='<p class="notice">Esta carrera no contiene coordenadas de recogida. Solicita al pasajero que comparta su ubicación o pide a la central que marque el punto en el mapa.</p>';
   }
   if(destination)html+=`<div class="row"><a class="btn primary nav-link" target="_blank" rel="noopener noreferrer" href="${destination.waze}">🏁 Waze al destino</a><a class="btn nav-link" target="_blank" rel="noopener noreferrer" href="${destination.google}">Google Maps al destino</a></div>`;
   else if(t.status==='inprogress')html+='<p class="small">El destino no tiene coordenadas registradas; confírmalo con el pasajero.</p>';
   return html+'<p class="tiny">La navegación abre otra aplicación. La carrera permanece en Metro Taxi. No uses el móvil mientras conduces.</p></div>';
 }
 let loadingServices=false;

 async function load(){
  if(loadingServices)return;
  loadingServices=true;
  try{
   let r=await M.api('/api/mine');let d=r.driver;
   $('driverdetail').innerHTML=`<h2>${M.esc(d.unit)} · ${M.esc(d.name)}</h2><p><b>Sede:</b> ${M.esc(d.station)}</p><p><b>Estado:</b> ${M.badge(d.status)}</p><p><b>Vehículo:</b> ${M.esc([d.vehicle_make,d.vehicle_model,d.vehicle_color,d.vehicle_year].filter(Boolean).join(' · ')||'Ficha del vehículo pendiente')}</p><p><b>Ubicación:</b> ${d.simulated?'SIMULADA':d.location_source==='device'?'GPS del dispositivo':'SIN GPS'} · última recepción ${M.esc(d.updated_at)}</p><p><b>Turno activo desde:</b> ${M.esc(r.active_shift_since||'Sin turno abierto')}</p><p><b>Rechazos de carreras registrados:</b> ${d.rejected_count||0}</p><p><b>Suspensión:</b> ${d.suspended?'Sí':'No'}</p>`;
   const qrValid=!!r.referral_url;
   $('qrstatus').textContent=!qrValid?'QR suspendido por administración':r.public_link_configured?
     'Enlace configurado. Comprueba que sea público y HTTPS antes de imprimir.':
     '🧪 MODO LOCAL: este QR usa 127.0.0.1; NO funcionará al escanearlo desde otro teléfono. Primero publica el backend HTTPS y configura METRO_PUBLIC_BASE_URL.';
   $('reflink').value=r.referral_url||'';
   $('driverqr').style.display=qrValid&&r.qr_ready?'block':'none';
   $('driverqr').src=qrValid&&r.qr_ready?'/api/referral/qr.svg':'';
   $('refcount').textContent=`Clientes registrados por esta unidad (teléfonos sin verificar): ${r.referral_count}`;
   $('copyqr').disabled=!qrValid;$('printqr').disabled=!qrValid||!r.qr_ready;
   $('on').disabled=!!d.suspended||d.status==='busy';$('off').disabled=d.status==='busy';
   if(d.status==='off'||d.suspended){if(gpsWatch!==null)stopGps(false);$('gps-start').disabled=true}else if(gpsWatch===null)$('gps-start').disabled=false;
   const activeOffers=new Set(r.trips.filter(t=>t.status==='offered').map(t=>t.id));
   if(!firstLoad&&Array.from(activeOffers).some(id=>!seenOffers.has(id))){
      M.show('🚕 Metro Taxi: tienes una nueva carrera para aceptar');
      if('Notification' in window&&Notification.permission==='granted')new Notification('Nueva carrera de Metro Taxi',{body:'Abre la aplicación para aceptar o rechazar'});
   }
   seenOffers=activeOffers;firstLoad=false;
   $('drivertrips').innerHTML=r.trips.length?r.trips.map(t=>`<article class="item"><b>#MT-${t.id}</b> ${M.badge(t.status)}<p><b>Cliente:</b> ${M.esc(t.name)}</p><p><b>Recogida:</b> ${M.esc(t.pickup)}</p><p><b>Destino:</b> ${M.esc(t.destination||'Por confirmar')}</p><p><b>Referencia:</b> ${M.esc(t.reference||'—')}</p>${t.status==='offered'&&t.offer_expires_at?`<p class="small">⏳ Responde antes de ${M.esc(new Date(t.offer_expires_at).toLocaleTimeString('es-PA'))}. Si vence, vuelve a la central.</p>`:''}${driverNavigation(t)}<div class="row">${(actions[t.status]||[]).map(([a,lab])=>`<button class="btn ${a==='reject'?'':'primary'} small" data-action="${a}" data-trip="${t.id}">${lab}</button>`).join('')}</div></article>`).join(''):'<p class="small">Sin carreras asignadas.</p>';
  }catch(e){
    console.error('Metro Taxi: error cargando carreras',e);
    $('drivertrips').innerHTML=`<div class="notice" role="alert">No se pudieron mostrar tus carreras: ${M.esc(e.message||'Error desconocido')}. <button class="btn small" type="button" data-refresh-trips="1">Reintentar</button></div>`;
    M.show('No se pudo actualizar la lista de servicios');
  }finally{loadingServices=false}
 }
 $('drivertrips').addEventListener('click',async e=>{
  if(e.target.closest('button[data-refresh-trips]')){await load();return}
  let b=e.target.closest('button[data-action]');if(!b)return;try{let reason; if(b.dataset.action==='reject'){reason=prompt('Explica por qué rechazas la carrera. Quedará registrado en la central:');if(reason===null)return;} await M.api('/api/trips/action','POST',{trip_id:Number(b.dataset.trip),action:b.dataset.action,...(reason!==undefined?{reason}: {})});M.show('Estado actualizado en Metro Taxi');await load()}catch(err){M.show(err.message)}});
 for(let [id,status] of [['on','available'],['off','off']])$(id).addEventListener('click',async()=>{try{await M.api('/api/driver/status','POST',{status});if(status==='off')stopGps(false);await load()}catch(e){M.show(e.message)}});
 $('copyqr').addEventListener('click',async()=>{
   try{await navigator.clipboard.writeText($('reflink').value);M.show('Enlace copiado')}catch(e){
    $('reflink').select();M.show('Selecciona y copia el enlace (Ctrl+C)');
   }
 });
 $('printqr').addEventListener('click',()=>{
   if(!$('reflink').value)return;
   document.body.classList.add('printing-qr');window.print();
   setTimeout(()=>document.body.classList.remove('printing-qr'),250);
 });
 window.addEventListener('afterprint',()=>document.body.classList.remove('printing-qr'));
 $('logout').addEventListener('click',async()=>{stopGps(false);await M.api('/api/logout','POST',{});location.href='/ingresar'});
 if('Notification' in window&&Notification.permission==='default'){
   const promptButton=document.createElement('button');promptButton.type='button';promptButton.className='btn small';promptButton.textContent='Permitir avisos mientras la app esté abierta';
   $('gps-section').appendChild(promptButton);
   promptButton.addEventListener('click',async()=>{const p=await Notification.requestPermission();M.show(p==='granted'?'Avisos habilitados (solo con app activa)':'Permiso de avisos no concedido');promptButton.remove()});
 }
 await load();setInterval(load,12000);
})();

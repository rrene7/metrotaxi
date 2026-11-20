'use strict';
(async()=>{
 const M=window.MT,$=M.$;
 const token=location.pathname.split('/').pop();
 const quick=$('quick-request');
 let qrActive=false;
 let gpsPoint=null;
 const locationName='Ubicación actual enviada por GPS';

 function gpsNote(txt,hasFix=false){
   $('quickgpsstatus').textContent=txt;
   $('quickgpsstatus').classList.toggle('gps-ready',hasFix);
 }
 function setReady(ready){
   $('quickgps').disabled=!ready;
   $('quicksubmit').disabled=!ready;
 }
 function clearPoint(){
   if($('quickpickup').value.trim()===locationName)$('quickpickup').value='';
   gpsPoint=null;
   $('quickcoords').classList.add('hide');
 }
 function captureGPS(){
   if(!navigator.geolocation){gpsNote('Este navegador no permite GPS. Escribe el punto de recogida o usa el formulario con mapa.');return}
   if(!window.isSecureContext){gpsNote('El GPS exige HTTPS o localhost. Abre el enlace desde una web segura. Mientras tanto escribe la dirección manualmente.');return}
   $('quickgps').disabled=true;
   gpsNote('Solicitando permiso del dispositivo y buscando la ubicación actual...');
   navigator.geolocation.getCurrentPosition(pos=>{
     $('quickgps').disabled=false;
     const {latitude,longitude,accuracy}=pos.coords;
     if(!Number.isFinite(latitude)||!Number.isFinite(longitude)||!Number.isFinite(accuracy)){
       clearPoint();gpsNote('El dispositivo devolvió coordenadas inválidas. Intenta de nuevo.');return;
     }
     const measured=new Date(pos.timestamp||Date.now());
     gpsPoint={lat:Math.round(latitude*1e7)/1e7,lng:Math.round(longitude*1e7)/1e7,
               accuracy:Math.round(accuracy),time:measured.toLocaleTimeString('es-PA')};
     // GPS supplies coordinates, not a street address. No geocoding or guessing.
     if(!$('quickpickup').value.trim())$('quickpickup').value=locationName;
     $('quickcoords').classList.remove('hide');
     $('quickcoords').textContent=`Latitud: ${gpsPoint.lat.toFixed(6)} · Longitud: ${gpsPoint.lng.toFixed(6)} · Precisión aproximada: ±${gpsPoint.accuracy} m · ${gpsPoint.time}`;
     gpsNote(gpsPoint.accuracy>100?
       '⚠️ Ubicación detectada, pero la precisión es baja. Pulsa el botón otra vez o describe tu punto exacto en Referencia.':
       '✅ Ubicación capturada. Confirma el punto de recogida y agrega una referencia si hace falta.',true);
     $('quickgps').textContent='🔄 Actualizar mi ubicación';
   },err=>{
     $('quickgps').disabled=false;
     clearPoint();
     const labels={1:'Permiso de ubicación denegado.',2:'La señal GPS no está disponible.',3:'La búsqueda de GPS excedió el tiempo de espera.'};
     gpsNote(`${labels[err.code]||'No se pudo obtener tu ubicación.'} Puedes escribir el punto de recogida manualmente.`);
   },{enableHighAccuracy:true,timeout:20000,maximumAge:0});
 }
 $('quickgps').addEventListener('click',captureGPS);
 if(!/^[A-Za-z0-9_-]{20,64}$/.test(token)){
   $('driverreference').textContent='Código QR no válido. Puedes pedir el enlace oficial de Metro Taxi.';
   quick.classList.add('hide');
   return;
 }
 try{
   await M.who();
   const r=await M.api('/api/referral/'+encodeURIComponent(token));
   $('driverreference').textContent=`🚕 Unidad ${r.unit} · Sede ${r.station} · Afiliada a Metro Taxi. Tus carreras las administra la central.`;
   $('quickstation').value=r.station;
   $('refsubmit').disabled=false;
   qrActive=true;
   setReady(true);
 }catch(e){
   $('driverreference').textContent='Este código QR no está vigente. Solicita otro código o utiliza el portal oficial Metro Taxi.';
   quick.classList.add('hide');
   return;
 }
 $('referralform').addEventListener('submit',async e=>{
   e.preventDefault();$('refsubmit').disabled=true;
   try{
     const r=await M.api('/api/referrals/register','POST',{
       token,name:$('refname').value,phone:$('refphone').value,
       consent:$('refconsent').checked,marketing_opt_in:$('refmarketing').checked
     });
     $('referralform').classList.add('hide');$('refresult').classList.remove('hide');
     $('refresult').innerHTML=`<h2>✅ Registro recibido</h2><p>${M.esc(r.message)}</p><p>Ahora puedes pedir un taxi con tu ubicación actual, aquí mismo.</p>`;
     $('quickname').value=$('refname').value.trim();
     $('quickphone').value=$('refphone').value.trim();
     quick.open=true;
     quick.scrollIntoView({behavior:'smooth',block:'start'});
   }catch(err){$('refsubmit').disabled=false;M.show(err.message)}
 });
 $('quicktripform').addEventListener('submit',async e=>{
   e.preventDefault();
   if(!qrActive)return M.show('QR no disponible. Entra desde el sitio oficial de Metro Taxi.');
   if(!$('quickconsent').checked)return M.show('Debes autorizar los datos usados para esta solicitud');
   $('quicksubmit').disabled=true;
   try{
     const payload={
       name:$('quickname').value.trim(),phone:$('quickphone').value.trim(),
       station:$('quickstation').value,pickup:$('quickpickup').value.trim(),
       destination:$('quickdest').value.trim(),reference:$('quickreference').value.trim(),
       pickup_lat:gpsPoint?.lat??null,pickup_lng:gpsPoint?.lng??null,
       pickup_accuracy_m:gpsPoint?.accuracy??null,
       dest_lat:null,dest_lng:null,consent:true,referral_token:token
     };
     const r=await M.api('/api/requests','POST',payload);
     $('quickresult').classList.remove('hide');
     $('quickresult').textContent=`✅ Solicitud #MT-${r.id} recibida por la central de Metro Taxi. ${gpsPoint?'Se enviaron las coordenadas GPS autorizadas.':'Se envió la referencia escrita, sin GPS.'} DEMOSTRACIÓN: no se despachó ningún taxi real.`;
     M.show('Carrera registrada en la central (modo de prueba)');
     $('quickresult').scrollIntoView({behavior:'smooth',block:'center'});
   }catch(err){M.show('No se pudo solicitar: '+err.message)}
   finally{$('quicksubmit').disabled=false}
 });
})();

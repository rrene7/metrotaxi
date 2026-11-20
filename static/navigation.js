/* Metro Taxi v0.8.3 — navigation links for a driver's assigned trip.
   Use stored, explicit coordinates only. Never geocode or guess from free text. */
'use strict';
(function(root){
  function validPoint(lat, lng){
    return typeof lat === 'number' && typeof lng === 'number' &&
      Number.isFinite(lat) && Number.isFinite(lng) &&
      lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
  }
  function urls(lat, lng){
    if(!validPoint(lat,lng))return null;
    const point=encodeURIComponent(`${lat},${lng}`);
    return {
      waze:`https://waze.com/ul?ll=${point}&navigate=yes`,
      google:`https://www.google.com/maps/dir/?api=1&destination=${point}&travelmode=driving&dir_action=navigate`
    };
  }
  function navLinks(t){
    // Do not offer navigation to unaffiliated, cancelled or finished services.
    if(!t || !['accepted','inprogress'].includes(t.status))return '';
    const pickup=urls(t.pickup_lat,t.pickup_lng);
    const dest= t.status==='inprogress' ? urls(t.dest_lat,t.dest_lng) : null;
    let html='<div class="trip-navigation"><p class="trip-navigation-heading">🧭 Navegación de esta carrera</p>';
    if(pickup){
      html+='<p class="small">Destino GPS: recogida indicada por el pasajero. Comprueba la entrada o referencia antes de salir.</p>';
      if(typeof t.pickup_accuracy_m==='number' && Number.isFinite(t.pickup_accuracy_m)){
        html+=`<p class="small">Precisión estimada del GPS: ±${Math.round(t.pickup_accuracy_m)} m.</p>`;
      }
      html+=`<div class="row"><a class="btn primary nav-link" target="_blank" rel="noopener noreferrer" href="${pickup.waze}">🚗 Navegar a recogida con Waze</a>`+
            `<a class="btn nav-link" target="_blank" rel="noopener noreferrer" href="${pickup.google}">📍 Google Maps</a></div>`;
    } else {
      html+='<p class="notice">Esta solicitud no tiene coordenadas verificables de recogida. Pide a la central que el cliente use «Mi ubicación» o marque el mapa. No se puede generar una ruta desde texto libre.</p>';
    }
    if(dest){
      html+=`<p class="small">Cuando ya lleves al pasajero, puedes navegar al destino que haya marcado:</p>`+
        `<div class="row"><a class="btn dark nav-link" target="_blank" rel="noopener noreferrer" href="${dest.waze}">🏁 Waze al destino</a>`+
        `<a class="btn nav-link" target="_blank" rel="noopener noreferrer" href="${dest.google}">Google Maps al destino</a></div>`;
    }else if(t.status==='inprogress'){
      html+='<p class="small">Destino sin coordenadas: confírmalo antes de iniciar la navegación. Metro Taxi no inventa ubicaciones.</p>';
    }
    html+='<p class="tiny">Al abrir Waze o Maps, esta carrera permanece en Metro Taxi. Regresa aquí para actualizar su estado. No manipules el teléfono mientras conduces.</p></div>';
    return html;
  }
  root.MTNavigation={urls,navLinks,validPoint};
})(typeof window!=='undefined'?window:globalThis);

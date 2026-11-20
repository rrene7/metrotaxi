'use strict';
/* Metro Taxi map: additive UI. Never required for dispatch/accept/finish.
 * Positions come ONLY from GPS or explicit user map clicks; no geocoding guesses.
 * Base map uses OSM public tiles in local staging only. Configure a commercial
 * provider before a real deployment. External route demo is opt-in and local only.
 */
window.MetroMap = (() => {
  const library = [
    'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
  ];
  let libraryPromise;
  function loadLibrary() {
    if(window.L) return Promise.resolve(window.L);
    if(libraryPromise) return libraryPromise;
    libraryPromise = new Promise((resolve, reject) => {
      let i=0;
      const next=()=>{
        if(i>=library.length){reject(Error('No se pudo cargar Leaflet. Revisa Internet o la red; las carreras siguen funcionando.'));return;}
        const sc=document.createElement('script');sc.src=library[i++];sc.async=true;
        sc.onload=()=>window.L?resolve(window.L):next();sc.onerror=next;
        document.head.appendChild(sc);
      };next();
    });
    return libraryPromise;
  }
  const good = (lat,lng) => typeof lat==='number' && typeof lng==='number' && Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat)<=90 && Math.abs(lng)<=180;
  const POINTS = {Pacora:[9.0825,-79.2896], '24 de Diciembre':[9.1017,-79.3603]}; // viewport ONLY, not actual station positions
  function make(config) {
    const root=document.getElementById(config.id), status=document.getElementById(config.id+'-status');
    let map,layer,road,roadMode=null,points=[],pickMode=null,tilesReady=false,loaded=false,cb=config.onChoose||(()=>{});
    const info=(str,error=false)=>{if(status){status.textContent=str;status.classList.toggle('map-error',error)}};
    if(!root) return {ready:Promise.resolve(false), update:()=>{}, pick:()=>{}, route:async()=>{}, clearRoute:()=>{}};
    const ready=loadLibrary().then(L=>{
      const initial=POINTS[config.station]||[9.092,-79.33];
      map=L.map(root,{zoomControl:true}).setView(initial,12);
      const tiles=window.METRO_MAP_TILES_URL || (location.hostname==='127.0.0.1'||location.hostname==='localhost' ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png' : '');
      if(tiles){
        let errors=0;
        L.tileLayer(tiles,{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'}).on('tileload',()=>{tilesReady=true;if(!points.length)info('Mapa cargado. Los taxis sin GPS reciente no aparecen como puntos.')}).on('tileerror',()=>{errors++;if(errors>=3 && !tilesReady)info('No se descargan las calles; verifica Internet/proveedor. Puedes seguir usando las carreras.',true)}).addTo(map);
      }else info('Configura METRO_MAP_TILES_URL con un proveedor autorizado antes de publicar mapas.',true);
      layer=L.layerGroup().addTo(map);
      map.on('click',event=>{if(pickMode){cb(pickMode,event.latlng.lat,event.latlng.lng);pickMode=null;root.style.cursor='';}});
      loaded=true;
      setTimeout(()=>map.invalidateSize(),100);
      return true;
    }).catch(e=>{info(e.message,true);root.innerHTML='<div class="map-fallback">No se pudo abrir el mapa. El despacho sigue disponible.</div>';return false;});
    function update(items,autoZoom=false) {
      points=items.filter(p=>good(p.lat,p.lng));
      if(!loaded)return ready.then(ok=>{if(ok)update(points,autoZoom)});
      // Updating live GPS markers must not erase the route currently viewed.
      // The route is cleared explicitly when selecting another trip.
      layer.clearLayers();
      const colors={available:'#16a36c',busy:'#f3a811',off:'#7e8995',pickup:'#1f69c5',destination:'#8c48c4',driver:'#16a36c'};
      const bounds=[];
      points.forEach(p=>{
        // A taxi is represented by a small taxi symbol, not a location dot.
        const taxi=['driver','available','busy','off'].includes(p.kind);
        const dot=taxi ? window.L.marker([p.lat,p.lng],{icon:window.L.divIcon({
          className:'metro-taxi-icon',html:'<span class="taxi-glyph" aria-label="Taxi">🚕</span>',
          iconSize:[30,30],iconAnchor:[15,15]})}) :
          window.L.circleMarker([p.lat,p.lng],{radius:8,color:'#fff',weight:2,fillColor:colors[p.kind]||'#e7a71b',fillOpacity:1});
        dot.bindPopup(`<strong>${MTCloud.esc(p.name||'Punto')}</strong>${p.detail?'<div>'+MTCloud.esc(p.detail)+'</div>':''}`);
        dot.addTo(layer);bounds.push([p.lat,p.lng]);
      });
      if(autoZoom&&bounds.length) map.fitBounds(window.L.latLngBounds(bounds).pad(.23),{maxZoom:16});
      if(points.length && !road)info(`Puntos GPS visibles: ${points.length}. No se muestran ubicaciones simuladas ni vencidas.`);
    }
    function clearRoute(){if(road && loaded){map.removeLayer(road);road=null;}roadMode=null;}
    function pick(which){pickMode=which;if(loaded)root.style.cursor='crosshair';info(`Pulsa el mapa para marcar ${which==='pickup'?'recogida':'destino'}. No se calculará dirección textual automáticamente.`);}
    async function route(a,b,options={}){
      if(!good(a?.lat,a?.lng)||!good(b?.lat,b?.lng)){info('No hay dos ubicaciones GPS válidas para calcular el recorrido.',true);return;}
      await ready;if(!loaded)return;
      const coords=[[a.lat,a.lng],[b.lat,b.lng]];
      if(road && roadMode==='direct' && typeof road.setLatLngs==='function')road.setLatLngs(coords);
      else {clearRoute();road=window.L.polyline(coords,{color:'#1d6fc4',dashArray:'8 8',weight:4}).addTo(map);}
      roadMode='direct';
      if(options.fit!==false)map.fitBounds(road.getBounds().pad(.18),{maxZoom:16});
      info('Trazo punteado = línea recta, NO recorrido por calles. Puedes solicitar una ruta real de prueba.');
      return {a,b};
    }
    async function streetRoute(a,b){
      if(!good(a?.lat,a?.lng)||!good(b?.lat,b?.lng)){info('Faltan coordenadas GPS reales.',true);return;}
      await ready;if(!loaded)return;
      const testing=location.hostname==='127.0.0.1'||location.hostname==='localhost';
      const provider=window.METRO_ROUTING_BASE_URL||(testing?'https://router.project-osrm.org':'');
      if(!provider){info('Recorrido por calles no configurado. Define METRO_ROUTING_BASE_URL antes del despliegue.',true);return;}
      info('Calculando ruta de prueba. Se enviarán las dos coordenadas al proveedor externo de navegación.');
      const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),8000);
      try{
        const r=await fetch(provider.replace(/\/$/,'')+'/route/v1/driving/'+a.lng+','+a.lat+';'+b.lng+','+b.lat+'?overview=full&geometries=geojson',{signal:ctrl.signal});
        if(!r.ok)throw Error('Servicio de rutas no disponible');
        const data=await r.json();const one=data.routes?.[0],loc=one?.geometry?.coordinates;
        if(!Array.isArray(loc)||loc.length<2)throw Error('No existe una ruta vial para los puntos elegidos');
        if(road){map.removeLayer(road);road=null;}
        road=window.L.polyline(loc.map(([lng,lat])=>[lat,lng]),{color:'#1463a8',weight:5,opacity:.85}).addTo(map);roadMode='street';
        map.fitBounds(road.getBounds().pad(.15),{maxZoom:16});
        info(`Ruta vial de PRUEBA: ${(one.distance/1000).toFixed(1)} km · aprox. ${Math.round(one.duration/60)} min; no garantiza el tiempo real de llegada.`);
      }catch(e){await route(a,b);info('Falló la ruta por calles ('+e.message+'). Solo se muestra la línea recta; usa Waze para navegar.',true)}finally{clearTimeout(timer)}
    }
    return {ready,update,pick,route,streetRoute,clearRoute,refresh:()=>ready.then(()=>loaded&&map.invalidateSize()),setView:(lat,lng)=>ready.then(()=>loaded&&good(lat,lng)&&map.setView([lat,lng],16))};
  }
  return {make,good};
})();

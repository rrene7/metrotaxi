'use strict';
(function(){
const $$=id=>document.getElementById(id);
let role='cliente',state='idle',step=0;
const pick=[9.083,-79.292],dest=[9.102,-79.320],driverInitial=[9.079,-79.311];
let driver=driverInitial.slice();
const operations=[];
const buttons={idle:{cliente:[['request','Solicitar taxi']]} ,pending:{central:[['offer','Asignar MT-01']]} ,
 offered:{conductor:[['accept','Aceptar carrera'],['reject','Rechazar carrera']]} ,
 accepted:{conductor:[['move','Simular avance del taxi'],['start','Recoger e iniciar']]} ,
 inprogress:{conductor:[['move','Simular avance del taxi'],['complete','Finalizar carrera']]} ,
 complete:{cliente:[['restart','Reiniciar demostración']]},rejected:{central:[['offer','Reasignar MT-01']],cliente:[['restart','Reiniciar demostración']]}};
const texts={idle:'No hay carreras activas.',pending:'Carrera MT-DEMO pendiente en la central.',offered:'Carrera MT-DEMO ofrecida a MT-01. Esperando al conductor.',accepted:'MT-01 aceptó la carrera. El taxi se acerca a la recogida.',inprogress:'Pasajero recogido. El conductor avanza hacia el destino.',complete:'Carrera simulada finalizada.',rejected:'Carrera rechazada. La central debe reasignar.'};
let map=null,layer=null,line=null,baseOk=false,errors=0;
const mapEl=$$('map');
function log(s){operations.unshift(s);if(operations.length>7)operations.pop();}
function distance(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];}
function initMap(){
 if(!window.L){$$('tile-status').textContent='No cargó la biblioteca de mapas; los controles de la simulación siguen funcionando.';mapEl.textContent='Mapa temporalmente no disponible';return;}
 map=L.map(mapEl,{zoomControl:true}).setView([9.09,-79.30],12);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap contributors'}).on('tileload',()=>{baseOk=true;$$('tile-status').textContent='Mapa de OpenStreetMap para uso de demostración.';}).on('tileerror',()=>{errors++;if(errors>3&&!baseOk)$$('tile-status').textContent='No cargan las calles; comprueba conexión. Los marcadores y controles siguen disponibles.';}).addTo(map);
 layer=L.layerGroup().addTo(map);draw();
}
function draw(){
 if(!map)return;layer.clearLayers();if(line){map.removeLayer(line);line=null;}
 const dot=(coords,label,color)=>L.circleMarker(coords,{radius:9,color:'#fff',weight:2,fillColor:color,fillOpacity:1}).bindPopup(label).addTo(layer);
 dot(pick,'Recogida de prueba','#316bc3');dot(dest,'Destino de prueba','#934bb8');
 dot(driver,'Unidad MT-01 · GPS SIMULADO',state==='accepted'||state==='inprogress'?'#eca923':'#159f71');
 if(role==='central'){dot([9.099,-79.363],'MT-02 · Disponible (simulado)','#159f71');dot([9.07,-79.34],'MT-03 · Desconectado (simulado)','#89939c');}
 if(['accepted','inprogress'].includes(state)){
  const goal=state==='accepted'?pick:dest;
  line=L.polyline([driver,goal],{color:'#1d70b5',dashArray:'8 8',weight:4}).addTo(map);
 }
}
function render(){
 const title={cliente:'Solicitud del pasajero',central:'Central de despacho',conductor:'Aplicación del conductor'};
 const info={cliente:'La central recibe y administra tu solicitud; verás únicamente al taxi confirmado.',
 central:'Asigna carreras a unidades afiliadas, registra los estados y supervisa sus servicios.',
 conductor:'Solo puedes aceptar carreras que Metro Taxi te ofrezca. La navegación abre Waze externamente.'};
 $$('role-title').textContent=title[role];$$('role-info').textContent=info[role];
 document.querySelectorAll('[data-role]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.role===role)));
 $$('trip-status').textContent=texts[state]||texts.idle;
 $$('requests').textContent=state==='idle'?0:1;$$('available').textContent=['offered','accepted','inprogress'].includes(state)?1:2;
 $$('active').textContent=['accepted','inprogress'].includes(state)?1:0;
 $$('driver-card').hidden=role!=='cliente'||!['accepted','inprogress','complete'].includes(state);
 const defs=(buttons[state]||{})[role]||[];
 $$('actions').innerHTML='';
 defs.forEach(([name,label])=>{
  const b=document.createElement('button');b.className='action'+(name==='move'?' secondary':'');b.textContent=label;b.type='button';
  b.addEventListener('click',()=>act(name));$$('actions').appendChild(b);
 });
 if(!defs.length){const p=document.createElement('p');p.className='muted';p.textContent=state==='rejected'?'Reinicia desde el pasajero para solicitar otra carrera.':'Cambia de rol para continuar el flujo.';$$('actions').appendChild(p);}
 const ol=$$('timeline');ol.innerHTML='';
 (operations.length?operations:['Selecciona «Solicitar taxi» para comenzar.']).forEach(t=>{const li=document.createElement('li');li.textContent=t;ol.appendChild(li);});
 $$('map-note').textContent=(role==='cliente'?'El pasajero no consulta la flota completa. ':'GPS y taxis SIMULADOS. ')+(state==='accepted'?'Se marca la recogida. ':state==='inprogress'?'Se marca el destino. ':'')+'La línea punteada es directa; no es una ruta vial.';
 draw();
}
function act(a){
 if(a==='request'){state='pending';driver=driverInitial.slice();step=0;operations.length=0;log('Pasajero solicitó una carrera ficticia en Pacora.');}
 else if(a==='offer'){state='offered';log('Central ofreció MT-DEMO a la unidad MT-01.');}
 else if(a==='accept'){state='accepted';step=0;log('Conductor MT-01 aceptó. El pasajero ve su ficha.');}
 else if(a==='reject'){state='rejected';log('Conductor rechazó. Se requiere reasignación por la central.');}
 else if(a==='move'){const target=state==='accepted'?pick:dest;step=Math.min(step+1,5);driver=distance(driver,target,Math.min(.45,.14*step));log('El taxi SIMULADO avanzó; el mapa actualiza su marcador y recorrido.');}
 else if(a==='start'){state='inprogress';step=0;driver=pick.slice();log('Conductor recogió al pasajero e inició la carrera.');}
 else if(a==='complete'){state='complete';driver=dest.slice();log('Carrera finalizada. La central conserva su registro.');}
 else if(a==='restart'){state='idle';driver=driverInitial.slice();step=0;operations.length=0;}
 render();
}
document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',()=>{role=b.dataset.role;render();}));
initMap();render();
})();
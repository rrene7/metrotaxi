/* MAP-104: GPS refresh must not erase the visible route. Node VM: no network needed. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../web-staging/js/mapa.js'),'utf8');
let removed=0, drawn=0;
const map={setView(){return this},on(){return this},invalidateSize(){},fitBounds(){},removeLayer(){removed++}};
const bounds={pad(){return this}};
const L={
  map(){return map},tileLayer(){return {on(){return this},addTo(){return this}}},
  layerGroup(){return {addTo(){return this},clearLayers(){}}},
  circleMarker(){return {bindPopup(){return this},addTo(){return this}}},
  marker(){return {bindPopup(){return this},addTo(){return this}}},
  divIcon(){return {}},
  polyline(){drawn++;return {addTo(){return this},getBounds(){return bounds}}},
  latLngBounds(){return bounds}
};
const root={style:{},innerHTML:''},status={textContent:'',classList:{toggle(){}}};
const sandbox={window:{L},document:{getElementById:id=>id==='map-test'?root:status},
  MTCloud:{esc:x=>String(x)},location:{hostname:'localhost'},setTimeout:()=>0};
vm.runInNewContext(code,sandbox,{filename:'mapa.js'});
(async()=>{
 const m=sandbox.window.MetroMap.make({id:'map-test',station:'Pacora'});
 assert.equal(await m.ready,true);
 m.update([{lat:9.1,lng:-79.3,kind:'pickup'}]);
 await m.route({lat:9.1,lng:-79.3},{lat:9.2,lng:-79.4});
 assert.equal(drawn,1);
 const before=removed;
 m.update([{lat:9.12,lng:-79.31,kind:'driver'}]);
 assert.equal(removed,before,'Refreshing GPS markers must not erase the active route');
 m.clearRoute();
 assert.equal(removed,before+1,'Changing trips must clear the old route');
 await m.route({lat:9.1,lng:-79.3},{lat:9.3,lng:-79.5});
 assert.equal(drawn,2,'A new trip can draw its route');
 console.log('OK: active route survives GPS refresh; changing trips clears the old route');
})().catch(e=>{console.error(e);process.exitCode=1});

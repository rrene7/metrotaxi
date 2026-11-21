/* GPS-115: outstanding upload must settle before remote stop. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../web-staging/js/conductor.js'),'utf8');
const begin=src.indexOf(' async function stopGPS(){');
const end=src.indexOf(" el('gps-start').addEventListener",begin);
assert(begin>=0&&end>begin,'GPS stop must remain independently testable');
const fn=src.slice(begin,end);
async function scenario(rejectStop=false){
 let releaseUpload,stopCalls=0,cleared=[],mapUpdates=0,notice='';
 const pending=new Promise(resolve=>{releaseUpload=resolve;});
 const status={textContent:''};
 const ctx={
  gpsGeneration:3,gpsWatch:21,gpsInFlight:pending,gpsStopping:null,
  currentDriver:{location:{lat:9,lng:-79}},navigator:{geolocation:{clearWatch:n=>cleared.push(n)}},
  mapCurrent(){mapUpdates++},
  el:id=>{assert.equal(id,'gps-status');return status},
  M:{
   api:async(path,method)=>{assert.equal(path,'/api/driver/location/stop');assert.equal(method,'POST');stopCalls++;if(rejectStop)throw Error('Sin conexión');return {};},
   notice:text=>{notice=text}
  }
 };
 vm.runInNewContext(fn,ctx,{timeout:1000});
 const p1=ctx.stopGPS(),p2=ctx.stopGPS();
 assert.equal(ctx.gpsGeneration,4,'Old callbacks invalidated synchronously');
 assert.equal(ctx.gpsWatch,null);
 assert.deepEqual(cleared,[21],'Stop watch only once');
 assert.equal(ctx.currentDriver.location,undefined,'Remove stale map location immediately');
 assert.equal(mapUpdates,1,'Map must be refreshed without the old GPS');
 assert.equal(stopCalls,0,'Remote stop cannot overtake the pending location upload');
 releaseUpload();
 await Promise.all([p1,p2]);
 assert.equal(stopCalls,1,'Stop sent exactly once for concurrent taps');
 if(rejectStop){
  assert.match(status.textContent,/no se confirm[oó]/i,'Never claim server stop succeeded after network error');
  assert.match(notice,/No se pudo confirmar/i,'Expose network error to driver');
 }else{
  assert.match(status.textContent,/detenido y confirmado/i);
 }
 assert.equal(ctx.gpsStopping,null,'Allow future retry or start');
}
(async()=>{
 await scenario(false);
 await scenario(true);
 assert.match(src,/generation!==gpsGeneration\|\|gpsStopping\|\|gpsSending/,'Old GPS callbacks must not start new uploads');
 assert.match(src,/if\(generation!==gpsGeneration\)return; \/\/ A stopped watch/,'Old upload responses must not restore markers');
 assert.match(src,/if\(generation!==gpsGeneration\)return;\s*el\('gps-status'\)\.textContent='GPS no disponible/,'Late geolocation errors must not stop a new watch');
 console.log('OK GPS-115: stop waits for upload, invalidates old watch and reports remote failure');
})().catch(e=>{console.error(e);process.exitCode=1});

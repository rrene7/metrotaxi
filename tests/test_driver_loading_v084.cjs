/* Regression: driver dispatch list must render independently of navigation.js.
   No browser or network needed; execute in isolated Node vm with simulated DOM. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const driverJs=fs.readFileSync(path.join(__dirname,'..','static','driver.js'),'utf8');

async function run(trips, shouldFail=false){
 const elements=new Map();
 const element=id=>{
  if(!elements.has(id))elements.set(id,{
   textContent:'',innerHTML:id==='drivertrips'?'Cargando...':'',disabled:false,value:'',style:{},
   addEventListener(){},classList:{add(){},remove(){}},select(){},appendChild(){}
  });
  return elements.get(id);
 };
 const win={addEventListener(){},print(){},MT:{
  $:element,who:async()=>({authenticated:true,user:{role:'driver',username:'conductor1'}}),
  api:async p=>{assert.equal(p,'/api/mine');if(shouldFail)throw Error('Servidor sin respuesta');return {
   driver:{id:1,unit:'MT-01',name:'Conductor DEMO 01',station:'24 de Diciembre',status:'busy',updated_at:'ahora'},
   trips,referral_url:null,referral_count:0,qr_ready:false,public_link_configured:false
  }},
  esc:v=>String(v??'').replace(/[&<>"]/g,'_'),
  badge:s=>`<span>${s}</span>`,show(){}
 }};
 const ctx={window:win,document:{getElementById:element,body:{classList:{add(){},remove(){}}},createElement:()=>({addEventListener(){}})},navigator:{},location:{replace(){},href:''},setInterval(){},setTimeout(){},clearTimeout(){},console,Date,Set,Math};
 vm.runInNewContext(driverJs,ctx,{filename:'driver.js'});
 await new Promise(setImmediate);
 await new Promise(setImmediate);
 return elements;
}
(async()=>{
 const sample={id:3,status:'accepted',name:'Cliente DEMO',pickup:'Ubicación actual GPS',destination:'Por confirmar',pickup_lat:9.01234,pickup_lng:-79.56789,pickup_accuracy_m:20};
 const dom=await run([sample]);
 const rendered=dom.get('drivertrips').innerHTML;
 assert.match(rendered,/#MT-3/);
 assert.match(rendered,/Navegar a recogida con Waze/);
 assert.match(rendered,/waze\.com\/ul/);
 assert.match(rendered,/google\.com\/maps\/dir/);
 assert.match(rendered,/Iniciar carrera/);
 assert.doesNotMatch(rendered,/Cargando/);
 const missingCoords=await run([{...sample,pickup_lat:null,pickup_lng:null}]);
 assert.match(missingCoords.get('drivertrips').innerHTML,/no contiene coordenadas de recogida/);
 assert.doesNotMatch(missingCoords.get('drivertrips').innerHTML,/waze\.com\/ul/);
 const failed=await run([],true);
 assert.match(failed.get('drivertrips').innerHTML,/No se pudieron mostrar tus carreras/);
 assert.match(failed.get('drivertrips').innerHTML,/Reintentar/);
 assert.doesNotMatch(failed.get('drivertrips').innerHTML,/Cargando/);
 console.log('3 pruebas v0.8.4 OK: sin navigation.js, sin coordenadas, error visible');
})().catch(e=>{console.error(e);process.exitCode=1});

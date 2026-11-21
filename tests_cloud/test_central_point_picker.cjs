/* POINT-108: execute the central screen's real click/confirm handlers with a fake API.
 * Detects JS runtime errors that syntax/static tests cannot see.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../web-staging/js/central.js'),'utf8');
const handlers=new Map(),nodes=new Map(),calls=[],messages=[];
const ride={id:42,station:'Pacora',status:'pending',name:'Pasajero simulado',phone:'50760009999',
  pickup:'Punto acordado por teléfono',destination:'Destino sin mapa',reference:'Portón azul',
  pickup_lat:null,pickup_lng:null,dest_lat:null,dest_lng:null,price:null};
function node(id){
 if(!nodes.has(id)){
  const classes=new Set(['hidden']);
  nodes.set(id,{id,innerHTML:'',textContent:'',value:'',checked:false,
    classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),
      contains:x=>classes.has(x),toggle:(x,y)=>y?classes.add(x):classes.delete(x)},
    addEventListener:(event,cb)=>handlers.set(id+':'+event,cb),
    scrollIntoView(){},
    querySelector:()=>({value:'1'})});
 }
 return nodes.get(id);
}
const pointOptions={};
let picked=null,cancelled=0;
const map={
 pick(point){picked=point},
 cancelPick(){picked=null;cancelled++},
 update(){},setView(){},refresh(){}
};
const M={
 async me(){return {authenticated:true,user:{role:'admin'}}},
 async api(url,method='GET',data){
  calls.push({url,method,data});
  if(url==='/api/trips')return {trips:[ride]};
  if(url==='/api/fleet')return {drivers:[]};
  if(url==='/api/stats')return {total:1,by_status:{done:0,cancelled:0},by_unit:[],note:'Solo pruebas'};
  if(url==='/api/messages')return {messages:[]};
  if(url==='/api/trips/point'){
    assert.equal(method,'POST');
    if(data.point==='pickup'){ride.pickup_lat=data.lat;ride.pickup_lng=data.lng;}
    else{ride.dest_lat=data.lat;ride.dest_lng=data.lng;}
    return {ok:true};
  }
  throw new Error('Unexpected endpoint '+url);
 },
 esc:value=>String(value??''),status:x=>x,text:(id,x)=>{node(id).textContent=x},notice:x=>messages.push(x)
};
const doc={getElementById:node};
const sandbox={
 document:doc,location:{replace:()=>{throw Error('Unexpected redirect')}},
 MetroMap:{good:(a,b)=>typeof a==='number'&&typeof b==='number'&&isFinite(a)&&isFinite(b),make:options=>{
    Object.assign(pointOptions,options);return map;
 }},
 MTAlerts:{make:()=>({observe(){},isEnabled:()=>false})},
 MTCloud:M,setInterval:()=>0,confirm:()=>true,console
};
vm.runInNewContext(src,sandbox,{filename:'central.js',timeout:4000});
async function flush(){for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));}
function clickPoint(point){
 const handler=handlers.get('trips:click');assert.equal(typeof handler,'function');
 handler({target:{closest:selector=>selector==='[data-edit-point]'?{dataset:{editPoint:point,geoTrip:'42'}}:null}});
}
async function submit(){
 const handler=handlers.get('point-form:submit');assert.equal(typeof handler,'function');
 await handler({preventDefault(){}});
}
(async()=>{
 await flush();
 clickPoint('pickup');
 assert.equal(picked,'pickup');
 assert.equal(node('point-editor').classList.contains('hidden'),false);
 pointOptions.onChoose('pickup',9.08,-79.28);
 assert.equal(node('point-lat').value,'9.080000');
 assert.equal(node('point-lng').value,'-79.280000');
 node('point-confirm').checked=true;
 await submit();
 const first=calls.filter(x=>x.url==='/api/trips/point')[0];
 assert(first,'Must submit confirmed pickup through the API');
 assert.equal(first.data.trip_id,42);
 assert.equal(first.data.point,'pickup');
 assert.equal(first.data.lat,9.08);
 assert.equal(first.data.lng,-79.28);
 assert.equal(first.data.method,'map_click');
 assert.equal(first.data.expected_lat,null);
 assert.equal(first.data.confirmed_with_passenger,true);
 assert.equal(node('point-editor').classList.contains('hidden'),true);
 assert(cancelled>0,'Picker must be cancelled on submit');
 clickPoint('destination');
 node('point-lat').value='9.09';
 node('point-lng').value='-79.29';
 handlers.get('point-lat:input')();
 node('point-confirm').checked=true;
 await submit();
 const second=calls.filter(x=>x.url==='/api/trips/point')[1];
 assert(second,'Must accept explicitly provided coordinates without external map');
 assert.equal(second.data.point,'destination');
 assert.equal(second.data.method,'provided_coordinates');
 assert.equal(second.data.lat,9.09);
 assert.equal(second.data.lng,-79.29);
 assert.equal(ride.dest_lat,9.09);
 console.log('OK: central popup, map click, manual coordinates, verification, API and cancellation.');
})().catch(err=>{console.error(err);process.exitCode=1});

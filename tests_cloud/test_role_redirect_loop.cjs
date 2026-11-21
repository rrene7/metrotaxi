'use strict';
// SESSION-124: existing customer cookie must not bounce login <> central.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const login=fs.readFileSync('web-staging/js/login.js','utf8');
const central=fs.readFileSync('web-staging/js/central.js','utf8');
const driver=fs.readFileSync('web-staging/js/conductor.js','utf8');

async function checkLogin(role,expected){
 const handlers={},replacements=[],notes=[];
 const submit={disabled:false};
 const nodes={
  login:{querySelector:()=>submit,addEventListener:(event,fn)=>{handlers[event]=fn}},
  clave:{value:'Clave123!',focus(){},select(){}},
  usuario:{value:'adminmetro'},
  'ver-clave':{addEventListener(){}}
 };
 const sandbox={document:{getElementById:id=>nodes[id]},
  MTCloud:{me:async()=>({authenticated:true,user:{role}}),notice:t=>notes.push(t),
   api:async()=>({role:'admin'})},
  location:{replace:url=>replacements.push(url)},console};
 vm.runInNewContext(login,sandbox,{timeout:1000});
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(replacements,expected?[expected]:[],'Unexpected automatic login redirect for '+role);
 if(role==='customer'){
  assert.match(notes.join(' '),/sesión de pasajero activa/);
  assert.equal(typeof handlers.submit,'function','Customer cookie must not disable explicit staff login');
  await handlers.submit({preventDefault(){}});
  assert.deepEqual(replacements,['/central.html']);
 }
}
function verifyGuards(){
 assert.match(central,/if\(!s\.authenticated\)\{location\.replace\('\/ingresar\.html'\)/);
 assert.match(central,/s\.user\.role==='driver'\?'\/conductor\.html':'\/cliente\.html'/);
 assert.match(driver,/s\.user\.role==='customer'\?'\/cliente\.html':'\/central\.html'/);
 assert.doesNotMatch(central,/!s\.authenticated\|\|!\['admin','operator'\]/);
 assert.doesNotMatch(driver,/!s\.authenticated\|\|s\.user\.role!=='driver'/);
}
(async()=>{
 await checkLogin('customer',null);
 await checkLogin('admin','/central.html');
 await checkLogin('operator','/central.html');
 await checkLogin('driver','/conductor.html');
 verifyGuards();
 console.log('SESSION-124 OK: customer cookie does not bounce; staff redirects and explicit role switching remain');
})().catch(e=>{console.error(e);process.exitCode=1});

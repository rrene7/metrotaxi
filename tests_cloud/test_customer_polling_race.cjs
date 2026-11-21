/* CUSTOMER-114: stale asynchronous passenger responses must never repaint newer state. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web-staging/js/cliente.js'),'utf8');
const match=source.match(/function isCurrentCustomerResponse\(generation\)\{[^}]+\}/);
assert(match,'Passenger response guard must be explicit and testable');
const context={requestGeneration:4};
vm.runInNewContext(match[0]+';globalResult=[isCurrentCustomerResponse(3),isCurrentCustomerResponse(4),isCurrentCustomerResponse(5)];',context,{timeout:1000});
assert.deepEqual(Array.from(context.globalResult),[false,true,false],'Only the latest started query may update UI');
assert.match(source,/const generation=\+\+requestGeneration;try\{const \[data,ms\]/,'Every load needs a new generation');
assert.match(source,/if\(!isCurrentCustomerResponse\(generation\)\)return;\s*lastTrips=data\.trips/,'Ignore late success before changing passenger state');
assert.match(source,/catch\(e\)\{if\(isCurrentCustomerResponse\(generation\)\)el\('trips'\)/,'Ignore late errors as well');
for(const snippet of ["++requestGeneration;const r=await M.api('/api/requests'","++requestGeneration;await M.api('/api/trips/cancel'","++requestGeneration;try{await M.logout()"]){
 assert(source.includes(snippet),'Trip mutations/logout must invalidate older reads: '+snippet);
}
console.log('OK: passenger reads ordered; stale successes/errors ignored after later load or mutation');

'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const src=fs.readFileSync(require('node:path').join(__dirname,'../web-staging/js/seguimiento.js'),'utf8');
const c={window:{}};vm.runInNewContext(src,c);
const segment=c.window.MetroTracking.segment;
const good=(a,b)=>typeof a==='number'&&typeof b==='number'&&Math.abs(a)<=90&&Math.abs(b)<=180;
const t={status:'accepted',pickup_lat:9.08,pickup_lng:-79.29,dest_lat:9.14,dest_lng:-79.31,
 driver:{confirmed:true,location:{lat:9.05,lng:-79.27,updated_at:'test-only'}}};
assert.deepEqual(JSON.parse(JSON.stringify(segment(t,good))),{start:{lat:9.05,lng:-79.27},end:{lat:9.08,lng:-79.29},live:true});
t.status='inprogress';
assert.deepEqual(JSON.parse(JSON.stringify(segment(t,good))),{start:{lat:9.05,lng:-79.27},end:{lat:9.14,lng:-79.31},live:true});
delete t.driver.location;
assert.equal(segment(t,good).live,false,'Without real GPS, only a planned pickup-to-destination line is allowed');
t.status='completed';
assert.equal(segment(t,good),null);
t.status='accepted';t.dest_lat=null;t.dest_lng=null;
assert.equal(segment(t,good),null,'Do not invent destination or missing GPS');
console.log('OK seguimiento: recogida, destino, GPS ausente y carrera terminada');

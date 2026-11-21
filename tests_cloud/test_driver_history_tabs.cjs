/* DRIVER-116: previous trips belong to a separate, non-actionable history view. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../web-staging/conductor.html'),'utf8');
const code=fs.readFileSync(path.join(__dirname,'../web-staging/js/conductor.js'),'utf8');
for(const id of ['trips','driver-trip-history','driver-active-pane','driver-history-pane']){
 assert(html.includes('id="'+id+'"'),'Missing driver section '+id);
}
assert.match(html,/id="driver-history-pane" hidden/,'History must be hidden by default');
assert.match(html,/data-driver-tab="active"/);
assert.match(html,/data-driver-tab="history"/);
assert.match(code,/function selectDriverTab\(tab\)/,'Switch tabs without rebuilding the whole screen');
const start=code.indexOf(' function partitionDriverTrips(trips){');
const end=code.indexOf(' function selectDriverTab',start);
assert(start>=0&&end>start,'Define a dedicated ride-partition function');
const sandbox={};
vm.runInNewContext(code.slice(start,end),sandbox,{timeout:1000});
const sample=[{id:1,status:'offered'},{id:2,status:'accepted'},{id:3,status:'inprogress'},{id:4,status:'done'},{id:5,status:'cancelled'}];
const result=sandbox.partitionDriverTrips(sample);
assert.deepEqual(Array.from(result.active,x=>x.id),[1,2,3],'Only active trips can offer actions');
assert.deepEqual(Array.from(result.history,x=>x.id),[4,5],'Finished and cancelled trips go to history');
const active=code.slice(code.indexOf("el('trips').innerHTML=grouped.active.length"),code.indexOf("el('driver-trip-history').innerHTML="));
const history=code.slice(code.indexOf("el('driver-trip-history').innerHTML="),code.indexOf("if(selected&&!grouped.active"));
assert.match(active,/data-action=/,'Active pane retains trip actions');
assert.doesNotMatch(history,/data-action=|data-view=/,'History may not expose trip actions or map-selection controls');
assert.match(code,/if\(selected&&!grouped.active.some/,'Do not continue tracking a closed trip');
assert.match(code,/el\('driver-active-pane'\)\.hidden=isHistory/);
assert.match(code,/el\('driver-history-pane'\)\.hidden=!isHistory/);
console.log('OK DRIVER-116: separate active/history, no historical actions, closed tracking cleared');

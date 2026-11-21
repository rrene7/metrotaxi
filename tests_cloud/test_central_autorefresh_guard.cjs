/* CENTRAL-113: timed polling must not erase edits in progress. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../web-staging/js/central.js'),'utf8');
assert.match(code,/function hasPendingCentralEdits\(\)/,'Central must expose a guard for unsaved edits');
assert.match(code,/load\(\{automatic:true\}\)/,'Polling must be explicitly marked automatic');
assert.match(code,/automatic\s*&&\s*hasPendingCentralEdits\(\)/,'Automatic updates must honor active edits');
const match=code.match(/function hasPendingCentralEdits\(\)\{[\s\S]*?\n \}/);
assert(match,'Guard must be a standalone function for regression testing');
function evaluate({pointEdit=null,focused=null,tripFields=[],driverFields=[]}={}){
 const nodes={
  trips:{contains:e=>e!=null&&e.area==='trips',querySelectorAll:()=>tripFields},
  drivers:{contains:e=>e!=null&&e.area==='drivers',querySelectorAll:()=>driverFields}
 };
 const sandbox={pointEdit,el:id=>nodes[id],document:{activeElement:focused,getElementById:id=>nodes[id]}};
 return vm.runInNewContext(match[0]+'\nhasPendingCentralEdits()',sandbox,{timeout:1000});
}
assert.equal(evaluate(),false,'Idle central must continue receiving automatic updates');
assert.equal(evaluate({pointEdit:{tripId:1}}),true,'Map-point editor must survive polling');
assert.equal(evaluate({focused:{area:'trips'}}),true,'Focused assignment must survive polling');
assert.equal(evaluate({focused:{area:'drivers'}}),true,'Focused vehicle form must survive polling');
assert.equal(evaluate({tripFields:[{tagName:'INPUT',type:'number',value:'12.00',defaultValue:'10.00'}]}),true,'Changed price must survive even after focus is lost');
assert.equal(evaluate({driverFields:[{tagName:'INPUT',type:'text',value:'ABC123',defaultValue:'ABC111'}]}),true,'Changed vehicle details must survive');
assert.equal(evaluate({tripFields:[{tagName:'SELECT',selectedIndex:1}]}),true,'Selected driver must survive');
assert.equal(evaluate({driverFields:[{tagName:'INPUT',type:'file',files:[{}]}]}),true,'Selected photo must survive');
assert.equal(evaluate({tripFields:[{tagName:'INPUT',type:'number',value:'10.00',defaultValue:'10.00'}]}),false,'Unmodified fields should not pause refresh');
console.log('OK: auto-refresh preserves unsaved central edits; idle refresh stays enabled');

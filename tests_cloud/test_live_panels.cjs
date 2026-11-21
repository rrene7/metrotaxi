'use strict';
// LIVE-122: polling must not destroy an unchanged panel's interactive DOM.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let renders=0;
const panel={
  firstChild:null,
  childNodes:[],
  get innerHTML(){return this.html||'';},
  set innerHTML(value){this.html=value;renders++;this.firstChild={value};this.childNodes=[this.firstChild];}
};
const context={window:{},document:{getElementById:id=>id==='panel'?panel:null}};
vm.runInNewContext(fs.readFileSync('web-staging/js/api.js','utf8'),context);
const M=context.window.MTCloud;
M.setHtml('panel','<button>Seleccionar</button>');
const selected=panel.firstChild;
assert.equal(renders,1);
M.setHtml('panel','<button>Seleccionar</button>');
assert.equal(renders,1,'Unchanged polling response must keep button nodes and focus');
assert.equal(panel.firstChild,selected);
M.setHtml('panel','<button>Asignada</button>');
assert.equal(renders,2,'Changed status must update panel');
panel.innerHTML='<p class="error">Error temporal</p>';
M.setHtml('panel','<button>Asignada</button>');
assert.equal(renders,4,'Recovery must replace error panel even with cached state');
M.setHtml('missing','<p>ignored</p>');
console.log('LIVE-122 OK: panels are stable on unchanged polls, refresh on changes and recover from errors');

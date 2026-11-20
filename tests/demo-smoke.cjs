'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const crypto=require('node:crypto');
const root=path.join(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const code=fs.readFileSync(path.join(root,'demo.js'),'utf8');
const gitBlob=crypto.createHash('sha1').update('blob '+Buffer.byteLength(code)+'\0').update(code).digest('hex').slice(0,12);
assert.ok(html.includes('./demo.js?v='+gitBlob),'HTML must refer to exact JS blob revision to prevent browser cache regressions');
assert.match(html,/id="passenger-nav"/,'Passenger tabs should exist by default');
assert.doesNotMatch(html,/id="passenger-nav" hidden/,'Passenger navigation must not be hidden when JS fails');
assert.match(html,/id="demo-init-error" hidden/,'Provide a fallback when the demo script fails');
for(const id of ['passenger-nav','passenger-body','passenger-history','operations-panel','demo-stats','actions','history-list']){
 assert.match(html,new RegExp('id="'+id+'"'),'Page must provide '+id);
}
assert.match(html,/id="operations-panel" hidden/,'Operational history hidden by default even if JS crashes');
assert.match(html,/id="demo-stats" hidden/,'Dispatch statistics hidden by default');
class Element {
 constructor(id){this.id=id;this.hidden=false;this.textContent='';this._innerHTML='';this.children=[];this.dataset={};this.handlers={};this.disabled=false;this.attrs={};}
 get innerHTML(){return this._innerHTML}
 set innerHTML(value){this._innerHTML=value;this.children=[]}
 setAttribute(name,value){this.attrs[name]=value}
 appendChild(child){this.children.push(child);return child}
 addEventListener(name,fn){this.handlers[name]=fn}
 click(){assert.equal(typeof this.handlers.click,'function','Action must be interactive');this.handlers.click()}
}
const nodes=new Map(), get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id)};
const roles=['cliente','central','conductor'].map(role=>{const el=new Element(role);el.dataset.role=role;return el});
const tabs=['active','history'].map(tab=>{const el=new Element(tab);el.dataset.passTab=tab;return el});
const document={
 getElementById:get,
 querySelectorAll:selector=>selector==='[data-role]'?roles:selector==='[data-pass-tab]'?tabs:[],
 createElement:tag=>new Element(tag)
};
const window={};const context={document,window,console};
vm.runInNewContext(code,context,{filename:'demo.js',timeout:3000});
function action(name){const btn=get('actions').children.find(x=>x.textContent===name);assert(btn,'Missing action: '+name);return btn}
assert.equal(get('operations-panel').hidden,true,'Passenger cannot see central operations');
assert.equal(get('demo-stats').hidden,true,'Passenger cannot see fleet KPIs');
assert.equal(get('passenger-nav').hidden,false,'Passenger tabs must be visible');
assert.equal(action('Solicitar taxi').disabled,false);
action('Solicitar taxi').click();
roles[1].click();
assert.equal(get('operations-panel').hidden,false,'Central can review its own operations');
action('Asignar MT-01').click();
roles[0].click();
assert.equal(get('operations-panel').hidden,true,'Passenger cannot see unit offers');
assert.match(get('trip-status').textContent,/buscando un taxi/i,'Public state must not reveal offered unit');
assert.equal(get('driver-card').hidden,true,'Driver card remains private until acceptance');
roles[2].click();
action('Aceptar carrera').click();
assert.equal(action('Recoger e iniciar').disabled,true,'Boarding prohibited from far away');
for(let i=0;i<4;i++)action('Simular avance del taxi').click();
assert.equal(action('Recoger e iniciar').disabled,false,'Boarding allowed at pickup');
action('Recoger e iniciar').click();
assert.equal(action('Finalizar carrera').disabled,true,'Finishing prohibited from far away');
for(let i=0;i<4;i++)action('Simular avance del taxi').click();
assert.equal(action('Finalizar carrera').disabled,false,'Finishing allowed at destination');
action('Finalizar carrera').click();
roles[0].click();
assert.equal(get('operations-panel').hidden,true);
assert.equal(get('driver-card').hidden,false,'Confirmed driver remains visible to its passenger after the trip');
tabs[1].click();
assert.equal(get('passenger-body').hidden,true);
assert.equal(get('passenger-history').hidden,false);
assert.match(get('history-list').children[0].textContent,/Finalizada/);
console.log('OK: passenger UI renders, internal data stays private, history works and arrival gates restrict actions.');

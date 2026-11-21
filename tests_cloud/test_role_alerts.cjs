'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('web-staging/js/avisos.js','utf8');
function test(kind,expected){
 const events={};let permissionCalls=0,beeps=0;
 const element={hidden:true,textContent:'',addEventListener:(name,fn)=>events['el-'+name]=fn};
 const button={textContent:'',setAttribute:()=>{},addEventListener:(name,fn)=>events['btn-'+name]=fn};
 class Audio{
  constructor(){this.currentTime=0;this.destination={};}
  resume(){return Promise.resolve()}
  suspend(){return Promise.resolve()}
  createOscillator(){return {frequency:{value:0},connect:()=>{},start:()=>{beeps++},stop:()=>{}}}
  createGain(){return {gain:{value:0},connect:()=>{}}}
 }
 const ctx={window:{AudioContext:Audio},document:{hidden:false},Notification:{permission:'default',requestPermission:()=>{permissionCalls++;return Promise.resolve('denied')}},Set,Number};
 vm.runInNewContext(src,ctx);
 const alert=ctx.window.MTAlerts.make({kind,element,button,selector:t=>t.status===expected});
 alert.observe([{id:1,status:expected}]);
 assert.equal(element.hidden,true,'First sync must not alert old offers');
 alert.observe([{id:1,status:expected}]);
 assert.equal(element.hidden,true,'Same offer cannot alert repeatedly');
 alert.observe([{id:1,status:expected},{id:2,status:expected},{id:5,status:'done'}]);
 assert.equal(element.hidden,false,'New matching trip must alert');
 assert.match(element.textContent,/MT-2/);
 assert.equal(beeps,0,'Audio requires user opt-in');
 events['el-click']();
 assert.equal(element.hidden,true,'User can dismiss banner');
 assert.equal(permissionCalls,0,'Permission never requested without button click');
 return Promise.resolve(events['btn-click']()).then(()=>{
  assert.equal(permissionCalls,1,'Permission requested on user action only');
  alert.observe([{id:1,status:expected},{id:2,status:expected},{id:3,status:expected}]);
  assert.equal(beeps,1,'Opt-in receives sound only for new trip');
  alert.observe([{id:1,status:expected},{id:2,status:expected},{id:3,status:expected}]);
  assert.equal(beeps,1,'No duplicate beeps');
 });
}
(async()=>{await test('driver','offered');await test('central','pending');console.log('ALERTS-123 OK: baseline, dedupe, correct roles, opt-in audio and dismiss')})().catch(e=>{console.error(e);process.exitCode=1});

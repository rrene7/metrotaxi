const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname+'/../static/app.js','utf8');
function createHarness(handler) {
  const calls = [];
  const context = { window: {}, navigator: {}, document: { getElementById: ()=>null },
    setTimeout(){}, clearTimeout(){},
    fetch: async(path, opts={}) => {
      const result = await handler(path, opts, calls);
      calls.push({path, opts, status: result.status});
      return {status:result.status, ok:result.status>=200&&result.status<300,
        json:async()=>result.body};
    }
  };
  vm.runInNewContext(source,context);
  return {MT:context.window.MT,calls};
}
async function main(){
  {
    const h=createHarness((path,opts)=>{
      if(path==='/api/me') return {status:200,body:{authenticated:true,csrf:'current'}};
      assert.equal(opts.headers['X-CSRF-Token'],'current');
      return {status:200,body:{ok:true}};
    });
    await h.MT.api('/api/dispatch/settings','POST',{mode:'manual'});
    assert.equal(h.calls.length,2);
    assert.equal(h.calls[0].path,'/api/me');
    console.log('PASS missing token fetches current session before mutation');
  }
  {
    let attempts=0;
    const h=createHarness((path,opts)=>{
      if(path==='/api/me')return {status:200,body:{authenticated:true,csrf:'renewed'}};
      attempts++;
      if(attempts===1){assert.equal(opts.headers['X-CSRF-Token'],'stale');return {status:403,body:{code:'CSRF_INVALID',error:'invalid'}}}
      assert.equal(opts.headers['X-CSRF-Token'],'renewed');
      return {status:200,body:{ok:true}};
    });
    h.MT.csrf='stale';
    const result=await h.MT.api('/api/dispatch/settings','POST',{mode:'manual'});
    assert.equal(result.ok,true);assert.equal(attempts,2);assert.equal(h.calls.length,3);
    console.log('PASS stale token refreshes and retries exactly once');
  }
  {
    let attempts=0;
    const h=createHarness((path,opts)=>{
      attempts++;
      return {status:403,body:{error:'Sin autorización'}};
    });
    h.MT.csrf='correct';
    await assert.rejects(()=>h.MT.api('/api/dispatch/settings','POST',{mode:'manual'}),/Sin autorización/);
    assert.equal(attempts,1);
    console.log('PASS non-CSRF 403 never retried');
  }
  {
    const h=createHarness((path,opts)=>{
      if(path==='/api/me')return {status:200,body:{authenticated:false,csrf:null}};
      assert.equal(opts.headers['X-CSRF-Token'],undefined);
      return {status:200,body:{ok:true}};
    });
    await h.MT.api('/api/login','POST',{username:'demo',password:'not-a-real-credential'});
    assert.equal(h.calls.length,2);
    console.log('PASS anonymous login does not need pre-existing CSRF token');
  }
}
main().catch(e=>{console.error(e);process.exit(1)});

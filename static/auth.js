'use strict';
(async()=>{
 const M=window.MT;const $=M.$;
 const s=await M.who().catch(()=>null);
 if(s?.authenticated){location.replace(s.user.role==='driver'?'/conductor':s.user.role==='customer'?'/cliente':'/central');return}
 $('loginform').addEventListener('submit',async e=>{
  e.preventDefault();try{
   let r=await M.api('/api/login','POST',{username:$('username').value,password:$('password').value});
   location.replace(r.role==='driver'?'/conductor':r.role==='customer'?'/cliente':'/central');
  }catch(err){M.show(err.message)}
 });
})();

'use strict';(async()=>{
 const M=MTCloud;
 try{const s=await M.me();if(s.authenticated){location.replace(s.user.role==='driver'?'/conductor.html':'/central.html');return;}}catch(e){M.notice(e.message,true)}
 document.getElementById('login').addEventListener('submit',async e=>{
  e.preventDefault();try{const r=await M.api('/api/login','POST',{username:document.getElementById('usuario').value,password:document.getElementById('clave').value});location.replace(r.role==='driver'?'/conductor.html':'/central.html');}
  catch(err){M.notice(err.message,true)}
 });
})();

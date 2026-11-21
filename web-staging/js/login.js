'use strict';(async()=>{
 const M=MTCloud;
 const form=document.getElementById('login');
 const password=document.getElementById('clave');
 const username=document.getElementById('usuario');
 const reveal=document.getElementById('ver-clave');
 const button=form.querySelector('button[type="submit"]');
 // Never log, store, strip or transform the password. Make accidental
 // browser autocomplete / keyboard differences visible on demand.
 reveal.addEventListener('change',()=>{password.type=reveal.checked?'text':'password';});
 try{const s=await M.me();if(s.authenticated){
  if(s.user.role==='customer')M.notice('Hay una sesión de pasajero activa en este navegador. Para entrar como personal, inicia sesión aquí; para usar ambos roles a la vez, utiliza perfiles de Chrome separados.',true);
  else {location.replace(s.user.role==='driver'?'/conductor.html':'/central.html');return;}
 }}catch(e){M.notice(e.message,true)}
 form.addEventListener('submit',async e=>{
  e.preventDefault();
  if(button.disabled)return;
  const user=username.value.trim();
  const pass=password.value;
  if(!user||!pass){M.notice('Completa usuario y contraseña.',true);return;}
  button.disabled=true;
  M.notice('Comprobando acceso…');
  try{
   const r=await M.api('/api/login','POST',{username:user,password:pass});
   location.replace(r.role==='driver'?'/conductor.html':'/central.html');
  }catch(err){
   M.notice(err.message,true);
   // Keep the typed values so that the user can inspect them with Mostrar.
   password.focus();
   password.select();
  }finally{button.disabled=false;}
 });
})();

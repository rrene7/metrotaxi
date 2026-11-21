'use strict';
// ALERTS-123: same-origin, role-scoped polling alerts. No service worker,
// no background delivery and no private passenger data in notification text.
window.MTAlerts={
 make({kind,element,button,selector}){
  let last=null,enabled=false,audio=null;
  const label=kind==='driver'?'Nueva carrera ofrecida':'Nueva solicitud recibida';
  function observe(trips){
   const rows=trips.filter(selector);
   const current=new Set(rows.map(t=>Number(t.id)));
   if(last!==null){
    const fresh=rows.filter(t=>!last.has(Number(t.id)));
    if(fresh.length){
     element.hidden=false;
     element.textContent=fresh.length===1?label+' · MT-'+fresh[0].id:fresh.length+' '+(kind==='driver'?'nuevas carreras ofrecidas':'nuevas solicitudes recibidas');
     if(enabled){
      try{if(audio){const o=audio.createOscillator(),g=audio.createGain();o.frequency.value=740;g.gain.value=0.06;o.connect(g);g.connect(audio.destination);o.start();o.stop(audio.currentTime+0.15)}}catch(_){}
      if(document.hidden&&typeof Notification!=='undefined'&&Notification.permission==='granted'){
       try{new Notification('Metro Taxi',{body:element.textContent,tag:'metro-'+kind})}catch(_){}
      }
     }
    }
   }
   last=current;
  }
  async function enable(){
   enabled=!enabled;
   button.textContent=enabled?'Desactivar sonido':'Activar avisos sonoros';
   button.setAttribute('aria-pressed',String(enabled));
   if(enabled){
    try{
     const Audio=window.AudioContext||window.webkitAudioContext;
     if(Audio){audio=audio||new Audio();await audio.resume();}
    }catch(_){audio=null;}
    // Permission is requested only from this explicit user gesture.
    if(typeof Notification!=='undefined'&&Notification.permission==='default'){
     try{await Notification.requestPermission()}catch(_){}
    }
   }else if(audio){try{await audio.suspend()}catch(_){}}
  }
  button.addEventListener('click',enable);
  element.addEventListener('click',()=>{element.hidden=true;});
  return {observe};
 }
};

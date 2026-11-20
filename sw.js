/* Metro Taxi PWA: cache static public assets only. NEVER cache sessions, trips, photos or API data. */
const CACHE='metro-taxi-static-v07';
const STATIC=['/static/app.css','/static/app.js','/static/metro-icon.svg','/static/metro-icon-192.png','/static/metro-icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(STATIC)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url);
 if(e.request.method!=='GET'||u.origin!==self.location.origin||!STATIC.includes(u.pathname))return;
 e.respondWith(fetch(e.request).then(resp=>{
   if(resp.ok){const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));}
   return resp;
 }).catch(()=>caches.match(e.request)));
});

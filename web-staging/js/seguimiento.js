/* Only use coordinates disclosed by the trip API. The server filters stale GPS. */
'use strict';
window.MetroTracking = Object.freeze({
 segment(trip,good) {
  if(!trip)return null;
  const pickup=good(trip.pickup_lat,trip.pickup_lng)?{lat:trip.pickup_lat,lng:trip.pickup_lng}:null;
  const dest=good(trip.dest_lat,trip.dest_lng)?{lat:trip.dest_lat,lng:trip.dest_lng}:null;
  const loc=trip.driver?.confirmed?trip.driver.location:null;
  const driver=loc&&good(loc.lat,loc.lng)?{lat:loc.lat,lng:loc.lng}:null;
  const target=trip.status==='accepted'?pickup:trip.status==='inprogress'?dest:null;
  if(driver&&target)return {start:driver,end:target,live:true};
  if(['pending','offered','accepted','inprogress'].includes(trip.status)&&pickup&&dest)return {start:pickup,end:dest,live:false};
  return null;
 }
});

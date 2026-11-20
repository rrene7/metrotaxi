package pa.metrotaxi.conductor;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.IBinder;
import android.os.SystemClock;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Seguimiento con notificación permanente y consentimiento explícito del conductor. */
public class LocationTrackingService extends Service implements LocationListener {
    static final String START="pa.metrotaxi.START_GPS";
    private static final String CHANNEL="metro_gps";
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private final AtomicBoolean sending=new AtomicBoolean(false);
    private LocationManager lm;
    private long lastSend=0;
    @Override public void onCreate(){super.onCreate();
        lm=(LocationManager)getSystemService(LOCATION_SERVICE);
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL,"Metro Taxi · Ubicación activa",NotificationManager.IMPORTANCE_LOW));
    }
    @Override public int onStartCommand(Intent intent,int flags,int id){
        if(intent==null||!START.equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}
        Notification notification=notification();
        if(Build.VERSION.SDK_INT>=29)startForeground(34,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);
        else startForeground(34,notification);
        if(checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED &&
           checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){stopSelf();return START_NOT_STICKY;}
        try {
            if(lm.isProviderEnabled(LocationManager.GPS_PROVIDER))lm.requestLocationUpdates(LocationManager.GPS_PROVIDER,10000,15f,this);
            if(lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER))lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER,15000,30f,this);
        } catch(SecurityException e){stopSelf();}
        return START_NOT_STICKY; // No reiniciar sin intervención del conductor.
    }
    private Notification notification(){
        Intent open=new Intent(this,MainActivity.class);
        PendingIntent p=PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,CHANNEL)
           .setSmallIcon(android.R.drawable.ic_menu_mylocation)
           .setContentTitle("Metro Taxi · compartiendo ubicación")
           .setContentText("Solo mientras el conductor mantiene activado el GPS")
           .setOngoing(true).setContentIntent(p).build();
    }
    @Override public void onLocationChanged(Location loc){
        if(!loc.hasAccuracy()||loc.getAccuracy()>1000||loc.getAccuracy()<0)return;
        if(loc.isFromMockProvider())return;
        if((SystemClock.elapsedRealtimeNanos()-loc.getElapsedRealtimeNanos())>30_000_000_000L)return;
        if(SystemClock.elapsedRealtime()-lastSend<10000 || !sending.compareAndSet(false,true))return;
        lastSend=SystemClock.elapsedRealtime();
        io.execute(()->{
            try {MetroApi.validateReady();MetroApi.postLocation(loc.getLatitude(),loc.getLongitude(),loc.getAccuracy());}
            catch(SecurityException e){stopSelf();}
            catch(Exception e){/* Fallo de red: no inventar ubicación; servidor caduca en 120 s. */}
            finally{sending.set(false);}
        });
    }
    @Override public void onDestroy(){
        if(lm!=null)lm.removeUpdates(this);
        io.execute(()->{try{MetroApi.stopLocation();}catch(Exception ignored){/* expirará en servidor */}});
        io.shutdown();super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent){return null;}
}

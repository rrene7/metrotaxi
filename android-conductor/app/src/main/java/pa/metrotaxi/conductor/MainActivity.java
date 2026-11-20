package pa.metrotaxi.conductor;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Message;
import android.os.Build;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.net.URI;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** No se usa addJavascriptInterface: la web nunca accede a permisos nativos. */
public class MainActivity extends Activity {
    private static final int REQ_LOCATION=31;
    private WebView web;
    private TextView status;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private boolean pendingStart=false;
    private void message(String msg){runOnUiThread(()->{status.setText(msg);Toast.makeText(this,msg,Toast.LENGTH_LONG).show();});}
    @Override public void onCreate(Bundle b){super.onCreate(b);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.rgb(11,29,50));
        status=new TextView(this);status.setTextColor(Color.WHITE);status.setPadding(18,12,18,12);
        status.setText("Metro Taxi · GPS nativo detenido");root.addView(status);
        LinearLayout controls=new LinearLayout(this);
        Button start=new Button(this);start.setText("Iniciar GPS");
        Button stop=new Button(this);stop.setText("Detener GPS");
        controls.addView(start,new LinearLayout.LayoutParams(0,LinearLayout.LayoutParams.WRAP_CONTENT,1));
        controls.addView(stop,new LinearLayout.LayoutParams(0,LinearLayout.LayoutParams.WRAP_CONTENT,1));
        root.addView(controls);
        web=new WebView(this);root.addView(web,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebChromeClient(new WebChromeClient(){
            // Waze/Google Maps usan target=_blank. Interceptar y abrir fuera del WebView.
            @Override public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message msg){
                if(!isUserGesture)return false;
                WebView child=new WebView(MainActivity.this);
                child.setWebViewClient(new WebViewClient(){
                    @Override public boolean shouldOverrideUrlLoading(WebView w, WebResourceRequest r){
                        openOutside(r.getUrl());w.destroy();return true;
                    }
                    @Override public boolean shouldOverrideUrlLoading(WebView w,String url){
                        openOutside(Uri.parse(url));w.destroy();return true;
                    }
                });
                WebView.WebViewTransport transport=(WebView.WebViewTransport) msg.obj;
                transport.setWebView(child);msg.sendToTarget();return true;
            }
        });
        web.getSettings().setSupportMultipleWindows(true);
        web.setWebViewClient(new WebViewClient(){
            private boolean route(Uri uri){
                if("https".equalsIgnoreCase(uri.getScheme()) && BuildConfig.BASE_URL.equals(uri.getScheme()+"://"+uri.getAuthority()))return false;
                // External Waze, Maps, WhatsApp are opened outside trusted WebView.
                openOutside(uri);return true;
            }
            @Override public boolean shouldOverrideUrlLoading(WebView w,WebResourceRequest r){return route(r.getUrl());}
            @Override public boolean shouldOverrideUrlLoading(WebView w,String url){return route(Uri.parse(url));}
            @Override public void onPageFinished(WebView w,String url){
                if(url.startsWith(BuildConfig.BASE_URL+"/conductor")) {
                    // La localización se controla solo desde botones NATIVOS, sin GPS doble.
                    w.evaluateJavascript("(function(){var s=document.getElementById('gps-section');if(s){s.style.display='none';}})()",null);
                }
            }
        });
        if(BuildConfig.BASE_URL.endsWith(".invalid")){
            status.setText("Configura primero el dominio HTTPS en Android Studio. No uses 127.0.0.1.");
        } else { web.loadUrl(BuildConfig.BASE_URL+"/ingresar.html"); }
        start.setOnClickListener(v->requestStart());
        stop.setOnClickListener(v->{stopService(new Intent(this,LocationTrackingService.class));message("GPS detenido. Última posición caduca en la central.");});
    }
    private void openOutside(Uri uri){
        String scheme=uri.getScheme();
        if ("https".equalsIgnoreCase(scheme) || "waze".equalsIgnoreCase(scheme) || "geo".equalsIgnoreCase(scheme)) {
            try{startActivity(new Intent(Intent.ACTION_VIEW,uri));}
            catch(Exception ex){message("No hay aplicación para abrir ese enlace");}
        }else{message("Se bloqueó un enlace no seguro");}
    }
    private void requestStart(){
        if(BuildConfig.BASE_URL.endsWith(".invalid")){message("Falta configurar el servidor HTTPS");return;}
        if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED &&
                checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED){
            pendingStart=true;requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},REQ_LOCATION);return;
        }
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
            // Notificaciones mejoran visibilidad; en Android se puede iniciar FGS aunque se deniegue.
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},REQ_LOCATION+1);
        }
        worker.execute(()->{
            try {MetroApi.validateReady();runOnUiThread(()->{
                try {
                    Intent i=new Intent(this,LocationTrackingService.class);
                    i.setAction(LocationTrackingService.START);
                    startForegroundService(i);
                    status.setText("GPS nativo iniciado · notificación permanente");
                }catch(Exception e){message("No se pudo iniciar GPS: "+e.getMessage());}
            });}catch(Exception e){message("GPS no iniciado: "+e.getMessage());}
        });
    }
    @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] results){
        super.onRequestPermissionsResult(requestCode,permissions,results);
        if(requestCode==REQ_LOCATION && pendingStart){pendingStart=false;
            boolean granted=checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED ||
                    checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED;
            if(granted)requestStart();else message("No autorizaste GPS; no se enviará ubicación");
        }
    }
    @Override public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override protected void onDestroy(){web.destroy();worker.shutdownNow();super.onDestroy();}
}

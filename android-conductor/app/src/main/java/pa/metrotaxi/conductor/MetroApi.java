package pa.metrotaxi.conductor;

import android.webkit.CookieManager;
import org.json.JSONObject;
import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** Solo el origen HTTPS del propio Metro Taxi. No se guardan contraseñas ni tokens en archivos. */
final class MetroApi {
    private MetroApi() {}
    private static HttpURLConnection connect(String path, String method) throws Exception {
        URL url = new URL(BuildConfig.BASE_URL + path);
        if (!"https".equals(url.getProtocol()) || !BuildConfig.BASE_URL.equals(url.getProtocol() + "://" + url.getAuthority()))
            throw new SecurityException("Origen HTTPS no confiable");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setInstanceFollowRedirects(false);
        conn.setRequestMethod(method);
        conn.setConnectTimeout(6000);
        conn.setReadTimeout(6000);
        conn.setUseCaches(false);
        conn.setRequestProperty("Accept", "application/json");
        String cookies = CookieManager.getInstance().getCookie(BuildConfig.BASE_URL);
        if (cookies != null && !cookies.isEmpty()) conn.setRequestProperty("Cookie", cookies);
        return conn;
    }
    static JSONObject get(String path) throws Exception {
        HttpURLConnection conn=connect(path,"GET");
        try {
            int status=conn.getResponseCode();
            if(status != 200) throw new Exception("HTTP " + status);
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            try(InputStream input=conn.getInputStream()) {
                byte[] chunk=new byte[4096];int n;
                while((n=input.read(chunk))!=-1) {
                    if(buffer.size()+n>65536) throw new Exception("Respuesta demasiado grande");
                    buffer.write(chunk,0,n);
                }
            }
            return new JSONObject(new String(buffer.toByteArray(), StandardCharsets.UTF_8));
        } finally { conn.disconnect(); }
    }
    static JSONObject driverSession() throws Exception {
        JSONObject me=get("/api/me");
        if(!me.optBoolean("authenticated") || !"driver".equals(me.optJSONObject("user") == null ? "" : me.getJSONObject("user").optString("role")))
            throw new SecurityException("Inicia sesión como conductor antes de activar GPS");
        return me;
    }
    static void validateReady() throws Exception {
        driverSession();
        JSONObject mine=get("/api/mine").optJSONObject("driver");
        if(mine==null || mine.optBoolean("suspended") || "off".equals(mine.optString("status")))
            throw new SecurityException("Ponte de servicio y verifica tu cuenta");
    }
    static void postLocation(double lat, double lng, float accuracy) throws Exception {
        JSONObject me=driverSession();
        JSONObject body=new JSONObject();
        body.put("lat",lat);body.put("lng",lng);
        body.put("accuracy_m",(double)accuracy);body.put("consent",true);
        post("/api/driver/location",body,me.getString("csrf"));
    }
    static void stopLocation() throws Exception {
        JSONObject me=driverSession();
        post("/api/driver/location/stop",new JSONObject(),me.getString("csrf"));
    }
    private static void post(String path, JSONObject body, String csrf) throws Exception {
        HttpURLConnection conn=connect(path,"POST");
        try {
            conn.setRequestProperty("Content-Type","application/json; charset=utf-8");
            conn.setRequestProperty("X-CSRF-Token",csrf);
            conn.setDoOutput(true);
            try(OutputStream out=conn.getOutputStream()) {out.write(body.toString().getBytes(StandardCharsets.UTF_8));}
            int code=conn.getResponseCode();
            if(code!=200)throw new Exception("Metro Taxi rechazó la ubicación (HTTP "+code+")");
        } finally {conn.disconnect();}
    }
}

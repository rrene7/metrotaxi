# Metro Taxi Conductor — proyecto Android nativo (v0.10 staging, sin compilar)

## Qué contiene

- Proyecto Android Studio **Java**, `minSdk 26`, `targetSdk 35`, Gradle/AGP `8.7.3`.
- Pantalla de acceso a la interfaz `/ingresar`/`/conductor` del **sitio HTTPS de Metro Taxi en Netlify (con proxy /api/* hacia el backend)**, dentro de un WebView restringido al mismo origen; sin `addJavascriptInterface`.
- Botones Android nativos «Iniciar GPS» y «Detener GPS» que controlan un `ForegroundService` tipo `location`, con notificación permanente.
- GPS transmitido a `/api/driver/location` con **cookie de sesión existente**, verificación de rol conductor y token **CSRF vigente**; rechaza usuarios fuera de turno y destinos HTTP.
- Enlaces Waze/Google Maps se abren fuera del WebView. Sin contraseña, API secret o teléfono de clientes dentro del APK.

## Para compilar y probar

1. Instalar Android Studio, SDK Platform 35, Build Tools y JDK 17.
2. Abrir carpeta `android-conductor` en Android Studio.
3. Usar Gradle 8.9 con plugin Android 8.7.3. Si Android Studio solicita wrapper, generar con Gradle 8.9 instalado: `gradle wrapper --gradle-version 8.9`. Se incluye `gradle/wrapper/gradle-wrapper.properties`; no se distribuye `gradle-wrapper.jar` sin verificar.
4. Ejecutar con **dominio HTTPS real** y API autorizada: `gradle :app:assembleDebug -PmetroBaseUrl=https://app.tudominio.com` (reemplaza dominio por uno propio).
5. Instalar el APK debug generado por Android Studio en teléfono **de pruebas**. Iniciar sesión como conductor, activar estado **Disponible** en la pantalla web y después «Iniciar GPS» en barra nativa.
6. Verificar que aparece una **notificación permanente de ubicación** y que `/api/mine` informa `location_source=device`, `simulated=false` y hora reciente. Volver a la pantalla; tocar Detener GPS y verificar que desaparece la ubicación.
7. Validar pantalla apagada, reconexiones, batería, permisos Android 14/15, suspensión, cierre de sesión, pérdida de cobertura y rutas Waze/Maps **en teléfonos físicos**. Marcar el checklist; aún no se ha realizado.

**IMPORTANTE:** El APK abrirá `/ingresar.html` del portal y usará `https://app.tudominio.com/api/*` a través del proxy Netlify. Confirma previamente que login, cookies de sesión, CSRF y GPS responden correctamente desde el portal. `https://example.invalid` es marcador de posición: sin dominio publicado la app **no conecta**. No apuntar a `127.0.0.1` ni exponer `server.py`/SQLite actual a Internet. Este proyecto **no incluye APK compilado o firmado**: no se dispone de Android SDK aquí. Firma release solo tras revisar seguridad, backend y permisos, usando claves privadas fuera de GitHub.

**Limitación consciente:** el seguimiento puede detenerse por batería, permisos o sistema operativo; no se garantiza 100 % continuidad. Conductor debe iniciar GPS voluntariamente desde primer plano. No se solicita `ACCESS_BACKGROUND_LOCATION` porque el caso piloto inicia un servicio visible desde la actividad abierta; antes de publicar revisar políticas de ubicación de Google Play. Si se pierde sesión, el servicio detiene la transmisión y el servidor caduca la posición al pasar el umbral.

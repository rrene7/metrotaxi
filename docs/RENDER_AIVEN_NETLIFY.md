# Metro Taxi — Piloto de costo cero: Netlify + Render Free + Aiven PostgreSQL Free

**Estado:** preparación de código. No afirmar que Render/Aiven/Netlify estén desplegados hasta verificar las URLs reales y sus paneles. Esto es **staging privado con datos ficticios**, no producción.

## Arquitectura

- **Netlify Free:** web estática `web-staging/` para pasajero, central y conductor; utiliza proxy `/api/*` cuando el backend HTTPS esté activo y probado. El dominio de Netlify se determina en tu cuenta, no desde GitHub.
- **Render Free:** API FastAPI, `cloud.pilot:app`, en contenedor Docker declarado en `render.yaml`. Render puede dormir el servicio tras 15 minutos de inactividad: **no sirve para despacho continuo en calle**.
- **Aiven PostgreSQL Free:** base de datos externa PostgreSQL; **no** uses SQLite ni almacenes credenciales en `render.yaml`. La versión gratuita tiene límites y puede suspenderse tras inactividad.

## 1. Base de datos Aiven

1. Desde [Aiven Console](https://console.aiven.io/) crea un servicio **PostgreSQL Free** en un proyecto de pruebas. Selecciona una base nueva sin datos personales; guarda las credenciales en el panel Aiven o tu gestor de secretos.
2. En «Connection information», copia la **URI de servicio** y configura TLS: `sslmode=require`. No publiques la URI ni el certificado en GitHub o chat. Si deseas verificar el certificado, consulta el modo `verify-full` con el CA de Aiven y valida el paquete de certificados dentro del contenedor.
3. Comprueba que la base acepta conexiones desde Render, respetando las políticas de IP/red de Aiven. No publiques las credenciales ni abras acceso administrativo innecesario.

## 2. API en Render (piloto privado)

1. En [Render Dashboard](https://dashboard.render.com/) conecta **GitHub** con acceso al repositorio `rrene7/metrotaxi`. Crea **New → Blueprint** con el `render.yaml` en la raíz de la rama `main`. El archivo declara **solo un Web Service Free**, no una base PostgreSQL de pago.
2. Introduce las variables **dentro de Render**, no en el repositorio:

| Variable | Qué colocar |
|---|---|
| `DATABASE_URL` | URI PostgreSQL de Aiven con TLS (por ejemplo, agregando `sslmode=require` a los parámetros). |
| `METRO_ALLOWED_ORIGINS` | `https://TU-DOMINIO-REAL.onrender.com` y, después de verificar el proxy, el dominio HTTPS de Netlify si es necesario. |
| `METRO_ALLOWED_HOSTS` | `TU-DOMINIO-REAL.onrender.com` sin protocolo. |
| `METRO_PILOT_USER` | `metrotaxi`, definido en el Blueprint. |
| `METRO_PILOT_PASSWORD` | Render genera una clave aleatoria, guárdala con seguridad; no la pegues en chats. |
| `METRO_BOOTSTRAP_EMPTY_DB` | `1` **únicamente en la primera inicialización sobre Aiven totalmente vacío**; cambiar a `0` al confirmar el esquema. |
| `METRO_PILOT_OSM_TILES` | `0` inicialmente. La app funciona sin mapas hasta habilitar proveedor autorizado. |

3. La URL `https://TU-DOMINIO-REAL.onrender.com/api/health` debe devolver `{"ok":true,"database":"ready",...}`. Si falla, revisa las variables/host/red y logs sin copiar las contraseñas. Si Aiven contiene tablas, el servidor **se negará a alterarlas automáticamente**.
4. Una vez inicializada la base, cambia `METRO_BOOTSTRAP_EMPTY_DB=0`. La aplicación no debe actualizar esquemas preexistentes automáticamente. Crea cuentas de prueba (admin, operador, conductor) usando el comando interactivo `python -m cloud.manage --create-admin` y sus opciones, ejecutado en una terminal del contenedor autorizada; **Render Free puede no ofrecer shell interactiva**. Si no tienes consola segura, no se pueden crear cuentas mediante la web existente: hay que preparar un bootstrap seguro antes de habilitar usuarios. **No** abras un endpoint público para crear administradores ni pongas contraseñas en comandos o variables de GitHub.
5. Comprueba desde tu PC la barrera privada y la conexión a PostgreSQL con:

```powershell
py -3.12 -m scripts.verificar_piloto_https --url https://TU-DOMINIO-REAL.onrender.com
```

La comprobación es solo lectura y anónima: exige HTTPS, PostgreSQL listo y 401 de protección en rutas privadas. Una salida correcta **no** acredita que las sesiones de usuarios funcionen.

## 3. Web en Netlify

La preparación `scripts/preparar_netlify.py` genera una carpeta estática con un proxy para `/api/*` a una API HTTPS confirmada. Desde PowerShell en el repositorio actualizado:

```powershell
py -3.12 scripts/preparar_netlify.py --api-url https://TU-DOMINIO-REAL.onrender.com --output netlify-dist
```

- No publiques la carpeta si el backend no supera las pruebas; no incluyas `.env`, bases de datos ni datos personales.
- La protección HTTP Basic puede presentar dificultades con el proxy Netlify y las cabeceras `Authorization`; **probarla expresamente** antes de utilizar la web. De no funcionar, no elimines la barrera para que la página cargue.
- Comprueba cookies `Secure; HttpOnly`, CSRF y `Origin` del dominio Netlify. Configurar `METRO_ALLOWED_ORIGINS` para el origen real del navegador es obligatorio.
- El frontend Netlify no almacena PostgreSQL ni ejecuta FastAPI; Render es el servidor.

## Limitaciones de seguridad y disponibilidad

- Render Free suspende instancias inactivas. Puede haber demoras en la primera petición y la disponibilidad continua del despacho **no está garantizada**.
- Aiven Free puede suspender servicios por inactividad; no es infraestructura de operación continua.
- Antes de pasajeros reales: OTP/verificación de teléfono, límites antiabuso, controles de GPS falsificado, copias/restauración, política de datos, proveedor cartográfico autorizado y pruebas en teléfonos físicos.
- Este conjunto **no es producción** ni debe recibir información privada real mientras esas barreras estén pendientes.

Consulta [Blueprint YAML Render](https://render.com/docs/blueprint-spec), [Render Free](https://render.com/docs/free) y [Aiven PostgreSQL TLS](https://aiven.io/docs/products/postgresql/howto/list-code-samples).

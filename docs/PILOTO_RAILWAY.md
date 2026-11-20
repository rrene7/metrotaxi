# Metro Taxi — Piloto HTTPS restringido con Railway + PostgreSQL

**Estado:** configuración preparada y probada en CI; la nube NO queda activada hasta que el propietario conecte su cuenta Railway, genere un dominio y establezca sus propias variables. No habilitar pasajeros reales todavía. La demo pública con taxis ficticios ya está en https://rrene7.github.io/metrotaxi/.

## Arquitectura del piloto

- Un servicio web Railway sirve la API FastAPI **y** `web-staging/` desde el mismo dominio HTTPS. No necesita Netlify ni redirecciones para esta prueba, por lo que la cookie `Secure` y el CSRF trabajan en el mismo origen.
- Un servicio PostgreSQL separado almacena sesiones y carreras. **No habilitar acceso público a PostgreSQL.**
- Acceso HTTP Basic previo a todas las páginas/API excepto `/api/health`. La contraseña del piloto es **distinta** de las contraseñas del personal; no está en GitHub.
- `cloud.preview` y bases SQLite solo se usan en local. Nunca migrar automáticamente `runtime/` ni `_runtime_staging/`.
- Los tiles/rutas web comerciales requieren proveedor apropiado. OSM público solo se permite expresamente para un piloto muy pequeño y no como proveedor comercial.

## Configuración inicial en Railway

1. Conecta GitHub y elige el repositorio `rrene7/metrotaxi`, rama `main`. Crear un proyecto Railway nuevo llamado `Metro Taxi Piloto` y agregar PostgreSQL desde `+ New` → `Database` → `PostgreSQL`.
2. Crea servicio Web desde el mismo GitHub y utiliza el `Dockerfile` en raíz (Railway detecta `railway.toml`). En Network → **Generate Domain** obtendrás algo como `mi-piloto.up.railway.app` (es un ejemplo, NO es una URL activa).
3. En Variables del **servicio Web** establece, con tus valores reales:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | Referencia a la base privada: `${{Postgres.DATABASE_URL}}` (ajusta `Postgres` al nombre del servicio DB) |
   | `METRO_ALLOWED_HOSTS` | `mi-piloto.up.railway.app,healthcheck.railway.app` |
   | `METRO_ALLOWED_ORIGINS` | `https://mi-piloto.up.railway.app` |
   | `METRO_PILOT_USER` | `metrotaxi` o un usuario distinto |
   | `METRO_PILOT_PASSWORD` | **Clave aleatoria única de 20+ caracteres** creada por ti |
   | `METRO_BOOTSTRAP_EMPTY_DB` | `1` **solo para primer arranque** en una base verdaderamente vacía |
   | `METRO_PILOT_OSM_TILES` | `1` solo si aceptas usar tiles OSM para una prueba limitada, o `0` para configurar proveedor propio |

   No agregues `.env` al repositorio, no uses contraseñas ficticias ni `cloud.preview:app`. No publiques el puerto TCP de PostgreSQL.
4. Railway despliega con HTTPS. Abre `https://TU-DOMINIO/api/health`: debe responder `ok=true` y `database=ready`. Si devuelve error, inspecciona logs antes de permitir pruebas.
5. Cuando la base esté inicializada, cambia `METRO_BOOTSTRAP_EMPTY_DB=0`. La aplicación se negará a modificar automáticamente bases parciales; para cambios posteriores se necesitan migraciones revisadas.
6. Abre `https://TU-DOMINIO/`. El navegador pedirá el **usuario y clave del piloto** (barrera básica). Después aparecerá el acceso del personal y pasajeros. La barrera no sustituye políticas de autenticación completas.
7. Dentro de Railway, con CLI y cuenta autorizada, crea cuentas sin contraseñas en argumentos:

   ```bash
   railway ssh -- python -m cloud.manage --create-admin
   railway ssh -- python -m cloud.manage --create-driver
   railway ssh -- python -m cloud.manage --create-operator
   ```

   El alta de conductor pide unidad, nombre, sede (`Pacora` o `24 de Diciembre`), usuario y contraseña. Se requiere `railway login` y vincular el CLI al proyecto y servicio de Railway. No compartir contraseñas en capturas o chats.
8. Comprueba los tres roles con cuentas ficticias, el GPS autorizado y el flujo solicitud → asignar → aceptar → iniciar → terminar. Para varias sesiones usa navegadores o perfiles distintos. Nunca pruebes con pasajeros reales hasta completar antiabuso, OTP, retención de datos, proveedor de mapas y pruebas físicas Android.

## Mapas de la web

- En Railway el archivo `/map-config.js` se genera en el backend; no contiene credenciales privadas. Para un proveedor adecuado establece `METRO_MAP_TILES_URL=https://.../{z}/{x}/{y}.png` (plantilla raster HTTPS). **Las claves dentro de una URL de tiles son visibles para el navegador.**
- Si no se configura proveedor, la app muestra aviso pero las carreras funcionan sin mapa.
- Para pilotos diminutos `METRO_PILOT_OSM_TILES=1` habilita tiles públicos de OSM con atribución, respetando su política de uso; no es un proveedor para operación comercial.
- El recorrido por calles de pruebas externo no está habilitado en dominio público hasta configurar un servicio real. Línea punteada significa distancia directa, no ruta vial ni ETA.

## Barreras pendientes antes de producción

Ver `docs/PLAN_SALIDA_A_PRODUCCION.md`: limitar fuerza bruta/registro, verificar teléfonos, asegurar acceso y retención, migraciones, respaldo-restauración, proveedor profesional de mapas, notificaciones/colas, 200–300 carreras/día y pruebas Android en carretera. No anunciar que esta configuración sea producción.


## Activación y verificación del piloto — DEPLOY-109 (noviembre de 2026)

**Este repositorio no crea ni cobra recursos de Railway por sí solo.** El titular debe autorizar la conexión a GitHub, elegir o crear el proyecto y confirmar las condiciones de Railway. No pegues contraseñas, variables privadas, enlaces de administración ni tokens en chats, commits ni capturas.

1. Abre https://railway.com/new y crea un proyecto vacío llamado **Metro Taxi Piloto**. Usa `+ New → Database → PostgreSQL`; la base debe permanecer en **red privada**, sin acceso TCP público.
2. Agrega otro servicio con **GitHub Repo → rrene7/metrotaxi → main**, desde la raíz del repositorio, usando el `Dockerfile` y `railway.toml` existentes. Obtén el hostname bajo **Settings → Networking → Generate Domain**. En el servicio web, configura `DATABASE_URL` con la referencia privada que proporciona Railway a PostgreSQL.
3. Agrega las variables privadas indicadas en la tabla anterior, usando **tu hostname real** en `METRO_ALLOWED_ORIGINS` y `METRO_ALLOWED_HOSTS`, además de `healthcheck.railway.app`. No escribas `https://` en la variable de hosts; sí en la de orígenes. La contraseña de acceso al piloto debe ser única, aleatoria y de más de 20 caracteres.
4. Activa `METRO_BOOTSTRAP_EMPTY_DB=1` **solo para el primer inicio sobre PostgreSQL realmente vacío**. Verifica `/api/health` y entonces establece `METRO_BOOTSTRAP_EMPTY_DB=0`. Si la base no está vacía, no fuerces el arranque ni borres tablas; inspecciona la estructura.
5. En la consola SSH del **servicio web** (no la consola de PostgreSQL), crea administrador, operador y conductor con `railway ssh -- python -m cloud.manage --create-admin` y opciones correspondientes. El comando solicita la contraseña de forma interactiva; no la incluyas en argumentos o variables de GitHub.
6. Ejecuta la verificación externa **sin introducir credenciales** desde tu PC, en la raíz del repositorio:

```powershell
py -3.12 -m scripts.verificar_piloto_https --url https://DOMINIO-REAL.up.railway.app
```

También puedes abrir GitHub → **Actions → Metro Taxi - Comprobar piloto HTTPS → Run workflow** e introducir solamente la URL HTTPS pública (no la contraseña). El verificador exige que `/api/health` reporte PostgreSQL disponible y que las rutas privadas respondan 401 + HTTP Basic cuando se consultan **sin** contraseña. **No realiza POST ni registra carreras.**

La comprobación HTTPS no sustituye las pruebas autenticadas de sesión/CSRF, geocerca, mapas, cobros, recuperación, derechos de datos, dispositivos reales y disponibilidad del proveedor. El piloto solo se habilita para cuentas ficticias y un grupo limitado de pruebas; **aún no hay autorización para pasajeros reales**.

**Si usas ChatGPT con la integración Railway**, primero conéctala desde tu cuenta: el repositorio en GitHub no concede por sí mismo acceso a Railway.

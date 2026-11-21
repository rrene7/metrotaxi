# Metro Taxi — registro de incidentes y prevención de recurrencia

| ID | Versión | Síntoma reportado | Causa encontrada | Reparación aplicada | Prueba obligatoria |
| --- | --- | --- | --- | --- | --- |
| REDIR-081 | 0.8.1 | Central recargaba/redirigía continuamente | Sesión de pasajero enviada erróneamente a central | Rutas por rol en servidor y pantalla de acceso | `test_auth_navigation_v081.py` |
| CSRF-082 | 0.8.2 | «Falta protección CSRF» al operar | Token de pestaña no actualizado en operaciones protegidas | Renovación desde sesión y reintento restringido al error específico | `test_csrf_v082.py` y `test_csrf_frontend_v082.cjs` |
| NAV-083 | 0.8.3 | Waze añadido, pero no se veía la carrera | Script nuevo no presente al actualizar parcialmente | El enlace se genera en `driver.js`; no es dependencia aparte | Validador de recursos + `test_driver_loading_v084.cjs` |
| LOAD-084 | 0.8.4 | Panel «Servicios que me ofreció» permanece en «Cargando…» | Excepción de JavaScript interrumpía el renderizado | `try/catch` con aviso y botón Reintentar; sin dependencia de navegación externa | `test_driver_loading_v084.cjs` |

## Nuevas barreras de regresión v0.10

| Riesgo | Prevención aplicada | Prueba |
| --- | --- | --- |
| CLOUD-DATA | Nueva API nube usa BD distinta; no se importa ni sobrescribe `runtime/` automáticamente | `tests_cloud/test_cloud_flow.py` y exclusiones `.gitignore` |
| CLOUD-CSRF | El token CSRF se almacena por sesión en DB, protegido por cookies; no se desactiva al separar frontend | `tests_cloud/test_cloud_flow.py::test_csrf_stays_mandatory` |
| CLOUD-ACL | Cliente no consulta la flota; conductor no recibe teléfono ni carreras ajenas; GPS solo de unidad aceptada | `tests_cloud/test_cloud_flow.py` |
| CLOUD-DEPLOY | No generar `_redirects` con URL HTTP/falsa ni incluir credenciales o bases en Netlify | `tests_cloud/test_netlify_builder.py` |
| CLOUD-LOAD | Todas las pantallas staging exponen error y Reintentar si falla la API | `tests_cloud/test_web_guard.py` y verificación manual pendiente |

## Protocolo ante un error nuevo

1. Registrar captura/URL, rol, versión, acción, mensaje, hora, navegador y si hay pérdida de datos (sin copiar datos personales).
2. Reproducir con una prueba; identificar causa raíz. Comprobar si es el mismo patrón de alguno de los incidentes anteriores.
3. Aplicar cambio mínimo; agregar prueba de regresión estable y verificar permisos, sesiones, API y actualización parcial.
4. Ejecutar **toda** la puerta de calidad en `scripts/validar_entrega.bat` en Windows, o ejecutar validación JS y batería Python por separado.
5. Actualizar `RUTA_DE_TRABAJO.md`, esta tabla y el procedimiento para actualizar sin tocar `runtime/`.
6. Verificar manualmente en Chrome/Edge y teléfonos si cambia la interfaz, GPS o Waze. La ausencia de prueba física se reporta explícitamente.

**Importante:** el propósito es reducir recurrencias; las pruebas no garantizan ausencia absoluta de errores.

## DEP-101 — Error greenlet en Python 3.9 (20-11-2026)

**Síntoma:** `Failed building wheel for greenlet`, solicita `Microsoft Visual C++ 14.0`, traza `win-amd64-cpython-39`, `pip 22.0.4`.

**Causa:** el BAT arrancaba con `py -3`, que escogía Python 3.9 del usuario; el paquete binario compatible no estaba disponible para esa combinación y pip intentaba compilar código nativo.

**Corrección:** BAT selecciona explícitamente Python 3.12/3.11/3.13 x64, usa su propio entorno virtual, actualiza pip e instala con `--only-binary=:all:`. No instalar compiladores como primer remedio, no alterar Python de otros proyectos.

**Control:** `tests/test_windows_staging_launcher_v101.py`, prueba manual en Windows con `py -0p`, `iniciar_staging_windows.bat`, health `http://127.0.0.1:8770/api/health`.

## ORIGIN-102 — Inicio de sesión bloqueado en staging local (20-11-2026)

**Síntoma:** `/api/me` 200 OK y `POST /api/login` 403 Forbidden repetidamente al entrar desde `http://127.0.0.1:8770`.

**Causa comprobada:** `verify_origin` solo aceptaba `http://testserver` en modo de pruebas, no el origen real que envían Chrome/Edge en POST (`http://127.0.0.1:8770`). La contraseña ni siquiera llegaba a validarse.

**Corrección:** autorizar exclusivamente `http://127.0.0.1:8770` y `http://localhost:8770` además de `http://testserver` **solo en test_mode**. Ningún origen HTTP local se autoriza en producción. Mantener comprobación de contraseña y token CSRF.

**Prevención:** `tests_cloud/test_login_origin_v102.py` prueba login, rechazo de orígenes externos, contraseña incorrecta, CSRF tras iniciar sesión y registro de cliente. Verificar manualmente en Chrome/Edge.

## ANDROID-BUILD-103 y MAP-104 — CI y recorrido estable (20-11-2026)

- **ANDROID-BUILD-103:** GitHub Actions falló en `:app:compileDebugJavaWithJavac`; `android.webkit.WebViewTransport` no es una clase de nivel superior. Se usa `WebView.WebViewTransport` y un guardia en `tests/test_android_source_v09.py`. Es obligatorio verificar el resultado real de Gradle en CI antes de afirmar que existe APK funcional.
- **MAP-104:** `MetroMap.update()` eliminaba la polilínea cada vez que se actualizaban los taxis o las carreras. Ahora actualiza marcadores sin borrar la ruta; `clearRoute()` la limpia al cambiar de carrera o faltar puntos válidos. Prueba `tests_cloud/test_map_route_persistence.cjs`, incluida en `scripts/validar_cloud.py`.
- **Pendientes:** comprobar mapas y GPS en Chrome/Android físico. El trazado en línea recta y el proveedor vial de pruebas no equivalen a ruta de producción ni garantizan tiempo de llegada.

## GPS-105 — destino y polilínea desactualizados (20-11-2026)

Se observó que la línea podía quedar estática tras una actualización GPS y, en el conductor, la fase en progreso dibujaba recogida → destino aunque hubiera GPS real. Se corrige refrescando el segmento desde la posición autorizada al punto correspondiente al estado, sin recentrar la vista. Si no existe GPS reciente, el trayecto es solo referencial (sin marcador inventado). Prueba `tests_cloud/test_tracking_segment.cjs`.


## PILOT-106 — Controles contra publicación insegura (20-11-2026)

- Riesgo: desplegar `cloud.preview` por error o publicar SQLite y claves de demostración. Control: Docker ejecuta exclusivamente `cloud.pilot:app`, Dockerfile sin root, .dockerignore sin datos/secretos y URL PostgreSQL obligatoria.
- Riesgo: registrar usuarios sin control en una URL pública. Control provisional: clave adicional de acceso HTTP Basic para un grupo pequeño de pruebas, `METRO_PILOT_PASSWORD` de 20+ caracteres, requerimiento de HTTPS y configuración explícita de orígenes/hosts. No sirve como endurecimiento final.
- Riesgo: alterar una base activa durante desplegado. Control: bootstrap exclusivo de base completamente vacía, bandera explícita, negativa ante tablas faltantes.
- Riesgo: mapa en blanco en dominio remoto. Control: servir `/map-config.js` desde API con proveedor raster HTTPS configurable. OSM para prueba limitada solamente con elección explícita.
- Pruebas: `tests_cloud/test_railway_pilot.py`, `tests_cloud/test_manage_pilot.py` y `tests_cloud/test_postgres_pilot.py` en PostgreSQL efímero de GitHub Actions.

## PRIV-106 / ARRIVAL-107 — privacidad y geocerca en despacho (20-11-2026)

El pasajero ya no recibe ofertas ni datos del conductor antes de la aceptación; historial y carrera activa se separan en pestañas. El servidor verifica la cercanía GPS al punto de recogida (≤150 m) y destino (≤180 m), precisión ≤75 m y antigüedad ≤120 s para iniciar y finalizar. Sin coordenadas, bloquea la acción. La geocerca es un control piloto, no autenticación de GPS frente a suplantación; antes del uso comercial se requieren mecanismos antifraude y pruebas reales. Tests en `tests_cloud/test_cloud_flow.py` y `tests_cloud/test_map_route_persistence.cjs`.

## POINT-108 — Carrera sin GPS no podía iniciar ni finalizar (20-11-2026)

**Síntoma:** la central registraba una carrera telefónica sin coordenadas de recogida/destino y el servidor la bloqueaba correctamente por la geocerca, pero la central no tenía cómo registrar las coordenadas confirmadas después.

**Causa:** faltaban el endpoint autenticado para corregir puntos y su control en la interfaz. No corresponde eliminar ARRIVAL-107 porque permitiría marcar una carrera desde cualquier lugar.

**Solución:** API `POST /api/trips/point` con rol admin/operador, CSRF, Origin, confirmación explícita con pasajero, validación numérica/finita, control por estado, actualización transaccional con comprobación de versión de coordenadas y auditoría. La central selecciona sobre mapa o introduce datos recibidos; se etiqueta como punto confirmado, no como GPS del conductor.

**Regresión obligatoria:** probar con conductor sin GPS (409), cargar punto de recogida confirmado, iniciar solo cerca, registrar destino en curso, finalizar solo cerca, negar cambio de punto al cerrar, negar usuarios ajenos y coordenadas inválidas. Tests en `tests_cloud/test_cloud_flow.py`, guardias de la interfaz en `tests_cloud/test_web_guard.py`.


## DB-109 — Inicialización administrativa sin protección ante tablas existentes (20-11-2026)

**Riesgo:** el comando `python -m cloud.manage --init-schema` ejecutaba `metadata.create_all` directamente. En una base parcialmente configurada podía agregar tablas sin plan ni revisión y ocultar un fallo de migración.

**Corrección:** `initialize_empty_schema()` comprueba primero que no exista ninguna tabla y reutiliza `ensure_schema` de la barrera de piloto. Ante cualquier tabla previa falla sin alterarla. La opción de primer arranque sigue destinada solo a bases nuevas; las migraciones de datos requieren un proceso independiente.

**Prevención:** `tests_cloud/test_pilot_deploy_readiness.py` comprueba base vacía, base con tablas y que un segundo intento no modifica tablas. El mismo test vigila dominios HTTPS y rechazo de rutas públicas sin contraseña.


## NETLIFY-111 — Riesgo de desplegar pantallas de staging sin API (20-11-2026)

**Problema evitado:** una conexión directa del repositorio a Netlify puede publicar `web-staging/` con botones que envían llamadas `/api/*` sin un backend HTTPS real, provocando inicio de sesión y solicitudes fallidas. Publicar el piloto local por error expondría datos y sesiones.

**Solución:** un `netlify.toml` con carpeta pública específica `netlify-public/` que contiene únicamente la demostración ficticia conocida de GitHub Pages, más tests que rechazan pérdida de privacidad, caché inconsistente, configuraciones de pago y presencia de componentes privados. La actualización real del backend se hará en una fase independiente con HTTPS y pruebas de autorización/CSRF.


### NETLIFY-112 — Mapa que impide iniciar la demostración (21-11-2026)

- **Riesgo:** una excepción lanzada por Leaflet al crear el mapa interrumpe la inicialización y bloquea botones, incluso cuando el despacho ficticio no depende del mapa.
- **Solución:** manejar el fallo durante `initMap()`, avisar que el mapa no está disponible y continuar con `render()`.
- **Prevención:** prueba Node que fuerza el fallo y verifica que solicitar/asignar conserva funcionalidad; revisión del hash del JS para despliegue sin caché incompatible.
- **Pendiente:** ejecución de CI y recorrido visual en la URL pública; no equivale a validación de mapa/GPS real.


## CENTRAL-113 — Refresco del tablero destruye operaciones en curso (21-11-2026)

- **Causa:** reconstrucción periódica de `#trips` y `#drivers` mediante `innerHTML` mientras el operador escribía una tarifa, elegía una unidad o editaba un vehículo.
- **Corrección:** diferenciar refresco programado de manual y omitir el automático con editor abierto, foco activo o formulario sin guardar. Revisar de nuevo el bloqueo después de la respuesta de la API para evitar una condición de carrera.
- **Control:** `tests_cloud/test_central_autorefresh_guard.cjs` ejecutado por `scripts/validar_cloud.py`; verificar visualmente selección, edición y guardado en 2 navegadores. No sustituye pruebas en el navegador.


## CUSTOMER-114 — actualización atrasada en pantalla del pasajero (21-11-2026)

- **Síntoma posible:** al coincidir sondeo automático con solicitud/cancelación, la respuesta vieja podría reemplazar el estado nuevo o mostrar un error ya superado.
- **Causa:** cargas asíncronas de carreras/mensajes en paralelo, sin protección contra respuestas fuera de orden.
- **Solución:** generación incremental por consulta, invalidación antes de mutaciones y descarte de éxitos/errores de generaciones antiguas.
- **Regresión:** `tests_cloud/test_customer_polling_race.cjs` verifica la guardia y los puntos de invalidación. Revisión manual en dos navegadores y retraso de red pendiente.


## GPS-115 — Ubicación reaparece después de detener GPS (21-11-2026)

- **Causa:** carreras asíncronas entre `/api/driver/location` y `/api/driver/location/stop`, callbacks del watch anteriores aún activos y detención remota fallida silenciada.
- **Corrección:** invalidación de generación GPS antes de esperar, liquidación de carga pendiente previa al POST de detención, exclusión de arranques simultáneos, aviso al conductor cuando la detención en servidor no se confirma y no restaurar marcadores con respuestas antiguas.
- **Control:** `tests_cloud/test_driver_gps_stop_race.cjs` y recorrido manual en Chrome/Android con conexión intermitente; nunca afirmar que la API confirmó detención si devolvió error.


## DRIVER-116 — Lista de conductor mezclaba trabajos actuales e históricos (21-11-2026)

- **Causa:** el frontend representaba todas las carreras devueltas por `/api/mine` en una misma lista y dejaba seleccionada una carrera finalizada.
- **Solución:** paneles independientes, filtro de estados `done/cancelled` hacia historial, listado operativo de servicios activos con sus controles existentes, y limpieza de selección de mapa al cerrar la carrera.
- **Prueba:** `tests_cloud/test_driver_history_tabs.cjs` y validación visual pendiente en navegador y Android físico. No requiere migración ni modifica la API.


## DISPATCH-117 — barrera de regresión integral para carreras entre tres roles (21-11-2026)

- **Riesgo controlado:** mejoras independientes a cliente, central y conductor pueden romper el ciclo real o filtrar ofertas/identidad de conductor antes de aceptar.
- **Prueba:** `tests_cloud/test_cloud_flow.py::CloudFlowTests.test_three_independent_sessions_full_dispatch_and_history`: verifica cookies/CSRF distintos, privacidad, asignación central, GPS lejano (bloqueo 409), GPS cercano (inicio y final correctos), historial privado y conductor liberado.
- **Límite:** ejecución HTTP simulada con datos ficticios y SQLite aislada; además exigir PostgreSQL efímero de CI, revisión visual multiusuario y ensayo Android físico antes de operar. No afirmar validación GPS antifraude.


## LOCAL-118 — No confundir demostración pública con piloto Docker privado (21-11-2026)

- **Riesgo:** usar por accidente `cloud.preview`/SQLite en Internet, exponer PostgreSQL, almacenar contraseñas en Git o destruir datos al reiniciar Docker.
- **Control:** `compose.local.yaml` limita la publicación al loopback; PostgreSQL solo en red privada Docker con volumen persistente; `cloud.local_docker` exige backend Postgres `db/metrotaxi_local` y tablas creadas manualmente; `metro-local.env` fuera de Git y del contexto de build.
- **Pruebas:** `tests_cloud/test_local_docker_pilot.py` y batería CI. No usar `down -v`, comandos prune ni publicar puertos de la red local. Ensayo físico pendiente.


## LOCAL-119 — arranque Docker no cubierto por pruebas de código (21-11-2026)

- **Riesgo:** el CI anterior aprobaba sintaxis, API y estructura del Compose sin arrancar PostgreSQL y FastAPI juntos; podían existir fallos de red, configuración de URL, cookies, puerto o persistencia sin detectar.
- **Prevención:** job `docker-local-smoke` y script `scripts/smoke_local_docker.py` en runner efímero; validan primer bootstrap, /api/health, login desde Origin local, Host externo rechazado y persistencia después de stop/start. No usar base real ni contraseñas de usuarios.
- **Límite:** CI Linux no sustituye ensayo Windows Docker Desktop y Android físico; no afirmar acceso desde otros dispositivos ni despliegue online.


### Hallazgo CI LOCAL-119 — Importación del CLI bloqueada (21-11-2026)

- **Reproducción:** primer job real de Docker falla al ejecutar `python -m cloud.manage --init-schema` antes de crear tablas. El import de `cloud.app` construía automáticamente una API adicional en modo producción porque ya existía `DATABASE_URL`; exigía `METRO_ALLOWED_ORIGINS` HTTPS incluso cuando el comando era solo inicialización de PostgreSQL local.
- **Arreglo acotado:** `METRO_FACTORY_ONLY=1` solo en `compose.local.yaml` evita construir esa API implícita durante importaciones. `cloud.local_docker` continúa creando la app explícitamente mediante `create_app(..., test_mode=True, auto_create=False)` y exige PostgreSQL/schema. Producción y su validación de host/origen no se relajan.
- **Control:** prueba estática `test_factory_only_prevents_cli_from_building_unrelated_public_app` y prueba real del bootstrap mediante `docker-local-smoke`; verificar nueva ejecución de CI.

# METRO TAXI — RUTA DE TRABAJO OBLIGATORIA

**Versión de desarrollo:** 0.10.3 (recuperación parcial de módulos en API cloud staging; APK sin compilar)  
**Última revisión:** 20-11-2026  
**Estado:** dos entornos separados (v0.9 piloto local íntegro y v0.10 cloud staging de alcance parcial); NO apto para pasajeros reales ni publicación comercial.

## 0. Regla para toda modificación

Antes de editar código, el desarrollador o asistente debe **leer este archivo, `AGENTS.md`, `docs/INCIDENTES_Y_SOLUCIONES.md` y `docs/CONTRATO_OPERATIVO.md`**. Al terminar cada cambio, actualizar esta ruta, registrar los problemas conocidos y ejecutar `scripts/validar_entrega.bat` (Windows), o bien `python scripts/validar_entrega.py --quick` y después `python -m unittest discover -s tests -v` y `python scripts/validar_cloud.py` (incluye prueba DEP-101 del instalador). Una entrega que falle la validación no se distribuye como funcional. No borrar ni sobrescribir `runtime/`.

### Ciclo de desarrollo

1. **Revisar:** leer esta ruta, los incidentes previos, el contrato operativo y los pendientes.
2. **Delimitar:** indicar qué pantallas, endpoints y roles resultan afectados; revisar dependencias estáticas y permisos.
3. **Implementar:** pequeños cambios con compatibilidad de datos y protección CSRF/sesiones.
4. **Probar:** crear o actualizar una prueba que reproduzca el error, y ejecutar toda la batería y el verificador de archivos.
5. **Verificar manualmente:** probar el recorrido de pasajero → central → conductor → Waze → iniciar/finalizar en Chrome/Edge; no afirmar prueba visual si no se realizó.
6. **Entregar:** anotar fecha, versión, archivos cambiados, resultados, límites y procedimiento de actualización que conserve `runtime/`.

## 1. Estado de módulos

| Módulo | Estado 0.8.4 | Siguiente comprobación |
| --- | --- | --- |
| Cuenta cliente, consentimiento, QR | MVP local | Teléfono verificado, recuperación de cuenta |
| Central, dos sedes, despacho y roles | MVP local | Prueba visual de acceso y autorización |
| Conductor: ofertas, aceptar/iniciar/finalizar | MVP local | Prueba visual de lista, errores y reintentos |
| Navegar a recogida Waze / Google Maps | Incorporado para coordenadas explícitas | Abrir enlaces en Android físico |
| GPS del conductor | Solo mientras la página está abierta | GPS Android nativo en segundo plano |
| Despacho por cercanía | Piloto, opcional y manual por defecto | Precisión, carga y pruebas de operación |
| Mapa | Opcional y no bloqueante | Proveedor, visualización y SLA/costos |
| HTTPS y backend público | Pendiente | Rediseño seguro y PostgreSQL |
| APK Android | Código fuente adaptado en v0.10 a `/ingresar.html` en Netlify (sin compilar) | Compilar en Android Studio, probar GPS, firma y permisos |
| API cloud FastAPI | CRUD base de carreras, roles, sesiones BD, GPS, CSRF con 17 pruebas automatizadas | PostgreSQL real, antiabuso, auditoría e integración en Netlify |
| Web staging Netlify | Cliente, central y conductor mínimos, sin QR ni mensajería cloud | Probar proxy y cookies en HTTPS real; paridad con la v0.9 |

## 2. Errores que NO debemos repetir

| Incidente | Causa / riesgo | Control antes de entregar |
| --- | --- | --- |
| ORIGIN-102 | `POST /api/login` devolvía 403 al recibir `Origin: http://127.0.0.1:8770` en staging, aunque `/api/me` funcionaba | Lista explícita de orígenes de preview solo en `test_mode`; `tests_cloud/test_login_origin_v102.py` |
| DEP-101 | `py -3` seleccionó Python 3.9 y `pip` intentó compilar `greenlet` sin Visual C++ | Instalador explícito 3.11/3.12/3.13 x64 + venv + wheels binarias; test `test_windows_staging_launcher_v101.py` |
| REDIR-081 | Cliente autenticado redirigido a `/central` y vuelta a login | `tests/test_auth_navigation_v081.py` + probar cada rol |
| CSRF-082 | Operación envía token vacío o caducado | `tests/test_csrf_v082.py` y `tests/test_csrf_frontend_v082.cjs`; NUNCA quitar protección |
| NAV-083 | Archivo de navegación incorporado parcialmente; JS no disponible | Verificador de referencias HTML vs rutas del servidor |
| LOAD-084 | Lista del conductor quedó en «Cargando…» por excepción de navegación | `tests/test_driver_loading_v084.cjs`: con Waze, sin coordenadas y error API |
| CACHE | Navegador o PWA conserva recursos antiguos | Revisar caché, actualizar recurso/versión y probar `Ctrl+F5` |
| DATA | Sustituir archivos del proyecto pudo sobrescribir datos de usuarios | Respaldar `runtime/`, no incluirla en distribución, nunca borrar sin permiso |

Todos los antecedentes y sus acciones correctivas están en `docs/INCIDENTES_Y_SOLUCIONES.md`.

## 3. Prioridades de entrega

- **P0 v0.10:** mantener sin cambios los módulos `server.py`/SQLite local v0.9; evitar importar datos personales sin plan.
- **P0 v0.10:** probar backend cloud con PostgreSQL de staging real, revisar migraciones, permisos y cookies de Netlify.
- **P0 v0.10:** migrar QR, contactos, reportes, fotos y expedientes faltantes con pruebas; NO afirmar paridad mientras falten.

- **P0 (actual):** cerrar 0.8.4 con lista de carreras y navegación que no dependan de un archivo opcional; errores visibles y botón «Reintentar». Checklist de regresión único.
- **P1:** ejecutar prueba manual completa en Windows/Chrome con usuario, central y conductor; comprobar MT-3 aceptada y enlace Waze desde dispositivo Android (no se ha hecho aquí).
- **P1:** decidir y montar backend HTTPS con datos seguros, base gestionada y control de despliegues; evitar exponer Python/SQLite de demostración.
- **P1:** compilar el proyecto `android-conductor/` con Android SDK real, desplegar API HTTPS y probar servicio GPS, notificación, cookies/CSRF, permisos Android y pérdida de señal. No afirmar APK disponible sin compilar.
- **P2:** verificación de teléfono, recuperación de contraseña, auditoría y métricas de despacho.
- **P2:** corregir proveedor de mapa y revisar costes, licencias y disponibilidad.
- **P2:** pruebas de carga, copias de seguridad, incidentes y normas de retención de datos.

## 4. Puerta de calidad (obligatoria)

Ejecutar en la raíz del proyecto:

```powershell
# Windows: comprueba archivos, JavaScript y todas las pruebas del servidor
scripts\validar_entrega.bat
```

En Linux/macOS o CI, ejecutar **ambos** comandos: `python scripts/validar_entrega.py --quick`, `python -m unittest discover -s tests -v` y `python scripts/validar_cloud.py` (incluye prueba DEP-101 del instalador).

- Verifica documentación, recursos locales referenciados y rutas servidas, sintaxis JS y pruebas JavaScript.
- Ejecuta la batería Python de permisos, CSRF, clientes, GPS y despacho.
- Si Node.js no está instalado, la puerta de calidad **no aprueba**; puede ejecutarse el piloto, pero hay que completar pruebas antes de entregar una nueva versión.
- Para revisar más rápido durante edición: `python scripts/validar_entrega.py --quick`.
- Los cambios enviados a GitHub ejecutarán ambas fases por CI (`.github/workflows/validar.yml`).
- Además, el checklist manual de `docs/PRUEBAS_DE_ACEPTACION.md` debe completarse **en el dispositivo objetivo**, sin marcar comprobaciones que no se hicieron.

## 5. Bitácora de versiones / decisiones

| Fecha | Versión | Cambio | Resultado | Pendiente |
| --- | --- | --- | --- | --- |
| 20-11-2026 | 0.8.1 | Arreglo de bucle de login por roles | Pruebas HTTP | Revisión visual en Windows |
| 20-11-2026 | 0.8.2 | Renovación segura de CSRF | Pruebas Python y JS | Comprobar sesión real en navegador |
| 20-11-2026 | 0.8.3 | Botones Waze/Maps en carreras aceptadas | Pruebas API y enlaces | Falló lista con dependencia faltante |
| 20-11-2026 | 0.8.4 | Navegación autocontenida, recuperación de lista, ruta y guardias de entrega | 41 pruebas HTTP superadas directamente; verificador JS aprobado; prueba manual pendiente | Revisión visual y Android físico |
| 20-11-2026 | v0.9 | Código Android nativo de conductor con GPS foreground y plan de migración web/Netlify; no hay APK compilada | Guardias de fuente (4/4), validador rápido JS y pruebas HTTP por módulos; validador completo se bloqueó en este entorno | Compilación en Android Studio, API HTTPS, pruebas móviles y Netlify |
| 20-11-2026 | v0.10 | Cloud staging separado: FastAPI + esquema PostgreSQL, sesiones persistentes, CSRF, carrera completa, web Netlify estática, Android URL compatible, validador cloud y documentación | 17 pruebas cloud y sintaxis JS aprobadas; puerta completa legado aprobada; v0.9 conservada; sin Postgres real/Netlify/APK | Paridad QR/mensajería/fotos, autenticación y controles de producción, despliegue y GPS de campo |

**Restricción:** la central administra las carreras, el pasajero solo consulta su servicio, y el conductor no recibe teléfonos privados de clientes ni acceso al resto de la flota. Ninguna mejora puede romper esta regla.

| 20-11-2026 | v0.10.1 | Reparación instalación Windows `greenlet`: detección Python x64, venv independiente, pip actualizado, instalación solo binarios, diagnóstico y prueba DEP-101 | Pendiente validación real en Windows, pruebas locales del instalador | PostgreSQL, Netlify y APK siguen sin publicar/compilar |

## Corrección 0.10.2 — ORIGIN-102

- Archivos cambiados: `cloud/app.py`, `tests_cloud/test_login_origin_v102.py`, `docs/INCIDENTES_Y_SOLUCIONES.md`, `RUTA_DE_TRABAJO.md`, `README.md` y `AGENTS.md`.
- Solución: aceptar solamente los orígenes locales exactos del servidor de staging en puerto 8770; sin relajar producción ni CSRF.
- Validación: ejecutar tests de la API, regresiones previas e inspección de configuración; probar luego desde Chrome/Edge de Windows.
- Actualización: detener servidor, respaldar carpeta completa, aplicar parche de código conservando `_runtime_staging/` y `runtime/`; reiniciar y recargar.

### Validación ejecutada del hotfix ORIGIN-102

- `python -m unittest tests_cloud.test_login_origin_v102 -v`: **5/5 aprobadas**.
- `python scripts/validar_cloud.py`: **22 pruebas cloud y 4 del instalador aprobadas**, JS de staging válido.
- `python scripts/validar_entrega.py --quick`: **aprobado**, JS y regresiones antiguas.
- `python -m unittest discover -s tests -v`: **49 aprobadas**.
- Servidor Uvicorn real en puerto 8770: `POST /api/login` con `Origin: http://127.0.0.1:8770` devolvió 200, `/api/me` confirmó sesión y otro origen devolvió 403.
- Pendiente en equipo de usuario: prueba manual Chrome/Edge y credenciales reales de su staging. Sin pruebas con PostgreSQL en línea ni Android físico.

## GitHub y estado v0.10.3 — 20-11-2026

- Repositorio de código: https://github.com/rrene7/metrotaxi (rama `main`).
- Se subieron **97 archivos fuente** sin `runtime/`, `_runtime_staging/`, bases de datos ni secretos.
- UI cloud de pruebas: mapa para recogida/destino, puntos de taxi con GPS reciente, recorrido visual/demostración, perfil de conductor, QR y estadísticas/mensajería en recuperación. **No se considera paridad total con la v0.9**.
- Verificaciones locales antes de importar: `python scripts/validar_cloud.py` y `python scripts/validar_entrega.py --quick` aprobadas. Pruebas reales de mapa, PostgreSQL, Android y operación en carretera pendientes.
- En la rama `main`, GitHub Actions ejecuta tests Python/JS y una compilación Android debug **sin distribuir APK**. Revisar los resultados antes de una nueva entrega.
- El repositorio es **público**: prohibido subir credenciales, teléfonos/ubicaciones reales o los directorios de datos.

## Continuación GitHub — ANDROID-BUILD-103 / MAP-104 (20-11-2026)

- Corregido el import Java que bloqueaba la compilación Android y añadida guardia de regresión. La compilación Android en GitHub Actions sigue siendo puerta de calidad.
- En la web staging el refresco GPS no borra el recorrido; se limpia al cambiar de carrera y al perder puntos válidos.
- Prueba añadida: `tests_cloud/test_map_route_persistence.cjs`, invocada automáticamente por `scripts/validar_cloud.py`.
- Pendiente: prueba real Android y navegador, proveedor de mapas/rutas para producción, PostgreSQL y Netlify HTTPS. No se ha distribuido un APK de uso comercial.

## GPS-105 — seguimiento de carrera en web staging (20-11-2026)
- Pasajero: la polilínea se actualiza cada vez que recibe GPS reciente del conductor confirmado; recogida antes de iniciar y destino durante la carrera.
- Las actualizaciones no recentran el mapa; vista de ruta por calles solo bajo petición explícita y no se recalcula en cada consulta.
- Sin GPS reciente, solo se muestra trayecto de referencia recogida–destino, identificado como tal; nunca se finge posición del taxi.
- Conductor: el trazado durante carrera activa apunta a destino desde GPS actual cuando está disponible.
- Prueba nueva `tests_cloud/test_tracking_segment.cjs`, ejecutada por `scripts/validar_cloud.py`.
- Pendientes: prueba en dos teléfonos, rutas por calles con proveedor de producción, PostgreSQL/HTTPS y monitoreo GPS; este cambio NO despliega backend público.


## PILOT-106 — Despliegue restringido, preparación 20-11-2026

- Infraestructura versionada: Dockerfile Python 3.12 sin root, `railway.toml`, app `cloud.pilot` que sirve la web junto a API HTTPS, conexión PostgreSQL privada, sin Netlify obligatorio.
- Seguridad extra: acceso previo HTTP Basic con clave aleatoria administrada por dueño, host/origen HTTPS explícitos, nunca SQLite ni credenciales de prueba. No sustituye seguridad de producción.
- Inicialización de esquema exclusivamente en BD vacía y por opción explícita. No hay migración automática de instalaciones anteriores.
- Manejo CLI interactivo para crear administrador, operador y conductor sin contraseñas en archivos.
- Mapas vía `/map-config.js` con plantilla raster HTTPS del proveedor; OSM público solo por habilitación explícita durante piloto mínimo.
- Pruebas: `tests_cloud/test_railway_pilot.py`, `test_manage_pilot.py`, `test_postgres_pilot.py` (PostgreSQL real efímero de CI); **no incluye prueba en proveedor Railway real**.
- Para habilitar el piloto hacen falta credenciales/acciones del usuario en Railway, dominio generado y variables secretas. Mantener la demostración pública ficticia de GitHub Pages separada.
- Pendiente producción: OTP, freno antiabuso, auditoría, política de datos, migraciones, mapas/rutas de pago y GPS Android físico.

- Railway healthcheck: permitir exclusivamente el host técnico `healthcheck.railway.app` además del dominio real; el guardia de configuración impide omitirlo dentro de Railway.

## PRIV-106 / ARRIVAL-107 (20-11-2026)
- Pasajero: pestañas para carrera activa, historial y mensajes; solo los estados comprensibles al cliente; ofertas de despacho y unidad no confirmada se ocultan también en API.
- Conductor: botón Iniciar/Finalizar deshabilitado si no hay GPS reciente y suficientemente preciso cerca de recogida/destino; seguridad aplicada **también en el servidor**.
- Mapa: taxi con icono 🚕 en vez de punto; llamadas GPS y recorrido siguen sin depender de las baldosas.
- No trasladar estos cambios a producción sin prueba física GPS, protección frente a GPS falsificado, UX para solicitudes sin coordenadas y proveedor autorizado de mapas.

## POINT-108 — Coordinadas verificadas por la central (20-11-2026)

- Problema: una carrera por llamada/WhatsApp sin latitud-longitud quedaba bloqueada por ARRIVAL-107; no se permite saltarse la geocerca para iniciar/finalizar.
- Implementado: la central puede abrir «Marcar recogida/destino», seleccionar manualmente un punto del mapa o escribir coordenadas que el pasajero proporcionó explícitamente y confirmar la verificación. **Nunca** geocodificar ni inventar coordenadas desde texto sin confirmación.
- API: `POST /api/trips/point`, rol admin/operador, CSRF, verificación de Origin, coordenadas y confirmación, auditoría de actor y método; `expected_lat/expected_lng` protege contra ediciones simultáneas.
- Recogida solo puede cambiarse en `pending/offered/accepted`; destino hasta `inprogress`; ambas coordenadas quedan inmutables tras `done/cancelled`.
- La actualización llega al pasajero y conductor mediante el sondeo existente (sin notificación push). Un punto validado por central NO es GPS del conductor; el conductor sigue necesitando posición de dispositivo precisa y reciente para las acciones de llegada.
- Pruebas agregadas: ciclo completo de carrera por llamada sin GPS, CSRF, autorización, auditoría, entradas inválidas, conflictos y cambios tras cierre. Revisar el workflow de GitHub antes de fusionar.
- Pendiente: ensayo visual local y en teléfono, política de cambios informados al pasajero cuando se actualizan puntos, HTTPS PostgreSQL real, validación de GPS frente a falsificación, proveedor cartográfico comercial.


## DEPLOY-109 — Puerta de publicación segura en Railway (20-11-2026)

- La cuenta Railway del titular no está conectada a ChatGPT: ningún dominio HTTPS operativo ni PostgreSQL alojado se ha creado o verificado mediante esta interacción. No llamar "publicado" a un piloto que solo tiene código en GitHub.
- Se añade `cloud/pilot_probe.py` y `scripts/verificar_piloto_https.py`: comprobación **sin secretos** de certificado HTTPS, /api/health con PostgreSQL listo y acceso HTTP Basic a páginas/API privadas; no realiza mutaciones ni sigue redirecciones.
- Workflow manual de Actions `Metro Taxi - Comprobar piloto HTTPS` recibe solo una URL, nunca credenciales. Probarlo **después** de activar dominio y la base desde Railway.
- CLI `cloud.manage --init-schema` ahora se niega a operar sobre cualquier base con tablas, aunque esté parcialmente inicializada. Registrar migraciones futuras por separado con respaldo y revisión.
- Tests automáticos `tests_cloud/test_pilot_deploy_readiness.py`; mantener validaciones de los flujos, roles, CSRF y PostgreSQL temporal.
- Sigue pendiente: autorización del propietario para crear Railway, conectar repositorio, variables privadas/hostname, bootstrap, cuentas ficticias, pruebas reales en teléfonos y entorno con mapas/rutas autorizados.


## DEPLOY-110 — Render Free + Aiven PostgreSQL Free + Netlify (20-11-2026)

- Se añade `render.yaml` sin credenciales, con web Docker Free y variables privadas solicitadas en el panel Render. No se crea PostgreSQL de Render; la base externa prevista es Aiven.
- Se agrega `docs/RENDER_AIVEN_NETLIFY.md` con TLS, límites de suspensión Free, inicialización de esquema vacío, despliegue Netlify con proxy HTTPS y validaciones de cookies/CSRF/Origin.
- Regresión `tests_cloud/test_render_blueprint.py` garantiza que el Blueprint conserve `plan: free` y no incluya secretos o bases de pago.
- **Acceso externo:** la integración Render todavía figura sin conexión activa cuando se consulta desde ChatGPT; no hay dominio Render, base Aiven ni web Netlify verificados. Nunca afirmar que se desplegó por subir el YAML a GitHub.
- Limitación funcional importante: los planes gratuitos pueden suspenderse; además Render Free puede no ofrecer terminal interactiva para crear la primera cuenta de administrador. No introducir cuentas semilla públicas o credenciales estáticas por solucionar ese problema.

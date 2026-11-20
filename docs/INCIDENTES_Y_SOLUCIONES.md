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

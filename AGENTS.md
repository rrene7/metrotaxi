# Instrucciones de trabajo para Codex, agentes de programación y colaboradores

**Lectura obligatoria antes de tocar este repositorio (en este orden):**

1. `RUTA_DE_TRABAJO.md` — avance, prioridades, dependencias, bitácora y lista de errores que no se deben repetir.
2. `docs/INCIDENTES_Y_SOLUCIONES.md` — historia de fallos y regresiones.
3. `docs/CONTRATO_OPERATIVO.md` — permisos de central, cliente y conductor.
4. `docs/PRUEBAS_DE_ACEPTACION.md` — escenario completo en navegadores y móviles.

## Política de cambios

- Trabaja a partir de la última versión validada; no reconstruyas interfaces ajenas a la tarea.
- Añade primero una prueba que falle con el problema, luego corrige la causa, no ocultes el error.
- Nunca sacrifiques autenticación, autorización, CSRF, validaciones GPS ni privacidad por hacer funcionar una pantalla.
- La lista de servicios del conductor no puede depender de MapLibre/Leaflet, Waze, bibliotecas opcionales ni recursos externos.
- Para las operaciones externas, implementa errores visibles y reintentos explícitos; evita un indicador de carga infinito.
- Las pantallas deben funcionar cuando el mapa falle; las rutas de navegación solo deben generarse con coordenadas reales explícitas.
- Antes de agregar un `<script src>` o `<link href>`, revisa que el archivo exista y que `server.py` autorice servirlo.
- Protege la carpeta `runtime/`, `.env`, contraseñas y fotos. No subas datos ni credenciales a GitHub. No copiar bases activas.
- Antes de entregar ejecuta **`scripts/validar_entrega.bat` (Windows), o bien `python scripts/validar_entrega.py --quick` y después `python -m unittest discover -s tests -v`** y actualiza la bitácora de `RUTA_DE_TRABAJO.md`.
- Si no pudiste hacer pruebas manuales en navegador/teléfono, repórtalas como pendientes, nunca como superadas.
- Existe proyecto fuente Android (`android-conductor/`) desde v0.9, pero NO APK compilada/validada. Antes de editarlo revisar permisos FGS, cookie/CSRF, seguridad WebView, y ejecutar las pruebas Android de CI. Publicación real, HTTPS y GPS de campo siguen pendientes.
- **v0.10 nube:** antes de modificar `cloud/` o `web-staging/`, revisar también `docs/PLAN_PUBLICACION_V10.md` y el contrato de roles. No reutilizar cuentas/sesiones o base de `runtime/` en la API nueva.
- Ejecutar obligatoriamente `python scripts/validar_cloud.py` además de las pruebas locales. El servidor cloud exige PostgreSQL fuera de tests; **no desplegar SQLite temporal ni permitir `test_mode=True` externamente**.
- Las nuevas pantallas de staging no sustituyen la v0.9. QR, fotografía, mensajería y estadísticas antiguas deben migrarse y probarse antes de anunciar compatibilidad.
- Probar que la central nunca se quede cargando sin error visible, que los conductores no obtengan teléfonos privados y que Netlify no se distribuya con un proxy de ejemplo. El generador exige una URL HTTPS real.

## Forma de entrega

Resume el problema, causa, archivos tocados, pruebas ejecutadas y sus resultados, riesgos y actualización paso a paso conservando `runtime/`.

## Regla DEP-101 (Windows)
- Revisar siempre `iniciar_staging_windows.bat` y `docs/INCIDENTES_Y_SOLUCIONES.md` antes de cambiar requisitos del backend cloud.
- No introducir `py -3` sin verificar la version: en la maquina del usuario escogia Python 3.9 y fallaba al compilar `greenlet`.
- El instalador debe seleccionar Python 3.11/3.12/3.13 64-bit, crear un venv aislado y preferir ruedas binarias (`--only-binary=:all:`).
- Ejecutar `python -m unittest tests.test_windows_staging_launcher_v101 -v` y las pruebas cloud antes de publicar.

## Regla ORIGIN-102 (staging navegador)
- Probar `POST /api/login` con encabezado `Origin: http://127.0.0.1:8770`, no solo requests de TestClient que omiten Origin.
- Distinguir HTTP 403 de Origin del 401 por contraseña incorrecta y del CSRF inválido en operaciones autenticadas.
- Solo permitir loopback con puerto explícito cuando `test_mode=True`, nunca en la API de producción.
- Ejecutar `python -m unittest tests_cloud.test_login_origin_v102 -v` antes de toda nueva entrega.

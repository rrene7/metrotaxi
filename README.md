# Metro Taxi v0.10.1 — Instalador Windows corregido (NO PRODUCCIÓN)

## Corrección v0.10.1 — instalación Windows / `greenlet`

**Incidente DEP-101 (20-11-2026):** `iniciar_staging_windows.bat` usaba `py -3`; en equipos con Python 3.9 se ejecutaba esa versión, incompatible con la versión requerida por el proyecto, y `pip` trataba de compilar `greenlet` con Microsoft Visual C++.

**Solución:** el instalador ahora detecta Python **3.12, 3.11 o 3.13 (64 bits)**, crea un entorno virtual `.venv-staging-312` (u otra versión compatible), actualiza su propio `pip` e instala **solo paquetes binarios**. No modifica Python 3.9 ni los entornos de otros proyectos. No instala compiladores ni borra `runtime` o `_runtime_staging`.

**Si el equipo solo tiene Python 3.9:** instala Python 3.12 de 64 bits desde https://www.python.org/downloads/windows/; abre una nueva consola y comprueba `py -0p`. Luego ejecuta `iniciar_staging_windows.bat` otra vez. Para diagnósticos adicionales ejecuta `diagnosticar_python_windows.bat`.

**Importante:** no usar `rem Usa iniciar_staging_windows.bat para instalar en el entorno virtual compatible` en este proyecto, porque puede elegir Python 3.9. Ejecuta el BAT o activa el entorno virtual seleccionado. Las pruebas cloud siguen siendo staging y no producción.

**Estado:** se conserva íntegra la **v0.9 local** (server.py/SQLite, central, QR y demás funciones). A su lado se añadió la **v0.10 cloud staging**, con FastAPI, esquema PostgreSQL, sesiones persistidas en BD y web estática preparada para Netlify. **La API cloud NO tiene aún paridad de funciones con la v0.9.** No está publicada ni hay APK compilada.

## ¿Qué puedes probar ya sin cuentas externas?

En Windows:

1. Descomprime esta nueva versión en una carpeta **diferente** de la anterior.
2. Ejecuta `iniciar_staging_windows.bat` (requiere Python 3.11/3.12/3.13 de 64 bits; recomienda 3.12; el instalador crea su propio entorno virtual).
3. Abre **http://127.0.0.1:8770/** en el mismo equipo.
4. Busca las contraseñas aleatorias en `_runtime_staging/credenciales_cloud_demo.txt`. Se crean solo en tu PC; no las subas a GitHub.
5. En `/cliente.html` registra un cliente ficticio, solicita un taxi para Pacora. En una ventana privada entra por `/ingresar.html` como `admin`, observa el servicio, y abre otra ventana privada para `conductor1` en `/conductor.html` (el conductor debe pulsar *Estoy disponible* antes de que la central lo asigne). Acepta, inicia y finaliza. Prueba Waze con coordenadas GPS reales del navegador solo si autorizas el permiso.

Esta prueba guarda los datos en `_runtime_staging/staging.sqlite3`, **no** en el `runtime/` de v0.9 y **no** en un servidor público. Usa datos inventados. Solo el servidor local de pruebas permite SQLite: el backend de nube real exige PostgreSQL.

Para seguir usando el **prototipo anterior** sin migrar datos ni perder QR/mensajería: ejecuta `iniciar_windows.bat` y entra a **http://127.0.0.1:8765/**. No mezcles ambos servidores ni bases de datos.

## ¿Qué se implementó en la nueva API cloud?

- Identidad con usuario/contraseña y contraseñas derivadas con PBKDF2, sesión de servidor en base de datos, cookie HttpOnly, CSRF y comprobación de origen.
- Registro e inicio de sesión del pasajero **sin verificación telefónica todavía**.
- Solicitudes con GPS autorizado o referencia; dos sedes; carreras manuales desde central; ofrecimiento con comprobación transaccional de unidad y carrera.
- Conductor: estado disponible/desconectado, aceptar/rechazar/iniciar/finalizar, GPS enviado explícitamente, navegación Waze/Maps, sin acceso al teléfono privado del pasajero.
- Pasajero: solo sus solicitudes y, tras la aceptación, ficha del taxista y GPS recibido recientemente (caducidad 120 segundos).
- Cancelaciones autorizadas, auditoría y devolución a pendientes de ofertas caducadas cuando hay consultas API.
- Web de **staging** separada en `web-staging/`; constructor `scripts/preparar_netlify.py` que genera reglas `/api/*` solo al recibir un URL HTTPS real.

**Aún NO migrados a cloud:** QR por conductor, foto del conductor, mensajería, incidentes, tarifas/reportes completos, verificación y recuperación del teléfono, estadísticas avanzadas, GPS en segundo plano validado, notificaciones push y cola automática persistente. Estos módulos continúan en la v0.9 local donde ya existían.

## Validar cambios

```powershell
# Instala con iniciar_staging_windows.bat; luego prueba con el Python del entorno virtual
".venv-staging-312\Scripts\python.exe" scripts\validar_cloud.py
".venv-staging-312\Scripts\python.exe" scripts\validar_entrega.py --quick
```

Para todas las pruebas anteriores de `server.py`: `.venv-staging-312\Scripts\python.exe scripts\validar_entrega.py --full` (ajusta `312` a `311` o `313` si seleccionaste otra versión). Si falla una prueba, **no publicar**. La validación cloud usa SQLite aislado *solo para pruebas*; **PostgreSQL real todavía no fue probado aquí**.

## Publicación: requiere tu infraestructura

1. Provisionar una **base PostgreSQL nueva y vacía** con TLS, respaldos y control de accesos.
2. Provisionar hosting de API HTTPS con dominio propio. Variables privadas: `DATABASE_URL`, `METRO_ALLOWED_ORIGINS` y `METRO_ALLOWED_HOSTS`. Ver `cloud/config.example.env`. No subir claves al repositorio.
3. Crear estructura explícitamente con `python -m cloud.manage --init-schema` desde un entorno de administración seguro. Dar de alta administrador con `python -m cloud.manage --create-admin` (contraseña ingresada en consola).
4. Probar `/api/health`, sesiones, cookies, CSRF y roles con PostgreSQL en un entorno aislado **antes de exponerlo públicamente**.
5. Preparar sitio Netlify: `python scripts/preparar_netlify.py --api-url https://api.TUDOMINIO.COM --output netlify-dist`. Subir **solo** la carpeta generada. No publicarla hasta cerrar la auditoría de seguridad y pruebas de aceptación. Netlify actúa como proxy mismo origen para `/api/*` (ver documentación de Netlify).
6. Compilar Android en Android Studio con `-PmetroBaseUrl=https://app.TUDOMINIO.COM` para que abra `/ingresar.html` y use las APIs a través del proxy. **No se incluye APK**. Validar permisos y GPS en teléfonos reales.

Ver `docs/PLAN_PUBLICACION_V10.md` y `RUTA_DE_TRABAJO.md` para bloqueos, medidas de seguridad y próximos pasos.

## Advertencias

No copiar automáticamente los datos de `runtime`/SQLite a PostgreSQL. Falta un procedimiento de migración validado con mapeo de clientes/roles, consentimientos, fotos y respaldo. No usar nombres, números ni ubicaciones reales en el staging. Ninguna versión es apta aún para operación comercial. La app no garantiza seguimiento GPS continuo ni tiempos de llegada.

## Hotfix v0.10.2 — Pantalla de ingreso devuelve 403 (ORIGIN-102)

La v0.10.1 puede rechazar el origen que envía el navegador al iniciar sesión desde
`http://127.0.0.1:8770`, aunque la API responda 200 a `/api/me`.
Esta versión corrige **exclusivamente el modo de prueba local**: acepta Origin exacto
`http://127.0.0.1:8770` o `http://localhost:8770` en `test_mode`. La política
HTTPS/Origin del backend de producción no cambia, y CSRF continúa obligatorio.

**Actualizar Windows sin perder datos:** detener `iniciar_staging_windows.bat`
con Ctrl+C, respaldar la carpeta de Metro Taxi, y copiar el parche sobre el proyecto
(conservar sin sobrescribir `_runtime_staging/`, `runtime/` y archivos `.env`).
Reabrir `iniciar_staging_windows.bat`, visitar `http://127.0.0.1:8770/ingresar.html`
y entrar con las claves de `_runtime_staging/credenciales_cloud_demo.txt`.
El archivo de claves se genera solamente al inicializar staging por primera vez.
Si se pierde, NO borrar la base para recuperarlo.

**Prueba nueva:** `python -m unittest tests_cloud.test_login_origin_v102 -v`.
La prueba de navegador en Windows queda pendiente hasta ejecutarla en el dispositivo real.

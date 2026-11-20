# METRO TAXI — Código fuente

Sistema privado de despacho de taxis de Metro Taxi para Pacora y 24 de Diciembre (Panamá).

**Estado: desarrollo / staging. NO apto aún para operar con pasajeros reales.**

## Componentes del repositorio

- **Piloto local** (`server.py`, `static/`, páginas de raíz): desarrollo Python/SQLite con gestión de carreras, dos sedes, afiliación QR, perfiles, reglas de despacho y controles de privacidad.
- **Nueva API** (`cloud/`): FastAPI, sesiones de servidor, CSRF y esquema compatible con PostgreSQL. Usa SQLite solo en la prueba local aislada.
- **Web de staging** (`web-staging/`): interfaz de central, cliente y conductor, con mapa, navegación y módulos en recuperación. Es un entorno separado del piloto local; todavía no tiene paridad completa.
- **Android** (`android-conductor/`): código fuente para Android Studio; **APK todavía sin validar ni distribuir**.
- **Ruta de calidad** (`RUTA_DE_TRABAJO.md`, `AGENTS.md`, `docs/`, `tests/`, `tests_cloud/`): reglas, incidentes y pruebas de regresión.

## Pruebas locales en Windows

Se recomienda **Python 3.12 x64**. No usar Python 3.9.

1. Clonar el repositorio: `git clone https://github.com/rrene7/metrotaxi.git`
2. Ejecutar `iniciar_staging_windows.bat` para levantar la API en `http://127.0.0.1:8770/`. El instalador crea un entorno virtual y credenciales ficticias guardadas **solo en tu PC** en `_runtime_staging/credenciales_cloud_demo.txt`.
3. Para conservar el piloto anterior de manera independiente, usar `iniciar_windows.bat`, en `http://127.0.0.1:8765/`.

**Nunca** copiar bases de datos de una instalación anterior sin respaldo y plan de migración validado.

## Comprobaciones antes de modificar o publicar

Leer primero `AGENTS.md`, `RUTA_DE_TRABAJO.md`, `docs/CONTRATO_OPERATIVO.md` y `docs/INCIDENTES_Y_SOLUCIONES.md`.

```powershell
python scripts/validar_entrega.py --quick
python -m unittest discover -s tests -v
python scripts/validar_cloud.py
```

La web usa una biblioteca de mapas externa para el piloto; el proveedor, su disponibilidad, atribución y condiciones comerciales deben comprobarse antes de publicarla. Ninguna dirección escrita se debe convertir en coordenadas inventadas.

## Publicación

Netlify aloja las interfaces; el backend y PostgreSQL necesitan un servicio HTTPS aparte. **No publicar el backend Python/SQLite de demostración.** Las variables privadas se configuran fuera del repositorio. El GPS Android en segundo plano requiere pruebas físicas y revisión de permisos.

Revisa `docs/PLAN_SALIDA_A_PRODUCCION.md` y `docs/PLAN_PUBLICACION_V10.md`.

**Principio funcional:** Metro Taxi controla todas las solicitudes; el conductor solo ve sus carreras y el pasajero solo sus servicios. No publicar la flota completa ni teléfonos privados de clientes.


## Piloto online restringido (Railway + PostgreSQL)

El código incluye `Dockerfile`, `railway.toml` y `cloud/pilot.py` para ejecutar web + API en **un mismo origen HTTPS**, con PostgreSQL privado y **contraseña de acceso previa**. Se añaden herramientas de inicialización de una base completamente vacía y cuentas de personal creadas de forma interactiva. **No implica que esté desplegado.** Lee `docs/PILOTO_RAILWAY.md` antes de habilitar una URL pública. No migrar datos del prototipo ni usar contraseñas de ejemplo. El despliegue comercial sigue bloqueado por antiabuso, verificación de teléfono, proveedor de mapas, copias/restauración y pruebas móviles.


## Comprobar un dominio de Railway (solo después de activarlo)

El despliegue restringido se configura en la cuenta del propietario siguiendo `docs/PILOTO_RAILWAY.md`. **GitHub Actions no crea recursos en Railway ni guarda contraseñas.** Una vez desplegados el servidor y PostgreSQL privados, comprueba la URL HTTPS desde la raíz del repositorio:

```powershell
py -3.12 -m scripts.verificar_piloto_https --url https://TU-DOMINIO-REAL.up.railway.app
```

También está disponible el workflow manual `Actions → Metro Taxi - Comprobar piloto HTTPS`. Introduce solo la URL; comprueba conexión a la base y las barreras privadas, sin iniciar sesión ni alterar carreras. Si no existe un dominio Railway **real**, esta comprobación no puede ejecutarse. Para activar la nube, autoriza la conexión de Railway a tu GitHub; la integración ChatGPT Railway debe conectarse de forma independiente si quieres operarla directamente desde aquí.

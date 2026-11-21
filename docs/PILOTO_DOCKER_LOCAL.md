# Metro Taxi — piloto local con Docker y PostgreSQL (LOCAL-118)

**Solo en tu PC Windows con Docker Desktop.** Esta instalación no publica taxis reales ni expone bases a Internet. Usa cuentas ficticias, conserva datos entre reinicios y se mantiene aislada de `runtime/`, `_runtime_staging/`, Netlify y del espacio institucional Render.

## Requisitos

- Docker Desktop iniciado con contenedores Linux.
- Windows PowerShell y Python 3.11–3.13 solo para generar la clave local. No requiere instalar PostgreSQL ni paquetes Python en Windows.
- Puerto **127.0.0.1:8770** libre. Detén antes `iniciar_staging_windows.bat` si utiliza el mismo puerto.
- Trabajar desde la carpeta de `rrene7/metrotaxi` descargada del último `main`.

## Primer arranque: solo base nueva

En PowerShell, desde la raíz del repositorio, genera la contraseña local privada (no pegues la clave en chats):

```powershell
py -3.12 -c "import secrets; from pathlib import Path; Path('metro-local.env').write_text('METRO_LOCAL_DB_PASSWORD='+secrets.token_hex(24)+'\n',encoding='utf-8')"
```

Si no tienes Python 3.12, usa `py -3.11` o `py -3.13`. El archivo `metro-local.env` queda excluido de Git y de la construcción Docker; **conserva una copia privada**. Si ya existe, NO vuelvas a generarlo ni cambies su clave: PostgreSQL persistente seguirá usando la clave anterior.

En la misma terminal ejecuta, en orden:

```powershell
docker compose --env-file metro-local.env -f compose.local.yaml build app
docker compose --env-file metro-local.env -f compose.local.yaml up -d db
docker compose --env-file metro-local.env -f compose.local.yaml run --rm app python -m cloud.manage --init-schema
docker compose --env-file metro-local.env -f compose.local.yaml run --rm app python -m cloud.manage --create-admin
docker compose --env-file metro-local.env -f compose.local.yaml run --rm app python -m cloud.manage --create-operator
docker compose --env-file metro-local.env -f compose.local.yaml run --rm app python -m cloud.manage --create-driver
docker compose --env-file metro-local.env -f compose.local.yaml up -d app
```

Las cuentas se crean **interactivamente** con contraseñas no almacenadas en archivos de ejemplo. El conductor pide nombre, unidad, sede Pacora o 24 de Diciembre y su acceso. Para añadir un segundo conductor repite `--create-driver` con una nueva unidad.

**Importante:** `--init-schema` se ejecuta **una sola vez** y solo si PostgreSQL está vacío. Si recibes «Base no vacía» detente: **no borres volúmenes ni bases**; revisa con respaldo y migración. La aplicación no inicializa ni modifica automáticamente el esquema.

## Acceso y pruebas

Abre **http://127.0.0.1:8770/ingresar.html** para central/conductor o **http://127.0.0.1:8770/cliente.html** para crear un pasajero ficticio. Usa tres perfiles de navegador separados para evitar mezclar cookies. Salud de la API: **http://127.0.0.1:8770/api/health** (debe mostrar `database: ready`).

El recorrido de prueba es pasajero crea carrera → central asigna → conductor acepta → GPS de dispositivo reciente y cerca de recogida habilita iniciar → GPS cerca del destino habilita finalizar → historial. **No simules falsamente GPS real para realizar servicios.** En una prueba de escritorio podrás verificar bloqueos de geocerca, pero no demostrar llegada física salvo desplazamiento autorizado y HTTPS en un teléfono.

El mapa puede quedar sin tiles: es una función opcional y no debe bloquear las operaciones.

## Parar, reiniciar y solucionar problemas

```powershell
docker compose --env-file metro-local.env -f compose.local.yaml ps
docker compose --env-file metro-local.env -f compose.local.yaml logs --tail=100 app
docker compose --env-file metro-local.env -f compose.local.yaml stop
docker compose --env-file metro-local.env -f compose.local.yaml start
```

**Nunca** uses comandos que eliminen volúmenes, ni `docker volume prune`, ni `docker compose down` con opción de volúmenes. Los datos quedan en el volumen `metro_local_pgdata`; el archivo `metro-local.env` conserva su contraseña.

## Barreras de seguridad

- La API se publica **únicamente en 127.0.0.1**, no en `0.0.0.0` ni en la red local.
- PostgreSQL no publica `5432`, solo usa la red interna de Docker.
- Esta entrada utiliza `test_mode=True` exclusivamente en este proceso local aislado para permitir cookies HTTP de loopback. **Prohibido** usar `cloud.local_docker:app` en Render, Railway, Netlify, VPS o equipos accesibles desde la LAN.
- No abrir puertos en router, firewall o Docker para este piloto. Para ensayos desde teléfonos se necesita posteriormente HTTPS con `cloud.pilot:app`, control de acceso y PostgreSQL privado.
- No subir archivos de contraseñas, bases, capturas con teléfonos ni datos reales.
- El prototipo v0.9 y su directorio `runtime/` permanecen intactos.

**Estado:** archivos preparados en GitHub; no se ha ejecutado Docker Desktop en la PC del propietario ni confirmado una sesión visual. Ver `docs/PRUEBAS_DE_ACEPTACION.md` para las comprobaciones pendientes.

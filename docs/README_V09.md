# Metro Taxi v0.9 — Fuente de APK Android y plan de publicación (NO producción)

**Novedad:** carpeta `android-conductor/` con proyecto Android Studio Java, interfaz del conductor en WebView restringido a origen HTTPS y GPS nativo con servicio de ubicación de primer plano, botón para iniciar/detener y notificación permanente. **No se ha compilado ni firmado ninguna APK**, porque aquí no hay Android SDK/Gradle. No conectar este código al servidor Python/SQLite de pruebas mediante Internet.

La v0.8.4 del backend sigue funcionando localmente sin cambios de API ni de base de datos. **No borrar ni sobrescribir `runtime/`.**

1. Para probar el servidor Windows: `iniciar_windows.bat` → `http://127.0.0.1:8765/ingresar`.
2. Para continuar con Android: `android-conductor/README.md` y `docs/PLAN_PUBLICACION_V09.md`.
3. Para validación de código sin Android SDK: `python scripts/validar_entrega.py --quick` + `python -m unittest discover -s tests -v`.
4. Para probar la compilación nativa: abrir `android-conductor/` en Android Studio, configurar URL HTTPS válida y compilar **debug**. Sin API desplegada la app no tendrá una sesión funcional.

## Pendientes antes de operación comercial

API estable PostgreSQL/HTTPS, hosting, Netlify, control de sesiones de producción, GPS en teléfonos con pantalla bloqueada, pruebas de WebView/cookies y CSRF, firma, notificaciones, verificación telefónica, auditoría y respaldo restaurado.

---

# Metro Taxi v0.8.4 — Corrección de «Servicios ... Cargando»

**Problema observado:** la información de la unidad aparecía, pero «Servicios que me ofreció Metro Taxi» permanecía en «Cargando…» después de agregar la navegación Waze. La versión 0.8.3 llamaba a `window.MTNavigation.navLinks(t)` al dibujar cada carrera; si `navigation.js` no se cargaba (por ejemplo, durante una actualización parcial), esa llamada lanzaba un error JavaScript. La excepción solo aparecía brevemente como aviso y no sustituía el texto «Cargando…».

**Solución v0.8.4:** la pantalla del conductor ahora genera por sí misma los enlaces Waze y Google Maps, utilizando únicamente coordenadas existentes en la carrera aceptada o en progreso. La lista de servicios ya no depende de `navigation.js`. Si ocurre otro error, muestra el motivo y un botón **Reintentar** en vez de dejar el indicador de carga. No se modificaron permisos, usuarios ni datos de carreras.

## Parche rápido recomendado para el problema mostrado

1. Detén Metro Taxi en la ventana de Python con **Ctrl+C**.
2. Haz copia de seguridad de la carpeta de instalación actual, incluyendo `runtime`. **No la elimines ni la sobrescribas**.
3. Dentro del ZIP de parche copia **`static/driver.js`** a la carpeta `static` de tu instalación reemplazando ese archivo. Opcionalmente, copia `conductor.html` para eliminar la referencia antigua a `navigation.js`.
4. Ejecuta `iniciar_windows.bat` de tu carpeta habitual (no inicies simultáneamente dos copias del servidor).
5. Abre **http://127.0.0.1:8765/conductor** y pulsa **Ctrl+F5** para actualizar el JavaScript.
6. Busca tu carrera aceptada (por ejemplo, MT-3). Si tiene `pickup_lat` y `pickup_lng`, verás **Navegar a recogida con Waze** y **Google Maps**. Si solo contiene una dirección escrita, verás un aviso para solicitar coordenadas: nunca se inventa el punto.

La actualización **no necesita copiar ni reemplazar** `server.py` ni `runtime`, ni recrear las cuentas. Compatible con las versiones 0.8.2 y 0.8.3 de la misma línea de desarrollo que usan `/api/mine`.

## Validación

- `py -3 -m unittest discover -s tests -q` — pruebas HTTP y de permisos del proyecto.
- `node tests/test_driver_loading_v084.cjs` — prueba de interfaz sin cargar `navigation.js`, con coordenadas ausentes y con fallo de servidor.
- `node tests/test_navigation_v083.cjs` — comprobación de URL Waze/Maps del módulo anterior, conservado como referencia.

No se ha podido ejecutar un navegador Chromium completo por una restricción del entorno. Debes comprobar el resultado visual en Chrome/Edge local. **Este servidor sigue siendo un piloto local, no apto para publicación pública ni servicios reales.**

---

# Metro Taxi v0.8.3 — Navegar a la recogida con Waze y Google Maps

Actualización de v0.8.2. Conserva las funciones anteriores: central, QR, pasajeros, turnos, GPS y despacho.

## Novedad

El conductor ve **Navegar a recogida con Waze** y **Google Maps** al aceptar una carrera que tenga coordenadas de recogida explícitas (GPS autorizado del pasajero o punto marcado en el mapa). Las URLs utilizan los enlaces oficiales de navegación. La ruta inicia desde la ubicación actual del dispositivo del conductor, si el navegador de mapas tiene acceso a ella. Al volver a Metro Taxi se mantiene la carrera abierta.

Cuando la carrera está **en curso**, si existe un punto de destino marcado con coordenadas, aparecen botones adicionales para navegar hacia el destino.

**No se inventan coordenadas a partir de una dirección o un texto de WhatsApp/Waze.** Si faltan coordenadas, el conductor verá un aviso para que la central obtenga el punto con el cliente; no se muestran enlaces de navegación engañosos. No se comparten teléfonos del pasajero.

## Instalación en Windows

1. Detén el servidor anterior con `Ctrl+C`.
2. Descomprime esta entrega en otra carpeta.
3. Si tienes datos, **respalda** primero y copia la carpeta `runtime` desde la versión anterior; no la borres ni subas credenciales a GitHub.
4. Ejecuta `iniciar_windows.bat`, abre `http://127.0.0.1:8765/ingresar` y accede como conductor.
5. En una carrera aceptada, pulsa **Navegar a recogida con Waze** desde el celular. En PC se abrirá Waze web. Si acabas de actualizar, presiona `Ctrl+F5`.

El GPS del pasajero puede tener un margen de error. El botón inicia la ruta en Waze/Maps, no crea una navegación propia de Metro Taxi. Se requiere Internet y Waze o Google Maps disponible; no use el teléfono mientras maneja.

## Pruebas

En la carpeta raíz:

```sh
python -m unittest discover -s tests -v
node tests/test_navigation_v083.cjs
```

## Pendientes de producción

Este sigue siendo un servidor de demostración local Python/SQLite. Antes de operar comercialmente: HTTPS, identidad real, permisos de producción, pruebas en Android, backup y autenticación endurecida, publicación del backend, GPS en segundo plano del APK, validación de precisión y rutas con pasajeros reales. La navegación externa no requiere token de API de mapas para estos enlaces oficiales.

Fuentes oficiales: https://developers.google.com/waze/deeplinks y https://developers.google.com/maps/documentation/urls/get-started

---

# Metro Taxi v0.8.2 — Corrección de protección CSRF

**Problema corregido:** al enviar una operación desde la central, el servidor podía responder «Falta protección CSRF» cuando el navegador tenía el token vacío o desactualizado (por ejemplo, al abrir otra pestaña o cambiar de sesión). **No se desactivó la protección:** el servidor sigue rechazando las peticiones sin el código vigente, mientras que el cliente renueva el token y reintenta una sola vez exclusivamente si recibe `CSRF_INVALID`.

## Actualización sin perder tus datos

1. **Detén** el servidor de la versión anterior (ventana de consola, `Ctrl + C`). Si hay otro Metro Taxi ejecutándose en el puerto 8765, ciérralo también.
2. **Respalda** la carpeta `runtime` de tu instalación actual (contiene la base de datos y las credenciales iniciales); no la compartas ni subas a GitHub.
3. **Descomprime** `metro_taxi_v08_2_csrf_corregido.zip` en una carpeta nueva, sin mezclar los programas de dos versiones.
4. Copia la carpeta `runtime` de la instalación anterior a la carpeta nueva **antes de iniciarla**. Esto conserva las carreras, clientes, unidades y contraseñas locales.
5. Ejecuta `iniciar_windows.bat` desde la carpeta v0.8.2.
6. Abre `http://127.0.0.1:8765/ingresar`, presiona `Ctrl + F5` y entra como `admin` u `operador`. Luego usa la central.
7. Si cambiaste de cuenta o abriste pestañas antiguas, cierra las anteriores y vuelve a abrir la central. **No borres `runtime` para corregir un error CSRF.**

## Comprobación rápida

- Como administrador, abre `/central` y pulsa **Guardar modalidad (administrador)** con «Solo despacho manual» seleccionado. Debe confirmar el guardado sin error de CSRF.
- Comprueba que puedes registrar una carrera ficticia y que aparece en la lista de la central.
- Como pasajero, la central debe mantener acceso restringido. No inhabilites permisos de seguridad.

## Pruebas ejecutadas

- `py -3 -m unittest discover -s tests -v` → **39 pruebas Python superadas**, incluyendo la respuesta explícita a tokens inválidos sin relajar las comprobaciones.
- `node tests/test_csrf_frontend_v082.cjs` → **4 escenarios JavaScript superados** (Node.js es opcional y solo para estas pruebas).
- Sintaxis de JavaScript y Python comprobada. **No se pudo completar la prueba visual con Chromium en este entorno por un bloqueo administrativo del navegador**; se debe validar en el Chrome/Edge del equipo local.

**Entorno local de desarrollo; no publiques este servidor Python/SQLite directamente en Internet.**

---

# Corrección Metro Taxi v0.8.1 — Central recargando

Se corrigió un ciclo de redirecciones: cuando la sesión pertenecía a un **cliente**, la pantalla `/ingresar` lo mandaba a `/central` y el servidor lo devolvía al acceso. Ahora el cliente pasa a `/cliente`, el conductor a `/conductor` y administrador/operador a `/central`. Si alguien abre un enlace de otra función, el servidor lo redirige a la pantalla de su rol.

**Para actualizar sin borrar tus datos:**

1. Cierra el servidor anterior (Ctrl+C en la ventana donde corre). No ejecutes dos servidores en el mismo puerto.
2. Descomprime este ZIP en una carpeta nueva.
3. Si conservas datos de la v0.8, copia la carpeta `runtime` completa de la v0.8 a esta carpeta **con el servidor detenido**. Haz una copia de seguridad primero. Si todavía son datos ficticios de prueba, puedes iniciar una base nueva sin copiarla.
4. Ejecuta `iniciar_windows.bat` en la nueva carpeta. Abre `http://127.0.0.1:8765/ingresar`.
5. En el navegador, pulsa `Ctrl+F5` para recargar archivos antiguos. Si ya tenías una sesión de pasajero, al intentar abrir `/central` ahora irás a `/cliente`, que es el comportamiento esperado. Para entrar a central, cierra sesión en cliente y usa la cuenta **admin** u **operador**.

**Pruebas:** `py -3 -m unittest discover -s tests -v` (Windows). La corrección no requiere cambiar ni eliminar cuentas, conductores, carreras o registros QR.

---

# METRO TAXI — v0.8, sistema de despacho local y automático opcional

**Fecha:** 20 de noviembre de 2026 · **Estado:** MVP local funcional de demostración, NO producción.

## Qué hace la versión actual

Metro Taxi funciona como **central propietaria de la relación con sus clientes**, con sedes Pacora y 24 de Diciembre. Conserva las funciones probadas de v0.6: clientes con cuenta, captación por QR de conductor, solicitud con GPS del pasajero, central con permisos, asignación manual, rechazo, tarifa informativa, fotografía y placa del conductor, mensajes cliente-central y estadísticas.

**Agregado en v0.7 y v0.8:**

1. Ficha administrada del vehículo: marca, modelo, color, año, placa y foto del conductor.
2. Turnos declarados por los conductores (puesta en servicio y desconexión), con historial visible para la central.
3. GPS del conductor **voluntario y solo con la página abierta**. Las actualizaciones se envían con permiso y precisión informada por el dispositivo. No se inventan coordenadas a partir de direcciones. Al apagar GPS se limpia la posición, y si pierde conexión la información caduca a los 120 s para el pasajero.
4. Pasajero autenticado ve **solo** el taxista de su carrera asignada; hasta que el conductor acepte se indica «pendiente de aceptación». Después de aceptar puede consultar únicamente la última ubicación GPS reciente, si existe. Otros clientes no ven esos datos.
5. Ofertas expiran a los **120 segundos** (configurable con `METRO_OFFER_SECONDS`) y regresan a la cola en la próxima petición de API. **No hay todavía un trabajador de cola en segundo plano** ni asignación automática al taxista más cercano.
6. Cancelación desde el cliente para carreras pendientes/ofrecidas o desde la central para servicios abiertos, con liberación de unidad y auditoría.
7. Pantallas cliente y conductor incluyen manifiestos y recursos de **PWA instalable** cuando se sirve desde localhost o HTTPS; no son un APK Android.
8. **Sugerencia por cercanía:** para carreras pendientes con punto GPS explícito, muestra solo conductores disponibles de la sede, con GPS del dispositivo no simulado y actualizado hace menos de 120 s. La distancia es en línea recta, **no una ruta ni tiempo de llegada**.
9. **Despacho automático opcional:** solo administración lo habilita. Tras 120 segundos sin asignar una carrera con recogida GPS, se le ofrece al conductor elegible más cercano por distancia en línea recta. Si no hay GPS reciente o el lugar es manual, queda en la cola. **Desactivado por defecto**. La lógica se ejecuta al recibir nuevas consultas al API (no hay servicio de tareas autónomo ni SLA).
10. **Historial de ofertas:** tras el vencimiento de 120 segundos, una oferta vuelve a pendiente y no se repite automáticamente al mismo conductor para esa carrera.
11. **Cambio de contraseñas** para clientes, conductores y central; requiere contraseña actual y cierra sus sesiones. Falta recuperación automática de contraseña y validación del teléfono.

## Instalación en Windows

1. Descarga y descomprime el ZIP completo, por ejemplo en `C:\proyectos\metro_taxi_v08`.
2. Instala Python 3.10 o superior. Ejecuta `iniciar_windows.bat`, que instalará la biblioteca `qrcode` si no existe.
3. Abre **cliente**: http://127.0.0.1:8765/cliente · **central**: http://127.0.0.1:8765/central · **conductor**: http://127.0.0.1:8765/conductor · **inicio del personal**: http://127.0.0.1:8765/ingresar
4. Las cuentas de demostración `admin`, `operador`, `conductor1` y `conductor7` se generan al iniciar la base. Las contraseñas aleatorias aparecen **solo en tu computadora**, en `runtime/credenciales_iniciales.txt`.
5. Usa nombres, teléfonos y recorridos ficticios. El sistema no envía taxis reales y las coordenadas de la flota sembrada inicialmente son **simulaciones**.

Si migras desde v0.6 o v0.7: detén el servidor anterior y respalda su carpeta `runtime`. Copia `runtime` al directorio nuevo **antes del primer inicio**. El servidor añade columnas y tablas nuevas automáticamente conservando viajes y registros locales. No mezcles bases de datos con el servidor abierto.

## Recorrido de prueba recomendado

1. Entra a `/cliente`, crea un pasajero de prueba y solicita una carrera para **Pacora**. Puedes pulsar **Mi ubicación actual** desde el equipo que ejecuta localhost, o escribir la referencia sin GPS.
2. En otro navegador abre `/ingresar` con `admin`, entra en `/central`, guarda el expediente de MT-07 (foto, placa, modelo, color), selecciona la carrera y asígnala a MT-07.
3. En otra ventana entra como `conductor7`, ve a `/conductor`; pulsa **Estoy disponible** si está desconectado, luego **Aceptar**. Si das permiso GPS y la página permanece abierta, se enviarán posiciones desde el dispositivo. El GPS de `127.0.0.1` solo funciona en el equipo local; para el teléfono se requiere **HTTPS real**.
4. El pasajero actualizará automáticamente la lista y verá conductor, vehículo y, si hay señal reciente, enlace para ver la última ubicación de esa unidad. No se muestra la flota completa.
5. El operador puede cancelar una solicitud; el pasajero puede cancelar solo antes de la aceptación. Si la oferta vence en dos minutos, la siguiente consulta la devuelve a pendientes. El administrador puede probar el modo automático desde el panel superior de la central (por defecto manual).
6. Desde la central observa el historial de turnos, los rechazos e incidentes, estadísticas y los registros por QR.

## Instalación como PWA en teléfono (para pruebas)

La versión cliente/conductor dispone de manifiestos y recursos 192/512 PNG. En Chrome/Edge, abre un dominio HTTPS que sirva la **app completa con backend** y selecciona «Instalar aplicación» o «Añadir a pantalla de inicio». **No basta subir los archivos estáticos a Netlify para que el backend funcione.** No se garantiza GPS con pantalla bloqueada. En localhost solo podrás usar GPS desde el dispositivo que está ejecutando el servidor.

## Pruebas automatizadas

En PowerShell: `py -3 -m unittest discover -s tests -v`.
En Linux/macOS: `python3 -m unittest discover -s tests -v`.

**32 pruebas de backend/API superadas.** La batería cubre asignaciones, acceso por roles, captación por QR, cuentas, fotos, GPS y caducidad, vehículos, cancelaciones, turnos, propuestas vencidas, modo automático y cambio de contraseña. No sustituye revisión de seguridad, pruebas de carga ni pruebas en teléfonos.

## Datos reales y publicación

**No publicar directamente este servidor Python `http.server` con SQLite en Internet.** Para uso real faltan backend endurecido HTTPS y PostgreSQL (o base gestionada), autenticación con teléfono verificado, recuperación de cuenta, protección antiabuso y sesiones persistentes, respaldos, observabilidad, cumplimiento de protección de datos y retención, notificaciones push, GPS Android en segundo plano, APK firmada y pruebas de calle. Netlify sirve para la interfaz web, pero **este backend no se puede publicar allí arrastrando el ZIP**.

Consulta `docs/GUIA_DE_PRUEBAS.md`, `docs/PLAN_SALIDA_A_PRODUCCION.md` y `docs/ARQUITECTURA_OBJETIVO.md`.

## Mapa y licencia

El mapa de Leaflet es opcional; se puede despachar con ubicaciones escritas incluso si fallan las teselas. Leaflet es código abierto, pero los proveedores de teselas tienen sus propios términos y costos. El servidor OSM público no es un servicio ilimitado para uso comercial intensivo. OpenFreeMap es candidato para el futuro, pendiente de verificación visual y pruebas de disponibilidad. No se han incluido imágenes satelitales.

## Seguridad mínima del repositorio

`.gitignore` excluye `runtime/`, `.env`, `*.sqlite3`, contraseñas y `__pycache__`. No subas fotos reales, teléfonos, GPS, claves, tokens, DB ni documentos personales a GitHub. Este repositorio de desarrollo no contiene datos personales reales.

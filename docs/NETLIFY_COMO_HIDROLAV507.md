# Metro Taxi — publicación automática en Netlify (modelo HidroLav507)

## Objetivo

Replicar el flujo que funciona en HidroLav507 (`rrene7/hidrolav507-web`):
**GitHub → pruebas → rama principal `main` → despliegue automático de Netlify.**

El repositorio `rrene7/metrotaxi` contiene ahora `netlify.toml` y `netlify-public/`.
**Solo** se publican en Netlify `netlify-public/index.html` y `netlify-public/demo.js`. Es una **simulación pública con datos ficticios**, para que puedas mostrar el diseño y probar los roles. **No registra carreras reales.**

La aplicación operativa (`cloud/`, `web-staging/`, PostgreSQL, conductor GPS, control de distancia) sigue aparte y no se expone copiándola a una web estática.

## Vincular GitHub a Netlify (una vez)

1. Entra en [Netlify](https://app.netlify.com/) con la cuenta donde ya administras HidroLav507.
2. **Add new project → Import an existing project → GitHub** y elige `rrene7/metrotaxi` (**no** `rrene7/hidrolav507-web`).
3. Crea **un proyecto nuevo** para Metro Taxi. No edites ni cambies el repositorio conectado al proyecto existente **hidrolav507**.
4. Selecciona la rama **`main`**, carpeta base **vacía**, y comprueba los parámetros de `netlify.toml`:
   - **Build command:** `node tests_cloud/test_netlify_public_demo.cjs`
   - **Publish directory:** `netlify-public`
   - No variables de entorno ni base de datos para esta demostración.
5. Verifica que Netlify indique que el plan es gratuito, revisa la vista previa y publica. Se asignará una URL `*.netlify.app` **real**; no debemos adivinarla.
6. Comprueba en el navegador: botón **Solicitar taxi** visible, cliente no ve la bitácora interna, **Historial** separado, conductor no inicia/finaliza hasta llegar en la simulación, marcador 🚕 y mapa con datos ficticios.

Netlify tomará nuevas versiones de **`main`** automáticamente al fusionar los cambios, como HidroLav507. El comando de build ejecuta la prueba JavaScript antes de publicar. GitHub Actions sigue comprobando la regresión en cada cambio.

## Cómo actualizar la demostración sin que las versiones se separen

La fuente de la demostración histórica de GitHub Pages sigue en la rama `gh-pages`. La copia para Netlify queda fijada en `main/netlify-public` para que **la publicación use siempre `main`**. Si mejoras `gh-pages`, actualiza también `netlify-public/index.html` y `netlify-public/demo.js` mediante PR a `main`; el test comprueba el hash de la versión JavaScript y los recorridos básicos.

La URL de GitHub Pages es **https://rrene7.github.io/metrotaxi/**, una demostración separada. La de Netlify aparecerá cuando enlaces este repositorio.

## Qué falta para el servicio real

Netlify sirve HTML/CSS/JS, pero **no reemplaza** la API Python de despacho ni PostgreSQL. Para probar con dos teléfonos reales tendremos que ejecutar el servidor y la base (por ejemplo Docker en tu computadora) y habilitar **HTTPS** y controles de acceso. Nunca publiques `cloud.preview`, SQLite, contraseñas o `runtime/`. Tampoco elimines `METRO_ALLOWED_ORIGINS`, CSRF o las restricciones GPS para facilitar la publicación.

Cuando exista una API HTTPS autorizada y verificada, se preparará **otro despliegue controlado** de `web-staging/` con proxy seguro, pruebas de cookies y CSRF. No reemplazar la simulación por pantallas rotas mientras ese backend no exista.

**Límite:** la demostración no tiene datos reales ni crea cuentas. No es apta para operar un negocio de taxis.

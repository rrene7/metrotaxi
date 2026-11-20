# Metro Taxi — Demostración pública con datos ficticios

Pasajero solo ve estado y su historial en una pestaña separada. La bitácora interna solo se muestra al seleccionar rol central o conductor (es una demo, no un sistema de permisos). El taxi simulado aparece como 🚕. El conductor no puede iniciar ni completar hasta que el vehículo simulado llegue a recogida o destino.

Esta demo **NO envía coordenadas GPS ni solicitudes reales**. No contiene clientes ni contraseñas reales.
## CACHE-108 — La demostración se veía sin botones (2026-11-20)

GitHub Pages publicó HTML actualizado pero Chrome pudo conservar el JavaScript antiguo bajo la ruta `demo.js`. El navegador ejecutaba un archivo con referencias `$()` inexistentes, mientras el HTML ya esperaba `$$()`; fallaba la inicialización después de dibujar el mapa. Ahora `index.html` incluye `demo.js?v=<hash-del-contenido>` y la prueba `tests/demo-smoke.cjs` obliga a mantener ese identificador sincronizado con el archivo. Las pestañas iniciales ya no dependen de ejecutar JavaScript para hacerse visibles; la pantalla muestra un aviso ante errores. Sin backend real: los datos de Pages son ficticios.

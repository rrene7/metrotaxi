# Arquitectura Metro Taxi y orden de desarrollo

## Producto

**Cliente:** web móvil PWA: acceso con cuenta, punto de recogida GPS autorizado o manual, QR de captación, solicitud y seguimiento de la unidad asignada. **Central:** web privada: controla carreras, tarifas informativas, clientes, QR, unidades y dos sedes, con rol administrador/operador. **Conductor:** aplicación Android privada (objetivo) para turnos, propuestas de servicios, foto y GPS voluntario; actualmente web/PWA local.

## Desarrollo verificado (v0.8)

Servidor local Python + SQLite, UI HTML/CSS/JS y pruebas HTTP. Operaciones manuales, ofertas vencidas, perfil del vehículo, geolocalización del conductor en primer plano, historial de turnos, QR, protección server-side, recomendaciones por GPS recientes, modo automático opcional y cambio de contraseñas. Los demo-taxis originales usan posiciones SIMULADAS. La central posee el teléfono del cliente; al conductor se le envía solo lo estrictamente operativo.

## Producción objetivo, no implementada

1. API transaccional desplegada en infraestructura HTTPS, base PostgreSQL gestionada, roles aplicados en servidor, almacenamiento privado de fotos, auditoría y recuperación.
2. Frontends cliente y central en Netlify con dominio Metro Taxi y API segura; no distribuir claves secretas en el frontend.
3. APK Android de conductor compilada y firmada, usando GPS nativo con servicio de primer plano y tratamiento correcto de ubicación en segundo plano. Notificaciones push y cola robusta de ofertas.
4. Opcional: WhatsApp Business oficial mediante API, proveedores de mensajes, mapas con licencias vigentes, cobro y tarifario conforme a normativa aplicable.

El usuario sigue siendo cliente de **Metro Taxi**, no de cada taxista. La central es quien administra y reasigna la carrera. Un pasajero jamás tiene acceso al mapa de toda la flota.

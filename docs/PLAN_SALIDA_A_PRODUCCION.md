# Bloqueos para producción de Metro Taxi

El MVP funciona localmente; para aceptar pasajeros reales faltan tareas de producto, seguridad, infraestructura, comercialización y móviles.

| Frente | Qué falta | Por qué importa |
|---|---|---|
| Infraestructura | API HTTPS alojada de manera segura, sesiones y almacenamiento persistentes, PostgreSQL, migraciones, backups/restauración, monitoreo | Python http.server + SQLite local no admiten el entorno público de esta operación |
| Identidad | Validar teléfono por SMS o canal confiable, recuperación de contraseña, gestión de sesiones persistentes, limitación de intentos, anti-bots | Evitar suplantación y solicitudes fraudulentas |
| Datos privados | Avisos, consentimiento, retención/borrado, permisos de acceso, fotos autorizadas, auditoría, cifrado y revisión legal de Ley 81 (Panamá) | Se trata teléfono y geolocalización de clientes y conductores |
| GPS Android | APK compilada, firmada, prueba en Android reales, servicio nativo de ubicación en primer plano, políticas de batería y permisos Android modernos, GPS al bloquear pantalla | PWA no mantiene GPS fiable en segundo plano |
| Mensajes | Push Android y notificaciones efectivas, persistencia de cola, reconexiones, SLA de aceptación y aviso a central | El conductor no puede perder carreras si la página no está abierta |
| Mapa | Elegir proveedor/contrato, comprobar atribución y costos, disponibilidad, rutas y ETA con datos de tráfico cuando existan | No confundir distancia en línea recta con tiempo real de llegada |
| Despacho | Asignación por cercanía calculada sobre GPS reciente con reglas de reparto, modo automático controlado, simulación y pruebas de saturación | Minimizar carreras mal asignadas, dos sedes y picos de 200–300 servicios/día |
| Operaciones | Definir política de cancelaciones, tarifas, reportes monetarios, cuota de piquera, controles de conductores, soporte y contingencia de caídas | Asegurar el control comercial de Metro Taxi |
| Publicación | Dominios, cuentas de proveedores, hosting API, Netlify, Apple/Google si aplica, certificados, compilación y firma APK | Son acciones externas que necesitan cuentas, permisos y claves del propietario |

**Importante:** No firmar una APK ni desplegar un servidor real usando claves de ejemplo. No afirmar que está en línea o listo hasta completar estas tareas y pruebas de campo. Este documento no sustituye revisión profesional legal y de seguridad.

## Estado tras la v0.8

Están implementados **solo para el piloto local** el despacho manual, la sugerencia geográfica y la autoasignación optativa después de 120 segundos. Esta última requiere una consulta activa al API para ejecutarse; **antes de producción necesita un proceso de cola independiente**, reintentos, idempotencia, notificaciones push y pruebas de sobrecarga. También se implementó cambio de contraseña con invalidación de sesión; faltan recuperación de contraseña, verificación de teléfonos y autenticación resistente a abuso.

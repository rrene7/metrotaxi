# Metro Taxi v0.9 — Publicación por componentes (PENDIENTE)

## Arquitectura segura antes de exponer datos de pasajeros

1. **API y base de datos:** migrar Python/SQLite local a un backend transaccional con PostgreSQL, sesiones persistentes, HTTPS, colas, seguridad, backups, auditoría y monitoreo. No publicar el `server.py` actual en Internet. Las dos sedes, la asignación y el control de clientes siempre permanecen en la API central.
2. **Web Netlify:** publicar **únicamente interfaces estáticas** del cliente y central, después de desacoplar las APIs y redirecciones actuales. La versión v0.8.x sirve HTML autenticado desde Python y NO funciona en Netlify por arrastrar el ZIP. El frontend debe llamar la API mediante origen autorizado, sin claves secretas en JavaScript; analizar cookies SameSite y CSRF, o gateway BFF.
3. **APK conductor:** compilar `android-conductor/` contra el dominio HTTPS de la API de producción. El APK abre la interfaz actual de conductor y envía GPS bajo sesión/CSRF y notificación visible. **No contiene servidor interno ni base de datos**, y no funciona apuntando a `127.0.0.1`.
4. **QR:** `METRO_PUBLIC_BASE_URL` debe usar el dominio público HTTPS del formulario de captación de clientes. Validar enlaces, protección anti-bots y consentimiento antes de imprimir los QR.
5. **Prueba piloto:** 2–3 conductores con Android físico, 2 sedes, decenas de solicitudes ficticias, cancelaciones y pérdida de GPS; después ensayar carga 200–300 carreras/día, incidentes y mantenimiento.

## Orden de lanzamiento

| Etapa | Entrada necesaria | Resultado / criterio |
| --- | --- | --- |
| A. API | hosting, PostgreSQL, dominio y TLS | Rutas, roles, GPS, CSRF y pruebas automatizadas en staging |
| B. Web | API staging estable | Netlify para cliente/central, 2 sedes y flujos integrados |
| C. APK | dominio API con HTTPS + Android Studio | APK debug instalada, GPS y navegación en teléfonos reales |
| D. Seguridad | política de datos, verificación de teléfono, auditoría | informe y permisos antes de uso comercial |
| E. Producción | monitoreo, backup restaurado y soporte | operación escalonada y medición de fallos |

**Estado real al entregar v0.9:** código Android entregado, no APK compilada; despliegue Netlify y API productiva todavía pendientes. No hay dominio, credenciales ni proveedor de nube configurado en el proyecto.

Referencias oficiales:
- Android FGS location: https://developer.android.com/about/versions/14/changes/fgs-types-required
- Restricciones FGS: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- Riesgos WebView: https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges
- Netlify funciones/hosting: https://docs.netlify.com/functions/overview/

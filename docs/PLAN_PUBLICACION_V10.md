# Publicación web/API de Metro Taxi — v0.10 (plan y verificaciones pendientes)

**No se ha desplegado ningún dominio ni PostgreSQL; no se ha instalado APK en Android.** Esta versión prepara el camino sin exponer los datos del prototipo.

## Separación estricta

- **v0.9 local:** `server.py`, `runtime/`, interfaces existentes y QR. Se mantiene intacta, sin migraciones automáticas.
- **v0.10 cloud:** `cloud/` API transaccional, `web-staging/` frontend de pruebas, base PostgreSQL en destino; *SQLite solo en pruebas controladas*.
- **Netlify:** solo frontend estático y ruta de proxy `/api/*` a API HTTPS real. Un ZIP con páginas no sustituye al servidor.
- **Android:** APK se compila con el origen **web Netlify**. El proxy permite que la sesión cookie y el token CSRF se envíen al backend en la misma ruta de origen. Confirmar comportamiento en red real.

## Puertas antes de publicar

1. Backend HTTPS real con `DATABASE_URL` gestionada, acceso de DB mínimo, TLS, backups y restauración comprobada.
2. DNS y dos dominios separados: `app.*` Netlify y `api.*` backend. `METRO_ALLOWED_ORIGINS=https://app.*`, `METRO_ALLOWED_HOSTS=api.*`. Certificados HTTPS válidos, proxy/trusted headers restringidos.
3. Migraciones de esquema versionadas, monitoreo, alertas, auditoría, gestión de secretos, restricción de red y respuesta a incidentes. `cloud.manage --init-schema` sirve únicamente para una **BD vacía de staging** y no es una herramienta general de actualización de producción.
4. Protección contra registro abusivo y fuerza bruta, limitación de tasas, captcha/OTP cuando proceda, recuperación de cuenta y verificación de teléfono.
5. Probar en Netlify real que `/api/me`, login, cookies `Secure; HttpOnly`, CSRF, `Origin`, `logout` y las rutas por rol funcionan. No permitir que un fallo de proxy redirija hacia un sitio no confiable.
6. Reglas de tratamiento y conservación de datos personales conforme a la legislación panameña, consentimientos, borrado, acceso y contratos con proveedores.
7. Migrar QR, fotos, mensajería, incidentes, tarifas y estadísticas de v0.9; cerrar la paridad antes de operaciones reales.
8. Compilar y firmar Android, probar foreground GPS, navegación Waze, batería, pérdida de cobertura, pantalla cerrada, suspensión y expiración de sesión.
9. Implementar trabajador de cola para vencimiento/autoasignación y notificaciones; hoy el vencimiento se procesa por consulta API y NO hay SLA ni alertas push.
10. Prueba piloto con pocas unidades, ensayo de carga 200–300 solicitudes/día y plan de reversión/continuidad.

## Configuración segura de Netlify

No escribir una URL de ejemplo en un ZIP para subirlo a producción. Generar desde el código fuente una vez **probado** el backend:

```powershell
py -3 scripts\preparar_netlify.py --api-url https://api.TUDOMINIO.COM --output netlify-dist
```

La carpeta tendrá `_redirects` con `/api/* https://api.TUDOMINIO.COM/api/:splat 200` (proxy del mismo origen para el navegador). Requiere que Netlify pueda establecer HTTPS con el servidor; su existencia no garantiza que las cookies funcionen sin pruebas en sitio real. Los archivos personales quedan fuera.

## Situación real al 20-11-2026

- Nueva API funcionando en tests automatizados con SQLite efímero. **Aún no verificada con PostgreSQL real.**
- Web staging con formularios de pasajero/central/conductor, lista de carreras y Waze, pero no publicación real.
- v0.9 local conserva el resto del flujo mientras se migran módulos.
- APK Android código fuente adaptado a la web staging; **sin compilación ni prueba física.**

Fuentes de diseño: https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/ y https://fastapi.tiangolo.com/deployment/https/

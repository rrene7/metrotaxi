# API cloud Metro Taxi (staging)

V0.10 usa SQLAlchemy Core y modelos compatibles PostgreSQL. **No es una migración de SQLite** y no incluye datos de producción. Para iniciar solo la prueba local usar `iniciar_staging_windows.bat`, que monta `web-staging/` y prepara una BD SQLite aislada en `_runtime_staging/`.

Para crear un esquema *nuevo y vacío* en PostgreSQL:

```bash
export DATABASE_URL='postgresql+psycopg://<usuario>:<secreto>@<host>:5432/<db>'
python -m cloud.manage --init-schema
python -m cloud.manage --create-admin
```

Para iniciar API HTTPS detrás de un proxy TLS confiable, definir también `METRO_ALLOWED_ORIGINS` y `METRO_ALLOWED_HOSTS`, cargar variables desde el gestor de secretos, y ejecutar `uvicorn cloud.app:app --host 127.0.0.1 --port 8000`. Se requiere proceso/infraestructura para mantenerla disponible; no usar sin controles de red y seguridad. No se incluyen administradores de prueba ni contraseñas en código.

**Seguridad:** cookies `Secure; HttpOnly`, `SameSite=Lax`, CSRF por sesión; origen de frontend explícito; consultas parametrizadas y sesiones persistentes; no CORS genérico. Falta limitación de intentos/OTP y auditoría de producción. El vencimiento de ofertas funciona al hacer consultas, todavía no hay colas ni notificaciones. Para Netlify la API debe tener un dominio HTTPS real.

Pruebas `python scripts/validar_cloud.py`: **sustituyen PostgreSQL por SQLite temporal solamente durante los tests**. El resto de los módulos locales se validan por separado.

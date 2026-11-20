# Metro Taxi

Plataforma privada de gestión de carreras para las sedes de **Pacora** y **24 de Diciembre**, Panamá.

## Estado del proyecto

**En desarrollo — no apto aún para producción.**

La solución conserva dos líneas de trabajo:
- **Piloto local v0.9:** central, clientes, conductores, QR, seguimiento GPS con la página abierta, navegación Waze/Maps y reglas de despacho (Python/SQLite).
- **API web en migración v0.10.x:** FastAPI, esquema PostgreSQL, portal de staging y proyecto Android sin APK firmado. La paridad funcional aún está incompleta.

Las carreras pertenecen a Metro Taxi y se administran desde la central. El conductor no tiene acceso a teléfonos privados de clientes ni a la flota completa; el pasajero únicamente puede consultar sus propios servicios.

## Antes de contribuir

Lee `AGENTS.md`, `RUTA_DE_TRABAJO.md`, `docs/CONTRATO_OPERATIVO.md` y `docs/INCIDENTES_Y_SOLUCIONES.md`. No reemplaces módulos ya funcionales sin una prueba de regresión.

Nunca subas `runtime/`, `_runtime_staging/`, bases SQLite, claves de API, archivos `.env`, credenciales, información de pasajeros ni firmas Android.

## Próximo trabajo

Restablecer en cloud los mapas, recorridos, QR, estadísticas y mensajería con pruebas por rol; validar PostgreSQL real, Netlify HTTPS y compilar/probar el APK Android.

> Este repositorio es público. Publica solo código fuente y ejemplos sin datos reales.

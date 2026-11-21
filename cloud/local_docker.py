"""Loopback-only local Docker/PostgreSQL staging. NOT for public traffic.

Run ONLY through compose.local.yaml with its 127.0.0.1 published port.
Test-mode here permits HTTP loopback cookies; never use this entrypoint on
a remote host or expose it to LAN/Internet. No demo users are seeded.
"""
import os
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .app import create_app
from .pilot_tools import normalize_postgres_url, ensure_schema, public_map_config

ROOT = Path(__file__).resolve().parents[1]


def build_local_app(env=None):
    cfg = os.environ if env is None else env
    # Reject non-PostgreSQL and any database outside this isolated Docker network.
    db_url = normalize_postgres_url(cfg.get('DATABASE_URL', ''))
    from sqlalchemy.engine import make_url
    parsed = make_url(db_url)
    if parsed.host != 'db' or parsed.database != 'metrotaxi_local':
        raise RuntimeError('Piloto Docker local requiere PostgreSQL privado db/metrotaxi_local')
    app = create_app(database_url=db_url, test_mode=True, auto_create=False)
    ensure_schema(app.state.engine, allow_empty_bootstrap=False)

    @app.middleware('http')
    async def loopback_host_only(request: Request, call_next):
        # Defense in depth: publication is restricted by compose port binding.
        host = request.headers.get('host', '').split(':')[0].lower()
        if host not in ('127.0.0.1', 'localhost', 'testserver'):
            return JSONResponse({'error':'Este piloto solo permite acceso desde el equipo local'},status_code=403)
        return await call_next(request)

    @app.get('/map-config.js')
    def map_config():
        return Response(public_map_config({}), media_type='application/javascript',
                        headers={'Cache-Control':'no-store'})

    app.mount('/', StaticFiles(directory=str(ROOT / 'web-staging'), html=True), name='local-docker-web')
    return app


app = build_local_app()

"""Restricted Railway pilot: PostgreSQL + HTTPS browser entry point. NOT production."""
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

from .app import create_app
from .pilot_tools import normalize_postgres_url, check_pilot_config, ensure_schema, add_pilot_gate, public_map_config

ROOT = Path(__file__).resolve().parents[1]

def build_pilot_app(env=None):
    cfg = os.environ if env is None else env
    database_url, user, password = check_pilot_config(cfg)
    # Ensure create_app sees the same explicit host/origin environment settings.
    # Railway uses the process environment; do not override it with uploaded .env.
    app = create_app(database_url=database_url, test_mode=False, auto_create=False)
    ensure_schema(app.state.engine, allow_empty_bootstrap=cfg.get('METRO_BOOTSTRAP_EMPTY_DB') == '1')
    map_js=public_map_config(cfg)
    @app.get('/map-config.js')
    def map_config():
        return Response(content=map_js,media_type='application/javascript',headers={'Cache-Control':'no-store'})
    add_pilot_gate(app, user=user, password=password)
    app.mount('/', StaticFiles(directory=str(ROOT / 'web-staging'), html=True), name='pilot-web')
    return app

app = build_pilot_app()

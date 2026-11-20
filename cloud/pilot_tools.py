"""Restrict an Internet staging pilot; never substitute for full production hardening."""
import base64
import binascii
import hmac
import json
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy import inspect

from .schema import metadata


def normalize_postgres_url(value):
    """Railway provides postgresql://; SQLAlchemy uses psycopg 3 explicitly."""
    if not isinstance(value, str):
        raise RuntimeError('DATABASE_URL PostgreSQL obligatorio')
    if value.startswith('postgresql+psycopg://'):
        return value
    for prefix in ('postgresql://', 'postgres://'):
        if value.startswith(prefix):
            return 'postgresql+psycopg://' + value[len(prefix):]
    raise RuntimeError('DATABASE_URL debe utilizar PostgreSQL, nunca SQLite')


def check_pilot_config(env):
    database_url = normalize_postgres_url(env.get('DATABASE_URL', ''))
    user = env.get('METRO_PILOT_USER', 'metrotaxi')
    password = env.get('METRO_PILOT_PASSWORD', '')
    origin = env.get('METRO_ALLOWED_ORIGINS', '')
    hosts = env.get('METRO_ALLOWED_HOSTS', '')
    if (not isinstance(password, str) or len(password) < 20 or not password.strip()
            or password in ('change-me', 'password', '12345678901234567890')):
        raise RuntimeError('Define METRO_PILOT_PASSWORD aleatoria de al menos 20 caracteres')
    if not user or ':' in user or len(user) > 50:
        raise RuntimeError('METRO_PILOT_USER no válido')
    permitted_origins = [x.strip() for x in origin.split(',') if x.strip()]
    permitted_hosts = [x.strip() for x in hosts.split(',') if x.strip()]
    if not permitted_origins or not permitted_hosts:
        raise RuntimeError('Configura METRO_ALLOWED_ORIGINS y METRO_ALLOWED_HOSTS')
    for entry in permitted_origins:
        parsed = urlparse(entry)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment
                or parsed.hostname in ('localhost', '127.0.0.1')
                or parsed.hostname.endswith(('.invalid', '.test', '.example', '.localhost'))
                or parsed.netloc != parsed.hostname and parsed.port is None):
            raise RuntimeError('METRO_ALLOWED_ORIGINS requiere dominios HTTPS reales')
        if parsed.hostname not in permitted_hosts:
            raise RuntimeError('METRO_ALLOWED_HOSTS debe incluir el host de cada origen')
    if env.get('METRO_BOOTSTRAP_EMPTY_DB', '0') not in ('0', '1'):
        raise RuntimeError('METRO_BOOTSTRAP_EMPTY_DB debe ser 0 o 1')
    return database_url, user, password


def ensure_schema(engine, allow_empty_bootstrap=False):
    """Initialize ONLY a completely empty DB with explicit opt-in; never migrate existing data."""
    existing = set(inspect(engine).get_table_names())
    expected = set(metadata.tables)
    if not existing:
        if not allow_empty_bootstrap:
            raise RuntimeError('Base vacía: habilita bootstrap inicial de forma explícita')
        metadata.create_all(engine)
        existing = set(inspect(engine).get_table_names())
    missing = expected - existing
    if missing:
        raise RuntimeError('Esquema incompleto: se requiere migración revisada; no actualizar automáticamente')


def add_pilot_gate(app, *, user, password):
    """Basic Auth is only an extra privacy gate for invited testers, over HTTPS."""
    @app.middleware('http')
    async def pilot_gate(request: Request, call_next):
        if request.url.path == '/api/health':
            return await call_next(request)
        auth = request.headers.get('authorization', '')
        authorized = False
        if auth.lower().startswith('basic '):
            try:
                decoded = base64.b64decode(auth[6:].strip(), validate=True).decode('utf-8')
                username, given_password = decoded.split(':', 1)
                authorized = (hmac.compare_digest(username, user)
                              & hmac.compare_digest(given_password, password))
            except (UnicodeDecodeError, ValueError, binascii.Error):
                pass
        if not authorized:
            return Response('Acceso reservado al piloto privado de Metro Taxi.', status_code=401,
                headers={'WWW-Authenticate': 'Basic realm="Metro Taxi Piloto", charset="UTF-8"',
                         'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
        return await call_next(request)
    return app


def public_map_config(env):
    """Return a safe public JS assignment; tile URLs are not private secrets."""
    url = env.get('METRO_MAP_TILES_URL', '').strip()
    if not url and env.get('METRO_PILOT_OSM_TILES', '0') == '1':
        url='https://tile.openstreetmap.org/{z}/{x}/{y}.png'
    if url:
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.username or parsed.password or not parsed.hostname or not all(('{'+p+'}') in url for p in ('x','y','z')):
            raise RuntimeError('METRO_MAP_TILES_URL requiere plantilla HTTPS pública con {z}/{x}/{y}')
    return 'window.METRO_MAP_TILES_URL='+json.dumps(url)+';\n'

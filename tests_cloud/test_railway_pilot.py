"""Staging deploy regressions; no real user data or external services."""
import base64
import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from cloud.pilot_tools import normalize_postgres_url, check_pilot_config, ensure_schema, add_pilot_gate, public_map_config


class RailwayPilotTests(unittest.TestCase):
    def test_normalize_railway_database_url(self):
        self.assertEqual(normalize_postgres_url('postgresql://u:p@db:5432/db'), 'postgresql+psycopg://u:p@db:5432/db')
        self.assertEqual(normalize_postgres_url('postgres://u:p@db/db'), 'postgresql+psycopg://u:p@db/db')
        self.assertEqual(normalize_postgres_url('postgresql+psycopg://u:p@db/db'), 'postgresql+psycopg://u:p@db/db')
        for bad in ('sqlite+pysqlite:///demo.db', '', 'mysql://abc', None):
            with self.assertRaises(RuntimeError):normalize_postgres_url(bad)

    def env(self):
        return {'DATABASE_URL': 'postgresql://user:secret@postgres.railway.internal:5432/railway',
            'METRO_ALLOWED_ORIGINS':'https://mt-piloto.up.railway.app',
            'METRO_ALLOWED_HOSTS':'mt-piloto.up.railway.app',
            'METRO_PILOT_PASSWORD':'pruebas-una-frase-muy-larga-123',
            'METRO_BOOTSTRAP_EMPTY_DB':'0'}

    def test_reject_unsafe_pilot_configuration(self):
        env=self.env()
        self.assertEqual(check_pilot_config(env)[1],'metrotaxi')
        for key, value in [('METRO_PILOT_PASSWORD','password'),('METRO_ALLOWED_ORIGINS','http://localhost:8770'),
                           ('METRO_ALLOWED_ORIGINS','https://elsewhere.example.com'),
                           ('METRO_ALLOWED_HOSTS','example.org'),('METRO_BOOTSTRAP_EMPTY_DB','true'),
                           ('DATABASE_URL','sqlite+pysqlite:///tmp/secret.db')]:
            broken=env | {key:value}
            with self.subTest(key=key,value=value):
                with self.assertRaises(RuntimeError):check_pilot_config(broken)

    def test_railway_healthcheck_host_explicit(self):
        env=self.env() | {'RAILWAY_PROJECT_ID':'demo-project'}
        with self.assertRaises(RuntimeError):check_pilot_config(env)
        env['METRO_ALLOWED_HOSTS']='mt-piloto.up.railway.app,healthcheck.railway.app'
        self.assertEqual(check_pilot_config(env)[1],'metrotaxi')

    def test_only_empty_database_can_be_bootstrapped(self):
        with tempfile.TemporaryDirectory() as d:
            engine=create_engine('sqlite+pysqlite:///'+str(Path(d)/'test.sqlite'))
            with self.assertRaises(RuntimeError):ensure_schema(engine, allow_empty_bootstrap=False)
            ensure_schema(engine, allow_empty_bootstrap=True)
            ensure_schema(engine, allow_empty_bootstrap=False)
            engine.dispose()
        with tempfile.TemporaryDirectory() as d:
            engine=create_engine('sqlite+pysqlite:///'+str(Path(d)/'partial.sqlite'))
            with engine.begin() as c:
                c.exec_driver_sql('CREATE TABLE incomplete (id INTEGER PRIMARY KEY)')
            with self.assertRaises(RuntimeError):ensure_schema(engine, allow_empty_bootstrap=True)
            engine.dispose()

    def test_private_gate_and_public_healthcheck(self):
        app=FastAPI()
        @app.get('/api/health')
        def health():return {'ok':True}
        @app.get('/api/me')
        def me():return {'authenticated':False}
        add_pilot_gate(app,user='metrotaxi',password='correct-pilot-password-long')
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/health').status_code,200)
            result=client.get('/api/me')
            self.assertEqual(result.status_code,401)
            self.assertIn('Basic',result.headers.get('www-authenticate',''))
            self.assertEqual(client.get('/api/me',headers={'Authorization':'Basic !!!'}).status_code,401)
            wrong=base64.b64encode(b'metrotaxi:incorrect').decode()
            self.assertEqual(client.get('/api/me',headers={'Authorization':'Basic '+wrong}).status_code,401)
            good=base64.b64encode(b'metrotaxi:correct-pilot-password-long').decode()
            self.assertEqual(client.get('/api/me',headers={'Authorization':'Basic '+good}).status_code,200)

    def test_public_map_config_requires_explicit_choice(self):
        self.assertIn('METRO_MAP_TILES_URL=""',public_map_config({}))
        demo=public_map_config({'METRO_PILOT_OSM_TILES':'1'})
        self.assertIn('tile.openstreetmap.org',demo)
        with self.assertRaises(RuntimeError):public_map_config({'METRO_MAP_TILES_URL':'http://evil.invalid/{z}/{x}/{y}.png'})
        self.assertIn('tile.example.org',public_map_config({'METRO_MAP_TILES_URL':'https://tile.example.org/{z}/{x}/{y}.png'}))

    def test_docker_restrictions(self):
        root=Path(__file__).resolve().parents[1]
        docker=(root/'Dockerfile').read_text()
        self.assertIn('USER metro',docker)
        self.assertIn('cloud.pilot:app',docker)
        self.assertNotIn('cloud.preview:app',docker)
        ignore=(root/'.dockerignore').read_text()
        for banned in ('_runtime_staging','runtime','*.sqlite*','.env'):
            self.assertIn(banned,ignore)
        railway=(root/'railway.toml').read_text()
        self.assertIn('"/api/health"',railway)

if __name__=='__main__':unittest.main()

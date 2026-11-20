"""Pilot production-readiness checks, isolated: no network and no real data."""
import json
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine

from cloud.manage import initialize_empty_schema
from cloud.pilot_probe import PilotProbeError, probe_pilot, validate_base_url
from cloud.schema import metadata


def fake_http(override=None):
    responses={
        '/api/health':(200,{'Content-Type':'application/json'},json.dumps({'ok':True,'database':'ready'}).encode()),
    }
    for p in ('/','/ingresar.html','/api/me','/api/trips','/map-config.js'):
        responses[p]=(401,{'WWW-Authenticate':'Basic realm="Metro Taxi Piloto"'},b'Protegido')
    responses.update(override or {})
    return lambda path:responses[path]


class PilotDeploymentVerification(unittest.TestCase):
    def test_https_domain_validation(self):
        self.assertEqual(validate_base_url('https://metro-piloto.up.railway.app'),
                         'https://metro-piloto.up.railway.app')
        for bad in (
            'http://metro-piloto.up.railway.app',
            'https://localhost', 'https://127.0.0.1',
            'https://example.test', 'https://example.com/private',
            'https://u:p@example.com', 'https://example.com/?token=secret',
            'https://example.com:8443', 'https://example.com/#admin', 'https://192.168.1.5', ''):
            with self.subTest(bad=bad):
                with self.assertRaises(PilotProbeError):
                    validate_base_url(bad)

    def test_all_paths_and_postgres_healthy(self):
        result=probe_pilot('https://metro-piloto.up.railway.app',fake_http())
        self.assertEqual(result['database'],'ready')
        self.assertEqual(len(result['protected_paths']),5)

    def test_reject_publicly_exposed_endpoints_and_failed_db(self):
        with self.assertRaises(PilotProbeError):
            probe_pilot('https://metro-piloto.up.railway.app',
                       fake_http({'/api/me':(200,{},b'{"authenticated":false}') }))
        with self.assertRaises(PilotProbeError):
            probe_pilot('https://metro-piloto.up.railway.app',
                       fake_http({'/api/health':(503,{},b'{"database":"unavailable"}')}))
        with self.assertRaises(PilotProbeError):
            probe_pilot('https://metro-piloto.up.railway.app',
                       fake_http({'/':(302,{'Location':'https://other.invalid'},b'')}))
        with self.assertRaises(PilotProbeError):
            probe_pilot('https://metro-piloto.up.railway.app',
                       fake_http({'/api/trips':(401,{},b'')}))

    def test_schema_initializer_rejects_existing_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=create_engine('sqlite+pysqlite:///'+str(Path(tmp)/'pilot.sqlite'))
            with engine.begin() as db:
                db.exec_driver_sql('CREATE TABLE existing_table(id INTEGER PRIMARY KEY)')
            with self.assertRaises(RuntimeError):
                initialize_empty_schema(engine)
            with engine.connect() as db:
                self.assertIsNotNone(db.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='existing_table'").first())
            engine.dispose()

    def test_schema_initializer_only_empty_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=create_engine('sqlite+pysqlite:///'+str(Path(tmp)/'pilot.sqlite'))
            initialize_empty_schema(engine)
            with self.assertRaises(RuntimeError):
                initialize_empty_schema(engine)
            from sqlalchemy import inspect
            self.assertEqual(set(inspect(engine).get_table_names()), set(metadata.tables))
            engine.dispose()


if __name__=='__main__':
    unittest.main()

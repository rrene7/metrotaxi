import tempfile
import unittest
from pathlib import Path
from scripts.preparar_netlify import build

class BuildNetlifyTests(unittest.TestCase):
    def test_requires_real_https_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ('http://api.example.com', 'https://example.invalid','https://127.0.0.1',
                        'https://user:secret@api.real.com', 'https://api.real.com/path'):
                with self.assertRaises(ValueError, msg=bad):build(bad,Path(tmp)/'out')

    def test_schema_compiles_for_postgres_without_live_db(self):
        from sqlalchemy.dialects import postgresql
        from sqlalchemy.schema import CreateTable
        from cloud.schema import metadata
        d=postgresql.dialect()
        for table in metadata.sorted_tables:
            ddl=str(CreateTable(table).compile(dialect=d))
            self.assertIn('CREATE TABLE',ddl)
            self.assertIn(table.name,ddl)

    def test_deployment_contains_proxy_and_no_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=build('https://api.metrotaxi.example.org',Path(tmp)/'dist')
            self.assertEqual((d/'_redirects').read_text().strip(),'/api/* https://api.metrotaxi.example.org/api/:splat 200')
            for name in ('index.html','cliente.html','central.html','conductor.html','ingresar.html','styles.css','_headers','js/api.js'):
                self.assertTrue((d/name).is_file(),name)
            self.assertFalse((d/'runtime').exists())
            self.assertFalse((d/'.env').exists())
            with self.assertRaises(ValueError):build('https://api.metrotaxi.example.org',d)

if __name__=='__main__':unittest.main()

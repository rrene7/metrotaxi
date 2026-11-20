"""REG-102: Browser Origin on local staging POST must not block login.

Do not weaken CSRF or the public API Origin check.
"""
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import insert
from cloud.app import create_app, password_hash
from cloud.schema import staff


class StagingLoginOriginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app('sqlite+pysqlite:///' + str(Path(self.tmp.name) / 'test.sqlite3'),
                              test_mode=True, auto_create=True)
        with self.app.state.engine.begin() as conn:
            conn.execute(insert(staff).values(username='admin', role='admin',
                        password_hash=password_hash('PruebaUnica123!')))
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.state.engine.dispose()
        self.tmp.cleanup()

    def login(self, origin):
        return self.client.post('/api/login', headers={'Origin': origin},
                         json={'username': 'admin', 'password': 'PruebaUnica123!'})

    def test_browser_post_localhost_8770_succeeds(self):
        for origin in ('http://127.0.0.1:8770', 'http://localhost:8770'):
            with self.subTest(origin=origin):
                r = self.login(origin)
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(r.json()['role'], 'admin')
                self.assertTrue(self.client.get('/api/me').json()['authenticated'])

    def test_untrusted_origin_and_different_port_remain_forbidden(self):
        for origin in ('http://evil.example:8770', 'http://127.0.0.1:8771',
                       'http://127.0.0.1:8770.evil.example', 'null', 'https://localhost:8770'):
            with self.subTest(origin=origin):
                r = self.login(origin)
                self.assertEqual(r.status_code, 403, r.text)
                self.assertEqual(r.json()['error'], 'Origen no autorizado')

    def test_wrong_password_is_401_not_403(self):
        r = self.client.post('/api/login',headers={'Origin':'http://127.0.0.1:8770'},
                             json={'username':'admin','password':'incorrecto'})
        self.assertEqual(r.status_code,401)
        self.assertEqual(r.json()['error'],'Credenciales incorrectas')

    def test_csrf_protection_is_still_required_after_login(self):
        self.assertEqual(self.login('http://127.0.0.1:8770').status_code, 200)
        r = self.client.post('/api/logout', headers={'Origin':'http://127.0.0.1:8770'},json={})
        self.assertEqual(r.status_code,403,r.text)
        csrf=self.client.get('/api/me').json()['csrf']
        r = self.client.post('/api/logout',headers={'Origin':'http://127.0.0.1:8770','X-CSRF-Token':csrf},json={})
        self.assertEqual(r.status_code,200,r.text)
        self.assertFalse(self.client.get('/api/me').json()['authenticated'])

    def test_browser_customer_registration_allowed_with_consent(self):
        r=self.client.post('/api/customer/register',headers={'Origin':'http://127.0.0.1:8770'},
             json={'name':'Cliente demostración','phone':'6123-4567','password':'UnaClaveMuySegura123!', 'consent':True})
        self.assertEqual(r.status_code,201,r.text)


if __name__ == '__main__':
    unittest.main()

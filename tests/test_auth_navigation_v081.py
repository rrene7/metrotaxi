"""Regression tests for authenticated navigation and role-based redirects (v0.8.1)."""
import unittest
import test_mvp as legacy

class NavigationV081Tests(unittest.TestCase):
    setUp=legacy.ApiMVPTests.setUp
    tearDown=legacy.ApiMVPTests.tearDown
    client=legacy.ApiMVPTests.client
    request=legacy.ApiMVPTests.request
    login=legacy.ApiMVPTests.login

    def assert_destination(self, client, path, expected):
        # Urllib follows 302; a loop would raise an HTTPError on too many redirects.
        result=client.open(self.origin+path,timeout=5)
        self.assertEqual(result.status,200)
        self.assertEqual(result.geturl(),self.origin+expected)

    def test_anonymous_central_requires_login_without_loop(self):
        self.assert_destination(self.client(),'/central','/ingresar')
        self.assert_destination(self.client(),'/conductor','/ingresar')

    def test_customer_cannot_loop_between_central_and_login(self):
        client=self.client()
        result=self.request('/api/customer/register','POST',{
            'name':'Cliente de prueba','phone':'60003330','password':'CuentaCliente2026!','consent':True
        },client)
        self.assertEqual(result[0],201)
        self.assert_destination(client,'/central','/cliente')
        self.assert_destination(client,'/conductor','/cliente')
        self.assert_destination(client,'/ingresar','/ingresar')

    def test_roles_receive_correct_view(self):
        for role,owned,other in [('admin','/central','/conductor'),('operador','/central','/conductor'),('conductor1','/conductor','/central')]:
            with self.subTest(role=role):
                c,_=self.login(role)
                self.assert_destination(c,owned,owned)
                self.assert_destination(c,other,owned)

    def test_login_and_views_disable_cache(self):
        c,_=self.login('admin')
        for url in ('/central','/ingresar','/static/auth.js','/static/office.js','/static/driver.js'):
            with self.subTest(url=url):
                r=c.open(self.origin+url,timeout=5)
                self.assertEqual(r.headers.get('Cache-Control'),'no-store')

if __name__=='__main__':unittest.main()

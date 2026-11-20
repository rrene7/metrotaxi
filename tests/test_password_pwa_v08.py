"""Metro Taxi v0.8: password rotation and PWA asset serving."""
import unittest
import test_mvp as legacy

class PasswordPWATests(unittest.TestCase):
    setUp=legacy.ApiMVPTests.setUp
    tearDown=legacy.ApiMVPTests.tearDown
    client=legacy.ApiMVPTests.client
    request=legacy.ApiMVPTests.request
    login=legacy.ApiMVPTests.login

    def test_admin_must_prove_old_password_and_relogin(self):
        admin,csrf=self.login('admin')
        new='NuevaClaveMetroTaxi2026!'
        self.assertEqual(self.request('/api/account/password','POST',{'current_password':'mal','new_password':new},admin,csrf)[0],403)
        self.assertEqual(self.request('/api/account/password','POST',{'current_password':self.passwords['admin'],'new_password':'abc'},admin,csrf)[0],400)
        self.assertEqual(self.request('/api/account/password','POST',{'current_password':self.passwords['admin'],'new_password':new},admin,csrf)[0],200)
        self.assertEqual(self.request('/api/fleet',client=admin)[0],401)
        self.assertEqual(self.request('/api/login','POST',{'username':'admin','password':self.passwords['admin']},self.client())[0],401)
        self.assertEqual(self.request('/api/login','POST',{'username':'admin','password':new},self.client())[0],200)

    def test_customer_password_change_and_assets(self):
        customer=self.client()
        status,data=self.request('/api/customer/register','POST',{'name':'Pasajero prueba','phone':'60002212',
                  'password':'ClaveClienteOriginal2026','consent':True},customer)
        self.assertEqual(status,201)
        token=self.request('/api/me',client=customer)[1]['csrf']
        status,r=self.request('/api/account/password','POST',{'current_password':'ClaveClienteOriginal2026','new_password':'ClaveClienteNueva2026'},customer,token)
        self.assertEqual(status,200,r)
        self.assertEqual(self.request('/api/customer/trips',client=customer)[0],401)
        self.assertEqual(self.request('/api/customer/login','POST',{'phone':'60002212','password':'ClaveClienteNueva2026'},customer)[0],200)
        for path in ('/sw.js','/manifest-cliente.webmanifest','/manifest-conductor.webmanifest','/static/metro-icon-192.png','/static/metro-icon-512.png'):
            status,raw=self.request(path)
            self.assertEqual(status,200,(path,status))
            self.assertGreater(len(raw),50,path)

if __name__=='__main__':unittest.main()

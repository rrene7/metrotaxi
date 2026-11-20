"""Additional integration tests for v0.6 passenger accounts and allocated driver profiles."""
import base64
from urllib.error import HTTPError
from urllib.request import Request
import unittest
import test_mvp as legacy

# Valid 1x1 image fixture - not a photo of any real individual.
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==')

class PassengerProfileTests(unittest.TestCase):
    setUp = legacy.ApiMVPTests.setUp
    tearDown = legacy.ApiMVPTests.tearDown
    client = legacy.ApiMVPTests.client
    request = legacy.ApiMVPTests.request
    login = legacy.ApiMVPTests.login
    newtrip = legacy.ApiMVPTests.newtrip
    def new_account(self,phone='60002345',name='Pasajero registrado'):
        c=self.client()
        status,body=self.request('/api/customer/register','POST',{
            'name':name,'phone':phone,'password':'ClaveDemostracion2026!','consent':True},client=c)
        self.assertEqual(status,201,body)
        self.assertFalse(body['phone_verified'])
        me=self.request('/api/me',client=c)[1]
        self.assertEqual(me['user']['role'],'customer')
        return c,me['csrf']
    def photo_request(self,driver_id,client):
        req=Request(self.origin+'/api/driver-photo/'+str(driver_id),method='GET')
        try:
            r=client.open(req,timeout=5)
            return r.status,r.read(),r.headers.get('Content-Type')
        except HTTPError as e:
            return e.code,e.read(),e.headers.get('Content-Type')

    def test_customer_account_requires_password_and_consent(self):
        self.assertEqual(self.request('/api/customer/register','POST',{
            'name':'Persona Demo','phone':'60001111','password':'abc','consent':True})[0],400)
        self.assertEqual(self.request('/api/customer/register','POST',{
            'name':'Persona Demo','phone':'60001111','password':'claveDEMO123','consent':False})[0],400)
        client,csrf=self.new_account()
        self.assertEqual(self.request('/api/fleet',client=client)[0],403)
        self.assertEqual(self.request('/api/trips',client=client)[0],403)
        self.assertEqual(self.request('/api/customer/trips',client=client)[0],200)
        self.assertEqual(self.request('/api/customer/trips',client=self.public)[0],401)
        self.assertEqual(self.request('/api/customer/register','POST',{
            'name':'Otro','phone':'60002345','password':'otraClaveDEMO321','consent':True})[0],409)
        self.assertEqual(self.request('/api/logout','POST',{},client=client,csrf=csrf)[0],200)
        self.assertEqual(self.request('/api/customer/login','POST',{'phone':'60002345','password':'incorrecta'},client=client)[0],401)
        self.assertEqual(self.request('/api/customer/login','POST',{'phone':'60002345','password':'ClaveDemostracion2026!'},client=client)[0],200)

    def test_driver_photo_access_by_trip_ownership_and_status(self):
        passenger,csrf=self.new_account()
        other,ocsrf=self.new_account('60002346','Otra cuenta')
        admin,acsrf=self.login('admin')
        operator,opcsrf=self.login('operador')
        # Normal customer request is bound to account, no phone/name overrides.
        status,res=self.request('/api/requests','POST',{'name':'Suplantacion','phone':'61111111',
             'pickup':'Ubicacion de prueba','station':'Pacora','consent':True},passenger,csrf)
        self.assertEqual(status,201,res)
        tid=res['id']
        body=self.request('/api/customer/trips',client=passenger)[1]
        self.assertEqual(body['account']['phone'],'50760002345')
        self.assertIsNone(body['trips'][0].get('driver'))
        self.assertEqual(self.photo_request(7,passenger)[0],403)
        # Only admin can upload photo. CSS / browser cannot force access for other customer.
        profile={'driver_id':7,'plate':'TX-707','photo_base64':base64.b64encode(PNG).decode()}
        self.assertEqual(self.request('/api/drivers/profile','POST',profile,operator,opcsrf)[0],403)
        self.assertEqual(self.request('/api/drivers/profile','POST',profile,admin,acsrf)[0],200)
        self.assertEqual(self.photo_request(7,other)[0],403)
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,opcsrf)[0],200)
        own=self.request('/api/customer/trips',client=passenger)[1]['trips'][0]
        self.assertEqual(own['driver']['unit'],'MT-07')
        self.assertEqual(own['driver']['plate'],'TX-707')
        self.assertTrue(own['driver']['photo_url'])
        self.assertNotIn('phone',own['driver'])
        self.assertNotIn('lat',own);self.assertNotIn('lng',own)
        self.assertEqual(self.photo_request(7,other)[0],403)
        code,img,mime=self.photo_request(7,passenger)
        self.assertEqual(code,200)
        self.assertEqual(img,PNG)
        self.assertEqual(mime,'image/png')
        self.assertEqual(self.request('/api/customer/trips',client=other)[1]['trips'],[])
        # Once completed, photo access is revoked, and the customer sees history metadata.
        driver,dcsrf=self.login('conductor7')
        for action in ('accept','start','complete'):
            self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':action},driver,dcsrf)[0],200)
        self.assertEqual(self.photo_request(7,passenger)[0],403)
        after=self.request('/api/customer/trips',client=passenger)[1]['trips'][0]
        self.assertIsNone(after['driver']['photo_url'])

    def test_customer_does_not_take_over_qr_referrals_or_old_trips(self):
        driver,_=self.login('conductor7')
        tok=self.request('/api/mine',client=driver)[1]['referral_url'].split('/')[-1]
        self.assertEqual(self.request('/api/referrals/register','POST',{
            'token':tok,'name':'Referido','phone':'60002345','consent':True})[0],201)
        # Account with same unverified phone doesn't claim QR record or old trips.
        c,csrf=self.new_account()
        self.assertEqual(self.request('/api/customer/trips',client=c)[1]['trips'],[])
        self.assertEqual(self.request('/api/trips/manual','POST',{'name':'Prueba','phone':'60002345',
            'pickup':'Avenida demo','station':'Pacora','channel':'Llamada','consent':True},c,csrf)[0],403)

    def test_photo_reject_invalid_and_other_drivers(self):
        admin,acsrf=self.login('admin')
        bad={'driver_id':7,'plate':'X-1','photo_base64':base64.b64encode(b'<svg><script>bad</script></svg>').decode()}
        self.assertEqual(self.request('/api/drivers/profile','POST',bad,admin,acsrf)[0],400)
        self.assertEqual(self.photo_request(7,self.public)[0],401)
        self.assertEqual(self.request('/api/drivers/profile','POST',{'driver_id':7,'plate':'ABC-123'},admin,acsrf)[0],200)
        fleet=self.request('/api/fleet',client=admin)[1]['drivers']
        dr=next(d for d in fleet if d['id']==7)
        self.assertEqual(dr['plate'],'ABC-123')
        self.assertFalse(dr['has_photo'])

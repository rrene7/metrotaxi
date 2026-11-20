"""V0.10: API staging regression; SQLite ephemeral for tests, never user runtime."""
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update
from cloud.app import create_app, password_hash
from cloud.schema import staff, drivers, trips


class CloudFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        url = 'sqlite+pysqlite:///' + str(Path(self.tmp.name) / 'cloud_test.sqlite')
        self.app = create_app(url, test_mode=True, auto_create=True)
        self.admin = TestClient(self.app)
        self.driver = TestClient(self.app)
        self.other_driver = TestClient(self.app)
        self.customer = TestClient(self.app)
        self.other_customer = TestClient(self.app)
        with self.app.state.engine.begin() as c:
            c.execute(insert(drivers), [
                {'id': 1, 'unit': 'MT-01', 'name': 'Taxista de prueba', 'station': 'Pacora'},
                {'id': 2, 'unit': 'MT-02', 'name': 'Otro taxista', 'station': '24 de Diciembre'},
            ])
            c.execute(insert(staff), [
                {'username': 'admin', 'role': 'admin', 'driver_id': None, 'password_hash': password_hash('contraseña-prueba-admin')},
                {'username': 'conductor1', 'role': 'driver', 'driver_id': 1, 'password_hash': password_hash('contraseña-prueba-driver')},
                {'username': 'conductor2', 'role': 'driver', 'driver_id': 2, 'password_hash': password_hash('contraseña-prueba-driver')},
            ])
        self.assertEqual(self.admin.post('/api/login', json={'username':'admin','password':'contraseña-prueba-admin'}).status_code, 200)
        self.assertEqual(self.driver.post('/api/login', json={'username':'conductor1','password':'contraseña-prueba-driver'}).status_code, 200)
        self.assertEqual(self.other_driver.post('/api/login', json={'username':'conductor2','password':'contraseña-prueba-driver'}).status_code, 200)
        for c, p in ((self.customer,'6123-4567'), (self.other_customer,'6123-4568')):
            r=c.post('/api/customer/register',json={'name':'Cliente de prueba','phone':p,
                             'password':'clave-prueba-123','consent':True})
            self.assertEqual(r.status_code,201,r.text)

    def tearDown(self):
        for c in (self.admin,self.driver,self.other_driver,self.customer,self.other_customer): c.close()
        self.app.state.engine.dispose()
        self.tmp.cleanup()

    def csrf(self,client):
        return {'X-CSRF-Token':client.get('/api/me').json()['csrf']}

    def new_trip(self):
        r=self.customer.post('/api/requests',json={'station':'Pacora','pickup':'Frente al colegio',
            'destination':'Parque central','pickup_lat':9.08,'pickup_lng':-79.28,
            'pickup_accuracy_m':25,'consent':True},headers=self.csrf(self.customer))
        self.assertEqual(r.status_code,201,r.text)
        return r.json()['id']

    def assign(self,tid,did=1):
        return self.admin.post('/api/trips/assign',json={'trip_id':tid,'driver_id':did},headers=self.csrf(self.admin))

    def test_end_to_end_and_phone_privacy(self):
        tid=self.new_trip()
        self.assertEqual(self.driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.driver)).status_code,200)
        self.assertEqual(self.assign(tid).status_code,200)
        offered=self.driver.get('/api/mine').json()['trips'][0]
        self.assertEqual(offered['status'],'offered')
        self.assertNotIn('phone',str(offered))
        self.assertEqual(self.driver.post('/api/trips/action',json={'trip_id':tid,'action':'accept'},headers=self.csrf(self.driver)).status_code,200)
        gps=self.driver.post('/api/driver/location',json={'lat':9.07,'lng':-79.28,'accuracy_m':14,'consent':True},headers=self.csrf(self.driver))
        self.assertEqual(gps.status_code,200,gps.text)
        own=self.customer.get('/api/customer/trips').json()['trips'][0]
        self.assertTrue(own['driver']['confirmed'])
        self.assertEqual(own['driver']['location']['lat'],9.07)
        self.assertEqual(self.other_customer.get('/api/customer/trips').json()['trips'],[])
        self.assertEqual(self.driver.post('/api/trips/action',json={'trip_id':tid,'action':'start'},headers=self.csrf(self.driver)).status_code,200)
        self.assertEqual(self.driver.post('/api/trips/action',json={'trip_id':tid,'action':'complete'},headers=self.csrf(self.driver)).status_code,200)
        self.assertEqual(self.driver.get('/api/mine').json()['driver']['status'],'available')

    def test_csrf_stays_mandatory(self):
        self.assertEqual(self.customer.post('/api/requests',json={'pickup':'Cerca','station':'Pacora','consent':True}).status_code,403)
        self.assertEqual(self.admin.post('/api/trips/assign',json={'trip_id':1,'driver_id':1}).status_code,403)
        self.assertEqual(self.driver.post('/api/driver/status',json={'status':'available'},headers={'X-CSRF-Token':'invalid'}).status_code,403)

    def test_public_cannot_read_fleet_or_driver_phone(self):
        self.assertEqual(self.customer.get('/api/fleet').status_code,403)
        self.assertEqual(self.other_customer.get('/api/trips').status_code,403)
        self.assertEqual(self.other_driver.get('/api/fleet').status_code,403)
        self.assertEqual(self.other_driver.get('/api/mine').json()['trips'],[])

    def test_no_cross_station_and_atomic_driver_lock(self):
        tid=self.new_trip()
        self.driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.driver))
        self.other_driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.other_driver))
        self.assertEqual(self.assign(tid,2).status_code,409)
        self.assertEqual(self.assign(tid,1).status_code,200)
        tid2=self.new_trip()
        self.assertEqual(self.assign(tid2,1).status_code,409)
        self.assertEqual(self.admin.get('/api/trips').json()['trips'][0]['status'],'pending')

    def test_cancel_and_private_customer(self):
        tid=self.new_trip()
        self.assertEqual(self.other_customer.post('/api/trips/cancel',json={'trip_id':tid},headers=self.csrf(self.other_customer)).status_code,403)
        self.assertEqual(self.customer.post('/api/trips/cancel',json={'trip_id':tid},headers=self.csrf(self.customer)).status_code,200)
        self.assertEqual(self.customer.get('/api/customer/trips').json()['trips'][0]['status'],'cancelled')

    def test_gps_denies_invalid_and_inactive(self):
        b={'lat':9.0,'lng':-79.0,'accuracy_m':11,'consent':True}
        self.assertEqual(self.driver.post('/api/driver/location',json=b,headers=self.csrf(self.driver)).status_code,403)
        self.driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.driver))
        self.assertEqual(self.driver.post('/api/driver/location',json=b|{'lat':91},headers=self.csrf(self.driver)).status_code,400)
        self.assertEqual(self.driver.post('/api/driver/location',json=b|{'accuracy_m':999},headers=self.csrf(self.driver)).status_code,400)
        self.assertEqual(self.driver.post('/api/driver/location',json=b,headers=self.csrf(self.driver)).status_code,200)
        self.assertEqual(self.driver.post('/api/driver/location/stop',json={},headers=self.csrf(self.driver)).status_code,200)
        self.assertIsNone(self.driver.get('/api/mine').json()['driver']['last_location_at'])

    def test_expired_gps_not_visible(self):
        tid=self.new_trip()
        self.driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.driver))
        self.assertEqual(self.assign(tid).status_code,200)
        self.driver.post('/api/trips/action',json={'trip_id':tid,'action':'accept'},headers=self.csrf(self.driver))
        with self.app.state.engine.begin() as c:
            c.execute(update(drivers).where(drivers.c.id==1).values(lat=9.0,lng=-79.0,
              location_source='device',location_updated_at=datetime.now(timezone.utc)-timedelta(minutes=10)))
        own=self.customer.get('/api/customer/trips').json()['trips'][0]
        self.assertNotIn('location',own['driver'])

    def test_session_db_and_logout(self):
        self.assertTrue(self.customer.get('/api/me').json()['authenticated'])
        self.assertEqual(self.customer.post('/api/logout',json={},headers=self.csrf(self.customer)).status_code,200)
        self.assertFalse(self.customer.get('/api/me').json()['authenticated'])

    def test_manual_call_entry_requires_operator_and_central_preserves_phone(self):
        body={'name':'Pasajero llamada de prueba','phone':'6000-9012','station':'Pacora',
              'pickup':'Punto telefónico de prueba','destination':'Destino ficticio'}
        self.assertEqual(self.customer.post('/api/trips/manual',json=body,headers=self.csrf(self.customer)).status_code,403)
        r=self.admin.post('/api/trips/manual',json=body,headers=self.csrf(self.admin))
        self.assertEqual(r.status_code,201,r.text)
        t=self.admin.get('/api/trips').json()['trips'][0]
        self.assertEqual(t['phone'],'50760009012')
        self.assertEqual(t['channel'],'Central - llamada/WhatsApp')
        self.assertEqual(self.driver.get('/api/mine').json()['trips'],[])

    def test_offer_expiration_requeues_without_giving_client_other_position(self):
        tid=self.new_trip()
        self.driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.driver))
        self.assertEqual(self.assign(tid).status_code,200)
        with self.app.state.engine.begin() as c:
            c.execute(update(trips).where(trips.c.id==tid).values(
              offer_expires_at=datetime.now(timezone.utc)-timedelta(seconds=4)))
        t=self.admin.get('/api/trips').json()['trips'][0]
        self.assertEqual(t['status'],'pending')
        self.assertIsNone(t['driver_id'])
        self.assertEqual(self.driver.get('/api/mine').json()['driver']['status'],'available')

    def test_origin_rejected(self):
        r=self.driver.post('/api/driver/status',json={'status':'available'},headers=self.csrf(self.driver)|{'Origin':'https://malicious.invalid'})
        self.assertEqual(r.status_code,403)


if __name__=='__main__':unittest.main()

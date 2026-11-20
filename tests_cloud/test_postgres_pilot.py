"""Real PostgreSQL integration only on disposable localhost CI DB metrotaxi_test."""
import os
import unittest
from urllib.parse import urlparse
from fastapi.testclient import TestClient
from sqlalchemy import insert
from cloud.app import create_app, password_hash
from cloud.schema import metadata, drivers, staff
from cloud.pilot_tools import normalize_postgres_url


class PostgreSQLPilotIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=os.environ.get('METRO_TEST_POSTGRES_URL','')
        if not source:
            raise unittest.SkipTest('Pruebas PostgreSQL reales requieren servicio temporal de CI')
        url=normalize_postgres_url(source)
        parsed=urlparse(url)
        if parsed.hostname not in ('127.0.0.1','localhost') or parsed.path!='/metrotaxi_test':
            raise RuntimeError('Prohibido usar PostgreSQL remoto o base no temporal para esta prueba')
        cls.app=create_app(database_url=url,test_mode=True,auto_create=True)
        cls.engine=cls.app.state.engine

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'engine'):
            metadata.drop_all(cls.engine)
            cls.engine.dispose()

    def test_real_postgres_dispatch_and_gps(self):
        with self.engine.begin() as c:
            driver_id=c.execute(insert(drivers).values(unit='CI-PG-01',name='Conductor ficticio',station='Pacora')).inserted_primary_key[0]
            c.execute(insert(staff),[
                {'username':'ci_pg_admin','password_hash':password_hash('password-ficticia-admin'),'role':'admin','driver_id':None},
                {'username':'ci_pg_driver','password_hash':password_hash('password-ficticia-driver'),'role':'driver','driver_id':driver_id},
            ])
        with TestClient(self.app) as admin,TestClient(self.app) as driver,TestClient(self.app) as passenger:
            self.assertEqual(admin.post('/api/login',json={'username':'ci_pg_admin','password':'password-ficticia-admin'}).status_code,200)
            self.assertEqual(driver.post('/api/login',json={'username':'ci_pg_driver','password':'password-ficticia-driver'}).status_code,200)
            self.assertEqual(passenger.post('/api/customer/register',json={'name':'Cliente ficticio','phone':'6123-0001','password':'password-ficticia-cliente','consent':True}).status_code,201)
            def csrf(c):return {'X-CSRF-Token':c.get('/api/me').json()['csrf']}
            self.assertEqual(driver.post('/api/driver/status',json={'status':'available'},headers=csrf(driver)).status_code,200)
            trip=passenger.post('/api/requests',json={'station':'Pacora','pickup':'Punto ficticio','destination':'Destino ficticio','pickup_lat':9.08,'pickup_lng':-79.28,'dest_lat':9.09,'dest_lng':-79.30,'consent':True},headers=csrf(passenger))
            self.assertEqual(trip.status_code,201,trip.text)
            tid=trip.json()['id']
            self.assertEqual(admin.post('/api/trips/assign',json={'trip_id':tid,'driver_id':driver_id},headers=csrf(admin)).status_code,200)
            self.assertEqual(driver.post('/api/trips/action',json={'trip_id':tid,'action':'accept'},headers=csrf(driver)).status_code,200)
            sent=driver.post('/api/driver/location',json={'lat':9.081,'lng':-79.283,'accuracy_m':9,'consent':True},headers=csrf(driver))
            self.assertEqual(sent.status_code,200,sent.text)
            tripinfo=passenger.get('/api/customer/trips').json()['trips'][0]
            self.assertTrue(tripinfo['driver']['confirmed'])
            self.assertEqual(tripinfo['driver']['location']['lat'],9.081)
            self.assertEqual(driver.post('/api/trips/action',json={'trip_id':tid,'action':'start'},headers=csrf(driver)).status_code,409)
            driver.post('/api/driver/location',json={'lat':9.08,'lng':-79.28,'accuracy_m':9,'consent':True},headers=csrf(driver))
            self.assertEqual(driver.post('/api/trips/action',json={'trip_id':tid,'action':'start'},headers=csrf(driver)).status_code,200)
            self.assertEqual(driver.post('/api/trips/action',json={'trip_id':tid,'action':'complete'},headers=csrf(driver)).status_code,409)
            driver.post('/api/driver/location',json={'lat':9.09,'lng':-79.30,'accuracy_m':9,'consent':True},headers=csrf(driver))
            self.assertEqual(driver.post('/api/trips/action',json={'trip_id':tid,'action':'complete'},headers=csrf(driver)).status_code,200)
            self.assertEqual(admin.get('/api/trips').json()['trips'][0]['status'],'done')

if __name__=='__main__':unittest.main()

"""Version 0.7 HTTP integration tests: vehicle records, shifts, GPS privacy and dispatch."""
import unittest
from datetime import datetime, timedelta, timezone
import test_mvp as legacy

class OpsTests(unittest.TestCase):
    setUp=legacy.ApiMVPTests.setUp
    tearDown=legacy.ApiMVPTests.tearDown
    client=legacy.ApiMVPTests.client
    request=legacy.ApiMVPTests.request
    login=legacy.ApiMVPTests.login
    newtrip=legacy.ApiMVPTests.newtrip

    def account(self,phone='60004111'):
        user=self.client()
        r=self.request('/api/customer/register','POST',{'name':'Cliente de prueba','phone':phone,
            'password':'DemostracionMetro2026!','consent':True},user)
        self.assertEqual(r[0],201,r)
        return user,self.request('/api/me',client=user)[1]['csrf']

    def own_trip(self,user,csrf):
        code,r=self.request('/api/requests','POST',{'name':'No debe usarse','phone':'60000000',
            'pickup':'Punto de prueba explícito','station':'Pacora','consent':True},user,csrf)
        self.assertEqual(code,201,r)
        return r['id']

    def test_vehicle_record_only_admin_and_owner_sees_limited_fields(self):
        admin,a=self.login('admin');operator,o=self.login('operador');driver,d=self.login('conductor7')
        data={'driver_id':7,'plate':'TXY-707','vehicle_make':'Toyota','vehicle_model':'Yaris',
              'vehicle_color':'Blanco','vehicle_year':'2021'}
        self.assertEqual(self.request('/api/drivers/profile','POST',data,operator,o)[0],403)
        self.assertEqual(self.request('/api/drivers/profile','POST',data,admin,a)[0],200)
        bad={**data,'vehicle_year':2049}
        self.assertEqual(self.request('/api/drivers/profile','POST',bad,admin,a)[0],400)
        fleet=self.request('/api/fleet',client=admin)[1]['drivers']
        record=next(d for d in fleet if d['id']==7)
        self.assertEqual(record['vehicle_model'],'Yaris')
        self.assertEqual(record['vehicle_year'],2021)
        self.assertEqual(self.request('/api/fleet',client=driver)[0],403)

    def test_shift_start_end_and_forbidden_history(self):
        driver,d=self.login('conductor7');admin,a=self.login('admin')
        self.assertEqual(self.request('/api/shifts',client=driver)[0],403)
        self.assertEqual(self.request('/api/shifts')[0],401)
        self.assertEqual(self.request('/api/driver/status','POST',{'status':'available'},driver,d)[0],200)
        self.assertTrue(self.request('/api/mine',client=driver)[1]['active_shift_since'])
        history=self.request('/api/shifts',client=admin)[1]['shifts']
        self.assertEqual(history[0]['unit'],'MT-07')
        self.assertIsNone(history[0]['ended_at'])
        self.assertEqual(self.request('/api/driver/status','POST',{'status':'off'},driver,d)[0],200)
        history=self.request('/api/shifts',client=admin)[1]['shifts']
        self.assertIsNotNone(history[0]['ended_at'])
        self.assertIsNone(self.request('/api/mine',client=driver)[1]['active_shift_since'])

    def test_gps_must_be_consented_and_driver_active(self):
        driver,d=self.login('conductor7');other,o=self.login('conductor1')
        admin,a=self.login('admin')
        payload={'lat':9.087,'lng':-79.287,'accuracy_m':15,'consent':True}
        self.assertEqual(self.request('/api/driver/location','POST',{**payload,'consent':False},driver,d)[0],400)
        self.assertEqual(self.request('/api/driver/location','POST',{**payload,'lng':-99},driver,d)[0],400)
        self.assertEqual(self.request('/api/driver/location','POST',{**payload,'accuracy_m':-7},driver,d)[0],400)
        self.assertEqual(self.request('/api/driver/location','POST',payload,driver)[0],403)
        self.assertEqual(self.request('/api/driver/location','POST',payload,driver,d)[0],200)
        fleet=self.request('/api/fleet',client=admin)[1]['drivers']
        self.assertFalse(next(x for x in fleet if x['id']==7)['simulated'])
        self.assertEqual(self.request('/api/driver/location/stop','POST',{},driver,d)[0],200)
        row=next(x for x in self.request('/api/fleet',client=admin)[1]['drivers'] if x['id']==7)
        self.assertIsNone(row['lat']);self.assertEqual(row['location_source'],'none')
        self.assertEqual(self.request('/api/driver/status','POST',{'status':'off'},driver,d)[0],200)
        self.assertEqual(self.request('/api/driver/location','POST',payload,driver,d)[0],409)
        self.assertEqual(self.request('/api/driver/location/stop','POST',{},self.public)[0],401)

    def test_private_gps_only_after_acceptance_then_expires(self):
        import server
        passenger,c=self.account();other,_=self.account('60004112')
        operator,o=self.login('operador');driver,d=self.login('conductor7')
        tid=self.own_trip(passenger,c)
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,o)[0],200)
        gps={'lat':9.087,'lng':-79.287,'accuracy_m':15,'consent':True}
        self.assertEqual(self.request('/api/driver/location','POST',gps,driver,d)[0],200)
        offered=self.request('/api/customer/trips',client=passenger)[1]['trips'][0]
        self.assertFalse(offered['driver']['confirmed'])
        self.assertNotIn('location',offered['driver'])
        self.assertEqual(self.request('/api/customer/trips',client=other)[1]['trips'],[])
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'accept'},driver,d)[0],200)
        accepted=self.request('/api/customer/trips',client=passenger)[1]['trips'][0]
        self.assertTrue(accepted['driver']['confirmed'])
        self.assertEqual(accepted['driver']['location']['lat'],9.087)
        self.assertNotIn('phone',str(accepted['driver']))
        # Only recent GPS is visible. The server must not present stale positions as live.
        old=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(timespec='seconds')
        with server.connect() as db:db.execute('UPDATE drivers SET updated_at=? WHERE id=7',(old,))
        expired=self.request('/api/customer/trips',client=passenger)[1]['trips'][0]
        self.assertNotIn('location',expired['driver'])
        self.assertIn('location_notice',expired['driver'])
        self.assertEqual(self.request('/api/driver/location/stop','POST',{},driver,d)[0],200)

    def test_cancellation_authority_and_driver_release(self):
        passenger,c=self.account();other,x=self.account('60004113')
        operator,o=self.login('operador');driver,d=self.login('conductor7')
        tid=self.own_trip(passenger,c)
        self.assertEqual(self.request('/api/trips/cancel','POST',{'trip_id':tid},other,x)[0],404)
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,o)[0],200)
        self.assertEqual(self.request('/api/trips/cancel','POST',{'trip_id':tid,'reason':'Cliente desistió'},passenger,c)[0],200)
        self.assertEqual(self.request('/api/mine',client=driver)[1]['driver']['status'],'available')
        t2=self.own_trip(passenger,c)
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':t2,'driver_id':7},operator,o)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':t2,'action':'accept'},driver,d)[0],200)
        self.assertEqual(self.request('/api/trips/cancel','POST',{'trip_id':t2},passenger,c)[0],403)
        self.assertEqual(self.request('/api/trips/cancel','POST',{'trip_id':t2,'reason':'Soporte central'},operator,o)[0],200)
        self.assertEqual(self.request('/api/mine',client=driver)[1]['driver']['status'],'available')
        self.assertEqual(self.request('/api/trips/cancel','POST',{'trip_id':t2},operator,o)[0],409)

    def test_expired_offer_returns_to_central_and_cannot_accept(self):
        import server
        _,res=self.newtrip();tid=res['id'];operator,o=self.login('operador');driver,d=self.login('conductor7')
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,o)[0],200)
        with server.connect() as db:db.execute('UPDATE trips SET offer_expires_at=? WHERE id=?',('2000-01-01T00:00:00+00:00',tid))
        trip=next(t for t in self.request('/api/trips',client=operator)[1]['trips'] if t['id']==tid)
        self.assertEqual(trip['status'],'pending')
        self.assertIsNone(trip['driver_id'])
        self.assertEqual(self.request('/api/mine',client=driver)[1]['driver']['status'],'available')
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'accept'},driver,d)[0],403)

if __name__=='__main__':unittest.main()

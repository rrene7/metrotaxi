"""Metro Taxi v0.8 — optional proximity recommendations and unattended dispatch."""
from datetime import datetime, timedelta, timezone
import unittest
import test_mvp as legacy
import server

class DispatchTests(unittest.TestCase):
    setUp=legacy.ApiMVPTests.setUp
    tearDown=legacy.ApiMVPTests.tearDown
    client=legacy.ApiMVPTests.client
    request=legacy.ApiMVPTests.request
    login=legacy.ApiMVPTests.login

    def new_geo_trip(self,coords=True):
        payload={'name':'Cliente de prueba','phone':'60000000','pickup':'Lugar GPS elegido','station':'Pacora',
                 'consent':True}
        if coords:payload.update({'pickup_lat':9.087,'pickup_lng':-79.287})
        code,data=self.request('/api/requests','POST',payload)
        self.assertEqual(code,201,data)
        return data['id']

    def enable_gps(self,unit='conductor7',lat=9.088,lng=-79.286):
        client,csrf=self.login(unit)
        code,res=self.request('/api/driver/location','POST',{'lat':lat,'lng':lng,'accuracy_m':12,'consent':True},client,csrf)
        self.assertEqual(code,200,res)
        return client,csrf

    def old(self,tid):
        old=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(timespec='seconds')
        with server.connect() as db:db.execute('UPDATE trips SET created_at=? WHERE id=?',(old,tid))

    def test_mode_default_manual_and_only_admin_may_change(self):
        admin,a=self.login('admin');operator,o=self.login('operador');driver,d=self.login('conductor7')
        self.assertEqual(self.request('/api/dispatch/settings')[0],401)
        self.assertEqual(self.request('/api/dispatch/settings',client=driver)[0],403)
        self.assertEqual(self.request('/api/dispatch/settings',client=operator)[1]['mode'],'manual')
        self.assertEqual(self.request('/api/dispatch/settings','POST',{'mode':'auto_after_120s'},operator,o)[0],403)
        self.assertEqual(self.request('/api/dispatch/settings','POST',{'mode':'invalid'},admin,a)[0],400)
        self.assertEqual(self.request('/api/dispatch/settings','POST',{'mode':'auto_after_120s'},admin,a)[0],200)
        self.assertEqual(self.request('/api/dispatch/settings',client=admin)[1]['mode'],'auto_after_120s')
        self.assertEqual(self.request('/api/dispatch/settings','POST',{'mode':'manual'},admin,a)[0],200)

    def test_suggestions_only_from_fresh_real_device_gps_same_station(self):
        tid=self.new_geo_trip();operator,_=self.login('operador')
        self.assertEqual(self.request('/api/dispatch/suggest',client=operator)[0],404)
        self.assertEqual(self.request('/api/dispatch/suggest?trip_id='+str(tid))[0],401)
        self.assertEqual(self.request('/api/dispatch/suggest?trip_id='+str(tid),client=operator)[1]['candidates'],[])
        self.enable_gps('conductor7')
        self.enable_gps('conductor1',9.088,-79.286) # belongs to 24 de Diciembre
        suggestions=self.request('/api/dispatch/suggest?trip_id='+str(tid),client=operator)[1]['candidates']
        self.assertEqual(len(suggestions),1)
        self.assertEqual(suggestions[0]['unit'],'MT-07')
        self.assertGreaterEqual(suggestions[0]['straight_line_km'],0)
        self.assertNotIn('phone',str(suggestions))

    def test_auto_dispatch_after_two_minutes_never_with_simulated_or_without_pickup(self):
        tid=self.new_geo_trip();no_coords=self.new_geo_trip(False)
        self.old(tid);self.old(no_coords)
        admin,a=self.login('admin')
        self.assertEqual(self.request('/api/dispatch/settings','POST',{'mode':'auto_after_120s'},admin,a)[0],200)
        # All demo drivers are simulated, hence no automatic assignment.
        trips=self.request('/api/trips',client=admin)[1]['trips']
        self.assertEqual(next(t['status'] for t in trips if t['id']==tid),'pending')
        self.enable_gps('conductor7')
        trips=self.request('/api/trips',client=admin)[1]['trips']
        assigned=next(t for t in trips if t['id']==tid)
        self.assertEqual(assigned['status'],'offered')
        self.assertEqual(assigned['driver_id'],7)
        self.assertEqual(next(t['status'] for t in trips if t['id']==no_coords),'pending')
        self.assertEqual(self.request('/api/mine',client=self.login('conductor7')[0])[1]['driver']['status'],'busy')

    def test_expiry_does_not_reoffer_to_same_driver_in_auto_mode(self):
        tid=self.new_geo_trip();self.old(tid)
        admin,a=self.login('admin');self.enable_gps()
        self.request('/api/dispatch/settings','POST',{'mode':'auto_after_120s'},admin,a)
        first=next(t for t in self.request('/api/trips',client=admin)[1]['trips'] if t['id']==tid)
        self.assertEqual(first['driver_id'],7)
        with server.connect() as db:db.execute('UPDATE trips SET offer_expires_at=? WHERE id=?',('2000-01-01T00:00:00+00:00',tid))
        result=next(t for t in self.request('/api/trips',client=admin)[1]['trips'] if t['id']==tid)
        self.assertEqual(result['status'],'pending')
        self.assertIsNone(result['driver_id'])
        # No repeated offering to the exact same driver; the central can intervene.
        with server.connect() as db:
            history=db.execute('SELECT driver_id,mode FROM trip_offer_history WHERE trip_id=?',(tid,)).fetchall()
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['mode'],'auto')

if __name__=='__main__':unittest.main()

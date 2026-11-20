"""Metro Taxi v0.8.3 — passenger pickup coordinates available only to assigned driver."""
import unittest
import test_mvp as legacy

class NavIntegrationTests(unittest.TestCase):
    setUp=legacy.ApiMVPTests.setUp
    tearDown=legacy.ApiMVPTests.tearDown
    client=legacy.ApiMVPTests.client
    request=legacy.ApiMVPTests.request
    login=legacy.ApiMVPTests.login

    def test_accepted_trip_has_passenger_gps_for_assigned_driver_only(self):
        status,trip=self.request('/api/requests','POST',{
            'name':'Pasajero de prueba','phone':'60002222','station':'Pacora',
            'pickup':'Ubicación actual enviada por GPS','reference':'Puerta principal',
            'pickup_lat':9.0876543,'pickup_lng':-79.2875432,'pickup_accuracy_m':23,
            'consent':True})
        self.assertEqual(status,201,trip)
        operator,ocsrf=self.login('operador')
        driver,dcsrf=self.login('conductor7')
        stranger,_=self.login('conductor1')
        tid=trip['id']
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,ocsrf)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'accept'},driver,dcsrf)[0],200)
        response=self.request('/api/mine',client=driver)[1]
        detail=next(t for t in response['trips'] if t['id']==tid)
        self.assertEqual((detail['pickup_lat'],detail['pickup_lng']),(9.0876543,-79.2875432))
        self.assertEqual(detail['status'],'accepted')
        self.assertNotIn('phone',detail)
        self.assertTrue(all(t['id']!=tid for t in self.request('/api/mine',client=stranger)[1]['trips']))
        code,js=self.request('/static/navigation.js',client=driver)
        self.assertEqual(code,200)
        self.assertIn(b'waze.com/ul',js)
        code,html=self.request('/conductor',client=driver)
        self.assertEqual(code,200)
        self.assertIn(b'/static/driver.js',html)
        self.assertNotIn(b'<script src="/static/navigation.js"></script>',html)
        code,js=self.request('/static/driver.js',client=driver)
        self.assertEqual(code,200)
        self.assertIn(b'waze.com/ul',js)

    def test_address_without_coords_remains_null(self):
        status,trip=self.request('/api/requests','POST',{
            'name':'Pasajero demo','phone':'60002221','station':'Pacora',
            'pickup':'Una direccion sin GPS','consent':True})
        self.assertEqual(status,201,trip)
        operator,ocsrf=self.login('operador')
        driver,dcsrf=self.login('conductor7')
        tid=trip['id']
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,ocsrf)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'accept'},driver,dcsrf)[0],200)
        d=next(t for t in self.request('/api/mine',client=driver)[1]['trips'] if t['id']==tid)
        self.assertIsNone(d['pickup_lat']);self.assertIsNone(d['pickup_lng'])

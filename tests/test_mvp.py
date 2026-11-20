"""API integration tests against actual local HTTP server, stdlib only."""
import http.cookiejar
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class ApiMVPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        server.RUN=Path(self.temp.name)
        server.DB_PATH=server.RUN/'metro_taxi_demo.sqlite3'
        server.SESSIONS.clear()
        server.init_database()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.origin='http://127.0.0.1:'+str(self.server.server_address[1])
        self.public=self.client()
        txt=(server.RUN/'credenciales_iniciales.txt').read_text()
        self.passwords={line.split(' (')[0]:line.split(' -> ')[1].strip() for line in txt.splitlines() if ' -> ' in line}
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
        self.temp.cleanup()
    def client(self):return build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(self,path,method='GET',data=None,client=None,csrf=None):
        client=client or self.public
        headers={}
        if data is not None:headers['Content-Type']='application/json'
        if csrf:headers['X-CSRF-Token']=csrf
        req=Request(self.origin+path,headers=headers,data=json.dumps(data).encode() if data is not None else None,method=method)
        try:
            r=client.open(req,timeout=5)
            return r.status,json.loads(r.read()) if path.startswith('/api/') and not path.endswith('.svg') else r.read()
        except HTTPError as e:
            return e.code,json.loads(e.read()) if path.startswith('/api/') else e.read()
    def login(self,user):
        c=self.client()
        status,body=self.request('/api/login','POST',{'username':user,'password':self.passwords[user]},c)
        self.assertEqual(status,200,body)
        status,me=self.request('/api/me',client=c)
        self.assertEqual(status,200)
        return c,me['csrf']
    def newtrip(self):
        return self.request('/api/requests','POST',{
            'name':'Cliente ficticio','phone':'00000000','station':'Pacora',
            'pickup':'Frente a lugar de prueba','destination':'Otra prueba',
            'province':'Panamá','district':'Panamá','corregimiento':'Pacora',
            'reference':'DEMO, no es real','consent':True})

    def test_qr_registration_central_owns_client_and_driver_sees_count_only(self):
        driver,csrf=self.login('conductor7')
        status,mine=self.request('/api/mine',client=driver)
        self.assertEqual(status,200)
        link=mine['referral_url']
        token=link.rsplit('/',1)[-1]
        self.assertTrue(link.endswith('/registro/'+token))
        status,public=self.request('/api/referral/'+token)
        self.assertEqual(status,200,public)
        self.assertEqual(public['unit'],'MT-07')
        self.assertNotIn('phone',public)
        self.assertEqual(self.request('/api/referrals')[0],401)
        self.assertEqual(self.request('/api/referrals',client=driver)[0],403)
        data={'token':token,'name':'Cliente de QR','phone':'6000-1111','consent':True,'marketing_opt_in':False}
        status,answer=self.request('/api/referrals/register','POST',data)
        self.assertEqual(status,201,answer)
        self.assertFalse(answer['phone_verified'])
        status,mine=self.request('/api/mine',client=driver)
        self.assertEqual(mine['referral_count'],1)
        self.assertNotIn('60001111',str(mine))
        admin,_=self.login('admin')
        status,report=self.request('/api/referrals',client=admin)
        self.assertEqual(status,200)
        self.assertEqual(report['customers'][0]['unit'],'MT-07')
        self.assertEqual(report['customers'][0]['phone'],'50760001111')
        self.assertEqual(report['customers'][0]['phone_verified'],0)
        self.assertEqual(report['customers'][0]['marketing_opt_in'],0)
        self.assertEqual(self.request('/api/trips',client=admin)[1]['trips'].__len__(),2)

    def test_duplicate_phone_never_reassigns_customer_to_second_driver(self):
        driver7,_=self.login('conductor7')
        driver1,_=self.login('conductor1')
        tok7=self.request('/api/mine',client=driver7)[1]['referral_url'].split('/')[-1]
        tok1=self.request('/api/mine',client=driver1)[1]['referral_url'].split('/')[-1]
        first={'token':tok7,'name':'Primer contacto','phone':'+507 6500-2222','consent':True}
        second={'token':tok1,'name':'No cambia origen','phone':'6500-2222','consent':True}
        self.assertEqual(self.request('/api/referrals/register','POST',first)[0],201)
        self.assertEqual(self.request('/api/referrals/register','POST',second)[0],201)
        admin,_=self.login('admin')
        report=self.request('/api/referrals',client=admin)[1]
        self.assertEqual(len(report['customers']),1)
        self.assertEqual(report['customers'][0]['unit'],'MT-07')
        self.assertEqual(self.request('/api/mine',client=driver1)[1]['referral_count'],0)
        self.assertEqual(self.request('/api/mine',client=driver7)[1]['referral_count'],1)

    def test_qr_revocation_and_suspension(self):
        driver7,_=self.login('conductor7')
        admin,acsrf=self.login('admin')
        operator,ocsrf=self.login('operador')
        old=self.request('/api/mine',client=driver7)[1]['referral_url'].split('/')[-1]
        self.assertEqual(self.request('/api/referrals/rotate','POST',{'driver_id':7},operator,ocsrf)[0],403)
        self.assertEqual(self.request('/api/referrals/rotate','POST',{'driver_id':7},admin,acsrf)[0],200)
        self.assertEqual(self.request('/api/referral/'+old)[0],404)
        new=self.request('/api/mine',client=driver7)[1]['referral_url'].split('/')[-1]
        self.assertNotEqual(old,new)
        self.assertEqual(self.request('/api/referral/'+new)[0],200)
        self.assertEqual(self.request('/api/drivers/suspend','POST',{'driver_id':7,'suspended':True},admin,acsrf)[0],200)
        self.assertEqual(self.request('/api/referral/'+new)[0],404)
        self.assertIsNone(self.request('/api/mine',client=driver7)[1]['referral_url'])

    def test_qr_svg_authorized_and_public_consent_required(self):
        self.assertEqual(self.request('/api/referral/qr.svg')[0],401)
        operator,_=self.login('operador')
        self.assertEqual(self.request('/api/referral/qr.svg',client=operator)[0],403)
        driver,_=self.login('conductor1')
        status,raw=self.request('/api/referral/qr.svg',client=driver)
        self.assertEqual(status,200)
        self.assertIn(b'<svg',raw)
        tok=self.request('/api/mine',client=driver)[1]['referral_url'].split('/')[-1]
        payload={'token':tok,'name':'Pasajero','phone':'60001111'}
        self.assertEqual(self.request('/api/referrals/register','POST',payload)[0],400)
        payload['consent']=True
        payload['phone']='NO ES TELEFONO'
        self.assertEqual(self.request('/api/referrals/register','POST',payload)[0],400)
        self.assertEqual(self.request('/registro/'+tok)[0],200)

    def test_public_private_fleet_and_gps_not_invented(self):
        self.assertEqual(self.request('/api/fleet')[0],401)
        self.assertEqual(self.request('/api/trips')[0],401)
        self.assertEqual(self.request('/api/messages')[0],401)
        self.assertEqual(self.request('/api/mine')[0],401)
        self.assertEqual(self.request('/api/catalog')[0],200)
        code,r=self.newtrip();self.assertEqual(code,201,r)
        c,csrf=self.login('operador')
        code,t=self.request('/api/trips',client=c);self.assertEqual(code,200)
        record=next(ti for ti in t['trips'] if ti['id']==r['id'])
        self.assertIsNone(record['pickup_lat'])
        self.assertIsNone(record['pickup_lng'])
        self.assertIsNone(record['dest_lat'])
    def test_role_permissions_and_assignment_flow(self):
        _,r=self.newtrip();tid=r['id']
        operator,ocsrf=self.login('operador')
        driver1,dcsrf=self.login('conductor1')
        driver7,d7csrf=self.login('conductor7')
        self.assertEqual(self.request('/api/fleet',client=operator)[0],200)
        self.assertEqual(self.request('/api/fleet',client=driver1)[0],403)
        self.assertEqual(self.request('/api/drivers/suspend','POST',{'driver_id':1,'suspended':True},operator,ocsrf)[0],403)
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':1},operator)[0],403) # CSRF missing
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,ocsrf)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'accept'},driver1,dcsrf)[0],403)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'accept'},driver7,d7csrf)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'start'},driver7,d7csrf)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'complete'},driver7,d7csrf)[0],200)
        code,fleet=self.request('/api/fleet',client=operator)
        dr7=next(d for d in fleet['drivers'] if d['id']==7)
        self.assertEqual(dr7['status'],'available');self.assertEqual(dr7['completed'],1)
    def test_explicit_points_and_unknown_territory(self):
        code,r=self.request('/api/requests','POST',{
            'name':'Usuario prueba','phone':'000','pickup':'un lugar que NO se geocodifica','station':'Pacora',
            'province':'Panamá','district':'Distrito ficticio','consent':True})
        self.assertEqual(code,400)
        code,r=self.request('/api/requests','POST',{
            'name':'Usuario prueba','phone':'000','pickup':'un lugar que NO se geocodifica','station':'Pacora',
            'province':'Panamá','district':'Distrito ficticio',
            'location_pending':'Distrito ficticio (pendiente)','consent':True})
        self.assertEqual(code,201)
        operator,csrf=self.login('operador')
        code,_=self.request('/api/trips/points','POST',{'trip_id':r['id'],'pickup_lat':9.12,'pickup_lng':-79.3,
                   'dest_lat':9.20,'dest_lng':-79.39},operator,csrf)
        self.assertEqual(code,200)
        _,data=self.request('/api/trips',client=operator)
        trip=next(x for x in data['trips'] if x['id']==r['id'])
        self.assertEqual(trip['pickup_lat'],9.12)
        self.assertEqual(trip['dest_lng'],-79.39)
        self.assertIn('pendiente',trip['location_pending'])
    def test_internal_chat_is_private(self):
        c,r=self.request('/api/contact','POST',{'name':'DEMO','phone':'00000','message':'¿Hay taxis en Pacora?'})
        self.assertEqual(c,201)
        self.assertEqual(self.request('/api/thread/'+'0'*64)[0],404)
        c,thread=self.request('/api/thread/'+r['token'])
        self.assertEqual(c,200);self.assertEqual(thread['thread']['response'],'')
        operator,csrf=self.login('operador')
        c,r2=self.request('/api/messages/'+str(r['id'])+'/reply','POST',{'response':'Sí (prueba)'},operator,csrf)
        self.assertEqual(c,200,r2)
        _,thread=self.request('/api/thread/'+r['token']);self.assertEqual(thread['thread']['response'],'Sí (prueba)')
    def test_admin_only_suspension_and_rejection(self):
        admin,csrf=self.login('admin')
        operator,cs2=self.login('operador')
        self.assertEqual(self.request('/api/drivers/suspend','POST',{'driver_id':1,'suspended':True},admin,csrf)[0],200)
        self.assertEqual(self.request('/api/drivers/suspend','POST',{'driver_id':1,'suspended':False},operator,cs2)[0],403)
        self.assertEqual(self.request('/api/drivers/suspend','POST',{'driver_id':1,'suspended':False},admin,csrf)[0],200)

    def test_manual_call_recording_driver_cannot_see_passenger_phone(self):
        # Only central can record calls; driver must not gain customer's direct phone.
        req={'name':'Cliente de prueba','phone':'6000-TEST','pickup':'Entrada de prueba',
             'station':'Pacora','channel':'Llamada','consent':True,'reference':'Junto a portón'}
        self.assertEqual(self.request('/api/trips/manual','POST',req)[0],401)
        operator,ocsrf=self.login('operador')
        code,res=self.request('/api/trips/manual','POST',req,operator,ocsrf)
        self.assertEqual(code,201,res)
        tid=res['id']
        code,res=self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,ocsrf)
        self.assertEqual(code,200,res)
        driver,csrf=self.login('conductor7')
        _,mine=self.request('/api/mine',client=driver)
        chosen=next(t for t in mine['trips'] if t['id']==tid)
        self.assertEqual(chosen['channel'],'Llamada')
        self.assertNotIn('phone',chosen)
        self.assertIn('name',chosen)
        self.assertEqual(self.request('/api/trips/manual','POST',req,driver,csrf)[0],403)
        self.assertEqual(self.request('/api/stats',client=driver)[0],403)

    def test_rejection_reason_requeue_and_stats(self):
        _,r=self.newtrip();tid=r['id']
        operator,ocsrf=self.login('operador')
        driver,csrf=self.login('conductor7')
        self.assertEqual(self.request('/api/trips/assign','POST',{'trip_id':tid,'driver_id':7},operator,ocsrf)[0],200)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'reject'},driver,csrf)[0],400)
        self.assertEqual(self.request('/api/trips/action','POST',{'trip_id':tid,'action':'reject','reason':'Estoy fuera de zona'},driver,csrf)[0],200)
        _,alltrips=self.request('/api/trips',client=operator)
        trip=next(t for t in alltrips['trips'] if t['id']==tid)
        self.assertEqual(trip['status'],'pending')
        self.assertIsNone(trip['driver_id'])
        _,stats=self.request('/api/stats',client=operator)
        driver7=next(d for d in stats['by_driver'] if d['unit']=='MT-07')
        self.assertEqual(driver7['rejected_count'],1)
        _,fleet=self.request('/api/fleet',client=operator)
        self.assertEqual(next(d for d in fleet['drivers'] if d['unit']=='MT-07')['status'],'available')

    def test_admin_registers_driver_account_with_offline_status(self):
        operator,ocsrf=self.login('operador')
        admin,acsrf=self.login('admin')
        record={'unit':'MT-13','name':'Unidad de prueba 13','station':'Pacora','username':'conductor13'}
        self.assertEqual(self.request('/api/drivers/create','POST',record,operator,ocsrf)[0],403)
        status,result=self.request('/api/drivers/create','POST',record,admin,acsrf)
        self.assertEqual(status,201,result)
        self.assertGreaterEqual(len(result['temporary_password']),16)
        self.assertEqual(self.request('/api/drivers/create','POST',record,admin,acsrf)[0],409)
        _,fleet=self.request('/api/fleet',client=admin)
        created=next(d for d in fleet['drivers'] if d['unit']=='MT-13')
        self.assertEqual(created['status'],'off')
        self.assertIsNone(created['lat'])
        self.assertIsNone(created['lng'])
        c=self.client()
        login_code,_=self.request('/api/login','POST',{'username':'conductor13','password':result['temporary_password']},c)
        self.assertEqual(login_code,200)
        self.assertEqual(self.request('/api/mine',client=c)[0],200)
        self.assertEqual(self.request('/api/stats',client=c)[0],403)

    def test_manual_tariff_and_incidents(self):
        _,r=self.newtrip();tid=r['id']
        operator,ocsrf=self.login('operador')
        admin,acsrf=self.login('admin')
        self.assertEqual(self.request('/api/trips/price','POST',{'trip_id':tid,'price':-2},operator,ocsrf)[0],400)
        code,res=self.request('/api/trips/price','POST',{'trip_id':tid,'price':1.50},operator,ocsrf)
        self.assertEqual(code,200,res)
        self.assertEqual(res['price'],1.5)
        entry={'driver_id':7,'trip_id':tid,'type':'queja','details':'La unidad llegó demasiado tarde al punto de recogida'}
        self.assertEqual(self.request('/api/incidents','POST',entry)[0],401)
        code,res=self.request('/api/incidents','POST',entry,operator,ocsrf)
        self.assertEqual(code,201,res)
        iid=res['id']
        self.assertEqual(self.request('/api/incidents/review','POST',{'incident_id':iid},operator,ocsrf)[0],403)
        self.assertEqual(self.request('/api/incidents/review','POST',{'incident_id':iid},admin,acsrf)[0],200)
        _,incidents=self.request('/api/incidents',client=admin)
        self.assertEqual(next(i for i in incidents['incidents'] if i['id']==iid)['status'],'reviewed')
        self.assertEqual(self.request('/api/incidents')[0],401)

    def test_catalog_and_static_are_independent_of_maps(self):
        # Even when Leaflet cannot load, central operations are local endpoints.
        c,csrf=self.login('operador')
        self.assertEqual(self.request('/api/trips',client=c)[0],200)
        code,html=self.request('/central',client=c)
        self.assertEqual(code,200)
        self.assertIn(b'manualtripform',html)
        self.assertIn(b'savefare',html)
        self.assertIn(b'newdriverform',html)
        self.assertEqual(self.request('/api/catalog')[0],200)


    def test_qr_passenger_can_request_with_authorized_gps_and_central_owns_trip(self):
        driver,csrf=self.login('conductor7')
        qr=self.request('/api/mine',client=driver)[1]['referral_url'].split('/')[-1]
        url='/registro/'+qr
        code,page=self.request(url)
        self.assertEqual(code,200)
        self.assertIn(b'quicktripform',page)
        self.assertIn(b'quickgps',page)
        self.assertIn(b'quickpickup',page)
        self.assertIn(b'quickconsent',page)
        request={'name':'Pasajero GPS ficticio','phone':'6000-1111','station':'Pacora',
                 'pickup':'Ubicación actual enviada por GPS','destination':'Barrio de prueba',
                 'reference':'Entrada ficticia','pickup_lat':9.0931834,'pickup_lng':-79.2846712,
                 'pickup_accuracy_m':17.3,'referral_token':qr,'consent':True}
        status,result=self.request('/api/requests','POST',request)
        self.assertEqual(status,201,result)
        op,_=self.login('operador')
        code,trips=self.request('/api/trips',client=op)
        self.assertEqual(code,200)
        trip=next(x for x in trips['trips'] if x['id']==result['id'])
        self.assertEqual(trip['pickup_lat'],9.0931834)
        self.assertEqual(trip['pickup_lng'],-79.2846712)
        self.assertEqual(trip['pickup_accuracy_m'],17.3)
        self.assertEqual(trip['channel'],'Web QR Metro Taxi')
        self.assertEqual(trip['phone'],'6000-1111')
        # The referring driver cannot query the central's trip list or phone data.
        self.assertEqual(self.request('/api/trips',client=driver)[0],403)
        self.assertNotIn('6000-1111',str(self.request('/api/mine',client=driver)[1]))

    def test_qr_gps_validation_manual_fallback_and_no_spoofed_qr_attribution(self):
        driver,_=self.login('conductor7')
        tok=self.request('/api/mine',client=driver)[1]['referral_url'].split('/')[-1]
        body={'name':'Pasajero demo','phone':'6000-3333','station':'Pacora',
              'pickup':'Frente a supermercado de prueba','reference':'Señal azul',
              'referral_token':tok,'consent':True}
        code,result=self.request('/api/requests','POST',body)
        self.assertEqual(code,201,result) # Request by manual description, no GPS needed.
        op,_=self.login('operador')
        trip=next(x for x in self.request('/api/trips',client=op)[1]['trips'] if x['id']==result['id'])
        self.assertIsNone(trip['pickup_lat'])
        self.assertIsNone(trip['pickup_accuracy_m'])
        # Accuracy requires coordinates and should be within accepted range.
        self.assertEqual(self.request('/api/requests','POST',{**body,'pickup_accuracy_m':20})[0],400)
        self.assertEqual(self.request('/api/requests','POST',{**body,'pickup_lat':150,'pickup_lng':-79.1})[0],400)
        self.assertEqual(self.request('/api/requests','POST',{**body,'pickup_lat':9.1,'pickup_lng':-79.1,'pickup_accuracy_m':-5})[0],400)
        code,result=self.request('/api/requests','POST',{**body,'referral_token':'not-a-real-qr'})
        self.assertEqual(code,201,result)
        trip=next(x for x in self.request('/api/trips',client=op)[1]['trips'] if x['id']==result['id'])
        self.assertEqual(trip['channel'],'Web cliente')

if __name__=='__main__':unittest.main()

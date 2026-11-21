"""Metro Taxi cloud API (v0.10 staging vertical slice; not production release).

PostgreSQL storage + DB sessions. Public UI is separate. Never start this
module against the old v0.9 SQLite runtime, and never auto-import users.
"""
import hashlib
import base64
import io
import hmac
import json
import math
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import create_engine, select, update, delete, insert, and_
from sqlalchemy.exc import IntegrityError

from .schema import metadata, staff, drivers, customers, trips, sessions, audit, driver_photos, referral_codes, referral_signups, customer_messages

STATIONS = ('Pacora', '24 de Diciembre')
ACTIVE = ('pending', 'offered', 'accepted', 'inprogress')


def now():
    return datetime.now(timezone.utc)


def iso(v):
    return v.replace(tzinfo=timezone.utc).isoformat() if v and v.tzinfo is None else v.isoformat() if v else None


def fresh(v, seconds=120):
    if v is None:
        return False
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return timedelta(0) <= now() - v <= timedelta(seconds=seconds)


def password_hash(secret):
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt, 260000)
    return f'{salt.hex()}:{derived.hex()}'


def password_matches(secret, stored):
    try:
        salt_hex, expected = stored.split(':', 1)
        actual = hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), bytes.fromhex(salt_hex), 260000)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, AttributeError):
        return False


def phone(value):
    if not isinstance(value, str):
        return None
    digits = re.sub(r'[\s()+.\-]', '', value)
    if re.fullmatch(r'\d{8}', digits):
        digits = '507' + digits
    return digits if re.fullmatch(r'507\d{8}', digits) else None


def string(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ''


def coordinates(body, prefix):
    lat = body.get(prefix + '_lat')
    lng = body.get(prefix + '_lng')
    if lat is None and lng is None:
        return None, None
    if isinstance(lat, bool) or isinstance(lng, bool) or not isinstance(lat, (float, int)) or not isinstance(lng, (float, int)):
        raise HTTPException(400, 'Latitud y longitud numéricas obligatorias')
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(400, 'Coordenadas fuera de rango')
    return float(lat), float(lng)



# Local geofence enforcement is a staging safety control, not GPS attestation.
# A modified or spoofed device can still report forged coordinates.
def distance_m(a_lat, a_lng, b_lat, b_lng):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat-a_lat), math.radians(b_lng-a_lng)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371000.0 * 2 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1-x)))


def arrival_gate(driver, ride, action):
    if action not in ('start', 'complete'):
        raise ValueError('Acción de llegada desconocida')
    coord = ('pickup_lat', 'pickup_lng') if action == 'start' else ('dest_lat', 'dest_lng')
    target = 'recogida' if action == 'start' else 'destino'
    radius_m = 150 if action == 'start' else 180
    if ride[coord[0]] is None or ride[coord[1]] is None:
        return {'allowed': False, 'reason': 'Faltan coordenadas verificadas del punto de '+target,
                'distance_m': None, 'radius_m': radius_m}
    if (driver['location_source'] != 'device' or not fresh(driver['location_updated_at'])
            or driver['lat'] is None or driver['lng'] is None):
        return {'allowed': False, 'reason': 'Activa el GPS y espera una ubicación reciente',
                'distance_m': None, 'radius_m': radius_m}
    accuracy = driver['accuracy_m']
    if accuracy is None or not math.isfinite(accuracy) or accuracy > 75:
        return {'allowed': False, 'reason': 'Se necesita GPS con precisión de 75 m o mejor',
                'distance_m': None, 'radius_m': radius_m}
    distance = round(distance_m(driver['lat'], driver['lng'], ride[coord[0]], ride[coord[1]]))
    return {'allowed': distance <= radius_m, 'distance_m': distance, 'radius_m': radius_m,
            'reason': ('Ya estás cerca del punto de '+target if distance <= radius_m
                       else 'Acércate al punto de '+target+' para continuar')}


def driver_public(d):
    return {k: d[k] for k in ('id', 'unit', 'name', 'station', 'status', 'suspended', 'plate',
                             'vehicle_make', 'vehicle_model', 'vehicle_color')} | {
        'last_location_at': iso(d['location_updated_at']),
        'location_source': d['location_source'],
        'gps_recent': fresh(d['location_updated_at']) and d['location_source'] == 'device',
    }


def trip_public(t, audience):
    allowed = ('id', 'station', 'pickup', 'destination', 'reference', 'pickup_lat',
               'pickup_lng', 'pickup_accuracy_m', 'dest_lat', 'dest_lng', 'status',
               'driver_id', 'channel', 'price')
    out = {k: t[k] for k in allowed}
    out['created_at'] = iso(t['created_at'])
    if t['offer_expires_at']:
        out['offer_expires_at'] = iso(t['offer_expires_at'])
    if audience == 'customer':
        # Do not disclose dispatch offers, expiry or a pending driver's identity.
        for private_key in ('driver_id', 'channel', 'offer_expires_at'):
            out.pop(private_key, None)
        if out['status'] == 'offered':
            out['status'] = 'pending'
    if audience == 'central':
        out.update(name=t['name'], phone=t['phone'])
    elif audience == 'driver':
        out['name'] = t['name']    # NO private phone
    return out


def create_app(database_url=None, *, test_mode=False, auto_create=False):
    database_url = database_url or os.environ.get('DATABASE_URL', '')
    if not database_url:
        raise RuntimeError('Configura DATABASE_URL: PostgreSQL obligatorio para la API de nube')
    if not database_url.startswith(('postgresql+psycopg://', 'sqlite+pysqlite://')):
        raise RuntimeError('DATABASE_URL: usa postgresql+psycopg://')
    if database_url.startswith('sqlite') and not test_mode:
        raise RuntimeError('SQLite solo se permite en tests automáticos aislados')
    origins = [x.strip().rstrip('/') for x in os.environ.get('METRO_ALLOWED_ORIGINS', '').split(',') if x.strip()]
    if not origins and not test_mode:
        raise RuntimeError('Configura METRO_ALLOWED_ORIGINS con el dominio HTTPS del portal')
    if not test_mode and any(not x.startswith('https://') for x in origins):
        raise RuntimeError('METRO_ALLOWED_ORIGINS requiere HTTPS en la nube')
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    if auto_create:
        if not test_mode:
            raise RuntimeError('No se crean tablas automáticamente en servidores públicos')
        metadata.create_all(engine)

    app = FastAPI(title='Metro Taxi API', version='0.10.3', docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.test_mode = test_mode
    if not test_mode:
        allowed_hosts=[x.strip() for x in os.environ.get('METRO_ALLOWED_HOSTS','').split(',') if x.strip()]
        if not allowed_hosts:
            raise RuntimeError('Configura METRO_ALLOWED_HOSTS para evitar solicitudes Host arbitrarias')
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    def auth(request: Request, allowed=None, csrf=False):
        cookie = request.cookies.get('metro_sid')
        if not cookie:
            raise HTTPException(401, 'Inicia sesión')
        key = hashlib.sha256(cookie.encode()).hexdigest()
        with engine.connect() as c:
            s = c.execute(select(sessions).where(sessions.c.token_hash == key)).mappings().first()
        if not s:
            raise HTTPException(401, 'Sesión caducada')
        exp = s['expires_at']
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= now():
            raise HTTPException(401, 'Sesión caducada')
        if allowed and s['role'] not in allowed:
            raise HTTPException(403, 'No autorizado')
        if csrf and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), s['csrf_token']):
            raise HTTPException(403, {'code': 'CSRF_INVALID', 'error': 'Token de sesión inválido'})
        return s

    def verify_origin(request):
        origin = request.headers.get('origin')
        # In the isolated local preview, modern browsers send an Origin header
        # even for same-origin POST requests. Allow ONLY the preview's exact
        # loopback origins; never grant this exception to public deployments.
        preview_origins = ('http://127.0.0.1:8770', 'http://localhost:8770', 'http://testserver') if test_mode else ()
        if origin and origin not in origins and origin not in preview_origins:
            raise HTTPException(403, 'Origen no autorizado')
        if not test_mode and origin and not origin.startswith('https://'):
            raise HTTPException(403, 'Se requiere HTTPS')

    def write_audit(c, session, action, trip_id=None, detail=''):
        c.execute(insert(audit).values(created_at=now(), actor_role=session['role'],
                      actor_id=session['user_id'], action=action, trip_id=trip_id, detail=detail))

    def make_session(role, uid, response):
        token = secrets.token_urlsafe(40)
        csrf = secrets.token_urlsafe(32)
        with engine.begin() as c:
            c.execute(insert(sessions).values(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        role=role, user_id=uid, csrf_token=csrf, expires_at=now()+timedelta(hours=8)))
        response.set_cookie('metro_sid', token, max_age=28800, path='/', httponly=True,
                            samesite='lax', secure=not test_mode)

    @app.exception_handler(HTTPException)
    async def http_error(_request, exc):
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={'error': str(exc.detail)})

    def requeue_expired():
        """No perpetual busy drivers: requeue when somebody polls API.

        This is a staging fallback only, not a durable production job.
        """
        with engine.begin() as c:
            expired = c.execute(select(trips).where(and_(
                trips.c.status == 'offered', trips.c.offer_expires_at <= now()))).mappings().all()
            for t in expired:
                moved = c.execute(update(trips).where(and_(trips.c.id == t['id'],
                    trips.c.status == 'offered')).values(status='pending',driver_id=None,offer_expires_at=None))
                if moved.rowcount and t['driver_id']:
                    c.execute(update(drivers).where(and_(drivers.c.id == t['driver_id'],
                        drivers.c.status == 'busy')).values(status='available'))

    @app.get('/api/health')
    def health():
        try:
            with engine.connect() as c:
                c.exec_driver_sql('SELECT 1')
            return {'ok': True, 'version': '0.10-staging', 'database': 'ready'}
        except Exception:
            return JSONResponse(status_code=503, content={'ok': False, 'database': 'unavailable'})

    @app.get('/api/me')
    def me(request: Request):
        try:
            s = auth(request)
        except HTTPException:
            return {'authenticated': False, 'user': None, 'csrf': None}
        return {'authenticated': True, 'user': {'role': s['role'], 'id': s['user_id']}, 'csrf': s['csrf_token']}

    @app.post('/api/login')
    async def login(request: Request):
        verify_origin(request)
        b = await request.json()
        with engine.connect() as c:
            a = c.execute(select(staff).where(staff.c.username == string(b.get('username'), 64))).mappings().first()
        if not a or not password_matches(b.get('password', ''), a['password_hash']):
            raise HTTPException(401, 'Credenciales incorrectas')
        response = JSONResponse({'role': a['role'], 'username': a['username']})
        make_session(a['role'], a['id'], response)
        return response

    @app.post('/api/customer/register')
    async def register(request: Request):
        verify_origin(request)
        b = await request.json()
        name, p, password = string(b.get('name'),100), phone(b.get('phone')), b.get('password')
        if len(name)<2 or not p or not isinstance(password,str) or not 10<=len(password)<=128 or b.get('consent') is not True:
            raise HTTPException(400,'Nombre, teléfono panameño, contraseña de 10+ caracteres y consentimiento obligatorios')
        try:
            with engine.begin() as c:
                cid=c.execute(insert(customers).values(name=name,phone=p,password_hash=password_hash(password),
                    consent_at=now(),created_at=now())).inserted_primary_key[0]
        except IntegrityError:
            raise HTTPException(409, 'Ya existe una cuenta con ese teléfono')
        # Attribution is only recorded for a newly registered customer. Never
        # give the driver the phone or access to passenger account details.
        referral_token = string(b.get('referral_token'),72)
        if referral_token:
            with engine.begin() as c:
                entry=c.execute(select(referral_codes).where(and_(referral_codes.c.token==referral_token,referral_codes.c.enabled.is_(True)))).mappings().first()
                if entry:
                    c.execute(insert(referral_signups).values(customer_id=cid, driver_id=entry['driver_id'], created_at=now()))
        response=JSONResponse({'ok':True,'phone_verified':False,'notice':'Registro de prueba; teléfono SIN verificar'},status_code=201)
        make_session('customer',cid,response)
        return response

    @app.post('/api/customer/login')
    async def customer_login(request: Request):
        verify_origin(request)
        b=await request.json()
        p=phone(b.get('phone'))
        with engine.connect() as c:
            a=c.execute(select(customers).where(customers.c.phone == p)).mappings().first() if p else None
        if not a or not password_matches(b.get('password',''),a['password_hash']):
            raise HTTPException(401,'Credenciales incorrectas')
        response=JSONResponse({'ok':True,'phone_verified':a['phone_verified']})
        make_session('customer',a['id'],response)
        return response

    @app.post('/api/logout')
    def logout(request: Request):
        verify_origin(request)
        s=auth(request,csrf=True)
        with engine.begin() as c:
            c.execute(delete(sessions).where(sessions.c.token_hash==s['token_hash']))
        response=JSONResponse({'ok':True})
        response.delete_cookie('metro_sid',path='/')
        return response

    @app.post('/api/requests')
    async def request_trip(request: Request):
        verify_origin(request)
        s=auth(request,('customer',),csrf=True)
        b=await request.json()
        pickup=string(b.get('pickup'),240)
        dest=string(b.get('destination'),240)
        station=b.get('station')
        if not pickup or station not in STATIONS or b.get('consent') is not True:
            raise HTTPException(400, 'Indica sede, punto de recogida y consentimiento')
        plat,plng=coordinates(b,'pickup')
        dlat,dlng=coordinates(b,'dest')
        accuracy=b.get('pickup_accuracy_m')
        if accuracy is not None and (plat is None or isinstance(accuracy,bool) or not isinstance(accuracy,(int,float)) or not 0<=accuracy<=10000):
            raise HTTPException(400,'Precisión GPS no válida')
        with engine.begin() as c:
            a=c.execute(select(customers).where(customers.c.id==s['user_id'])).mappings().first()
            if not a:raise HTTPException(401,'Cuenta no disponible')
            rid=c.execute(insert(trips).values(created_at=now(), customer_id=a['id'],name=a['name'],phone=a['phone'],
                  station=station,pickup=pickup,destination=dest,reference=string(b.get('reference'),240),
                  pickup_lat=plat,pickup_lng=plng,pickup_accuracy_m=accuracy,
                  dest_lat=dlat,dest_lng=dlng,channel='Web Metro Taxi')).inserted_primary_key[0]
            write_audit(c,s,'ride_requested',rid)
        return JSONResponse({'ok':True,'id':rid,'status':'pending'}, status_code=201)

    @app.get('/api/customer/trips')
    def customer_trips(request: Request):
        s=auth(request,('customer',))
        requeue_expired()
        with engine.connect() as c:
            a=c.execute(select(customers).where(customers.c.id==s['user_id'])).mappings().first()
            if not a:raise HTTPException(404,'Cuenta no disponible')
            rows=c.execute(select(trips).where(trips.c.customer_id==a['id']).order_by(trips.c.id.desc()).limit(50)).mappings().all()
            result=[]
            for t in rows:
                item=trip_public(t,'customer')
                if t['driver_id'] and t['status'] in ('accepted','inprogress','done'):
                    d=c.execute(select(drivers).where(drivers.c.id==t['driver_id'])).mappings().first()
                    if d:
                        item['driver']={k:d[k] for k in ('name','unit','plate','vehicle_make','vehicle_model','vehicle_color')}
                        item['driver']['confirmed']=True
                        if item['driver']['confirmed']:
                            photo=c.execute(select(driver_photos.c.driver_id).where(driver_photos.c.driver_id==d['id'])).first()
                            item['driver']['photo_url']=f'/api/driver-photo/{d["id"]}' if photo else None
                        if item['driver']['confirmed'] and d['location_source']=='device' and fresh(d['location_updated_at']) and d['lat'] is not None:
                            item['driver']['location']={'lat':d['lat'],'lng':d['lng'],'updated_at':iso(d['location_updated_at']),
                                                        'accuracy_m':d['accuracy_m'],'fresh':True,'source':'device'}
                result.append(item)
        return {'account':{'name':a['name'],'phone':a['phone'],'phone_verified':a['phone_verified']},'trips':result}

    @app.get('/api/fleet')
    def fleet(request: Request):
        auth(request,('admin','operator'))
        with engine.connect() as c:
            rows=c.execute(select(drivers).order_by(drivers.c.unit)).mappings().all()
            out=[]
            for d in rows:
                item=driver_public(d)
                # Fresh device GPS only. Never send cached/simulated positions.
                if item['gps_recent'] and d['lat'] is not None and d['lng'] is not None:
                    item['location']={'lat':d['lat'],'lng':d['lng'],'accuracy_m':d['accuracy_m'],
                                      'updated_at':iso(d['location_updated_at']),'source':'device'}
                out.append(item)
            return {'drivers':out}

    @app.get('/api/trips')
    def all_trips(request: Request):
        auth(request,('admin','operator'))
        requeue_expired()
        with engine.connect() as c:
            return {'trips':[trip_public(t,'central') for t in c.execute(select(trips).order_by(trips.c.id.desc()).limit(200)).mappings()]}

    @app.post('/api/trips/manual')
    async def manual_trip(request: Request):
        verify_origin(request)
        s=auth(request,('admin','operator'),csrf=True)
        b=await request.json()
        name,p=string(b.get('name'),100),phone(b.get('phone'))
        pickup=string(b.get('pickup'),240)
        station=b.get('station')
        if len(name)<2 or not p or not pickup or station not in STATIONS:
            raise HTTPException(400,'Nombre, teléfono, recogida y sede válidos obligatorios')
        lat,lng=coordinates(b,'pickup')
        with engine.begin() as c:
            tid=c.execute(insert(trips).values(created_at=now(),name=name,phone=p,station=station,
                pickup=pickup,destination=string(b.get('destination'),240),
                reference=string(b.get('reference'),240),pickup_lat=lat,pickup_lng=lng,
                channel='Central - llamada/WhatsApp')).inserted_primary_key[0]
            write_audit(c,s,'ride_entered_by_central',tid)
        return JSONResponse({'ok':True,'id':tid,'status':'pending'},status_code=201)

    @app.post('/api/trips/point')
    async def set_trip_point(request: Request):
        """Central confirms coordinates provided by the rider or chosen on map.

        Does not geocode, invent a GPS fix or override closed rides. The stored
        point is a passenger-confirmed place, not the operator's device GPS.
        """
        verify_origin(request)
        session=auth(request,('admin','operator'),csrf=True)
        b=await request.json()
        tid=b.get('trip_id')
        if isinstance(tid,bool) or not isinstance(tid,int) or tid < 1:
            raise HTTPException(400,'Identificador de carrera inválido')
        kind=b.get('point')
        if kind not in ('pickup','destination'):
            raise HTTPException(400,'Indica recogida o destino')
        method=b.get('method')
        if method not in ('map_click','provided_coordinates'):
            raise HTTPException(400,'Indica el origen explícito de las coordenadas')
        if b.get('confirmed_with_passenger') is not True:
            raise HTTPException(400,'Confirma el punto con el pasajero antes de guardarlo')
        if 'expected_lat' not in b or 'expected_lng' not in b:
            raise HTTPException(400,'Recarga la carrera antes de modificar el punto')
        def validated_pair(lat,lng,allow_missing=False):
            if allow_missing and lat is None and lng is None:
                return None,None
            if (isinstance(lat,bool) or isinstance(lng,bool)
                    or not isinstance(lat,(int,float)) or not isinstance(lng,(int,float))
                    or not math.isfinite(lat) or not math.isfinite(lng)
                    or not -90 <= lat <= 90 or not -180 <= lng <= 180
                    or (lat == 0 and lng == 0)):
                raise HTTPException(400,'Introduce latitud y longitud verificadas y válidas')
            return float(lat),float(lng)
        lat,lng=validated_pair(b.get('lat'),b.get('lng'))
        previous_lat,previous_lng=validated_pair(b['expected_lat'],b['expected_lng'],allow_missing=True)
        states=('pending','offered','accepted') if kind=='pickup' else ('pending','offered','accepted','inprogress')
        latcol=trips.c.pickup_lat if kind=='pickup' else trips.c.dest_lat
        lngcol=trips.c.pickup_lng if kind=='pickup' else trips.c.dest_lng
        with engine.begin() as c:
            t=c.execute(select(trips).where(trips.c.id==tid)).mappings().first()
            if not t:
                raise HTTPException(404,'Carrera no encontrada')
            if t['status'] not in states:
                raise HTTPException(409,'Este punto ya no se puede modificar en esta etapa')
            if t[latcol.name]!=previous_lat or t[lngcol.name]!=previous_lng:
                raise HTTPException(409,'Otro operador modificó este punto; actualiza la central')
            if lat==previous_lat and lng==previous_lng:
                return {'ok':True,'trip_id':tid,'point':kind,'unchanged':True}
            conditions=[trips.c.id==tid,trips.c.status==t['status'],
                latcol.is_(None) if previous_lat is None else latcol==previous_lat,
                lngcol.is_(None) if previous_lng is None else lngcol==previous_lng]
            updated=c.execute(update(trips).where(and_(*conditions)).values({latcol:lat,lngcol:lng}))
            if updated.rowcount!=1:
                raise HTTPException(409,'Punto cambiado simultáneamente; actualiza y vuelve a confirmar')
            write_audit(c,session,'trip_point_confirmed',tid,
                        f'point={kind};method={method};confirmed_with_passenger=true;replaced={previous_lat is not None}')
        return {'ok':True,'trip_id':tid,'point':kind,'lat':lat,'lng':lng,'status':t['status']}

    @app.post('/api/trips/assign')
    async def assign(request: Request):
        verify_origin(request)
        s=auth(request,('admin','operator'),csrf=True)
        b=await request.json()
        try: tid,did=int(b.get('trip_id')),int(b.get('driver_id'))
        except (ValueError,TypeError): raise HTTPException(400,'Identificadores inválidos')
        with engine.begin() as c:
            # Atomic updates guard against two operators offering the same ride,
            # or trying to offer two rides to the same driver.
            t=c.execute(select(trips).where(trips.c.id==tid)).mappings().first()
            d=c.execute(select(drivers).where(drivers.c.id==did)).mappings().first()
            if not t or not d:raise HTTPException(404,'Carrera o conductor inexistente')
            if t['station'] != d['station']:raise HTTPException(409,'No corresponde a la sede')
            updated=c.execute(update(trips).where(and_(trips.c.id==tid,trips.c.status=='pending')).values(
                driver_id=did,status='offered',offer_expires_at=now()+timedelta(seconds=120)))
            if updated.rowcount!=1:raise HTTPException(409,'La carrera ya no está pendiente')
            updated=c.execute(update(drivers).where(and_(drivers.c.id==did,drivers.c.status=='available',drivers.c.suspended.is_(False))).values(status='busy'))
            if updated.rowcount!=1:raise HTTPException(409,'Unidad no disponible o suspendida')
            write_audit(c,s,'ride_offered',tid, f'driver_id={did}')
        return {'ok':True,'status':'offered'}

    @app.get('/api/mine')
    def mine(request: Request):
        s=auth(request,('driver',))
        requeue_expired()
        with engine.connect() as c:
            u=c.execute(select(staff).where(staff.c.id==s['user_id'])).mappings().first()
            if not u or not u['driver_id']:raise HTTPException(403,'Conductor sin unidad')
            d=c.execute(select(drivers).where(drivers.c.id==u['driver_id'])).mappings().first()
            if not d:raise HTTPException(404,'Unidad no disponible')
            assigned=[]
            for t in c.execute(select(trips).where(trips.c.driver_id==d['id']).order_by(trips.c.id.desc()).limit(60)).mappings():
                item=trip_public(t,'driver')
                if t['status']=='accepted':
                    item['arrival']={'start': arrival_gate(d, t, 'start')}
                elif t['status']=='inprogress':
                    item['arrival']={'complete': arrival_gate(d, t, 'complete')}
                assigned.append(item)
        shown_driver=driver_public(d)
        if shown_driver['gps_recent'] and d['lat'] is not None:
            shown_driver['location']={'lat':d['lat'],'lng':d['lng'],'accuracy_m':d['accuracy_m'],
                                      'updated_at':iso(d['location_updated_at']),'source':'device'}
        return {'driver':shown_driver,'trips':assigned,'referral_url':None,'referral_count':0,
                'active_shift_since':None,'qr_ready':False,'public_link_configured':False}

    def driver_for_session(c,s):
        u=c.execute(select(staff).where(staff.c.id==s['user_id'])).mappings().first()
        if not u or not u['driver_id']:raise HTTPException(403,'Unidad no asignada')
        d=c.execute(select(drivers).where(drivers.c.id==u['driver_id'])).mappings().first()
        if not d:raise HTTPException(404,'Unidad no existe')
        return d

    @app.post('/api/driver/status')
    async def driver_status(request: Request):
        verify_origin(request)
        s=auth(request,('driver',),csrf=True)
        b=await request.json()
        status=b.get('status')
        if status not in ('available','off'):raise HTTPException(400,'Estado no permitido')
        with engine.begin() as c:
            d=driver_for_session(c,s)
            if d['suspended']:raise HTTPException(403,'Unidad suspendida')
            if d['status']=='busy':raise HTTPException(409,'Termina la carrera asignada')
            values={'status':status}
            if status=='off':values.update(lat=None,lng=None,accuracy_m=None,location_source='none',location_updated_at=None)
            c.execute(update(drivers).where(drivers.c.id==d['id']).values(**values))
            write_audit(c,s,'status_'+status)
        return {'ok':True,'status':status}

    @app.post('/api/driver/location')
    async def driver_location(request: Request):
        verify_origin(request)
        s=auth(request,('driver',),csrf=True)
        b=await request.json()
        # Android and browser both send explicit lat/lng, not a text address.
        lat,lng=b.get('lat'),b.get('lng')
        if isinstance(lat,bool) or isinstance(lng,bool) or not isinstance(lat,(int,float)) or not isinstance(lng,(int,float)) or not -90<=lat<=90 or not -180<=lng<=180:
            raise HTTPException(400,'GPS inválido')
        accuracy=b.get('accuracy_m')
        if b.get('consent') is not True or isinstance(accuracy,bool) or not isinstance(accuracy,(int,float)) or not 0<=accuracy<=200:
            raise HTTPException(400,'GPS requiere consentimiento y precisión hasta 200 m')
        with engine.begin() as c:
            d=driver_for_session(c,s)
            if d['status']=='off' or d['suspended']:raise HTTPException(403,'Primero entra en servicio')
            c.execute(update(drivers).where(drivers.c.id==d['id']).values(lat=float(lat),lng=float(lng),accuracy_m=float(accuracy),
                  location_source='device',location_updated_at=now()))
        return {'ok':True,'updated_at':iso(now()),'accuracy_m':accuracy}

    @app.post('/api/driver/location/stop')
    def stop_location(request: Request):
        verify_origin(request)
        s=auth(request,('driver',),csrf=True)
        with engine.begin() as c:
            d=driver_for_session(c,s)
            c.execute(update(drivers).where(drivers.c.id==d['id']).values(
                lat=None,lng=None,accuracy_m=None,location_updated_at=None,location_source='none'))
        return {'ok':True}

    @app.post('/api/trips/action')
    async def trip_action(request: Request):
        verify_origin(request)
        s=auth(request,('driver',),csrf=True)
        b=await request.json()
        action=b.get('action')
        try:tid=int(b.get('trip_id'))
        except (TypeError,ValueError):raise HTTPException(400,'Carrera inválida')
        states={'accept':('offered','accepted'),'reject':('offered','pending'),
                'start':('accepted','inprogress'),'complete':('inprogress','done')}
        if action not in states:raise HTTPException(400,'Acción desconocida')
        old,new=states[action]
        with engine.begin() as c:
            d=driver_for_session(c,s)
            t=c.execute(select(trips).where(trips.c.id==tid)).mappings().first()
            if not t or t['driver_id']!=d['id']:raise HTTPException(403,'No es tu carrera')
            if t['status']!=old:raise HTTPException(409,'La carrera cambió de estado')
            if action=='accept' and t['offer_expires_at']:
                expires=t['offer_expires_at']
                if expires.tzinfo is None:expires=expires.replace(tzinfo=timezone.utc)
                if expires<=now():raise HTTPException(409,'Oferta vencida; consulta a la central')
            if action in ('start', 'complete'):
                result=arrival_gate(d,t,action)
                if not result['allowed']:
                    raise HTTPException(409, result['reason'])
            values={'status':new}
            if action=='reject':values.update(driver_id=None,offer_expires_at=None)
            updated=c.execute(update(trips).where(and_(trips.c.id==tid,trips.c.status==old,trips.c.driver_id==d['id'])).values(**values))
            if updated.rowcount!=1:raise HTTPException(409,'La carrera cambió de estado')
            if action in ('reject','complete'):
                c.execute(update(drivers).where(drivers.c.id==d['id']).values(status='available'))
            write_audit(c,s,'trip_'+action,tid)
        return {'ok':True,'status':new}

    @app.post('/api/trips/cancel')
    async def cancel(request: Request):
        verify_origin(request)
        s=auth(request,('customer','operator','admin'),csrf=True)
        b=await request.json()
        try:tid=int(b.get('trip_id'))
        except (ValueError,TypeError):raise HTTPException(400,'Carrera inválida')
        with engine.begin() as c:
            t=c.execute(select(trips).where(trips.c.id==tid)).mappings().first()
            if not t:raise HTTPException(404,'Carrera desconocida')
            if s['role']=='customer' and (t['customer_id']!=s['user_id'] or t['status'] not in ('pending','offered')):
                raise HTTPException(403,'No puedes cancelar esta carrera')
            if t['status'] not in ACTIVE:raise HTTPException(409,'Carrera cerrada')
            updated=c.execute(update(trips).where(and_(trips.c.id==tid,trips.c.status==t['status'])).values(status='cancelled'))
            if updated.rowcount!=1:raise HTTPException(409,'La carrera cambió')
            if t['driver_id']:
                c.execute(update(drivers).where(and_(drivers.c.id==t['driver_id'], drivers.c.status=='busy')).values(status='available'))
            write_audit(c,s,'trip_cancelled',tid)
        return {'ok':True}

    @app.post('/api/trips/price')
    async def set_price(request: Request):
        verify_origin(request)
        s=auth(request,('admin','operator'),csrf=True)
        b=await request.json()
        try:tid=int(b.get('trip_id'))
        except (ValueError,TypeError):raise HTTPException(400,'Carrera inválida')
        price=b.get('price')
        if isinstance(price,bool) or not isinstance(price,(int,float)) or not 0<=price<=500:
            raise HTTPException(400,'Tarifa válida de 0 a 500 USD')
        with engine.begin() as c:
            changed=c.execute(update(trips).where(trips.c.id==tid).values(price=round(float(price),2)))
            if not changed.rowcount:raise HTTPException(404,'Carrera desconocida')
            write_audit(c,s,'trip_price_updated',tid)
        return {'ok':True,'price':round(float(price),2)}

    @app.get('/api/messages')
    def read_messages(request: Request):
        s=auth(request,('customer','operator','admin'))
        with engine.connect() as c:
            if s['role']=='customer':
                rows=c.execute(select(customer_messages).where(customer_messages.c.customer_id==s['user_id']).order_by(customer_messages.c.id.desc()).limit(100)).mappings().all()
            else:
                rows=c.execute(select(customer_messages).order_by(customer_messages.c.id.desc()).limit(150)).mappings().all()
            out=[{'id':m['id'],'customer_id':m['customer_id'],'sender':m['sender'],'body':m['body'],
                  'created_at':iso(m['created_at'])} for m in rows]
        return {'messages':out}

    @app.post('/api/messages')
    async def send_message(request: Request):
        verify_origin(request)
        s=auth(request,('customer','operator','admin'),csrf=True)
        b=await request.json()
        msg=string(b.get('body'),800)
        if not msg or len(msg)<2:raise HTTPException(400,'El mensaje debe tener 2 caracteres como mínimo')
        if s['role']=='customer':cid=s['user_id'];sender='customer'
        else:
            try:cid=int(b.get('customer_id'))
            except (TypeError,ValueError):raise HTTPException(400,'Selecciona un cliente registrado')
            sender='central'
        with engine.begin() as c:
            if not c.execute(select(customers.c.id).where(customers.c.id==cid)).first():raise HTTPException(404,'Cliente inexistente')
            mid=c.execute(insert(customer_messages).values(customer_id=cid,sender=sender,body=msg,created_at=now())).inserted_primary_key[0]
            write_audit(c,s,'message_sent',detail=f'customer_id={cid} message_id={mid}')
        return JSONResponse({'ok':True,'id':mid},status_code=201)

    @app.get('/api/stats')
    def stats(request: Request):
        auth(request,('admin','operator'))
        with engine.connect() as c:
            rows=c.execute(select(trips.c.driver_id,trips.c.status,trips.c.price,trips.c.station)).mappings().all()
            units=c.execute(select(drivers.c.id,drivers.c.unit,drivers.c.name)).mappings().all()
        by_status={key:sum(1 for t in rows if t['status']==key)
                   for key in ('pending','offered','accepted','inprogress','done','cancelled')}
        by_unit=[{'unit':d['unit'],'name':d['name'],
                  'completed':sum(1 for t in rows if t['driver_id']==d['id'] and t['status']=='done'),
                  'revenue_recorded':round(sum(float(t['price'] or 0) for t in rows if t['driver_id']==d['id'] and t['status']=='done'),2)} for d in units]
        return {'total':len(rows),'by_status':by_status,'by_unit':by_unit,'note':'Solo tarifas registradas; no es contabilidad de cobros reales'}

    @app.patch('/api/drivers/{driver_id}/vehicle')
    async def vehicle_profile(driver_id: int, request: Request):
        verify_origin(request)
        s=auth(request,('admin',),csrf=True)
        b=await request.json()
        fields={'plate':32,'vehicle_make':80,'vehicle_model':80,'vehicle_color':40}
        values={k:string(b.get(k),n) for k,n in fields.items()}
        with engine.begin() as c:
            changed=c.execute(update(drivers).where(drivers.c.id==driver_id).values(**values))
            if not changed.rowcount:raise HTTPException(404,'Unidad inexistente')
            write_audit(c,s,'vehicle_profile_updated',detail=f'driver_id={driver_id}')
        return {'ok':True}

    @app.post('/api/drivers/{driver_id}/photo')
    async def upload_driver_photo(driver_id: int,request: Request):
        verify_origin(request)
        s=auth(request,('admin',),csrf=True)
        b=await request.json()
        mime=b.get('mime')
        if mime not in ('image/jpeg','image/png'):raise HTTPException(400,'Solo JPG o PNG')
        try:content=base64.b64decode(b.get('base64',''),validate=True)
        except (ValueError,TypeError):raise HTTPException(400,'Fotografía inválida')
        valid=(mime=='image/jpeg' and content[:3]==b'\xff\xd8\xff') or (mime=='image/png' and content[:8]==b'\x89PNG\r\n\x1a\n')
        if not valid or not 100<=len(content)<=1_000_000:raise HTTPException(400,'Fotografía inválida o mayor a 1 MB')
        with engine.begin() as c:
            if not c.execute(select(drivers.c.id).where(drivers.c.id==driver_id)).first():raise HTTPException(404,'Unidad inexistente')
            c.execute(delete(driver_photos).where(driver_photos.c.driver_id==driver_id))
            c.execute(insert(driver_photos).values(driver_id=driver_id,mime=mime,content=content,uploaded_at=now()))
            write_audit(c,s,'driver_photo_updated',detail=f'driver_id={driver_id}')
        return {'ok':True,'photo_url':f'/api/driver-photo/{driver_id}'}

    @app.get('/api/driver-photo/{driver_id}')
    def read_driver_photo(driver_id: int,request: Request):
        s=auth(request)
        with engine.connect() as c:
            if s['role'] in ('driver',):
                d=driver_for_session(c,s)
                if d['id']!=driver_id:raise HTTPException(403,'No autorizado')
            elif s['role']=='customer':
                belongs=c.execute(select(trips.c.id).where(and_(trips.c.customer_id==s['user_id'],
                    trips.c.driver_id==driver_id,trips.c.status.in_(('accepted','inprogress')))).limit(1)).first()
                if not belongs:raise HTTPException(403,'No autorizado')
            elif s['role'] not in ('admin','operator'):raise HTTPException(403,'No autorizado')
            record=c.execute(select(driver_photos).where(driver_photos.c.driver_id==driver_id)).mappings().first()
        if not record:raise HTTPException(404,'Fotografía pendiente')
        return Response(content=record['content'],media_type=record['mime'],headers={'Cache-Control':'private, no-store'})

    @app.get('/api/driver/referral')
    def my_referral(request: Request):
        s=auth(request,('driver',))
        with engine.begin() as c:
            d=driver_for_session(c,s)
            r=c.execute(select(referral_codes).where(referral_codes.c.driver_id==d['id'])).mappings().first()
            if not r:
                token=secrets.token_urlsafe(30)
                c.execute(insert(referral_codes).values(driver_id=d['id'],token=token,enabled=True))
                enabled=True
            else:token,enabled=r['token'],r['enabled']
            count=len(c.execute(select(referral_signups.c.customer_id).where(referral_signups.c.driver_id==d['id'])).all())
        return {'enabled':bool(enabled),'url':'/cliente.html?referido='+token if enabled else None,
                'qr_url':'/api/driver/referral-qr.svg' if enabled else None,'count':count,
                'public_link_configured':bool(test_mode or os.environ.get('METRO_PUBLIC_BASE_URL'))}

    @app.get('/api/driver/referral-qr.svg')
    def my_referral_svg(request: Request):
        s=auth(request,('driver',))
        with engine.connect() as c:
            d=driver_for_session(c,s)
            r=c.execute(select(referral_codes).where(referral_codes.c.driver_id==d['id'])).mappings().first()
        if not r or not r['enabled']:raise HTTPException(404,'QR inactivo')
        base='http://127.0.0.1:8770' if test_mode else os.environ.get('METRO_PUBLIC_BASE_URL','').rstrip('/')
        if not base or (not test_mode and not base.startswith('https://')):
            raise HTTPException(503,'Configura METRO_PUBLIC_BASE_URL HTTPS antes de emitir QR')
        import qrcode
        from qrcode.image.svg import SvgPathImage
        output=io.BytesIO()
        qrcode.make(base+'/cliente.html?referido='+r['token'],image_factory=SvgPathImage,box_size=9,border=4).save(output)
        return Response(content=output.getvalue(),media_type='image/svg+xml',headers={'Cache-Control':'private, no-store','Content-Security-Policy':"default-src 'none'; style-src 'none'"})

    @app.get('/api/referral/{token}')
    def referral_info(token: str):
        if not re.fullmatch(r'[A-Za-z0-9_-]{20,72}',token):raise HTTPException(404,'Código inválido')
        with engine.connect() as c:
            r=c.execute(select(referral_codes).where(and_(referral_codes.c.token==token,referral_codes.c.enabled.is_(True)))).mappings().first()
            if not r:raise HTTPException(404,'Código inactivo')
            d=c.execute(select(drivers.c.unit,drivers.c.station,drivers.c.suspended).where(drivers.c.id==r['driver_id'])).mappings().first()
        if not d or d['suspended']:raise HTTPException(404,'Código inactivo')
        return {'company':'Metro Taxi','unit':d['unit'],'station':d['station'], 'phone_verified':False}

    @app.post('/api/driver/referral/revoke')
    def revoke_referral(request: Request):
        verify_origin(request)
        s=auth(request,('driver',),csrf=True)
        with engine.begin() as c:
            d=driver_for_session(c,s)
            c.execute(update(referral_codes).where(referral_codes.c.driver_id==d['id']).values(enabled=False))
        return {'ok':True,'enabled':False}

    return app


# Fail fast if configuration is missing. Tests call create_app with temporary SQLite.
if os.environ.get('DATABASE_URL') and os.environ.get('METRO_FACTORY_ONLY') != '1':
    app = create_app()
else:
    # The loopback Docker entrypoint and management CLI import create_app but
    # configure their own isolated application. Never construct an unrelated
    # production app during those imports; no security check is bypassed in
    # create_app itself.
    app = None

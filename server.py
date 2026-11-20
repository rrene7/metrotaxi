#!/usr/bin/env python3
"""Metro Taxi MVP v0.7 local: turnos, ficha vehículo, GPS consentido y estados seguros.
PROTOTYPE ONLY: not production authentication, anti-abuse or TLS. Do not expose to Internet.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from math import radians,sin,cos,atan2,sqrt
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
try:
    import qrcode
    import qrcode.image.svg
except ImportError:
    qrcode = None  # HTML still runs; QR rendering requires pip install qrcode>=8.0

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'runtime'
DB_PATH = RUN / 'metro_taxi_demo.sqlite3'
CATALOG = json.loads((ROOT / 'catalogo_inec_2023_piloto.json').read_text(encoding='utf-8'))
DB_LOCK = threading.RLock()
SESSIONS = {}   # ephemeral in-memory sessions, not production store
REFERRAL_LIMITS = {}  # rudimentary local antiabuse; NOT production-ready
CUSTOMER_LIMITS = {}  # local prototype limits, not a production anti-abuse system
# Test points are invented simulated demo markers, not geocoded street addresses.
DEMO_DRIVERS = [
    ('MT-01','Conductor DEMO 01','24 de Diciembre',9.0952,-79.3571,'available'),
    ('MT-02','Conductor DEMO 02','24 de Diciembre',9.0921,-79.3653,'available'),
    ('MT-03','Conductor DEMO 03','24 de Diciembre',9.1060,-79.3490,'busy'),
    ('MT-04','Conductor DEMO 04','24 de Diciembre',9.0835,-79.3793,'off'),
    ('MT-05','Conductor DEMO 05','24 de Diciembre',9.1143,-79.3640,'available'),
    ('MT-06','Conductor DEMO 06','24 de Diciembre',9.1003,-79.3411,'available'),
    ('MT-07','Conductor DEMO 07','Pacora',9.0905,-79.2816,'available'),
    ('MT-08','Conductor DEMO 08','Pacora',9.0819,-79.3006,'available'),
    ('MT-09','Conductor DEMO 09','Pacora',9.1009,-79.2962,'busy'),
    ('MT-10','Conductor DEMO 10','Pacora',9.0935,-79.3136,'off'),
    ('MT-11','Conductor DEMO 11','Pacora',9.0754,-79.2802,'available'),
    ('MT-12','Conductor DEMO 12','Pacora',9.1090,-79.2697,'available'),
]


def referral_token():
    # 192 bits unpredictable, URL safe; not a sequential driver identifier.
    return secrets.token_urlsafe(24)


def referral_base(port):
    configured = os.environ.get('METRO_PUBLIC_BASE_URL', '').strip().rstrip('/')
    if configured:
        u = urlparse(configured)
        if u.scheme == 'https' and u.netloc and not u.username and not u.password and not u.query and not u.fragment and u.path in ('', '/'):
            return configured
        if u.scheme == 'http' and u.hostname in ('localhost', '127.0.0.1') and not u.query and not u.fragment and u.path in ('', '/'):
            return configured
        raise ValueError('METRO_PUBLIC_BASE_URL debe ser HTTPS o localhost para pruebas')
    return f'http://127.0.0.1:{port}'


def phone_normalized(value):
    if not isinstance(value, str):
        return ''
    digits = re.sub(r'[ ()+.-]', '', value.strip())
    # Panama: 8 digits. Also accept country-prefixed +507 / 507.
    if not digits.isdecimal():
        return ''
    if len(digits) == 8:
        digits = '507' + digits
    return digits if re.fullmatch(r'507\d{8}', digits) else ''


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=12, check_same_thread=False)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        with db:
            yield db
    finally:
        db.close()


def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 220000)
    return base64.b64encode(salt).decode() + ':' + base64.b64encode(key).decode()


def valid_password(password, hashed):
    try:
        a, b = hashed.split(':', 1)
        salt = base64.b64decode(a)
        candidate = password_hash(password, salt).split(':', 1)[1]
        return hmac.compare_digest(candidate, b)
    except (ValueError, TypeError):
        return False


def live_position(driver):
    """Return a current device-provided position, never an invented/demo point."""
    if not driver or driver['simulated'] or driver['location_source'] != 'device':
        return None
    if driver['lat'] is None or driver['lng'] is None or driver['status']=='off':
        return None
    try:
        timestamp=datetime.fromisoformat(driver['updated_at'])
        age=(datetime.now(timezone.utc)-timestamp).total_seconds()
        if age < 0 or age > 120:
            return None
    except (TypeError, ValueError):
        return None
    return {'lat':driver['lat'],'lng':driver['lng'],'accuracy_m':driver['location_accuracy_m'],
            'updated_at':driver['updated_at'],'source':'device','fresh':True}


def expire_offers():
    """Requeue expired offers at the next API request; not a background scheduler."""
    with DB_LOCK, connect() as db:
        rows=db.execute("SELECT id,driver_id FROM trips WHERE status='offered' AND offer_expires_at IS NOT NULL AND offer_expires_at<=?",(utcnow(),)).fetchall()
        for t in rows:
            db.execute("UPDATE trips SET status='pending',driver_id=NULL,offer_expires_at=NULL WHERE id=? AND status='offered'",(t['id'],))
            db.execute("UPDATE drivers SET status='available' WHERE id=? AND status='busy'",(t['driver_id'],))
            audit(db,'sistema','offer_expired',{'trip_id':t['id'],'driver_id':t['driver_id']})
        if rows:db.commit()


def shift_change(db,driver_id,status,actor):
    if status=='available':
        if not db.execute('SELECT 1 FROM driver_shifts WHERE driver_id=? AND ended_at IS NULL',(driver_id,)).fetchone():
            db.execute('INSERT INTO driver_shifts(driver_id,started_at,started_by) VALUES (?,?,?)',
                       (driver_id,utcnow(),actor))
    if status=='off':
        db.execute('UPDATE driver_shifts SET ended_at=?,ended_by=? WHERE driver_id=? AND ended_at IS NULL',
                   (utcnow(),actor,driver_id))


def haversine_km(lat1,lng1,lat2,lng2):
    """Straight-line distance only. Does not estimate drive route or ETA."""
    r=6371.0
    a=radians(lat2-lat1);b=radians(lng2-lng1)
    h=sin(a/2)**2+cos(radians(lat1))*cos(radians(lat2))*sin(b/2)**2
    return 2*r*atan2(sqrt(h),sqrt(max(0,1-h)))


def candidates_for_trip(db,trip,excluded=()):
    if trip['pickup_lat'] is None or trip['pickup_lng'] is None:return []
    possibilities=[]
    for d in db.execute("SELECT * FROM drivers WHERE station=? AND status='available' AND suspended=0 AND simulated=0",
                        (trip['station'],)):
        if d['id'] in excluded:continue
        loc=live_position(d)
        if not loc or loc['accuracy_m'] is None or loc['accuracy_m']>200:continue
        dist=haversine_km(trip['pickup_lat'],trip['pickup_lng'],loc['lat'],loc['lng'])
        possibilities.append({'driver_id':d['id'],'unit':d['unit'],'name':d['name'],
                              'straight_line_km':round(dist,2),'gps_accuracy_m':loc['accuracy_m'],
                              'updated_at':loc['updated_at']})
    return sorted(possibilities,key=lambda x:(x['straight_line_km'],x['unit']))


def dispatch_cycle():
    """Opt-in auto dispatch for old pending requests; executed when app polls API."""
    with DB_LOCK,connect() as db:
        row=db.execute("SELECT value FROM app_settings WHERE key='dispatch_mode'").fetchone()
        if not row or row['value']!='auto_after_120s':return
        threshold=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat(timespec='seconds')
        for trip in db.execute("SELECT * FROM trips WHERE status='pending' AND created_at<=? AND pickup_lat IS NOT NULL AND pickup_lng IS NOT NULL ORDER BY id LIMIT 25",(threshold,)).fetchall():
            previous={r[0] for r in db.execute('SELECT driver_id FROM trip_offer_history WHERE trip_id=?',(trip['id'],))}
            options=candidates_for_trip(db,trip,previous)
            if not options:continue
            chosen=options[0]
            expiry=(datetime.now(timezone.utc)+timedelta(seconds=max(30,min(600,int(os.environ.get('METRO_OFFER_SECONDS','120')))))).isoformat(timespec='seconds')
            db.execute("UPDATE trips SET status='offered',driver_id=?,offer_expires_at=? WHERE id=? AND status='pending'",
                       (chosen['driver_id'],expiry,trip['id']))
            db.execute("UPDATE drivers SET status='busy' WHERE id=? AND status='available'",(chosen['driver_id'],))
            db.execute('INSERT OR IGNORE INTO trip_offer_history(trip_id,driver_id,offered_at,mode) VALUES (?,?,?,?)',
                       (trip['id'],chosen['driver_id'],utcnow(),'auto'))
            audit(db,'sistema','trip_auto_offered',{'trip_id':trip['id'],'driver_id':chosen['driver_id'],
                                                   'straight_line_km':chosen['straight_line_km']})
        db.commit()


def init_database():
    RUN.mkdir(exist_ok=True)
    with DB_LOCK, connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS drivers (
          id INTEGER PRIMARY KEY, unit TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
          station TEXT NOT NULL, lat REAL, lng REAL,
          status TEXT NOT NULL CHECK(status IN ('available','busy','off')),
          suspended INTEGER NOT NULL DEFAULT 0, simulated INTEGER NOT NULL DEFAULT 1,
          updated_at TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
          rejected_count INTEGER NOT NULL DEFAULT 0,
          referral_token TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL,
          driver_id INTEGER REFERENCES drivers(id)
        );
        CREATE TABLE IF NOT EXISTS trips (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
          name TEXT NOT NULL, phone TEXT NOT NULL,
          station TEXT NOT NULL, pickup TEXT NOT NULL,
          destination TEXT NOT NULL DEFAULT '', reference TEXT NOT NULL DEFAULT '',
          province TEXT NOT NULL DEFAULT '', district TEXT NOT NULL DEFAULT '',
          corregimiento TEXT NOT NULL DEFAULT '', location_pending TEXT NOT NULL DEFAULT '',
          community TEXT NOT NULL DEFAULT '', barriada TEXT NOT NULL DEFAULT '',
          street TEXT NOT NULL DEFAULT '', house TEXT NOT NULL DEFAULT '',
          pickup_lat REAL, pickup_lng REAL, dest_lat REAL, dest_lng REAL,
          pickup_accuracy_m REAL,
          price REAL, status TEXT NOT NULL DEFAULT 'pending',
          driver_id INTEGER REFERENCES drivers(id), channel TEXT NOT NULL DEFAULT 'Web',
          consent INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
          name TEXT NOT NULL, phone TEXT NOT NULL, body TEXT NOT NULL,
          response TEXT NOT NULL DEFAULT '', public_token TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customers (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
          first_driver_id INTEGER NOT NULL REFERENCES drivers(id),
          station TEXT NOT NULL, registered_at TEXT NOT NULL,
          consent_at TEXT NOT NULL, marketing_opt_in INTEGER NOT NULL DEFAULT 0,
          phone_verified INTEGER NOT NULL DEFAULT 0,
          source TEXT NOT NULL DEFAULT 'QR conductor'
        );
        CREATE INDEX IF NOT EXISTS idx_customers_first_driver ON customers(first_driver_id);
        CREATE TABLE IF NOT EXISTS customer_accounts (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, phone_verified INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, consent_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_customer_accounts_phone ON customer_accounts(phone);
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY, created_at TEXT, actor TEXT, action TEXT, detail TEXT
        );
        CREATE TABLE IF NOT EXISTS incidents (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
          actor TEXT NOT NULL, driver_id INTEGER NOT NULL REFERENCES drivers(id),
          trip_id INTEGER REFERENCES trips(id), type TEXT NOT NULL, details TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','reviewed')),
          reviewed_by TEXT, reviewed_at TEXT
        );
        ''')
        # Upgrade existing 0.2 databases without deleting trips or credentials.
        trip_columns = {c[1] for c in db.execute('PRAGMA table_info(trips)')}
        if 'pickup_accuracy_m' not in trip_columns:
            db.execute('ALTER TABLE trips ADD COLUMN pickup_accuracy_m REAL')
        if 'customer_id' not in trip_columns:
            db.execute('ALTER TABLE trips ADD COLUMN customer_id INTEGER REFERENCES customer_accounts(id)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_trips_customer_id ON trips(customer_id)')
        driver_columns = {c[1] for c in db.execute('PRAGMA table_info(drivers)')}
        if 'rejected_count' not in driver_columns:
            db.execute('ALTER TABLE drivers ADD COLUMN rejected_count INTEGER NOT NULL DEFAULT 0')
        if 'referral_token' not in driver_columns:
            db.execute('ALTER TABLE drivers ADD COLUMN referral_token TEXT')
        if 'plate' not in driver_columns:
            db.execute("ALTER TABLE drivers ADD COLUMN plate TEXT NOT NULL DEFAULT ''")
        if 'photo_bytes' not in driver_columns:
            db.execute('ALTER TABLE drivers ADD COLUMN photo_bytes BLOB')
        if 'photo_mime' not in driver_columns:
            db.execute('ALTER TABLE drivers ADD COLUMN photo_mime TEXT')
        for column,sql in {
            'vehicle_make':"TEXT NOT NULL DEFAULT ''",
            'vehicle_model':"TEXT NOT NULL DEFAULT ''",
            'vehicle_color':"TEXT NOT NULL DEFAULT ''",
            'vehicle_year':'INTEGER',
            'location_source':"TEXT NOT NULL DEFAULT 'simulated'",
            'location_accuracy_m':'REAL',
        }.items():
            if column not in driver_columns:
                db.execute(f'ALTER TABLE drivers ADD COLUMN {column} {sql}')
        if 'offer_expires_at' not in trip_columns:
            db.execute('ALTER TABLE trips ADD COLUMN offer_expires_at TEXT')
        if 'cancelled_by' not in trip_columns:
            db.execute('ALTER TABLE trips ADD COLUMN cancelled_by TEXT')
        if 'cancel_reason' not in trip_columns:
            db.execute('ALTER TABLE trips ADD COLUMN cancel_reason TEXT')
        db.execute("""CREATE TABLE IF NOT EXISTS driver_shifts (
            id INTEGER PRIMARY KEY, driver_id INTEGER NOT NULL REFERENCES drivers(id),
            started_at TEXT NOT NULL, ended_at TEXT, started_by TEXT NOT NULL, ended_by TEXT
        )""")
        db.execute('CREATE INDEX IF NOT EXISTS idx_driver_shifts_driver ON driver_shifts(driver_id,started_at)')
        db.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO app_settings(key,value) VALUES ('dispatch_mode','manual')")
        db.execute("""CREATE TABLE IF NOT EXISTS trip_offer_history (
            id INTEGER PRIMARY KEY,trip_id INTEGER NOT NULL REFERENCES trips(id),
            driver_id INTEGER NOT NULL REFERENCES drivers(id),offered_at TEXT NOT NULL,
            mode TEXT NOT NULL,UNIQUE(trip_id,driver_id)
        )""")
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_drivers_referral_token ON drivers(referral_token)')
        if db.execute('SELECT COUNT(*) FROM drivers').fetchone()[0] == 0:
            db.executemany('INSERT INTO drivers(unit,name,station,lat,lng,status,updated_at) VALUES (?,?,?,?,?,?,?)',
                           [(*d,utcnow()) for d in DEMO_DRIVERS])
        for row in db.execute('SELECT id FROM drivers WHERE referral_token IS NULL').fetchall():
            db.execute('UPDATE drivers SET referral_token=? WHERE id=?', (referral_token(), row['id']))
        if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
            creds = [('admin','admin',None),('operador','operator',None),('conductor1','driver',1),('conductor7','driver',7)]
            lines = ['METRO TAXI · CREDENCIALES TEMPORALES LOCALES',
                     'NO COMPARTIR ESTE ARCHIVO, NO SUBIR A GITHUB',
                     'Generadas: '+utcnow(), '']
            for user,role,did in creds:
                password = secrets.token_urlsafe(12)
                db.execute('INSERT INTO users(username,password_hash,role,driver_id) VALUES (?,?,?,?)',
                           (user,password_hash(password),role,did))
                lines.append(f'{user} ({role}) -> {password}')
            path = RUN / 'credenciales_iniciales.txt'
            path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            try: os.chmod(path, 0o600)
            except OSError: pass
            print('\n[METRO TAXI] Contraseñas locales: '+str(path)+'\n',flush=True)
        if db.execute('SELECT COUNT(*) FROM trips').fetchone()[0] == 0:
            db.executemany('INSERT INTO trips(created_at,name,phone,station,pickup,destination,reference,consent) VALUES (?,?,?,?,?,?,?,1)',[
                (utcnow(),'Pasajero DEMO A','NO REAL','24 de Diciembre','Punto de prueba A','Destino por definir','Datos ficticios'),
                (utcnow(),'Pasajero DEMO B','NO REAL','Pacora','Punto de prueba B','Destino por definir','Datos ficticios')
            ])
        db.commit()


def audit(db,actor,action,detail):
    db.execute('INSERT INTO audit(created_at,actor,action,detail) VALUES (?,?,?,?)',
               (utcnow(),actor,action,json.dumps(detail,ensure_ascii=False)))


def public_driver(row):
    data={k:row[k] for k in ('id','unit','name','station','lat','lng','status','suspended','simulated','updated_at','completed','rejected_count','plate','vehicle_make','vehicle_model','vehicle_color','vehicle_year','location_source','location_accuracy_m')}
    data['has_photo']=bool(row['photo_bytes'])
    return data


def trip_dict(row, role):
    fields=['id','created_at','station','pickup','destination','reference','province','district','corregimiento',
            'location_pending','community','barriada','street','house','pickup_lat','pickup_lng','dest_lat','dest_lng','pickup_accuracy_m',
            'price','status','driver_id','channel','offer_expires_at','cancel_reason']
    if role in ('admin','operator'):
        fields += ['name','phone']
    elif role == 'driver' and row['driver_id']:
        fields += ['name'] # Never expose passenger phone to driver: central manages contact
    return {k:row[k] for k in fields}


def clean_text(v, maxlength=180):
    if not isinstance(v,str):return ''
    return re.sub(r'[\x00-\x1f\x7f]', ' ', v).strip()[:maxlength]


def maybe_coord(v, limit):
    if v in (None, ''): return None
    if isinstance(v, bool): raise ValueError('Coordenada inválida')
    try: f=float(v)
    except (TypeError,ValueError): raise ValueError('Coordenada inválida')
    if not -limit<=f<=limit or f!=f:raise ValueError('Coordenada fuera de rango')
    return round(f, 7)


def optional_accuracy(v, has_coords):
    # Browser-reported GPS accuracy is an estimate, not verified location proof.
    if v in (None, ''): return None
    if not has_coords or isinstance(v, bool): raise ValueError('Precisión GPS inválida')
    try: x=float(v)
    except (ValueError, TypeError): raise ValueError('Precisión GPS inválida')
    if not (0 <= x <= 10000): raise ValueError('Precisión GPS fuera de rango')
    return round(x,1)


def location_fields(body):
    out = {}
    for f in ('pickup_lat','dest_lat'):
        out[f] = maybe_coord(body.get(f),90)
    for f in ('pickup_lng','dest_lng'):
        out[f] = maybe_coord(body.get(f),180)
    for prefix in ('pickup','dest'):
        if (out[prefix+'_lat'] is None)!=(out[prefix+'_lng'] is None):
            raise ValueError('Latitud y longitud deben enviarse juntas')
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = 'MetroTaxiDemo/0.8.2'
    def log_message(self,fmt,*args):
        print('[HTTP]',fmt%args)
    def send_json(self,obj,status=200,cookie=None):
        raw=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def fail(self,code,msg):self.send_json({'error':msg},code)
    def get_session(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except Exception:return None
        token=cookie.get('metro_sid')
        if not token:return None
        s=SESSIONS.get(token.value)
        if s and s['exp']>time.time():return s
        return None
    def require(self,roles):
        sess=self.get_session()
        if not sess:self.fail(401,'Inicia sesión para acceder');return None
        if sess['role'] not in roles:self.fail(403,'No autorizado para esta función');return None
        return sess
    def read_json(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            limit=400000 if urlparse(self.path).path=='/api/drivers/profile' else 16000
            if n<1 or n>limit:raise ValueError('Tamaño no válido')
            body=json.loads(self.rfile.read(n))
            if not isinstance(body,dict):raise ValueError('Se esperaba objeto JSON')
            return body
        except (ValueError,json.JSONDecodeError) as e:
            self.fail(400,'JSON incorrecto o excede tamaño')
            return None
    def csrf_ok(self):
        sess=self.get_session()
        if sess:
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),sess['csrf']):
                self.send_json({'error':'El código de seguridad de sesión no coincide. Se intentará renovarlo.','code':'CSRF_INVALID'},403);return False
        origin=self.headers.get('Origin')
        if origin:
            target=urlparse(origin)
            if target.netloc!=self.headers.get('Host') or target.scheme not in ('http','https'):
                self.fail(403,'Origen no autorizado');return False
        return True
    def do_GET(self):
        p=urlparse(self.path).path
        if p.startswith('/api/'):
            return self.api_get(p)
        if p=='/central':
            s=self.get_session()
            if not s:return self.redirect('/ingresar')
            if s['role']=='customer':return self.redirect('/cliente')
            if s['role']=='driver':return self.redirect('/conductor')
            if s['role'] not in ('admin','operator'):return self.redirect('/ingresar')
            return self.serve('central.html')
        if re.fullmatch(r'/registro/[A-Za-z0-9_-]{20,64}',p):
            return self.serve('registro.html')
        if p=='/conductor':
            s=self.get_session()
            if not s:return self.redirect('/ingresar')
            if s['role']=='customer':return self.redirect('/cliente')
            if s['role'] in ('admin','operator'):return self.redirect('/central')
            if s['role']!='driver':return self.redirect('/ingresar')
            return self.serve('conductor.html')
        if p in ('/','/cliente'):return self.serve('cliente.html')
        if p=='/ingresar':return self.serve('ingresar.html')
        if p in ('/static/app.css','/static/app.js','/static/office.js','/static/driver.js','/static/navigation.js','/static/client.js','/static/auth.js','/static/referral.js','/static/metro-icon.svg','/static/metro-icon-192.png','/static/metro-icon-512.png','/sw.js','/manifest-cliente.webmanifest','/manifest-conductor.webmanifest'):
            return self.serve(p.lstrip('/'))
        self.fail(404,'Ruta no encontrada')
    def redirect(self,path):
        self.send_response(302)
        self.send_header('Location',path)
        self.send_header('Cache-Control','no-store')
        self.end_headers()
    def serve(self,path):
        f=(ROOT/path).resolve()
        if ROOT not in f.parents or not f.is_file():return self.fail(404,'Archivo no encontrado')
        data=f.read_bytes()
        content={'html':'text/html','js':'text/javascript','css':'text/css','svg':'image/svg+xml','png':'image/png','webmanifest':'application/manifest+json'}.get(f.suffix.lstrip('.'),'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type',content+'; charset=utf-8')
        self.send_header('Cache-Control','no-store' if path in ('ingresar.html','central.html','conductor.html','static/app.js','static/client.js','static/referral.js','static/auth.js','static/office.js','static/driver.js','static/navigation.js') else 'no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy','geolocation=(self)')
        self.send_header('Content-Security-Policy',
            "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' https://unpkg.com; "
            "img-src 'self' data: https:; connect-src 'self'; font-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def api_get(self,p):
        if p=='/api/me':
            s=self.get_session()
            return self.send_json({'authenticated':bool(s),'user':{'username':s['username'],'role':s['role'],'driver_id':s.get('driver_id'),'customer_id':s.get('customer_id')} if s else None,'csrf':s['csrf'] if s else None})
        if p=='/api/config':
            url=os.environ.get('MAP_TILE_URL','https://tile.openstreetmap.org/{z}/{x}/{y}.png')
            if not url.startswith('https://') or not all(x in url for x in ('{z}','{x}','{y}')):
                url='https://tile.openstreetmap.org/{z}/{x}/{y}.png'
            whatsapp=os.environ.get('METRO_WHATSAPP_NUMBER','').strip()
            if not re.fullmatch(r'\d{8,15}',whatsapp):whatsapp=''
            return self.send_json({'tile_url':url,'attribution':os.environ.get('MAP_ATTRIBUTION','<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>'),
                    'max_zoom':max(5,min(20,int(os.environ.get('MAP_MAX_ZOOM','19')))),
                    'whatsapp':whatsapp,'demo':True,'catalog':{'fuente':CATALOG['fuente'],'fecha_base':CATALOG['fecha_base'],
                    'fecha_consulta':CATALOG['fecha_consulta'],'alcance':CATALOG['alcance'],'url':CATALOG['url']}})
        if p=='/api/catalog':return self.send_json(CATALOG)
        if p in ('/api/customer/trips','/api/mine','/api/trips','/api/fleet'):
            expire_offers()
            dispatch_cycle()
        if p=='/api/customer/trips':
            sess=self.require(('customer',))
            if not sess:return
            with connect() as db:
                account=db.execute('SELECT name,phone,phone_verified FROM customer_accounts WHERE id=?',(sess['customer_id'],)).fetchone()
                if not account:return self.fail(401,'Cuenta no disponible')
                rows=db.execute('''SELECT t.id,t.created_at,t.station,t.pickup,t.destination,t.status,t.price,
                           t.driver_id,d.unit,d.name AS driver_name,d.plate,d.photo_bytes,d.vehicle_make,d.vehicle_model,d.vehicle_color,d.vehicle_year,d.simulated,d.location_source,d.location_accuracy_m,d.lat,d.lng,d.updated_at,d.status AS driver_status
                           FROM trips t LEFT JOIN drivers d ON d.id=t.driver_id
                           WHERE t.customer_id=? ORDER BY t.id DESC LIMIT 100''',(sess['customer_id'],)).fetchall()
            trips=[]
            for r in rows:
                item={k:r[k] for k in ('id','created_at','station','pickup','destination','status','price')}
                if r['driver_id'] is not None and r['status'] in ('offered','accepted','inprogress'):
                    item['driver']={'name':r['driver_name'],'unit':r['unit'], 'plate':r['plate'] or '',
                                    'vehicle_make':r['vehicle_make'],'vehicle_model':r['vehicle_model'],
                                    'vehicle_color':r['vehicle_color'],'vehicle_year':r['vehicle_year'],
                                    'confirmed':r['status'] in ('accepted','inprogress'),
                                    'photo_url':f"/api/driver-photo/{r['driver_id']}" if r['photo_bytes'] else None}
                    if r['status'] in ('accepted','inprogress'):
                        coords=live_position(r)
                        if coords:item['driver']['location']=coords
                        else:item['driver']['location_notice']='Sin posición GPS reciente del conductor'
                elif r['driver_id'] is not None and r['status']=='done':
                    item['driver']={'name':r['driver_name'],'unit':r['unit'],'plate':'','photo_url':None}
                trips.append(item)
            return self.send_json({'account':dict(account),'trips':trips,
              'notice':'Solo carreras de esta cuenta; las anteriores al registro no se vinculan automáticamente.'})
        if re.fullmatch(r'/api/driver-photo/\d+',p):
            sess=self.get_session()
            if not sess:return self.fail(401,'Inicia sesión para ver fotografías autorizadas')
            did=int(p.rsplit('/',1)[-1]);role=sess['role']
            if role=='driver' and sess.get('driver_id')!=did:return self.fail(403,'No autorizado')
            if role=='customer':
                with connect() as db:
                    belongs=db.execute("""SELECT 1 FROM trips WHERE customer_id=? AND driver_id=?
                       AND status IN ('offered','accepted','inprogress') LIMIT 1""",(sess['customer_id'],did)).fetchone()
                if not belongs:return self.fail(403,'Foto disponible solo para tu conductor asignado')
            elif role not in ('admin','operator','driver'):
                return self.fail(403,'No autorizado')
            with connect() as db:
                driver=db.execute('SELECT photo_bytes,photo_mime FROM drivers WHERE id=?',(did,)).fetchone()
            if not driver or not driver['photo_bytes']:return self.fail(404,'Fotografía pendiente de carga')
            content=driver['photo_bytes']
            self.send_response(200)
            self.send_header('Content-Type',driver['photo_mime'])
            self.send_header('Cache-Control','private, no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(content)))
            self.end_headers();self.wfile.write(content);return
        if re.fullmatch(r'/api/referral/[A-Za-z0-9_-]{20,64}',p):
            tok=p.rsplit('/',1)[1]
            with connect() as db:
                dr=db.execute('SELECT unit,station,suspended FROM drivers WHERE referral_token=?',(tok,)).fetchone()
            if not dr or dr['suspended']:
                return self.fail(404,'Código QR no vigente')
            return self.send_json({'company':'Metro Taxi','unit':dr['unit'],'station':dr['station'],
                'status':'active','notice':'Registro de cliente sin verificación de teléfono; la central administra las carreras'})
        if p=='/api/referral/qr.svg':
            s=self.require(('driver',))
            if not s:return
            if qrcode is None:
                return self.fail(503,'Librería QR no instalada. Ejecuta pip install -r requirements.txt')
            with connect() as db:
                dr=db.execute('SELECT referral_token,suspended FROM drivers WHERE id=?',(s['driver_id'],)).fetchone()
            if not dr or dr['suspended']:
                return self.fail(403,'Código QR desactivado')
            target=referral_base(self.server.server_port)+'/registro/'+dr['referral_token']
            qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=8)
            qr.add_data(target)
            qr.make(fit=True)
            svg=qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).to_string()
            self.send_response(200)
            self.send_header('Content-Type','image/svg+xml; charset=utf-8')
            self.send_header('Content-Length',str(len(svg)))
            self.send_header('Cache-Control','private, no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'none'; sandbox")
            self.end_headers()
            self.wfile.write(svg)
            return
        if p=='/api/dispatch/settings':
            user=self.require(('admin','operator'))
            if not user:return
            with connect() as db:mode=db.execute("SELECT value FROM app_settings WHERE key='dispatch_mode'").fetchone()[0]
            return self.send_json({'mode':mode,'offer_seconds':max(30,min(600,int(os.environ.get('METRO_OFFER_SECONDS','120')))),
                   'notice':'Asignación automática optativa solo con GPS de conductor reciente; sin GPS se deja en cola.'})
        if p=='/api/dispatch/suggest':
            user=self.require(('admin','operator'))
            if not user:return
            try:tid=int(parse_qs(urlparse(self.path).query).get('trip_id',['0'])[0])
            except ValueError:return self.fail(400,'Carrera inválida')
            with connect() as db:
                trip=db.execute('SELECT * FROM trips WHERE id=?',(tid,)).fetchone()
                if not trip:return self.fail(404,'Carrera no encontrada')
                if trip['status']!='pending':return self.fail(409,'La carrera no está pendiente')
                possible=candidates_for_trip(db,trip)
            return self.send_json({'candidates':possible[:10],'mode':'straight_line','note':'Distancias en línea recta. No son rutas, distancias de conducción ni ETA.'})
        if p=='/api/shifts':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:
                rows=[dict(r) for r in db.execute('SELECT sh.id,d.unit,d.station,sh.started_at,sh.ended_at,sh.started_by,sh.ended_by FROM driver_shifts sh JOIN drivers d ON d.id=sh.driver_id ORDER BY sh.id DESC LIMIT 150')]
            return self.send_json({'shifts':rows,'note':'Turnos de prueba: no son registros biométricos ni nómina'})
        if p=='/api/referrals':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:
                items=[dict(r) for r in db.execute('''SELECT c.id,c.name,c.phone,c.registered_at,c.marketing_opt_in,
                  c.phone_verified,c.source,d.unit,d.station FROM customers c JOIN drivers d ON d.id=c.first_driver_id
                  ORDER BY c.id DESC LIMIT 200''')]
                counts=[dict(r) for r in db.execute('''SELECT d.id,d.unit,d.station,COUNT(c.id) as registered
                  FROM drivers d LEFT JOIN customers c ON c.first_driver_id=d.id GROUP BY d.id ORDER BY d.station,d.unit''')]
            return self.send_json({'customers':items,'by_driver':counts,'notice':'Teléfonos sin verificar; no representa clientes que hicieron carreras'})
        if p=='/api/fleet':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:drivers=[public_driver(r) for r in db.execute('SELECT * FROM drivers ORDER BY unit')]
            return self.send_json({'drivers':drivers,'simulation':True})
        if p=='/api/trips':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:items=[trip_dict(x,s['role']) for x in db.execute('SELECT * FROM trips ORDER BY id DESC LIMIT 300')]
            return self.send_json({'trips':items})
        if p=='/api/stats':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:
                totals=dict(db.execute('''SELECT count(*) AS total,
                   sum(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                   sum(CASE WHEN status='done' THEN 1 ELSE 0 END) AS completed,
                   sum(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) AS cancelled,
                   coalesce(sum(CASE WHEN status='done' THEN price ELSE 0 END),0) AS fares_completed
                   FROM trips''').fetchone())
                by_unit=[dict(r) for r in db.execute('''SELECT d.id,d.unit,d.name,d.station,d.completed,d.rejected_count,d.suspended,
                  count(CASE WHEN t.status='done' THEN 1 END) AS completed_trips,
                  coalesce(sum(CASE WHEN t.status='done' THEN t.price ELSE 0 END),0) AS fares_completed
                  FROM drivers d LEFT JOIN trips t ON t.driver_id=d.id
                  GROUP BY d.id ORDER BY d.station,d.unit''')]
                by_station=[dict(r) for r in db.execute('''SELECT station, count(*) AS total,
                    sum(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                    sum(CASE WHEN status='done' THEN 1 ELSE 0 END) AS completed
                    FROM trips GROUP BY station ORDER BY station''')]
            return self.send_json({'totals':totals,'by_driver':by_unit,'by_station':by_station,'demo':True,
                                   'note':'Tarifas registradas; no representan pagos cobrados'})
        if p=='/api/incidents':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:
                items=[dict(r) for r in db.execute('''SELECT i.*,d.unit,d.name AS driver_name FROM incidents i
                   JOIN drivers d ON d.id=i.driver_id ORDER BY i.id DESC LIMIT 250''')]
            return self.send_json({'incidents':items})
        if p=='/api/messages':
            s=self.require(('admin','operator'))
            if not s:return
            with connect() as db:items=[dict(r) for r in db.execute('SELECT id,created_at,name,phone,body,response FROM messages ORDER BY id DESC LIMIT 100')]
            return self.send_json({'messages':items})
        if p=='/api/mine':
            s=self.require(('driver',))
            if not s:return
            with connect() as db:
                row=db.execute('SELECT * FROM drivers WHERE id=?',(s['driver_id'],)).fetchone()
                trips=[trip_dict(r,'driver') for r in db.execute('SELECT * FROM trips WHERE driver_id=? ORDER BY id DESC',(s['driver_id'],))]
                count=db.execute('SELECT COUNT(*) FROM customers WHERE first_driver_id=?',(s['driver_id'],)).fetchone()[0]
                shift=db.execute('SELECT started_at FROM driver_shifts WHERE driver_id=? AND ended_at IS NULL ORDER BY id DESC LIMIT 1',(s['driver_id'],)).fetchone()
            if not row:return self.fail(404,'Unidad no encontrada')
            url=referral_base(self.server.server_port)+'/registro/'+row['referral_token']
            return self.send_json({'driver':public_driver(row),'trips':trips,'simulation':True,
                'referral_url':url if not row['suspended'] else None,'referral_count':count,
                'active_shift_since':shift['started_at'] if shift else None,'qr_ready':qrcode is not None,'public_link_configured':bool(os.environ.get('METRO_PUBLIC_BASE_URL'))})
        if p.startswith('/api/thread/'):
            token=p[len('/api/thread/'):]
            if not re.fullmatch('[0-9a-f]{64}',token):return self.fail(404,'Hilo no encontrado')
            with connect() as db:r=db.execute('SELECT created_at,body,response FROM messages WHERE public_token=?',(token,)).fetchone()
            if not r:return self.fail(404,'Hilo no encontrado')
            return self.send_json({'thread':dict(r)})
        self.fail(404,'API desconocida')
    def do_POST(self):
        p=urlparse(self.path).path
        if not p.startswith('/api/'):return self.fail(404,'Ruta no encontrada')
        if not self.csrf_ok():return
        data=self.read_json()
        if data is None:return
        if p=='/api/account/password':
            sess=self.require(('admin','operator','driver','customer'))
            if not sess:return
            old=data.get('current_password');new=data.get('new_password')
            if not isinstance(old,str) or not isinstance(new,str) or not (10<=len(new)<=128):
                return self.fail(400,'Contraseña nueva de 10 a 128 caracteres y clave actual obligatorias')
            with DB_LOCK,connect() as db:
                if sess['role']=='customer':
                    r=db.execute('SELECT password_hash FROM customer_accounts WHERE id=?',(sess['customer_id'],)).fetchone()
                else:r=db.execute('SELECT password_hash FROM users WHERE username=?',(sess['username'],)).fetchone()
                if not r or not valid_password(old,r['password_hash']):return self.fail(403,'Contraseña actual incorrecta')
                if hmac.compare_digest(old,new):return self.fail(400,'La nueva contraseña debe ser distinta')
                if sess['role']=='customer':db.execute('UPDATE customer_accounts SET password_hash=? WHERE id=?',(password_hash(new),sess['customer_id']))
                else:db.execute('UPDATE users SET password_hash=? WHERE username=?',(password_hash(new),sess['username']))
                audit(db,sess['username'],'password_changed',{'role':sess['role']})
                db.commit()
            for token,x in list(SESSIONS.items()):
                if sess['role']=='customer':
                    if x.get('role')=='customer' and x.get('customer_id')==sess['customer_id']:SESSIONS.pop(token,None)
                elif x.get('role')==sess['role'] and x.get('username')==sess['username']:
                    SESSIONS.pop(token,None)
            return self.send_json({'ok':True,'notice':'Contraseña actualizada; inicia sesión nuevamente'},
                    cookie='metro_sid=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if p=='/api/dispatch/settings':
            user=self.require(('admin',))
            if not user:return
            mode=clean_text(data.get('mode'),30)
            if mode not in ('manual','auto_after_120s'):return self.fail(400,'Modo incorrecto')
            with DB_LOCK,connect() as db:
                db.execute("UPDATE app_settings SET value=? WHERE key='dispatch_mode'",(mode,))
                audit(db,user['username'],'dispatch_mode_changed',{'mode':mode})
                db.commit()
            return self.send_json({'ok':True,'mode':mode})
        if p=='/api/driver/location':
            sess=self.require(('driver',))
            if not sess:return
            if data.get('consent') is not True:return self.fail(400,'Activa voluntariamente el envío GPS')
            try:
                lat=maybe_coord(data.get('lat'),90);lng=maybe_coord(data.get('lng'),180)
                acc=optional_accuracy(data.get('accuracy_m'),True)
            except ValueError as e:return self.fail(400,str(e))
            if lat is None or lng is None or acc is None or not (5<=lat<=12 and -85<=lng<=-76):
                return self.fail(400,'Coordenadas o precisión GPS inválidas para el área de prueba')
            with DB_LOCK,connect() as db:
                d=db.execute('SELECT status,suspended FROM drivers WHERE id=?',(sess['driver_id'],)).fetchone()
                if not d or d['suspended'] or d['status']=='off':return self.fail(409,'Primero ponte de servicio')
                db.execute('UPDATE drivers SET lat=?,lng=?,simulated=0,location_source="device", location_accuracy_m=?,updated_at=? WHERE id=?',
                           (lat,lng,acc,utcnow(),sess['driver_id']))
                db.commit()
            return self.send_json({'ok':True,'updated_at':utcnow(),'accuracy_m':acc,
                                   'note':'GPS de navegador; puede detenerse si minimizas o bloqueas el teléfono'})
        if p=='/api/driver/location/stop':
            sess=self.require(('driver',))
            if not sess:return
            with DB_LOCK,connect() as db:
                db.execute("UPDATE drivers SET lat=NULL,lng=NULL,simulated=0,location_source='none',location_accuracy_m=NULL,updated_at=? WHERE id=?",
                           (utcnow(),sess['driver_id']))
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/trips/cancel':
            sess=self.require(('admin','operator','customer'))
            if not sess:return
            try:tid=int(data.get('trip_id',0))
            except (TypeError,ValueError):return self.fail(400,'Carrera inválida')
            reason=clean_text(data.get('reason'),160) or 'Sin motivo adicional'
            with DB_LOCK,connect() as db:
                t=db.execute('SELECT * FROM trips WHERE id=?',(tid,)).fetchone()
                if not t:return self.fail(404,'Carrera no encontrada')
                if sess['role']=='customer' and t['customer_id']!=sess['customer_id']:return self.fail(404,'Carrera no encontrada')
                if t['status'] in ('done','cancelled'):return self.fail(409,'Carrera ya cerrada')
                if sess['role']=='customer' and t['status'] not in ('pending','offered'):
                    return self.fail(403,'Solicita a la central la cancelación de un viaje en curso')
                if t['status']=='inprogress' and sess['role'] not in ('admin','operator'):
                    return self.fail(403,'Contacta a la central')
                actor=sess['username']
                db.execute("UPDATE trips SET status='cancelled',cancelled_by=?,cancel_reason=?,offer_expires_at=NULL WHERE id=?",
                           (actor,reason,tid))
                if t['driver_id'] is not None:
                    db.execute("UPDATE drivers SET status='available' WHERE id=? AND status='busy'",(t['driver_id'],))
                audit(db,actor,'trip_cancelled',{'trip_id':tid,'reason':reason})
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/customer/register':
            name=clean_text(data.get('name'),80)
            phone=phone_normalized(data.get('phone'))
            password=data.get('password','')
            if not isinstance(password,str):password=''
            if len(name)<2 or not phone or not 10<=len(password)<=128 or data.get('consent') is not True:
                return self.fail(400,'Nombre, teléfono panameño, contraseña de 10 caracteres y consentimiento obligatorios')
            key=self.client_address[0];now=time.monotonic()
            with DB_LOCK:
                attempts=[t for t in CUSTOMER_LIMITS.get(key,[]) if now-t<3600]
                if len(attempts)>=20:return self.fail(429,'Demasiados intentos de registro en esta demo')
                CUSTOMER_LIMITS[key]=attempts+[now]
            with DB_LOCK,connect() as db:
                try:
                    cur=db.execute('INSERT INTO customer_accounts(name,phone,password_hash,created_at,consent_at) VALUES (?,?,?,?,?)',
                        (name,phone,password_hash(password),utcnow(),utcnow()))
                except sqlite3.IntegrityError:
                    return self.fail(409,'Ya existe una cuenta con ese número; inicia sesión')
                cid=cur.lastrowid
                audit(db,'cuenta_publica','customer_account_created',{'customer_id':cid,'phone_verified':False})
                db.commit()
            token=secrets.token_urlsafe(40)
            SESSIONS[token]={'username':name,'role':'customer','customer_id':cid,'driver_id':None,
                             'csrf':secrets.token_urlsafe(32),'exp':time.time()+8*3600}
            return self.send_json({'ok':True,'phone_verified':False,'notice':'Cuenta DEMO creada; teléfono SIN verificar.'},201,
                cookie=f'metro_sid={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
        if p=='/api/customer/login':
            phone=phone_normalized(data.get('phone'))
            password=data.get('password','')
            if not isinstance(password,str):password=''
            with connect() as db:
                account=db.execute('SELECT * FROM customer_accounts WHERE phone=?',(phone,)).fetchone() if phone else None
            if not account or not valid_password(password,account['password_hash']):
                return self.fail(401,'Teléfono o contraseña incorrectos')
            token=secrets.token_urlsafe(40)
            SESSIONS[token]={'username':account['name'],'role':'customer','customer_id':account['id'],
                             'driver_id':None,'csrf':secrets.token_urlsafe(32),'exp':time.time()+8*3600}
            return self.send_json({'ok':True,'phone_verified':bool(account['phone_verified'])},
                cookie=f'metro_sid={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
        if p=='/api/login':
            username=clean_text(data.get('username'),50)
            password=data.get('password','')
            if not isinstance(password,str):password=''
            with connect() as db:r=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            if not r or not valid_password(password,r['password_hash']):return self.fail(401,'Credenciales incorrectas')
            token=secrets.token_urlsafe(40)
            s={'username':r['username'],'role':r['role'],'driver_id':r['driver_id'],'csrf':secrets.token_urlsafe(32),'exp':time.time()+8*3600}
            SESSIONS[token]=s
            return self.send_json({'role':s['role'],'username':s['username']},cookie=f'metro_sid={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
        if p=='/api/logout':
            c=SimpleCookie()
            try:c.load(self.headers.get('Cookie',''))
            except Exception:pass
            if c.get('metro_sid'):SESSIONS.pop(c['metro_sid'].value,None)
            return self.send_json({'ok':True},cookie='metro_sid=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if p=='/api/referrals/register':
            tok=clean_text(data.get('token'),64)
            if not re.fullmatch(r'[A-Za-z0-9_-]{20,64}',tok):
                return self.fail(400,'Código QR inválido')
            name=clean_text(data.get('name'),80)
            phone=phone_normalized(data.get('phone'))
            consent=data.get('consent') is True
            marketing=data.get('marketing_opt_in') is True
            if len(name)<2 or not phone or not consent:
                return self.fail(400,'Completa nombre, teléfono panameño y acepta el registro de tus datos')
            key=(self.client_address[0],tok)
            now=time.monotonic()
            with DB_LOCK:
                attempts=[t for t in REFERRAL_LIMITS.get(key,[]) if now-t<3600]
                if len(attempts)>=30:
                    return self.fail(429,'Demasiados registros; intenta luego o comunícate con la central')
                REFERRAL_LIMITS[key]=attempts+[now]
            with DB_LOCK,connect() as db:
                dr=db.execute('SELECT id,station,suspended FROM drivers WHERE referral_token=?',(tok,)).fetchone()
                if not dr or dr['suspended']:
                    return self.fail(404,'Código QR no vigente')
                try:
                    db.execute('''INSERT INTO customers(name,phone,first_driver_id,station,registered_at,
                        consent_at,marketing_opt_in) VALUES (?,?,?,?,?,?,?)''',
                        (name,phone,dr['id'],dr['station'],utcnow(),utcnow(),int(marketing)))
                    audit(db,'registro_publico','customer_referral_created',{'driver_id':dr['id']})
                except sqlite3.IntegrityError:
                    # Avoid disclosing if a phone belongs to an existing customer.
                    audit(db,'registro_publico','duplicate_referral_phone',{'driver_id':dr['id']})
                db.commit()
            return self.send_json({'ok':True,'message':'Solicitud recibida por Metro Taxi. La central verificará el contacto; el QR no crea una carrera.',
                'phone_verified':False},201)
        if p=='/api/requests':
            try:
                coords=location_fields(data)
                accuracy=optional_accuracy(data.get('pickup_accuracy_m'),coords['pickup_lat'] is not None)
            except ValueError as e:return self.fail(400,str(e))
            name=clean_text(data.get('name'),80)
            phone=clean_text(data.get('phone'),30)
            sess=self.get_session()
            customer_id=None
            if sess and sess['role']=='customer':
                with connect() as db:
                    owner=db.execute('SELECT id,name,phone FROM customer_accounts WHERE id=?',(sess['customer_id'],)).fetchone()
                if not owner:return self.fail(401,'Cuenta de cliente no disponible')
                customer_id=owner['id']
                name=owner['name'];phone=owner['phone']
            pickup=clean_text(data.get('pickup'),150)
            dest=clean_text(data.get('destination'),150)
            station=clean_text(data.get('station'),50)
            if not name or not phone or not pickup or station not in ('Pacora','24 de Diciembre') or data.get('consent') is not True:
                return self.fail(400,'Nombre, teléfono, recogida, sede y consentimiento obligatorios')
            province=clean_text(data.get('province'),80)
            district=clean_text(data.get('district'),80)
            corr=clean_text(data.get('corregimiento'),80)
            pending=clean_text(data.get('location_pending'),150)
            # Validate official catalog paths. Unknown address labels remain explicitly pending.
            territory=CATALOG['provincias_comarcas']
            if province and province not in territory:return self.fail(400,'Provincia o comarca no reconocida')
            if province and district and district not in territory[province] and not pending:
                return self.fail(400,'Distrito fuera del catálogo piloto: usa pendiente de verificación')
            if province and district in territory[province] and corr and corr not in territory[province][district] and not pending:
                return self.fail(400,'Corregimiento fuera del catálogo piloto: usa pendiente de verificación')
            extra={f:clean_text(data.get(f),150) for f in ('reference','community','barriada','street','house')}
            # A QR originated request still belongs to the central, never the referring driver.
            # Only a currently valid QR token may label a request as QR-sourced.
            # No private passenger contact details go into the driver's session/API.
            qr_token=clean_text(data.get('referral_token'),64)
            channel='Web cliente'
            if re.fullmatch(r'[A-Za-z0-9_-]{20,64}',qr_token):
                with connect() as db:
                    qr_owner=db.execute('SELECT id FROM drivers WHERE referral_token=? AND suspended=0',
                                        (qr_token,)).fetchone()
                if qr_owner:
                    channel='Web QR Metro Taxi'
            with DB_LOCK,connect() as db:
                c=db.execute('''INSERT INTO trips(created_at,name,phone,station,pickup,destination,reference,
                  province,district,corregimiento,location_pending,community,barriada,street,house,
                  pickup_lat,pickup_lng,dest_lat,dest_lng,pickup_accuracy_m,consent,channel,customer_id)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)''',
                  (utcnow(),name,phone,station,pickup,dest,extra['reference'],province,district,corr,pending,
                   extra['community'],extra['barriada'],extra['street'],extra['house'],
                   coords['pickup_lat'],coords['pickup_lng'],coords['dest_lat'],coords['dest_lng'],accuracy,channel,customer_id))
                audit(db,'cliente','request_created',{'trip_id':c.lastrowid,'channel':channel})
                db.commit()
            return self.send_json({'ok':True,'id':c.lastrowid,'status':'pending','note':'Solo la central gestiona esta carrera'},201)
        if p=='/api/contact':
            name=clean_text(data.get('name'),80)
            phone=clean_text(data.get('phone'),30)
            msg=clean_text(data.get('message'),1000)
            if not name or not phone or not msg:return self.fail(400,'Completa nombre, teléfono y mensaje')
            token=secrets.token_hex(32)
            with DB_LOCK,connect() as db:
                c=db.execute('INSERT INTO messages(created_at,name,phone,body,public_token) VALUES (?,?,?,?,?)',
                             (utcnow(),name,phone,msg,token))
                audit(db,'cliente','contact_created',{'message_id':c.lastrowid})
                db.commit()
            return self.send_json({'ok':True,'id':c.lastrowid,'token':token},201)
        if p=='/api/trips/manual':
            s=self.require(('admin','operator'))
            if not s:return
            name=clean_text(data.get('name'),80)
            phone=clean_text(data.get('phone'),30)
            pickup=clean_text(data.get('pickup'),150)
            dest=clean_text(data.get('destination'),150)
            station=clean_text(data.get('station'),50)
            channel=clean_text(data.get('channel'),30)
            reference=clean_text(data.get('reference'),150)
            if not all((name,phone,pickup)) or station not in ('Pacora','24 de Diciembre') or channel not in ('Llamada','WhatsApp','Presencial'):
                return self.fail(400,'Completa nombre, teléfono, recogida, sede y canal permitido')
            if data.get('consent') is not True:
                return self.fail(400,'Confirma que el cliente fue informado del registro de datos')
            try:coords=location_fields(data)
            except ValueError as e:return self.fail(400,str(e))
            with DB_LOCK, connect() as db:
                c=db.execute('''INSERT INTO trips(created_at,name,phone,station,pickup,destination,reference,
                   pickup_lat,pickup_lng,dest_lat,dest_lng,channel,consent)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)''',
                   (utcnow(),name,phone,station,pickup,dest,reference,coords['pickup_lat'],coords['pickup_lng'],
                    coords['dest_lat'],coords['dest_lng'],channel))
                audit(db,s['username'],'manual_trip_created',{'trip_id':c.lastrowid,'channel':channel})
                db.commit()
            return self.send_json({'ok':True,'id':c.lastrowid,'status':'pending'},201)
        if p=='/api/trips/price':
            s=self.require(('admin','operator'))
            if not s:return
            try:
                tid=int(data.get('trip_id',0))
                amount=float(data.get('price'))
            except (ValueError,TypeError):return self.fail(400,'Precio numérico obligatorio')
            if not 0 < amount <= 1000 or amount != amount or amount == float('inf'):
                return self.fail(400,'Precio fuera del rango permitido para esta demostración')
            amount=round(amount,2)
            with DB_LOCK, connect() as db:
                r=db.execute('SELECT status FROM trips WHERE id=?',(tid,)).fetchone()
                if not r:return self.fail(404,'Carrera inexistente')
                if r['status']=='cancelled':return self.fail(409,'No registrar tarifa en carrera cancelada')
                db.execute('UPDATE trips SET price=? WHERE id=?',(amount,tid))
                audit(db,s['username'],'fare_recorded',{'trip_id':tid,'amount':amount})
                db.commit()
            return self.send_json({'ok':True,'price':amount})
        if p=='/api/drivers/create':
            s=self.require(('admin',))
            if not s:return
            unit=clean_text(data.get('unit'),15).upper()
            name=clean_text(data.get('name'),80)
            station=clean_text(data.get('station'),50)
            username=clean_text(data.get('username'),50).lower()
            if not re.fullmatch(r'MT-[0-9A-Z]{2,6}',unit) or not name or station not in ('Pacora','24 de Diciembre') or not re.fullmatch('[a-z][a-z0-9_.]{3,29}',username):
                return self.fail(400,'Verifica unidad (MT-XX), conductor, sede y usuario (4-30 caracteres)')
            password=secrets.token_urlsafe(16)
            try:
                with DB_LOCK, connect() as db:
                    cursor=db.execute('''INSERT INTO drivers(unit,name,station,lat,lng,status,simulated,updated_at)
                       VALUES (?,?,?,NULL,NULL,'off',0,?)''',(unit,name,station,utcnow()))
                    did=cursor.lastrowid
                    db.execute('INSERT INTO users(username,password_hash,role,driver_id) VALUES (?,?,?,?)',
                               (username,password_hash(password),'driver',did))
                    db.execute('UPDATE drivers SET referral_token=? WHERE id=?',(referral_token(),did))
                    audit(db,s['username'],'driver_created',{'driver_id':did,'unit':unit,'username':username})
                    db.commit()
            except sqlite3.IntegrityError:
                return self.fail(409,'Ya existe esa unidad o usuario')
            # Shown once to administrator. Never written in a document or sent to a driver from the app.
            return self.send_json({'ok':True,'driver_id':did,'username':username,'temporary_password':password},201)
        if p=='/api/referrals/rotate':
            s=self.require(('admin',))
            if not s:return
            try:did=int(data.get('driver_id',0))
            except (TypeError,ValueError):return self.fail(400,'Conductor inválido')
            with DB_LOCK,connect() as db:
                if not db.execute('SELECT 1 FROM drivers WHERE id=?',(did,)).fetchone():
                    return self.fail(404,'Conductor inexistente')
                db.execute('UPDATE drivers SET referral_token=? WHERE id=?',(referral_token(),did))
                audit(db,s['username'],'referral_rotated',{'driver_id':did})
                db.commit()
            return self.send_json({'ok':True,'note':'QR anterior desactivado y QR nuevo disponible para el conductor'})
        if p=='/api/incidents':
            s=self.require(('admin','operator'))
            if not s:return
            try:
                did=int(data.get('driver_id',0))
                tid=data.get('trip_id')
                tid=int(tid) if tid not in (None,'') else None
            except (TypeError,ValueError):return self.fail(400,'Identificador inválido')
            kind=clean_text(data.get('type'),30)
            details=clean_text(data.get('details'),600)
            if kind not in ('rechazo','no_se_presento','queja','otro') or len(details)<8:
                return self.fail(400,'Selecciona el tipo y escribe detalles (mínimo 8 caracteres)')
            with DB_LOCK, connect() as db:
                if not db.execute('SELECT 1 FROM drivers WHERE id=?',(did,)).fetchone():
                    return self.fail(404,'Conductor inexistente')
                if tid is not None and not db.execute('SELECT 1 FROM trips WHERE id=?',(tid,)).fetchone():
                    return self.fail(404,'Carrera inexistente')
                c=db.execute('''INSERT INTO incidents(created_at,actor,driver_id,trip_id,type,details)
                   VALUES (?,?,?,?,?,?)''',(utcnow(),s['username'],did,tid,kind,details))
                audit(db,s['username'],'incident_created',{'incident_id':c.lastrowid,'driver_id':did})
                db.commit()
            return self.send_json({'ok':True,'id':c.lastrowid},201)
        if p=='/api/incidents/review':
            s=self.require(('admin',))
            if not s:return
            try:iid=int(data.get('incident_id',0))
            except (TypeError,ValueError):return self.fail(400,'Incidencia inválida')
            with DB_LOCK, connect() as db:
                c=db.execute('''UPDATE incidents SET status='reviewed',reviewed_by=?,reviewed_at=?
                   WHERE id=? AND status='open' ''',(s['username'],utcnow(),iid))
                if not c.rowcount:return self.fail(404,'Incidencia inexistente o ya revisada')
                audit(db,s['username'],'incident_reviewed',{'incident_id':iid})
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/trips/assign':
            s=self.require(('admin','operator'))
            if not s:return
            try:tid=int(data.get('trip_id',0));did=int(data.get('driver_id',0))
            except (TypeError,ValueError):return self.fail(400,'ID incorrecto')
            with DB_LOCK,connect() as db:
                trip=db.execute('SELECT * FROM trips WHERE id=?',(tid,)).fetchone()
                dr=db.execute('SELECT * FROM drivers WHERE id=?',(did,)).fetchone()
                if not trip or not dr:return self.fail(404,'Carrera o conductor inexistente')
                if trip['status']!='pending' or dr['status']!='available' or dr['suspended'] or dr['station']!=trip['station']:
                    return self.fail(409,'Conductor no disponible, sede incorrecta o carrera ya asignada')
                deadline=(datetime.now(timezone.utc)+timedelta(seconds=int(os.environ.get('METRO_OFFER_SECONDS','120')))).isoformat(timespec='seconds')
                db.execute('UPDATE trips SET driver_id=?, status=?,offer_expires_at=? WHERE id=?',(did,'offered',deadline,tid))
                db.execute('UPDATE drivers SET status=? WHERE id=?',('busy',did))
                db.execute('INSERT OR IGNORE INTO trip_offer_history(trip_id,driver_id,offered_at,mode) VALUES (?,?,?,?)',
                           (tid,did,utcnow(),'manual'))
                audit(db,s['username'],'trip_assigned',{'trip_id':tid,'driver_id':did})
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/trips/points':
            s=self.require(('admin','operator'))
            if not s:return
            try:tid=int(data.get('trip_id',0));coords=location_fields(data)
            except (TypeError,ValueError) as e:return self.fail(400,str(e))
            with DB_LOCK,connect() as db:
                trip=db.execute('SELECT id FROM trips WHERE id=?',(tid,)).fetchone()
                if not trip:return self.fail(404,'Carrera no encontrada')
                db.execute('UPDATE trips SET pickup_lat=?,pickup_lng=?,dest_lat=?,dest_lng=? WHERE id=?',
                           (coords['pickup_lat'],coords['pickup_lng'],coords['dest_lat'],coords['dest_lng'],tid))
                audit(db,s['username'],'trip_points_updated',{'trip_id':tid,'mode':'explicit marker'})
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/trips/action':
            expire_offers()
            s=self.require(('driver',))
            if not s:return
            try:tid=int(data.get('trip_id',0))
            except (ValueError,TypeError):return self.fail(400,'ID incorrecto')
            action=clean_text(data.get('action'),15)
            states={'accept':('offered','accepted'),'reject':('offered','pending'),
                    'start':('accepted','inprogress'),'complete':('inprogress','done')}
            if action not in states:return self.fail(400,'Acción desconocida')
            src,dst=states[action]
            with DB_LOCK,connect() as db:
                r=db.execute('SELECT * FROM trips WHERE id=? AND driver_id=?',(tid,s['driver_id'])).fetchone()
                if not r:return self.fail(403,'Esta carrera no está asignada a tu unidad')
                if r['status']!=src:return self.fail(409,'Estado de carrera incompatible')
                if action=='reject':
                    reason=clean_text(data.get('reason'),300)
                    if len(reason)<5:return self.fail(400,'Indica por qué rechazas la carrera (mínimo 5 caracteres)')
                    db.execute('UPDATE trips SET status=?,driver_id=NULL,offer_expires_at=NULL WHERE id=?',(dst,tid))
                    db.execute('UPDATE drivers SET rejected_count=rejected_count+1 WHERE id=?',(s['driver_id'],))
                else:reason=None
                if action!='reject':db.execute('UPDATE trips SET status=?,offer_expires_at=NULL WHERE id=?',(dst,tid))
                if action in ('reject','complete'):
                    db.execute('UPDATE drivers SET status=?,completed=completed+? WHERE id=?',
                               ('available',1 if action=='complete' else 0,s['driver_id']))
                audit(db,s['username'],'trip_'+action,{'trip_id':tid, **({'reason':reason} if reason else {})})
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/driver/status':
            s=self.require(('driver',))
            if not s:return
            status=clean_text(data.get('status'),15)
            if status not in ('available','off'):return self.fail(400,'Estado inválido')
            with DB_LOCK,connect() as db:
                r=db.execute('SELECT * FROM drivers WHERE id=?',(s['driver_id'],)).fetchone()
                if r['suspended']:return self.fail(403,'Unidad suspendida')
                if r['status']=='busy':return self.fail(409,'Finaliza la carrera activa primero')
                db.execute('UPDATE drivers SET status=? WHERE id=?',(status,s['driver_id']))
                if status=='off':db.execute("UPDATE drivers SET lat=NULL,lng=NULL,simulated=0,location_source='none',location_accuracy_m=NULL WHERE id=?",(s['driver_id'],))
                shift_change(db,s['driver_id'],status,s['username'])
                audit(db,s['username'],'status_change',{'to':status})
                db.commit()
            return self.send_json({'ok':True})
        if p=='/api/drivers/profile':
            sess=self.require(('admin',))
            if not sess:return
            try:did=int(data.get('driver_id',0))
            except (ValueError,TypeError):return self.fail(400,'Identificador incorrecto')
            plate=clean_text(data.get('plate'),16).upper()
            if plate and not re.fullmatch(r'[A-Z0-9 -]{2,16}',plate):
                return self.fail(400,'Formato de placa no válido')
            photo_data=data.get('photo_base64')
            content=None;mime=None
            if photo_data is not None:
                if not isinstance(photo_data,str) or len(photo_data)>270000:
                    return self.fail(400,'Fotografía demasiado grande (máximo 200 KB)')
                try:content=base64.b64decode(photo_data,validate=True)
                except Exception:return self.fail(400,'Fotografía no válida')
                if not content or len(content)>200000:return self.fail(400,'Fotografía demasiado grande (máximo 200 KB)')
                if content.startswith(b'\x89PNG\r\n\x1a\n') and content[12:16]==b'IHDR':mime='image/png'
                elif content.startswith(b'\xff\xd8\xff') and content.endswith(b'\xff\xd9'):mime='image/jpeg'
                else:return self.fail(400,'Solo fotos PNG o JPEG válidas')
            with DB_LOCK,connect() as db:
                if not db.execute('SELECT id FROM drivers WHERE id=?',(did,)).fetchone():
                    return self.fail(404,'Conductor inexistente')
                if content is not None:
                    db.execute('UPDATE drivers SET plate=?,photo_bytes=?,photo_mime=? WHERE id=?',
                               (plate,content,mime,did))
                else:db.execute('UPDATE drivers SET plate=? WHERE id=?',(plate,did))
                for field in ('vehicle_make','vehicle_model','vehicle_color'):
                    if field in data:
                        db.execute(f'UPDATE drivers SET {field}=? WHERE id=?',
                                   (clean_text(data[field],50),did))
                if 'vehicle_year' in data:
                    year=data['vehicle_year']
                    if year in (None,''):year=None
                    else:
                        try:year=int(year)
                        except (TypeError,ValueError):return self.fail(400,'Año del vehículo inválido')
                        if not 1980<=year<=2035:return self.fail(400,'Año fuera del rango permitido')
                    db.execute('UPDATE drivers SET vehicle_year=? WHERE id=?',(year,did))
                audit(db,sess['username'],'driver_profile_updated',{'driver_id':did,'photo_uploaded':content is not None})
                db.commit()
            return self.send_json({'ok':True,'has_photo':content is not None})
        if p=='/api/drivers/suspend':
            s=self.require(('admin',))
            if not s:return
            try:did=int(data.get('driver_id',0))
            except (TypeError,ValueError):return self.fail(400,'Conductor inválido')
            suspended=bool(data.get('suspended'))
            with DB_LOCK,connect() as db:
                dr=db.execute('SELECT * FROM drivers WHERE id=?',(did,)).fetchone()
                if not dr:return self.fail(404,'Conductor inexistente')
                if suspended and dr['status']=='busy':return self.fail(409,'Primero resuelve la carrera en curso')
                db.execute('UPDATE drivers SET suspended=?,status=CASE WHEN ?=1 THEN ? ELSE status END WHERE id=?',
                           (int(suspended),int(suspended),'off',did))
                if suspended:shift_change(db,did,'off',s['username'])
                audit(db,s['username'],'suspension_changed',{'driver_id':did,'suspended':suspended})
                db.commit()
            return self.send_json({'ok':True})
        if re.fullmatch(r'/api/messages/\d+/reply',p):
            s=self.require(('admin','operator'))
            if not s:return
            mid=int(p.split('/')[3]);reply=clean_text(data.get('response'),1000)
            if not reply:return self.fail(400,'Respuesta vacía')
            with DB_LOCK,connect() as db:
                c=db.execute('UPDATE messages SET response=? WHERE id=?',(reply,mid))
                if not c.rowcount:return self.fail(404,'Mensaje no encontrado')
                audit(db,s['username'],'message_reply',{'message_id':mid})
                db.commit()
            return self.send_json({'ok':True})
        self.fail(404,'Acción desconocida')


def main():
    init_database()
    host=os.environ.get('METRO_HOST','127.0.0.1')
    port=int(os.environ.get('METRO_PORT','8765'))
    server=ThreadingHTTPServer((host,port),Handler)
    print(f'Metro Taxi MVP: http://{host}:{port}/cliente\nCentral: http://{host}:{port}/central\n',flush=True)
    print('Solo desarrollo local; no publicar este servidor HTTP en internet.\n',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()

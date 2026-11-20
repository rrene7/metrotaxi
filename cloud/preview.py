"""Local-only staging preview at http://127.0.0.1:8770/ (NOT public)."""
import os
import secrets
from pathlib import Path
from sqlalchemy import insert, select
from fastapi.staticfiles import StaticFiles
from .app import create_app, password_hash
from .schema import drivers, staff

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / '_runtime_staging'
RUN.mkdir(exist_ok=True)
app = create_app('sqlite+pysqlite:///'+str(RUN/'staging.sqlite3'),test_mode=True,auto_create=True)

@app.middleware('http')
async def require_localhost(request, call_next):
    # Defense in depth for this demonstration server; always bind to 127.0.0.1.
    from fastapi.responses import JSONResponse
    host = request.headers.get('host','').split(':')[0]
    client = request.client.host if request.client else ''
    if host not in ('localhost','127.0.0.1','testserver') or client not in ('127.0.0.1','::1','testclient'):
        return JSONResponse({'error':'La demostración solo admite acceso desde el mismo equipo'},status_code=403)
    return await call_next(request)
with app.state.engine.begin() as c:
    exists = c.execute(select(staff.c.id).limit(1)).first()
    if not exists:
        c.execute(insert(drivers), [
            dict(id=1,unit='MT-01',name='Conductor de prueba',station='Pacora'),
            dict(id=2,unit='MT-02',name='Conductor de prueba 2',station='24 de Diciembre'),
        ])
        credentials=[]
        for username,role,did in [('admin','admin',None),('operador','operator',None),('conductor1','driver',1),('conductor2','driver',2)]:
            pwd=secrets.token_urlsafe(13)
            c.execute(insert(staff).values(username=username,role=role,driver_id=did,password_hash=password_hash(pwd)))
            credentials.append(f'{username} ({role}) -> {pwd}')
        path=RUN/'credenciales_cloud_demo.txt'
        path.write_text('SOLO STAGING LOCAL. NO PUBLICAR.\n'+'\n'.join(credentials)+'\n',encoding='utf-8')
        try: os.chmod(path,0o600)
        except OSError:pass
        print('[METRO TAXI STAGING] Credenciales de prueba:',path,flush=True)
# Mount static preview last. /api endpoints registered first.
app.mount('/', StaticFiles(directory=str(ROOT/'web-staging'), html=True),name='staging-static')

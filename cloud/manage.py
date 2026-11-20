"""Interactive setup for a fresh PostgreSQL pilot, never accept passwords in argv."""
import argparse
import getpass
import os
from sqlalchemy import create_engine, insert, select, inspect
from .app import password_hash
from .pilot_tools import ensure_schema
from .pilot_tools import normalize_postgres_url
from .schema import staff, drivers

STATIONS=('Pacora', '24 de Diciembre')


def initialize_empty_schema(engine):
    """Opt-in bootstrap for an entirely empty database; no create_all on partial DBs."""
    existing=inspect(engine).get_table_names()
    if existing:
        raise RuntimeError('Base no vacía: --init-schema nunca modifica tablas existentes. '
                           'Usa migraciones revisadas y respaldo.')
    ensure_schema(engine,allow_empty_bootstrap=True)



def create_staff(engine, user, pwd, *, role='admin', driver=None):
    user=user.strip()
    if not user or len(user)>64 or role not in ('admin','operator','driver') or len(pwd)<14:
        raise ValueError('Usuario, contraseña o rol inválidos (contraseña mín. 14)')
    if role=='driver' and not driver:
        raise ValueError('Falta el expediente del conductor')
    with engine.begin() as c:
        if c.execute(select(staff.c.id).where(staff.c.username==user)).first():
            raise ValueError('El usuario ya existe')
        driver_id=None
        if driver:
            unit,name,station=driver
            if not unit or len(unit)>32 or not name or len(name)>120 or station not in STATIONS:
                raise ValueError('Unidad, nombre o sede inválidos')
            if c.execute(select(drivers.c.id).where(drivers.c.unit==unit)).first():
                raise ValueError('Esa unidad ya existe')
            driver_id=c.execute(insert(drivers).values(unit=unit,name=name,station=station)).inserted_primary_key[0]
        c.execute(insert(staff).values(username=user,role=role,driver_id=driver_id,password_hash=password_hash(pwd)))


def main():
    p=argparse.ArgumentParser()
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--init-schema',action='store_true',help='Crear tablas solo en una BD nueva')
    group.add_argument('--create-admin',action='store_true')
    group.add_argument('--create-operator',action='store_true')
    group.add_argument('--create-driver',action='store_true')
    opts=p.parse_args()
    dburl=normalize_postgres_url(os.environ.get('DATABASE_URL',''))
    engine=create_engine(dburl,pool_pre_ping=True)
    try:
        if opts.init_schema:
            initialize_empty_schema(engine)
            print('Esquema inicial creado sobre base completamente vacía. No se importa SQLite.')
            return
        role='driver' if opts.create_driver else 'operator' if opts.create_operator else 'admin'
        driver=None
        if role=='driver':
            unit=input('Unidad (ej. MT-01): ').strip()
            name=input('Nombre del conductor: ').strip()
            station=input('Sede (Pacora o 24 de Diciembre): ').strip()
            driver=(unit,name,station)
        username=input('Usuario para iniciar sesión: ').strip()
        pwd=getpass.getpass('Contraseña fuerte (mínimo 14 caracteres): ')
        create_staff(engine,username,pwd,role=role,driver=driver)
        print('Cuenta creada. No se guardó la contraseña en archivos.')
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    finally:
        engine.dispose()

if __name__=='__main__':main()

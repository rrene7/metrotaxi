"""Explicit PostgreSQL database initialization and staff bootstrap.
Do not run against the v0.9 demo data, and never pass passwords via CLI args.
"""
import argparse
import getpass
import os
import sys
from sqlalchemy import create_engine, insert, select
from .app import password_hash
from .schema import metadata, staff


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--init-schema', action='store_true', help='Crear estructura vacía (nueva BD PostgreSQL)')
    parser.add_argument('--create-admin', action='store_true', help='Crear administrador inicial desde consola privada')
    options=parser.parse_args()
    if options.init_schema == options.create_admin:
        parser.error('Usa una opción: --init-schema o --create-admin')
    url=os.environ.get('DATABASE_URL','')
    if not url.startswith('postgresql+psycopg://'):
        raise SystemExit('Se requiere DATABASE_URL PostgreSQL; SQLite NO permitido aquí')
    engine=create_engine(url,pool_pre_ping=True)
    if options.init_schema:
        metadata.create_all(engine)
        print('Esquema PostgreSQL creado; aún no hay datos. No importa SQLite automáticamente.')
    else:
        user=input('Usuario administrador: ').strip()
        if not user or len(user)>64:raise SystemExit('Usuario inválido')
        pwd=getpass.getpass('Contraseña fuerte (mín. 14 caracteres): ')
        if len(pwd)<14:raise SystemExit('Contraseña demasiado corta')
        with engine.begin() as c:
            if c.execute(select(staff.c.id).where(staff.c.username==user)).first():
                raise SystemExit('El usuario ya existe')
            c.execute(insert(staff).values(username=user,role='admin',driver_id=None,password_hash=password_hash(pwd)))
        print('Administrador inicial creado. Ninguna contraseña se escribió en el repositorio.')

if __name__=='__main__':main()

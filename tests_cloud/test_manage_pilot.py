"""Exercise interactive pilot account creation without personal data or PostgreSQL secrets."""
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine, select
from cloud.manage import create_staff
from cloud.schema import metadata, staff, drivers


class PilotAccountBootstrap(unittest.TestCase):
    def test_admin_and_driver_creation_and_no_default_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=create_engine('sqlite+pysqlite:///'+str(Path(tmp)/'test.sqlite'))
            metadata.create_all(engine)
            create_staff(engine,'admin_demo','unaclave-simulada-fuerte',role='admin')
            create_staff(engine,'driver_demo','otra-clave-simulada-123',role='driver',driver=('MT-01','Conductor ficticio','Pacora'))
            with engine.connect() as c:
                s=c.execute(select(staff)).mappings().all()
                d=c.execute(select(drivers)).mappings().one()
            self.assertEqual({a['role'] for a in s},{'admin','driver'})
            self.assertEqual(d['unit'],'MT-01')
            self.assertEqual(next(a for a in s if a['role']=='driver')['driver_id'],d['id'])
            self.assertNotIn('otra-clave-simulada',str(s))
            with self.assertRaises(ValueError):create_staff(engine,'driver_demo','otra-clave-simulada-123',role='admin')
            with self.assertRaises(ValueError):create_staff(engine,'driver2','otra-clave-simulada-123',role='driver',driver=('MT-01','Otro','Pacora'))
            with self.assertRaises(ValueError):create_staff(engine,'driver3','otra-clave-simulada-123',role='driver',driver=('MT-03','Otro','Sede inventada'))
            engine.dispose()

if __name__=='__main__':unittest.main()

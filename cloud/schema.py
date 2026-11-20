"""Portable PostgreSQL / SQLite-test schema. NOT an automatic v0.9 migration."""
from sqlalchemy import (MetaData, Table, Column, Integer, String, Float, Boolean,
                        DateTime, ForeignKey, Text, LargeBinary, UniqueConstraint, CheckConstraint, Index)
from sqlalchemy.sql import func, false

metadata = MetaData()

staff = Table('staff_accounts', metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(64), nullable=False, unique=True),
    Column('password_hash', String(256), nullable=False),
    Column('role', String(16), nullable=False),
    Column('driver_id', Integer, ForeignKey('drivers.id'), nullable=True),
    CheckConstraint("role IN ('admin','operator','driver')", name='valid_staff_role'))

drivers = Table('drivers', metadata,
    Column('id', Integer, primary_key=True),
    Column('unit', String(32), nullable=False, unique=True),
    Column('name', String(120), nullable=False),
    Column('station', String(32), nullable=False),
    Column('status', String(16), nullable=False, server_default='off'),
    Column('suspended', Boolean, nullable=False, server_default=false()),
    Column('plate', String(32), nullable=False, server_default=''),
    Column('vehicle_make', String(80), nullable=False, server_default=''),
    Column('vehicle_model', String(80), nullable=False, server_default=''),
    Column('vehicle_color', String(40), nullable=False, server_default=''),
    Column('lat', Float, nullable=True),
    Column('lng', Float, nullable=True),
    Column('accuracy_m', Float, nullable=True),
    Column('location_updated_at', DateTime(timezone=True), nullable=True),
    Column('location_source', String(16), nullable=False, server_default='none'),
    CheckConstraint("status IN ('off','available','busy')", name='driver_status_valid'),
    CheckConstraint("station IN ('Pacora','24 de Diciembre')", name='driver_station_valid'))

customers = Table('customer_accounts', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(100), nullable=False),
    Column('phone', String(15), nullable=False, unique=True),
    Column('password_hash', String(256), nullable=False),
    Column('phone_verified', Boolean, nullable=False, server_default=false()),
    Column('consent_at', DateTime(timezone=True), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False))

trips = Table('trips', metadata,
    Column('id', Integer, primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('customer_id', Integer, ForeignKey('customer_accounts.id'), nullable=True),
    Column('name', String(100), nullable=False),
    Column('phone', String(15), nullable=False),
    Column('station', String(32), nullable=False),
    Column('pickup', String(240), nullable=False),
    Column('destination', String(240), nullable=False, server_default=''),
    Column('reference', String(240), nullable=False, server_default=''),
    Column('pickup_lat', Float, nullable=True),
    Column('pickup_lng', Float, nullable=True),
    Column('pickup_accuracy_m', Float, nullable=True),
    Column('dest_lat', Float, nullable=True),
    Column('dest_lng', Float, nullable=True),
    Column('status', String(16), nullable=False, server_default='pending'),
    Column('driver_id', Integer, ForeignKey('drivers.id'), nullable=True),
    Column('channel', String(40), nullable=False, server_default='Web Metro Taxi'),
    Column('offer_expires_at', DateTime(timezone=True), nullable=True),
    Column('price', Float, nullable=True),
    CheckConstraint("status IN ('pending','offered','accepted','inprogress','done','cancelled')",name='trip_status_valid'),
    CheckConstraint("station IN ('Pacora','24 de Diciembre')",name='trip_station_valid'))

sessions = Table('sessions', metadata,
    Column('token_hash', String(64), primary_key=True),
    Column('role', String(16), nullable=False),
    Column('user_id', Integer, nullable=False),
    Column('csrf_token', String(64), nullable=False),
    Column('expires_at', DateTime(timezone=True), nullable=False))

audit = Table('audit', metadata,
    Column('id', Integer, primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('actor_role', String(16), nullable=False),
    Column('actor_id', Integer, nullable=False),
    Column('action', String(64), nullable=False),
    Column('trip_id', Integer, ForeignKey('trips.id'), nullable=True),
    Column('detail', Text, nullable=False, server_default=''))

Index('idx_trips_station_status', trips.c.station, trips.c.status)
Index('idx_trips_customer', trips.c.customer_id)
Index('idx_trips_driver', trips.c.driver_id)
Index('idx_sessions_expiry', sessions.c.expires_at)


# v0.10.3 additive tables. `create_all` does not modify preexisting tables.
# Store photos separate from the drivers table so a local staging DB can be
# upgraded without destructive ALTER operations.
driver_photos = Table('driver_photos', metadata,
    Column('driver_id', Integer, ForeignKey('drivers.id'), primary_key=True),
    Column('mime', String(16), nullable=False),
    Column('content', LargeBinary, nullable=False),
    Column('uploaded_at', DateTime(timezone=True), nullable=False))
referral_codes = Table('referral_codes', metadata,
    Column('driver_id', Integer, ForeignKey('drivers.id'), primary_key=True),
    Column('token', String(72), unique=True, nullable=False),
    Column('enabled', Boolean, nullable=False, server_default='1'))
referral_signups = Table('referral_signups', metadata,
    Column('customer_id', Integer, ForeignKey('customer_accounts.id'), primary_key=True),
    Column('driver_id', Integer, ForeignKey('drivers.id'), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False))

customer_messages = Table('customer_messages',metadata,
    Column('id', Integer, primary_key=True),
    Column('customer_id', Integer, ForeignKey('customer_accounts.id'), nullable=False),
    Column('sender', String(16), nullable=False),
    Column('body', String(800), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    CheckConstraint("sender IN ('customer','central')",name='valid_sender'))
Index('idx_messages_customer',customer_messages.c.customer_id)

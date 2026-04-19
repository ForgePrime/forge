import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# Connection pool tuning (audit #: scale/performance — connection pooling).
# Defaults sized for single-uvicorn-worker development; tune via env
# FORGE_DB_POOL_SIZE / FORGE_DB_MAX_OVERFLOW / FORGE_DB_POOL_RECYCLE for
# production where multiple workers share the DB.
#
# pool_size:         persistent connections kept open (baseline)
# max_overflow:      extra temporary connections allowed under burst
# pool_recycle:      seconds — reconnect sessions older than this to dodge
#                    middlebox idle-disconnect (e.g. pgbouncer).
# pool_pre_ping:     SELECT 1 before using a pooled connection — catches
#                    stale connections at cost of one round-trip/checkout.

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=_int_env("FORGE_DB_POOL_SIZE", 10),
    max_overflow=_int_env("FORGE_DB_MAX_OVERFLOW", 20),
    pool_recycle=_int_env("FORGE_DB_POOL_RECYCLE", 1800),  # 30 minutes
    pool_timeout=_int_env("FORGE_DB_POOL_TIMEOUT", 30),    # seconds to wait for a connection
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

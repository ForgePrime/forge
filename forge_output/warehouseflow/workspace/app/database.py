import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://forge:forge@localhost:5432/warehouseflow",
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)


class Base(DeclarativeBase):
    pass


def get_db():
    with Session(engine) as session:
        yield session

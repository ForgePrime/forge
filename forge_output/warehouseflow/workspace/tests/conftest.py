import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/warehouseflow_test",
)


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(scope="session")
def db_engine(run_migrations):
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_conn(db_engine):
    conn = db_engine.connect()
    trans = conn.begin()
    yield conn
    trans.rollback()
    conn.close()

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://forge:forge@localhost:5432/warehouseflow_test"
)

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def db_session(db_engine):
    """Function-scoped SQLAlchemy Session; rolls back after each test."""
    with Session(db_engine) as session:
        session.begin()
        yield session
        session.rollback()

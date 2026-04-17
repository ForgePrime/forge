import os

# Set DATABASE_URL to the test database before any app module is imported.
# app/database.py creates the engine at import time, so this must run first.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://forge:forge@localhost:5432/warehouseflow_test",
)

import bcrypt as _bcrypt
import pytest
from sqlalchemy import text

_TEST_EMAIL = "auth_test_user@example.com"
_TEST_PASSWORD = "securepassword123"


@pytest.fixture(scope="session")
def test_credentials():
    return {"email": _TEST_EMAIL, "password": _TEST_PASSWORD}


@pytest.fixture(scope="session", autouse=True)
def seed_auth_user(db_engine, run_migrations):
    password_hash = _bcrypt.hashpw(_TEST_PASSWORD.encode(), _bcrypt.gensalt()).decode()
    with db_engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, warehouse_id) "
                "VALUES (:email, :hash, 'operator', NULL) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {"email": _TEST_EMAIL, "hash": password_hash},
        )
        conn.commit()
    yield
    with db_engine.connect() as conn:
        conn.execute(text("DELETE FROM users WHERE email = :email"), {"email": _TEST_EMAIL})
        conn.commit()


@pytest.fixture(scope="session")
def client(seed_auth_user):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c

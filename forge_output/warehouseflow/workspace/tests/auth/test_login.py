from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import ALGORITHM, SECRET_KEY


def test_login_success_returns_jwt_with_role(client, test_credentials):
    resp = client.post("/api/auth/login", json=test_credentials)
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["role"] == "operator"
    assert data["user"]["warehouse_id"] is None
    assert data["user"]["email"] == test_credentials["email"]
    payload = jwt.decode(data["token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert "sub" in payload
    assert "exp" in payload


def test_invalid_password_returns_401_generic_message(client, test_credentials):
    resp = client.post(
        "/api/auth/login",
        json={"email": test_credentials["email"], "password": "wrongpassword999"},
    )
    assert resp.status_code == 401
    body = resp.json()
    detail = body.get("detail", "")
    # Must not hint whether the email exists or not
    assert "email" not in detail.lower()
    assert "password" not in detail.lower()
    assert detail == "Invalid credentials"


def test_missing_token_returns_401(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


def test_expired_jwt_returns_401(client):
    expired_token = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401

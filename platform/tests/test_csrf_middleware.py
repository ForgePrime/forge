"""Direct contract tests for CSRF middleware.

Audit top-10 item #9: CSRF enforcement verification. Confirms the
double-submit cookie pattern actually rejects unsafe requests lacking
the matching X-CSRF-Token header.

Uses a minimal FastAPI app wired only with CSRFMiddleware — isolates
the contract from unrelated platform behavior.
"""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.services.csrf import CSRFMiddleware, CSRF_COOKIE


def _make_app():
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.post("/write")
    def write():
        return {"ok": True}

    @app.patch("/write")
    def write_patch():
        return {"ok": True}

    @app.delete("/write")
    def write_delete():
        return {"ok": True}

    @app.put("/write")
    def write_put():
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    def login():
        return {"ok": True}  # exempt path — should work without token

    @app.post("/health")
    def health_post():
        return {"ok": True}  # exempt — but /health is usually GET anyway

    return app


# ---------- GET always allowed ----------

def test_get_does_not_require_csrf():
    client = TestClient(_make_app())
    r = client.get("/ping")
    assert r.status_code == 200
    # Middleware sets the cookie on first visit
    assert CSRF_COOKIE in r.cookies


# ---------- Unsafe methods require matching header ----------

def test_post_without_cookie_is_rejected():
    client = TestClient(_make_app())
    r = client.post("/write")
    assert r.status_code == 403
    assert "CSRF" in r.json().get("detail", "")


def test_post_with_cookie_but_no_header_rejected():
    client = TestClient(_make_app())
    # First GET to obtain cookie
    client.get("/ping")
    # Second POST with cookie but no header
    r = client.post("/write")
    assert r.status_code == 403


def test_post_with_mismatched_header_rejected():
    client = TestClient(_make_app())
    client.get("/ping")  # sets cookie
    r = client.post("/write", headers={"X-CSRF-Token": "wrong-value"})
    assert r.status_code == 403


def test_post_with_matching_header_accepted():
    client = TestClient(_make_app())
    g = client.get("/ping")
    token = g.cookies[CSRF_COOKIE]
    r = client.post("/write", headers={"X-CSRF-Token": token})
    assert r.status_code == 200


def test_patch_delete_put_all_enforce_csrf():
    """Every unsafe method path must go through the same gate."""
    client = TestClient(_make_app())
    g = client.get("/ping")
    token = g.cookies[CSRF_COOKIE]

    # Without token — rejected
    assert client.patch("/write").status_code == 403
    assert client.delete("/write").status_code == 403
    assert client.put("/write").status_code == 403

    # With matching token — accepted
    assert client.patch("/write", headers={"X-CSRF-Token": token}).status_code == 200
    assert client.delete("/write", headers={"X-CSRF-Token": token}).status_code == 200
    assert client.put("/write", headers={"X-CSRF-Token": token}).status_code == 200


# ---------- Exempt paths ----------

def test_auth_login_exempt():
    """Login cannot require a pre-existing session cookie — CSRF exempt."""
    client = TestClient(_make_app())
    r = client.post("/api/v1/auth/login")
    assert r.status_code == 200  # no CSRF required


def test_health_exempt():
    client = TestClient(_make_app())
    r = client.post("/health")
    assert r.status_code == 200


# ---------- Cookie set on first visit ----------

def test_cookie_persists_across_requests():
    client = TestClient(_make_app())
    r1 = client.get("/ping")
    token1 = r1.cookies[CSRF_COOKIE]
    r2 = client.get("/ping")
    # Cookie should still be present; value may or may not rotate — middleware
    # only rotates when cookie is MISSING, so within same client it stays.
    assert CSRF_COOKIE in client.cookies
    # Consistency — second request without header should still work (GET)
    assert r2.status_code == 200

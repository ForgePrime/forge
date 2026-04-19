"""Auth middleware — path-based exclusion list.

Everything under /api/v1/* or /ui/* requires auth unless in PUBLIC_PATHS.
Anonym:
- /api/v1/*   → 401 JSON
- /ui/*       → 303 redirect to /ui/login?next=<original>
- others      → pass through

Attaches user to request.state.user on success for downstream handlers.
"""

import re
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import SessionLocal
from app.models import User, Membership, Organization
from app.services.auth import decode_access_token


# Paths that DO NOT require auth (prefix OR exact match)
PUBLIC_PATHS = [
    "/",
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/logout",
    "/ui/login",
    "/ui/signup",
    "/ui/logout",
]
PUBLIC_PATH_PREFIXES = [
    "/static/",       # future static assets
    "/openapi",       # swagger assets
    "/share/",        # capability-link public views
]


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.cookies.get("forge_token")


def _load_user_and_org(token: str) -> tuple[User | None, Organization | None, str | None]:
    """Returns (user, current_org, role) or (None, None, None) if not authenticated.

    Current org = first membership (Phase 1 single-org-per-session).
    Multi-org switcher deferred to Phase 2.
    """
    payload = decode_access_token(token)
    if not payload:
        return None, None, None
    try:
        uid = int(payload["sub"])
    except (KeyError, ValueError):
        return None, None, None
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == uid).first()
        if not u or not u.is_active:
            return None, None, None
        # First membership = current org
        m = db.query(Membership).filter(Membership.user_id == u.id).order_by(Membership.id).first()
        org = m.organization if m else None
        role = m.role if m else None
        # Detach to avoid session leakage
        db.expunge(u)
        if org:
            db.expunge(org)
        return u, org, role
    finally:
        db.close()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Always set attrs (None if not authenticated)
        request.state.user = None
        request.state.org = None
        request.state.role = None
        path = request.url.path

        token = _extract_token(request)
        if token:
            user, org, role = _load_user_and_org(token)
            if user:
                request.state.user = user
                request.state.org = org
                request.state.role = role
        else:
            user = None

        if _is_public(path):
            return await call_next(request)

        # Protected path — require user
        if not user:
            if path.startswith("/ui/"):
                next_url = path
                if request.url.query:
                    next_url += "?" + request.url.query
                return RedirectResponse(url=f"/ui/login?next={next_url}", status_code=303)
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )

        return await call_next(request)

"""CSRF protection — double-submit cookie pattern.

On first GET to UI, middleware sets `forge_csrf` cookie with random token.
POST/PATCH/DELETE must include token either:
- in hidden form field `csrf_token` (standard form)
- in header `X-CSRF-Token` (HTMX / AJAX)

Middleware validates cookie == form/header. Samesite=lax cookie blocks cross-site POST.
"""

import secrets
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


CSRF_COOKIE = "forge_csrf"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"
# Paths excluded from CSRF (login pages need to work on first visit without cookie)
# Auth/public POST endpoints are protected by middleware auth wall, not CSRF.
CSRF_EXEMPT_PREFIXES = [
    "/api/v1/auth/",  # JSON API login/register from non-browser clients
    "/ui/login", "/ui/signup", "/ui/logout",  # pre-auth flow — CSRF useless here (no session)
    "/health",
    "/share/",  # public read-only share links — no session, no CSRF
]


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validates CSRF on POST/PATCH/DELETE/PUT for HTML routes.

    - Sets forge_csrf cookie on every response if missing
    - On unsafe methods: require cookie match to form/header
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        is_unsafe = method in ("POST", "PATCH", "DELETE", "PUT")
        is_exempt = any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES)

        # Ensure cookie for subsequent requests
        existing = request.cookies.get(CSRF_COOKIE)
        new_token: str | None = None
        if not existing:
            new_token = secrets.token_urlsafe(32)

        # Make the token available to downstream handlers (for injection into forms)
        request.state.csrf_token = existing or new_token

        if is_unsafe and not is_exempt:
            # Validate header only (reading body in middleware breaks downstream FastAPI Form handlers
            # in Starlette <0.40 — we require HTMX-injected X-CSRF-Token for all unsafe requests).
            supplied = request.headers.get(CSRF_HEADER)
            if not existing or not supplied or existing != supplied:
                # Reject with 403 (JSON for API paths, HTML for UI)
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF validation failed"},
                    )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed — reload the page and retry"},
                )

        response = await call_next(request)
        if new_token:
            response.set_cookie(
                key=CSRF_COOKIE, value=new_token,
                httponly=False,  # JS/HTMX reads to put in header
                samesite="lax", max_age=60 * 60 * 12,  # 12h
            )
        return response

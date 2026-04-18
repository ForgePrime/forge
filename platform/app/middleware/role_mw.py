"""RBAC role enforcement middleware.

Maps method+path → minimum role required (owner > editor > viewer).
Anonymous (no membership) blocked at AuthMiddleware. This layer adds:
- Viewer can only GET
- Editor can mutate project content (CRUD objectives/tasks/AC, run orchestrate)
- Owner can also mutate org settings (Anthropic key, budget) + delete project

Returns 403 JSON for /api/* and 403 with HTML body for /ui/*.
"""

import re
from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware


_ROLE_RANK = {"viewer": 1, "editor": 2, "owner": 3}


# Per-path-pattern minimum role for unsafe methods
# Order matters — first match wins
_RULES: list[tuple[str, str, str]] = [
    # (regex, method-prefix-or-* , min_role)
    (r"^/ui/(login|signup|logout)", "*", None),  # exempt
    (r"^/api/v1/auth/", "*", None),              # exempt
    (r"^/health", "*", None),
    # Org settings — owner only
    (r"^/ui/org/settings", "*", "owner"),
    (r"^/api/v1/.*organizations", "*", "owner"),
    # Project delete — owner only
    (r"^/api/v1/projects/[^/]+$", "DELETE", "owner"),
    # Project create — editor (anyone in org with editor+ can create)
    (r"^/ui/projects$", "POST", "editor"),
    (r"^/api/v1/projects$", "POST", "editor"),
    # Default for unsafe methods — editor
    (r"^/ui/", "*", "editor"),
    (r"^/api/v1/", "*", "editor"),
]

_COMPILED = [(re.compile(pat), method, role) for pat, method, role in _RULES]


def _required_role(path: str, method: str) -> str | None:
    """None means no role check needed (exempt or safe method handled elsewhere)."""
    for pat, m, role in _COMPILED:
        if pat.match(path) and (m == "*" or method.upper().startswith(m)):
            return role
    return None


class RoleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()

        # Only enforce on unsafe methods
        if method not in ("POST", "PATCH", "DELETE", "PUT"):
            return await call_next(request)

        required = _required_role(path, method)
        if required is None:
            return await call_next(request)

        # User must already be set by AuthMiddleware (it runs first)
        role = getattr(request.state, "role", None)
        if not role:
            # Auth middleware should have already returned 401, but guard anyway
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        if _ROLE_RANK.get(role, 0) < _ROLE_RANK.get(required, 999):
            msg = f"Forbidden: requires '{required}' role (you have '{role}')"
            if path.startswith("/api/"):
                return JSONResponse(status_code=403, content={"detail": msg})
            return HTMLResponse(status_code=403, content=f"<h1>403 Forbidden</h1><p>{msg}</p>")

        return await call_next(request)

"""Page context middleware — runs after auth + role, before handler.

Infers a default PageContext from the request path and stores it on
request.state.page_ctx. Route handlers can override by assigning their own.
base.html reads request.state.page_ctx and renders as JSON for the AI sidebar.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.page_context import build_page_context


class PageContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only populate for UI / HTML routes; API routes don't need it.
        path = request.url.path
        if path.startswith("/ui/") or path == "/" or path == "/ui":
            try:
                request.state.page_ctx = build_page_context(request)
            except Exception:
                request.state.page_ctx = None
        return await call_next(request)

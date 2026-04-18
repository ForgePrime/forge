"""Tenant isolation helpers.

Prevents cross-org data access via URL/slug guessing.

Usage in route handlers:
    from app.services.tenant import assert_project_in_org
    proj = assert_project_in_org(db, slug, request)  # raises 404 if not in current org
"""

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.models import Project


def current_org_id(request: Request) -> int | None:
    """Return current org id from request.state (set by AuthMiddleware), or None."""
    org = getattr(request.state, "org", None)
    return org.id if org else None


def assert_project_in_org(db: Session, slug: str, request: Request) -> Project:
    """Return project IF it belongs to current org, else 404.

    Returns 404 (not 403) to avoid leaking existence of cross-org resources.
    """
    org_id = current_org_id(request)
    if org_id is None:
        # No org context → treat as not-found (user without membership should never reach here,
        # but guard anyway). Mutations are already blocked by RoleMiddleware; this handles GETs.
        raise HTTPException(404)
    p = db.query(Project).filter(
        Project.slug == slug,
        Project.organization_id == org_id,
    ).first()
    if not p:
        raise HTTPException(404)
    return p

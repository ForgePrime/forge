from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.execute import router as execute_router
from app.api.projects import router as projects_router
from app.api.pipeline import router as pipeline_router
from app.api.ui import router as ui_router
from app.api.auth import router as auth_router
from app.api.webhooks_api import router as webhooks_router
from app.api.ai import router as ai_router
from app.api.tier1 import router as tier1_router
from app.api.skills import router as skills_router
from app.config import settings
from app.database import engine, Base, SessionLocal


def _bootstrap_default_org():
    """Ensure default organization exists for existing pilots + register fallback flow."""
    import app.models  # ensure models loaded
    from app.models import Organization, Project
    db = SessionLocal()
    try:
        default = db.query(Organization).filter(Organization.slug == settings.default_org_slug).first()
        if not default:
            default = Organization(slug=settings.default_org_slug, name=settings.default_org_name)
            db.add(default)
            db.flush()
        # Migrate existing projects without org_id to default
        orphan_projects = db.query(Project).filter(Project.organization_id.is_(None)).all()
        for p in orphan_projects:
            p.organization_id = default.id
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (MVP — use Alembic in production)
    import app.models  # noqa: ensure all models registered
    Base.metadata.create_all(bind=engine)
    # Add new columns to existing tables (idempotent ALTER ... IF NOT EXISTS)
    from app.services.schema_migrations import apply as _apply_alters
    _apply_alters(engine)
    # Bootstrap default org + assign existing projects (Phase 1 migration)
    _bootstrap_default_org()
    yield

app = FastAPI(
    title="Forge Platform",
    description="Meta-prompting engine for AI-driven software development",
    version="0.1.0",
    lifespan=lifespan,
)

from app.middleware.auth_mw import AuthMiddleware
from app.middleware.role_mw import RoleMiddleware
from app.middleware.page_ctx_mw import PageContextMiddleware
from app.services.csrf import CSRFMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Order: middleware added later runs FIRST on request, LAST on response.
# Pipeline desired: Auth → CSRF → Role → PageContext → handler
# add order is reverse of execution.
app.add_middleware(PageContextMiddleware)
app.add_middleware(RoleMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuthMiddleware)

app.include_router(auth_router)
app.include_router(execute_router)
app.include_router(projects_router)
app.include_router(pipeline_router)
app.include_router(webhooks_router)
app.include_router(ai_router)
app.include_router(tier1_router)
app.include_router(skills_router)
app.include_router(ui_router)
from app.api.ui import share_router
app.include_router(share_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

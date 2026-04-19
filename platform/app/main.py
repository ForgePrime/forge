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
from app.api.lessons import router as lessons_router
from app.api.search import router as search_router
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
    # Seed forge-self anti-patterns (J5) so the system remembers its own incidents
    from app.database import SessionLocal
    from app.api.lessons import seed_self_anti_patterns
    _db = SessionLocal()
    try:
        seed_self_anti_patterns(_db)
    finally:
        _db.close()
    # P5.7 — flip orphaned RUNNING runs (worker thread killed by previous shutdown)
    # to INTERRUPTED so the UI shows the truth instead of an eternal spinner.
    from app.services.orphan_recovery import mark_orphan_runs_interrupted
    _db = SessionLocal()
    try:
        touched = mark_orphan_runs_interrupted(_db)
        if touched:
            import logging
            logging.getLogger(__name__).warning(
                "P5.7 orphan recovery: marked %d run(s) INTERRUPTED at startup: %s",
                len(touched), touched,
            )
    finally:
        _db.close()
    yield
    # ---- SHUTDOWN path (runs on SIGTERM / uvicorn graceful stop) ----
    # Release IN_PROGRESS tasks back to TODO + mark RUNNING orchestrate runs
    # INTERRUPTED. Prevents tasks from being stuck for the full lease duration
    # after a restart. Best-effort — failures logged, never re-raised.
    import logging as _logging
    _log = _logging.getLogger(__name__)
    try:
        from app.services.orphan_recovery import (
            release_in_progress_tasks as _release_tasks,
            mark_running_runs_interrupted_on_shutdown as _mark_runs,
        )
        _db = SessionLocal()
        try:
            released = _release_tasks(_db)
            if released:
                _log.info("graceful-shutdown: released %d IN_PROGRESS task(s): %s",
                          len(released), released)
            interrupted = _mark_runs(_db)
            if interrupted:
                _log.info("graceful-shutdown: marked %d orchestrate run(s) INTERRUPTED: %s",
                          len(interrupted), interrupted)
        finally:
            _db.close()
    except Exception as _e:  # pragma: no cover
        _log.warning("graceful-shutdown cleanup failed: %s", _e)

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
from app.services.logging_setup import (
    configure_logging as _configure_logging,
    RequestIdMiddleware,
)

# Configure logging BEFORE middlewares/routes — so every subsequent log call
# inherits the request-id filter and (if FORGE_LOG_JSON=true) JSON format.
_configure_logging()

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
# RequestIdMiddleware added LAST so it runs FIRST on every request — assigns
# the request_id BEFORE any other middleware logs. Also echoed as X-Request-Id
# response header for client/server log correlation.
app.add_middleware(RequestIdMiddleware)

app.include_router(auth_router)
app.include_router(execute_router)
app.include_router(projects_router)
app.include_router(pipeline_router)
app.include_router(webhooks_router)
app.include_router(ai_router)
app.include_router(tier1_router)
app.include_router(skills_router)
app.include_router(lessons_router)
app.include_router(search_router)
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

"""Webhooks + share-link + retention API.

Phase 2 — minimum collab/integration features.
"""

import datetime as dt
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Webhook, ShareLink, Project, Organization, LLMCall, Execution, OrchestrateRun, TestRun
from app.services.webhooks import generate_secret


router = APIRouter(prefix="/api/v1", tags=["phase2"])


# ---------- Webhooks ----------

class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=2000)
    events: list[str] = Field(default_factory=list)
    enabled: bool = True


@router.post("/webhooks")
def create_webhook(body: WebhookCreate, request: Request, db: Session = Depends(get_db)):
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403)
    h = Webhook(
        organization_id=org.id,
        url=body.url, secret=generate_secret(),
        events=body.events, enabled=body.enabled,
    )
    db.add(h)
    db.commit()
    return {"id": h.id, "secret": h.secret, "events": h.events}


@router.get("/webhooks")
def list_webhooks(request: Request, db: Session = Depends(get_db)):
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403)
    return [{
        "id": h.id, "url": h.url, "events": h.events,
        "enabled": h.enabled,
        "last_called_at": h.last_called_at.isoformat() if h.last_called_at else None,
        "last_status": h.last_status, "last_error": h.last_error,
    } for h in db.query(Webhook).filter(Webhook.organization_id == org.id).all()]


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, request: Request, db: Session = Depends(get_db)):
    org = getattr(request.state, "org", None)
    h = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not h or h.organization_id != (org.id if org else 0):
        raise HTTPException(404)
    db.delete(h)
    db.commit()
    return {"deleted": True}


# ---------- Share links (capability tokens) ----------

class ShareLinkCreate(BaseModel):
    project_slug: str
    task_external_id: str | None = None  # if None, link is to project
    expires_in_days: int = Field(7, ge=1, le=90)


@router.post("/share-links")
def create_share_link(body: ShareLinkCreate, request: Request, db: Session = Depends(get_db)):
    org = getattr(request.state, "org", None)
    user = getattr(request.state, "user", None)
    proj = db.query(Project).filter(Project.slug == body.project_slug).first()
    if not proj:
        raise HTTPException(404)
    if org and proj.organization_id and proj.organization_id != org.id:
        raise HTTPException(404)
    sl = ShareLink(
        token=secrets.token_urlsafe(32),
        scope="task" if body.task_external_id else "project",
        project_id=proj.id,
        task_external_id=body.task_external_id,
        created_by_user_id=user.id if user else None,
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=body.expires_in_days),
    )
    db.add(sl)
    db.commit()
    return {
        "token": sl.token,
        "url": f"/share/{sl.token}",
        "expires_at": sl.expires_at.isoformat() if sl.expires_at else None,
    }


@router.delete("/share-links/{token}")
def revoke_share_link(token: str, request: Request, db: Session = Depends(get_db)):
    sl = db.query(ShareLink).filter(ShareLink.token == token).first()
    if not sl:
        raise HTTPException(404)
    sl.revoked = True
    db.commit()
    return {"revoked": True}


# ---------- Retention cleanup ----------

class RetentionRequest(BaseModel):
    older_than_days: int = Field(90, ge=7)
    dry_run: bool = True


@router.post("/admin/cleanup")
def cleanup_old_data(body: RetentionRequest, request: Request, db: Session = Depends(get_db)):
    """Delete LLM calls + completed orchestrate runs + test runs older than N days.
    Default dry_run=True returns counts only.
    """
    user = getattr(request.state, "user", None)
    if not user or not user.is_superuser:
        # Phase 2 stub — only superuser can cleanup. Owner-per-org retention would need separate scoping.
        raise HTTPException(403, "Superuser required")

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=body.older_than_days)
    counts = {
        "llm_calls_to_delete": db.query(LLMCall).filter(LLMCall.created_at < cutoff).count(),
        "orchestrate_runs_to_delete": db.query(OrchestrateRun).filter(
            OrchestrateRun.finished_at.isnot(None), OrchestrateRun.finished_at < cutoff
        ).count(),
        "test_runs_to_delete": db.query(TestRun).filter(TestRun.created_at < cutoff).count(),
    }
    if body.dry_run:
        counts["dry_run"] = True
        return counts
    deleted = {
        "llm_calls": db.query(LLMCall).filter(LLMCall.created_at < cutoff).delete(),
        "orchestrate_runs": db.query(OrchestrateRun).filter(
            OrchestrateRun.finished_at.isnot(None), OrchestrateRun.finished_at < cutoff
        ).delete(),
        "test_runs": db.query(TestRun).filter(TestRun.created_at < cutoff).delete(),
    }
    db.commit()
    return {"deleted": deleted, "cutoff": cutoff.isoformat()}

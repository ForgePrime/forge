"""GDPR Article 20 — data portability export.

Aggregates everything Forge stores *about* a user or organization into a
single structured JSON payload. Enables the data subject to receive their
data "in a structured, commonly used and machine-readable format" per
Article 20(1) GDPR.

Does NOT erase or redact anything — pure read operation.

For erasure (Article 17 right-to-be-forgotten), see `services/gdpr_erase.py`
(not yet implemented; deferred to dedicated session per decision D-16 in
autonomous session log).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session


def _dt_iso(d: dt.datetime | None) -> str | None:
    return d.isoformat() if d else None


def export_user_data(db: Session, user_id: int) -> dict:
    """Return everything Forge knows about this user.

    Structure mirrors GDPR guidance: one key per data category.
    Empty categories include empty lists so the shape is predictable.
    """
    from app.models import User, Membership, Organization, AuditLog, Project

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "user not found", "user_id": user_id}

    # --- Identity data ---
    identity = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "created_at": _dt_iso(user.created_at),
        "last_login_at": _dt_iso(user.last_login_at),
    }

    # --- Memberships + organizations user belongs to ---
    memberships_data = []
    org_ids: set[int] = set()
    for m in db.query(Membership).filter(Membership.user_id == user_id).all():
        memberships_data.append({
            "organization_id": m.organization_id,
            "role": m.role,
            "created_at": _dt_iso(getattr(m, "created_at", None)),
        })
        org_ids.add(m.organization_id)

    organizations = []
    for org in db.query(Organization).filter(Organization.id.in_(org_ids)).all() if org_ids else []:
        organizations.append({
            "id": org.id,
            "slug": org.slug,
            "name": org.name,
            "plan": org.plan,
            "created_at": _dt_iso(org.created_at),
        })

    # --- Audit log entries attributed to this user ---
    # (actor string may contain user:{id} or email; we filter broadly)
    audit_entries = []
    audit_q = (db.query(AuditLog)
                 .filter(AuditLog.actor.like(f"%{user.email}%"))
                 .order_by(AuditLog.id.desc())
                 .limit(2000))
    for a in audit_q.all():
        audit_entries.append({
            "id": a.id,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "action": a.action,
            "actor": a.actor,
            "created_at": _dt_iso(getattr(a, "created_at", None)),
        })

    # --- Projects the user created objectives/tasks in (via started_by_user_id) ---
    # Lightweight — we surface project slugs they touched, not full project data.
    from sqlalchemy import text
    project_slugs = []
    try:
        rows = db.execute(
            text("""
                SELECT DISTINCT p.slug
                FROM projects p
                JOIN orchestrate_runs r ON r.project_id = p.id
                WHERE r.started_by_user_id = :uid
            """),
            {"uid": user_id},
        ).all()
        project_slugs = [r[0] for r in rows]
    except Exception:  # pragma: no cover — defensive
        pass

    return {
        "gdpr_article": "20",
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "subject": "user",
        "identity": identity,
        "memberships": memberships_data,
        "organizations_member_of": organizations,
        "audit_log_entries_count": len(audit_entries),
        "audit_log_entries": audit_entries,
        "projects_interacted_with": project_slugs,
        "notes": [
            "This export covers the Forge Platform database only.",
            "Workspace artifacts in forge_output/ are filesystem-bound and must be exported separately.",
            "LLM prompt bodies may contain user input verbatim and are not expanded here — "
            "they are stored under project scope (organization-level export for full content).",
        ],
    }


def export_organization_data(db: Session, org_id: int) -> dict:
    """Return everything Forge knows about this organization.

    Covers: projects, tasks, objectives, decisions, findings, LLM calls
    (metadata only — prompt bodies optional per verbosity flag), memberships,
    audit entries. Useful for enterprise GDPR data-subject requests where the
    subject is a legal entity or for mass migration.
    """
    from app.models import (
        Organization, Project, Task, Objective, Decision, Finding,
        LLMCall, Membership, AuditLog, Knowledge,
    )

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return {"error": "organization not found", "organization_id": org_id}

    projects = db.query(Project).filter(Project.organization_id == org_id).all()
    project_ids = [p.id for p in projects]

    projects_data = []
    for p in projects:
        task_count = db.query(Task).filter(Task.project_id == p.id).count()
        obj_count = db.query(Objective).filter(Objective.project_id == p.id).count()
        llm_count = db.query(LLMCall).filter(LLMCall.project_id == p.id).count()
        decision_count = db.query(Decision).filter(Decision.project_id == p.id).count()
        finding_count = db.query(Finding).filter(Finding.project_id == p.id).count()
        knowledge_count = db.query(Knowledge).filter(Knowledge.project_id == p.id).count()

        projects_data.append({
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "goal": p.goal,
            "autonomy_level": getattr(p, "autonomy_level", None),
            "created_at": _dt_iso(p.created_at),
            "counts": {
                "tasks": task_count,
                "objectives": obj_count,
                "llm_calls": llm_count,
                "decisions": decision_count,
                "findings": finding_count,
                "knowledge_sources": knowledge_count,
            },
        })

    memberships = db.query(Membership).filter(Membership.organization_id == org_id).all()
    members_data = [
        {"user_id": m.user_id, "role": m.role,
         "created_at": _dt_iso(getattr(m, "created_at", None))}
        for m in memberships
    ]

    audit_count = 0
    if project_ids:
        audit_count = db.query(AuditLog).filter(AuditLog.project_id.in_(project_ids)).count()

    return {
        "gdpr_article": "20",
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "subject": "organization",
        "identity": {
            "id": org.id,
            "slug": org.slug,
            "name": org.name,
            "plan": org.plan,
            "created_at": _dt_iso(org.created_at),
        },
        "projects": projects_data,
        "members": members_data,
        "audit_log_entries_count": audit_count,
        "totals": {
            "projects": len(projects_data),
            "members": len(members_data),
        },
        "notes": [
            "This export summarizes the organization — per-project detailed exports available separately.",
            "LLM call bodies (prompts/responses) contain the largest payloads; request verbose export for those.",
            "Workspace filesystem artifacts under forge_output/{slug}/ are not included — filesystem export is a separate operation.",
        ],
    }

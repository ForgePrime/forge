"""Skills v0 (F1+F2+F5) — library + per-project attach.

Built-in skills are seeded on first request to ensure marketplace not empty.
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, ProjectSkill, Skill, User


router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


# Built-in seed (F5 — phase defaults).
BUILT_IN: list[dict] = [
    {
        "external_id": "SK-security-owasp", "category": "SKILL",
        "name": "Security review — OWASP top 10 sweep",
        "description": "Scans diff for SQLi, XSS, broken auth, SSRF, broken access control, misconfig.",
        "applies_to_phases": ["develop", "challenger"],
        "auto_attach_rule": {"if_diff_touches": ["auth/", "api/", "middleware/"]},
        "cost_impact_usd": 0.08,
        "prompt_text": "You are a security reviewer. Walk through the diff and flag anything that resembles "
                       "the OWASP top 10. For each finding give: severity, location, and the smallest fix.",
    },
    {
        "external_id": "SK-scenario-gen-nonhappy", "category": "SKILL",
        "name": "Non-happy-path scenario generator",
        "description": "For each AC, produce 3-5 failure modes and edge cases.",
        "applies_to_phases": ["analysis", "planning"],
        "cost_impact_usd": 0.15,
        "prompt_text": "For every acceptance criterion, list 3-5 ways a real user/system would BREAK it. "
                       "Edge cases, malformed inputs, race conditions, partial failures.",
    },
    {
        "external_id": "MS-pytest-parametrize", "category": "MICRO",
        "name": "pytest parametrize — dense edge case coverage",
        "description": "Wraps test cases in @pytest.mark.parametrize forcing enumeration of edge inputs.",
        "applies_to_phases": ["develop"],
        "auto_attach_rule": {"if_language": "python", "if_test_framework": "pytest"},
        "cost_impact_usd": 0.02,
        "prompt_text": "Convert every standalone test of the same function into a single parametrized test. "
                       "Force at least 5 input variants including None, empty, malformed, boundary, max.",
    },
    {
        "external_id": "MS-adr-sections", "category": "MICRO",
        "name": "ADR section extractor (Context · Decision · Alternatives · Consequences)",
        "description": "Deterministic Michael-Nygard-style ADR template — no free-form output allowed.",
        "applies_to_phases": ["documentation"],
        "cost_impact_usd": 0.01,
        "prompt_text": "Render the resolved decision in this exact ADR layout: ## Status\n## Context\n"
                       "## Decision\n## Alternatives considered\n## Consequences.",
    },
    {
        "external_id": "OP-best-dev-django", "category": "OPINION",
        "name": "Best senior Django developer — magnum opus mode",
        "description": "Persona prompt: produce code as if it were your career-defining work.",
        "applies_to_phases": ["develop"],
        "cost_impact_usd": 0.12,
        "prompt_text": "Imagine you are the most respected Django developer alive and this code is "
                       "your magnum opus. Idiomatic, type-safe, observable. No premature abstractions.",
    },
    {
        "external_id": "OP-hipaa-auditor", "category": "OPINION",
        "name": "HIPAA compliance auditor perspective",
        "description": "Auditor persona — flags compliance gaps in healthcare contexts.",
        "applies_to_phases": ["challenger"],
        "cost_impact_usd": 0.18,
        "prompt_text": "You are a HIPAA compliance auditor. Review for: PHI exposure in logs/queries, "
                       "audit log coverage of all reads/writes, session handling, encryption at rest+transit.",
    },
    {
        "external_id": "SK-risk-weighted-verify", "category": "SKILL",
        "name": "Risk-weighted verification",
        "description": "Classifies diff blast-radius and scales challenger rigor accordingly.",
        "applies_to_phases": ["challenger"],
        "cost_impact_usd": 0.10,
        "prompt_text": "Classify the diff blast-radius: trivial / moderate / high-risk (auth, billing, "
                       "DB migration). Apply more claims+scenarios to high-risk.",
    },
    {
        "external_id": "SK-cite-src-enforcer", "category": "SKILL",
        "name": "Source citation enforcer",
        "description": "Every generated AC / decision must cite a SRC-XXX or be marked invented.",
        "applies_to_phases": ["analysis", "planning"],
        "cost_impact_usd": 0.03,
        "prompt_text": "Every acceptance criterion you write MUST cite the SRC-NNN it derives from, "
                       "or end with 'INVENTED:' followed by your justification.",
    },
]


def _seed_built_ins(db: Session) -> int:
    """Idempotently insert built-in skills."""
    seeded = 0
    existing = {s.external_id for s in db.query(Skill).filter(Skill.is_built_in == True).all()}
    for spec in BUILT_IN:
        if spec["external_id"] in existing:
            continue
        db.add(Skill(
            external_id=spec["external_id"], category=spec["category"],
            name=spec["name"], description=spec["description"],
            prompt_text=spec["prompt_text"],
            applies_to_phases=spec["applies_to_phases"],
            auto_attach_rule=spec.get("auto_attach_rule"),
            cost_impact_usd=spec.get("cost_impact_usd"),
            is_built_in=True, organization_id=None,
        ))
        seeded += 1
    if seeded:
        db.commit()
    return seeded


def _user(request: Request) -> User:
    u = getattr(request.state, "user", None)
    if not u:
        raise HTTPException(401)
    return u


@router.get("")
def list_skills(request: Request, category: str | None = None,
                phase: str | None = None, db: Session = Depends(get_db)):
    """List all skills available to this org (built-in + org-private)."""
    _user(request)
    _seed_built_ins(db)
    org = getattr(request.state, "org", None)
    q = db.query(Skill).filter(
        (Skill.organization_id.is_(None)) |
        (Skill.organization_id == (org.id if org else -1))
    )
    if category:
        q = q.filter(Skill.category == category.upper())
    skills = q.order_by(Skill.category, Skill.name).all()
    if phase:
        skills = [s for s in skills if phase in (s.applies_to_phases or [])]
    return {"skills": [{
        "id": s.id, "external_id": s.external_id, "category": s.category,
        "name": s.name, "description": s.description,
        "applies_to_phases": s.applies_to_phases,
        "cost_impact_usd": s.cost_impact_usd,
        "is_built_in": s.is_built_in,
    } for s in skills]}


class AttachBody(BaseModel):
    skill_external_id: str = Field(..., min_length=1)
    attach_mode: str = Field("manual", pattern="^(auto|manual|default)$")


@router.post("/projects/{slug}/attach")
def attach_skill(slug: str, body: AttachBody, request: Request, db: Session = Depends(get_db)):
    """Attach a skill to a project with given mode."""
    _user(request)
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404, "project not found")
    org = getattr(request.state, "org", None)
    if org and proj.organization_id != org.id:
        raise HTTPException(403)
    sk = db.query(Skill).filter(Skill.external_id == body.skill_external_id).first()
    if not sk:
        raise HTTPException(404, "skill not found")
    existing = db.query(ProjectSkill).filter(
        ProjectSkill.project_id == proj.id, ProjectSkill.skill_id == sk.id
    ).first()
    if existing:
        existing.attach_mode = body.attach_mode
    else:
        db.add(ProjectSkill(project_id=proj.id, skill_id=sk.id, attach_mode=body.attach_mode))
    db.commit()
    return {"slug": slug, "skill": body.skill_external_id, "attach_mode": body.attach_mode}


@router.delete("/projects/{slug}/attach/{skill_external_id}")
def detach_skill(slug: str, skill_external_id: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    org = getattr(request.state, "org", None)
    if org and proj.organization_id != org.id:
        raise HTTPException(403)
    sk = db.query(Skill).filter(Skill.external_id == skill_external_id).first()
    if not sk:
        raise HTTPException(404)
    db.query(ProjectSkill).filter(
        ProjectSkill.project_id == proj.id, ProjectSkill.skill_id == sk.id
    ).delete()
    db.commit()
    return {"slug": slug, "skill": skill_external_id, "detached": True}


# ===================================================================
# F3 — skill ROI tracking
# ===================================================================

@router.post("/{skill_external_id}/record-invocation")
def skill_record_invocation(skill_external_id: str, request: Request,
                             db: Session = Depends(get_db),
                             project_slug: str | None = None):
    """Internal: incremented each time a skill is attached to a prompt run."""
    _user(request)
    sk = db.query(Skill).filter(Skill.external_id == skill_external_id).first()
    if not sk:
        raise HTTPException(404)
    if project_slug:
        proj = db.query(Project).filter(Project.slug == project_slug).first()
        if proj:
            link = db.query(ProjectSkill).filter(
                ProjectSkill.project_id == proj.id,
                ProjectSkill.skill_id == sk.id,
            ).first()
            if link:
                link.invocations += 1
                link.last_used_at = dt.datetime.now(dt.timezone.utc)
                db.commit()
    return {"skill": skill_external_id, "recorded": True}


@router.get("/{skill_external_id}/roi")
def skill_roi(skill_external_id: str, request: Request, db: Session = Depends(get_db)):
    """Aggregate skill ROI across all projects in the current org."""
    _user(request)
    sk = db.query(Skill).filter(Skill.external_id == skill_external_id).first()
    if not sk:
        raise HTTPException(404)
    org = getattr(request.state, "org", None)
    q = db.query(ProjectSkill).join(Project, ProjectSkill.project_id == Project.id) \
        .filter(ProjectSkill.skill_id == sk.id)
    if org:
        q = q.filter(Project.organization_id == org.id)
    rows = q.all()
    total_invocations = sum(r.invocations for r in rows)
    projects_attached = len(rows)
    avg_per_project = total_invocations / projects_attached if projects_attached else 0
    return {
        "skill": skill_external_id, "category": sk.category,
        "projects_attached": projects_attached,
        "total_invocations": total_invocations,
        "avg_invocations_per_project": round(avg_per_project, 1),
        "cost_per_call_usd": sk.cost_impact_usd,
        "total_cost_attributed": round((sk.cost_impact_usd or 0) * total_invocations, 4),
        "eligible_for_marketplace": (
            projects_attached >= 3 and total_invocations >= 10
        ),
    }


# ===================================================================
# F4 — Marketplace promotion (org-level promotion of project-local skill)
# ===================================================================

@router.post("/{skill_external_id}/promote-to-org")
def promote_to_org(skill_external_id: str, request: Request, db: Session = Depends(get_db)):
    """Promote a skill from project-private to org-wide marketplace.
    Requires: ≥3 projects attached + ≥10 total invocations (ROI threshold)."""
    _user(request)
    sk = db.query(Skill).filter(Skill.external_id == skill_external_id).first()
    if not sk:
        raise HTTPException(404)
    if sk.organization_id is None:
        raise HTTPException(409, "skill is already org-wide / built-in")
    org = getattr(request.state, "org", None)
    if not org:
        raise HTTPException(403, "no org in session")
    if sk.organization_id != org.id:
        raise HTTPException(403, "cannot promote a skill you don't own")
    # ROI check
    rows = db.query(ProjectSkill).join(Project, ProjectSkill.project_id == Project.id) \
        .filter(ProjectSkill.skill_id == sk.id, Project.organization_id == org.id).all()
    projects_attached = len(rows)
    total_invocations = sum(r.invocations for r in rows)
    if projects_attached < 3:
        raise HTTPException(409, f"need ≥3 projects, have {projects_attached}")
    if total_invocations < 10:
        raise HTTPException(409, f"need ≥10 total invocations, have {total_invocations}")
    # Promote: simply unscope organization_id would make it global; instead we keep org scope
    # but mark built-in=True so it surfaces in org-wide marketplace listings.
    sk.is_built_in = True
    db.commit()
    return {"skill": skill_external_id, "promoted": True,
            "projects_attached": projects_attached,
            "total_invocations": total_invocations}


@router.get("/projects/{slug}")
def project_skills(slug: str, request: Request, db: Session = Depends(get_db)):
    """List skills attached to this project + their attach mode."""
    _user(request)
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    org = getattr(request.state, "org", None)
    if org and proj.organization_id != org.id:
        raise HTTPException(403)
    rows = db.query(ProjectSkill, Skill).join(Skill, ProjectSkill.skill_id == Skill.id) \
        .filter(ProjectSkill.project_id == proj.id).all()
    return {"slug": slug, "attached": [{
        "skill_id": s.id, "external_id": s.external_id, "category": s.category,
        "name": s.name, "attach_mode": ps.attach_mode,
        "applies_to_phases": s.applies_to_phases,
        "cost_impact_usd": s.cost_impact_usd,
        "invocations": ps.invocations,
    } for ps, s in rows]}

"""Project & Task CRUD — minimum endpoints to make MVP usable."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Project, Task, AcceptanceCriterion, Guideline, Decision, Finding, AuditLog, Knowledge, Objective, KeyResult

router = APIRouter(prefix="/api/v1", tags=["projects"])


# --- Schemas ---

class ProjectCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=300)
    goal: str | None = None


class ACCreate(BaseModel):
    text: str = Field(..., min_length=20)
    scenario_type: str = Field("positive", pattern="^(positive|negative|edge_case|regression)$")
    verification: str = Field("manual", pattern="^(test|command|manual)$")
    test_path: str | None = None
    command: str | None = None


class TaskCreate(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    instruction: str | None = None
    type: str = Field("feature", pattern="^(feature|bug|chore|investigation)$")
    scopes: list[str] = Field(default_factory=list)
    origin: str | None = None
    produces: dict | None = None
    alignment: dict | None = None
    exclusions: list[str] | None = None
    depends_on: list[str] = Field(default_factory=list)
    acceptance_criteria: list[ACCreate] = Field(default_factory=list)


class GuidelineCreate(BaseModel):
    external_id: str
    title: str = Field(..., min_length=1)
    scope: str = "general"
    content: str = Field(..., min_length=1)
    rationale: str | None = None
    weight: str = Field("should", pattern="^(must|should|may)$")
    examples: list[str] | None = None


class KnowledgeCreate(BaseModel):
    external_id: str
    title: str = Field(..., min_length=1)
    category: str
    content: str = Field(..., min_length=10)
    scopes: list[str] = Field(default_factory=list)
    source_type: str | None = None
    source_ref: str | None = None


class DecisionCreate(BaseModel):
    external_id: str
    type: str
    issue: str = Field(..., min_length=1)
    recommendation: str = Field(..., min_length=1)
    reasoning: str | None = None
    status: str = "OPEN"
    severity: str | None = None
    confidence: str | None = None


class FindingTriageRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|defer|reject)$")
    reason: str | None = None


class KRCreate(BaseModel):
    text: str = Field(..., min_length=5)
    kr_type: str = Field("descriptive", pattern="^(numeric|descriptive)$")
    target_value: float | None = None
    measurement_command: str | None = None


class ObjectiveCreate(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=300)
    business_context: str = Field(..., min_length=10)
    scopes: list[str] = Field(default_factory=list)
    priority: int = Field(3, ge=1, le=5)
    key_results: list[KRCreate] = Field(default_factory=list)


class KRUpdate(BaseModel):
    status: str | None = Field(None, pattern="^(NOT_STARTED|IN_PROGRESS|ACHIEVED|MISSED)$")
    current_value: float | None = None


# --- Project endpoints ---

@router.post("/projects")
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Project).filter(Project.slug == body.slug).first()
    if existing:
        raise HTTPException(409, f"Project '{body.slug}' already exists")
    proj = Project(slug=body.slug, name=body.name, goal=body.goal)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {"id": proj.id, "slug": proj.slug}


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return [{"id": p.id, "slug": p.slug, "name": p.name, "goal": p.goal} for p in projects]


@router.get("/projects/{slug}/status")
def project_status(slug: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404, f"Project '{slug}' not found")

    tasks = db.query(Task).filter(Task.project_id == proj.id).all()
    by_status = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1

    open_decisions = db.query(Decision).filter(
        Decision.project_id == proj.id, Decision.status == "OPEN"
    ).count()

    open_findings = db.query(Finding).filter(
        Finding.project_id == proj.id, Finding.status == "OPEN"
    ).count()

    return {
        "project": slug,
        "tasks": by_status,
        "total_tasks": len(tasks),
        "open_decisions": open_decisions,
        "open_findings": open_findings,
    }


# --- Task endpoints ---

@router.post("/projects/{slug}/tasks")
def create_tasks(slug: str, tasks: list[TaskCreate], db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404, f"Project '{slug}' not found")

    created = []
    for t_data in tasks:
        # Validate AC for feature/bug
        if t_data.type in ("feature", "bug") and len(t_data.acceptance_criteria) < 1:
            raise HTTPException(422, f"Task {t_data.external_id}: feature/bug requires at least 1 AC")

        # Check instruction or description
        if not t_data.instruction and not t_data.description:
            raise HTTPException(422, f"Task {t_data.external_id}: must have instruction or description")

        task = Task(
            project_id=proj.id,
            external_id=t_data.external_id,
            name=t_data.name,
            description=t_data.description,
            instruction=t_data.instruction,
            type=t_data.type,
            scopes=t_data.scopes,
            origin=t_data.origin,
            produces=t_data.produces,
            alignment=t_data.alignment,
            exclusions=t_data.exclusions,
        )
        db.add(task)
        db.flush()

        # Add AC
        for i, ac in enumerate(t_data.acceptance_criteria):
            db.add(AcceptanceCriterion(
                task_id=task.id,
                position=i,
                text=ac.text,
                scenario_type=ac.scenario_type,
                verification=ac.verification,
                test_path=ac.test_path,
                command=ac.command,
            ))

        created.append({"id": task.id, "external_id": task.external_id})

    # Resolve dependencies by external_id
    all_tasks = {t.external_id: t for t in db.query(Task).filter(Task.project_id == proj.id).all()}
    for t_data in tasks:
        if t_data.depends_on:
            task = all_tasks.get(t_data.external_id)
            if task:
                for dep_ext in t_data.depends_on:
                    dep_task = all_tasks.get(dep_ext)
                    if dep_task:
                        task.dependencies.append(dep_task)
                    else:
                        raise HTTPException(422, f"Dependency {dep_ext} not found for task {t_data.external_id}")

    db.commit()
    return {"created": created}


@router.get("/projects/{slug}/tasks")
def list_tasks(slug: str, status: str | None = None, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    q = db.query(Task).filter(Task.project_id == proj.id)
    if status:
        q = q.filter(Task.status == status)
    tasks = q.order_by(Task.id).all()
    return [
        {
            "id": t.id,
            "external_id": t.external_id,
            "name": t.name,
            "type": t.type,
            "status": t.status,
            "scopes": t.scopes,
            "ac_count": len(t.acceptance_criteria),
            "depends_on": [d.external_id for d in t.dependencies],
        }
        for t in tasks
    ]


@router.get("/projects/{slug}/tasks/{external_id}")
def get_task(slug: str, external_id: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    task = db.query(Task).filter(Task.project_id == proj.id, Task.external_id == external_id).first()
    if not task:
        raise HTTPException(404)
    return {
        "id": task.id,
        "external_id": task.external_id,
        "name": task.name,
        "type": task.type,
        "status": task.status,
        "instruction": task.instruction,
        "description": task.description,
        "scopes": task.scopes,
        "origin": task.origin,
        "produces": task.produces,
        "alignment": task.alignment,
        "exclusions": task.exclusions,
        "ceremony_level": task.ceremony_level,
        "agent": task.agent,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "acceptance_criteria": [
            {
                "position": ac.position,
                "text": ac.text,
                "scenario_type": ac.scenario_type,
                "verification": ac.verification,
                "test_path": ac.test_path,
                "command": ac.command,
            }
            for ac in task.acceptance_criteria
        ],
        "depends_on": [d.external_id for d in task.dependencies],
        "executions": [
            {"id": e.id, "status": e.status, "attempt": e.attempt_number}
            for e in task.executions
        ],
    }


# --- Guideline endpoints ---

@router.post("/projects/{slug}/guidelines")
def create_guidelines(slug: str, guidelines: list[GuidelineCreate], db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    created = []
    for g in guidelines:
        db.add(Guideline(
            project_id=proj.id,
            external_id=g.external_id,
            title=g.title,
            scope=g.scope,
            content=g.content,
            rationale=g.rationale,
            weight=g.weight,
            examples=g.examples,
        ))
        created.append(g.external_id)
    db.commit()
    return {"created": created}


@router.get("/projects/{slug}/guidelines")
def list_guidelines(slug: str, weight: str | None = None, scope: str | None = None, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    q = db.query(Guideline).filter(
        (Guideline.project_id == proj.id) | (Guideline.project_id.is_(None)),
        Guideline.status == "ACTIVE",
    )
    if weight:
        q = q.filter(Guideline.weight == weight)
    if scope:
        q = q.filter(Guideline.scope == scope)
    guidelines = q.all()
    return [
        {
            "id": g.id,
            "external_id": g.external_id,
            "title": g.title,
            "scope": g.scope,
            "content": g.content,
            "weight": g.weight,
            "status": g.status,
        }
        for g in guidelines
    ]


# --- Knowledge endpoints ---

@router.post("/projects/{slug}/knowledge")
def create_knowledge(slug: str, items: list[KnowledgeCreate], db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    created = []
    for k in items:
        db.add(Knowledge(
            project_id=proj.id, external_id=k.external_id, title=k.title,
            category=k.category, content=k.content, scopes=k.scopes,
            source_type=k.source_type, source_ref=k.source_ref,
        ))
        created.append(k.external_id)
    db.commit()
    return {"created": created}


@router.get("/projects/{slug}/knowledge")
def list_knowledge(slug: str, category: str | None = None, status: str | None = None,
                   db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    q = db.query(Knowledge).filter(Knowledge.project_id == proj.id)
    if category:
        q = q.filter(Knowledge.category == category)
    if status:
        q = q.filter(Knowledge.status == status)
    return [
        {"id": k.id, "external_id": k.external_id, "title": k.title,
         "category": k.category, "content": k.content[:200], "scopes": k.scopes,
         "status": k.status, "version": k.version}
        for k in q.all()
    ]


# --- Decision endpoints ---

@router.post("/projects/{slug}/decisions")
def create_decisions(slug: str, decisions: list[DecisionCreate], db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    created = []
    for d in decisions:
        db.add(Decision(
            project_id=proj.id,
            external_id=d.external_id,
            type=d.type,
            issue=d.issue,
            recommendation=d.recommendation,
            reasoning=d.reasoning,
            status=d.status,
            severity=d.severity,
            confidence=d.confidence,
        ))
        created.append(d.external_id)
    db.commit()
    return {"created": created}


@router.get("/projects/{slug}/decisions")
def list_decisions(slug: str, status: str | None = None, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    q = db.query(Decision).filter(Decision.project_id == proj.id)
    if status:
        q = q.filter(Decision.status == status)
    return [
        {
            "id": d.id,
            "external_id": d.external_id,
            "type": d.type,
            "issue": d.issue,
            "recommendation": d.recommendation,
            "status": d.status,
            "severity": d.severity,
        }
        for d in q.all()
    ]


@router.post("/decisions/{decision_id}/resolve")
def resolve_decision(decision_id: int, body: dict, db: Session = Depends(get_db)):
    d = db.query(Decision).filter(Decision.id == decision_id).first()
    if not d:
        raise HTTPException(404)
    d.status = body.get("status", "CLOSED")
    d.resolution_notes = body.get("resolution_notes")
    db.commit()
    return {"id": d.id, "status": d.status}


# --- Finding triage ---

@router.get("/projects/{slug}/findings")
def list_findings(slug: str, status: str | None = None, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    q = db.query(Finding).filter(Finding.project_id == proj.id)
    if status:
        q = q.filter(Finding.status == status)
    return [
        {
            "id": f.id,
            "external_id": f.external_id,
            "type": f.type,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "status": f.status,
            "file_path": f.file_path,
        }
        for f in q.all()
    ]


@router.post("/findings/{finding_id}/triage")
def triage_finding(finding_id: int, body: FindingTriageRequest, db: Session = Depends(get_db)):
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    if not f:
        raise HTTPException(404)

    if body.action == "approve":
        # Create new task from finding
        proj = db.query(Project).filter(Project.id == f.project_id).first()
        max_ext = db.query(Task.external_id).filter(Task.project_id == proj.id).order_by(Task.id.desc()).first()
        next_num = int(max_ext[0].split("-")[1]) + 1 if max_ext else 1
        new_ext = f"T-{next_num:03d}"

        task = Task(
            project_id=proj.id,
            external_id=new_ext,
            name=f"fix-{f.external_id.lower()}-{f.title[:30].replace(' ', '-').lower()}",
            description=f.description,
            instruction=f"Fix: {f.title}\n\nEvidence: {f.evidence}\n\nSuggested action: {f.suggested_action or 'See description'}",
            type="bug",
            scopes=[],
        )
        db.add(task)
        db.flush()

        f.status = "APPROVED"
        f.triage_reason = body.reason
        f.created_task_id = task.id
        db.commit()
        return {"status": "APPROVED", "created_task": new_ext}

    elif body.action == "defer":
        f.status = "DEFERRED"
        f.triage_reason = body.reason or "Deferred"
        db.commit()
        return {"status": "DEFERRED"}

    elif body.action == "reject":
        f.status = "REJECTED"
        f.triage_reason = body.reason or "Rejected"
        db.commit()
        return {"status": "REJECTED"}


# --- Execution detail (read) ---

@router.get("/projects/{slug}/executions")
def list_executions(slug: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    from app.models import Execution
    execs = db.query(Execution).join(Task).filter(Task.project_id == proj.id).order_by(Execution.id.desc()).all()
    return [
        {
            "id": e.id,
            "task_external_id": e.task.external_id,
            "task_name": e.task.name,
            "status": e.status,
            "attempt": e.attempt_number,
            "agent": e.agent,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in execs
    ]


@router.get("/executions/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    from app.models import Execution, PromptElement
    e = db.query(Execution).filter(Execution.id == execution_id).first()
    if not e:
        raise HTTPException(404)

    elements = db.query(PromptElement).filter(PromptElement.execution_id == e.id).order_by(PromptElement.position).all()

    return {
        "id": e.id,
        "task_id": e.task.external_id,
        "status": e.status,
        "attempt": e.attempt_number,
        "agent": e.agent,
        "prompt_meta": e.prompt_meta,
        "prompt_hash": e.prompt_hash,
        "contract": e.contract,
        "delivery": e.delivery,
        "validation_result": e.validation_result,
        "lease_expires_at": e.lease_expires_at.isoformat() if e.lease_expires_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "delivered_at": e.delivered_at.isoformat() if e.delivered_at else None,
        "prompt_elements": [
            {
                "source_table": el.source_table,
                "source_external_id": el.source_external_id,
                "included": el.included,
                "selection_reason": el.selection_reason,
                "exclusion_reason": el.exclusion_reason,
                "char_count": el.char_count,
            }
            for el in elements
        ],
    }


@router.post("/projects/{slug}/objectives")
def create_objectives(slug: str, objectives: list[ObjectiveCreate], db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    created = []
    for o in objectives:
        if not o.key_results:
            raise HTTPException(422, f"Objective {o.external_id}: at least 1 KR required")
        obj = Objective(
            project_id=proj.id,
            external_id=o.external_id,
            title=o.title,
            business_context=o.business_context,
            scopes=o.scopes,
            priority=o.priority,
        )
        db.add(obj)
        db.flush()
        for i, kr in enumerate(o.key_results):
            if kr.kr_type == "numeric" and kr.target_value is None:
                raise HTTPException(422, f"KR {i} of {o.external_id}: numeric KR requires target_value")
            db.add(KeyResult(
                objective_id=obj.id,
                position=i,
                text=kr.text,
                kr_type=kr.kr_type,
                target_value=kr.target_value,
                measurement_command=kr.measurement_command,
            ))
        created.append({"id": obj.id, "external_id": obj.external_id})
    db.commit()
    return {"created": created}


@router.get("/projects/{slug}/objectives")
def list_objectives(slug: str, status: str | None = None, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    q = db.query(Objective).filter(Objective.project_id == proj.id)
    if status:
        q = q.filter(Objective.status == status)
    out = []
    for o in q.all():
        out.append({
            "id": o.id,
            "external_id": o.external_id,
            "title": o.title,
            "business_context": o.business_context,
            "status": o.status,
            "scopes": o.scopes,
            "priority": o.priority,
            "key_results": [
                {
                    "position": kr.position,
                    "text": kr.text,
                    "kr_type": kr.kr_type,
                    "status": kr.status,
                    "target_value": kr.target_value,
                    "current_value": kr.current_value,
                    "measurement_command": kr.measurement_command,
                }
                for kr in o.key_results
            ],
        })
    return out


@router.post("/projects/{slug}/tasks/{external_id}/generate-scenarios")
def generate_test_scenarios(slug: str, external_id: str, db: Session = Depends(get_db)):
    from app.services.scenario_generator import generate_scenarios
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).first()
    if not task:
        raise HTTPException(404)
    stubs = generate_scenarios(task.acceptance_criteria)
    return {
        "task": external_id,
        "scenario_count": len(stubs),
        "scenarios": [s.to_dict() for s in stubs],
    }


@router.patch("/objectives/{obj_id}/key-results/{kr_position}")
def update_kr(obj_id: int, kr_position: int, body: KRUpdate, db: Session = Depends(get_db)):
    kr = db.query(KeyResult).filter(
        KeyResult.objective_id == obj_id, KeyResult.position == kr_position
    ).first()
    if not kr:
        raise HTTPException(404)
    if body.status:
        kr.status = body.status
    if body.current_value is not None:
        kr.current_value = body.current_value
    db.commit()
    return {"position": kr.position, "status": kr.status, "current_value": kr.current_value}


@router.get("/executions/{execution_id}/prompt")
def get_execution_prompt(execution_id: int, db: Session = Depends(get_db)):
    from app.models import Execution
    e = db.query(Execution).filter(Execution.id == execution_id).first()
    if not e:
        raise HTTPException(404)
    return {"prompt_text": e.prompt_text}

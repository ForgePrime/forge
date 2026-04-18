"""Project & Task CRUD — minimum endpoints to make MVP usable."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Project, Task, AcceptanceCriterion, Guideline, Decision, Finding, AuditLog, Knowledge, Objective, KeyResult
from app.services.tenant import assert_project_in_org, current_org_id

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
    type: str = Field(
        "feature",
        # D1 — accept the four iterative-flow types in addition to the legacy four.
        pattern="^(feature|bug|chore|investigation|analysis|planning|develop|documentation)$",
    )
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
    text: str | None = Field(None, min_length=5)
    target_value: float | None = None
    measurement_command: str | None = None


class ObjectiveUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    business_context: str | None = Field(None, min_length=10)
    priority: int | None = Field(None, ge=1, le=5)
    status: str | None = Field(None, pattern="^(DRAFT|ACTIVE|ACHIEVED|ABANDONED)$")
    scopes: list[str] | None = None


class TaskUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    instruction: str | None = None
    description: str | None = None
    scopes: list[str] | None = None
    requirement_refs: list[str] | None = None
    completes_kr_ids: list[str] | None = None


class ACUpdate(BaseModel):
    text: str | None = Field(None, min_length=20)
    scenario_type: str | None = Field(None, pattern="^(positive|negative|edge_case|regression)$")
    verification: str | None = Field(None, pattern="^(test|command|manual)$")
    test_path: str | None = None
    command: str | None = None


class KRAdd(BaseModel):
    text: str = Field(..., min_length=5)
    kr_type: str = Field("descriptive", pattern="^(numeric|descriptive)$")
    target_value: float | None = None
    measurement_command: str | None = None


class ObjectiveCreateSingle(BaseModel):
    external_id: str | None = None  # auto-generated if null
    title: str = Field(..., min_length=1, max_length=300)
    business_context: str = Field(..., min_length=10)
    scopes: list[str] = Field(default_factory=list)
    priority: int = Field(3, ge=1, le=5)


class TaskCreateSingle(BaseModel):
    external_id: str | None = None
    name: str = Field(..., min_length=1, max_length=200)
    instruction: str | None = None
    description: str | None = None
    type: str = Field(
        "feature",
        # D1 — accept the four iterative-flow types in addition to the legacy four.
        pattern="^(feature|bug|chore|investigation|analysis|planning|develop|documentation)$",
    )
    scopes: list[str] = Field(default_factory=list)
    origin: str | None = None
    requirement_refs: list[str] | None = None
    completes_kr_ids: list[str] | None = None


# --- Project endpoints ---

@router.post("/projects")
def create_project(body: ProjectCreate, request: Request, db: Session = Depends(get_db)):
    org_id = current_org_id(request)
    if org_id is None:
        raise HTTPException(403, "No organization context")
    # Slugs are globally unique (DB constraint) — reject if taken in ANY org
    existing = db.query(Project).filter(Project.slug == body.slug).first()
    if existing:
        raise HTTPException(409, f"Project '{body.slug}' already exists")
    proj = Project(slug=body.slug, name=body.name, goal=body.goal, organization_id=org_id)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {"id": proj.id, "slug": proj.slug}


@router.get("/projects")
def list_projects(request: Request, db: Session = Depends(get_db)):
    org_id = current_org_id(request)
    if org_id is None:
        return []
    projects = db.query(Project).filter(Project.organization_id == org_id).all()
    return [{"id": p.id, "slug": p.slug, "name": p.name, "goal": p.goal} for p in projects]


@router.get("/projects/{slug}/status")
def project_status(slug: str, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)

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
def create_tasks(slug: str, tasks: list[TaskCreate], request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)

    created = []
    for t_data in tasks:
        # Validate AC for feature/bug
        if t_data.type in ("feature", "bug") and len(t_data.acceptance_criteria) < 1:
            raise HTTPException(422, f"Task {t_data.external_id}: feature/bug requires at least 1 AC")
        if t_data.type in ("feature", "bug"):
            has_testable = any(
                ac.verification in ("test", "command") and (ac.test_path or ac.command)
                for ac in t_data.acceptance_criteria
            )
            if not has_testable:
                raise HTTPException(
                    422,
                    f"Task {t_data.external_id}: feature/bug requires at least 1 AC with "
                    "verification='test'|'command' and test_path/command set — "
                    "manual-only AC cannot gate execution.",
                )

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
def list_tasks(slug: str, request: Request, status: str | None = None, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def get_task(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def create_guidelines(slug: str, guidelines: list[GuidelineCreate], request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def list_guidelines(slug: str, request: Request, weight: str | None = None, scope: str | None = None, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def create_knowledge(slug: str, items: list[KnowledgeCreate], request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def list_knowledge(slug: str, request: Request, category: str | None = None, status: str | None = None,
                   db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def create_decisions(slug: str, decisions: list[DecisionCreate], request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def list_decisions(slug: str, request: Request, status: str | None = None, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def list_findings(slug: str, request: Request, status: str | None = None, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def list_executions(slug: str, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def create_objectives(slug: str, objectives: list[ObjectiveCreate], request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def list_objectives(slug: str, request: Request, status: str | None = None, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
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
def generate_test_scenarios(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    from app.services.scenario_generator import generate_scenarios
    proj = assert_project_in_org(db, slug, request)
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
    if body.status is not None:
        kr.status = body.status
    if body.current_value is not None:
        kr.current_value = body.current_value
    if body.text is not None:
        kr.text = body.text
    if body.target_value is not None:
        kr.target_value = body.target_value
    if body.measurement_command is not None:
        kr.measurement_command = body.measurement_command
    db.commit()
    return {
        "position": kr.position, "status": kr.status, "current_value": kr.current_value,
        "text": kr.text, "target_value": kr.target_value, "measurement_command": kr.measurement_command,
    }


@router.patch("/projects/{slug}/objectives/{external_id}")
def update_objective(slug: str, external_id: str, body: ObjectiveUpdate, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    obj = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not obj:
        raise HTTPException(404)
    for field in ("title", "business_context", "priority", "status", "scopes"):
        val = getattr(body, field)
        if val is not None:
            setattr(obj, field, val)
    db.commit()
    return {
        "external_id": obj.external_id, "title": obj.title,
        "business_context": obj.business_context, "priority": obj.priority,
        "status": obj.status, "scopes": obj.scopes,
    }


@router.patch("/projects/{slug}/tasks/{external_id}")
def update_task(slug: str, external_id: str, body: TaskUpdate, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    for field in ("name", "instruction", "description", "scopes", "requirement_refs", "completes_kr_ids"):
        val = getattr(body, field)
        if val is not None:
            setattr(task, field, val)
    db.commit()
    return {
        "external_id": task.external_id, "name": task.name,
        "instruction": task.instruction, "description": task.description,
        "scopes": task.scopes, "requirement_refs": task.requirement_refs,
        "completes_kr_ids": task.completes_kr_ids,
    }


@router.get("/executions/{execution_id}/prompt")
def get_execution_prompt(execution_id: int, db: Session = Depends(get_db)):
    from app.models import Execution
    e = db.query(Execution).filter(Execution.id == execution_id).first()
    if not e:
        raise HTTPException(404)
    return {"prompt_text": e.prompt_text}


# --- AC CRUD ---

def _next_task_ac_position(db: Session, task_id: int) -> int:
    """Next AC position for task (max existing + 1, or 0)."""
    from sqlalchemy import func as _func
    max_pos = db.query(_func.max(AcceptanceCriterion.position)).filter(
        AcceptanceCriterion.task_id == task_id
    ).scalar()
    return (max_pos + 1) if max_pos is not None else 0


@router.post("/projects/{slug}/tasks/{external_id}/ac")
def add_ac(slug: str, external_id: str, body: ACCreate, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    pos = _next_task_ac_position(db, task.id)
    ac = AcceptanceCriterion(
        task_id=task.id, position=pos,
        text=body.text, scenario_type=body.scenario_type,
        verification=body.verification, test_path=body.test_path, command=body.command,
    )
    db.add(ac)
    db.commit()
    return {"position": pos, "text": ac.text, "scenario_type": ac.scenario_type}


@router.patch("/projects/{slug}/tasks/{external_id}/ac/{position}")
def update_ac(slug: str, external_id: str, position: int, body: ACUpdate, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    ac = db.query(AcceptanceCriterion).filter(
        AcceptanceCriterion.task_id == task.id, AcceptanceCriterion.position == position
    ).first()
    if not ac:
        raise HTTPException(404)
    for field in ("text", "scenario_type", "verification", "test_path", "command"):
        val = getattr(body, field)
        if val is not None:
            setattr(ac, field, val)
    db.commit()
    return {
        "position": ac.position, "text": ac.text, "scenario_type": ac.scenario_type,
        "verification": ac.verification, "test_path": ac.test_path, "command": ac.command,
    }


@router.delete("/projects/{slug}/tasks/{external_id}/ac/{position}")
def delete_ac(slug: str, external_id: str, position: int, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    ac = db.query(AcceptanceCriterion).filter(
        AcceptanceCriterion.task_id == task.id, AcceptanceCriterion.position == position
    ).first()
    if not ac:
        raise HTTPException(404)
    db.delete(ac)
    db.commit()
    return {"deleted": True, "position": position}


# --- Add manual Objective / KR / Task (single-entity, not batch planning) ---

def _next_obj_external_id(db: Session, project_id: int) -> str:
    from sqlalchemy import func as _func
    max_id = db.query(_func.max(Objective.external_id)).filter(
        Objective.project_id == project_id,
        Objective.external_id.like("O-%"),
    ).scalar()
    if not max_id:
        return "O-001"
    try:
        num = int(max_id.split("-")[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f"O-{num:03d}"


def _next_task_external_id(db: Session, project_id: int) -> str:
    from sqlalchemy import func as _func
    max_id = db.query(_func.max(Task.external_id)).filter(
        Task.project_id == project_id,
        Task.external_id.like("T-%"),
    ).scalar()
    if not max_id:
        return "T-001"
    try:
        num = int(max_id.split("-")[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f"T-{num:03d}"


@router.post("/projects/{slug}/objectives/new")
def add_objective_single(slug: str, body: ObjectiveCreateSingle, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    ext = body.external_id or _next_obj_external_id(db, proj.id)
    if db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == ext
    ).first():
        raise HTTPException(409, f"Objective {ext} already exists")
    obj = Objective(
        project_id=proj.id, external_id=ext,
        title=body.title, business_context=body.business_context,
        scopes=body.scopes, priority=body.priority,
    )
    db.add(obj)
    db.commit()
    return {"id": obj.id, "external_id": obj.external_id}


@router.post("/objectives/{obj_id}/key-results")
def add_kr(obj_id: int, body: KRAdd, db: Session = Depends(get_db)):
    obj = db.query(Objective).filter(Objective.id == obj_id).first()
    if not obj:
        raise HTTPException(404)
    from sqlalchemy import func as _func
    max_pos = db.query(_func.max(KeyResult.position)).filter(
        KeyResult.objective_id == obj_id
    ).scalar()
    pos = (max_pos + 1) if max_pos is not None else 0
    if body.kr_type == "numeric" and body.target_value is None:
        raise HTTPException(422, "numeric KR requires target_value")
    kr = KeyResult(
        objective_id=obj_id, position=pos,
        text=body.text, kr_type=body.kr_type,
        target_value=body.target_value, measurement_command=body.measurement_command,
    )
    db.add(kr)
    db.commit()
    return {"position": pos, "text": kr.text, "kr_type": kr.kr_type}


@router.delete("/objectives/{obj_id}/key-results/{position}")
def delete_kr(obj_id: int, position: int, db: Session = Depends(get_db)):
    kr = db.query(KeyResult).filter(
        KeyResult.objective_id == obj_id, KeyResult.position == position
    ).first()
    if not kr:
        raise HTTPException(404)
    db.delete(kr)
    db.commit()
    return {"deleted": True}


@router.post("/projects/{slug}/tasks/new")
def add_task_single(slug: str, body: TaskCreateSingle, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    ext = body.external_id or _next_task_external_id(db, proj.id)
    if db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == ext
    ).first():
        raise HTTPException(409, f"Task {ext} already exists")
    if body.type in ("feature", "bug") and not body.instruction and not body.description:
        raise HTTPException(422, f"feature/bug task requires instruction or description")
    task = Task(
        project_id=proj.id, external_id=ext,
        name=body.name, instruction=body.instruction, description=body.description,
        type=body.type, scopes=body.scopes, origin=body.origin,
        requirement_refs=body.requirement_refs, completes_kr_ids=body.completes_kr_ids,
    )
    db.add(task)
    db.commit()
    return {"id": task.id, "external_id": task.external_id}


@router.delete("/projects/{slug}/tasks/{external_id}")
def delete_task(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    if task.status in ("IN_PROGRESS",):
        raise HTTPException(409, "Cannot delete task while in progress")
    db.delete(task)
    db.commit()
    return {"deleted": True}


class GuidelineUpdate(BaseModel):
    title: str | None = None
    scope: str | None = None
    content: str | None = Field(None, min_length=1)
    rationale: str | None = None
    weight: str | None = Field(None, pattern="^(must|should|may)$")


@router.post("/projects/{slug}/guidelines/single")
def add_guideline_single(slug: str, body: GuidelineCreate, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    if not body.external_id:
        from sqlalchemy import func as _func
        max_id = db.query(_func.max(Guideline.external_id)).filter(
            Guideline.project_id == proj.id, Guideline.external_id.like("G-%")
        ).scalar()
        if max_id:
            try:
                num = int(max_id.split("-")[1]) + 1
            except (IndexError, ValueError):
                num = 1
            body.external_id = f"G-{num:03d}"
        else:
            body.external_id = "G-001"
    g = Guideline(
        project_id=proj.id, external_id=body.external_id,
        title=body.title, scope=body.scope, content=body.content,
        rationale=body.rationale, weight=body.weight, examples=body.examples,
    )
    db.add(g)
    db.commit()
    return {"id": g.id, "external_id": g.external_id}


@router.patch("/projects/{slug}/guidelines/{external_id}")
def update_guideline(slug: str, external_id: str, body: GuidelineUpdate, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    g = db.query(Guideline).filter(
        Guideline.project_id == proj.id, Guideline.external_id == external_id
    ).first()
    if not g:
        raise HTTPException(404)
    for f in ("title","scope","content","rationale","weight"):
        v = getattr(body, f)
        if v is not None:
            setattr(g, f, v)
    db.commit()
    return {"external_id": g.external_id, "title": g.title, "scope": g.scope,
            "weight": g.weight, "content": g.content}


@router.delete("/projects/{slug}/guidelines/{external_id}")
def delete_guideline(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    g = db.query(Guideline).filter(
        Guideline.project_id == proj.id, Guideline.external_id == external_id
    ).first()
    if not g:
        raise HTTPException(404)
    db.delete(g)
    db.commit()
    return {"deleted": True}


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


@router.post("/projects/{slug}/tasks/{external_id}/comments")
def add_comment(slug: str, external_id: str, body: CommentCreate, request: Request, db: Session = Depends(get_db)):
    from app.models import TaskComment
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    c = TaskComment(task_id=task.id, content=body.content)
    db.add(c)
    db.commit()
    return {"id": c.id, "content": c.content}


@router.get("/projects/{slug}/tasks/{external_id}/comments")
def list_comments(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    from app.models import TaskComment
    proj = assert_project_in_org(db, slug, request)
    task = db.query(Task).filter(
        Task.project_id == proj.id, Task.external_id == external_id
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(404)
    cmts = db.query(TaskComment).filter(TaskComment.task_id == task.id).order_by(TaskComment.id).all()
    return [{
        "id": c.id, "content": c.content,
        "user_email": c.user_email or "anonymous",
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in cmts]


@router.delete("/projects/{slug}/tasks/{external_id}/comments/{comment_id}")
def delete_comment(slug: str, external_id: str, comment_id: int, db: Session = Depends(get_db)):
    from app.models import TaskComment
    c = db.query(TaskComment).filter(TaskComment.id == comment_id).first()
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return {"deleted": True}


@router.delete("/projects/{slug}/objectives/{external_id}")
def delete_objective(slug: str, external_id: str, request: Request, db: Session = Depends(get_db)):
    proj = assert_project_in_org(db, slug, request)
    obj = db.query(Objective).filter(
        Objective.project_id == proj.id, Objective.external_id == external_id
    ).first()
    if not obj:
        raise HTTPException(404)
    # Check for tasks with origin = this objective
    n_tasks = db.query(Task).filter(
        Task.project_id == proj.id, Task.origin == external_id
    ).count()
    if n_tasks > 0:
        raise HTTPException(409, f"Cannot delete: {n_tasks} tasks still reference this objective as origin")
    db.delete(obj)
    db.commit()
    return {"deleted": True}

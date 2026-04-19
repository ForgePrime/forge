"""J4 + J5 — project lessons + org-level anti-patterns."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AntiPattern, Project, ProjectLesson, User


router = APIRouter(prefix="/api/v1/lessons", tags=["lessons"])


def _user(request: Request) -> User:
    u = getattr(request.state, "user", None)
    if not u:
        raise HTTPException(401)
    return u


class LessonBody(BaseModel):
    kind: str = Field(..., pattern="^(worked|didnt_work|incident|insight)$")
    title: str = Field(..., min_length=3, max_length=300)
    description: str = Field(..., min_length=10, max_length=10000)
    objective_external_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = Field("user", max_length=64)


@router.post("/projects/{slug}")
def create_lesson(slug: str, body: LessonBody, request: Request, db: Session = Depends(get_db)):
    user = _user(request)
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    org = getattr(request.state, "org", None)
    if org and proj.organization_id != org.id:
        raise HTTPException(403)
    lesson = ProjectLesson(
        project_id=proj.id, objective_external_id=body.objective_external_id,
        kind=body.kind, title=body.title.strip(), description=body.description.strip(),
        tags=body.tags, source=body.source, created_by_user_id=user.id,
    )
    db.add(lesson); db.commit()
    return {"id": lesson.id, "title": lesson.title}


@router.get("/projects/{slug}")
def list_lessons(slug: str, request: Request, db: Session = Depends(get_db)):
    _user(request)
    proj = db.query(Project).filter(Project.slug == slug).first()
    if not proj:
        raise HTTPException(404)
    org = getattr(request.state, "org", None)
    if org and proj.organization_id != org.id:
        raise HTTPException(403)
    rows = db.query(ProjectLesson).filter(
        ProjectLesson.project_id == proj.id
    ).order_by(ProjectLesson.id.desc()).all()
    return {"slug": slug, "lessons": [{
        "id": l.id, "kind": l.kind, "title": l.title, "description": l.description,
        "tags": l.tags, "source": l.source,
        "objective": l.objective_external_id,
        "created_at": l.created_at.isoformat(),
    } for l in rows]}


class AntiPatternBody(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    description: str = Field(..., min_length=10)
    example: str | None = None
    correct_way: str | None = None
    applies_to_kinds: list[str] = Field(default_factory=list)
    promoted_from_lesson_id: int | None = None


@router.post("/anti-patterns")
def create_anti_pattern(body: AntiPatternBody, request: Request, db: Session = Depends(get_db)):
    _user(request)
    org = getattr(request.state, "org", None)
    ap = AntiPattern(
        organization_id=org.id if org else None,
        title=body.title.strip(), description=body.description.strip(),
        example=body.example, correct_way=body.correct_way,
        applies_to_kinds=body.applies_to_kinds,
        promoted_from_lesson_id=body.promoted_from_lesson_id,
    )
    db.add(ap); db.commit()
    return {"id": ap.id, "title": ap.title}


@router.get("/anti-patterns")
def list_anti_patterns(request: Request, db: Session = Depends(get_db)):
    _user(request)
    org = getattr(request.state, "org", None)
    q = db.query(AntiPattern).filter(AntiPattern.active == True)
    if org:
        q = q.filter((AntiPattern.organization_id == org.id) | (AntiPattern.organization_id.is_(None)))
    rows = q.order_by(AntiPattern.times_seen.desc(), AntiPattern.id.desc()).all()
    return {"anti_patterns": [{
        "id": ap.id, "title": ap.title, "description": ap.description,
        "example": ap.example, "correct_way": ap.correct_way,
        "applies_to_kinds": ap.applies_to_kinds,
        "times_seen": ap.times_seen,
        "promoted_from_lesson_id": ap.promoted_from_lesson_id,
    } for ap in rows]}


@router.post("/anti-patterns/{ap_id}/record-seen")
def record_seen(ap_id: int, request: Request, db: Session = Depends(get_db)):
    _user(request)
    ap = db.query(AntiPattern).filter(AntiPattern.id == ap_id).first()
    if not ap:
        raise HTTPException(404)
    ap.times_seen += 1
    db.commit()
    return {"times_seen": ap.times_seen}


@router.delete("/anti-patterns/{ap_id}")
def deactivate_ap(ap_id: int, request: Request, db: Session = Depends(get_db)):
    _user(request)
    ap = db.query(AntiPattern).filter(AntiPattern.id == ap_id).first()
    if not ap:
        raise HTTPException(404)
    ap.active = False
    db.commit()
    return {"deactivated": True}


# ---- Forge-self seed: the incident user just hit ----

SELF_ANTI_PATTERN_SEED = [
    {
        "title": "Tests only cover fresh-signup fixtures — miss pre-existing-data paths",
        "description": (
            "Route handlers added new imports / DB joins, but the test suite's module-scoped "
            "fixture created a brand-new project+org+user for every test. Routes running "
            "against ORIGINAL DB state (pre-existing projects like `asda`) exposed import / "
            "schema mismatches that fresh-fixture tests never exercised. Result: 500 Internal "
            "Server Error on production data, but 100% green CI."
        ),
        "example": (
            "objective_detail_view imported `AcceptanceCriterion` from app.models, but a later "
            "edit removed the import. Tests all called /ui/projects/{fresh-slug}/objectives/"
            "O-001 — that code path didn't hit the AC query because fresh objective has no "
            "tasks → AC query never ran. User opened /ui/projects/asda/objectives/O-002 with "
            "pre-existing tasks → AC query fired → NameError: AcceptanceCriterion is not defined."
        ),
        "correct_way": (
            "Every UI route test MUST run twice: once on a fresh-fixture project and once on a "
            "pre-existing project with populated data (tasks, ACs, llm_calls, decisions). "
            "Add a conftest.py fixture `populated_project` that seeds the DB before the test "
            "module runs, alongside `fresh_project`. Every route test iterates both fixtures "
            "(pytest.mark.parametrize over [fresh_project, populated_project])."
        ),
        "applies_to_kinds": ["test", "import", "regression", "ui-routing"],
    },
    {
        "title": "'97% passed on mockup review' without running the server end-to-end",
        "description": (
            "After adding new UI template sections referenced by mockups (scrutiny debt, "
            "decision modals, SVG DAG, per-objective rollup), tests only verified that "
            "template-parsing returned HTTP 200 — not that every template context key was "
            "populated without errors. Missing context keys render as empty but don't crash; "
            "missing module imports DO crash but only on code paths not exercised by fresh-"
            "fixture tests."
        ),
        "correct_way": (
            "Add a 'deep-render' test per template that asserts: (a) every {% if x %} "
            "condition branch gets evaluated at least once across fixtures, (b) every template "
            "variable actually has a value in the passed context, (c) the whole response body "
            "length is > minimum viable (e.g. 5000 chars) to catch silent-empty renders."
        ),
        "applies_to_kinds": ["test", "template", "regression"],
    },
    # 2026-04-19 P5.4 round 1 — surfaced by live re-run after P1-P3 shipped.
    {
        "title": "Validator's structural rules ignore per-AC verification mode",
        "description": (
            "The contract validator enforced `must_reference_file_or_test` on every AC's "
            "evidence string, regardless of whether the AC's verification was `test` "
            "(file/test ref makes sense), `command` (evidence is naturally command output), "
            "or `manual` (user judgment). For command ACs, Claude's correct evidence "
            "(e.g. `alembic upgrade head — exit 0`) was rejected. With max_retries=3, the "
            "task FAILED unrecoverably."
        ),
        "example": (
            "T-001 of WarehouseFlow had AC-2: `alembic downgrade -1 && alembic upgrade head` "
            "with verification='command'. All 3 attempts failed validator with "
            "fix_hint='AC evidence [2] must reference file path or test name'. Claude "
            "couldn't satisfy the rule because command output naturally contains neither."
        ),
        "correct_way": (
            "Validators that enforce structural rules on Claude's output MUST be aware of "
            "the per-item type/mode. Pass the relevant DB ground truth (here: AC.verification "
            "per AC index) into the validator instead of applying one rule to all. When a "
            "rule swap is type-specific, the fix_hint must name the type so Claude knows "
            "what shape of evidence is expected."
        ),
        "applies_to_kinds": ["validator", "contract", "regression", "fix_hint"],
    },
    # 2026-04-19 P5.6 — surfaced same day; orchestrate run finished `status=DONE` while
    # `tasks_failed=1` and `tasks_completed=0`. Misleading.
    {
        "title": "Terminal status conflates 'loop finished' with 'work succeeded'",
        "description": (
            "OrchestrateRun.status went to `DONE` whenever the loop exited normally, even "
            "if every task in the run had FAILED. The progress_message read "
            "`Completed N tasks (0 done)` — the word 'completed' implied success while the "
            "parenthetical reversed it. Operators glanced at the dashboard and assumed work "
            "was shipped."
        ),
        "example": (
            "P5.4 live run #207 ended with status=DONE, tasks_failed=1, tasks_completed=0, "
            "and progress_message='Completed 1 tasks (0 done)'. Status pill rendered green."
        ),
        "correct_way": (
            "Distinguish 'loop completed' from 'work succeeded'. Add intermediate terminal "
            "states (here: PARTIAL_FAIL when any task FAILED, even if loop exited normally). "
            "Pill colors must match the user's intuition (green only for fully successful)."
        ),
        "applies_to_kinds": ["status", "ui", "telemetry", "regression"],
    },
]


def seed_self_anti_patterns(db: Session) -> int:
    """Idempotent seed. Returns number of new rows."""
    seeded = 0
    for spec in SELF_ANTI_PATTERN_SEED:
        existing = db.query(AntiPattern).filter(AntiPattern.title == spec["title"]).first()
        if existing:
            continue
        db.add(AntiPattern(
            organization_id=None,  # global / forge-self
            title=spec["title"], description=spec["description"],
            example=spec.get("example"), correct_way=spec.get("correct_way"),
            applies_to_kinds=spec.get("applies_to_kinds") or [],
        ))
        seeded += 1
    if seeded:
        db.commit()
    return seeded


@router.post("/seed-self")
def seed_self(request: Request, db: Session = Depends(get_db)):
    _user(request)
    n = seed_self_anti_patterns(db)
    return {"seeded": n}

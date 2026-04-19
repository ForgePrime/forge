"""Shared fixtures that populate a project with NON-TRIVIAL pre-existing data.

Rationale (from AntiPattern seed):
  The `asda`/`O-002` incident was a NameError on a code path that only fires when
  a project has real tasks + AC + executions. Fresh-signup fixtures never triggered it.
  Every route test must now run against a *populated* project fixture to catch
  import/query errors that only surface with real data.

Usage:
    from tests.conftest_populated import populated_slug_factory
    slug = populated_slug_factory()
"""
import time
import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    AcceptanceCriterion, Decision, Execution, Finding, Knowledge,
    LLMCall, Objective, Project, Task,
)


BASE = "http://127.0.0.1:8063"


# Registry of project slugs created during the pytest session.
# Read by tests/conftest.py at session-finish to docker-rm matching workspace
# infra containers (`forge-{slug}-postgres`, `forge-{slug}-redis`).
CREATED_SLUGS: list[str] = []


def _signup_and_project(prefix: str = "pop") -> tuple[requests.Session, str]:
    """Signup a new user + create a project under them."""
    ts = int(time.time() * 1000)
    s = requests.Session()
    r = s.post(f"{BASE}/ui/signup", data={
        "email": f"{prefix}-{ts}@t.com", "password": "pw-test-12345", "full_name": prefix.upper(),
        "org_slug": f"{prefix}-{ts}", "org_name": prefix.upper(),
    }, allow_redirects=False)
    assert r.status_code == 303
    s.headers["X-CSRF-Token"] = s.cookies.get("forge_csrf") or ""
    slug = f"{prefix}-{ts}"
    r = s.post(f"{BASE}/ui/projects", data={"slug": slug, "name": f"{prefix}", "goal": "populated"},
               allow_redirects=False)
    assert r.status_code == 303
    CREATED_SLUGS.append(slug)
    return s, slug


def populate_with_realistic_data(slug: str) -> None:
    """Seed a project with: 1 KB source + 2 objectives + 4 tasks (1 with ACs, 1 with exec+llm_call,
    1 FAILED, 1 IN_PROGRESS) + 1 decision OPEN + 1 finding.

    Mirrors what a real week-old project looks like. Code paths that assume entities
    exist (joins, aggregations) now fire on real data.
    """
    db: Session = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        assert proj, f"project {slug} not created"
        # KB source
        kn = Knowledge(
            project_id=proj.id, external_id="SRC-001",
            title="Populated source", category="source-document",
            content="# test\nValuable KB content for route coverage.", source_type="manual",
            description="description for the source",
        )
        db.add(kn)
        # Objective
        obj = Objective(project_id=proj.id, external_id="O-001",
                        title="Populated objective", business_context="ctx" * 10,
                        status="ACTIVE", priority=3)
        db.add(obj)
        obj2 = Objective(project_id=proj.id, external_id="O-002",
                         title="Second populated objective", business_context="ctx" * 10,
                         status="ACHIEVED", priority=2)
        db.add(obj2)
        db.flush()

        # Task 1: DONE with ACs + execution + llm_call
        t1 = Task(project_id=proj.id, external_id="T-001",
                  name="populated task 1", instruction="do thing",
                  type="develop", status="DONE", origin="O-001",
                  requirement_refs=["SRC-001"])
        db.add(t1); db.flush()
        db.add(AcceptanceCriterion(
            task_id=t1.id, position=0,
            text="Populated AC text minimum 20 chars here.",
            scenario_type="positive", verification="test",
            source_ref="SRC-001",
        ))
        db.add(AcceptanceCriterion(
            task_id=t1.id, position=1,
            text="Another populated AC also with enough characters.",
            scenario_type="negative", verification="manual",
            source_ref=None,  # triggers "INVENTED BY LLM" badge
        ))
        exe = Execution(task_id=t1.id, agent="orch", status="ACCEPTED",
                        attempt_number=1)
        db.add(exe); db.flush()
        db.add(LLMCall(
            execution_id=exe.id, project_id=proj.id,
            purpose="execute", model="sonnet",
            prompt_hash="sha256:populated",
            prompt_chars=100, prompt_preview="populated prompt",
            full_prompt="populated full prompt text",
            response_chars=50, response_text="populated response",
            return_code=0, duration_ms=1200, cost_usd=0.05,
            model_used="sonnet",
        ))
        # Task 2: FAILED
        db.add(Task(project_id=proj.id, external_id="T-002",
                    name="failed task", instruction="thing",
                    type="develop", status="FAILED", origin="O-001"))
        # Task 3: IN_PROGRESS analysis
        db.add(Task(project_id=proj.id, external_id="T-003",
                    name="analysis in progress", instruction="analyze",
                    type="analysis", status="IN_PROGRESS", origin="O-002"))
        # Task 4: TODO planning
        db.add(Task(project_id=proj.id, external_id="T-004",
                    name="planning queued", instruction="plan",
                    type="planning", status="TODO", origin="O-002"))

        # Decision (OPEN) + Finding
        db.add(Decision(project_id=proj.id, external_id="D-001",
                        type="question", severity="HIGH",
                        issue="Populated open question",
                        recommendation="Initial recommendation",
                        status="OPEN", reasoning="test"))
        # Finding needs a finding-friendly model
        db.add(Finding(project_id=proj.id, execution_id=exe.id,
                       external_id="F-001", type="lint", severity="medium",
                       title="populated finding",
                       description="populated finding description",
                       status="OPEN"))
        db.commit()
    finally:
        db.close()


def build_populated_project(prefix: str = "pop") -> tuple[requests.Session, str]:
    """One-shot: signup + create + populate. Returns (session, slug)."""
    s, slug = _signup_and_project(prefix=prefix)
    populate_with_realistic_data(slug)
    return s, slug

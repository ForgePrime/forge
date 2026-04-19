"""P1.2 — ProjectHooks must actually fire when tasks complete.

The regression we're preventing: hooks_tab in the UI let users wire a stage→skill
mapping, but the orchestrate loop never fired them. User got no audit trail, no
llm_call, nothing — the hook was inert config.

These tests mechanically prove:
  1. `fire_hooks_for_task` inserts a HookRun row when a matching hook exists.
  2. Disabled hooks are skipped.
  3. Hooks for mismatched stages are skipped.
  4. `skipped_no_skill` path runs when hook has no Skill attached.
  5. `skipped_no_cli` path runs when Claude CLI is not installed.
  6. `list_hooks` surfaces `last_fired_at` + `last_status`.
  7. `list_hook_runs` returns the audit trail.
"""
import datetime as dt
from unittest import mock

import pytest

from app.database import SessionLocal
from app.models import (
    HookRun, LLMCall, Project, ProjectHook, Skill, Task,
)
from app.services.hooks_runner import fire_hooks_for_task, TASK_TYPE_TO_STAGE
from tests.conftest_populated import build_populated_project

BASE = "http://127.0.0.1:8063"


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p1hooks")


def _seed_hook(db, proj_id: int, stage: str, skill_id: int | None = None,
               enabled: bool = True, purpose: str = "test") -> int:
    h = ProjectHook(
        project_id=proj_id, stage=stage, skill_id=skill_id,
        enabled=enabled, purpose_text=purpose,
    )
    db.add(h); db.commit(); db.refresh(h)
    return h.id


def _seed_skill(db, name: str = "test-skill") -> int:
    sk = Skill(
        external_id=f"SK-{name}-{int(dt.datetime.now().timestamp()*1000)}",
        category="SKILL", name=name, prompt_text="You are a test skill.",
        applies_to_phases=[],
    )
    db.add(sk); db.commit(); db.refresh(sk)
    return sk.id


def _pick_task(db, proj_id: int, task_type: str = "develop") -> Task:
    """Get any task for this project; set its type so the stage mapping fires."""
    t = db.query(Task).filter(Task.project_id == proj_id).first()
    assert t, "populated fixture should have tasks"
    t.type = task_type
    db.commit()
    return t


def test_task_type_to_stage_mapping_covers_all_stages():
    """Every hook stage in the CHECK constraint must have at least one task type that maps to it."""
    stages_used = set(TASK_TYPE_TO_STAGE.values())
    for s in ("after_analysis", "after_planning", "after_develop", "after_documentation"):
        assert s in stages_used, f"no task type maps to {s}"


def test_fire_hooks_with_no_hooks_configured_returns_empty(ps):
    """Baseline: no ProjectHook rows for this project → nothing fires, no rows inserted."""
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        # Make sure no hooks exist
        db.query(ProjectHook).filter(ProjectHook.project_id == proj.id).delete()
        db.commit()
        task = _pick_task(db, proj.id, task_type="develop")
        before = db.query(HookRun).filter(HookRun.project_id == proj.id).count()
        runs = fire_hooks_for_task(db, proj, task)
        after = db.query(HookRun).filter(HookRun.project_id == proj.id).count()
        assert runs == []
        assert after == before
    finally:
        db.close()


def test_fire_hooks_skips_disabled(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _pick_task(db, proj.id, task_type="develop")
        hook_id = _seed_hook(db, proj.id, "after_develop", skill_id=None, enabled=False)
        before = db.query(HookRun).filter(HookRun.project_id == proj.id).count()
        fire_hooks_for_task(db, proj, task)
        after = db.query(HookRun).filter(HookRun.project_id == proj.id).count()
        assert after == before, "disabled hook must not fire"
        # cleanup
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.commit()
    finally:
        db.close()


def test_fire_hooks_skips_mismatched_stage(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _pick_task(db, proj.id, task_type="develop")
        # Hook on a different stage — should NOT fire for a develop task
        hook_id = _seed_hook(db, proj.id, "after_analysis", skill_id=None, enabled=True)
        before = db.query(HookRun).filter(HookRun.project_id == proj.id).count()
        fire_hooks_for_task(db, proj, task)
        after = db.query(HookRun).filter(HookRun.project_id == proj.id).count()
        assert after == before, "stage mismatch must not fire"
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.commit()
    finally:
        db.close()


def test_fire_hooks_records_skipped_no_skill(ps):
    """Hook with no skill attached still gets a HookRun row (proves wiring)."""
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _pick_task(db, proj.id, task_type="develop")
        hook_id = _seed_hook(db, proj.id, "after_develop", skill_id=None, enabled=True,
                             purpose="metadata only")
        runs = fire_hooks_for_task(db, proj, task)
        assert len(runs) == 1
        assert runs[0].hook_id == hook_id
        assert runs[0].status == "skipped_no_skill"
        assert runs[0].finished_at is not None
        assert runs[0].task_id == task.id
        db.query(HookRun).filter(HookRun.hook_id == hook_id).delete()
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.commit()
    finally:
        db.close()


def test_fire_hooks_records_skipped_no_cli(ps):
    """When CLI is missing and hook has a skill, status=skipped_no_cli."""
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _pick_task(db, proj.id, task_type="develop")
        skill_id = _seed_skill(db, "hook-test-skill")
        hook_id = _seed_hook(db, proj.id, "after_develop", skill_id=skill_id, enabled=True)
        with mock.patch("app.services.hooks_runner._claude_available", return_value=False):
            runs = fire_hooks_for_task(db, proj, task)
        assert len(runs) == 1
        assert runs[0].status == "skipped_no_cli"
        assert runs[0].llm_call_id is None
        db.query(HookRun).filter(HookRun.hook_id == hook_id).delete()
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.query(Skill).filter(Skill.id == skill_id).delete()
        db.commit()
    finally:
        db.close()


def test_fire_hooks_records_llm_call_when_cli_present(ps):
    """With CLI + skill, a HookRun is created AND an LLMCall is linked."""
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = _pick_task(db, proj.id, task_type="develop")
        skill_id = _seed_skill(db, "hook-llm-test")
        hook_id = _seed_hook(db, proj.id, "after_develop", skill_id=skill_id, enabled=True)

        fake_result = mock.MagicMock(
            agent_response="This is the hook review.",
            cost_usd=0.03, duration_ms=120, return_code=0,
            input_tokens=50, output_tokens=20, model_used="sonnet",
            is_error=False, stderr="",
        )
        with mock.patch("app.services.hooks_runner._claude_available", return_value=True), \
             mock.patch("app.services.claude_cli.invoke_claude", return_value=fake_result):
            runs = fire_hooks_for_task(db, proj, task)
        assert len(runs) == 1
        run = runs[0]
        assert run.status == "fired"
        assert run.llm_call_id is not None
        llm = db.query(LLMCall).filter(LLMCall.id == run.llm_call_id).first()
        assert llm is not None
        assert llm.purpose == "hook:after_develop"
        assert "hook review" in (llm.response_text or "")

        db.query(HookRun).filter(HookRun.hook_id == hook_id).delete()
        db.query(LLMCall).filter(LLMCall.id == run.llm_call_id).delete()
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.query(Skill).filter(Skill.id == skill_id).delete()
        db.commit()
    finally:
        db.close()


def test_list_hooks_surfaces_last_fired(ps):
    """GET /hooks must include last_fired_at + last_status so the UI can render it."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        hook_id = _seed_hook(db, proj.id, "after_develop", skill_id=None, enabled=True,
                             purpose="surface test")
        # Seed a HookRun directly
        run = HookRun(
            project_id=proj.id, hook_id=hook_id, stage="after_develop",
            status="fired", summary="ok",
            started_at=dt.datetime.now(dt.timezone.utc),
            finished_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(run); db.commit()
        run_id = run.id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/hooks")
    assert r.status_code == 200
    j = r.json()
    our = [h for h in j["hooks"] if h["id"] == hook_id]
    assert our, "our seeded hook should be in the list"
    h = our[0]
    assert h["last_fired_at"] is not None
    assert h["last_status"] == "fired"

    # cleanup
    db = SessionLocal()
    try:
        db.query(HookRun).filter(HookRun.id == run_id).delete()
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.commit()
    finally:
        db.close()


def test_list_hook_runs_returns_audit_trail(ps):
    """GET /hook-runs must expose the recent firings."""
    s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        hook_id = _seed_hook(db, proj.id, "after_develop", skill_id=None, enabled=True)
        run = HookRun(
            project_id=proj.id, hook_id=hook_id, task_id=task.id,
            stage="after_develop", status="skipped_no_skill",
            summary="no skill — metadata only",
            started_at=dt.datetime.now(dt.timezone.utc),
            finished_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(run); db.commit()
        run_id = run.id
    finally:
        db.close()

    r = s.get(f"{BASE}/api/v1/tier1/projects/{slug}/hook-runs")
    assert r.status_code == 200
    j = r.json()
    ours = [x for x in j["runs"] if x["id"] == run_id]
    assert ours, "seeded run must appear"
    row = ours[0]
    assert row["hook_stage"] == "after_develop"
    assert row["status"] == "skipped_no_skill"
    assert row["task_external_id"] is not None
    assert row["task_name"] is not None

    db = SessionLocal()
    try:
        db.query(HookRun).filter(HookRun.id == run_id).delete()
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.commit()
    finally:
        db.close()

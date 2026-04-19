"""P5.8 — hook timeout: default bumped + per-skill override.

2026-04-19 round 2c live run: hook fired on `after_develop`, invoked
SK-pytest-parametrize, timed out at the old 90s ceiling. Status flipped
to `error` with summary 'timeout'. Fix: default is 180s; each Skill can
override via `recommended_timeout_sec`."""
import datetime as dt
from unittest import mock

import pytest

from app.database import SessionLocal
from app.models import HookRun, LLMCall, Project, ProjectHook, Skill, Task
from app.services.hooks_runner import fire_hooks_for_task
from tests.conftest_populated import build_populated_project


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p58hook")


def _setup(slug: str, *, recommended_timeout_sec: int | None) -> tuple[int, int]:
    """Create skill + hook. Returns (skill_id, hook_id). Uses a fresh session."""
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        ts = int(dt.datetime.now().timestamp() * 1000)
        sk = Skill(
            external_id=f"SK-tmt-{ts}",
            category="SKILL", name="timeout-test", prompt_text="x",
            applies_to_phases=[],
            recommended_timeout_sec=recommended_timeout_sec,
        )
        db.add(sk); db.flush()
        h = ProjectHook(project_id=proj.id, stage="after_develop",
                        skill_id=sk.id, enabled=True)
        db.add(h); db.flush()
        # Make sure there's a develop task to fire on
        t = db.query(Task).filter(Task.project_id == proj.id).first()
        t.type = "develop"
        db.commit()
        return sk.id, h.id
    finally:
        db.close()


def _cleanup(skill_id: int, hook_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(HookRun).filter(HookRun.hook_id == hook_id).delete()
        db.query(LLMCall).filter(LLMCall.purpose == "hook:after_develop").delete()
        db.query(ProjectHook).filter(ProjectHook.id == hook_id).delete()
        db.query(Skill).filter(Skill.id == skill_id).delete()
        db.commit()
    finally:
        db.close()


def _fire(slug: str) -> dict:
    """Invoke fire_hooks_for_task with a mocked invoke_claude. Returns the kwargs the mock got."""
    captured: dict = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return mock.MagicMock(
            agent_response="ok", cost_usd=0.01, duration_ms=100, return_code=0,
            input_tokens=10, output_tokens=5, model_used="sonnet",
            is_error=False, stderr="",
        )

    with mock.patch("app.services.hooks_runner._claude_available", return_value=True), \
         mock.patch("app.services.claude_cli.invoke_claude", side_effect=_capture):
        db = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.slug == slug).first()
            task = db.query(Task).filter(
                Task.project_id == proj.id, Task.type == "develop"
            ).first()
            fire_hooks_for_task(db, proj, task)
        finally:
            db.close()
    return captured


def test_default_timeout_is_180s_when_skill_has_none(ps):
    _s, slug = ps
    skill_id, hook_id = _setup(slug, recommended_timeout_sec=None)
    try:
        captured = _fire(slug)
        assert captured.get("timeout_sec") == 180, f"got {captured.get('timeout_sec')}"
    finally:
        _cleanup(skill_id, hook_id)


def test_per_skill_override_wins(ps):
    _s, slug = ps
    skill_id, hook_id = _setup(slug, recommended_timeout_sec=420)
    try:
        captured = _fire(slug)
        assert captured.get("timeout_sec") == 420
    finally:
        _cleanup(skill_id, hook_id)


def test_skill_model_accepts_recommended_timeout(ps):
    """DB-level: the new column roundtrips correctly."""
    db = SessionLocal()
    skill_id = None
    try:
        ts = int(dt.datetime.now().timestamp() * 1000)
        sk = Skill(
            external_id=f"SK-rt-{ts}",
            category="SKILL", name="ts-check", prompt_text="x",
            applies_to_phases=[], recommended_timeout_sec=300,
        )
        db.add(sk); db.commit(); db.refresh(sk)
        skill_id = sk.id
        assert sk.recommended_timeout_sec == 300
        sk.recommended_timeout_sec = None
        db.commit(); db.refresh(sk)
        assert sk.recommended_timeout_sec is None
    finally:
        if skill_id:
            db.query(Skill).filter(Skill.id == skill_id).delete()
            db.commit()
        db.close()

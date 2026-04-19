"""P1.3 — Objective.challenger_checks must be injected into the Phase C prompt.

The regression we're preventing: users typed their domain-specific suspicions
into Objective.challenger_checks ("verify the user flow works end-to-end, not
just unit pass"), they were stored in the DB, and the challenger prompt never
read them. Challenger was blind to user intent.

These tests prove:
  1. resolve_challenger_checks_for_task walks the origin Objective + its dependency
     chain, dedupes by text, tolerates missing origin, handles str/dict entries.
  2. run_challenge injects the resolved checks into the prompt.
  3. run_challenge returns `injected_checks` in llm_call_meta for audit.
"""
from unittest import mock

import pytest

from app.database import SessionLocal
from app.models import Objective, Project, Task
from app.services.challenger import (
    _normalize_check,
    resolve_challenger_checks_for_task,
    run_challenge,
)
from tests.conftest_populated import build_populated_project


@pytest.fixture(scope="module")
def ps():
    return build_populated_project(prefix="p1chal")


# -----------------------------------------------------------------------------
# Resolver unit tests
# -----------------------------------------------------------------------------

def test_normalize_check_accepts_plain_string():
    assert _normalize_check("must return 403 on expired token") == "must return 403 on expired token"


def test_normalize_check_accepts_dict_with_text():
    assert _normalize_check({"text": "hello", "kind": "sec"}) == "hello"


def test_normalize_check_accepts_dict_with_description():
    assert _normalize_check({"description": "check payload"}) == "check payload"


def test_normalize_check_returns_none_for_empty():
    assert _normalize_check("") is None
    assert _normalize_check(None) is None
    assert _normalize_check({}) is None
    assert _normalize_check({"text": "   "}) is None


def test_resolve_returns_empty_when_task_has_no_origin(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        orig = task.origin
        task.origin = None
        db.commit()
        try:
            assert resolve_challenger_checks_for_task(db, task) == []
        finally:
            task.origin = orig
            db.commit()
    finally:
        db.close()


def test_resolve_returns_empty_when_origin_does_not_match(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        orig = task.origin
        task.origin = "O-does-not-exist-zzz"
        db.commit()
        try:
            assert resolve_challenger_checks_for_task(db, task) == []
        finally:
            task.origin = orig
            db.commit()
    finally:
        db.close()


def test_resolve_pulls_checks_from_root_objective(ps):
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(
            Task.project_id == proj.id, Task.origin.isnot(None)
        ).first()
        assert task, "populated fixture should have a task with origin"
        obj = db.query(Objective).filter(
            Objective.project_id == proj.id,
            Objective.external_id == task.origin,
        ).first()
        assert obj, "origin objective should resolve"
        original = obj.challenger_checks
        obj.challenger_checks = [
            "must return 403 on expired token",
            {"text": "verify idempotency"},
            "   ",  # whitespace only — must be filtered
            "must return 403 on expired token",  # dupe — must collapse
        ]
        db.commit()
        try:
            checks = resolve_challenger_checks_for_task(db, task)
            assert checks == ["must return 403 on expired token", "verify idempotency"]
        finally:
            obj.challenger_checks = original
            db.commit()
    finally:
        db.close()


def test_resolve_walks_objective_dependency_chain(ps):
    """Checks from a dependency-ancestor objective must also be included."""
    _s, slug = ps
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.slug == slug).first()
        task = db.query(Task).filter(
            Task.project_id == proj.id, Task.origin.isnot(None)
        ).first()
        root = db.query(Objective).filter(
            Objective.project_id == proj.id,
            Objective.external_id == task.origin,
        ).first()
        # Pick another objective as dependency
        other = db.query(Objective).filter(
            Objective.project_id == proj.id,
            Objective.id != root.id,
        ).first()
        if other is None:
            pytest.skip("populated fixture has only one objective")

        orig_root = root.challenger_checks
        orig_other = other.challenger_checks
        root.challenger_checks = ["root check"]
        other.challenger_checks = ["dep check"]
        if other not in (root.dependencies or []):
            root.dependencies.append(other)
        db.commit()
        try:
            checks = resolve_challenger_checks_for_task(db, task)
            assert "root check" in checks
            assert "dep check" in checks
            # root check comes first (BFS)
            assert checks.index("root check") < checks.index("dep check")
        finally:
            if other in root.dependencies:
                root.dependencies.remove(other)
            root.challenger_checks = orig_root
            other.challenger_checks = orig_other
            db.commit()
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Prompt-injection integration tests
# -----------------------------------------------------------------------------

class _FakeCLI:
    def __init__(self, response_json: str):
        self.captured_prompt: str | None = None
        self.response = response_json

    def __call__(self, *, prompt, workspace_dir, model, max_budget_usd, timeout_sec):
        self.captured_prompt = prompt
        from types import SimpleNamespace
        return SimpleNamespace(
            cost_usd=0.01, duration_ms=50, model_used=model,
            is_error=False, parse_error=None,
            delivery={"overall_verdict": "PASS", "summary": "ok",
                      "per_claim_verdicts": [], "new_findings": []},
            agent_response=self.response,
        )


def _mk_stub_task():
    from types import SimpleNamespace
    return SimpleNamespace(
        external_id="T-001", name="stub", type="feature",
        requirement_refs=[], completes_kr_ids=[],
    )


def test_run_challenge_injects_extra_checks_into_prompt():
    task = _mk_stub_task()
    fake = _FakeCLI('{"overall_verdict":"PASS","summary":"ok","per_claim_verdicts":[],"new_findings":[]}')
    checks = [
        "Verify rate limit on /login returns 429 after 5 attempts",
        "Ensure audit log row is written for every 2FA bypass",
    ]
    res = run_challenge(
        task=task, delivery={}, acceptance_criteria=[], test_run_data=None,
        extracted_decisions=[], extracted_findings=[],
        invoke_fn=fake, workspace_dir=".", extra_checks=checks,
    )
    assert fake.captured_prompt is not None
    for c in checks:
        assert c in fake.captured_prompt, f"check missing from prompt: {c}"
    assert "EXTRA CHALLENGER RULES" in fake.captured_prompt
    # Injection must come before the JSON contract marker
    inj_pos = fake.captured_prompt.find("EXTRA CHALLENGER RULES")
    json_pos = fake.captured_prompt.find("ODPOWIEDŹ — czysty JSON bez markdown:")
    assert 0 < inj_pos < json_pos, "checks must be injected before the JSON contract"
    # Audit meta
    assert res.llm_call_meta["injected_checks_count"] == 2
    assert res.llm_call_meta["injected_checks"] == checks


def test_run_challenge_omits_section_when_extra_checks_empty():
    task = _mk_stub_task()
    fake = _FakeCLI('{"overall_verdict":"PASS","summary":"ok","per_claim_verdicts":[],"new_findings":[]}')
    res = run_challenge(
        task=task, delivery={}, acceptance_criteria=[], test_run_data=None,
        extracted_decisions=[], extracted_findings=[],
        invoke_fn=fake, workspace_dir=".",
    )
    assert "EXTRA CHALLENGER RULES" not in fake.captured_prompt
    assert res.llm_call_meta["injected_checks_count"] == 0


def test_run_challenge_filters_blank_entries_in_extra_checks():
    task = _mk_stub_task()
    fake = _FakeCLI('{"overall_verdict":"PASS","summary":"ok","per_claim_verdicts":[],"new_findings":[]}')
    res = run_challenge(
        task=task, delivery={}, acceptance_criteria=[], test_run_data=None,
        extracted_decisions=[], extracted_findings=[],
        invoke_fn=fake, workspace_dir=".",
        extra_checks=["", "   ", "real check", None],
    )
    # Only "real check" should make it
    assert res.llm_call_meta["injected_checks"] == ["real check"]
    assert "real check" in fake.captured_prompt

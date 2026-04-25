"""Tests for `app/services/kill_criteria.py`.

Covers the K1-K6 event writer + K1 detection + last-24h count helper.
Uses a real DB connection (forge_migration_test or live forge_platform);
falls back gracefully if neither is reachable so the suite still passes
in pure-stdlib contexts (e.g. CI lint job that doesn't spin up Postgres).
"""

from __future__ import annotations

import datetime as dt
import os

import pytest

# These imports trigger SQLAlchemy bind, which requires postgres.
# If postgres isn't reachable, mark the entire module skipped so other
# offline test runs still pass cleanly.
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import (
        Decision,
        Execution,
        KillCriteriaEventLog,
        Project,
        SideEffectMap,
    )
    from app.services.kill_criteria import (
        VALID_KC_CODES,
        detect_k1_unowned_side_effects,
        detect_k2_uncited_ac_in_verify,
        detect_k4_solo_verifier,
        log_kill_criterion,
        tripped_in_last_24h,
    )
    from app.models import AcceptanceCriterion, LLMCall, Task
except Exception as e:  # pragma: no cover
    pytest.skip(f"DB-dependent imports failed: {e}", allow_module_level=True)


# Use the dedicated migration-test DB if it's been seeded; otherwise the
# main forge_platform. Tests are isolated by writing rows with a unique
# kc_code variant... actually we use a shared kc_code but always a brand-new
# decision_id (sequential), so no collision possible.

DB_URL = os.environ.get(
    "FORGE_TEST_DATABASE_URL",
    "postgresql://forge:forge@localhost:5432/forge_platform",
)

try:
    _engine = create_engine(DB_URL)
    with _engine.connect() as _c:
        pass
except Exception as e:  # pragma: no cover
    pytest.skip(f"could not connect to DB at {DB_URL}: {e}", allow_module_level=True)

SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture
def db_session():
    """Yield a Session that rolls back at the end (test isolation)."""
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def project_decision(db_session):
    """Create a throwaway Project + Decision for a test. Rolled back."""
    proj = Project(slug=f"kc-test-{dt.datetime.now().timestamp()}", name="kc-test", goal="t")
    db_session.add(proj)
    db_session.flush()

    dec = Decision(
        project_id=proj.id,
        external_id=f"DEC-KC-{proj.id}",
        type="root_cause",
        issue="test issue",
        recommendation="test rec",
        status="OPEN",
    )
    db_session.add(dec)
    db_session.flush()
    return proj, dec


# --- log_kill_criterion validation -------------------------------------------


def test_log_kill_criterion_writes_row(db_session, project_decision):
    proj, dec = project_decision
    event = log_kill_criterion(
        db_session, "K1", "test reason for K1 firing",
        decision_id=dec.id,
    )
    assert event.id is not None
    assert event.kc_code == "K1"
    assert event.decision_id == dec.id
    assert event.fired_at is not None


def test_log_kill_criterion_rejects_invalid_kc_code(db_session, project_decision):
    proj, dec = project_decision
    with pytest.raises(ValueError, match="kc_code"):
        log_kill_criterion(db_session, "K9", "reason here", decision_id=dec.id)


def test_log_kill_criterion_rejects_short_reason(db_session, project_decision):
    proj, dec = project_decision
    with pytest.raises(ValueError, match="reason"):
        log_kill_criterion(db_session, "K1", "abc", decision_id=dec.id)


def test_log_kill_criterion_rejects_no_entity_ref(db_session):
    with pytest.raises(ValueError, match="at least one"):
        log_kill_criterion(db_session, "K1", "reason without ref")


def test_log_kill_criterion_accepts_objective_only(db_session, project_decision):
    """Single entity ref is sufficient — DB CHECK uses OR."""
    proj, dec = project_decision
    # Use objective_id only (we don't have a real objective; pass NULL as
    # decision_id to verify objective-only path works at the validation level).
    # In practice objective_id would be a real FK; here we just verify the
    # validator accepts the shape.
    from app.models import Objective
    obj = Objective(
        project_id=proj.id,
        external_id="O-KC-TEST",
        title="test",
        business_context="test",
        status="ACTIVE",
        priority=3,
    )
    db_session.add(obj)
    db_session.flush()

    event = log_kill_criterion(db_session, "K2", "test reason", objective_id=obj.id)
    assert event.objective_id == obj.id
    assert event.decision_id is None


# --- detect_k1_unowned_side_effects ------------------------------------------


def _make_task(db_session, proj):
    """Helper: create minimal Task FK target for Execution."""
    from app.models import Task
    task = Task(
        project_id=proj.id,
        external_id=f"T-KC-{proj.id}",
        name="kc-test-task",
        type="feature",
        status="TODO",
        scopes=[],
        description="kc test",
    )
    db_session.add(task)
    db_session.flush()
    return task


def test_detect_k1_logs_event_for_unowned_side_effect(db_session, project_decision):
    proj, dec = project_decision
    task = _make_task(db_session, proj)

    # Attach an Execution to the Task
    exec_ = Execution(task_id=task.id, agent="test-agent", status="PROMPT_ASSEMBLED")
    db_session.add(exec_)
    db_session.flush()

    # Re-link the decision to the execution
    dec.execution_id = exec_.id
    db_session.flush()

    # Add 1 owned + 1 unowned side_effect_map row
    db_session.add(SideEffectMap(decision_id=dec.id, kind="db_write", owner="alice"))
    db_session.add(SideEffectMap(decision_id=dec.id, kind="api_call", owner=None))
    db_session.flush()

    events = detect_k1_unowned_side_effects(db_session, exec_.id)

    assert len(events) == 1
    assert events[0].kc_code == "K1"
    assert events[0].decision_id == dec.id
    assert "owner=NULL" in events[0].reason


def test_detect_k1_returns_empty_when_all_owned(db_session, project_decision):
    proj, dec = project_decision
    task = _make_task(db_session, proj)
    exec_ = Execution(task_id=task.id, agent="test-agent", status="PROMPT_ASSEMBLED")
    db_session.add(exec_)
    db_session.flush()
    dec.execution_id = exec_.id
    db_session.add(SideEffectMap(decision_id=dec.id, kind="db_write", owner="alice"))
    db_session.flush()

    events = detect_k1_unowned_side_effects(db_session, exec_.id)
    assert events == []


def test_detect_k1_returns_empty_when_no_decisions(db_session):
    """Execution with no linked Decisions = no K1 events."""
    events = detect_k1_unowned_side_effects(db_session, execution_id=99999999)
    assert events == []


# --- tripped_in_last_24h ----------------------------------------------------


def test_tripped_in_last_24h_counts_recent_events(db_session, project_decision):
    proj, dec = project_decision

    # Log 3 K1 events
    for i in range(3):
        log_kill_criterion(db_session, "K1", f"K1 reason #{i}", decision_id=dec.id)
    db_session.flush()

    count, last_at = tripped_in_last_24h(db_session, "K1", project_ids=[proj.id])
    assert count >= 3  # >= because other tests may have written rows in same DB
    assert last_at is not None


def test_tripped_in_last_24h_zero_for_unused_kc(db_session, project_decision):
    """K6 likely has no events; should return (0, None) without error."""
    proj, _ = project_decision
    count, last_at = tripped_in_last_24h(db_session, "K6", project_ids=[proj.id])
    assert count == 0
    assert last_at is None


def test_tripped_in_last_24h_rejects_invalid_code(db_session):
    with pytest.raises(ValueError):
        tripped_in_last_24h(db_session, "K9")


def test_tripped_in_last_24h_empty_project_list_returns_zero(db_session):
    count, last_at = tripped_in_last_24h(db_session, "K1", project_ids=[])
    assert count == 0
    assert last_at is None


# --- Constants exposure -----------------------------------------------------


def test_valid_kc_codes_is_complete():
    assert VALID_KC_CODES == {"K1", "K2", "K3", "K4", "K5", "K6"}


# --- K2: detect_k2_uncited_ac_in_verify -------------------------------------


_ac_position_counter = [0]


def _make_ac(db_session, task, *, source_ref=None, last_executed_at=None, epistemic_tag=None):
    _ac_position_counter[0] += 1
    ac = AcceptanceCriterion(
        task_id=task.id,
        position=_ac_position_counter[0],
        text="The system MUST do the thing in the prescribed manner X.",
        scenario_type="positive",
        verification="manual",
        source_ref=source_ref,
        last_executed_at=last_executed_at,
        epistemic_tag=epistemic_tag,
    )
    db_session.add(ac)
    db_session.flush()
    return ac


def test_detect_k2_fires_when_ac_verified_and_untagged(db_session, project_decision):
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    ac = _make_ac(
        db_session, task,
        last_executed_at=dt.datetime.now(dt.timezone.utc),
        epistemic_tag=None,
    )
    event = detect_k2_uncited_ac_in_verify(db_session, ac.id)
    assert event is not None
    assert event.kc_code == "K2"
    assert event.task_id == task.id
    assert "epistemic_tag=None" in event.reason or "INVENTED" in event.reason or "None" in event.reason


def test_detect_k2_fires_when_ac_verified_and_invented(db_session, project_decision):
    from app.models import EpistemicTag
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    ac = _make_ac(
        db_session, task,
        last_executed_at=dt.datetime.now(dt.timezone.utc),
        epistemic_tag=EpistemicTag.INVENTED,
    )
    event = detect_k2_uncited_ac_in_verify(db_session, ac.id)
    assert event is not None
    assert event.kc_code == "K2"


def test_detect_k2_quiet_when_ac_not_verified_yet(db_session, project_decision):
    """AC without last_executed_at = not-yet-verified → K2 doesn't apply."""
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    ac = _make_ac(db_session, task, last_executed_at=None, epistemic_tag=None)
    event = detect_k2_uncited_ac_in_verify(db_session, ac.id)
    assert event is None


def test_detect_k2_quiet_when_ac_cited(db_session, project_decision):
    from app.models import EpistemicTag
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    ac = _make_ac(
        db_session, task,
        last_executed_at=dt.datetime.now(dt.timezone.utc),
        epistemic_tag=EpistemicTag.ADR_CITED,
    )
    event = detect_k2_uncited_ac_in_verify(db_session, ac.id)
    assert event is None


def test_detect_k2_returns_none_for_missing_ac(db_session):
    event = detect_k2_uncited_ac_in_verify(db_session, ac_id=999999999)
    assert event is None


# --- K4: detect_k4_solo_verifier --------------------------------------------


def _make_llm_call(db_session, exec_id, *, purpose, model, model_used=None, project_id=None):
    call = LLMCall(
        execution_id=exec_id,
        purpose=purpose,
        model=model,
        model_used=model_used,
        project_id=project_id,
        prompt_hash=f"hash-{purpose}-{exec_id}",
        prompt_chars=100,
        prompt_preview=f"{purpose} prompt preview",
        return_code=0,
    )
    db_session.add(call)
    db_session.flush()
    return call


def test_detect_k4_fires_when_executor_and_challenger_same_model(db_session, project_decision):
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    exec_ = Execution(task_id=task.id, agent="test-agent", status="VALIDATING")
    db_session.add(exec_)
    db_session.flush()

    _make_llm_call(db_session, exec_.id, purpose="execute", model="claude-opus-4-7", project_id=proj.id)
    _make_llm_call(db_session, exec_.id, purpose="challenge", model="claude-opus-4-7", project_id=proj.id)

    event = detect_k4_solo_verifier(db_session, exec_.id)
    assert event is not None
    assert event.kc_code == "K4"
    assert event.task_id == task.id
    assert "claude-opus-4-7" in event.reason


def test_detect_k4_quiet_when_models_differ(db_session, project_decision):
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    exec_ = Execution(task_id=task.id, agent="test-agent", status="VALIDATING")
    db_session.add(exec_)
    db_session.flush()

    _make_llm_call(db_session, exec_.id, purpose="execute", model="claude-opus-4-7", project_id=proj.id)
    _make_llm_call(db_session, exec_.id, purpose="challenge", model="claude-sonnet-4-6", project_id=proj.id)

    event = detect_k4_solo_verifier(db_session, exec_.id)
    assert event is None


def test_detect_k4_quiet_without_challenge_call(db_session, project_decision):
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    exec_ = Execution(task_id=task.id, agent="test-agent", status="IN_PROGRESS")
    db_session.add(exec_)
    db_session.flush()
    _make_llm_call(db_session, exec_.id, purpose="execute", model="claude-opus-4-7", project_id=proj.id)
    # No challenge call → K4 doesn't apply
    event = detect_k4_solo_verifier(db_session, exec_.id)
    assert event is None


def test_detect_k4_uses_model_used_when_set(db_session, project_decision):
    """If LLMCall.model_used is set (actual model after fallback), K4 should
    compare those, not the requested `model`."""
    proj, _ = project_decision
    task = _make_task(db_session, proj)
    exec_ = Execution(task_id=task.id, agent="test-agent", status="VALIDATING")
    db_session.add(exec_)
    db_session.flush()

    # Both requested different models, but both fell back to the same model_used
    _make_llm_call(db_session, exec_.id, purpose="execute",
                   model="claude-opus-4-7", model_used="claude-haiku-4-5", project_id=proj.id)
    _make_llm_call(db_session, exec_.id, purpose="challenge",
                   model="claude-sonnet-4-6", model_used="claude-haiku-4-5", project_id=proj.id)

    event = detect_k4_solo_verifier(db_session, exec_.id)
    assert event is not None  # model_used matches → K4
    assert "claude-haiku-4-5" in event.reason

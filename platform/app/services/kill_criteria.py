"""Kill-criteria event service — Phase 1 redesign.

Foundational helpers for K1-K6 instrumentation. The kill_criteria are
gates over GateRegistry (per ADR-028 §Composite + UX_DESIGN.md §11.10):

  K1 — Unowned side-effect: side_effect_map row with owner=NULL at execute time
  K2 — ADR-uncited AC reached Verify: AC.epistemic_tag NULL entering verify
  K3 — Tier downgrade without Steward sign-off
  K4 — Solo-verifier: challenger model_id == executor model_id
  K5 — Gate spectrum WEAK → promote (gate-grade taxonomy expansion needed)
  K6 — Contract drift > 5% (ContractRevision diff metric)

This module provides:
  - `log_kill_criterion(...)` — pure writer, validates payload, appends one
    row to kill_criteria_event_log. Used by all detection paths.
  - `detect_k1_unowned_side_effects(db, execution_id)` — concrete K1 predicate.
    Reads side_effect_map rows linked to the Execution's Decisions, logs
    K1 for every owner-NULL row found.
  - `tripped_in_last_24h(db, kc_code, project_ids=None)` — count helper for
    DashboardView K1-K6 panel.

Detection helpers are designed for *call-site instrumentation*: callers
(state_transition, gate engine, verdict engine) invoke them at the
appropriate lifecycle hook. This module does NOT auto-instrument; that's
a separate decision per K-criterion.

Per CONTRACT §B.1 evidence-first: every K-event row carries a `reason`
string with the specific evidence (FK ids, snapshot values).
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.models import (
    AcceptanceCriterion,
    Decision,
    Execution,
    KillCriteriaEventLog,
    LLMCall,
    Project,
    SideEffectMap,
    Task,
)


VALID_KC_CODES = frozenset({"K1", "K2", "K3", "K4", "K5", "K6"})
MIN_REASON_LENGTH = 5  # mirrors DB CHECK constraint kc_reason_nonempty


def log_kill_criterion(
    db: Session,
    kc_code: str,
    reason: str,
    *,
    objective_id: int | None = None,
    decision_id: int | None = None,
    task_id: int | None = None,
    evidence_set_id: int | None = None,
) -> KillCriteriaEventLog:
    """Append one K-event to kill_criteria_event_log.

    Validates payload against the same constraints as the DB CHECK clauses
    so failures surface at write call site (clear stack) rather than at
    commit() (opaque IntegrityError).

    Returns the persisted row (with `id` populated). Does NOT auto-block
    a transition — blocking is the caller's responsibility (this is just
    the audit log).
    """
    if kc_code not in VALID_KC_CODES:
        raise ValueError(
            f"kc_code must be one of {sorted(VALID_KC_CODES)}; got {kc_code!r}"
        )
    if len(reason) < MIN_REASON_LENGTH:
        raise ValueError(
            f"reason must be ≥{MIN_REASON_LENGTH} characters; got {len(reason)}"
        )
    if not any((objective_id, decision_id, task_id)):
        raise ValueError(
            "at least one of objective_id, decision_id, task_id must be set "
            "(matches DB CHECK kc_at_least_one_ref)"
        )

    event = KillCriteriaEventLog(
        kc_code=kc_code,
        reason=reason,
        objective_id=objective_id,
        decision_id=decision_id,
        task_id=task_id,
        evidence_set_id=evidence_set_id,
    )
    db.add(event)
    db.flush()  # populate event.id without committing the outer transaction
    return event


def _k1_already_logged_for_se(db: Session, side_effect_id: int) -> bool:
    """Idempotency check: has K1 already been logged for this
    side_effect_map row?"""
    return (
        db.query(KillCriteriaEventLog.id)
        .filter(KillCriteriaEventLog.kc_code == "K1")
        .filter(KillCriteriaEventLog.reason.like(f"%side_effect_map.id={side_effect_id} %"))
        .first()
    ) is not None


def detect_k1_unowned_side_effects(
    db: Session,
    execution_id: int,
) -> list[KillCriteriaEventLog]:
    """K1 — Unowned side-effect: any side_effect_map row linked to this
    Execution (via execution.decision relationship) with owner IS NULL
    at execute time.

    Returns the list of K1 events logged (empty if no unowned side-effects).

    **Idempotent per side_effect_map.id**: if K1 has already been logged
    for a particular side_effect row (matched by `reason LIKE
    '%side_effect_map.id={N} %'`), it is skipped. Prevents duplicate
    events on retries / re-runs of the post_commit hook.

    Per CONTRACT §B.1: each event carries a reason naming the specific
    side_effect_map.id and kind for traceability.
    """
    # All Decisions tied to this Execution
    decision_ids = [
        row[0]
        for row in db.query(Decision.id).filter(Decision.execution_id == execution_id).all()
    ]
    if not decision_ids:
        return []

    unowned = (
        db.query(SideEffectMap)
        .filter(SideEffectMap.decision_id.in_(decision_ids))
        .filter(SideEffectMap.owner.is_(None))
        .all()
    )
    if not unowned:
        return []

    out: list[KillCriteriaEventLog] = []
    for se in unowned:
        if _k1_already_logged_for_se(db, se.id):
            continue
        reason = (
            f"K1 fired: side_effect_map.id={se.id} kind={se.kind!r} "
            f"on decision_id={se.decision_id} has owner=NULL at execute time "
            f"(execution_id={execution_id})"
        )
        event = log_kill_criterion(
            db,
            "K1",
            reason,
            decision_id=se.decision_id,
            evidence_set_id=se.evidence_set_id,
        )
        out.append(event)
    return out


def detect_k1_for_task(
    db: Session,
    task_id: int,
) -> list[KillCriteriaEventLog]:
    """K1 — Unowned side-effect, scoped to a Task.

    Walks Decisions linked to this Task (via decisions.task_id) and logs
    K1 for any side_effect_map row with owner IS NULL. Used as a
    post_commit hook on Task -> IN_PROGRESS transitions.

    Idempotent per side_effect_map.id (delegates to detect_k1
    idempotency logic).

    Returns the list of K1 events newly logged.
    """
    decision_ids = [
        row[0]
        for row in db.query(Decision.id).filter(Decision.task_id == task_id).all()
    ]
    if not decision_ids:
        return []

    unowned = (
        db.query(SideEffectMap)
        .filter(SideEffectMap.decision_id.in_(decision_ids))
        .filter(SideEffectMap.owner.is_(None))
        .all()
    )
    if not unowned:
        return []

    out: list[KillCriteriaEventLog] = []
    for se in unowned:
        if _k1_already_logged_for_se(db, se.id):
            continue
        reason = (
            f"K1 fired: side_effect_map.id={se.id} kind={se.kind!r} "
            f"on decision_id={se.decision_id} has owner=NULL at execute time "
            f"(task_id={task_id})"
        )
        event = log_kill_criterion(
            db,
            "K1",
            reason,
            task_id=task_id,
            decision_id=se.decision_id,
            evidence_set_id=se.evidence_set_id,
        )
        out.append(event)
    return out


def detect_k2_uncited_ac_in_verify(
    db: Session,
    ac_id: int,
) -> KillCriteriaEventLog | None:
    """K2 — ADR-uncited AC reached Verify: AcceptanceCriterion has been
    verified (last_executed_at set) but epistemic_tag is NULL or INVENTED.

    Returns the K2 event row if logged, else None.

    "Reached Verify" is a fuzzy lifecycle term in the redesign mock; in
    Forge's data model, an AC is considered verified once it has a
    `last_executed_at` timestamp (B1 trust-debt counter semantics). The
    epistemic_tag enum values that count as "cited" are everything EXCEPT
    `INVENTED` (and NULL).
    """
    ac = db.query(AcceptanceCriterion).filter(AcceptanceCriterion.id == ac_id).one_or_none()
    if ac is None:
        return None
    if ac.last_executed_at is None:
        # AC has not been verified — K2 doesn't apply yet.
        return None
    # Cited statuses: anything except NULL or INVENTED
    tag = getattr(ac, "epistemic_tag", None)
    if tag is not None and str(tag).upper() not in ("INVENTED", "EPISTEMICTAG.INVENTED"):
        # Tagged as something other than INVENTED → cited.
        return None
    # Resolve the task_id ref for entity scope
    task_id = ac.task_id
    reason = (
        f"K2 fired: AcceptanceCriterion.id={ac.id} reached verify "
        f"(last_executed_at={ac.last_executed_at}) with epistemic_tag={tag!r} "
        f"(NULL or INVENTED treated as un-cited)"
    )
    event = log_kill_criterion(db, "K2", reason, task_id=task_id)
    return event


def detect_k4_solo_verifier(
    db: Session,
    execution_id: int,
) -> KillCriteriaEventLog | None:
    """K4 — Solo-verifier: the LLMCall with purpose='challenge' on this
    Execution uses the same model as the LLMCall with purpose='execute'.

    Per ADR-012 distinct-actor: challenger MUST use a different model
    OR a human-in-loop. K4 fires when the challenger model == executor
    model AND no human-in-loop indicator (out-of-scope here; assumed False).

    Returns the K4 event row if logged, else None.

    **Idempotent per-execution**: if a K4 event has already been logged
    for this execution_id (any K4 row whose reason mentions
    `execution_id={N}`), skip and return None. Prevents duplicate events
    when the detector is invoked multiple times (e.g. on challenge call
    retry, or by the audit script after the auto-instrumentation already
    fired).

    Limitations (CONTRACT §A.1 disclosure):
    - 'human-in-loop' is not encoded on LLMCall in current schema; this
      detector treats every same-model executor+challenger pair as K4.
      Steward override path (per ADR-012) is not modelled here.
    - If multiple challenge calls exist (retries), only the first is
      compared — refine when retry semantics matter.
    """
    # Idempotency check: was K4 already logged for this execution?
    already = (
        db.query(KillCriteriaEventLog.id)
        .filter(KillCriteriaEventLog.kc_code == "K4")
        .filter(KillCriteriaEventLog.reason.like(f"%execution_id={execution_id}:%"))
        .first()
    )
    if already is not None:
        return None
    # Find executor model
    exec_call = (
        db.query(LLMCall)
        .filter(LLMCall.execution_id == execution_id)
        .filter(LLMCall.purpose == "execute")
        .order_by(LLMCall.id.asc())
        .first()
    )
    challenge_call = (
        db.query(LLMCall)
        .filter(LLMCall.execution_id == execution_id)
        .filter(LLMCall.purpose == "challenge")
        .order_by(LLMCall.id.asc())
        .first()
    )
    if exec_call is None or challenge_call is None:
        # No executor/challenger pair → K4 doesn't apply
        return None

    exec_model = exec_call.model_used or exec_call.model
    challenge_model = challenge_call.model_used or challenge_call.model
    if exec_model != challenge_model:
        return None

    # Resolve task_id via Execution → Task
    exec_row = db.query(Execution).filter(Execution.id == execution_id).one_or_none()
    task_id = exec_row.task_id if exec_row is not None else None

    reason = (
        f"K4 fired: solo-verifier on execution_id={execution_id}: "
        f"executor LLMCall.id={exec_call.id} model={exec_model!r} == "
        f"challenger LLMCall.id={challenge_call.id} model={challenge_model!r}"
    )
    event = log_kill_criterion(db, "K4", reason, task_id=task_id)
    return event


def tripped_in_last_24h(
    db: Session,
    kc_code: str,
    *,
    project_ids: Iterable[int] | None = None,
) -> tuple[int, dt.datetime | None]:
    """Return `(count, last_at)` for the given K-code over the last 24h.

    Powers DashboardView K1-K6 panel — the count drives the "Nx last 24h"
    badge; last_at drives the "HH:MM" timestamp.

    Filtering by project: events are filtered to rows whose objective_id
    OR (decision_id ∈ Decisions of project_ids) OR (task_id ∈ Tasks of
    project_ids) are in the visible scope. For now, simple filter:
    if project_ids is None → count all events. Project scoping is a
    refinement for later.
    """
    if kc_code not in VALID_KC_CODES:
        raise ValueError(f"kc_code must be one of {sorted(VALID_KC_CODES)}")

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)

    q = (
        db.query(
            sqlfunc.count(KillCriteriaEventLog.id),
            sqlfunc.max(KillCriteriaEventLog.fired_at),
        )
        .filter(KillCriteriaEventLog.kc_code == kc_code)
        .filter(KillCriteriaEventLog.fired_at >= since)
    )
    # Project scoping — filter to events whose linked entity is in the
    # visible projects (best-effort; uses subquery join).
    if project_ids is not None:
        project_ids_list = list(project_ids)
        if not project_ids_list:
            return (0, None)
        # Build a subquery of decision_ids visible to the org
        visible_decision_ids = (
            db.query(Decision.id).filter(Decision.project_id.in_(project_ids_list))
        )
        # Filter: event has decision_id in visible OR objective_id in visible OR task_id in visible
        # For simplicity in this first cut, filter ONLY by decision_id (most common ref).
        # Future refinement can add multi-FK subqueries.
        q = q.filter(
            (KillCriteriaEventLog.decision_id.in_(visible_decision_ids))
            | (KillCriteriaEventLog.decision_id.is_(None))
        )

    count, last_at = q.one()
    return (count or 0, last_at)


__all__ = [
    "VALID_KC_CODES",
    "log_kill_criterion",
    "detect_k1_unowned_side_effects",
    "detect_k1_for_task",
    "detect_k2_uncited_ac_in_verify",
    "detect_k4_solo_verifier",
    "tripped_in_last_24h",
]

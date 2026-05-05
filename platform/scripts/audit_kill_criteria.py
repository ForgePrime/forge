#!/usr/bin/env python3
"""Ad-hoc audit script for K1-K6 kill-criteria across the live DB.

Walks every implemented detector over the full corpus and reports counts.
Useful for:
  - Validating instrumentation coverage (do detectors find anything real?)
  - One-shot Steward review ahead of Phase 2 promotion
  - Sanity check before/after migration application

Does NOT auto-fix or auto-block — read-only audit. Each finding is logged
to kill_criteria_event_log only when --record is passed (default: dry-run).

Usage:
  audit_kill_criteria.py                  # dry-run, prints summary
  audit_kill_criteria.py --record         # ALSO writes events to DB
  audit_kill_criteria.py --json           # machine-readable output
  audit_kill_criteria.py --kc K1,K2,K4    # restrict to specific K-codes

Exit code: 0 always (audit is informational).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AcceptanceCriterion, Decision, Execution, LLMCall, SideEffectMap
from app.services.kill_criteria import (
    detect_k1_unowned_side_effects,
    detect_k2_uncited_ac_in_verify,
    detect_k4_solo_verifier,
)


def audit_k1(db: Session, *, record: bool) -> dict:
    """K1 — Unowned side-effect: count side_effect_map rows with owner=NULL.

    Returns counts grouped by Decision. When --record is passed, also
    writes K1 events for each unowned side-effect (via detect_k1 helper
    invoked per Execution).
    """
    unowned_count = (
        db.query(sqlfunc.count(SideEffectMap.id))
        .filter(SideEffectMap.owner.is_(None))
        .scalar() or 0
    )

    events_logged = 0
    if record and unowned_count > 0:
        # Walk every Execution that has a Decision linked → run detector
        exec_ids_with_unowned = (
            db.query(Decision.execution_id)
            .join(SideEffectMap, SideEffectMap.decision_id == Decision.id)
            .filter(SideEffectMap.owner.is_(None))
            .filter(Decision.execution_id.is_not(None))
            .distinct()
            .all()
        )
        for (exec_id,) in exec_ids_with_unowned:
            events = detect_k1_unowned_side_effects(db, exec_id)
            events_logged += len(events)
        db.commit()

    return {
        "code": "K1",
        "label": "Unowned side-effect",
        "unowned_side_effect_rows": unowned_count,
        "events_logged": events_logged,
    }


def audit_k2(db: Session, *, record: bool) -> dict:
    """K2 — ADR-uncited AC reached Verify: count ACs with last_executed_at
    set but epistemic_tag NULL or INVENTED."""
    # Both NULL and INVENTED count. Use OR via two queries summed.
    total_verified_ac = (
        db.query(sqlfunc.count(AcceptanceCriterion.id))
        .filter(AcceptanceCriterion.last_executed_at.is_not(None))
        .scalar() or 0
    )
    untagged_ac = (
        db.query(sqlfunc.count(AcceptanceCriterion.id))
        .filter(AcceptanceCriterion.last_executed_at.is_not(None))
        .filter(
            (AcceptanceCriterion.epistemic_tag.is_(None))
            | (AcceptanceCriterion.epistemic_tag == "INVENTED")
        )
        .scalar() or 0
    )

    events_logged = 0
    if record and untagged_ac > 0:
        ac_ids = [
            row[0]
            for row in db.query(AcceptanceCriterion.id)
                .filter(AcceptanceCriterion.last_executed_at.is_not(None))
                .filter(
                    (AcceptanceCriterion.epistemic_tag.is_(None))
                    | (AcceptanceCriterion.epistemic_tag == "INVENTED")
                )
                .all()
        ]
        for ac_id in ac_ids:
            event = detect_k2_uncited_ac_in_verify(db, ac_id)
            if event:
                events_logged += 1
        db.commit()

    return {
        "code": "K2",
        "label": "ADR-uncited AC reached Verify",
        "verified_ac_total": total_verified_ac,
        "untagged_or_invented": untagged_ac,
        "ratio_untagged": (untagged_ac / total_verified_ac) if total_verified_ac else None,
        "events_logged": events_logged,
    }


def audit_k4(db: Session, *, record: bool) -> dict:
    """K4 — Solo-verifier: count Executions where execute and challenge
    LLMCalls used the same model."""
    # Find executions that have BOTH execute and challenge calls
    exec_ids = [
        row[0]
        for row in db.query(LLMCall.execution_id)
            .filter(LLMCall.purpose.in_(["execute", "challenge"]))
            .filter(LLMCall.execution_id.is_not(None))
            .group_by(LLMCall.execution_id)
            .having(sqlfunc.count(LLMCall.purpose.distinct()) >= 2)
            .all()
    ]

    solo_count = 0
    events_logged = 0
    for exec_id in exec_ids:
        event = detect_k4_solo_verifier(db, exec_id)
        if event:
            solo_count += 1
            if record:
                events_logged += 1
            else:
                # Roll back to keep dry-run pure
                db.rollback()
    if record:
        db.commit()
    else:
        db.rollback()  # discard any flushed events

    return {
        "code": "K4",
        "label": "Solo-verifier",
        "executions_with_pair": len(exec_ids),
        "solo_verifier_count": solo_count,
        "events_logged": events_logged,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--record",
        action="store_true",
        help="ALSO write K-events to kill_criteria_event_log (default: dry-run)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--kc",
        type=str,
        default="K1,K2,K4",
        help="comma-separated K-codes to audit (default: K1,K2,K4 — implemented detectors)",
    )
    args = parser.parse_args(argv)

    requested = {kc.strip().upper() for kc in args.kc.split(",")}
    available = {"K1", "K2", "K4"}
    audit_funcs = {"K1": audit_k1, "K2": audit_k2, "K4": audit_k4}

    results: list[dict] = []
    with SessionLocal() as db:
        for code in sorted(requested & available):
            results.append(audit_funcs[code](db, record=args.record))

    skipped = requested - available
    if args.json:
        out = {"results": results, "skipped": sorted(skipped), "record_mode": args.record}
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"=== K-criteria audit (record={'ON' if args.record else 'DRY-RUN'}) ===")
        for r in results:
            print(f"\n{r['code']}: {r['label']}")
            for k, v in r.items():
                if k in ("code", "label"):
                    continue
                print(f"  {k}: {v}")
        if skipped:
            print(f"\nSkipped (not yet implemented): {sorted(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

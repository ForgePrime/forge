# ADR-024 — Error propagation mechanism (downstream artifact invalidation)

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** user (Tier 1 closure mass-accept) + AI agent (draft)
**Related:** AIOS A18 (Err(x)→Err(Dep(x))), AI-SDLC §19 + #20 (Errors invalidate downstream), Forge Complete §14 (Impact Closure), PLAN_GOVERNANCE new Stage G.11, THEOREM_VERIFICATION_AIOS_AISDLC.md §5.1 G-SHARED-2.

## Context

Three theorems require explicit error propagation:

- **AIOS Axiom 18**: `Err(x) → Err(Dependent(x))` for every dependent y.
- **AI-SDLC §19**: `Err_i ≠ empty ⇒ Invalidate(DependentArtifacts(S_i))`.
- **Forge Complete §14**: Impact closure covers dependencies, usages, side effects, execution paths.

Current Forge state:
- `ImpactClosure` (C.3) computes **forward impact** of a change: "what files/modules a Change touches."
- `Finding` entity exists for errors/observations but not linked to dependent Tasks.
- **No explicit propagation**: when Task X fails with a Finding, dependent Tasks Y, Z are not automatically flagged.
- Invalidation semantics unclear: a Change downstream of a failed upstream task proceeds as if upstream succeeded.

Without this, a Task failure can silently allow downstream work to execute against invalid state. Per AIOS A18 + AI-SDLC §19, this is architectural defect — not just inefficiency.

## Decision

**Two-mechanism propagation**: per-Finding inheritance + Execution-level invalidation.

### Mechanism 1: Finding inheritance

```sql
ALTER TABLE findings ADD COLUMN parent_finding_id INT FK REFERENCES findings(id) NULL;
ALTER TABLE findings ADD COLUMN propagation_depth INT NOT NULL DEFAULT 0;
  -- 0 = original Finding, 1 = inherited once, etc.
ALTER TABLE findings ADD COLUMN propagates_to_task_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
  -- list of Task IDs the propagation mechanism identified as affected
ALTER TABLE findings ADD COLUMN inheritance_kind TEXT NULL;
  -- ENUM-like: 'direct_dependency', 'data_flow', 'shared_state', 'test_coverage_gap'

CREATE INDEX ix_findings_parent ON findings(parent_finding_id) WHERE parent_finding_id IS NOT NULL;
```

### Mechanism 2: Execution invalidation

```sql
ALTER TABLE executions ADD COLUMN invalidated_by_finding_id INT FK REFERENCES findings(id) NULL;
ALTER TABLE executions ADD COLUMN invalidated_at TIMESTAMP NULL;
ALTER TABLE executions ADD COLUMN invalidation_reason TEXT NULL;
  -- free text; typically "upstream_finding:<finding_id>:<description>"
```

### Propagation trigger — `propagate_finding_on_rejection`

When an Execution commits a Finding (severity ≥ HIGH) during its REJECTED path:

1. Identify `affected_task_set = causal_descendants(origin_task_id)` via `task_dependencies` + `causal_edges WHERE relation_semantic IN ('depends_on', 'derives_from', 'consumes', 'uses_data_from')`.
2. For each `task_y ∈ affected_task_set`:
   - Create inherited Finding: `Finding(parent_finding_id=original.id, propagation_depth=original.depth+1, inheritance_kind='direct_dependency', target_task_id=task_y.id, severity=original.severity)`.
   - If Task_y has any `Execution` currently `status=IN_PROGRESS` or `COMMITTED`: mark it `invalidated_by_finding_id=original.id`, `invalidated_at=now()`, `invalidation_reason='upstream_finding:<id>:<summary>'`.
   - Task_y itself: `Task.status → BLOCKED_UPSTREAM_FAILURE` (new enum value added to Task.status).
3. Cascade: if inherited Finding has severity ≥ HIGH and further descendants exist, recurse with `max_depth=5` (ADR-004 calibration constant; prevents runaway cascades in dense DAGs).

### Resolution / un-invalidation

When the original Finding is resolved (Decision(type='finding_resolution') committed + Evidence provided):

1. All inherited Findings in this cascade are marked `resolved_by_cascade_resolution_id = original.resolution_decision_id`.
2. Each affected Task transitions `BLOCKED_UPSTREAM_FAILURE → READY` (or back to prior status if tracked).
3. Invalidated Executions: their `invalidated_by_finding_id` retained for audit; re-executions are new Execution rows referencing the resolved prior.

### Propagation validator (`ErrorPropagationCheck`)

Added to GateRegistry for `(Execution, IN_PROGRESS, COMMITTED)` chain:

```python
def error_propagation_check(execution):
    task = execution.task

    # Check if any upstream task has unresolved high-severity Finding
    upstream_findings = db.query(Finding).filter(
        Finding.task_id.in_(causal_ancestors(task.id)),
        Finding.severity >= 'HIGH',
        Finding.resolved_at.is_(None),
    ).count()

    if upstream_findings > 0:
        return Verdict(
            passed=False,
            rule_code='upstream_error_unresolved',
            reason=f'{upstream_findings} unresolved HIGH-severity Finding(s) upstream; '
                   f'Execution cannot commit until upstream resolved'
        )

    return Verdict.PASS
```

This prevents new Executions from committing when an upstream error hasn't been resolved.

## Rationale

1. **AIOS A18 + AI-SDLC §19 explicit requirements** — error propagation must be mechanical, not best-effort.
2. **Parallel to B.7 SourceConflictDetector** — conflicts in Knowledge propagate via BLOCKED status; errors in Tasks propagate via inherited Findings.
3. **Standard incident-response pattern** — identify blast radius, quarantine, resolve, un-quarantine; well-understood procedure adapted here.
4. **Depth cap prevents runaway cascades** — in pathological DAGs (e.g., one central Task with 500 descendants), unbounded propagation could block entire project; `max_depth=5` keeps blast radius bounded while requiring explicit Steward sign-off to expand.

## Alternatives considered

- **A. Forward impact only (current state)** — rejected: violates AIOS A18 explicitly.
- **B. Invalidate all transitively-reachable Executions unconditionally** — rejected: unbounded cascade; single upstream failure halts entire project.
- **C. Notify only, no auto-block** — rejected: relies on human vigilance; violates AI-SDLC §19 mandate.
- **D. Mechanism 2 only (Execution invalidation), no inherited Findings** — rejected: loses Finding-level audit trail; inherited Findings are the mechanism by which G.9 proof-trail audit detects propagated errors.

## Consequences

### Immediate

1. `findings` schema extensions (5 columns).
2. `executions.invalidated_by_finding_id` + related columns.
3. `Task.status` enum extended with `BLOCKED_UPSTREAM_FAILURE`.
4. `propagate_finding_on_rejection` hook in VerdictEngine REJECTED path.
5. `ErrorPropagationCheck` gate added to `(Execution, IN_PROGRESS, COMMITTED)` transition.
6. Stage G.11 ErrorPropagationMechanism added to PLAN_GOVERNANCE.

### Downstream

- Failure cascades become visible: G.3 metric `M_propagation_blast_radius` (avg number of affected Tasks per HIGH-severity Finding).
- G.9 proof-trail audit extended to check that every cascade is either resolved or explicitly accepted.
- Steward quarterly audit includes review of long-unresolved cascades (severity ≥ HIGH with resolution pending > 14 days).

### Risks

1. **False propagation** — propagation rule over-broad; legitimate downstream work blocked. Mitigation: `propagates_to_task_ids` list is inspectable; affected Task authors may challenge via `POST /findings/{id}/contest-propagation` → triggers Steward review.
2. **Cascade depth hit** — at `max_depth=5`, cascade stops; deeper dependents NOT flagged automatically. Mitigation: G.11 T3 test asserts behavior; Steward may manually extend via signed record.
3. **Resolution lag** — resolved upstream Findings have cascade-un-invalidation lag; mitigation: `resolved_by_cascade_resolution_id` indexed for fast un-cascade query at commit time.

### Reversibility

REVERSIBLE — gate disabled via feature flag `ERROR_PROPAGATION_ENFORCEMENT=off`; inherited Findings retained in DB for audit but not blocking new Executions. Schema stays (append-only).

## Evidence captured

- **[CONFIRMED: AIOS Axiom 18 text]** "Err(x) → Err(Dependent(x))".
- **[CONFIRMED: AI-SDLC §19 text]** "Err_i ≠ empty ⇒ Invalidate(DependentArtifacts(S_i))".
- **[CONFIRMED: Forge Complete §14 text]** Impact covers dependencies + usages + side effects.
- **[CONFIRMED: THEOREM_VERIFICATION_AIOS_AISDLC.md §5.1 G-SHARED-2]** gap explicitly identified.
- **[ASSUMED]** `max_depth=5` reasonable for typical Forge Task DAGs (<50 nodes/Objective); if DAGs grow deeper, recalibrate.
- **[UNKNOWN]** performance impact of cascade propagation on hot paths; requires benchmark.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — initial DRAFT + CLOSED via Tier 1 mass-accept; content DRAFT pending distinct-actor review.

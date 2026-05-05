# ADR-023 — Critical Path enforcement for Task scheduling

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** user (Tier 1 closure mass-accept) + AI agent (draft)
**Related:** AIOS A8 (LongestPath), AI-SDLC #10 (Plan CritPath), PLAN_QUALITY_ASSURANCE new Stage D.6, THEOREM_VERIFICATION_AIOS_AISDLC.md §5.1 G-SHARED-1.

## Context

Two theorems flag explicit Critical Path as required:

- **AIOS Axiom 8**: `CritPath = LongestPath(T_main)` — all scheduling must respect CritPath.
- **AI-SDLC §10 Planning Stage**: plan is valid only if `CriticalPathDefined`.

Current Forge state:
- `task_dependencies` table exists (ADR-001 era) + `causal_edges WHERE relation_semantic='depends_on'` (after ADR-017 ENUM backfill).
- Phase A-G ordering encodes coarse-grained precedence.
- **No mechanical LongestPath computation.** No scheduler gate enforcing CritPath respect. No metric tracking slippage from planned CritPath.

Without this, planning deadlines are informal. A delay in any task silently propagates without alarm; parallel tasks may starve critical-path tasks for resources.

## Decision

**Implement CPM (Critical Path Method) as mechanical planning discipline.**

### Schema extensions

```sql
ALTER TABLE tasks ADD COLUMN duration_estimate_hours NUMERIC(10, 2) NULL;
  -- NULL allowed for Tasks not yet estimated; CPM skips NULL-duration tasks.
ALTER TABLE tasks ADD COLUMN duration_actual_hours NUMERIC(10, 2) NULL;
  -- populated when Task.status transitions to DONE.

ALTER TABLE objectives ADD COLUMN critical_path_task_ids JSONB NULL;
  -- computed at Objective ACTIVATE time; re-computed on Task graph change.
  -- Structure: [{task_id: "abc", duration: 4.5, earliest_start: 0, earliest_finish: 4.5, latest_start: 0, latest_finish: 4.5, slack: 0.0}, ...]
ALTER TABLE objectives ADD COLUMN critical_path_computed_at TIMESTAMP NULL;
ALTER TABLE objectives ADD COLUMN critical_path_total_duration_hours NUMERIC(12, 2) NULL;
```

### Algorithm (standard CPM)

Implemented in `platform/scripts/compute_critical_path.py`:

1. Load Task graph filtered by `Objective.id`: nodes = Tasks, edges = `causal_edges WHERE relation_semantic='depends_on'`.
2. Topological sort; reject if cycle detected (should not occur given B.1 acyclicity, but defensive check).
3. Forward pass: compute `earliest_start` and `earliest_finish` per Task using Task.duration_estimate_hours.
4. Backward pass: compute `latest_start` and `latest_finish`.
5. Compute `slack = latest_start - earliest_start` per Task.
6. CritPath = Tasks where `slack = 0`.
7. Persist result to `Objective.critical_path_task_ids` + `critical_path_total_duration_hours`.
8. Deterministic: same graph + same durations → same CritPath.

### Scheduler gate (`CriticalPathGate`)

Added to GateRegistry for `(Execution, pending, IN_PROGRESS)` chain (runs after B.5 TimelyDeliveryGate):

```python
def critical_path_gate(execution):
    task = execution.task
    obj = task.objective

    # Skip if Objective doesn't have CritPath computed (e.g., very early Stage 0 tasks)
    if obj.critical_path_task_ids is None:
        return Verdict.PASS  # gate inactive until CritPath computed

    crit_task_ids = set(t['task_id'] for t in obj.critical_path_task_ids)

    # If this Task is on CritPath → allow unconditionally
    if task.id in crit_task_ids:
        return Verdict.PASS

    # If this Task is NOT on CritPath, check for starvation of CritPath tasks:
    # Is there any READY critical-path Task waiting for executor capacity?
    starved_critpath = db.query(Task).filter(
        Task.id.in_(crit_task_ids),
        Task.status == 'READY',
        Task.current_executor_id.is_(None),
    ).count()

    if starved_critpath > 0 and available_executor_capacity() == 0:
        return Verdict(
            passed=False,
            rule_code='critical_path_starvation',
            reason=f'{starved_critpath} critical-path Task(s) READY but starved; '
                   f'non-critical Task {task.id} cannot proceed'
        )

    return Verdict.PASS
```

Gate behavior:
- Critical tasks always proceed (gate returns PASS immediately).
- Non-critical tasks pause if critical tasks are READY but starved for executor capacity.
- If no starvation, non-critical tasks proceed normally.

### Metrics (G.3 extension)

Add two metrics to the 7 existing (M8 + M9):

- **M_critpath_slippage**: sum over completed Objectives of `(actual_total_duration - planned_critical_path_total_duration) / planned` — tracks how much Objectives exceed planned CritPath.
- **M_critpath_respect_rate**: fraction of Executions where CriticalPathGate returned PASS on first check (high value = scheduler respects CritPath).

Weekly Steward review dashboard surface these.

### CritPath re-computation triggers

CritPath computed + persisted:
1. At `Objective.status` transition `DRAFT → ACTIVE` (initial computation).
2. On any `Task` insert/delete within the Objective.
3. On any `task_dependencies` (causal_edge relation='depends_on') change.
4. On `Task.duration_estimate_hours` change.

Computation is idempotent (same input → same result), so triggers may over-compute but not corrupt.

### Duration estimation source

`Task.duration_estimate_hours` populated at Task creation:
- Default via historical-average lookup: `AVG(duration_actual_hours)` for Tasks with same `scope_tags` ± similar decomposition pattern.
- Override by Task author: explicit value.
- [UNKNOWN] if no historical data + no override → Task cannot participate in CritPath (excluded until estimated). Execution dispatch still allowed but CritPath incomplete. Dashboard flags incomplete-CritPath Objectives.

## Rationale

1. **AIOS A8 explicit requirement** — `CritPath = LongestPath(T_main)` must be defined mechanically.
2. **AI-SDLC §10 Planning Stage** — plan not valid without `CriticalPathDefined`.
3. **Standard CPM is well-understood** — not invention; PERT/CPM in use since 1950s for project scheduling.
4. **Non-invasive** — Tasks without `duration_estimate_hours` simply opt out of CritPath; existing Forge flow unaffected.
5. **Starvation prevention** — makespan reduction (AIOS A12 partial closure) emerges from CritPath respect.

## Alternatives considered

- **A. PERT with probability distributions** — rejected: requires duration_min/max/most_likely triple; over-specified for Forge's current scale (<100 Tasks/Objective typical); standard CPM sufficient.
- **B. Resource-constrained scheduling (RCPSP)** — rejected: NP-hard; heavy tooling (solver integration); overkill for current scope.
- **C. No enforcement, reporting only** — rejected: violates AIOS A8 "scheduling must respect CritPath"; reporting alone allows silent slippage.
- **D. Delegate to external scheduler (Jenkins, Airflow)** — rejected: couples Forge to orchestrator-of-orchestrator; CPM is simple enough to compute in-process.

## Consequences

### Immediate

1. `tasks.duration_estimate_hours` + `duration_actual_hours` columns added.
2. `objectives.critical_path_*` columns added.
3. `scripts/compute_critical_path.py` authored.
4. `CriticalPathGate` added to GateRegistry for Execution pending→IN_PROGRESS chain.
5. G.3 metrics extended with M_critpath_slippage + M_critpath_respect_rate.
6. Stage D.6 CriticalPathScheduler added to PLAN_QUALITY_ASSURANCE (see plan update).

### Downstream

- Every Objective activated post-deployment has CritPath computed.
- Steward dashboard includes per-Objective CritPath visualization.
- Phase A-G execution order respects CritPath when multiple Phase-ready Tasks compete.

### Risks

1. **Estimation drift** — historical-average estimates drift as Task patterns change; mitigation: M_critpath_slippage surfaces divergence.
2. **Under-estimated duration** — Task runs longer than estimated; downstream re-plan required; G.9 T7 bounded-revision test bounds this.
3. **CritPath thrashing** — small duration changes can alter CritPath; mitigation: only promote new CritPath if >10% duration change (stability heuristic; documented in script).

### Reversibility

REVERSIBLE — gate disabled via feature flag `CRITICAL_PATH_GATE_ENFORCEMENT=off` (reverts to no-op scheduling); columns can stay without enforcement; compute script can be paused.

## Evidence captured

- **[CONFIRMED: AIOS Axiom 8 text]** "CritPath = LongestPath(T_main). All scheduling must respect CritPath."
- **[CONFIRMED: AI-SDLC §10 text]** "ValidPlan iff ... CriticalPathDefined ..."
- **[CONFIRMED: THEOREM_VERIFICATION_AIOS_AISDLC.md §5.1 G-SHARED-1]** gap explicitly identified.
- **[ASSUMED]** historical Task duration data availability — requires 3 months production before per-Objective estimates accurate.
- **[UNKNOWN]** edge case: very-fast Tasks (< 1 hour) may produce unstable CritPath; verify in Phase D.6 exit test.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — initial DRAFT + CLOSED via Tier 1 mass-accept; content DRAFT pending distinct-actor review.

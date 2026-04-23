# PLAN: Memory & Context — Causal DAG + Context Projection

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** PLAN_GATE_ENGINE complete (G_A = PASS).
**Must complete before:** PLAN_QUALITY_ASSURANCE (D.2 property tests need G_{B.1}; C.3 ImpactClosure needs G_{B.2}), PLAN_CONTRACT_DISCIPLINE (E.1 ContractSchema needs ContextProjector at G_{B.4}).
**ROADMAP phases:** B.1 → B.4.
**Source spec:** FORMAL_PROPERTIES_v2.md P14, P15, partial P4.
**Soundness theorem source:** `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md`.

---

## Soundness conditions addressed

| Theorem condition | What "addressed" means | Closed in |
|---|---|---|
| **1** — RequiredInfo(i) ⊆ C_i | ContextProjector delivers the minimal justification frontier to the agent — C_i is now formally computed, not session-dependent | Stage B.4 exit |
| **3** — O_i derived from C_i, R_i, E_<i | B.1 establishes the DAG structure (necessary condition only — ancestor edge exists); condition 3 proper — the agent's output is actually *derived from* E_<i at generation time — is only closed at B.4 when ContextProjector delivers E_<i into C_i. B.1 alone guarantees only presence of ancestor edges, not derivation. | Stage B.4 exit (B.1 is a prerequisite, not a closure point) |

Conditions 2 (Suff), 4 (A_i propagated), 5 (deterministic T_i), 6 (gate), 7 (Missing→Stop) are NOT closed by this plan. They depend on PLAN_GATE_ENGINE (5, 6) and PLAN_CONTRACT_DISCIPLINE (2, 4, 7).

---

## Theorem variable bindings

```
C_i = {codebase after previous stage} ∪ {CausalEdge projection for current task}
R_i = FORMAL_PROPERTIES_v2 P14 (causal DAG), P15 (projection)
A_i = listed explicitly per stage
T_i = pytest / property-test (hypothesis) / grep — no LLM-in-loop
O_i = {CausalEdge table, CausalGraph service, ContextProjector, context_projections table}
G_i = all T_i pass AND existing tests green AND distinct-actor spot-check where noted
```

**Condition 1 — how it is closed:** Before B.4, `C_i` was defined by session priors (what the agent happened to have in context). After B.4, `C_i = ContextProjector.project(task, budget_tokens)` — a deterministic BFS over the causal DAG filtered by `scope_tags ∪ requirement_refs`. RequiredInfo(i) is now formally bounded.

**Residual gap (disclosed):** ContextProjector can only project what is *in* the DAG. Implicit invariants and tribal knowledge not captured as CausalEdge entries remain outside C_i. This gap is tracked in AUTONOMOUS_AGENT_FAILURE_MODES.md §2.4 and is not closed by this plan.

---

## Stage B.1 — CausalEdge table + acyclicity trigger

**Closes:** P14 structural foundation — history becomes a DAG with enforced acyclicity.

**Entry conditions:**
- G_A = PASS (Phase A exit gate, all 5 stages).

**A_{B.1}:**
- `src.created_at < dst.created_at` acyclicity trigger — [ASSUMED: this is the chosen mechanism per FORMAL_PROPERTIES_v2 P14 binding]. [UNKNOWN: clock-skew tolerance value — must be set by ADR-004. ADR-004 is not yet authored on disk as of 2026-04-23 (platform/docs/decisions/ contains only ADR-001..003). B.1 is BLOCKED until ADR-004 file exists with `Status: CLOSED` — see Q1.]
- Unique constraint scope: `(src_type, src_id, dst_type, dst_id, relation)` — [ASSUMED: adding `created_at` to unique key would make idempotent re-insert impossible; leave it out per standard pattern. If wrong → duplicate edges on re-run of backfill]. Mitigation: B.2 tests idempotency explicitly.

**Work:**
1. Alembic migration: `causal_edges(id, src_type, src_id, dst_type, dst_id, relation, created_at)`.
2. Unique constraint: `(src_type, src_id, dst_type, dst_id, relation)`.
3. DB trigger or app-level check: reject insert where `src.created_at >= dst.created_at` (acyclicity via clock).
4. App-level insert gate: `Decision | Change | Finding` insert requires ≥ 1 CausalEdge to an ancestor OR `is_objective_root = true` (adds nullable-defaulting `is_objective_root` boolean column to the three entities in this B.1 migration). Root exception must be explicit at insert time — no silent bypass.

**Exit test T_{B.1} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
# exits 0

# T2: unique constraint idempotency
pytest tests/test_causal_edge_unique.py -x
# PASS: inserting same (src_type, src_id, dst_type, dst_id, relation) twice → second raises IntegrityError

# T3: acyclicity — property test
pytest tests/property/test_causal_acyclicity.py -x --hypothesis-seed=0
# PASS: 10,000 random edge inserts never produce a cycle (hypothesis)

# T4: insert gate
pytest tests/test_causal_insert_gate.py -x
# PASS: Decision insert with no ancestor edge → rejected (root exception: Objective root documented)

# T5: regression
pytest tests/ -x
# all existing + Gate Engine tests green
```

**Gate G_{B.1}:** T1–T5 pass → PASS.

---

## Stage B.2 — Idempotent backfill of existing FKs

**Closes:** P14 — existing causal relations in schema become edges in the DAG.

**Entry conditions:**
- G_{B.1} = PASS.

**A_{B.2}:**
- 10 known FK-based causal relations per GAP_ANALYSIS_v2 §P14 (after ADR-002 corrections) PLUS the `task_dependencies` table (required for PLAN_QUALITY_ASSURANCE C.3 walk):
  `Task.origin_finding_id`, `AcceptanceCriterion.source_ref`, `AcceptanceCriterion.source_llm_call_id`, `Finding.source_llm_call_id`, `Finding.execution_id`, `Decision.execution_id`, `Decision.task_id`, `Change.execution_id`, `Change.task_id`, `Knowledge.source_ref`, `task_dependencies.(src_task_id, dst_task_id, relation)` — [CONFIRMED via GAP_ANALYSIS_v2 §P14; `task_dependencies` added per cross-plan dependency with C.3].
- `Finding.source_execution_id` was a hallucinated column (GAP_ANALYSIS_v2 §0 correction 2) — [CONFIRMED: use `Finding.execution_id`].
- `Decision.blocked_by_decisions` does not exist in DB (GAP_ANALYSIS_v2 §0 correction 1) — [CONFIRMED: omit from backfill].
- Relation type assignment (e.g. `Task.origin_finding_id` → relation='produced_by') — [ASSUMED: mapping in backfill script; distinct-actor spot-check required per T3].

**Work:**
1. `scripts/backfill_causal_edges.py` — reads each of 10 FK relations, inserts CausalEdge rows. Idempotent: uses `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING`.
2. Script takes `--dry-run` flag for pre-production review.

**Exit test T_{B.2} (deterministic):**
```bash
# T1: idempotency
python scripts/backfill_causal_edges.py && python scripts/backfill_causal_edges.py
# row count identical after second run (no duplicates)

# T2: FK coverage (10 FK relations + task_dependencies)
pytest tests/test_backfill_coverage.py -x
# PASS: for each of 10 FK relations + task_dependencies, at least one edge exists in causal_edges after backfill

# T2b: task_dependencies specifically backfilled (required by PLAN_QUALITY_ASSURANCE C.3)
pytest tests/test_backfill_task_dependencies.py -x
# PASS: every task_dependencies row has a corresponding causal_edges row with relation='depends_on'

# T3: relation-type spot-check [MANUAL, SLA: 5 working days from B.2 code-complete]
# distinct actor reviews 20 random edges: verify relation type matches semantic intent
# Record: docs/reviews/review-backfill-edges-by-<actor>-<date>.md
# Escalation: if SLA exceeded, B.2 auto-reverts to BLOCKED; Steward must name fallback reviewer.

# T4: regression
pytest tests/ -x
# all tests green
```

**Gate G_{B.2}:** T1–T2b automated + T4 green + T3 distinct-actor review record filed (within SLA) → PASS.

---

## Stage B.3 — CausalGraph service

**Closes:** P14 operational — graph queries available as pure Python service.

**Entry conditions:**
- G_{B.2} = PASS.

**A_{B.3}:**
- BFS depth limit for `ancestors()` — [UNKNOWN: not specified in FORMAL_PROPERTIES_v2 or ADR-004. See Q3 in open questions table. B.3 is BLOCKED until platform owner names a value via a recorded Decision (format: `[ASSUMED: accepted-by=<role>, date=YYYY-MM-DD]` per CONTRACT §B.2). Default=10 is a strawman, not a resolution.]
- `minimal_justification()` definition: shortest path vs minimum weight? — [ASSUMED: shortest path (hop count) for simplicity; minimum weight requires P10 risk weights which are Phase D. Acceptable assumption — document].

**Work:**
1. `app/evidence/causal_graph.py`:
   - `ancestors(node, depth=10, relation_filter=None) → List[CausalEdge]` — BFS over `causal_edges` table.
   - `minimal_justification(node) → List[CausalEdge]` — shortest path to root.
   - Pure Python: no side effects, no writes, no external calls.

**Exit test T_{B.3} (deterministic):**
```bash
# T1: ancestors correctness
pytest tests/test_causal_graph.py::test_ancestors -x
# PASS: known fixture graph — ancestors(node_D) returns {A, B, C} for known DAG A→B→C→D

# T2: minimal_justification
pytest tests/test_causal_graph.py::test_minimal_justification -x
# PASS: minimal_justification(node_D) returns shortest path [A→B→C→D] not longer detour

# T3: purity check
grep -n "session\|db\.\|commit\|add(" app/evidence/causal_graph.py
# exits 1 (no matches — pure reads only)

# T4: regression
pytest tests/ -x
# all tests green
```

**Gate G_{B.3}:** T1–T4 pass → PASS.

---

## Stage B.4 — ContextProjector + prompt assembly integration

**Closes:** P15 (context projection) — **condition 1 of soundness theorem fully closed here**.

**Entry conditions:**
- G_{B.3} = PASS.

**A_{B.4}:**
- Budget unit: tokens or characters? — [ASSUMED: tokens, matching LLM context window accounting. If wrong → projection may over- or under-fill context]. Mitigation: T1 tests with 10 canonical fixtures to catch systematic over/under-fill.
- Priority order for pruning under budget: [ASSUMED: must-guidelines → recent decisions → evidence → knowledge, per FORMAL_PROPERTIES_v2 P15 binding. Document in code].
- `scope_tags ∪ requirement_refs` filter source — [UNKNOWN: must grep-verify `task.scope_tags` and `task.requirement_refs` field existence in current schema before B.4 starts. See Q2. B.4 is BLOCKED on Q2 resolution.]

**Work:**
1. `app/evidence/context_projector.py`:
   - `project(task, budget_tokens) → ContextProjection` — BFS over CausalGraph, filtered by `scope_tags ∪ requirement_refs`, pruned by priority order.
   - Deterministic: same task + same budget + same DAG state → same projection.
2. `context_projections` table migration: stores projection per Execution for audit.
3. `app/prompt_parser.py` integration: use `ContextProjector.project()` when `CAUSAL_PROJECTION=on` flag set.
4. Default: `CAUSAL_PROJECTION=off` — behind flag until B.4 exit gate passed.

**Exit test T_{B.4} (deterministic):**
```bash
# T1: budget compliance — 10 canonical fixtures
pytest tests/test_context_projector.py::test_budget_compliance -x
# PASS: projection token count ≤ budget_tokens for all 10 fixtures

# T2: fidelity — 10 historical executions
pytest tests/test_context_projector.py::test_fidelity -x
# PASS: for each historical execution, projection contains every Decision the agent's
# reasoning referenced (spot-check via parsing stored reasoning text)

# T3: determinism
pytest tests/test_context_projector.py::test_determinism -x
# PASS: same (task_id, budget) called 3 times → identical projection output

# T4: context_projections audit trail
pytest tests/test_context_projector.py::test_audit_persistence -x
# PASS: each project() call persists a row in context_projections

# T5: flag off = no behavior change
pytest tests/ -x  # with CAUSAL_PROJECTION=off (default)
# all existing tests green — flag off means projector not invoked

# T6: flag on smoke
pytest tests/test_context_projector_integration.py -x  # with CAUSAL_PROJECTION=on
# PASS: prompt assembly uses projection, not raw session context
```

**Gate G_{B.4}:** T1–T6 pass → PASS.
**Condition 1 achieved:** C_i is now formally `ContextProjector.project(task, budget_tokens)` — RequiredInfo(i) is bounded by the DAG projection, not session priors. [ASSUMED: projection fidelity T2 uses spot-check on 10 historical executions; systematic coverage gap for novel task types remains — disclosed per AUTONOMOUS_AGENT_FAILURE_MODES.md §2.2].

---

## Phase B exit gate (G_B)

```
G_B = PASS iff:
  G_{B.1} = PASS  (CausalEdge table, acyclicity, insert gate)
  AND G_{B.2} = PASS  (backfill idempotent, FK coverage, distinct-actor spot-check)
  AND G_{B.3} = PASS  (CausalGraph service pure + correct)
  AND G_{B.4} = PASS  (ContextProjector live behind flag, fidelity + determinism confirmed)
  AND pytest tests/ -x → all existing + Gate Engine + Memory tests green
  AND every new Decision|Change|Finding has ≥ 1 CausalEdge OR is flagged as an objective-root (e.g. Decision.is_objective_root = true) — DB invariant query:
      SELECT count(*) FROM (decisions UNION changes UNION findings) d
        LEFT JOIN causal_edges e ON e.dst_id = d.id
        WHERE e.id IS NULL AND COALESCE(d.is_objective_root, false) = false
      → 0 (root exception documented in B.1 Work item 4 requires is_objective_root column added in B.1 migration)
```

**Soundness conditions closed at G_B:**
- **Condition 1** — RequiredInfo(i) ⊆ C_i: ContextProjector delivers formally computed C_i. [T_{B.4} T2, T3]
- **Condition 3 (full)** — O_i derived from E_<i: CausalEdge enforces ancestry; ContextProjector delivers that ancestry to the agent. [T_{B.1} T4, T_{B.4} T6]

**Residual gap (disclosed):** projection fidelity tested on 10 historical executions (spot-check). Novel task types not covered by fidelity test. Full coverage requires Phase E ContractSchema (typed `Task.produces` → typed `RequiredInfo`).

---

## Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks |
|---|---|---|
| Q1 | ADR-004 clock-skew tolerance value — read from ADR-004 before implementing acyclicity trigger | Stage B.1 |
| Q2 | Do `task.scope_tags` and `task.requirement_refs` fields exist in current schema? Grep `app/models/task.py` before implementing projector filter | Stage B.4 |
| Q3 | BFS depth limit default — decide before implementing `ancestors()`; currently [ASSUMED: 10] | Stage B.3 |

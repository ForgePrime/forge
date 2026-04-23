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

| Theorem condition | Source theorem | What "addressed" means | Closed in |
|---|---|---|---|
| **1** — RequiredInfo(i) ⊆ C_i | CCEGAP | ContextProjector delivers the minimal justification frontier to the agent — C_i is now formally computed, not session-dependent | Stage B.4 exit |
| **3** — O_i derived from C_i, R_i, E_<i | CCEGAP | B.1 establishes the DAG structure (necessary condition only — ancestor edge exists); condition 3 proper — the agent's output is actually *derived from* E_<i at generation time — is only closed at B.4 when ContextProjector delivers E_<i into C_i. B.1 alone guarantees only presence of ancestor edges, not derivation. | Stage B.4 exit (B.1 is a prerequisite, not a closure point) |
| **C3** — Timely delivery | ECITP | All required info materialized in P_i BEFORE F_i executes; no post-hoc compensation. Enforced at Execution state transition (pending → IN_PROGRESS). | Stage B.5 exit (WARN); auto-promotes to REJECT at G_{E.1} |
| **C6** — Topology preservation | ECITP | Semantic dependency relations (requirement ↔ risk ↔ AC ↔ test) survive transfer via `causal_edges.relation_semantic` ENUM; CausalGraph exposes relation-typed queries. | Stage B.6 exit (WARN); promotes to REJECT at G.9 |

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

## Stage B.5 — TimelyDeliveryGate

**Closes:** ECITP C3 (Timely delivery — all required info present in P_i BEFORE F_i executes). Source: `.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` §3 C3.

**Rationale (ESC-3 root-cause uniqueness):** ECITP C3 requires that "all information required by stage i is delivered before F_i is executed — no stage may compensate after the fact." Three candidate enforcement points were considered:
1. Inline check in `prompt_parser.py` before LLM call — **rejected**: too late; Execution has already transitioned to IN_PROGRESS, so gate-failure would require rollback, contradicting F.4 no-auto-fill and violating ECITP Lemma 4 (broken continuity amplifies revision cost).
2. Gate at `Execution.status` transition (pending → IN_PROGRESS) — **chosen**: atomic with state machine; failure prevents transition, preserving invariant "IN_PROGRESS implies materialized P_i"; consistent with F.4 BLOCKED pattern.
3. Both 1 + 2 — **rejected**: duplicated enforcement, higher maintenance cost, no additional guarantee because (2) subsumes (1).

**Entry conditions:**
- G_{B.4} = PASS (ContextProjector exists and produces `ContextProjection` rows).
- G_{E.1} = PASS for full enforcement (ContractSchema.required_context(task) needed to define what counts as "required"). **Phased rollout:** B.5 may start in WARN mode before E.1; promotes to REJECT at G_{E.1} = PASS.

**A_{B.5}:**
- Required-context schema source: `ContractSchema.required_context(task) → Set[FieldRef]` per task type — [UNKNOWN: schema not yet defined; depends on E.1 ContractSchema. B.5 enforcement is WARN-only until G_{E.1} = PASS, then promotes to REJECT]. Mitigation: seed minimum required_context = `{scope_tags, requirement_refs, ancestor_findings}` for all task types until ContractSchema arrives.

**Work:**
1. `app/validation/timely_delivery_gate.py`:
   - `TimelyDeliveryGate.check(execution) → Verdict` — returns PASS iff `execution.context_projection_id IS NOT NULL` AND for every `FieldRef f ∈ ContractSchema.required_context(execution.task)`: `f ∈ execution.context_projection.structured_fields`.
2. Alembic migration: `executions.context_projection_id UUID FK NOT NULL constraint deferred` (SET NULL allowed in pending state; enforced at IN_PROGRESS transition).
3. GateRegistry entry: `(Execution, pending, IN_PROGRESS) → [TimelyDeliveryGate]`.
4. Phase toggle: env var `TIMELY_DELIVERY_MODE ∈ {WARN, REJECT}`; default WARN; switches to REJECT when G_{E.1} = PASS is recorded in `feature_flags` table.

**Exit test T_{B.5} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: transition blocked without projection (REJECT mode)
pytest tests/test_timely_delivery_gate.py::test_no_projection_blocks -x
# PASS: Execution.status=pending, context_projection_id=NULL, transition to IN_PROGRESS → blocked

# T3: transition blocked when projection missing required field (REJECT mode)
pytest tests/test_timely_delivery_gate.py::test_missing_field_blocks -x
# PASS: projection lacking 'requirement_refs' when task.requirement_refs non-empty → blocked

# T4: WARN mode emits Finding but allows transition
pytest tests/test_timely_delivery_gate.py::test_warn_mode_emits_finding -x
# PASS: WARN mode → Finding inserted, Execution.status advances to IN_PROGRESS

# T5: no NL-only fallback in prompt_parser
grep -nE "session_context|raw_prompt_fallback|fallback.*projection" app/prompt_parser.py
# exits 1 (no matches — fallback path explicitly removed)

# T6: regression
pytest tests/ -x
```

**Gate G_{B.5}:** T1–T6 pass → PASS. **ECITP C3 closed** in WARN mode at G_{B.5}; auto-promotes to REJECT at G_{E.1}.

**ESC-4 impact completeness:** touches `executions` table (new NOT NULL FK), `prompt_parser.py` (removes fallback), `GateRegistry`, `ContextProjector` (no changes — consumer-side), and adds dependency from Phase F.10 (StructuredTransferGate reuses same `required_context` schema). **ESC-5 invariants preserved:** F.4 BLOCKED semantic unchanged; B.4 ContextProjector interface unchanged (additive). **ESC-7 failure modes:** (a) novel task type with empty `required_context` → defaults to minimum seed; (b) race between projection compute and transition → FK NOT NULL constraint serializes; (c) WARN→REJECT promotion before ContractSchema ready → env-flag gated on G_{E.1} recorded state.

---

## Stage B.6 — SemanticRelationTypes on CausalEdge

**Closes:** ECITP C6 (topology preservation — requirement/risk/AC/test dependency relations survive transfer). Source: `.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` §3 C6.

**Rationale (ESC-3 root-cause uniqueness):** ECITP C6 requires that semantic dependency relations survive decomposition. Current `causal_edges.relation TEXT` field is free-form; two candidate schemas were considered:
1. Separate relation-type table `causal_relation_types(id, code, semantic_class)` — **rejected**: adds join overhead to every CausalGraph traversal; breaks simple `relation='depends_on'` backward compatibility; requires re-tagging all B.2 backfilled rows.
2. `causal_edges.relation_semantic ENUM` column alongside existing `relation TEXT` — **chosen**: backward compatible (existing TEXT preserved); deterministic mapping script; ENUM constraint at DB level enforces completeness.
3. Polymorphic relation via JSONB metadata — **rejected**: not queryable with indexed lookups; violates ESC-1 determinism (JSONB ordering is not guaranteed across PG versions).

**Entry conditions:**
- G_{B.2} = PASS (backfilled edges exist in DB).

**A_{B.6}:**
- ENUM values — [ASSUMED: `{requirement_of, risk_of, ac_of, test_of, mitigates, derives_from, produces, blocks, verifies}` per FORMAL_PROPERTIES_v2 P14 binding + ECITP C6 semantic classes. Missing values → Finding, not silent fallback].
- Backfill mapping: `relation TEXT → relation_semantic ENUM` per deterministic script — [UNKNOWN: canonical mapping table must be authored before this stage; Q4 blocks B.6].

**Work:**
1. Alembic migration: add `causal_edges.relation_semantic ENUM(...) NULL` (NOT NULL defered); index on `(dst_type, dst_id, relation_semantic)`.
2. `scripts/backfill_relation_semantic.py` — deterministic map from `relation TEXT` values to ENUM; unmappable → `NULL` + Finding.
3. `app/evidence/causal_graph.py` extension:
   - `requirements_of(ac) → List[CausalEdge]` — edges WHERE `dst_id = ac.id AND relation_semantic = 'requirement_of'`.
   - `risks_of(ac) → List[CausalEdge]` — same pattern, `relation_semantic = 'risk_of'`.
   - `tests_of(ac) → List[CausalEdge]` — same pattern, `relation_semantic = 'test_of'`.
4. Validator (WARN phase; promotes to REJECT at G.9): `AcceptanceCriterion insert` → emit Finding if `requirements_of(ac)` empty AND `risks_of(ac)` empty.

**Exit test T_{B.6} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: backfill deterministic (ESC-1)
python scripts/backfill_relation_semantic.py && python scripts/backfill_relation_semantic.py
# row count identical; no duplicate mappings

# T3: unmappable edges reported as Findings
pytest tests/test_relation_semantic_backfill.py::test_unmappable_finding -x
# PASS: TEXT relation with no ENUM mapping → Finding emitted, relation_semantic=NULL

# T4: CausalGraph query methods
pytest tests/test_causal_graph_semantic.py -x
# PASS: requirements_of/risks_of/tests_of return expected edges on fixture DAG

# T5: AC validator emits Finding when requirement AND risk both absent (WARN mode)
pytest tests/test_ac_topology_warn.py -x
# PASS: AC insert with no 'requirement_of' and no 'risk_of' edge → Finding inserted

# T6: regression
pytest tests/ -x
```

**Gate G_{B.6}:** T1–T6 pass → PASS. **ECITP C6 closed (WARN mode)**; REJECT promotion handled at G.9 ProofTrailCompleteness.

**ESC-4 impact:** `causal_edges` schema (+1 column, +1 index); `CausalGraph` (+3 methods — additive); `AcceptanceCriterion` validator (WARN phase). **ESC-5 invariants preserved:** B.1 unique constraint on (src_type, src_id, dst_type, dst_id, relation) unchanged (relation_semantic is additional, not part of uniqueness). **ESC-7 failure modes:** (a) unmappable historical TEXT → Finding not silent NULL default; (b) new relation class introduced → ENUM type check raises at insert; (c) partial backfill coverage → T3 catches.

---

## Phase B exit gate (G_B)

```
G_B = PASS iff:
  G_{B.1} = PASS  (CausalEdge table, acyclicity, insert gate)
  AND G_{B.2} = PASS  (backfill idempotent, FK coverage, distinct-actor spot-check)
  AND G_{B.3} = PASS  (CausalGraph service pure + correct)
  AND G_{B.4} = PASS  (ContextProjector live behind flag, fidelity + determinism confirmed)
  AND G_{B.5} = PASS  (TimelyDeliveryGate — ECITP C3 closed in WARN, auto-promotes to REJECT at G_{E.1})
  AND G_{B.6} = PASS  (SemanticRelationTypes — ECITP C6 closed in WARN, promotes at G.9)
  AND pytest tests/ -x → all existing + Gate Engine + Memory tests green
  AND every new Decision|Change|Finding has ≥ 1 CausalEdge OR is flagged as an objective-root (e.g. Decision.is_objective_root = true) — DB invariant query:
      SELECT count(*) FROM (decisions UNION changes UNION findings) d
        LEFT JOIN causal_edges e ON e.dst_id = d.id
        WHERE e.id IS NULL AND COALESCE(d.is_objective_root, false) = false
      → 0 (root exception documented in B.1 Work item 4 requires is_objective_root column added in B.1 migration)
```

**Soundness conditions closed at G_B:**
- **CCEGAP Condition 1** — RequiredInfo(i) ⊆ C_i: ContextProjector delivers formally computed C_i. [T_{B.4} T2, T3]
- **CCEGAP Condition 3 (full)** — O_i derived from E_<i: CausalEdge enforces ancestry; ContextProjector delivers that ancestry to the agent. [T_{B.1} T4, T_{B.4} T6]
- **ECITP C3 (WARN→REJECT)** — timely delivery enforced at Execution state transition; no F_i runs without P_i materialized. [T_{B.5} T2, T3, T5]
- **ECITP C6 (WARN; REJECT at G.9)** — semantic relation topology (requirement/risk/AC/test) survives transfer via relation_semantic ENUM. [T_{B.6} T4, T5]

**Residual gap (disclosed):** projection fidelity tested on 10 historical executions (spot-check). Novel task types not covered by fidelity test. Full coverage requires Phase E ContractSchema (typed `Task.produces` → typed `RequiredInfo`).

---

## Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | B.1 insert gate rejects Decision/Change/Finding without ancestor edge (unless `is_objective_root=true`); B.4 ContextProjector with empty DAG produces empty `ContextProjection` → B.5 TimelyDeliveryGate blocks pending→IN_PROGRESS transition; B.6 AC validator emits Finding when requirement+risk edges both empty. |
| 2 | timeout_or_dependency_failure | Handled | B.3 CausalGraph is pure Python over DB; BFS bounded by `max_depth` (Q3); slow projection → Execution stays in `pending`, TimelyDeliveryGate (B.5) prevents LLM call. No external network dependency. |
| 3 | repeated_execution | Handled | B.2 backfill idempotent (T1 explicit — INSERT ... ON CONFLICT DO NOTHING); B.4 ContextProjector deterministic (T3: same task+budget+DAG → identical projection byte-for-byte); B.6 backfill script idempotent on re-run (T2). |
| 4 | missing_permissions | JustifiedNotApplicable | CausalGraph queries are DB reads scoped by `project_id` via application-layer auth already enforced upstream. CausalEdge table has no user-level permission model; cross-project isolation at query layer. If cross-project CausalEdge exposure becomes concern → new ADR. |
| 5 | migration_or_old_data_shape | Handled | Every B-stage with schema change has alembic upgrade→downgrade→upgrade round-trip (B.1 T1, B.4 T4-audit, B.5 T1, B.6 T1). B.1 `is_objective_root` column added with `DEFAULT false` to backward-fill existing rows; B.6 `relation_semantic` NULL-allowed with Finding on unmappable TEXT. |
| 6 | frontend_not_updated | JustifiedNotApplicable | Memory/Context is backend-internal: CausalEdge table, CausalGraph service, ContextProjector, gates. No UI surface in Phase B. If future stage exposes projection-view UI → revisit. |
| 7 | rollback_or_restore | Handled | B.4 `CAUSAL_PROJECTION=off` env flag disables projector without migration rollback (feature-flag rollback). B.5 `TIMELY_DELIVERY_MODE=WARN` reverts REJECT mode. B.6 feature flag promotion WARN→REJECT reversible by flipping flag. All alembic migrations have `down_revision`. |
| 8 | monday_morning_user_state | Handled | ContextProjector is stateless per call — no overnight accumulation. `context_projections` table stores audit trail but is read-only; Monday-morning invocation produces identical projection given identical DAG. B.5 `executions.context_projection_id` NOT NULL constraint at IN_PROGRESS transition survives process restart. |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Memory/Context operates on CausalEdge DAG (Decision/Change/Finding entities); no geographic or regional data in scope. |

---

## Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks |
|---|---|---|
| Q1 | ADR-004 clock-skew tolerance value — read from ADR-004 before implementing acyclicity trigger | Stage B.1 |
| Q2 | Do `task.scope_tags` and `task.requirement_refs` fields exist in current schema? Grep `app/models/task.py` before implementing projector filter | Stage B.4 |
| Q3 | BFS depth limit default — decide before implementing `ancestors()`; currently [UNKNOWN: strawman=10] | Stage B.3 |
| Q4 | Canonical mapping table `relation TEXT → relation_semantic ENUM` — must be authored as part of ADR-017 (proposed, per ROADMAP §12) before B.6 backfill runs | Stage B.6 |
| Q5 | Seed list for `ContractSchema.required_context(task)` per task type when E.1 not yet complete — minimum viable set to unblock B.5 WARN mode | Stage B.5 |

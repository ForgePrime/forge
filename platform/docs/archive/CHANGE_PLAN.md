# Forge Platform — Change Plan

**Date:** 2026-04-22
**Source of truth:** [`FORMAL_PROPERTIES.md`](FORMAL_PROPERTIES.md).
**Gap input:** [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md).
**Scope:** `platform/` only. No changes outside `platform/` are in this plan.

The plan closes gaps in an order that respects dependencies: structural foundations first (they unblock everything), functional completeness next (evidence, rollback, projection), quality next (failure-oriented testing), diagonalization last (structural refactor on a now-stable substrate).

---

## 0. Principles this plan respects

| Principle | How it shapes the plan |
|---|---|
| **Idempotent** | Every migration, every backfill, every seed is safe to run twice. Re-running the plan produces the same end state. |
| **Continuous / differentiable** | Each phase is sized to bound blast radius; impact is estimated before each PR; mid-phase kill-switches (feature flags) exist. |
| **Reversible** | Every phase has a named downgrade path (flag off, migration down, tag revert). No step is IRREVERSIBLE. |
| **Diagonal** | Phases do not cross modes mid-stream. Phase A touches gates, Phase B touches memory, etc. Cross-mode changes live in their own phase (E). |
| **Self-adjoint** | Acceptance signal for each phase is defined in the same vocabulary as the property itself — we don't test A against B's model. |
| **Surjective over goals** | Every `CRITICAL`/`HIGH` gap from `GAP_ANALYSIS.md` is addressed by at least one phase. Nothing is deferred silently. |
| **Causal trace** | Each phase writes to the causal memory structure it builds — the plan is its own first user. |

---

## 1. Phase overview

| Phase | Goal | Closes | Duration (est.) | Blast radius | Depends on |
|---|---|---|---|---|---|
| **A** | Deterministic gate fundament | 4.2, 5.1, 5.2, 3.1 | 2–3 sprints | Wide (30+ sites) but shadowed | — |
| **B** | Causal memory + context projection | 5.5, 5.6, 3.4 (partial) | 3 sprints | DB migration + prompt path | A |
| **C** | Reversibility + impact pre-estimate | 3.5, 3.3, 3.2 | 2 sprints | `Change` model + pre-execution hook | A |
| **D** | Failure-oriented testing + coverage | 4.3, 4.4 | 2–3 sprints | Test infrastructure only | A, B |
| **E** | Continuous autonomy + diagonalization | 3.4 (full), 5.3, 5.4, 4.1 | 3 sprints | Refactor + new ledger | A, B, C, D |

Phases A, B, C can overlap in calendar time but all depend on A's exit gate for irreversible commits. Phase D depends on A+B because it writes its property tests against them. Phase E is last.

---

## 2. Phase A — Deterministic gate fundament

### 2.1 Goal

Every state transition passes through one gate. Every verdict is a function of inputs. Every mutating MCP call is idempotent. This phase is the leverage point — three CRITICAL gaps close together.

### 2.2 Scope

1. **`EvidenceSet` entity**
   - New table `evidence_sets(id, artifact_type, artifact_id, kind, provenance, checksum, rule_ref, sufficient_for_json, created_at)`.
   - Migration with down path.
   - Wrappers in existing writers (`contract_validator`, `plan_gate`, `execute.py`) that emit `EvidenceSet` rows as a side effect — no behavior change yet, only data capture.

2. **`GateRegistry`**
   - Static registry: `(entity, from_state, to_state) → [rule_ref]` for `Execution` (8 transitions), `Task` (5), `Decision` (6), `Finding` (triage), `KeyResult` (3).
   - Pure Python module; no DB component in phase A.

3. **`VerdictEngine`**
   - Single entry `evaluate(artifact, evidence_set, rules) → Verdict{verdict, failed_rules, missing_evidence, risk}`.
   - Single entry `commit(entity, target_state, verdict)` — performs the state write.
   - `plan_gate.validate_plan_requirement_refs` and `contract_validator` checks registered as rules.
   - Deterministic: no wall-clock, no network, no global mutable state.

4. **Shadow mode**
   - Feature flag `VERDICT_ENGINE_MODE ∈ {off, shadow, enforce}`. In `shadow`, engine computes its verdict in parallel with existing code and logs divergences to a `VerdictDivergence` table. No state change routed through engine yet.
   - Run shadow for one week on real traffic. Close divergences to zero.

5. **Enforcement cutover**
   - Flip to `enforce`. Direct `.status = "..."` assignments wrapped with a call to `VerdictEngine.commit()`.
   - Pre-commit hook in repo that rejects any new direct `\.status\s*=\s*['\"]` outside `VerdictEngine`.

6. **MCP idempotency**
   - New table `idempotent_calls(tool, key, args_hash, result_ref, expires_at)`.
   - Middleware in `mcp_server/server.py` that short-circuits duplicate calls within TTL (default 60 s).
   - Clients (including Claude Code) pass `idempotency_key` on every mutating call.

### 2.3 Exit gate

All three must hold before phase A is declared complete:

- **Determinism.** Replay harness re-executes last 100 accepted executions against `VerdictEngine` with persisted `(artifact, evidence_set, rules)`. Every verdict matches.
- **Zero direct transitions.** `Grep '\.status\s*=\s*['\"]'` across `platform/app/` returns matches **only** inside `app/validation/verdict_engine.py`. Pre-commit hook enforces.
- **Idempotency.** Two identical `forge_deliver(idempotency_key=X)` within 60 s produce one `Execution` row and one result. Integration test.

### 2.4 Blast radius

Estimated from the 30+ call sites catalogued in `GAP_ANALYSIS.md` §5.2. Shadow mode absorbs the variance. Enforcement cutover is a single PR with ~30 small diffs.

### 2.5 Reversal plan

- `VERDICT_ENGINE_MODE=off` — engine inert, old paths untouched.
- Migration down for `evidence_sets`, `idempotent_calls`, `verdict_divergences`.
- Pre-commit hook removable.
- No data loss: old code still wrote authoritative rows; engine rows are additive.

### 2.6 Out of scope (phase A)

- Contract typing (`ContractSchema`) — phase E.
- Risk bound $\tau$ calibration — decision, not code.
- Dashboards / UI for divergences — use SQL.

---

## 3. Phase B — Causal memory + context projection

### 3.1 Goal

Every decision, change, finding lives in a DAG with explicit justification edges. The agent's prompt context is a projection of that DAG, not a static scope filter. Memory becomes structurally queryable.

### 3.2 Scope

1. **`CausalEdge` table**
   - Columns: `id, src_type, src_id, dst_type, dst_id, relation, created_at`.
   - Unique constraint on `(src_type, src_id, dst_type, dst_id, relation)`.
   - DB trigger enforcing `src.created_at < dst.created_at` (acyclicity by time order).
   - Relations seeded: `justifies`, `supersedes`, `evidences`, `produced_by`, `blocks`.

2. **Insert guards**
   - Each `Decision`, `Change`, `Finding` insert requires at least one `CausalEdge` to an ancestor — enforced by database trigger, not application code.
   - Bootstrap exception: `kind='seed'` edges for initial project creation.

3. **Idempotent backfill**
   - Script `scripts/backfill_causal_edges.py` derives edges from existing FKs:
     - `Change.execution_id` → `produced_by` edge Change ← Execution.
     - `Finding.source_execution_id` (if present) → `evidences` edge Finding ← Execution.
     - `Decision.task_id` → `blocks` edge Decision → Task (reverse).
     - `Decision.alternatives_considered` JSONB scan for cross-decision refs.
   - Run twice safely (unique constraint absorbs).

4. **`CausalGraph` service**
   - `ancestors(node, depth=None, relation_filter=None) → [Node]`
   - `descendants(...)` symmetrical.
   - `minimal_justification(node) → [Node]` — shortest justification path.
   - Pure Python over the table.

5. **`ContextProjector`**
   - `project(task, budget_tokens) → ContextProjection{nodes, edges, char_count}`.
   - BFS over `CausalGraph`, filtered by task's `scope_tags` and `requirement_refs`, truncated to budget with a deterministic priority (must-guidelines → recent decisions → evidence → knowledge).
   - Persists as `context_projections(execution_id, projection_json, char_count, created_at)` for audit.

6. **Prompt assembly integration**
   - `prompt_parser.py` swaps its static `kb_scope` call for `ContextProjector.project()` behind a flag `CAUSAL_PROJECTION=on`.
   - `page_context.py` left untouched — that is UI sidebar, orthogonal.

### 3.3 Exit gate

- **Edge invariant.** Every new `Decision`/`Change`/`Finding` has $\ge 1$ `CausalEdge`. Trigger test.
- **Acyclicity.** Property test via `hypothesis`: random inserts never produce a cycle.
- **Projection fidelity.** For 10 historical executions, the projection contains every decision the agent actually referenced in reasoning. Spot-checked.
- **Budget respected.** `char_count < budget` for all 10 fixtures.

### 3.4 Reversal plan

- `CAUSAL_PROJECTION=off` — prompt assembly falls back to old path.
- Drop `causal_edges` and `context_projections` tables via migration down.
- Triggers defined in migration — dropped together.

### 3.5 Out of scope (phase B)

- Visualising the graph — nice-to-have, not required.
- Cross-project edges — phase B is per-project only.

---

## 4. Phase C — Reversibility + impact pre-estimate

### 4.1 Goal

Every mutation is classified and carries a compensation path where possible. Every change is preceded by an impact estimate that is later checked against reality.

### 4.2 Scope

1. **`Change` model extension**
   - Add `reversibility_class ∈ {REVERSIBLE, COMPENSATABLE, RECONSTRUCTABLE, IRREVERSIBLE}`.
   - Add `rollback_ref` (nullable, opaque string — script id, op id, snapshot path).
   - Default on insert: `IRREVERSIBLE` unless classifier says otherwise. Fail-safe conservative.

2. **`ReversibilityClassifier`**
   - Rule-based: add-only → REVERSIBLE; pure rename → REVERSIBLE; data migration → RECONSTRUCTABLE; `DROP TABLE`/destructive → IRREVERSIBLE.
   - Plugs into `forge_deliver` before `VerdictEngine.commit`.

3. **`Rollback` service**
   - `attempt(change_id) → RollbackResult`.
   - REVERSIBLE: re-applies inverse diff.
   - COMPENSATABLE: runs compensation script from `rollback_ref`.
   - RECONSTRUCTABLE: rebuilds state from evidence set.
   - IRREVERSIBLE: refuses, emits `Finding` requesting human.

4. **`BlastRadiusEstimator`**
   - Pre-execution: `estimate(task, proposed_diff) → {files_touched, tests_invalidated, risk_delta, review_cost_tokens}`.
   - Persisted in `Execution.impact_estimate`.
   - Post-execution: compares to actual diff; if |actual − estimated| > τ → `Finding(kind="impact_divergence")`.

5. **`ImpactDiff`** (plan-level)
   - `diff(old_plan, new_plan) → {tasks_preserved_ids, tasks_changed, ac_invalidated, fraction_changed}`.
   - Wired into `/change-request` path; blocks plan update if `fraction_changed > threshold` without explicit `--force`.

### 4.3 Exit gate

- **Disaster drill.** Against 5 historical REVERSIBLE changes, `Rollback.attempt` restores state with byte-identical checksums.
- **Estimator calibration.** Mean absolute error on `files_touched` across the last 20 executions is ≤ 1 file.
- **Plan stability.** Editing a single requirement mutates ≤ 2 task IDs in regeneration (snapshot test).

### 4.4 Reversal plan

- Columns nullable; downgrade removes them.
- Services disabled via flag; no behavior change when off.

---

## 5. Phase D — Failure-oriented testing + risk-weighted coverage

### 5.1 Goal

The test gate becomes a high-confidence falsification filter. Risk-weighted coverage replaces line coverage as the merge gate.

### 5.2 Scope

1. **Property tests (`tests/property/`)**
   - `test_verdict_determinism.py` — `@given` random `(artifact, evidence)` pairs; same inputs → same verdict.
   - `test_causal_acyclicity.py` — random edge insertions never produce cycles.
   - `test_idempotent_call.py` — calling any mutating tool twice with the same key has no additional side effect.
   - `test_reversibility.py` — REVERSIBLE changes round-trip losslessly.

2. **Metamorphic tests (`tests/metamorphic/`)**
   - `test_validator_paraphrase.py` — reasoning A and reasoning A' (paraphrased) with same evidence → same verdict.
   - `test_ac_permutation.py` — permuting AC order does not change verdict.
   - `test_finding_noise.py` — adding an unrelated Finding does not change verdict for a separate execution.

3. **Adversarial tests (`tests/adversarial/`)**
   - Every historical `Finding` becomes a regression fixture.
   - Generator: `build_adversarial_fixtures.py` reads `Finding` rows, emits pytest cases that reproduce the failure context.

4. **`FailureMode` entity**
   - `failure_modes(id, code, description, risk_weight, capability)`.
   - Each `Finding` optionally tagged with `failure_mode_id`.
   - Seeded with known modes (resubmit padding, confabulation, schema drift, …).

5. **`RiskWeightedCoverage` report**
   - Script `scripts/coverage_report.py` builds $\sum w_m \text{Cov}(T, m)$ per capability.
   - CI gate: below per-capability $\alpha$ → merge blocked.

6. **Deterministic harness**
   - `tests/conftest.py` pins random seed, uses `freezegun`, hermetic DB fixture.

### 5.3 Exit gate

- **Deterministic runs.** Three consecutive full test runs produce bit-identical results.
- **Mutation smoke.** Removing any single rule from `VerdictEngine` fails ≥ 1 test.
- **Coverage floor.** Risk-weighted coverage ≥ $\alpha$ for at least three capabilities.

### 5.4 Reversal plan

Tests only — removing them affects nothing in production.

---

## 6. Phase E — Continuous autonomy + diagonalization

### 6.1 Goal

Autonomy becomes continuous and reversible (can fall). The services tree diagonalizes into independent modes with typed interfaces. Contracts are self-adjoint (single source of truth for prompt + validator).

### 6.2 Scope

1. **Autonomy ledger**
   - `autonomy_states(project_id, capability, window_start, success_rate, rollback_rate, evidence_sufficiency, confabulation_rate)`.
   - Ingestor updates per execution.
   - Promotion / demotion policy: all four over floors → step up; any below → step down. Veto clauses unchanged.
   - L1–L5 retained as labels; internal state continuous.

2. **`ContractSchema`**
   - Typed Pydantic model for `Task.produces`.
   - `render_prompt_fragment() → str`
   - `validator_rules() → [Rule]`
   - A change to a field must change both — contract test.
   - Migration: existing `produces` JSONB coerced to `ContractSchema` or flagged as legacy.

3. **`ReachabilityCheck`**
   - Pre-`Objective ACTIVE` gate: at least one plan template or generator produces a plan satisfying each KR. Evidence recorded as JSONB in `Objective.reachability_evidence`.

4. **Services → modes refactor**
   - `app/services/` → `app/{planning, evidence, execution, validation, governance, autonomy}/`.
   - Mechanical `git mv` preserving blame.
   - Re-export shims in old paths for one release, then removed.
   - Typed Pydantic DTOs at mode boundaries.

5. **Per-mode contract tests**
   - Each mode has `tests/{mode}/contract/` asserting its external interface. Replacing the mode with a stub does not break other modes' contract tests.

### 6.3 Exit gate

- **Ledger operative.** After an induced regression (failure injection), measured quality drops and scope demotes within one run.
- **Self-adjoint contracts.** Mutation of a `ContractSchema` field changes prompt and validator in lock-step; drift test passes.
- **Diagonalization.** Stubbing `execution/` module does not break `validation/` tests.
- **Reachability.** Every ACTIVE objective has `reachability_evidence ≠ null`.

### 6.4 Reversal plan

- Autonomy: read-only mode (`AUTONOMY_LEDGER_MODE=log_only`).
- Refactor: re-export shims allow gradual rollback; full revert via `git revert`.
- `ContractSchema`: legacy path retained for objects flagged `contract_schema_version=0`.

---

## 7. What this plan explicitly does not do

Keeping this list honest is part of the spec.

- **No migration to LangGraph.** `Execution` + `ExecutionAttempt` already form a state machine. Adding LangGraph means rebuilding, not extending. Decision recorded in [ADR-TBD].
- **No multi-agent for interdependent tasks.** Forge tasks are, by construction, interdependent (shared contract, shared evidence). Multi-agent is considered only for explicitly decomposable fan-out (e.g. bulk profiling) in a future phase.
- **No new `CLAUDE.md`-style agent framework invention.** We keep the existing `forge/.claude/CLAUDE.md` minimal. Principles live in `FORMAL_PROPERTIES.md`; operational instructions stay short.
- **No standalone observability stack in this plan.** Logfire/Langfuse is a separate decision. `audit_log` + `ExecutionAttempt` + `VerdictDivergence` are enough for phase A–E acceptance.
- **No UI overhaul.** `page_context.py` is untouched. Sidebar is orthogonal to the causal projector.
- **No AI-generated ADRs without human review.** Any ADR this plan spawns is drafted by Forge, reviewed by a human before CLOSED (per Equal Experts guidance).

---

## 8. First PR (single unit of work, verifiable)

**PR title:** Phase A bootstrap — `EvidenceSet` entity + `VerdictEngine` shadow

**Scope:**
1. Alembic migration adding `evidence_sets` and `verdict_divergences` tables (with `down_revision`).
2. `app/validation/verdict_engine.py` — pure evaluator, registers `plan_gate` and `contract_validator` as rules.
3. `app/validation/gate_registry.py` — static dict of allowed transitions.
4. Feature flag `VERDICT_ENGINE_MODE` default `shadow`.
5. In `execute.py` and `pipeline.py`, *add* shadow calls alongside existing `.status =` assignments (no replacement yet).
6. `tests/property/test_verdict_determinism.py` — 1 `hypothesis` test to seed the property folder.
7. Docs update: `platform/docs/FORMAL_PROPERTIES.md` and `GAP_ANALYSIS.md` referenced from `platform/README.md`.

**Acceptance:**
- All existing tests green.
- New property test green.
- After one hour of real traffic in shadow mode, divergence count is 0 on `/executions` path.

**Size estimate:** ~400 LOC additive, 0 LOC removed. Reversible via migration down + flag off.

**Blast radius:** zero to existing flows (shadow-only). Adds DB tables; existing writers untouched.

**This PR is the Faza-A-step-1 entry. All subsequent steps compose on top of it.**

---

## 9. Dependency graph of phases

```
           ┌─── Phase B (memory + projection) ────┐
           │                                      │
Phase A ───┼─── Phase C (reversibility + impact) ─┼─── Phase E (autonomy + diagonal)
           │                                      │
           └─── Phase D (failure-oriented tests) ─┘
                        ↑
                   (writes tests against A and B's outputs)
```

Phases B, C, D are independent of each other once A exit gate passes — they can run in parallel on separate branches. Phase E waits for all.

---

## 10. How this plan is itself idempotent and reversible

Re-running the plan on the current state produces the same sequence: A opens, D is blocked until A+B close, E is last. No step loses information if re-read from the top. Every phase has a named rollback. The plan document is append-only; decisions to change course produce new ADRs, not edits to existing phases.

If any phase fails its exit gate, the plan halts — subsequent phases are blocked-by the failing phase's gate. That is how continuity is preserved as a property of the plan itself.

# Forge Platform — Gap Analysis

**Date:** 2026-04-22
**Audit method:** direct code read (`Grep`, `Read`) of `platform/app/`, `platform/tests/`, `platform/IMPLEMENTATION_TRACKER.md`. No agent summaries trusted — every claim traces to a file:line.
**Measured against:** [`FORMAL_PROPERTIES.md`](FORMAL_PROPERTIES.md) v2026-04-22-v1.
**Scope:** `platform/` only. Legacy `forge/core/` and `forge_output/` excluded.

**Legend:** PRESENT (exists and satisfies the property), PARTIAL (exists but incomplete), ABSENT (not built), WRONG-SHAPE (exists under this name but does not satisfy the property).

---

## Summary table

| # | Property | Status | Primary evidence | Severity |
|---|---|---|---|---|
| 3.1 | Idempotence | PARTIAL | `ExecutionAttempt.reasoning_hash` yes; MCP tools no `idempotency_key` | HIGH |
| 3.2 | Continuity | ABSENT | no `ImpactDiff`; `/change-request` rebuilds plan without bounded-delta check | HIGH |
| 3.3 | Operational differentiability | ABSENT | no `BlastRadiusEstimator`; plan accepts without impact estimate | MEDIUM |
| 3.4 | Asymptotic autonomy | PARTIAL | `autonomy.py` L1–L5 discrete; no continuous ledger, no demotion path | HIGH |
| 3.5 | Reversibility | ABSENT | `Change` has no class, no rollback_ref | HIGH |
| 4.1 | Outcome surjectivity | PARTIAL | `Objective`/`KeyResult` present; no `ReachabilityCheck` before ACTIVE | MEDIUM |
| 4.2 | Evidence Completeness Theorem | WRONG-SHAPE | validators exist as scattered pure functions; no `EvidenceSet` entity, no `VerdictEngine`, no enforced biconditional | **CRITICAL** |
| 4.3 | Coverage completeness (risk-weighted) | ABSENT | no `FailureMode` entity, no risk-weighted coverage report | HIGH |
| 4.4 | Failure-oriented test selection | ABSENT | 60+ test files, zero `hypothesis`/metamorphic/adversarial | HIGH |
| 5.1 | Deterministic evaluation | PARTIAL | `plan_gate.py`, `contract_validator.py` are pure-ish; no replay harness | MEDIUM |
| 5.2 | Universal gating | **ABSENT** | **30+ direct `execution.status = "X"` / `task.status = "X"` sites across 6 files** | **CRITICAL** |
| 5.3 | Architectural diagonalizability | ABSENT | 47 services in one flat directory, modes not separated | MEDIUM |
| 5.4 | Operational self-adjointness | PARTIAL | `Task.produces` exists (contract shape); not used as single source for prompt + validator | HIGH |
| 5.5 | Causal decision memory | ABSENT | `Decision` is atom (no parent_id/supersedes); no `CausalEdge` table | **CRITICAL** |
| 5.6 | Context projection | WRONG-SHAPE | `page_context.py` is UI sidebar context, not history projection; no projector over causal graph | HIGH |

Four **CRITICAL** / seven **HIGH** findings. The rest MEDIUM. Zero properties fully satisfied; three fully absent; five partial. That is the shape of the delta.

---

## Property-by-property detail

### 3.1 Idempotence — PARTIAL

**Present.**
- `execution_attempts` table stores `reasoning_hash` per attempt. `IMPLEMENTATION_TRACKER.md:152` reports attempts #3 and #4 sharing `r_hash 9ba117e0`, triggering `resubmit.identical_reasoning` warning. So dedup exists for *delivery* re-submissions.

**Gap.**
- MCP tools (`mcp_server/server.py`: `forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`) accept no `idempotency_key`. Two identical HTTP/MCP calls during a network retry produce two rows. No `IdempotentCall` table, no `(tool, key, args_hash) → result` cache.
- `POST /projects` and `POST /projects/{slug}/tasks` have the same shape. Grep on `idempotency_key` returns zero hits across platform.

**Delta to close.** Add `IdempotentCall` table (`tool, key, args_hash, result_ref, expires_at`), middleware that intercepts mutating MCP calls, client-side contract to generate `idempotency_key`.

---

### 3.2 Continuity — ABSENT

**Gap.**
- `/change-request` path (seen in `IMPLEMENTATION_TRACKER.md` and root `CLAUDE.md`) documents the slash command but platform has no equivalent endpoint or service that reports a bounded delta. No `ImpactDiff` service. No persisted `plan_delta` for before/after.
- Plan regeneration is not shape-preserving: task IDs are re-allocated rather than matched on stable identity (requirement refs).

**Delta.** `ImpactDiff(old_plan, new_plan) → {tasks_preserved, tasks_changed, ac_invalidated, plan_fraction_changed}`. Plan regenerator preserves IDs where `requirement_refs` match.

---

### 3.3 Operational differentiability — ABSENT

**Gap.** No `BlastRadiusEstimator`. Grep on that name returns zero. Plan approval does not carry an estimate. `Finding` model exists but it is post-hoc, not predictive.

**Delta.** Pre-mutation estimator returning `{files_touched, tests_invalidated, risk_delta, review_cost_tokens}`, persisted on `Execution`; post-execution divergence > τ emits a `Finding`.

---

### 3.4 Asymptotic autonomy — PARTIAL

**Present.**
- `app/services/autonomy.py` implements L1–L5 with `PROMOTION_CRITERIA` (clean_runs_required, min_contract_chars). Uses `OrchestrateRun` to count clean runs. Has veto (see module docstring lines 8–11).

**Gap.**
- Progression is **discrete** (five levels). The property demands a continuous ledger with rolling quality $Q_n$.
- No demotion path. `autonomy.py:63` `can_promote_to` is one-way; nothing decrements on failure.
- `Q_n` components (rollback_rate, evidence_sufficiency, confabulation_rate) are not tracked as time-series. `clean_runs_count` is a single integer.
- Per-capability scope is missing — autonomy is per-project, not per-capability envelope.

**Delta.** Extend `autonomy.py` with a rolling ledger (`AutonomyState(project_id, capability, window_start, success_rate, rollback_rate, ...)`). Add demotion triggers. Keep L1–L5 as public labels; make internal state continuous.

---

### 3.5 Reversibility — ABSENT

**Gap.**
- `Change` model (`app/models/change.py:8–24`) fields: `action, file_path, summary, reasoning, lines_added, lines_removed`. **No** `reversibility_class`, **no** `rollback_ref`.
- No `Rollback` service. No disaster drill. No per-class handling.

**Delta.** Add columns on `Change`; add `ReversibilityClassifier` that inspects diff shape; add `Rollback.attempt(change_id)` with branch per class; disaster-drill test that cycles a REVERSIBLE change and asserts state checksum.

---

### 4.1 Outcome surjectivity — PARTIAL

**Present.** `Objective` and `KeyResult` entities exist (confirmed `IMPLEMENTATION_TRACKER.md:26–27`, `pipeline.py:1209–1211` auto-updates KR on task completion).

**Gap.** No `ReachabilityCheck` gate. An Objective transitions to ACTIVE (`tier1.py:513`) without evidence that at least one plan template can satisfy each KR.

**Delta.** Pre-ACTIVE gate: KR has at least one candidate workflow (`plan_template_ref` or generator that produces one). Reject transition otherwise. Record the evidence.

---

### 4.2 Evidence Completeness Theorem — WRONG-SHAPE (CRITICAL)

**Present in pieces.**
- `contract_validator.py:52` `CheckResult(status, check, detail)` is per-check pure.
- `plan_gate.py:42` `validate_plan_requirement_refs(tasks, *, project_has_source_docs)` is a pure boolean validator.
- `Execution` model has `contract`, `delivery`, `validation_result` JSONB blobs.

**Why still WRONG-SHAPE.**
- No `EvidenceSet` entity. Evidence is interleaved across `PromptElement`, `ExecutionAttempt`, `Change`, `Finding`, and `validation_result` blob. No way to say "these evidence rows justify artifact $a$ sufficiently for rule $r$".
- No `VerdictEngine`. The biconditional $\text{Gate}(a) = 1 \iff (\text{Req}(a) \subseteq \text{Prov}(a) \wedge \text{Verify}(a) = 1 \wedge \text{Risk}(a) \le \tau)$ is implemented piecemeal inside `execute.py:317` (`status = "ACCEPTED"`), `pipeline.py:1272`, `pipeline.py:1459`. No enforcement that the three conditions hold together.
- `Task.produces` exists but is not used to derive $\text{Req}(a)$ — it is a free-form JSONB comment.

**Delta.**
1. Introduce `EvidenceSet` table: `{id, artifact_ref, kind, provenance, checksum, sufficient_for: [rule_ids], created_at}`.
2. Introduce `VerdictEngine.evaluate(artifact, evidence_set, rules) → {verdict, failed_rules, missing_evidence}`.
3. Replace all `execution.status = "ACCEPTED"/"REJECTED"` sites with `VerdictEngine.commit(execution, verdict)`.
4. Derive `Req(a)` from `Task.produces` + registered rules.

This is the single largest change and everything else composes on top of it.

---

### 4.3 Coverage completeness (risk-weighted) — ABSENT

**Gap.** Grep `FailureMode`, `risk_weighted`, `coverage` across platform: nothing relevant. `test_coverage_analyzer.py` exists but analyses test-to-AC coverage (nominal), not failure-mode coverage.

**Delta.** Add `FailureMode` entity; link every `Finding` that names a recurring mode; build `RiskWeightedCoverage` report; CI gate $\sum w_m \text{Cov}(T, m) \ge \alpha$ per capability.

---

### 4.4 Failure-oriented test selection — ABSENT

**Evidence of absence.** Grep `from hypothesis|import hypothesis|@given|metamorphic|adversarial` across platform: **zero** hits. 60+ test files under `platform/tests/`, all unit or integration using plain pytest.

**Delta.** `pyproject.toml` += `hypothesis`, `freezegun`. New dirs: `tests/property/`, `tests/metamorphic/`, `tests/adversarial/`. Seed property tests against `VerdictEngine` determinism, `CausalEdge` acyclicity, idempotency invariants.

---

### 5.1 Deterministic evaluation — PARTIAL

**Present.** `plan_gate.py:42` is a pure function over `tasks_data + flag`. `contract_validator.py` is mostly pure (reads no global state in the inspected header).

**Gap.**
- No replay harness. Cannot re-run a historical verdict against persisted evidence and check bit-identical result.
- Clock / randomness not pinned in production gates. A rule using `datetime.utcnow()` would slip through today.

**Delta.** Forbid wall-clock / rand inside `VerdictEngine`. Replay test on top 20 historical executions.

---

### 5.2 Universal gating — ABSENT (CRITICAL)

**Evidence of absence.** `Grep 'execution\.status\s*=|task\.status\s*='` returned **30+ direct assignments** across:
- `app/api/execute.py:125, 243, 244, 317, 319, 398, 428, 431, 458, 461`
- `app/api/pipeline.py:863, 972, 975, 1261, 1272, 1274, 1459, 1464, 1465, 1632`
- `app/api/tier1.py:481, 513, 1396, 1706`
- `app/api/projects.py:573, 580, 586`
- `app/api/ui.py:937`
- `app/services/orphan_recovery.py:59, 113, 165`

Each of these is a silent state transition. The `CheckConstraint` in `execution.py:14` and `decision.py:12` prevents *invalid values* but not *ungoverned transitions*.

**Delta.** `GateRegistry(from_state, to_state) → [required_rules]`. Single `transition(from, to, evidence)` API. Pre-commit grep that rejects any new direct `\.status\s*=\s*['\"]` outside the engine. Migration path: introduce engine, wrap call sites one-by-one behind a feature flag, flip flag when zero-drift shadow mode confirms parity.

---

### 5.3 Architectural diagonalizability — ABSENT

**Evidence.** `app/services/` has 47 files in a flat namespace (see glob output). A sample of cross-mode mixing: `hooks_runner.py` (governance) imports `budget_guard.py` (governance) but is called from `execute.py` (execution). `autonomy.py` reads `Objective`/`Project` directly (tight coupling to planning).

**Delta.** Refactor to `app/{planning, evidence, execution, validation, governance, autonomy}/` as the last phase (after functional gaps are closed). Typed Pydantic DTOs at mode boundaries. Today's services become adapters.

---

### 5.4 Operational self-adjointness — PARTIAL

**Present.** `Task.produces` exists (JSONB, per Forge CLAUDE.md). `Execution.contract` stores a frozen snapshot.

**Gap.** There is no `ContractSchema` that **simultaneously** renders prompt constraints and validator checks. The prompt assembly (in `prompt_parser.py`) and validation (in `contract_validator.py`) share no source of truth; drift between them is possible and silent.

**Delta.** `ContractSchema` dataclass owned by the task's `produces`. Two outputs: (a) rendered prompt fragment, (b) validator rule set. Tested by a unit that mutates one field of `ContractSchema` and asserts both outputs change.

---

### 5.5 Causal decision memory — ABSENT (CRITICAL)

**Evidence.** `Decision` model (`app/models/decision.py:9–33`) columns: `id, project_id, execution_id, external_id, task_id, type, issue, recommendation, reasoning, status, severity, confidence, alternatives_considered, resolution_notes`. **No** `parent_decision_id`, **no** `supersedes`, **no** graph edges.

`Change` ties to `execution_id` and `task_id` but not to the `Decision` that motivated it. `Finding` has its own external id but no causal upstream.

**Delta.** `CausalEdge(src_type, src_id, dst_type, dst_id, relation, created_at)` with unique constraint and acyclicity enforced (`src.created_at < dst.created_at`). Backfill from `Decision.blocked_by_decisions` (per root `CLAUDE.md`), `Change.execution_id`, `Finding.source_execution_id` where present. Idempotent backfill — runnable twice without duplicates.

---

### 5.6 Context projection — WRONG-SHAPE

**Evidence.** `app/services/page_context.py:11–57` defines `PageContext` with `page_id, title, description, entity_type, actions, suggestions`. It is the **UI sidebar context** for the HTMX chat. Docstring (line 4): *"Each route populates `request.state.page_ctx` with a PageContext. base.html renders it as JSON…"*

This is not a causal-graph projector. It has no connection to history, decisions, or evidence.

`app/services/kb_scope.py` does filter knowledge by scope tags — that is a primitive projector over Knowledge only, missing the rest of the graph.

**Delta.** New `ContextProjector(task, budget_tokens)`: BFS over `CausalEdge`, filter by scope + requirement refs, prune to budget. Persist selected subgraph per `Execution` as `ContextProjection` for audit.

---

## Cross-cutting diagnostics

These aren't properties — they are **structural anti-patterns** that cause multiple gaps at once. Closing the diagnostic closes several gaps.

### D1. Scattered state mutations (causes 3.1, 4.2, 5.2)

Every module that wants to change state calls `x.status = "..."`. Adding a new transition type today means editing N files and hoping nothing drifted. This is the single largest leverage point: introducing `VerdictEngine` + `GateRegistry` is forced by three properties at once.

### D2. Contract shape is free-form JSONB (causes 4.2, 5.4, 3.2)

`Task.produces`, `Execution.contract`, `Execution.delivery` are all typed `dict`. Free JSONB cannot mechanically drive self-adjointness (5.4), evidence completeness (4.2), or impact diffing (3.2). Tightening these into `ContractSchema` (typed) unlocks three properties.

### D3. Post-hoc evidence, no pre-hoc estimate (causes 3.3, 4.1, 3.4)

Forge records what happened (`Change`, `Finding`, `validation_result`) but does not record what it *expected* to happen. Adding pre-execution estimates (blast radius, reachability, $Q_n$ forecast) closes three properties.

### D4. No graph-shaped memory (causes 5.5, 5.6, 3.4)

Decisions, changes, findings, executions all live in flat tables with loose FKs. A causal edge table is cheap and forces projection (5.6), memory (5.5), and autonomy trend analysis (3.4) into a single shared structure.

---

## What is already good

Not all news is bad. The following are load-bearing foundations the plan builds on, not replaces.

- `Execution`, `ExecutionAttempt`, `PromptSection`, `PromptElement` form a complete audit trail of **prompt assembly**. Good evidence base.
- `plan_gate.py` and `contract_validator.py` are pure functions — good adapters for a future `VerdictEngine`.
- `autonomy.py` captures the intent of graduated autonomy — the shape is right, the resolution is too coarse.
- `Knowledge`, `Objective`, `KeyResult`, `Finding` entities exist and are wired into prompts and KR auto-update (`pipeline.py:1209–1211`).
- `IMPLEMENTATION_TRACKER.md` is a real artifact with EXECUTED/INFERRED discipline — keep it and extend its verification method to the new changes.

---

## Risk map for closing the gap

| Change | Blast radius | Reversibility class | Main risk |
|---|---|---|---|
| `VerdictEngine` + `GateRegistry` | 30+ call sites | COMPENSATABLE (shadow mode) | validator drift during shadow window |
| `EvidenceSet` entity | DB migration, ~10 writers | REVERSIBLE (nullable FK, downgrade) | orphaned evidence if writer skipped |
| `CausalEdge` + backfill | DB migration, one-time job | REVERSIBLE (table drop) | backfill misses implicit relations |
| `ContextProjector` | prompt assembly | REVERSIBLE (feature flag) | prompt regression on token count |
| Autonomy ledger | `autonomy.py` internals | REVERSIBLE (new table only) | over-aggressive floors block delivery |
| Property / metamorphic tests | test dir only | REVERSIBLE (delete) | flaky without deterministic harness |
| Services → modes refactor | 47 files, ~200 imports | COMPENSATABLE (re-export shims) | broad PR, merge conflicts |
| `ReversibilityClassifier` + `Rollback` | `Change` model | REVERSIBLE (column + service) | classifier misclassifies → fail-safe wins |

No single change is IRREVERSIBLE. Every row has a named downgrade. That matters.

---

## What this gap analysis does not answer

- What the right value of $\alpha$ (risk-weighted coverage threshold) or $\tau$ (risk bound) is per capability. Those are calibration decisions for `/decide`.
- Whether `CausalEdge` should live in Postgres (recommended) or in a separate graph store. Decision due before Phase B.
- Whether `hypothesis` is the right PBT library. Decision due before Phase D.

These should be recorded as OPEN decisions, not assumed in the plan.

# Forge Platform — Gap Analysis (v2)

**Status:** **DRAFT** — pending distinct-actor peer review per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Gap findings authored solo; must be independently re-verified (grep + read, not by accepting author's citation) before binding. Tracked as **R-GOV-01** in deep-risk 2026-04-23.
**Date:** 2026-04-22 (status demotion 2026-04-23).
**Audit method:** direct code read (`Grep`, `Read`) of `platform/app/`, `platform/tests/`, `platform/IMPLEMENTATION_TRACKER.md`. Every citation verified against current code.
**Evidence caveat** (deep-risk R-GAP-02, composite 15 HIGH): `platform/IMPLEMENTATION_TRACKER.md` is self-reported evidence from a prior Claude session (dated 2026-04-15/16). Per CONTRACT §B.8 transitivity, those claims are [ASSUMED] at this level until independently re-verified via HTTP smoke test against running platform. Any v2 gap binding on an [EXECUTED] tracker claim should be re-checked before Phase A.
**Measured against:** [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md). Supersedes [`archive/GAP_ANALYSIS.md`](archive/GAP_ANALYSIS.md) v1.
**Scope:** `platform/` only.

## 0. Corrections from v1 (before new analysis)

Three factual errors in v1 are corrected here:

1. **Hallucinated reference: `Decision.blocked_by_decisions`** — not a column on the DB model. `blocked_by_decisions` is documented in `forge/.claude/CLAUDE.md:121` as an *intended task property*, but `platform/app/models/task.py` does not persist it either. Backfill source removed; see §P14 below.

2. **Hallucinated reference: `Finding.source_execution_id`** — not a column. `finding.py:24` has `execution_id`, `finding.py:43` has `source_llm_call_id`. The correct backfill source for causal edges is `Finding.execution_id`.

3. **Undercount: "30+ direct `.status = ` sites"** — actual count via `Grep status\s*=\s*['\"]|\.state\s*=\s*['\"]` on `platform/app/`: **75 occurrences across 9 files** (`execute.py`, `pipeline.py`, `projects.py`, `tier1.py`, `ui.py`, `hooks_runner.py`, `orphan_recovery.py`, `pipeline_state.py`, `templates/base.html`). Scope of P7 migration is larger than v1 stated.

4. **Severity misclassification: P14 Causal Memory was ABSENT** — should be PARTIAL. Eight FK-based causal relations already exist in the schema (catalogued in §P14 below). The shape gap is still critical, but the source material for backfill is richer than v1 acknowledged.

## 1. Summary table — 24 atomic properties

| # | Property | Status | Primary evidence | Severity |
|---|---|---|---|---|
| P1 | Idempotence | PARTIAL | `ExecutionAttempt.reasoning_hash` yes; no `idempotency_key` on MCP tools (0 hits) | HIGH |
| P2 | Continuity | ABSENT | no `ImpactDiff`; `/change-request` lacks delta reporting | HIGH |
| P3 | Impact Closure | ABSENT | no closure-of-dependencies; only partial via `task_dependencies` (which has no import graph + side-effect registry) | HIGH |
| P4 | Asymptotic autonomy | PARTIAL | `autonomy.py` L1–L5 discrete; **no demote() function** (confirmed: zero `def demote`/`demote(` matches); no rolling $Q_n$ ledger | HIGH |
| P5 | Reversibility | ABSENT | `Change` has no class, no rollback_ref | HIGH |
| P6 | Deterministic evaluation | PARTIAL | `plan_gate.py`, `contract_validator.py` are pure-ish; no replay harness | MEDIUM |
| P7 | Universal gating | **ABSENT** | **75 direct `.status = "..."` across 9 files** | **CRITICAL** |
| P8 | Evidence Completeness Theorem | WRONG-SHAPE | validators scattered; no `EvidenceSet`, no `VerdictEngine`; biconditional not enforced | **CRITICAL** |
| P9 | Outcome surjectivity | PARTIAL | `Objective`/`KeyResult` present; no `ReachabilityCheck` pre-ACTIVE | MEDIUM |
| P10 | Risk-weighted coverage | PARTIAL | `AcceptanceCriterion.scenario_type ∈ {positive,negative,edge_case,regression}` exists (task.py:86); no `FailureMode` entity with risk weights; zero property-based / metamorphic tests | HIGH |
| P11 | Architectural diagonalizability | ABSENT | 47 files in flat `app/services/`; modes not separated; cross-imports frequent | MEDIUM |
| P12 | Operational self-adjointness | PARTIAL | `Task.produces` JSONB exists; no `ContractSchema` deriving prompt + validator from one source | HIGH |
| P13 | Invariant preservation *(NEW)* | ABSENT | no `Invariant` entity; DB `CheckConstraint` catches value violations but not state-transition invariants | HIGH |
| P14 | Causal decision memory | PARTIAL | 8 FK-based causal relations in schema (list below); no `CausalEdge` table; no graph operations | **CRITICAL** |
| P15 | Context projection | WRONG-SHAPE | `page_context.py` is UI sidebar; `kb_scope.py` is primitive knowledge-scope filter; no causal-graph projector | HIGH |
| P16 | Evidence existence | PARTIAL | `Decision.execution_id` and `Decision.task_id` present (loose); no invariant "decision → non-empty evidence set" | HIGH |
| P17 | Evidence source constraint *(NEW)* | ABSENT | no `EvidenceSet.kind` enum with provenance constraint | MEDIUM |
| P18 | Evidence verifiability *(NEW)* | ABSENT | no reproducer_ref / checksum on evidence; no replay job | MEDIUM |
| P19 | Assumption control | PARTIAL | contract_validator emits 3 WARNINGs for missing tags (IMPLEMENTATION_TRACKER.md:126); partial, not REJECT | HIGH |
| P20 | Uncertainty blocks execution *(NEW)* | ABSENT | no BLOCKED status on Execution; UNKNOWN is tagged-and-continue today | **CRITICAL** |
| P21 | Root cause uniqueness *(NEW)* | ABSENT | `Decision.alternatives_considered` is free JSONB; no `type="root_cause"` enforcement | MEDIUM |
| P22 | Disclosure protocol | PARTIAL | operational contract in prompt + partial validator (assumptions required, impact required); 5 templates not fully enforced | HIGH |
| P23 | Verification independence *(NEW)* | PARTIAL | `forge_challenge` exists (independent challenger per `IMPLEMENTATION_TRACKER.md:55`) but not required for ACCEPTED; solo-verifier rule not enforced | HIGH |
| P24 | Transitive accountability *(NEW)* | ABSENT | `ai_interaction` / LLM-call tracking exists but parent→child epistemic degradation not modelled | MEDIUM |

**Tally:** 3 CRITICAL, 11 HIGH, 10 MEDIUM. Zero properties fully satisfied. Eight PARTIAL, two WRONG-SHAPE, fourteen ABSENT.

Seven of the properties are **NEW in v2** (P13, P17, P18, P20, P21, P23, P24) — they represent the gap that v1 missed.

---

## 2. Property-by-property detail (only deltas from v1 highlighted)

### P1 — Idempotence (unchanged vs v1)

`ExecutionAttempt.reasoning_hash` present. Grep `idempotency_key` across platform: zero hits. Same delta as v1: `IdempotentCall` table + middleware.

### P2 — Continuity (unchanged vs v1)

No `ImpactDiff`. Delta unchanged.

### P3 — Impact Closure *(upgraded)*

**v1 proposal was too weak.** v1 said "BlastRadiusEstimator estimates {files_touched, tests_invalidated, risk_delta}". Engineer Soundness §4 demands `Impact(Δ) = Closure(dependencies)` — **full transitive closure**, not estimate.

**Present.** `task_dependencies` association table (`task.py:10–16`) — partial dependency structure at task level only.

**Gap.**
- No transitive closure over imports. `ImpactClosure` would need to walk Python import graph.
- No side-effect registry — functions that touch DB, external APIs, file system are not tagged.
- `BlastRadiusEstimator` (v1 proposal) is an estimate; it does not close the closure obligation.

**Delta.** Two services, one gate:
1. `ImportGraph` service (static AST walk of `app/`) — closed set of reverse-dependents of any module.
2. `SideEffectRegistry` — functions tagged `@side_effect(kind=...)`; closure includes callers of side-effects.
3. `ImpactClosure(change) → Set[File]` = `ImportGraph.reverse_deps(change.files) ∪ SideEffectRegistry.callers_in_path(...) ∪ task_dependencies.affected()`.
4. `BlastRadiusEstimator` retained as a *review-cost hint* over the closure, not the closure itself.

### P4 — Asymptotic autonomy (corrected & strengthened)

**Verified absent:** `def demote` / `demote(` → zero matches in `platform/app/`. `project.autonomy_level =` set only in `autonomy.py:103` inside `promote()`. Autonomy is strictly monotonic upward — **no demotion path exists**.

Delta unchanged from v1: add `AutonomyState` ledger, add `demote()`, per-capability not per-project.

### P5 — Reversibility (unchanged vs v1)

Delta unchanged.

### P6 — Deterministic evaluation (unchanged vs v1)

`plan_gate.py:42` `validate_plan_requirement_refs(tasks_data, *, project_has_source_docs)` — pure. `contract_validator.py:52` `CheckResult` dataclass — pure-ish. No replay harness.

### P7 — Universal gating (corrected count)

**Verified count: 75 occurrences across 9 files.** Specific file list:
- `app/api/execute.py` — execution/task state transitions
- `app/api/pipeline.py` — multi-transition orchestration (incl. KR status at 1209–1211)
- `app/api/projects.py` — finding triage (573, 580, 586)
- `app/api/tier1.py` — task/objective/finding/run state (481, 513, 1396, 1706)
- `app/api/ui.py` — run state (937)
- `app/services/orphan_recovery.py` — recovery transitions (59, 113, 165)
- `app/services/hooks_runner.py` — hook run state
- `app/services/pipeline_state.py` — pipeline state
- `app/templates/base.html` — render-time conditionals (not mutating)

Delta: `GateRegistry` + `VerdictEngine.commit()` + pre-commit grep. Scope larger than v1 estimated. Shadow mode for 1 week absorbs variance.

### P8 — Evidence Completeness Theorem (WRONG-SHAPE, unchanged)

Delta unchanged from v1. Largest single change in the plan.

### P9 — Outcome surjectivity (unchanged)

Delta unchanged.

### P10 — Risk-weighted coverage (PARTIAL, upgraded from ABSENT)

**Present (found in v2 audit, missed in v1):**
- `AcceptanceCriterion.scenario_type ∈ {positive, negative, edge_case, regression}` (`task.py:86–88`) — 4-category taxonomy already persisted.
- `AcceptanceCriterion.verification ∈ {test, command, manual}` (`task.py:89–92`) — verification mode typed.
- `AcceptanceCriterion.last_executed_at` (`task.py:106`) — B1 "trust-debt counter" tracks evidence staleness.
- `failure_mode` appears as a `kind` enum value on objective scenarios (`tier1.py:703`, `objective.py:39`, `templates/objective_detail.html:392`) — vocabulary exists, not entity.

**Gap.** No `FailureMode` **entity** with `risk_weight`. No risk-weighted coverage report. Zero `hypothesis` / metamorphic / adversarial tests across 59 test files.

**Delta.** Promote `failure_mode` from enum kind to first-class entity with `risk_weight`. Add property-based test infrastructure (`tests/property/`, `tests/metamorphic/`, `tests/adversarial/`). CI gate $\sum w_m \text{Cov}(T,m) \geq \alpha$.

### P11 — Architectural diagonalizability (unchanged)

47 files in `app/services/` (confirmed exact count via glob). Delta unchanged.

### P12 — Operational self-adjointness (unchanged)

### P13 — Invariant preservation *(NEW in v2)*

**Present in pieces:**
- DB `CheckConstraint` catches value violations (e.g., `execution.py:14` valid status enum; `task.py:33–36` status enum; `decision.py:12` decision status; `finding.py:12–19` finding type/severity/status).
- `task.py:22–25` `task_has_content` constraint (instruction OR description required).
- `task.py:15` `no_self_dep` on task_dependencies.

**Gap.** No `Invariant` entity registered per transition. No pre/post check on `execution.status` change that validates domain invariants (e.g., "task with ACCEPTED execution must have all AC verdicts = PASS").

**Delta.** `Invariant(code, applies_to_entity, check_fn)` table. `VerdictEngine.commit()` evaluates all applicable invariants post-transition; any failure → reject + rollback.

### P14 — Causal decision memory (PARTIAL, upgraded from ABSENT)

**Present (found in v2 audit):** eight FK-based causal relations already exist:
1. `Task.origin_finding_id` (`task.py:62`) → Finding caused Task
2. `Decision.execution_id` (`decision.py:20`) → Decision from Execution
3. `Decision.task_id` (`decision.py:22`) → Decision about Task
4. `Change.execution_id` (`change.py:16`) → Change from Execution
5. `Change.task_id` (`change.py:18`) → Change serves Task
6. `Finding.execution_id` (`finding.py:24`) → Finding from Execution
7. `Finding.source_llm_call_id` (`finding.py:43`) → Finding from LLMCall
8. `AcceptanceCriterion.source_llm_call_id` (`task.py:108`) → AC from LLMCall
9. `AcceptanceCriterion.source_ref` (`task.py:104`) → text attribution to SRC-XXX or objective
10. `Knowledge.source_ref` (`knowledge.py:43`) → text attribution

**Gap.** No normalized graph table. No cycle detection. No relation naming (`justifies` vs `supersedes` vs `produced_by` — all collapsed into FK semantics). No insert trigger.

**Delta.** `CausalEdge` table with unique constraint + acyclicity trigger. Idempotent backfill walks the 10 FK relations above plus parses `source_ref` tokens (SRC-XXX) into edges to Knowledge rows.

### P15 — Context projection (WRONG-SHAPE, unchanged)

`page_context.py:11–57` is UI sidebar (confirmed by docstring "Each route populates `request.state.page_ctx`"). `kb_scope.py` filters knowledge by scope tags — primitive. Delta: `ContextProjector` over `CausalEdge`.

### P16 — Evidence existence *(NEW in v2 as atomic)*

**Present:** `Decision` has `execution_id` and `task_id` (loose evidence anchor). `IMPLEMENTATION_TRACKER.md:20` records D-001 creation and resolution — flow exists.

**Gap.** No invariant "every Decision has at least one `EvidenceSet` link".

**Delta.** After `EvidenceSet` is introduced (phase A), require ≥ 1 `EvidenceSet` link per Decision. Trigger-level enforcement.

### P17 — Evidence source constraint *(NEW in v2)*

**Gap.** No `EvidenceSet.kind` enum. Evidence today is free-form in `Execution.validation_result`, `PromptElement.source_table`, `Change.reasoning`.

**Delta.** `EvidenceSet.kind ∈ {data_observation, code_reference, requirement_ref, test_output, command_output, file_citation}`. No `pattern`, no `intuition`, no `assumption`. Schema-enforced.

### P18 — Evidence verifiability *(NEW in v2)*

**Gap.** No reproducer (command / replay path) per evidence. No checksum at citation time.

**Delta.** `EvidenceSet.reproducer_ref` + `EvidenceSet.checksum_at_capture`. Weekly replay job on 5% sample.

### P19 — Assumption control (PARTIAL, upgraded & sharpened)

**Present.** `IMPLEMENTATION_TRACKER.md:126`: "Confabulation tag validation DONE — 3 WARNINGs generated for missing [EXECUTED]/[INFERRED]/[ASSUMED] tags." So `contract_validator` already detects missing tags — but emits WARNING, not FAIL.

**Gap.** Non-trivial claims (CONTRACT.md "7 triggers") without tags should REJECT, not WARN. Definition of "non-trivial" not enforced operationally.

**Delta.** `contract_validator` check: for reasoning mentioning data mutation / contract change / external system / cascade / timing — require `[CONFIRMED|ASSUMED]` tag; else REJECT. Promote 3 WARNING paths to FAIL per CONTRACT §A.

### P20 — Uncertainty blocks execution *(NEW in v2, CRITICAL)*

**Gap.** `Execution.status` enum (`execution.py:14–19`) has `PROMPT_ASSEMBLED, IN_PROGRESS, DELIVERED, VALIDATING, ACCEPTED, REJECTED, EXPIRED, FAILED`. **No `BLOCKED` state.** Today UNKNOWN is tagged-and-continue; user's satisfaction point §3 demands it blocks.

**Delta.** Add `BLOCKED` to `Execution.status` enum. Add `Execution.uncertainty_state` JSONB `{certain: [ids], uncertain: [ids]}`. Pipeline refuses to transition to ACCEPTED while uncertain ≠ ∅ on non-trivial claims. Resolution endpoint: `POST /executions/{id}/resolve-uncertainty` with explicit `[ASSUMED: accepted-by=<role>, date=YYYY-MM-DD]` record.

### P21 — Root cause uniqueness *(NEW in v2)*

**Present.** `Decision.alternatives_considered` JSONB column (`decision.py:30`). `Decision.type` string (`decision.py:23`).

**Gap.** No `type="root_cause"` specialization. No constraint that `alternatives_considered` has ≥ 2 entries each with explicit rejection reason.

**Delta.** Validator rule: `Decision.type in {"root_cause", "diagnosis"}` → `alternatives_considered` must have ≥ 2 items each with `rejected_because` field. Reject at `POST /decisions` if violated.

### P22 — Disclosure protocol (PARTIAL)

**Present (per IMPLEMENTATION_TRACKER.md:107–116):**
- "Evidence-first" clause in prompt ✓; "completion_claims checked" ✓ (PARTIAL)
- "Confabulation check" clause in prompt ✓; validator NOT DONE → fixed (see P19)
- "Assumptions before implementation" ✓ (assumptions required on delivery)
- "Impact before file change" ✓ (impact_analysis required)
- "Completeness check" clause in prompt ✓; completion_claims checked ✓
- "Fałszywa zgoda", "Granica kompetencji", "Wąska interpretacja" — in prompt, **NOT checked in validator**
- "Kontekst selektywny" — PARTIAL (impact_analysis)

**Gap.** Five format templates from CONTRACT §B are not fully enforced as structured output; §A behaviors 4–7 (narrow scope, selective context, false completeness, propagation failure) not validated.

**Delta.** Extend `contract_validator` with five template validators (DID/DID NOT/CONCLUSION, ASSUMING/VERIFIED/ALTERNATIVES, MODIFYING/IMPORTED BY/NOT MODIFYING, DONE/SKIPPED/FAILURE SCENARIOS ≥ 3). Missing template on applicable execution type → REJECT. Plus 7 behavior validators for CONTRACT §A.

### P23 — Verification independence (PARTIAL — already a partial builder exists)

**Present.** `forge_challenge` endpoint (`IMPLEMENTATION_TRACKER.md:55`) — "200, 6 auto-generated questions + enriched command returned — 2026-04-15". Independent challenger agent pattern is built.

**Gap.** Challenge is optional. Solo self-validation (contract_validator alone on same-turn reasoning) is accepted today. CONTRACT §B.8 solo-verifier rule: an artifact produced in turn $n$ cannot be marked verified in turn $n$ by the same actor.

**Delta.** Policy: `Execution.status = "ACCEPTED"` requires either (a) deterministic check passed (existing `verification: "test"|"command"` on AC), OR (b) `forge_challenge` passed by a distinct agent. Today: path (a) partially enforced, path (b) optional. Make exactly one of (a) or (b) mandatory.

### P24 — Transitive accountability *(NEW in v2)*

**Present.** `ai_interaction` model tracks LLM calls. `LLMCall` referenced by `Finding.source_llm_call_id` and `AcceptanceCriterion.source_llm_call_id`.

**Gap.** Parent→child epistemic degradation not modelled. A parent reasoning "CONFIRMED: the subagent said X is done" is treated as `[CONFIRMED]` today.

**Delta.** Validator rule: reasoning token patterns like "the agent reported", "subagent confirmed", "after delegation" + `[CONFIRMED]` within ≤ 200 chars → downgrade to `[ASSUMED]` WARNING. Repeated → REJECT. Side-effects from `ai_interaction` rows aggregate into parent's `MODIFYING` list (§P22).

---

## 3. Cross-cutting diagnostics (v2)

D1–D4 from v1 retained and one new added:

- **D1.** Scattered state mutations (75 sites) — causes P1, P7, P8, P13.
- **D2.** Contract shape is free-form JSONB — causes P8, P12, P2.
- **D3.** Post-hoc evidence, no pre-hoc estimate/closure — causes P3, P9, P4.
- **D4.** No graph-shaped memory, only loose FKs — causes P14, P15, P4.
- **D5 (new).** Disclosure is prose-in-prompt but not structured-in-output — causes P19, P20, P22, P23. Five format templates from CONTRACT §B are injected into the prompt but not validated as structured sections in the delivery. Making them structured JSON fields on `Execution.delivery` with validator rules closes four properties at once.

---

## 4. What is already good (v2 expanded)

- `Execution + ExecutionAttempt + PromptSection + PromptElement` — complete audit of **prompt assembly**.
- `plan_gate.py`, `contract_validator.py` — pure functions, adapter-ready.
- `autonomy.py` L1–L5 — shape correct, resolution coarse, **demote missing**.
- **Eight FK-based causal relations** already in schema — backfill source richer than v1 thought (see §P14).
- `AcceptanceCriterion.scenario_type` — 4-category failure taxonomy already persisted.
- `AcceptanceCriterion.verification` — three-mode verification typed.
- `AcceptanceCriterion.last_executed_at` — partial B1 trust-debt counter.
- `forge_challenge` endpoint — partial builder for P23 verification independence.
- `ai_interaction` + `LLMCall` model — tracks LLM calls, base for P24.
- `Decision.alternatives_considered` — present, just unstructured; base for P21.

---

## 5. Risk map

| Change | Blast radius | Reversibility class | Main risk |
|---|---|---|---|
| `VerdictEngine` + `GateRegistry` + shadow | 75 sites | COMPENSATABLE (shadow mode) | validator drift during shadow |
| `EvidenceSet` entity | DB migration, ~10 writers | REVERSIBLE | orphaned evidence if writer skipped |
| `CausalEdge` + backfill (10 FK sources) | DB migration, one-time job | REVERSIBLE | backfill misses implicit text refs |
| `ContextProjector` | prompt assembly | REVERSIBLE (flag) | prompt regression on token count |
| Autonomy ledger + demote | `autonomy.py` | REVERSIBLE | over-aggressive demotion |
| Property / metamorphic / adversarial tests | test dir only | REVERSIBLE (delete) | flakiness without deterministic harness |
| Services → modes refactor | 47 files, 200+ imports estimated | COMPENSATABLE (re-export shims) | broad PR churn |
| `ReversibilityClassifier` + `Rollback` | `Change` model | REVERSIBLE | misclassification → fail-safe = IRREVERSIBLE |
| `Invariant` entity + post-transition eval | `VerdictEngine.commit` | REVERSIBLE | false-positive invariant blocks delivery |
| `BLOCKED` state + uncertainty gate | `execution.py` enum + pipeline | COMPENSATABLE | agent confused by new state |
| Disclosure-protocol structured output | contract_validator + prompt | COMPENSATABLE | prompt rewrite affects all executions |
| Transitive-accountability validator | validator | REVERSIBLE | false-downgrades |
| Root-cause uniqueness validator | decision endpoint | REVERSIBLE | blocks legacy decisions |

No row is IRREVERSIBLE. Shadow / flag / migration-down available for each.

---

## 6. Open calibration decisions (required before phase A exit)

Per `FORMAL_PROPERTIES_v2.md §7`:

| Decision | Required by |
|---|---|
| Rolling window $W$ for $Q_n$ | P4 |
| Autonomy floors $q_{\min}$ (4 values per level) | P4 |
| Risk bound $\tau$ | P8 |
| Coverage floor $\alpha$ per capability | P10 |
| Idempotency TTL | P1 |
| Non-trivial definition: do we adopt CONTRACT.md's 7 triggers verbatim? | P19 |
| Uncertainty resolution actors: `user` / `product-owner` / `reviewer` — which roles may ACK? | P20 |
| Challenge requirement: per capability (P23) or universal? | P23 |

These must be CLOSED `Decision` rows before phase A ships. Any unresolved = P19 violation (assumption presented as confirmation).

---

## 7. What this gap analysis does not answer

- Concrete import-graph closure algorithm (topological vs depth-limited) — decision before phase B (Impact Closure).
- Whether `Invariant.check_fn` is Python callable reference or DSL expression — decision before phase E.
- Whether `BLOCKED` and `UNCERTAINTY_RESOLVED` are two states or one state with sub-status — decision before phase A.
- Whether `hypothesis` is the PBT library of record — decision before phase D.

All recorded as OPEN decisions in their respective phase entry gates.

---

## 8. Patch v2.1 — coverage categories + deterministic synthesis + CGAID framework gaps

Deep-verify 2026-04-22 pass surfaced five coverage-category findings, one deterministic-synthesis finding, and the omission of the entire CGAID framework layer from v2 (OPERATING_MODEL §2 Stage 0, §3 11 artifacts, §5 7 metrics, §4.3 Rule Lifecycle, §9.4 Snapshot Validation). All additions below.

### 8.1 Coverage categories — P10 strengthened

| Category | Verified state | file:line evidence | Severity |
|---|---|---|---|
| `scenario_type='edge_case'` | **ENFORCED** | `contract_validator.py:188-194`: FAIL if feature/bug lacks negative/edge_case PASS. `scenario_generator.py:33,117` knows category. `task.py:86` in enum. | OK — no change |
| `scenario_type='boundary'` | **ABSENT** (conflated with edge_case) | `scenario_generator.py:33` "Boundary condition handled correctly" — but only as edge_case subtext. No enum value `boundary`. | HIGH |
| `scenario_type='concurrent'` | **ABSENT** | no enum value; CONTRACT.md §B.5 FAILURE SCENARIOS example mentions "concurrent access" — prose only. | HIGH |
| `scenario_type='malformed'` | **ABSENT** (conflated with negative) | `scenario_generator.py:113-115` generates "400/409/422" error-code coverage — only shape errors, not fuzz/injection/binary. | HIGH |
| `scenario_type='performance'` | **PARTIAL** | `tier1.py:703` `kind='performance'` exists on `objective.scenarios.kind` but not on AC `scenario_type`. Inconsistent vocabulary. | MEDIUM |
| `scenario_type='security'` | **PARTIAL** | same as above (`objective.py:39`, `tier1.py:703`). | MEDIUM |
| `scenario_type='regression'` | PARTIAL — enum value exists, no auto-regenerate gate | `task.py:86` enum has `regression`; no gate that auto-creates a regression AC from closed Finding. | MEDIUM |

**Delta.** Unify vocab between `AcceptanceCriterion.scenario_type` and `objective.scenarios.kind`; extend enum to 9 values: `{positive, negative, edge_case, boundary, concurrent, malformed, regression, performance, security}`. Update `CheckConstraint` on `task.py:86–88`. Extend `scenario_generator.py` with per-category heuristic (boundary → triplet N-1/N/N+1; concurrent → interleaving; malformed → fuzz set).

### 8.2 Deterministic test synthesis — P25 (new)

**Present.** `scenario_generator.py:64` `generate_scenarios(acceptance_criteria)` is deterministic (same input → same output, pure Python, no randomness). Produces structured stubs from AC text.

**Gap.** Generation works AC-text → stub. It does NOT work ContractSchema → property-based test. Forge has no `TestSynthesizer` that walks `Task.produces` JSONB (or future `ContractSchema`) to emit `hypothesis` strategies, nor walks registered `Invariant.check_fn` to emit assert-based property tests.

**Delta.** `TestSynthesizer(contract_schema, invariants)` service emits `hypothesis`-parametrized tests per contract schema. Lands in `tests/synthesized/` (regeneratable, versioned in git for diffability). Part of Phase D (property tests) + Phase E (ContractSchema dependency).

### 8.3 CGAID framework layer — entirely absent in v2

Reading `ITRP/.ai/framework/OPERATING_MODEL.md` §2, §3, §4.3, §5, §9.4 surfaced **six compliance gaps** the v2 spec did not name:

| CGAID element | Forge status | Severity |
|---|---|---|
| **Stage 0 Data Classification Gate** (OM §2, DATA_CLASSIFICATION.md artifact #10) | **ABSENT** — `data_retention.py`, `pii_scanner.py` exist (partial) but no pre-ingest 4-tier classification (`PUBLIC/INTERNAL/CONFIDENTIAL/SECRET`) with routing matrix, Steward sign-off for Confidential+, 11-field log per entry. | **CRITICAL** for regulated contexts; HIGH otherwise |
| **Contract Violation Log** (enables OM §5 Metric 4) | **ABSENT** — no `ContractViolation` entity. Metric 4 is "aspirational, not measurable" in OM §5 until this log exists. | HIGH |
| **7 metrics service** (OM §5 M1–M7) | **ABSENT as service** — some signals exist in scattered form (`ExecutionAttempt`, `Finding`, `orphan_recovery`, `autonomy.clean_runs_count`), no dedicated collector, no dashboard, no quarterly aggregate. | MEDIUM |
| **Rule Lifecycle** (OM §4.3) | **ABSENT** — no `Rule` entity with `created_at / prevents_scenario / last_evidence_of_prevention / retired_at`. Existing `MicroSkill`, `Guideline`, validator rules have no retirement mechanism. | MEDIUM |
| **Framework Steward role** (OM §9.2 three rotating Stewards) | **ABSENT in schema** — no `User.steward_role`, no `AuditLog.reviewed_by_steward`, no `Decision.steward_sign_off`. | MEDIUM |
| **11 standardized artifacts** (OM §3) | **PARTIAL mapping** — most exist in Forge under different names: Evidence Pack (loose, distributed), Master Plan (`Objective`), Execution Plan (`Task` graph), Handoff (`handoff_exporter.py` exists!), ADR (`Decision` type), Edge-Case Test Plan (`AcceptanceCriterion`), Business DoD (no dedicated field), Skill Change Log (`skill_log_exporter.py` exists!), Framework Manifest (this doc set), Data Classification Rubric (missing, G1), **Side-Effect Map (artifact #11, missing — addressed by Phase C `SideEffectRegistry`).** | MEDIUM (mostly mapping, not building) |
| **Deterministic Snapshot Validation** (OM §9.4, 5-component reference pattern) | **ABSENT as framework** — individual snapshot-style checks exist (P5 `freezegun` in test fixtures proposed in phase D), no reusable service. | MEDIUM |
| **Adaptive Rigor alignment** (OM §7) | **RESOLVED** via [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md) — verified Forge `ceremony_level ∈ {LIGHT, STANDARD, FULL}` (3 levels, not 4 as v2.1 initially claimed — `MINIMAL` was cross-source hallucination from outer `forge/.claude/CLAUDE.md` legacy-pipeline docs). CGAID has `Fast Track / Standard / Critical` (3 tiers). **1:1 mapping CLOSED 2026-04-22.** | CLOSED |

These are addressed collectively in **Phase G — CGAID Compliance** (see CHANGE_PLAN_v2 §13).

### 8.4 Updated summary tally

Patch v2.1 changes the gap count:

| Severity | v2 (before patch) | v2.1 (after patch) |
|---|---|---|
| CRITICAL | 3 | 4 (adds Stage 0 in regulated contexts) |
| HIGH | 11 | 15 (adds boundary, concurrent, malformed, Contract Violation Log) |
| MEDIUM | 10 | 15 (adds perf/security vocabulary, regression gate, metrics service, Rule Lifecycle, Steward role, artifact mapping, snapshot validation, adaptive rigor alignment) |
| LOW | 0 | 1 (ceremony_level ↔ CGAID tier mismatch) |

Total atomic properties: **25** (up from 24 after adding P25).

Total tracked gaps: **35** (up from 24).

None of the v2.1 additions are IRREVERSIBLE. Every delta has a named rollback in CHANGE_PLAN_v2 §13 (Phase G).

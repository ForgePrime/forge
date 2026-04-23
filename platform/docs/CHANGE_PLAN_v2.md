# Forge Platform — Change Plan (v2)

**Status:** **DRAFT** — pending distinct-actor peer review per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Phase exit gates and blast-radius estimates authored solo — each phase's entry requires reviewer confirmation of its exit-gate feasibility. **Phase A may not begin** until this document + `FORMAL_PROPERTIES_v2.md` + `GAP_ANALYSIS_v2.md` transition to NORMATIVE.
**Date:** 2026-04-22 (status demotion 2026-04-23, deduplication vs ROADMAP 2026-04-23).
**Source of truth:** [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md).
**Gap input:** [`GAP_ANALYSIS_v2.md`](GAP_ANALYSIS_v2.md).
**Scope:** `platform/` only.
**Supersedes:** [`archive/CHANGE_PLAN.md`](archive/CHANGE_PLAN.md) v1 (retained append-only).

> **Division of concerns (updated 2026-04-23 deduplication):**
> - **This doc** — phase **rationale**, alternatives considered, blast-radius analysis, reversal plan, divergences from v1, Phase G compliance detail.
> - **[`ROADMAP.md`](ROADMAP.md)** — **operational view**: stages × entry/exit tests per phase, Pre-flight, test strategy, First PR, progress tracking.
>
> Where both documents say the same thing (phase overview, dependency graph, non-goals, First PR), **ROADMAP is canonical** — this doc links there.

v2 closes 24 atomic gaps (v1 addressed 15). New phase F introduces decision-discipline enforcement (P16–P24). Phases A–E retained, tightened, fixed for three concrete v1 issues: rule-adapter mismatch, impact-closure vs estimator, refactor impact subplan.

---

## 0. Principles (unchanged from v1)

Idempotent · continuous · reversible · diagonal · self-adjoint · surjective over goals · causal trace.

Each of these maps to a v2 atomic property: P1, P2+P3, P5, P11, P12, P9, P14. The plan is its own first consumer of P22 disclosure protocol — every phase is stated with DID / DID NOT / CONCLUSION equivalent (goal / scope / exit gate), alternatives, FAILURE SCENARIOS.

---

## 1. Phase overview

Canonical phase table lives in **[`ROADMAP.md §1`](ROADMAP.md)** (adds Pre-flight + stages + durations per phase). Read that for execution view. This document contains the **rationale per phase** in §2–§7 + §13.

---

## 2. Phase A — Deterministic gate fundament (tightened)

### 2.1 Goal

One write path for state. One verdict function. One idempotency contract on MCP tools. `EvidenceSet` captured as first-class. This is the leverage phase.

### 2.2 Scope

1. **`EvidenceSet` entity** (P8, P16)
   - Table `evidence_sets(id, artifact_type, artifact_id, kind, provenance, checksum_at_capture, reproducer_ref, rule_ref, sufficient_for_json, created_at)`.
   - `kind ∈ {data_observation, code_reference, requirement_ref, test_output, command_output, file_citation}` (P17).
   - Alembic up + down.
   - Wrappers in existing writers (`contract_validator`, `plan_gate`, `execute.py`) emit `EvidenceSet` rows as side effect; no behavior change.

2. **`GateRegistry`** (P7)
   - Static `(entity, from_state, to_state) → [rule_ref]` for `Execution` (8 transitions), `Task` (5), `Decision` (6 statuses), `Finding` (3 triage outcomes), `KeyResult` (3 statuses), `OrchestrateRun` (states).
   - Pure Python module `app/validation/gate_registry.py`; no DB.

3. **`VerdictEngine`** (P6, P7, P8)
   - `evaluate(artifact, evidence_set, rules) → Verdict{verdict, failed_rules, missing_evidence, risk}`.
   - `commit(entity, target_state, verdict)` — single write path.
   - **Rule adapter pattern** *(v1 fix)*: existing validators have different signatures (`plan_gate.validate_plan_requirement_refs(tasks_data, *, project_has_source_docs)` vs `contract_validator(reasoning, ac_evidence, ...)`) — not directly compatible with `Rule(artifact, evidence, context) → RuleResult`. Introduce `RuleAdapter` protocol that wraps existing pure functions into the interface. No rewrite of `plan_gate` / `contract_validator` — only adaptation.
   - Deterministic: no wall-clock, no rand, no network, no global mutable state.

4. **Shadow mode**
   - Flag `VERDICT_ENGINE_MODE ∈ {off, shadow, enforce}`.
   - In `shadow`: engine runs in parallel with existing `.status = "..."` paths; divergences logged to `verdict_divergences`.
   - Run shadow ≥ 1 week on real traffic. Close divergences to zero before cutover.

5. **Enforcement cutover**
   - Flip to `enforce`. Wrap all 75 `.status = "..."` sites behind `VerdictEngine.commit()`.
   - Pre-commit grep rejects any new direct `\.status\s*=\s*['\"]` outside the engine.

6. **MCP idempotency** (P1)
   - Table `idempotent_calls(tool, key, args_hash, result_ref, expires_at)`.
   - Middleware in `mcp_server/server.py` short-circuits duplicates within TTL.
   - `idempotency_key` added to signatures of `forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`.

7. **`Decision` evidence invariant** (P16)
   - DB trigger or app-level gate: `Decision` insert requires ≥ 1 `EvidenceSet` link.

### 2.3 Exit gate

All four:

- **Determinism.** Replay harness on last 100 accepted executions: bit-identical verdicts.
- **Zero direct transitions.** Grep `\.status\s*=\s*['\"]` outside `app/validation/verdict_engine.py` → zero matches. Pre-commit hook active.
- **Idempotency.** Two identical `forge_deliver(idempotency_key=X)` within 60 s: one row, one result.
- **Evidence invariant.** DB query: zero `Decision` rows with no `EvidenceSet` link.

### 2.4 Blast radius

75 call sites catalogued. Shadow absorbs. Enforcement = single PR with ~75 small wraps.

### 2.5 Reversal plan

- `VERDICT_ENGINE_MODE=off`.
- Alembic down for `evidence_sets`, `idempotent_calls`, `verdict_divergences`.
- Pre-commit hook removable.

### 2.6 Calibration decisions required for exit

Per GAP_ANALYSIS_v2 §6: idempotency TTL; what "artifact_type" enum values exist at phase A; whether `Decision` invariant is trigger-level or app-level.

---

## 3. Phase B — Causal memory + context projection (tightened)

### 3.1 Goal

History as DAG. Prompt context as projection. Backfill uses the **10 FK-based relations verified in v2 audit**, not the two hallucinated ones in v1.

### 3.2 Scope

1. **`CausalEdge` table** (P14)
   - `id, src_type, src_id, dst_type, dst_id, relation, created_at`.
   - Unique constraint on the tuple.
   - DB trigger enforcing `src.created_at < dst.created_at`.
   - Relations: `justifies`, `supersedes`, `evidences`, `produced_by`, `blocks`.

2. **Insert guards**
   - `Decision`, `Change`, `Finding` inserts require ≥ 1 `CausalEdge` to an ancestor (DB trigger).
   - Bootstrap exception: `kind='seed'` for initial project creation.

3. **Idempotent backfill** *(corrected from v1)*
   - Source FKs from `platform/app/models/*.py` (verified 2026-04-22):
     - `Task.origin_finding_id` → `produced_by` Task←Finding
     - `Decision.execution_id` → `produced_by` Decision←Execution
     - `Decision.task_id` → `blocks` Decision→Task (reverse)
     - `Change.execution_id` → `produced_by` Change←Execution
     - `Change.task_id` → `produced_by` Change←Task
     - `Finding.execution_id` → `produced_by` Finding←Execution
     - `Finding.source_llm_call_id` → `evidences` Finding←LLMCall
     - `AcceptanceCriterion.source_llm_call_id` → `evidences` AC←LLMCall
     - `AcceptanceCriterion.source_ref` → parse `SRC-NNN` tokens → `justifies` AC←Knowledge
     - `Knowledge.source_ref` → similar parse
     - `origin` field on Task (objective ref) → `justifies` Task←Objective
   - **Not in scope**: v1's proposed `Decision.blocked_by_decisions` (does not exist), v1's `Finding.source_execution_id` (does not exist).
   - Script `scripts/backfill_causal_edges.py` — runnable twice without duplicates (unique constraint absorbs).

4. **`CausalGraph` service** (P14)
   - `ancestors(node, depth, relation_filter)`, `descendants`, `minimal_justification`.

5. **`ContextProjector`** (P15)
   - `project(task, budget_tokens) → ContextProjection{nodes, edges, char_count}`.
   - BFS with deterministic priority: must-guidelines → recent decisions → evidence → knowledge. Truncate to budget.
   - Persists per Execution in `context_projections`.

6. **Prompt assembly integration**
   - `prompt_parser.py` swaps `kb_scope` for `ContextProjector.project()` behind `CAUSAL_PROJECTION=on`.
   - `page_context.py` untouched (UI orthogonal).

### 3.3 Exit gate

- Every new Decision/Change/Finding has ≥ 1 CausalEdge (trigger test).
- Random insertions never produce a cycle (`hypothesis` property test — phase D prerequisite).
- For 10 historical executions, projection contains every decision referenced in reasoning.
- Budget respected on all fixtures.

### 3.4 Reversal

`CAUSAL_PROJECTION=off`; migration down; triggers drop with migration.

---

## 4. Phase C — Impact closure + reversibility (corrected)

### 4.1 Goal *(v1 fix)*

v1 proposed `BlastRadiusEstimator`. v2 demands `Impact(Δ) = Closure(dependencies)` per Engineer Soundness §4. Estimator stays, but as a *review-cost hint* over a closure, not as the closure itself.

### 4.2 Scope

1. **`ImportGraph` service** (P3)
   - Static AST walk of `app/` modules. Stored as a cached adjacency structure.
   - `reverse_deps(module) → Set[module]` — transitive closure.

2. **`SideEffectRegistry`** (P3)
   - Functions tagged `@side_effect(kind=...)` with kinds: `db_write`, `external_api`, `filesystem`, `state_mutation`, `publish`.
   - `callers_in_path(module_set) → Set[function]`.

3. **`ImpactClosure`** (P3)
   - `compute(change) → Set[File]` = `ImportGraph.reverse_deps(change.files) ∪ SideEffectRegistry.callers_in_path(...) ∪ task_dependencies.affected(task_id)`.
   - Persisted per Execution. Gate: delivery whose `declared_modified_files ⊄ ImpactClosure ∪ {change.files}` is REJECTED (selective-context violation, CONTRACT §A.5).

4. **`ImpactDiff`** (P2)
   - `diff(old_plan, new_plan) → {preserved_ids, changed, ac_invalidated, fraction_changed}`.
   - Wired into `/change-request`; `fraction_changed > threshold` without `--force` → reject.

5. **`BlastRadiusEstimator` (demoted)** (P3 hint)
   - Runs over closure; returns `{files_touched, tests_invalidated, risk_delta, review_cost_tokens}` as *review cost*, not the closure.

6. **`Change.reversibility_class` + `Change.rollback_ref`** (P5)
   - Enum `REVERSIBLE | COMPENSATABLE | RECONSTRUCTABLE | IRREVERSIBLE`.
   - Default on insert ambiguity: `IRREVERSIBLE` (fail-safe).

7. **`ReversibilityClassifier`** (P5)
   - Rule-based: add-only → REVERSIBLE; pure rename → REVERSIBLE; data migration → RECONSTRUCTABLE; DROP/destructive → IRREVERSIBLE.
   - Invoked in `forge_deliver` before `VerdictEngine.commit`.

8. **`Rollback` service** (P5)
   - `attempt(change_id) → RollbackResult` per class.

### 4.3 Exit gate

- **Impact closure correctness.** Fixture: function $f$ called by $\{g, h\}$, $g$ by $\{k\}$. `ImpactClosure("modify f")` returns $\{f, g, h, k\}$ exactly. No element missing, no extra.
- **Plan stability.** Single-requirement edit mutates ≤ 2 task IDs (snapshot).
- **Disaster drill.** 5 historical REVERSIBLE changes round-trip via `Rollback.attempt` with byte-identical checksum.

### 4.4 Reversal

Flags; columns nullable; services idle without writers.

---

## 5. Phase D — Failure-oriented testing + risk-weighted coverage

### 5.1 Scope

1. **Property tests (`tests/property/`)** (P10)
   - `test_verdict_determinism.py` — `@given` random `(artifact, evidence)`; same inputs → same verdict (P6).
   - `test_causal_acyclicity.py` — random edge insertions never produce cycles (P14 invariant).
   - `test_idempotent_call.py` — two calls with same key → zero additional side effect (P1 invariant).
   - `test_reversibility_roundtrip.py` — REVERSIBLE changes round-trip losslessly (P5).
   - `test_invariant_preservation.py` — any `Invariant.check_fn` holds across its applicable transitions (P13).

2. **Metamorphic tests (`tests/metamorphic/`)** (P10)
   - `test_validator_paraphrase.py` — reasoning A vs paraphrase A', same evidence → same verdict.
   - `test_ac_permutation.py` — AC order permutation does not change verdict.
   - `test_finding_noise.py` — unrelated Finding does not change verdict.
   - `test_evidence_permutation.py` — order of EvidenceSet items does not affect verdict.

3. **Adversarial tests (`tests/adversarial/`)** (P10)
   - `build_adversarial_fixtures.py` reads historical `Finding`; emits regression pytest cases.

4. **`FailureMode` entity** (P10)
   - Table `failure_modes(id, code, description, risk_weight, capability)`.
   - Migrate vocab from `kind='failure_mode'` AC scenarios (already persisted per GAP §P10) into entity rows.
   - `Finding.failure_mode_id` optional FK.

5. **`RiskWeightedCoverage` report** (P10)
   - Script `scripts/coverage_report.py` builds $\sum w_m \text{Cov}(T,m)$ per capability.
   - CI gate: below $\alpha$ → merge blocked.

6. **Evidence verifiability sample replay** (P18)
   - Weekly job: 5% random sample of `EvidenceSet` rows. For `kind in {test_output, command_output}` → re-execute `reproducer_ref`; for `kind in {code_reference, file_citation}` → re-read + checksum compare. Divergence → Finding.

7. **Deterministic harness** (P6 + P10)
   - `tests/conftest.py`: pinned random seed, `freezegun` for time, hermetic DB fixture.

### 5.2 Exit gate

- Three consecutive full test runs — bit-identical.
- Mutation smoke — removing any `VerdictEngine` rule fails ≥ 1 test.
- Risk-weighted coverage ≥ $\alpha$ for ≥ 3 capabilities.
- Weekly replay job runs green on first scheduled run.

### 5.3 Reversal

Tests only — removal affects nothing in production.

### 5.4 Calibration

PBT library choice (`hypothesis` vs alternatives) as decision; $\alpha$ per capability as decision.

---

## 6. Phase E — Self-adjoint contract + diagonalization + invariants + autonomy

### 6.1 Goal

Long-tail structural work: invariants registered, contracts typed, services diagonalized, autonomy continuous.

### 6.2 Scope

1. **`Invariant` entity** (P13)
   - `invariants(code, description, applies_to_entity, check_fn_ref)`.
   - Registered per transition via `GateRegistry`.
   - `VerdictEngine.commit()` evaluates applicable invariants post-transition; `False` → reject + rollback.

2. **`ContractSchema`** (P12)
   - Typed Pydantic for `Task.produces`.
   - `render_prompt_fragment() → str` and `validator_rules() → [Rule]`.
   - Contract test: mutating a field changes both sides in lockstep; drift test must fail.
   - Migration: existing `produces` JSONB coerced OR flagged `contract_schema_version=0` (legacy).

3. **Autonomy ledger + demote** (P4)
   - `autonomy_states(project_id, capability, window_start, success_rate, rollback_rate, evidence_sufficiency, confabulation_rate, updated_at)`.
   - Ingestor updates per `Execution` completion.
   - `demote()` function — currently missing (verified). Triggers on any $Q_n$ component below floor.
   - L1–L5 retained as labels; internal state continuous.

4. **`ReachabilityCheck`** (P9)
   - Pre-`Objective ACTIVE` gate: ≥ 1 plan template satisfies each KR. Evidence in `Objective.reachability_evidence`.

5. **Services → modes refactor** (P11)
   - **v1 fix: sub-plan for impact.** Before refactor, run `ImpactClosure` (from phase C) on each of the 47 service files. Estimated ~200 import call sites (to be confirmed by `ImportGraph`).
   - Mechanical `git mv` preserving blame.
   - Re-export shims in `app/services/` for one release; then removed.
   - Typed Pydantic DTOs at mode boundaries.

6. **Per-mode contract tests** (P11)
   - `tests/{mode}/contract/` per mode. Stubbing one mode does not break other modes' contract tests.

### 6.3 Exit gate

- **Invariants live.** ≥ 1 invariant per entity with > 1 state; synthetic violation rejected at gate.
- **Contract self-adjoint.** Mutating `ContractSchema` field changes prompt and validator in lockstep; drift test green.
- **Autonomy ledger operative.** After injected regression, scope demotes within one run (synthetic drill).
- **Reachability invariant.** Every ACTIVE objective has `reachability_evidence ≠ null`.
- **Diagonalization.** Stub `execution/` → `validation/` tests still green.

### 6.4 Reversal

- Flags per sub-feature.
- Re-export shims allow gradual rollback of the refactor.
- `ContractSchema`: legacy `contract_schema_version=0` path retained.

---

## 7. Phase F — Decision discipline *(new in v2)*

### 7.1 Goal

Enforce the operational contract (CONTRACT §A + §B), evidence-only decisions (Evidence-Only Model), uncertainty-blocks-execution (user §3), verification independence (CONTRACT §B.8), transitive accountability (CONTRACT subagent rules). Eight properties close together because they share one operational substrate: **structured disclosure on delivery**.

### 7.2 Scope

1. **Evidence source constraint** (P17)
   - `EvidenceSet.kind` enum strictly validated (see phase A §2 for kind list).
   - No `pattern` / `intuition` / `assumption` accepted. Schema constraint.

2. **Evidence verifiability** (P18)
   - `EvidenceSet.reproducer_ref` mandatory for `test_output` / `command_output` kinds.
   - `checksum_at_capture` mandatory for `file_citation` / `code_reference`.
   - Weekly replay job in phase D.

3. **Assumption control enforcement** (P19)
   - Promote existing 3-tag WARNING check (`IMPLEMENTATION_TRACKER.md:126`) to REJECT for non-trivial claims.
   - Non-trivial per CONTRACT §A operational definition (7 triggers: data/contract/assumption/cascade/regulatory/timing/external). Encode as a classifier function (heuristic or LLM-judge).

4. **Uncertainty blocks execution** (P20)
   - Add `BLOCKED` to `Execution.status` enum (`execution.py:14–19` needs update; DB `CheckConstraint` updated).
   - Add `Execution.uncertainty_state` JSONB.
   - Pipeline refuses transition to ACCEPTED while `uncertainty_state.uncertain ≠ ∅` on non-trivial claims.
   - Endpoint `POST /executions/{id}/resolve-uncertainty` with explicit `[ASSUMED: accepted-by=<role>, date=YYYY-MM-DD]` record (appended to `EvidenceSet` with kind=`human_acceptance`).

5. **Root cause uniqueness** (P21)
   - Validator rule at `POST /decisions`: `type in {"root_cause", "diagnosis"}` requires `alternatives_considered` with ≥ 2 items, each with `rejected_because` field.
   - Schema: `alternatives_considered` validated as list of `{candidate, rejected_because}` (typed sub-schema).

6. **Disclosure protocol — structured delivery** (P22)
   - `Execution.delivery` JSONB gains typed sub-fields for each CONTRACT §B template:
     - `evidence_first: {did, did_not, conclusion}`
     - `pre_implementation: {assuming, verified, alternatives}` (optional for simple bugs)
     - `pre_modification: {modifying, imported_by, not_modifying}`
     - `pre_completion: {done, skipped, failure_scenarios (≥ 3)}`
   - `contract_validator` extended with five template validators. Missing template on applicable execution → REJECT.
   - CONTRACT §A behaviors 1–7: seven validator rules, each REJECT on silence violation.

7. **Verification independence** (P23)
   - Policy: `Execution.status = "ACCEPTED"` requires one of:
     - all AC with `verification in {test, command}` have deterministic evidence (existing P5.5 check — extend to 100%), OR
     - `forge_challenge` passed by a distinct agent.
   - Solo self-validation (contract_validator alone) is insufficient. Pre-existing `forge_challenge` endpoint becomes load-bearing.

8. **Transitive accountability** (P24)
   - Validator pattern: parent reasoning tokens ["the agent reported", "subagent confirmed", "after delegation", "tool returned"] + `[CONFIRMED]` within ≤ 200 chars of each other → downgrade to `[ASSUMED]` WARNING. Repeated → REJECT.
   - Side-effects aggregation: parent's `pre_modification.modifying` must include side-effects from `ai_interaction` children.

### 7.3 Exit gate

- **Source constraint.** Insert EvidenceSet with kind=`assumption` → rejected at schema.
- **Verifiability.** Replay job passes on first scheduled weekly run.
- **Assumption control.** Synthetic reasoning with a data-mutation claim missing a tag → REJECTED (not WARNED).
- **Uncertainty blocks.** Synthetic delivery with non-empty `uncertain` → BLOCKED, no ACCEPTED path.
- **Root cause.** Root-cause Decision with single alternative → REJECTED.
- **Disclosure.** Delivery missing pre-completion template → REJECTED.
- **Independence.** ACCEPTED without deterministic AC evidence AND without challenge → blocked.
- **Transitivity.** Copy-pasted subagent `[CONFIRMED]` → downgraded to `[ASSUMED]`.

### 7.4 Reversal

Validator rules behind feature flags (`P19_ENFORCE`, `P20_BLOCK`, etc.) — each can go off independently.

### 7.5 Calibration

- Non-trivial classifier threshold (heuristic false-positive/negative tradeoff).
- Which roles may ACK UNKNOWN (user / product-owner / reviewer).
- Challenge-required per capability or universal.

---

## 8. What v2 still does not do

Canonical non-goals list in **[`ROADMAP.md §16`](ROADMAP.md)**. Same content; maintained there.

---

## 9. First PR

Canonical First PR scope in **[`ROADMAP.md §13`](ROADMAP.md)** — Phase A Stage A.1 `EvidenceSet` bootstrap (~500 LOC additive, shadow mode, zero production impact). Read there for exact file list + acceptance tests.

---

## 10. Dependency graph

Canonical dependency graph in **[`ROADMAP.md §2`](ROADMAP.md)** — includes Phase G post-v2.1 patch.

---

## 11. Why this plan is itself idempotent, reversible, diagonalizable

- **Idempotent:** re-reading the plan yields the same sequence. Every migration has `down_revision`. Every backfill unique-constrained.
- **Reversible:** each phase has named rollback (flag, migration down, git revert).
- **Diagonalizable:** phases do not cross modes mid-stream. E is the only cross-mode phase and comes last.
- **Self-adjoint:** acceptance signal for each phase uses vocabulary of the property it closes.
- **Surjective:** every CRITICAL/HIGH gap in GAP_ANALYSIS_v2 is addressed by ≥ 1 phase. Table §1 maps.
- **Causal:** the plan writes to structures it builds — `EvidenceSet` captures this plan's own evidence; `CausalEdge` would link this plan ADR to its implementation decisions.

---

## 12. Divergences from v1 (explicit)

| v1 | v2 | Why |
|---|---|---|
| "BlastRadiusEstimator" as closure | "ImpactClosure" (closure) + BlastRadiusEstimator (review-cost hint over closure) | Engineer Soundness §4 demands closure, not estimate |
| Rule registration without adapter spec | Explicit `RuleAdapter` protocol in phase A | Existing validator signatures incompatible with `Rule(artifact, evidence) → Verdict` |
| "30+ status sites" | 75 sites (9 files) | Verified count |
| "5.5 Causal Memory ABSENT" | "P14 PARTIAL with 10 FK sources" | FK-based relations already persisted, just unnormalized |
| No phase for uncertainty blocking | Phase F | user §3 satisfaction criterion requires BLOCKED state |
| No phase for disclosure protocol | Phase F | CONTRACT §B five templates must be structured, not prose |
| No phase for verification independence | Phase F (uses existing `forge_challenge`) | CONTRACT §B.8 solo-verifier rule |
| No phase for root-cause uniqueness | Phase F | Engineer Soundness §3 |
| No phase for invariant preservation | Phase E (added sub-scope) | Engineer Soundness §5 |
| Backfill from `Decision.blocked_by_decisions` | Removed — does not exist | Verified against decision.py |
| Backfill from `Finding.source_execution_id` | Corrected to `Finding.execution_id` | Verified against finding.py |
| Refactor services/ without impact sub-plan | Impact sub-plan required via phase C's `ImpactClosure` | ~200 import sites estimated, needs closure before refactor |

Everything else from v1 retained.

---

## 13. Phase G — CGAID Compliance *(added in patch v2.1, 2026-04-22)*

### 13.1 Goal

Align Forge v2 with its parent framework CGAID (`ITRP/.ai/framework/`). v2 implicitly implemented MANIFEST principles through consolidation with CONTRACT.md + two theorems, but **eight CGAID-specific gaps** are unaddressed (see `GAP_ANALYSIS_v2 §8.3`). Phase G is the capstone — after it, Forge is a declared CGAID reference implementation with traceable binding for every MANIFEST principle, every operating-model artifact, every metric.

### 13.2 Dependencies

Phase G is **last** — depends on A (VerdictEngine for G2), B (CausalEdge for G3 metric collection), C (SideEffectRegistry for G8 artifact #11), E (ContractSchema for G6 mapping, Invariant for G4 rule lifecycle, modes refactor for G8 layer labeling), F (disclosure protocol structured for G2 violation classification).

Duration: **3 sprints**.

### 13.3 Scope

#### G1 — Stage 0 Data Classification Gate (CGAID OM §2 + DATA_CLASSIFICATION.md)

- `DataClassification(id, artifact_ref, artifact_type, tier ∈ {PUBLIC, INTERNAL, CONFIDENTIAL, SECRET}, classified_by, classified_at, rationale, dpa_ref, provenance_marker, expires_at)` entity.
- 11-field log per row (fields verbatim from DATA_CLASSIFICATION.md template — decision required on final field list).
- **Pre-ingest gate**: no `Knowledge`, `Decision.reasoning` with external quote, or ad-hoc upload enters platform without a `DataClassification` row.
- **Routing matrix config** per tier × capability (which model processes which class). Stored as `data_routing_matrix.yaml` in platform config.
- **Steward sign-off for Confidential+** (reuses G5 role).
- **Provenance marker propagation**: Confidential+ tier flag cascades through `CausalEdge` — a downstream `EvidenceSet` derived from Confidential source inherits the tier.
- **Honesty note (per OM §2) — ESCALATED by deep-risk R-FW-02 composite 19 CRITICAL (IRREVERSIBLE blast radius)**: this is a *policy gate* enforced by config + discipline. Technical enforcement (DLP, egress proxy) is out of scope unless deploying org ships that infrastructure. OM §2 explicitly states any engineer can bypass via copy-paste/screenshot/ad-hoc upload. A Confidential leak via that path is IRREVERSIBLE — client data in vendor training corpus cannot be unleaked.
  - **Mandatory for adoption:** before any Forge deployment processes Confidential+ material, adopting organization must either (a) deploy DLP / egress proxy / restricted AI connectors, or (b) record signed acceptance that Forge is certified only for Public/Internal tier until DLP adopted.
  - **Forge UI** (Phase G1 deliverable) must show a persistent banner on Confidential+ ingest UI: *"Policy-gate only. No technical enforcement. If your organization has not deployed DLP, do not upload Confidential material. See ADR-TBD (adoption posture)."*
  - **Steward audit** (G5 quarterly) MUST report count of Confidential+ ingests per adopting org and flag any without DLP record.
  - **Kill-criteria candidate:** if ≥1 Confidential leak occurs via Forge during adoption, Forge is pulled from Confidential-processing capability per OM §12 kill-criteria until remediated.

#### G2 — Contract Violation Log (enables OM §5 Metric 4)

- `ContractViolation(id, execution_id, behavior_code ∈ {A1..A7}, template_missing ∈ {B1..B5, null}, disclosed ∈ {True, False}, detected_at, detected_by ∈ {validator, challenger, finding_triage, reviewer, steward_audit}, severity, remediation_finding_id)`.
- **Auto-populated**: every REJECT from phase-F validators (P19, P20, P22, P24) writes a row. Challenge failures write rows. Steward-audit findings write rows.
- **Enables OM §5 Metric 4**: `count(disclosed=True) / count(total)` — the key signal for "is the contract effective".
- Exposed via `GET /projects/{slug}/contract-violations` with filters.

#### G3 — 7 Metrics Collection Service (OM §5)

`app/services/metrics_service.py` with 7 collectors, each named per OM §5:

| Metric | Collector | Source | Measurable day 1? |
|---|---|---|---|
| M1 Inconsistencies caught pre-code | `count_evidence_pack_items(project, stage1_window)` | `EvidenceSet` + `Finding` with `kind=inconsistency` | YES after G6 |
| M2 Decisions surfaced in planning vs production | `ratio_decisions_planned_vs_emergent(project)` | `Decision.created_at` vs `Task.completed_at` | YES |
| M3 Edge cases caught in planning vs production | `ratio_edge_cases_planned_vs_prod(project)` | pre-impl AC count with `scenario_type='edge_case'` vs post-impl `Finding` count tagged failure_mode | YES |
| M4 Contract violations disclosed vs detected | `contract_violations_ratio(project)` | G2 log | YES after G2 |
| M5 Skill change outcome delta | `skill_change_outcome(skill_id, window=30d)` | `MicroSkill` version history + 30-day defect/rework rate | YES — `skill_log_exporter.py` exists |
| M6 Time from merge to business verification | `merge_to_verification_time(task)` | `Task.completed_at` → `KeyResult.achieved_at` | YES after G6 BL-DoD field |
| M7 PR review cycle time | `pr_review_cycle_time(window)` | `github_pr` service timestamps | YES — `github_pr.py` exists |

- Scheduled runs: daily (M2, M3, M4, M7); weekly (M5, M6, M1 aggregation).
- Endpoint `GET /projects/{slug}/metrics` returns last snapshot.
- Quarterly aggregate → Steward audit report (see G5).
- **Per OM §5 honesty**: Metric 4 was aspirational pre-G2; others measurable day 1.

#### G4 — Rule Lifecycle (OM §4.3)

- `Rule(id, code, source ∈ {contract, standards, skill, checklist, guideline, validator}, created_at, prevents_scenario, last_evidence_of_prevention, retired_at, retirement_reason)`.
- **Auto-population** from existing `MicroSkill`, `Guideline`, `contract_validator` rule set. One-time migration.
- **Quarterly review endpoint**: `GET /projects/{slug}/rules/review` returns rules with no evidence of prevention in last 12 months (retirement candidates) + rules referenced in recent Findings (load-bearing confirmation).
- **Retirement workflow**: `POST /rules/{id}/retire` with rationale; archived to `archive/retired_rules.md`.
- **Runtime-incident → rule** (OM §4.3 v1.5): production `Finding` with `severity ≥ HIGH` auto-proposes a rule candidate when it reveals a coverage gap in Stage 1/2/3. Steward confirms promotion.

#### G5 — Framework Steward Role

- Extend `User` with `steward_role ∈ {None, Steward, Lead}` + `steward_rotation_start_at`, `steward_rotation_end_at`.
- **Three rotating Stewards** with Lead (per OM §12 governance). Rotation period: calibration decision (default 6 months).
- `AuditLog.reviewed_by_steward_id` (nullable).
- `Decision.steward_sign_off_by_id` + `signed_at` — required for `ceremony_level in {STANDARD, FULL}` with `severity in {HIGH, CRITICAL}` (mapping to CGAID Critical tier).
- `Finding.steward_escalated_to_id` for tier escalations.
- **Quarterly audit report generator**: `GET /projects/{slug}/audit/quarterly` produces report per OM §4.5 (validates CONTRACT still satisfies §4.4 clauses 1–8).

#### G6 — 11 Artifacts Mapping (OM §3)

Separate document `platform/docs/FRAMEWORK_MAPPING.md` records the 1:1 binding. Per-artifact build-work:

| # | CGAID Artifact | Forge Entity | Build work in G6 |
|---|---|---|---|
| 1 | Evidence Pack | `EvidenceSet` (phase A) + curated `Finding` + `Knowledge` inconsistencies | Aggregation view / endpoint `GET /projects/{slug}/evidence-pack?stage=1` |
| 2 | Master Plan (Cockpit) | `Objective` + `KeyResult` | expose rendered view matching CGAID template |
| 3 | Execution Plan | `Task` graph (DAG via `task_dependencies`) | add `plan_exporter.py` variant for CGAID format (service exists, just format alignment) |
| 4 | Handoff Document | `handoff_exporter.py` output | **exists** — verify CGAID-required fields present |
| 5 | ADRs | `Decision` with `type='adr'` | add explicit `type='adr'` seed; add `adr_exporter.py` variant (exists) |
| 6 | Edge-Case Test Plan | `AcceptanceCriterion` with `scenario_type` | aggregation view per task |
| 7 | Business-Level DoD | NEW field `Objective.business_dod` JSONB | migration; rendered in Master Plan |
| 8 | Skill Change Log | `MicroSkill` version + `skill_log_exporter.py` | **exists** — verify CGAID format |
| 9 | Framework Manifest & Changelog | `platform/docs/FRAMEWORK_MAPPING.md` + `FORMAL_PROPERTIES_v2.md` + `README.md` | this doc set |
| 10 | Data Classification Rubric | G1 entity + `data_classification_rubric.md` | done by G1 |
| 11 | Side-Effect Map | Phase C `SideEffectRegistry` + per-task view | aggregation view per task; tie-in with `ImpactClosure` output |

#### G7 — Adaptive Rigor alignment (OM §7)

- Forge has `Task.ceremony_level ∈ {LIGHT, STANDARD, FULL}` (3 levels — verified `execute.py:53-60` `_determine_ceremony`, `seed_data.py:21,29,57,85`). Earlier drafts of this plan claimed 4 levels including `MINIMAL`; that came from the outer `forge/.claude/CLAUDE.md` which describes the legacy `core/` pipeline, not `platform/`. Correction documented in [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md).
- CGAID has `Fast Track / Standard / Critical` (3 tiers).
- **Calibration decision CLOSED** per [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md): **1:1 mapping `{LIGHT → Fast Track, STANDARD → Standard, FULL → Critical}`**.
- Per-tier artifact requirements (OM §7.1 table) encoded in `output_contracts` seed data. Forge `output_contracts` table exists; just align seed to CGAID requirements.
- **Fast Track preconditions** (OM §7.2 — 4 conditions all must hold) encoded as validator rule on tier classification.
- **Tier escalation triggers** (OM §7.4) as validator rules that propose escalation during delivery.
- **Emergency Response Pattern** (OM §7.5) — not in G7 scope (orthogonal operational capability, defer to later decision).

#### G8 — Deterministic Snapshot Validation (OM §9.4)

- `app/validation/snapshot_validator.py` implementing the 5-component reference pattern:
  1. `BaselineArtifact` — versioned, checksummed, stored.
  2. `CaptureProcedure` — reproducible capture command recorded.
  3. `SnapshotComparator` — byte-exact or field-exact comparator.
  4. `FailureContract` — what a mismatch means (REJECTED vs WARNING).
  5. `RefreshPolicy` — when baselines are re-validated (rolling window, manual sign-off).
- Applied to: Stage 1 volume check (row-count fingerprint), Stage 3 output shape match, Stage 4 business-outcome signature.
- Reusable per-task via `TaskGate(snapshot_ref=...)`.

### 13.4 Exit gate

All eight must hold:

- **G1.** Any new `Knowledge` / `Decision.reasoning` with external quote has a `DataClassification` row before ACCEPTED.
- **G2.** Every phase-F REJECT produces a `ContractViolation` row.
- **G3.** 7 metrics collected; dashboard live; weekly snapshot written.
- **G4.** Rule review report produced on first quarterly run; at least one retirement candidate identified.
- **G5.** Every `Decision` with `ceremony_level in {STANDARD, FULL}` and `severity ≥ HIGH` has `steward_sign_off_by_id`.
- **G6.** `FRAMEWORK_MAPPING.md` lists all 11 CGAID artifacts with pointer to Forge entity; every artifact either exists or has `status=ACKNOWLEDGED_GAP`.
- **G7.** Ceremony-level ↔ CGAID-tier mapping encoded; output_contracts seed aligned.
- **G8.** At least 3 gates use snapshot validation (Stage 1 volume check, Stage 3 output shape, Stage 4 business-outcome).

### 13.5 Reversal

- G1: flag `STAGE0_ENFORCEMENT ∈ {off, log_only, enforce}` — can stay in log-only indefinitely while routing matrix is refined.
- G2: tables are additive; drop via migration down.
- G3: collectors are read-only; disabling zeroes dashboard but no state damage.
- G4: `Rule` table is log-only initially; enforcement incremental.
- G5: Steward role columns nullable; default null is permissive.
- G6: documentation; no reversal needed.
- G7: mapping is config; reverting reverts to Forge-native ceremony vocabulary.
- G8: snapshot gates per-task opt-in.

### 13.6 Calibration decisions required

| Decision | Default proposal | Status | Who decides |
|---|---|---|---|
| 11-field Stage 0 log columns | per DATA_CLASSIFICATION.md verbatim | OPEN | governance |
| Data routing matrix per tier × capability | conservative (Confidential → zero-retention tier only) | OPEN | governance + security |
| Steward rotation period | 6 months | OPEN | governance |
| `scenario_type` enum extension | 9 values `{positive, negative, edge_case, boundary, concurrent, malformed, regression, performance, security}` | **CLOSED** — [ADR-001](decisions/ADR-001-scenario-type-enum-extension.md) | user 2026-04-22 |
| Ceremony ↔ CGAID tier mapping | 1:1 `{LIGHT→Fast, STANDARD→Standard, FULL→Critical}` | **CLOSED** — [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md) | user 2026-04-22 (premise corrected) |
| Rule retirement evidence window | 12 months (per OM §4.3) | OPEN | governance |
| Snapshot refresh policy per gate class | per-gate; default 90 days | OPEN | per capability |

### 13.7 Why Phase G is separate, not merged into E

Alternative considered: fold G content into E (modes refactor + invariants). Rejected because:
- **Diagonalizability violated.** E is structural (rearrange code). G is compliance (add framework-specific tables + services). Mixing modes.
- **Dependency direction.** G needs E's `ContractSchema` + `Invariant` entities. Cannot parallelize.
- **Calibration weight.** G requires multiple governance decisions (routing matrix, Steward rotation, retirement policy) that belong in their own phase gate.

So G is the last phase. Its exit is Forge's CGAID compliance acceptance.

### 13.8 Dependency graph

Canonical dependency graph (including Phase G) in **[`ROADMAP.md §2`](ROADMAP.md)**.

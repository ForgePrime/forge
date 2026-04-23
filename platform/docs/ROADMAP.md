# Forge Platform — Unified Roadmap

> **Status:** DRAFT per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Pending distinct-actor peer review; not binding until NORMATIVE.

**Date:** 2026-04-23
**Supersedes:** executive layer of [`CHANGE_PLAN_v2.md`](CHANGE_PLAN_v2.md) (CHANGE_PLAN retains phase rationale + alternatives + blast-radius detail; this doc is the **operational plan** with stages + tests per phase).
**Scope:** `platform/` only.

---

## 0. Intent

This is the **single operational plan** for bringing Forge from current DRAFT spec to NORMATIVE + implemented. It consolidates:

- 7 phases (A → G) from `CHANGE_PLAN_v2.md §1`
- 25 atomic properties from `FORMAL_PROPERTIES_v2.md §3`
- 29 risks from `DEEP_RISK_REGISTER.md`
- 3 closed ADRs + calibration ADRs pending

Each phase decomposes into **stages** (sub-milestones) with explicit **entry tests** (what must be green before the stage starts) and **exit tests** (what must be green before the stage closes). A phase cannot advance until all stage exit tests pass.

Test strategy per phase: combination of (a) existing pytest suite regression, (b) property-based tests (phase D adds `hypothesis`), (c) metamorphic tests, (d) adversarial fixtures from `Finding` regression set, (e) deterministic replay harness.

---

## 1. Phase overview

| Phase | Goal | Stages | Duration | Closes properties / theorem conditions | Depends on |
|---|---|---|---|---|---|
| **Pre-flight** | ADR-003 ratification, calibration ADRs, smoke tests | 3 | 1 sprint | — | — |
| **A** | Deterministic gate fundament: VerdictEngine + GateRegistry + EvidenceSet + idempotency | 5 | 2–3 sprints | P1, P6, P7, P8, P16; CCEGAP 5, 6 | Pre-flight |
| **B** | Causal memory + context projection + timely delivery + topology preservation | 6 | 3–4 sprints | P14, P15, partial P4; CCEGAP 1, 3; **ECITP C3, C6** | A |
| **C** | Impact Closure + Reversibility | 4 | 2–3 sprints | P3, P5, P2 | A |
| **D** | Failure-oriented testing + risk-weighted coverage | 5 | 2–3 sprints | P10, P18 (replay), P25; CCEGAP 5 strengthened | A, B |
| **E** | Self-adjoint contract + diagonalization + invariants + continuous autonomy + additive progression | 7 | 3–4 sprints | P4, P9, P11, P12, P13; CCEGAP 2; **ECITP C8** | A, B, C, D |
| **F** | Decision discipline (disclosure, uncertainty blocks, root cause, transitive) + structured transfer | 10 | 3–4 sprints | P17, P18, P19, P20, P21, P22, P23, P24; CCEGAP 4, 7; **ECITP C11** | A, B |
| **G** | CGAID compliance capstone: Stage 0, metrics, Rule Lifecycle, Steward, 11 artifacts + proof trail | 9 | 3–4 sprints | — (closes CGAID alignment); **ECITP C7, C12** | E, F |

**Calendar estimate:** 20–26 sprints (~5–6 months at one-sprint-per-week) — realistic calendar: 7–11 months with overhead. **This is NOT a commitment** — it's a capacity estimate subject to R-OP-01 (composite 12 MEDIUM). Revised upward from 17–22 sprints to account for 5 new ECITP-driven stages (B.5, B.6, E.7, F.10, G.9).

---

## 2. Dependency graph

```
                      ┌── B (causal memory) ────┐
                      │                         │
Pre-flight ─── A ─────┼── C (impact + reverse) ─┼── E (contract + diagonal)
                      │                         │              │
                      └── D (failure tests) ────┘              ▼
                              ▲                              G (CGAID
                              │                              compliance)
                              │                                ▲
                              └── F (decision discipline) ─────┘
                                    ▲
Pre-flight ─── A ─── B ─────────────┘
```

- B, C, D parallel after A.
- F parallel after A+B.
- E after A+B+C+D.
- G last.

---

## 3. Pre-flight (prerequisites to any Phase A PR)

### Stage 0.1 — Ratify ADR-003

**Entry tests:**
- ADR-003 exists and is readable (`docs/decisions/ADR-003-human-reviewer-normative-transition.md`).

**Exit tests:**
- [ ] Review record filed in `docs/reviews/review-ADR-003-by-<actor>-<date>.md` per [`reviews/_template.md`](reviews/_template.md).
- [ ] ADR-003 status transitions OPEN → RATIFIED.
- [ ] `docs/decisions/README.md` index updated.

**Risk:** R-GOV-01 unmitigated if ratification never happens → ALL downstream work is on unverified foundation. **This is the #1 blocking step.**

### Stage 0.2 — Calibration ADRs

**Entry tests:**
- ADR-003 RATIFIED (Stage 0.1).

**Exit tests:**
- [ ] ADR-004 `calibration constants` — sets W (rolling window for $Q_n$), q_min (autonomy floors, 4 values per level), τ (risk bound), α per capability, idempotency TTL, acyclicity clock-skew tolerance, impact-closure review-cost threshold. Decision CLOSED.
- [ ] ADR-005 `Invariant.check_fn format` — Python callable vs DSL. Decision CLOSED.
- [ ] ADR-006 `Model version pinning policy` — which models, how updated, canary eval frequency (R-SPEC-05 mitigation).
- [ ] At least one distinct-actor review per ADR (ADRs 4–6 content review).

**Risk:** R-SPEC-01 (composite 14) — phase A cannot exit without these constants.

### Stage 0.3 — Smoke-test IMPLEMENTATION_TRACKER claims

**Entry tests:** Forge platform running on port 8012 (or test port).

**Exit tests:**
- [ ] HTTP calls against every `[EXECUTED]` claim in `platform/IMPLEMENTATION_TRACKER.md`. Results compared to tracker evidence.
- [ ] Any divergence opens a `Finding` in Forge + patch note in `GAP_ANALYSIS_v2.md`.
- [ ] `[ASSUMED]` tag on IMPLEMENTATION_TRACKER claims in GAP_ANALYSIS_v2 either removed (verified) or reclassified (diverged).

**Risk:** R-GAP-02 (composite 15 HIGH) — v2 gap analysis partially rests on self-reported claims; must be independently verified before Phase A binds on them.

---

## 4. Phase A — Deterministic gate fundament

**Goal:** every state transition through one gate; every verdict a function; every mutating MCP call idempotent; every Decision has an EvidenceSet.

### Stage A.1 — EvidenceSet entity (DB foundation)

**Entry tests:**
- Pre-flight complete.
- Alembic working (`uv run alembic current` green).

**Stage tests:**
- [ ] Migration up/down round-trips cleanly.
- [ ] `evidence_sets` table exists with columns per CHANGE_PLAN_v2 §2.2.1 + ADR-001 enum.
- [ ] Pytest: `tests/test_evidence_set_model.py` — insert, query, delete.

**Exit tests:**
- [ ] Existing 420 tests still green.
- [ ] `Decision.insert` trigger/gate rejects when no EvidenceSet link (P16 invariant).

### Stage A.2 — GateRegistry (static, in-memory)

**Entry:** A.1 complete.

**Stage tests:**
- [ ] `app/validation/gate_registry.py` enumerates all transitions for 6 entities (Execution, Task, Decision, Finding, KeyResult, OrchestrateRun). Count matches existing CheckConstraints.
- [ ] Registry is a pure dict, no DB calls.

**Exit:** Registry is referenced-only (no enforcement yet). Pytest: registry integrity test (every current valid transition is registered).

### Stage A.3 — VerdictEngine in shadow mode

**Entry:** A.1, A.2 complete.

**Stage tests:**
- [ ] `VerdictEngine.evaluate(artifact, evidence, rules) → Verdict` is pure (no wall-clock, no rand, no network).
- [ ] `RuleAdapter` wraps existing `plan_gate` + `contract_validator` without rewriting them.
- [ ] Replay harness: on 100 historical executions, engine verdict matches current behavior (no divergence in shadow).

**Exit:** `VERDICT_ENGINE_MODE=shadow` flag on; `verdict_divergences` table logs anything unexpected. **One week of production traffic with zero divergence** before next stage.

### Stage A.4 — Enforcement cutover

**Entry:** A.3 with zero divergence in shadow over 1 week.

**Stage tests:**
- [ ] Flag flipped to `enforce`.
- [ ] All 75 direct `.status = "..."` sites wrapped through `VerdictEngine.commit()`.
- [ ] Pre-commit grep rejects any new direct `\.status\s*=\s*['"]` outside `VerdictEngine`.

**Exit:** `grep` invariant returns zero matches outside engine file. Canary 48h green.

### Stage A.5 — MCP idempotency

**Entry:** A.4 complete (independent of it, but test dep on VerdictEngine).

**Stage tests:**
- [ ] `idempotent_calls` table migration.
- [ ] Middleware short-circuits duplicate `(tool, key, args_hash)` within TTL (per ADR-004 TTL).
- [ ] Integration test: two identical `forge_deliver(idempotency_key=X)` within TTL → one row, one result.

**Exit:** All 4 mutating MCP tools accept `idempotency_key`. Test green.

### Phase A exit gate (all must hold)

- [ ] Replay determinism: 100 executions, bit-identical verdicts.
- [ ] Zero direct transitions: `grep '\.status\s*=\s*['"]'` outside engine = 0.
- [ ] Idempotency: canonical fixture two-call test green.
- [ ] Every `Decision` has ≥ 1 `EvidenceSet` link (DB query invariant).
- [ ] Existing 420 tests green. New tests for A.1–A.5 green.
- [ ] Shadow divergence log reviewed by distinct actor.

---

## 5. Phase B — Causal memory + context projection

**Goal:** history is a DAG; prompt context is a projection of minimal justification frontier.

### Stage B.1 — CausalEdge table + acyclicity trigger

**Entry:** Phase A exit.

**Stage tests:**
- [ ] Table + unique constraint + `src.created_at < dst.created_at` trigger.
- [ ] Property test (`hypothesis`): random edge inserts never produce a cycle.

### Stage B.2 — Idempotent backfill

**Entry:** B.1.

**Stage tests:**
- [ ] Backfill script runs twice: no duplicate rows.
- [ ] Every current FK (10 known relations per ADR-002 corrections applied to GAP_ANALYSIS_v2 §P14) produces edges.
- [ ] Backfill review: Steward (or distinct actor) spot-checks 20 random edges for relation-type correctness.

### Stage B.3 — CausalGraph service

**Entry:** B.2.

**Stage tests:**
- [ ] `ancestors(node, depth, relation_filter)` returns a DAG subset.
- [ ] `minimal_justification(node)` returns shortest path.
- [ ] Pure Python over the table; no side effects.

### Stage B.4 — ContextProjector + prompt assembly integration

**Entry:** B.3.

**Stage tests:**
- [ ] `ContextProjector.project(task, budget)` respects budget for 10 canonical fixtures.
- [ ] For 10 historical executions, projection contains every decision the reasoning referenced (spot-check).
- [ ] **Evidence continuity property test (ECITP §2.3):** hypothesis-based — for 10,000 random DAG+task pairs, every decision-relevant ancestor edge appears in `ContextProjection`; zero false-negatives allowed.
- [ ] Persisted in `context_projections` table for audit.

**Exit:** `CAUSAL_PROJECTION=on` behind flag; `prompt_parser` uses projector.

### Stage B.5 — TimelyDeliveryGate (ECITP C3)

**Entry:** B.4. Full REJECT mode requires G_{E.1}.

**Stage tests:**
- [ ] `Execution.context_projection_id IS NULL` at pending→IN_PROGRESS transition → blocked (REJECT mode).
- [ ] Projection missing any `ContractSchema.required_context(task)` field → blocked.
- [ ] Env flag `TIMELY_DELIVERY_MODE=WARN` emits Finding; `=REJECT` blocks transition.
- [ ] `grep -nE "session_context|raw_prompt_fallback" app/prompt_parser.py` exits 1 (no fallback path).

**Exit:** TimelyDeliveryGate live; WARN-to-REJECT promotion auto-triggered at G_{E.1}.

### Stage B.6 — SemanticRelationTypes on CausalEdge (ECITP C6)

**Entry:** B.2.

**Stage tests:**
- [ ] Alembic migration round-trip (adds `causal_edges.relation_semantic ENUM`).
- [ ] `scripts/backfill_relation_semantic.py` deterministic (idempotent on re-run).
- [ ] Unmappable historical TEXT relation → Finding emitted, NULL retained (no silent default).
- [ ] `CausalGraph.requirements_of(ac) / risks_of(ac) / tests_of(ac)` return expected edges on fixture DAG.
- [ ] WARN-mode AC validator: AC without requirement AND risk edge → Finding emitted.

**Exit:** ENUM live; CausalGraph exposes relation-typed queries; REJECT-promotion handled at G.9.

### Phase B exit gate

- [ ] Every new `Decision | Change | Finding` insert has ≥ 1 edge OR `is_objective_root = true` (DB invariant test).
- [ ] No cycle detected in 10,000 random inserts (property test).
- [ ] Projection fidelity test green on 10 historical.
- [ ] Budget test green.
- [ ] TimelyDeliveryGate blocks IN_PROGRESS without materialized projection (B.5).
- [ ] `relation_semantic` ENUM populated for all backfilled edges; unmappable rows have Findings (B.6).

---

## 6. Phase C — Impact Closure + Reversibility

**Goal:** `Impact(Δ) = Closure(deps)` not estimate; every change classified; rollback possible where claimed.

### Stage C.1 — ImportGraph service

**Entry:** A exit (independent of B).

**Stage tests:**
- [ ] Static AST walk of `app/` produces reverse-dep graph.
- [ ] `reverse_deps(module) → Set[module]` transitive closure correct for fixture (known graph).
- [ ] Graph is cached; invalidated on any `app/*.py` change (file watcher or PR-gate).

### Stage C.2 — SideEffectRegistry + `@side_effect` decorator

**Entry:** C.1.

**Stage tests:**
- [ ] Tag ≥ 20 known side-effecting functions with `@side_effect(kind=...)` — sample: `audit_log.add`, `metrics_service` writes, external API calls.
- [ ] `callers_in_path(modules)` returns union of registered callers.
- [ ] Coverage report: % of functions that mutate state that are tagged.

### Stage C.3 — ImpactClosure

**Entry:** C.1 + C.2.

**Stage tests:**
- [ ] `ImpactClosure(change) → Set[File]` = union of ImportGraph reverse-deps + SideEffect callers + task_dependencies.
- [ ] Gate: delivery whose declared `modifying` files ⊄ ImpactClosure ∪ change.files → REJECTED.

### Stage C.4 — Reversibility class + Rollback service

**Entry:** C.3.

**Stage tests:**
- [ ] `Change.reversibility_class` + `rollback_ref` columns.
- [ ] `ReversibilityClassifier` heuristic: add-only → REVERSIBLE; DROP → IRREVERSIBLE; default → IRREVERSIBLE (fail-safe).
- [ ] Disaster drill: 5 historical REVERSIBLE changes round-trip via `Rollback.attempt` → byte-identical checksum.

### Phase C exit gate

- [ ] ImpactClosure correctness on canonical fixture.
- [ ] Plan stability: 1-line edit mutates ≤ 2 task IDs (snapshot test).
- [ ] Disaster drill green for REVERSIBLE class.

---

## 7. Phase D — Failure-oriented testing + coverage

**Goal:** tests maximize falsification, not nominal coverage. Risk-weighted `∑ w_m Cov(T, m) ≥ α` per capability.

### Stage D.1 — Deterministic test harness

**Entry:** A exit (other phases optional).

**Stage tests:**
- [ ] `tests/conftest.py` pins random seed.
- [ ] `freezegun` for frozen clocks.
- [ ] Hermetic DB fixture (docker-compose test profile).
- [ ] Three consecutive `pytest` runs: bit-identical output.

### Stage D.2 — Property tests (`tests/property/`)

**Entry:** D.1.

**Stage tests:**
- [ ] `test_verdict_determinism.py` (`hypothesis`): same `(artifact, evidence)` → same verdict. Test seeded, fuzzed.
- [ ] `test_causal_acyclicity.py`: random inserts, no cycle.
- [ ] `test_idempotent_call.py`: two calls with same key, no additional side effect.
- [ ] `test_reversibility_roundtrip.py`: REVERSIBLE changes round-trip.
- [ ] `test_invariant_preservation.py`: every `Invariant.check_fn` holds across its applicable transitions.

### Stage D.3 — Metamorphic tests (`tests/metamorphic/`)

**Entry:** D.1, D.2 for infrastructure.

**Stage tests:**
- [ ] `test_validator_paraphrase.py`: reasoning A vs A' paraphrase, same evidence → same verdict.
- [ ] `test_ac_permutation.py`: AC order doesn't change verdict.
- [ ] `test_evidence_permutation.py`: EvidenceSet order doesn't change verdict.

### Stage D.4 — Adversarial fixtures (`tests/adversarial/`)

**Entry:** D.3.

**Stage tests:**
- [ ] `build_adversarial_fixtures.py` reads historical `Finding` rows + `PRACTICE_SURVEY.md` incidents; emits regression cases.
- [ ] Each new `Finding` with `severity ≥ HIGH` auto-proposes an adversarial fixture for Steward review (Phase G4 rule lifecycle dep).

### Stage D.5 — FailureMode entity + RiskWeightedCoverage report

**Entry:** D.2–D.4 give data to weight.

**Stage tests:**
- [ ] `failure_modes` table migration.
- [ ] Seed from existing `kind='failure_mode'` AC scenarios (`objective.py:39`, `tier1.py:703`).
- [ ] `scripts/coverage_report.py` computes $\sum w_m \text{Cov}(T, m)$ per capability.
- [ ] CI gate: below α (per ADR-004) blocks merge.

### Phase D exit gate

- [ ] 3 consecutive runs bit-identical.
- [ ] Mutation smoke: remove any `VerdictEngine` rule → ≥ 1 test fails.
- [ ] Coverage ≥ α for ≥ 3 capabilities.
- [ ] Weekly evidence-verifiability replay job (partial P18) green on first run.

---

## 8. Phase E — Self-adjoint contract + diagonalization + invariants + autonomy

**Goal:** one contract governs both execution and validation; 6 diagonal modes; invariants registered; autonomy continuous with demotion.

### Stage E.1 — ContractSchema

**Entry:** Phase A, B, C, D exits.

**Stage tests:**
- [ ] Typed Pydantic model for `Task.produces`.
- [ ] `render_prompt_fragment()` + `validator_rules()` — both derived from one source.
- [ ] Mutation test: change a field → both outputs change; drift test fails otherwise.

### Stage E.2 — Invariant entity + VerdictEngine integration

**Entry:** E.1 + ADR-005 (Invariant.check_fn format).

**Stage tests:**
- [ ] `invariants` table + register interface.
- [ ] `VerdictEngine.commit()` evaluates applicable invariants post-transition.
- [ ] Synthetic violation test: each registered invariant has ≥ 1 transition that would violate it, blocked by gate.

### Stage E.3 — Autonomy ledger + demote

**Entry:** E.2.

**Stage tests:**
- [ ] `autonomy_states` table.
- [ ] `demote()` function triggered on any `Q_n` component below floor (ADR-004 q_min values).
- [ ] L1–L5 retained as labels; internal state continuous.
- [ ] Regression drill: inject failures → scope demotes within one run.

### Stage E.4 — ReachabilityCheck

**Entry:** A exit.

**Stage tests:**
- [ ] Pre-`Objective ACTIVE` gate: ≥ 1 plan template or generator satisfies each KR.
- [ ] Evidence in `Objective.reachability_evidence` JSONB non-empty.

### Stage E.5 — Services → modes refactor

**Entry:** E.1–E.4 + ImpactClosure (C.3) for impact sub-plan.

**Stage tests:**
- [ ] Compute impact per file pre-move (ImpactClosure).
- [ ] Mechanical `git mv` preserving blame.
- [ ] Re-export shims in `app/services/` for one release.
- [ ] Typed Pydantic DTOs at mode boundaries.

### Stage E.6 — Per-mode contract tests + stub-replacement drill

**Entry:** E.5.

**Stage tests:**
- [ ] Each mode has `tests/{mode}/contract/`.
- [ ] Stubbing `execution/` module → `validation/` tests still green.

### Stage E.7 — EpistemicProgressGate (ECITP C8 + §2.7 explicit invalidation)

**Entry:** E.1 + E.2 + F.3.

**Stage tests:**
- [ ] Alembic migration (`executions.epistemic_snapshot_before`, `executions.epistemic_delta`, `executions.invalidated_evidence_refs`).
- [ ] Execution with zero deltas from {new_evidence, reduced_ambiguity, new_failure_mode, narrowed_scope, tightened_schema, new_ac_with_source} → REJECTED with reason=`epistemically_null_stage`.
- [ ] Execution with only Δ1 (new EvidenceSet) → PASS (single delta sufficient per ECITP C8).
- [ ] Paraphrase-only Decision (no new Evidence, same uncertainty, same schema) → REJECTED.
- [ ] Baseline snapshot captured at pending→IN_PROGRESS transition (integrates with B.5).
- [ ] **Explicit invalidation test (ECITP §2.7):** silent drop of prior `E_old` → REJECTED with reason=`silent_invalidation_violation_§2.7`; drop with valid `{evidence_set_id, reason_code}` entry in `invalidated_evidence_refs` → PASS. Valid reason_codes: `{superseded_by_newer, retracted_at_source, rejected_by_independent_check, made_obsolete_by_decision}`.

### Phase E exit gate

- [ ] Invariants live + violation test green.
- [ ] Contract self-adjoint: mutation lockstep.
- [ ] Autonomy demotes on injected regression.
- [ ] Reachability invariant: every ACTIVE Objective has non-null evidence.
- [ ] Diagonalization: stub drill green.
- [ ] EpistemicProgressCheck rejects null stages (E.7).

---

## 9. Phase F — Decision discipline

**Goal:** CONTRACT §A + §B + Evidence-Only Decision Model enforced structurally.

### Stage F.1 — Evidence source constraint (P17)

- [ ] `EvidenceSet.kind` enum validated (from ADR-001 enum).
- [ ] Schema constraint rejects `kind='assumption'`.

### Stage F.2 — Evidence verifiability (P18)

- [ ] `EvidenceSet.reproducer_ref` mandatory for test_output / command_output.
- [ ] `checksum_at_capture` mandatory for file_citation / code_reference.
- [ ] Weekly replay job (from Phase D).

### Stage F.3 — Assumption control enforcement (P19)

- [ ] Non-trivial classifier (7 triggers from CONTRACT).
- [ ] Validator rejects non-trivial claims without tag.
- [ ] Promote existing 3 WARNINGs to FAIL.

### Stage F.4 — Uncertainty blocks execution (P20) + Ambiguity continuity (ECITP §2.4)

- [ ] `BLOCKED` added to `Execution.status` enum (migration up/down).
- [ ] `Execution.uncertainty_state` JSONB.
- [ ] `POST /executions/{id}/resolve-uncertainty` endpoint.
- [ ] Synthetic test: non-empty `uncertain` → BLOCKED; cannot ACCEPTED until resolved.
- [ ] `resolved_uncertainty(ambiguity_id, execution_id, resolved_by, accepted_role, resolved_at)` durable resolution-record table (migration up/down).
- [ ] **Ambiguity continuity property test (ECITP §2.4):** hypothesis-based — for 10,000 random execution chains (length 2..5), every unresolved UNKNOWN at step n persists in uncertainty_state of step n+1 unless matching `resolved_uncertainty` row exists with `execution_id ≥ n`.

### Stage F.5 — Root cause uniqueness (P21) + Disclosure protocol (P22)

- [ ] `Decision.type in {"root_cause", "diagnosis"}` requires ≥ 2 alternatives with explicit rejection.
- [ ] 5 structured delivery sub-fields (CONTRACT §B1–B5) validated.
- [ ] 7 disclosure-behavior validator rules (CONTRACT §A1–A7).

### Stage F.6 — Verification independence (P23) + Transitive accountability (P24)

- [ ] ACCEPTED requires deterministic AC check OR `forge_challenge` pass.
- [ ] Subagent-downgrade validator (regex pattern detect parent-copied child CONFIRMED).

### Stage F.7 — AgentAuthorityCheck gate (SR-1)

> Source: [`AUTONOMOUS_AGENT_FAILURE_MODES.md §8 SR-1`](AUTONOMOUS_AGENT_FAILURE_MODES.md#sr-1-agentauthoritycheck-gate-pre-phase)

**Entry:** F.6 complete.

**Stage tests:**
- [ ] `AgentAuthorityCheck(phase) → {authorized, missing_premises}` implemented as first gate in every phase entry.
- [ ] Gate rejects phase start when: calibration ADRs not CLOSED, Steward not staffed (for CRITICAL decisions), any UNKNOWN in phase prerequisites.
- [ ] Synthetic test: phase A entry with ADR-004 open → BLOCKED.
- [ ] Synthetic test: CRITICAL Decision without Steward → BLOCKED.

**Closes:** failure modes §1.1 (calibration undefined), §1.2 (Steward authority gap), §1.4 (UNKNOWN escalation with no receiver).

### Stage F.8 — Skip-cost structural enforcement (SR-2)

> Source: [`AUTONOMOUS_AGENT_FAILURE_MODES.md §8 SR-2`](AUTONOMOUS_AGENT_FAILURE_MODES.md#sr-2-skip-cost-enforcement)

**Entry:** F.7 complete.

**Stage tests:**
- [ ] VerdictEngine delivery validator enforces: every governance slot in delivery output is either filled or has an explicit SKIP BLOCK.
- [ ] SKIP BLOCK minimum length: justification must exceed `min_skip_justification_chars` (per ADR-004 calibration) — enforced structurally, not by convention.
- [ ] Synthetic test: delivery with empty slot (no fill, no SKIP) → REJECTED.
- [ ] Synthetic test: delivery with one-line SKIP → REJECTED if below minimum.

**Closes:** failure modes §7 Evidence_Constrained_Planning §3 (shortcut economics), §13 (self-check honesty).

### Stage F.9 — Distinct-actor spawn in autonomous loop (SR-3)

> Source: [`AUTONOMOUS_AGENT_FAILURE_MODES.md §8 SR-3`](AUTONOMOUS_AGENT_FAILURE_MODES.md#sr-3-distinct-actor-mandatory-for-rationale-ratification)

**Entry:** ADR-003 RATIFIED (Stage 0.1). F.6 complete.

**Stage tests:**
- [ ] Autonomous agent loop has a defined hook point: after producing rationale, before self-ratifying, must invoke `forge_challenge` (Phase F.6) or file an explicit deferral to a named actor.
- [ ] No delivery with `ACCEPTED` verdict can be produced by the same agent instance that produced the rationale in the same session — unless a deterministic AC check (not LLM review) is the gate.
- [ ] Synthetic test: agent produces plan + immediately marks it CONFIRMED → REJECTED without distinct-actor or deterministic check.
- [ ] ADR-012 drafted: non-trivial classifier edge cases (renaming private API field, Optional kwarg with default, retry count change).

**Closes:** R-GOV-01, CONTRACT §B.8, failure modes §3 (root cause uniqueness), §1 (deterministic evaluation), §8 (proof of correctness) in autonomous loop context.

### Stage F.10 — StructuredTransferGate (ECITP C11)

**Entry:** F.4 + B.5 + B.6.

**Stage tests:**
- [ ] `ContextProjection` pydantic model has 6 typed structural fields: `requirements: List[RequirementRef]`, `evidence_refs: List[EvidenceRef]`, `ambiguity_state: AmbiguityState`, `test_obligations: List[TestObligation]`, `dependency_relations: List[DependencyRelation]`, `hard_constraints: List[InvariantRef]`.
- [ ] NL-only projection (e.g. `requirements = "some text"`) → BLOCKED with `blocked_reason = "structured_transfer_incomplete"`.
- [ ] Missing required category when task schema demands it → BLOCKED.
- [ ] `grep -rnE "session_context|fallback.*projection|nl_only_prompt" app/` exits 1 (no fallback path).
- [ ] `grep -rnE "StructuredTransferIncomplete.*warn|log\.warning.*structured_transfer" app/` exits 1 (raise only, no warn).

**Closes:** ECITP C11 (downstream inheritance) + Lemma 3 (summary-only transfer destroys second-order constraints).

### Phase F exit gate

- [ ] Schema: insert `kind=assumption` → rejected.
- [ ] Replay job green (P18).
- [ ] Synthetic non-trivial-untagged-claim → REJECT.
- [ ] BLOCKED state test green.
- [ ] Root-cause with 1 alternative → REJECT.
- [ ] ACCEPTED without challenge/deterministic → blocked.
- [ ] AgentAuthorityCheck gate green (F.7).
- [ ] Skip-cost enforcement: empty slot → REJECTED (F.8).
- [ ] Distinct-actor spawn mechanism active; self-ratification → REJECTED (F.9).
- [ ] ADR-012 drafted and filed for review.
- [ ] StructuredTransferGate: NL-only projection → BLOCKED; grep-gates on fallback paths green (F.10).

---

## 10. Phase G — CGAID compliance

**Goal:** close framework-level gaps flagged in `FRAMEWORK_MAPPING.md §12`.

### Stage G.1 — Stage 0 Data Classification Gate

**Entry:** Phase A + F exits.

**Stage tests:**
- [ ] `DataClassification` entity migration.
- [ ] Pre-ingest gate on `Knowledge`, `Decision.reasoning` with external quote.
- [ ] Routing matrix config per tier × capability.
- [ ] UI banner on Confidential+ without DLP.
- [ ] Steward sign-off for Confidential+ (reuses G5).
- [ ] **R-FW-02 escalation:** kill-criteria trigger on ≥ 1 leak.

### Stage G.2 — Contract Violation Log

**Entry:** Phase F exit (needs validator rejections as input).

**Stage tests:**
- [ ] `ContractViolation` table.
- [ ] Phase F validators auto-populate log.
- [ ] Endpoint: `GET /projects/{slug}/contract-violations`.

### Stage G.3 — 7 Metrics Collection Service

**Entry:** G.2 (M4 depends on it) + B (causal memory for M1, M3).

**Stage tests:**
- [ ] `metrics_service.py` with 7 collectors.
- [ ] Scheduled runs (daily / weekly).
- [ ] Endpoint: `GET /projects/{slug}/metrics`.
- [ ] Quarterly aggregate → Steward audit report.

### Stage G.4 — Rule Lifecycle

**Entry:** Phase E (uses `Invariant` + rule definitions).

**Stage tests:**
- [ ] `Rule` entity + auto-populate from existing `MicroSkill`, `Guideline`, validator rules.
- [ ] `GET /projects/{slug}/rules/review` returns retirement candidates (no evidence of prevention in 12 months).
- [ ] Retirement workflow: proposal → Steward review → archive.
- [ ] OM §4.3 v1.5 runtime-incident → rule candidate auto-proposal.
- [ ] **Rule prevention tracking** (closes `AUTONOMOUS_AGENT_FAILURE_MODES.md §5.7`): every REJECTED delivery logs `{rule_id, rejection_reason}` to `rule_prevention_log` table. `GET /rules/review` uses this log to compute "evidence of prevention" — retirement only triggers when log is empty for that rule for 12 months. Without this tracking, retirement never fires and rulebook accumulates indefinitely.

### Stage G.5 — Framework Steward role

**Entry:** requires ADR-007 (Steward rotation for Forge project — who, how many, rotation period).

**Stage tests:**
- [ ] `User.steward_role` + rotation columns.
- [ ] `AuditLog.reviewed_by_steward`, `Decision.steward_sign_off_by` for Critical tier.
- [ ] Quarterly audit report generator.

### Stage G.6 — 11 Artifacts mapping

**Entry:** `FRAMEWORK_MAPPING.md §6` table.

**Stage tests:**
- [ ] Each of 11 artifacts either EXISTS with endpoint/view or has `status=ACKNOWLEDGED_GAP` documented.
- [ ] Side-Effect Map artifact (#11) linked to Phase C `SideEffectRegistry` output.
- [ ] Business-Level DoD field added to `Objective`.

### Stage G.7 — Adaptive Rigor alignment

**Entry:** ADR-002 (already CLOSED).

**Stage tests:**
- [ ] `app/services/adaptive_rigor.py` with CEREMONY_TO_CGAID_TIER mapping per ADR-002.
- [ ] Per-tier artifact requirements (OM §7.1) encoded in `output_contracts` seed.
- [ ] Fast Track preconditions validator (4 conditions OM §7.2).

### Stage G.8 — Deterministic Snapshot Validation

**Entry:** Phase D (uses snapshot pattern). ADR-TBD on 5 components (OM §9.4).

**Stage tests:**
- [ ] `app/validation/snapshot_validator.py` with 5 components.
- [ ] Applied to Stage 1 volume check, Stage 3 output shape, Stage 4 business-outcome.

### Stage G.9 — ProofTrailCompleteness + ECITP C6/C11 promotion (ECITP C12 + C7)

**Entry:** G.8 + B.6 + F.10 + E.7. Requires ADR-014 (Requirement entity) and ADR-015 (Test entity) CLOSED.

**Stage tests:**
- [ ] `scripts/proof_trail_audit.py` traverses `Change → Execution → AC → Test → Requirement → Task → Objective → Finding → Knowledge` for every `Change`; missing link → Finding(severity=HIGH, kind='proof_trail_gap').
- [ ] Synthetic gap test: Change with no linked Execution → script exits 1 + Finding emitted.
- [ ] Complete chain test: fixture with full 10-link chain → script exits 0.
- [ ] CLI: `forge audit proof-trail --change-id=<uuid>` works per-Change.
- [ ] `feature_flags.CAUSAL_RELATION_SEMANTIC_REJECT=true` — promotes B.6 AC validator from WARN to REJECT.
- [ ] `feature_flags.STRUCTURED_TRANSFER_REJECT=true` — promotes F.10 gate to REJECT (raise not warn).
- [ ] Bounded-revision test (ECITP C7): 10 minor-edit PR fixtures → `len(ImpactClosure) ≤ threshold` from ADR-004.
- [ ] Nightly cron job configured in `.github/workflows/` or equivalent.

**Closes:** ECITP C12 (end-to-end proof trail structurally auditable), ECITP C7 (continuity of meaning — bounded downstream revision).

### Phase G exit gate

- [ ] Every Confidential+ ingest has Classification row + (DLP record OR signed acceptance).
- [ ] 7 metrics live + first quarterly snapshot.
- [ ] Rule review report produced; ≥ 1 retirement candidate identified.
- [ ] Every HIGH/CRITICAL Decision has Steward sign-off.
- [ ] FRAMEWORK_MAPPING.md 11 artifacts 1:1 resolved (EXISTS or ACKNOWLEDGED_GAP).
- [ ] Adaptive Rigor mapping encoded.
- [ ] ≥ 3 gates use snapshot validation.
- [ ] `proof_trail_audit.py` exits 0 on full DB; every Change has complete 10-link chain (G.9).
- [ ] ECITP C6/C11 REJECT-promotion flags active; WARN→REJECT transition verified (G.9).

---

## 11. Test strategy summary

| Test kind | Phase intro | Purpose |
|---|---|---|
| Regression (existing pytest) | All phases | Maintain current 420 tests green. |
| Migration round-trip (alembic up/down) | A, B, C, F, G | Each migration reversible without data loss. |
| Invariant / property-based (`hypothesis`) | D.2 | Check determinism, acyclicity, idempotence, reversibility, invariant preservation. |
| Metamorphic | D.3 | Check symmetry / permutation invariance of validators. |
| Adversarial (regression from `Finding`) | D.4 | Prevent regression of known failure modes. |
| Replay harness | A.3 | Bit-identical verdict on historical inputs (determinism P6). |
| Weekly evidence replay | D.5 + F.2 | 5% `EvidenceSet` sample re-executed; divergence → Finding. |
| Mutation smoke | D.5 | Remove any rule → ≥ 1 test fails. Proves tests are load-bearing. |
| Stub-replacement drill | E.6 | Mode diagonalization: replacing a mode with a stub doesn't break siblings. |
| Disaster drill (rollback) | C.4 | REVERSIBLE class changes round-trip byte-identical. |
| Synthetic violation test | E.2, F.4, F.5 | Injected bad delivery → validator blocks. |
| CI gate (RiskWeightedCoverage) | D.5 | Below α per capability → merge blocked. |

Each stage exit test is **automated** (pytest or shell script) except where marked Steward review.

---

## 12. Calibration ADRs pending (unblocks phases)

| ADR | Unblocks | Who decides |
|---|---|---|
| ADR-004 Calibration constants | Phase A exit (all of A.1–A.5) | governance |
| ADR-005 Invariant.check_fn format | Phase E.2 | platform |
| ADR-006 Model version pinning | R-SPEC-05 / ongoing | governance |
| ADR-007 Steward rotation for Forge | Phase G.5 | governance |
| ADR-008 Retroactive Stage 0 strategy | Phase G.1 | governance + security |
| ADR-009 Snapshot Validation 5 components | Phase G.8 | platform |
| ADR-010 Non-trivial classifier threshold | Phase F.3 | platform |
| ADR-011 BLOCKED state down-migration handling | Phase F.4 | platform |
| ADR-012 Non-trivial classifier edge cases | Phase F.9 (SR-3) | platform — see `AUTONOMOUS_AGENT_FAILURE_MODES.md §1.3` |
| ADR-013 Challenger REFUTED: mandatory re-queue OR human override? | Phase F.6 | platform — from `EPISTEMIC_CONTINUITY_ASSESSMENT.md §8 Q2` |
| ADR-014 C2 sufficiency: pre-LLM gate required or post-hoc validator sufficient? | Phase A exit | platform — from `EPISTEMIC_CONTINUITY_ASSESSMENT.md §8 Q4` |
| ADR-015 Requirement entity — promote `Finding.type='requirement'` to separate table, or accept Finding-as-Requirement in proof-trail audit? | Phase G.9 | platform — from ECITP C12 10-link proof trail |
| ADR-016 Test entity — promote `AcceptanceCriterion.scenario_type` to separate `Test` table, or treat AC+scenario_type as chain's test link? | Phase G.9 | platform — from ECITP C12 10-link proof trail |
| ADR-017 Canonical `relation TEXT → relation_semantic ENUM` mapping for B.6 backfill | Phase B.6 | platform — from ECITP C6 topology preservation |
| ADR-018 DLP mechanism for Confidential+ tier — technology choice, OR formal ACKNOWLEDGED_GAP per FRAMEWORK_MAPPING §12 with Steward sign-off | Phase G.1 | platform + security — from FRAMEWORK_MAPPING R-FW-02 |

ADRs 4–7 are P1 per deep-risk; must be created + reviewed before their respective phase starts.
ADRs 15–17 block G.9 and B.6; ADR-018 blocks G.1.

---

## 13. First PR (concrete, small, reversible)

**Title:** Phase A Stage A.1 — `EvidenceSet` entity (shadow)

**Scope:**
1. Alembic migration `evidence_sets` with `down_revision`.
2. `app/models/evidence_set.py` with columns per spec.
3. `app/validation/verdict_engine.py` stub (interface only, no rules wired).
4. `app/validation/gate_registry.py` — static dict.
5. `app/validation/rule_adapter.py` — protocol only.
6. Feature flag `VERDICT_ENGINE_MODE=off` default.
7. `tests/test_evidence_set_model.py` — insert/query/delete round-trip.
8. Update `docs/README.md` status table (evidence_set model: EXISTS).

**Size:** ~250 LOC additive, 0 removed.

**Blast radius:** zero to production — flag OFF; engine stub present but not invoked.

**Acceptance:**
- All existing 420 tests green.
- New test green.
- Migration up + down round-trip clean.
- `alembic current` updated.

**Reversal:** flag stays off; migration down.

**Prerequisite:** Pre-flight complete (ADR-003 ratified, ADR-004 calibration CLOSED, smoke tests done).

---

## 14. Progress tracking

This is a living document. Update per stage completion:

- [ ] Pre-flight
  - [ ] Stage 0.1 ADR-003 ratified
  - [ ] Stage 0.2 Calibration ADRs (004, 005, 006)
  - [ ] Stage 0.3 IMPLEMENTATION_TRACKER smoke tests
- [ ] Phase A (5 stages)
- [ ] Phase B (6 stages)
  - [ ] Stage B.1–B.4 (CausalEdge, backfill, CausalGraph, ContextProjector)
  - [ ] Stage B.5 TimelyDeliveryGate (ECITP C3)
  - [ ] Stage B.6 SemanticRelationTypes (ECITP C6)
- [ ] Phase C (4 stages)
- [ ] Phase D (5 stages)
- [ ] Phase E (7 stages)
  - [ ] Stage E.1–E.6 (contract schema, invariants, autonomy, reachability, modes, contract tests)
  - [ ] Stage E.7 EpistemicProgressGate (ECITP C8)
- [ ] Phase F (10 stages)
  - [ ] Stage F.1–F.6 (decision discipline)
  - [ ] Stage F.7 AgentAuthorityCheck gate (SR-1)
  - [ ] Stage F.8 Skip-cost enforcement (SR-2)
  - [ ] Stage F.9 Distinct-actor spawn in autonomous loop (SR-3)
  - [ ] Stage F.10 StructuredTransferGate (ECITP C11)
- [ ] Phase G (9 stages)
  - [ ] Stage G.1–G.8 (CGAID compliance)
  - [ ] Stage G.9 ProofTrailCompleteness + ECITP REJECT-promotion (ECITP C7, C12)

Total: 3 + 5 + 6 + 4 + 5 + 7 + 10 + 9 = **49 stages**.

Each completed stage produces either a commit (stage tests green) or a blocking Finding if tests fail. No "partial" stages — incomplete = DRAFT.

---

## 15. Risk pointer

See [`DEEP_RISK_REGISTER.md`](DEEP_RISK_REGISTER.md) for 29 risks. Before any phase starts, review risks in that phase's category:

- Phase A: R-SPEC-01, R-SPEC-03, R-PLAN-01, R-PLAN-02, R-IRR-01
- Phase B: R-IRR-02
- Phase C: R-PLAN-02 (adapter)
- Phase D: R-SPEC-02 (Invariant format)
- Phase E: R-PLAN-03 (refactor blast), R-SPEC-05 (vendor-dep)
- Phase F: R-PLAN-04 (classifier overblocks), R-PLAN-05 (Metric 4 gaming)
- Phase G: R-FW-02 (Stage 0 IRREVERSIBLE), R-FW-04 (Steward audit)
- Cross-cutting: R-GOV-01 (solo-author — blocks everything until ADR-003 ratified)

---

## 16. Non-goals (from CHANGE_PLAN_v2 §7)

- Not migrating to LangGraph.
- Not multi-agent for interdependent tasks.
- Not new agent framework.
- Not standalone observability stack in this plan.
- Not UI overhaul.
- No automatic UNKNOWN resolution (P20 requires human ACK).
- No autonomous HIGH/CRITICAL root-cause approval (P21).

---

## 17. When this ROADMAP.md is updated

- After each stage completion: update §14 checklist.
- After a phase exit gate passes: mark phase DONE; note any deltas from plan.
- When a new ADR ratifies: update §12 pending list.
- When `DEEP_RISK_REGISTER.md` adds/closes risk: update §15 pointers.
- **Never** silent edits. Changes that alter strategy → new ADR.

---

## 18. Priority quickstart — Epistemic Continuity soundness order

> **Source:** [`EPISTEMIC_CONTINUITY_ASSESSMENT.md`](EPISTEMIC_CONTINUITY_ASSESSMENT.md) (2026-04-23). Maps the 12 conditions of the *Epistemic Continuity and Information-Topology Preservation* theorem (C1–C12) onto the 25 atomic properties and this roadmap's phases.
>
> **Purpose:** The theorem's degradation corollary and topology theorem impose a specific ordering constraint not fully visible from the phase dependency graph alone. This section captures that ordering and is authoritative for "what to do first if soundness (not just completeness) is the goal."

The theorem states two blocking results:

1. **Degradation theorem:** if stage k allows the agent to continue with missing critical information (`ContinueByGuess(k)`), all stages `j ≥ k` inherit epistemic degradation. One prior-substitution event propagates forward.
2. **Topology theorem:** local plausibility of every individual stage does not imply global correctness if dependency relations between evidence, requirements, decisions, and tests are not preserved across stages.

These two results reorder the roadmap's priorities as follows.

### Priority order for soundness (independent of completeness order)

| Priority | Action | Theorem condition(s) closed | Roadmap stage | Rationale |
|----------|--------|-----------------------------|---------------|-----------|
| **P-0** | Ratify ADR-003 (distinct-actor review) | prerequisite for all | Pre-flight 0.1 | Without ratification all 25 properties are DRAFT; no binding gate exists. Human step — can proceed in parallel with P-1 design. |
| **P-1** | Fix 75 `.status=` violations — Universal Gating enforce mode | C6 (topology preservation), C9, C12 | Phase A Stage A.4 | **Topology theorem direct instantiation.** Every bypass creates a causal-edge gap. Widest single breach. Mechanically testable (grep = 0). Requires A.1→A.2→A.3 (shadow week) first. |
| **P-2** | Add `BLOCKED` status for `[UNKNOWN]` claims | C4 (ambiguity exposure), C10 (stop-or-escalate) | Phase F Stage F.4 | **Degradation theorem activation trigger.** Without BLOCKED, the system structurally cannot satisfy C10. Every `[UNKNOWN]` → continue → all downstream degraded. |
| **P-3** | Promote confabulation WARNING → REJECT | C4 (partial), C5 (evidence-grounded) | Phase F Stage F.3 | Closes prior substitution for non-trivial untagged claims. Single-file change in `contract_validator.py`. |
| **P-4** | Make challenger blocking (REFUTED → re-queue) | C5 (partial), C12 (proof trail) | Phase F Stage F.6 | Closes "refuted artifact accepted as evidence" gap. Without this, a challenger REFUTED enters the proof trail as ACCEPTED — C12 broken. |
| **P-5** | Set `VERDICT_ENGINE_MODE=enforce` as default | C9 (deterministic evaluation guarantee) | Phase A Stage A.4 | Without enforce as default, gate fixes are opt-in. One misconfigured deployment reverts to pre-A state. |
| **P-6** | Phase B: CausalEdge table + ContextProjector | C1, C6 (graph layer), C11, C12 | Phase B | Completes topology preservation layer and replaces `kb_scope` with causal-graph projection. Requires Phase A complete. |
| **P-7** | Phase C: ImpactClosure + ImpactDiff | C3 (full closure), C7 (continuity of meaning) | Phase C | Closes "one-line change silently propagates to unrelated tasks" gap. Requires Phase A. |

### Structural note

Phases A and F are **co-critical**: Phase A closes the topology/gate layer (C6, C9); Phase F closes the epistemic-discipline layer (C4, C5, C10). Neither alone is sufficient for soundness.

Per the roadmap dependency graph (§2), F depends on A + B. This means:
- Start Phase A immediately (additive, zero blast-radius stages A.1→A.2 are safe to begin now).
- Design Phase F (F.3, F.4, F.6) in parallel so implementation begins immediately after Phase A exit.
- Do not declare soundness until both Phase A Stage A.4 AND Phase F Stage F.4 + F.6 are complete.

### Conditions already satisfied

C3 (timely delivery — sequencing) and C8 (additive epistemic progression) are satisfied by architectural design. No remediation required.

### New ADRs required by this assessment

| ADR | Question | Blocks |
|-----|----------|--------|
| ADR-011 | BLOCKED state: max TTL before auto-escalation? Down-migration handling? | Phase F F.4 |
| ADR-013 | Challenger REFUTED: mandatory re-queue OR human override path? | Phase F F.6 |
| ADR-014 | C2 sufficiency: pre-LLM gate required or post-hoc validator sufficient for current maturity? | Phase A exit |

ADR-011 is already listed in §12. ADR-013 and ADR-014 are new, identified by this assessment.

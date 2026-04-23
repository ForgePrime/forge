# Forge Platform — Formal Properties (v2, consolidated)

**Status:** **DRAFT** — pending distinct-actor peer review per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Authored by a single actor in one session (2026-04-22); §B.8 Solo-verifier violation tracked as risk **R-GOV-01 (composite 19, CRITICAL)** in deep-risk audit 2026-04-23. Not binding until reviewed + ratified. Phase A PR referencing this document as NORMATIVE is blocked until transition.
**Supersedes:** [`archive/FORMAL_PROPERTIES.md`](archive/FORMAL_PROPERTIES.md) (v1 retained append-only for audit) — same DRAFT constraint applies to v1.
**Version:** 2026-04-22-v2 + 2026-04-22-v2.1 patch (§11) + 2026-04-23 status demotion.
**Scope:** `platform/` only.

## 0. What changed vs v1

v1 captured 10 algebraic properties derived from the conversation. Deep-verify against the codebase surfaced two hallucinated file references, one severity misclassification, and — most importantly — **five atomic properties are missing** relative to two formal theorems already in the user's workspace (`ITRP/.ai/theorems/Engineer_Soundness_Completeness.md`, `ITRP/.ai/theorems/Evidence_Only_Decision_Model.md`) and the operational contract (`ITRP/.ai/CONTRACT.md`), plus the user's 8-point satisfaction criterion.

v2 is the **closure** of four sources:
- v1 (10 dynamical/structural properties)
- Engineer Soundness & Completeness Theorem (8 conditions) — `ITRP/.ai/theorems/Engineer_Soundness_Completeness.md`
- Evidence-Only Decision Model Theorem (8 conditions) — `ITRP/.ai/theorems/Evidence_Only_Decision_Model.md`
- Operational Contract (§A 7 silences, §B 5 format templates + 3 self-check triggers + 4 subagent rules, non-trivial triggers) — `ITRP/.ai/CONTRACT.md`
- User's satisfaction criterion (8 points, delivered 2026-04-22)

After deduplication, **24 atomic properties** remain. Each one has: formula, operational meaning, binding in Forge (concrete entity or rule), acceptance signal. The mapping table in §10 shows exactly which source condition is covered by which atomic property.

---

## 1. Spaces and symbols

| Symbol | Meaning |
|---|---|
| $\mathcal{I}$ | intent / requirement space |
| $\mathcal{C}$ | working context (projection of history + knowledge delivered to the agent) |
| $\mathcal{S}$ | delivery state |
| $\mathcal{E}$ | evidence artifacts |
| $\mathcal{D}$ | decisions |
| $\mathcal{W}$ | execution paths |
| $\mathcal{O}$ | outcomes / objectives / key results |
| $\mathcal{X}$ | input / case space |
| $\mathcal{M}$ | failure modes |
| $\mathcal{T}$ | test scenarios |
| $\mathcal{H}$ | candidate hypotheses (for diagnosis) |
| $\mathcal{A}$ | assumption set on a decision or artifact |
| $\text{Req}(a)$ | required evidence set for artifact $a$ |
| $\text{Prov}(a)$ | provided evidence set for artifact $a$ |
| $\text{Closure}(\cdot)$ | transitive closure under the dependency relation |
| $E(d)$ | evidence supporting decision $d$ |
| $\text{Suff}(E, x)$ | evidence $E$ is sufficient to justify $x$ |
| $Q_n$ | quality signal at step $n$ |
| $a_n$ | autonomy scope at step $n$ |

## 2. System operator

$$T : (I, C, S) \to (D, E, S')$$

All $\mathcal{S}$ mutations go through $T$. Anything that writes state outside $T$ violates the model.

---

## 3. Atomic properties — the 24

Organized in six groups. Each property is stated once; §10 maps the 41 source conditions to these 24.

### Group A — Dynamics (5)

#### P1 — Idempotence

$$T(T(x)) = T(x)\qquad\text{for stabilizing operations.}$$

Re-running the same intent on the same state with the same policy produces the same result and no new write.

**Binding.** Every mutating MCP tool (`forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`) accepts an `idempotency_key`. A `(tool, key, args_hash)` tuple within TTL returns the original result; zero new writes.

**Acceptance signal.** Integration test: two identical calls inside the idempotency window produce one row.

---

#### P2 — Continuity

$$\forall \varepsilon>0\ \exists \delta>0:\ d\!\big((I,C,S),(I',C',S')\big)<\delta \Rightarrow d_O\!\big(T(\ldots),T(\ldots)\big)<\varepsilon$$

Small semantic change in intent, context, or state causes a bounded change in plan and scope.

**Binding.** `ImpactDiff(old, new) → {preserved_ids, changed, ac_invalidated, fraction_changed}`. Plan regeneration preserves task IDs whose `requirement_refs` are unchanged.

**Acceptance signal.** Canonical fixture: one-line requirement edit mutates ≤ 2 tasks; unrelated edit mutates 0.

---

#### P3 — Impact Closure

$$\text{Impact}(\Delta) = \text{Closure}(\text{dependencies})$$

*(Upgraded in v2: v1 had "operational differentiability" + `BlastRadiusEstimator` — too weak. Engineer Soundness §4 demands full transitive closure.)*

Every change declares the **complete** transitive closure of dependencies, usages, side effects, and execution paths. No local-only fixes.

**Binding.** `ImpactClosure(change)` walks `task_dependencies`, `CausalEdge`, import graph (static), and registered side-effect declarations (functions tagged with `@side_effect` metadata). Returns a closed set. `BlastRadiusEstimator` is retained but demoted to a *review-cost hint* over that closure, not the closure itself.

**Acceptance signal.** For a canonical fixture where a function $f$ is called by $\{g, h\}$ and $g$ by $\{k\}$, the closure returned for "modify $f$" equals $\{f, g, h, k\}$. No element missing.

---

#### P4 — Asymptotic autonomy

$$\lim_{n\to\infty} a_n = A_{\max}\quad\text{subject to}\quad \forall n\ Q_n \ge q_{\min}$$

with $Q_n = (\text{success\_rate}, \text{rollback\_rate}, \text{evidence\_sufficiency}, \text{confabulation\_rate})$ aggregated over a rolling window $W$ (calibration in §7).

Autonomy rises **or falls** depending on rolling quality.

**Binding.** Extends `app/services/autonomy.py` (L1–L5 stays as labels) with `AutonomyState(project, capability, window_start, <Q_n fields>)`. `demote()` added — currently missing. Per-capability scope, not per-project.

**Acceptance signal.** Synthetic drill: inject regression → $Q_n$ drops → scope demotes within one run.

---

#### P5 — Reversibility

$$T^{-1}(S') = S\quad\text{or}\quad R\!\big(T(S)\big) \approx S$$

Every mutation classified: `REVERSIBLE | COMPENSATABLE | RECONSTRUCTABLE | IRREVERSIBLE`.

**Binding.** `Change.reversibility_class`, `Change.rollback_ref`. Default on ambiguity = `IRREVERSIBLE` (fail-safe).

**Acceptance signal.** Disaster drill: `Rollback.attempt(change_id)` on a REVERSIBLE change restores state checksum byte-identical.

---

### Group B — Gates & completeness (5)

#### P6 — Deterministic evaluation

$$V : (a, e(a), r) \to \{\text{accept}, \text{reject}\}\quad\text{is a pure function}$$

Same inputs ⟹ same verdict. No wall-clock, no randomness, no global mutable state, no network.

**Binding.** `VerdictEngine.evaluate(artifact, evidence_set, rules)`. `plan_gate`, `contract_validator` become rule adapters behind it.

**Acceptance signal.** Replay harness: last 100 accepted executions re-evaluated against persisted evidence → bit-identical verdicts.

---

#### P7 — Universal gating

$$S' = T_i(S) \iff G_i(S, T_i, E) = 1$$

**Every** transition passes through a registered gate.

**Binding.** `GateRegistry[(entity, from, to)] = [rule_refs]`. `VerdictEngine.commit(entity, target_state, verdict)` is the single write path. Direct `.status = "..."` assignments banned by pre-commit grep.

**Acceptance signal.** Grep invariant: zero matches of `\.status\s*=\s*['"]` outside `app/validation/verdict_engine.py`. Today: **75 matches across 9 files** (see GAP_ANALYSIS_v2 §5.2).

---

#### P8 — Evidence Completeness Theorem

$$\text{Gate}(a) = 1 \iff \big(\text{Req}(a) \subseteq \text{Prov}(a)\ \wedge\ \text{Verify}(a) = 1\ \wedge\ \text{Risk}(a) \le \tau\big)$$

Biconditional. All three ⟹ pass. Any failing ⟹ fail.

**Binding.** `EvidenceSet` entity: `{artifact_ref, kind, provenance, checksum, rule_ref, sufficient_for}`. `Req(a)` derived from `Task.produces` (once it becomes typed via `ContractSchema` in phase E).

**Acceptance signal.** Property-based test: random $(a, E)$ pairs; gate PASS ⟺ the three conditions hold.

---

#### P9 — Outcome surjectivity

$$\forall o \in \mathcal{O}\ \exists w \in \mathcal{W}:\ F(w) = o$$

For every declared objective / KR, at least one governed workflow can reach it.

**Binding.** `ReachabilityCheck` gate before `Objective.status = "ACTIVE"`. Evidence stored in `Objective.reachability_evidence`.

**Acceptance signal.** Every ACTIVE objective has non-empty `reachability_evidence`.

---

#### P10 — Risk-weighted coverage

$$\sum_{m \in \mathcal{M}} w_m \cdot \text{Cov}(T, m)\ \ge\ \alpha\qquad\text{(per capability)}$$

with test selection:

$$T^* = \arg\max_{T\subseteq \mathcal{X},\ |T|=n}\ P\!\big(\exists x \in T : F(x) \ne \text{Spec}(x)\big)$$

Coverage is failure-mode-weighted, not line-weighted. Tests maximise falsification probability.

**Binding.** `FailureMode(id, code, description, risk_weight, capability)` as first-class. `Finding` tagged with `failure_mode_id` where applicable. `tests/property/`, `tests/metamorphic/`, `tests/adversarial/` (built from `Finding` regression set).

**Acceptance signal.** CI: below $\alpha$ blocks merge. Mutation smoke: removing any `VerdictEngine` rule fails ≥ 1 test.

---

### Group C — Architecture (3)

#### P11 — Architectural diagonalizability

$$T = P \Lambda P^{-1}$$

System decomposes into independent modes: **planning, evidence, execution, validation, governance, autonomy**.

**Binding.** `app/{planning, evidence, execution, validation, governance, autonomy}/` modules. Typed Pydantic DTOs at boundaries. Each mode swappable with a stub without breaking siblings' contract tests.

**Acceptance signal.** Stub-replacement drill: `execution/` stubbed → `validation/` tests still green.

---

#### P12 — Operational self-adjointness

$$\langle Tx, y \rangle = \langle x, Ty \rangle\quad\text{(operationally)}$$

Same contract structure governs **both** execution and validation. Drift between "what the agent produces" and "what the validator checks" is structurally impossible.

**Binding.** `ContractSchema` owned by `Task.produces`. Renders `prompt_constraint` and `validator_rules` from one source. Mutation of a field changes both; a drift test fails otherwise.

**Acceptance signal.** Unit: mutate a field; both prompt fragment and validator rule change; drift test fails.

---

#### P13 — Invariant preservation *(NEW in v2, from Engineer Soundness §5)*

$$\forall x \in \text{ValidStates}:\ \text{Invariant}(x) \Rightarrow \text{Invariant}\!\big(F(x)\big)$$

Every transition preserves declared system invariants.

**Binding.** `Invariant` entity: `{code, check_fn, applies_to}`. Registered per entity (e.g., Execution, Task, Decision). `VerdictEngine.commit()` evaluates all applicable invariants post-transition; any `False` → rejected, state reverted.

**Acceptance signal.** Invariant list is non-empty per entity with > 1 state. Synthetic test: each invariant has at least one transition that would violate it, blocked by the gate.

---

### Group D — Memory (2)

#### P14 — Causal decision memory

History is a DAG $G = (V, E)$ with $V = \{\text{Decision, Change, Finding, AC, KR, Execution, EvidenceSet, LLMCall}\}$ and $E$ carrying $\{\text{justifies, supersedes, evidences, produced\_by, blocks}\}$. Not a flat log.

**Binding.** `CausalEdge(src_type, src_id, dst_type, dst_id, relation, created_at)` table, unique constraint, acyclicity via `src.created_at < dst.created_at`. Idempotent backfill from existing FK-based edges (`Task.origin_finding_id`, `AcceptanceCriterion.source_ref`, `AcceptanceCriterion.source_llm_call_id`, `Finding.source_llm_call_id`, `Finding.execution_id`, `Decision.execution_id`, `Decision.task_id`, `Change.execution_id`, `Change.task_id`, `Knowledge.source_ref`). Insert without an edge rejected by trigger.

**Acceptance signal.** Invariant test: every `Decision | Change | Finding` row has ≥ 1 `CausalEdge` to an ancestor. Property test: random insertions never produce a cycle.

---

#### P15 — Context projection

$$\pi_k : G \to C_k$$

For task $k$, the prompt context is the **minimal justification frontier** from $G$ relevant to $k$, pruned to a token budget.

**Binding.** `ContextProjector.project(task, budget_tokens)`: BFS over `CausalEdge`, filtered by `scope_tags ∪ requirement_refs`, pruned with deterministic priority (must-guidelines → recent decisions → evidence → knowledge). Persisted per `Execution` as `ContextProjection` for audit.

**Acceptance signal.** For 10 historical executions, the projection contains every decision the agent's reasoning referenced. Budget respected.

---

### Group E — Decision discipline (6 — all NEW in v2 or tightened)

#### P16 — Evidence existence

$$\forall d \in \mathcal{D}:\ d\ \text{valid} \Rightarrow \exists E(d) \ne \emptyset$$

No decision without evidence.

**Binding.** `Decision` row insertion requires at least one `EvidenceSet` link. DB trigger or app-level gate.

**Acceptance signal.** DB invariant query: zero `Decision` rows with no evidence edge.

---

#### P17 — Evidence source constraint *(NEW, from Evidence-Only §2)*

$$E(d) \subseteq \text{Data} \cup \text{Code} \cup \text{Requirements}$$

Evidence comes only from observed data, system code, or defined requirements. No external guess, no pattern-match intuition.

**Binding.** `EvidenceSet.kind ∈ {data_observation, code_reference, requirement_ref, test_output, command_output, file_citation}`. No `kind = "assumption"` or `"pattern"` accepted. Source URL/path required per row.

**Acceptance signal.** Schema constraint on `kind`. Integration test: attempt to insert evidence without provenance → rejected.

---

#### P18 — Evidence verifiability *(NEW, from Evidence-Only §3)*

$$\forall e \in E(d):\ \text{Verifiable}(e) = (\text{reproducible}\ \wedge\ \text{inspectable}\ \wedge\ \text{independently checkable})$$

Evidence must be re-runnable (or the artifact re-readable) by an independent party without access to the original reasoning.

**Binding.** For `kind in {test_output, command_output}`: `EvidenceSet.reproducer_ref` is the command line that produces it. For `kind in {code_reference, file_citation}`: `file_path + line_range + checksum` at time of citation. Validation replays/rereads and confirms equality.

**Acceptance signal.** Replay job: random sample of 5% of evidence rows re-executed/re-read weekly; equality checked; divergences emit `Finding`.

---

#### P19 — Assumption control *(NEW, from CONTRACT §B.2 + Evidence-Only §5)*

Every non-trivial claim is tagged $\tau \in \{\text{[CONFIRMED]}, \text{[ASSUMED]}, \text{[UNKNOWN]}\}$.

- `[CONFIRMED]` — executed / cited with quoted output or file:line.
- `[ASSUMED]` — inferred from code without execution; reading ≠ confirmation.
- `[UNKNOWN]` — STOP, ask. After escalation, if a responsible human accepts the risk, record as `[ASSUMED: accepted-by=<role>, date=YYYY-MM-DD]`. Acceptance does not transmute into `[CONFIRMED]`.

**Binding.** Prompt assembly injects the tagging rule (`prompt_parser`). `contract_validator` already detects missing tags (partial — per `IMPLEMENTATION_TRACKER.md`). Strengthen: reasoning without tags on non-trivial claims is REJECTED, not WARNED. Non-trivial defined by CONTRACT.md "7 triggers" (data/contract/assumption/cascade/regulatory/timing/external).

**Acceptance signal.** Integration test: reasoning with a claim touching state but no tag → REJECTED. Pre-existing `IMPLEMENTATION_TRACKER.md:126` reports 3 WARNINGs for missing tags — promote to FAIL.

---

#### P20 — Explicit uncertainty separation with execution blocking *(NEW, from Evidence-Only §7 + user satisfaction §3)*

$$\text{State} = (\text{Certain}, \text{Uncertain}),\qquad \text{Certain} \cap \text{Uncertain} = \emptyset$$

Strengthened by user's 8-point satisfaction criterion: **uncertainty blocks execution**. `[UNKNOWN]` is not tagged-and-continue; it halts the pipeline until resolved by human or resolved to `[CONFIRMED]` via verification.

**Binding.** `Execution.uncertainty_state` JSONB: `{certain: [ids], uncertain: [ids]}`. Non-empty `uncertain` with non-trivial classification → `Execution.status = "BLOCKED"` (new state in enum). Only human ACK via `POST /executions/{id}/resolve-uncertainty` with explicit `[ASSUMED: accepted-by=<role>]` unblocks.

**Acceptance signal.** Integration test: deliver with non-empty `[UNKNOWN]` item → BLOCKED, no ACCEPTED path available until resolve.

---

#### P21 — Root cause uniqueness *(NEW, from Engineer Soundness §3)*

$$\exists! h \in \mathcal{H}:\ \text{Consistent}(h, \text{Data})\ \wedge\ \forall h' \ne h:\ \lnot \text{Consistent}(h', \text{Data})$$

For diagnosis / debug / root-cause analysis: exactly one hypothesis survives. Alternatives explicitly rejected.

**Binding.** `Decision.type = "root_cause"` must carry `Decision.alternatives_considered` with ≥ 2 alternatives, each with an explicit rejection reason. Validator rule: root-cause Decision without ≥ 2 rejected alternatives → REJECTED at gate.

**Acceptance signal.** DB invariant query: every `type="root_cause"` Decision has `len(alternatives_considered) ≥ 2` and each alt has a `rejected_because` field. Synthetic test: submit root-cause with one alt → REJECTED.

---

### Group F — Disclosure & behavior (3 — all NEW in v2, from CONTRACT)

#### P22 — Disclosure protocol

Every execution attempt conforms to CONTRACT §B format. Fail-closed.

Required templates (one of each when applicable):
- **Evidence-first** (DID / DID NOT / CONCLUSION) — before any "works/done/OK" claim.
- **Pre-implementation** (ASSUMING / VERIFIED / ALTERNATIVES) — for features & architecture (skip ALTERNATIVES for simple bugs).
- **Pre-modification** (MODIFYING / IMPORTED BY / NOT MODIFYING) — before any file touch; grep-based import chain required.
- **Pre-completion** (DONE / SKIPPED / FAILURE SCENARIOS ≥ 3) — before marking ACCEPTED.

Plus the 7 disclosure behaviors (CONTRACT §A): assumption-vs-verification, partial implementation, happy path only, narrow scope, selective context, false completeness, failure to propagate.

**Binding.** `prompt_parser` already emits the operational contract at end of prompt (§109 of CONTRACT.md mirror). `contract_validator` partially validates (assumptions required, impact required, completion claims) — **incomplete** vs CONTRACT §B. Strengthen: validator rules for each of the 5 templates; missing template → REJECT.

**Acceptance signal.** Per rule: synthetic reasoning missing template X → REJECTED with specific error. Pre-existing partial checks (`IMPLEMENTATION_TRACKER.md:107-116`) audited and extended to 100% coverage of §B.

---

#### P23 — Verification independence *(NEW, from CONTRACT §B.8 solo-verifier)*

An artifact produced in turn $n$ **cannot** be marked verified in turn $n$ by the same actor. Verification requires either:
- a deterministic check (grep, test run, type check with observable output), OR
- a separate actor (user, reviewer, another agent without the original reasoning trace).

**Binding.** `Execution.verified_by ≠ Execution.agent` OR `Execution.verified_by_check ∈ {"grep", "test", "typecheck"}` with stored output. `forge_challenge` endpoint already spawns an independent challenger — strengthen: ACCEPTED status requires either deterministic check or challenge pass, not only contract_validator self-check.

**Acceptance signal.** Integration test: accept without either deterministic check or challenge → blocked.

---

#### P24 — Transitive accountability *(NEW, from CONTRACT subagent rules)*

Delegation does not reset accountability.

- Subagent `[CONFIRMED]` is `[ASSUMED]` at parent level until parent independently verifies.
- Subagent side-effects (files modified, external calls) aggregate into parent's MODIFYING list and FAILURE SCENARIOS.
- Skipped disclosure by any agent in the chain is the parent's violation.

**Binding.** Every sub-call (`Agent` tool, `mcp_*` mutating call) records into `ai_interaction` + `ChildExecution`. Parent reasoning that claims `[CONFIRMED]` on a child's output → validator downgrades to `[ASSUMED]` unless parent cites its own verification line.

**Acceptance signal.** Integration test: parent reports `[CONFIRMED]` that is literally copied from child's output → validator emits downgrade WARNING; repeated → REJECT.

---

## 4. The 8-point satisfaction criterion (user, 2026-04-22)

The system satisfies the Operational Contract iff, for every execution:

| # | User's point | Covered by atomic properties |
|---|---|---|
| 1 | every decision is evidence-based | P16 Evidence Existence + P8 Evidence Completeness Theorem |
| 2 | every claim is explicitly classified | P19 Assumption Control |
| 3 | every uncertainty blocks execution | P20 Explicit Uncertainty Separation |
| 4 | every critical risk is disclosed | P22 Disclosure Protocol (§A.6 false completeness, §A.3 happy path) |
| 5 | every action is gated | P7 Universal Gating |
| 6 | every result is traceable | P14 Causal Decision Memory + P15 Context Projection |
| 7 | every assumption is controlled | P19 Assumption Control + P17 Evidence Source Constraint |
| 8 | every verification is independent | P23 Verification Independence |

All eight must hold simultaneously for a compliant execution. This is a corollary of §3, not a separate spec.

---

## 5. Consistency claims (cross-property implications)

- P8 Evidence Completeness + P7 Universal Gating ⟹ no state advance without fulfilled `Req(a)`.
- P14 Causal Memory + P15 Context Projection ⟹ agent's context is a subgraph of a verifiable justification record.
- P12 Self-Adjointness + P6 Deterministic Evaluation ⟹ agent cannot complete under a definition differing from the validator's.
- P5 Reversibility + P4 Asymptotic Autonomy ⟹ $A_{\max}$ is capped where rollback is impossible; IRREVERSIBLE classes block promotion beyond floor.
- P10 Risk-Weighted Coverage + P18 Evidence Verifiability ⟹ failure-mode coverage is itself verifiable, not merely counted.
- P20 Uncertainty Blocks + P23 Verification Independence ⟹ solo-produced uncertain artifacts cannot self-resolve in the same turn; they block until independent verification resolves them.
- P13 Invariant Preservation + P7 Universal Gating ⟹ invariants are checked at every transition, not just at boundaries.
- P24 Transitive Accountability + P22 Disclosure Protocol ⟹ delegation forces explicit disclosure of who did what at every level.
- P19 Assumption Control + P21 Root Cause Uniqueness ⟹ diagnostic decisions cannot accept an untagged hypothesis OR multiple co-valid hypotheses.
- P3 Impact Closure + P13 Invariant Preservation ⟹ a change's declared impact must include every point where a named invariant could be violated.

---

## 6. Engineer's corollary (composite statement)

A solution $\Delta$ is engineering-correct in Forge iff **all 24 atomic properties hold simultaneously** for its path through the system. Equivalently (Engineer Soundness & Completeness Theorem, §8):

$$\forall x \in \text{ValidInputs}:\ F(x) = \text{Spec}(x)$$

— not as a proof, but as the asymptotic target under the gates of §3. Passing every gate raises confidence that $F \approx \text{Spec}$ within the declared contract boundary; no claim stronger than "high confidence within contract" is made.

---

## 7. Calibration constants (decisions, not assumptions)

These are parameters the spec names but does not fix. Each must be recorded as a CLOSED `Decision` before phase A exit. Any value used ad-hoc is a P19 violation (assumption, not confirmation).

| Parameter | Symbol | Where used | Decision owner |
|---|---|---|---|
| Rolling window for $Q_n$ | $W$ | P4 | governance |
| Autonomy floors $q_{\min}$ | $q_{\min}$ | P4 | governance |
| Risk bound | $\tau$ | P8 | governance |
| Coverage floor per capability | $\alpha$ | P10 | per capability |
| Impact-closure review-cost threshold | — | P3 | governance |
| Impact-estimate error tolerance | — | P3 (hint) | governance |
| Idempotency TTL | — | P1 | platform |
| Acyclicity tolerance window (clock skew) | — | P14 | platform |

---

## 8. Non-goals

- Not a classical formal-verification framework for code. Raises falsification probability; does not prove correctness.
- Code-level properties (null safety, SQL injection, etc.) live in contract validators and lint rules, not here.
- $A_{\max}$ is per-capability. Full autonomy everywhere is **not** claimed.
- Continuity (P2) and impact closure (P3) are **local** approximations / constructions for practical blast radius. They are not analytic continuity / derivatives.
- No property licenses removing a human from the loop for `IRREVERSIBLE` mutations — these always require explicit ACK regardless of $Q_n$.

---

## 9. What v2 explicitly does **not** pin

- Model versions, prompt wording, skill contents (versioned prompt manifests).
- UI routing / affordances.
- Observability backend (Logfire / Langfuse / custom — decision, not property).
- Orchestration framework (property P11 says "separable modes"; it does not say "LangGraph").
- Specific values of calibration constants in §7 (they must be recorded, not guessed).

Anything here not explicitly pinned is a decision to be recorded via `/decide` — never assumed.

---

## 10. Mapping — 41 source conditions → 24 atomic properties

Every condition from v1, Engineer Soundness, Evidence-Only, and CONTRACT has a destination. `=` means direct coverage; `⊆` means the source is strictly weaker (covered and strengthened). NEW marks a property not present in v1.

| Source | Condition | Atomic property | Relation |
|---|---|---|---|
| v1 §3.1 | Idempotence | P1 | = |
| v1 §3.2 | Continuity | P2 | = |
| v1 §3.3 | Operational differentiability | P3 | ⊆ (upgraded) |
| v1 §3.4 | Asymptotic autonomy | P4 | = |
| v1 §3.5 | Reversibility | P5 | = |
| v1 §4.1 | Outcome surjectivity | P9 | = |
| v1 §4.2 | Evidence Completeness Theorem | P8 | = |
| v1 §4.3 | Coverage completeness | P10 | = |
| v1 §4.4 | Failure-oriented test selection | P10 | = (merged) |
| v1 §5.1 | Deterministic evaluation | P6 | = |
| v1 §5.2 | Universal gating | P7 | = |
| v1 §5.3 | Diagonalizability | P11 | = |
| v1 §5.4 | Self-adjointness | P12 | = |
| v1 §5.5 | Causal decision memory | P14 | = |
| v1 §5.6 | Context projection | P15 | = |
| Eng §1 | Deterministic Evaluation | P6 | = |
| Eng §2 | Evidence Sufficiency | P8, P16 | = |
| Eng §3 | Root Cause Uniqueness | **P21** | NEW |
| Eng §4 | Impact Completeness (Closure) | **P3** | upgrade of v1 §3.3 |
| Eng §5 | Invariant Preservation | **P13** | NEW |
| Eng §6 | Evidence Completeness | P8 | = |
| Eng §7 | Failure-Mode Coverage | P10 | = |
| Eng §8 | Proof of Correctness (F=Spec) | §6 corollary | composite, not atomic |
| EvO §1 | Evidence Existence | P16 | = |
| EvO §2 | Evidence Source Constraint | **P17** | NEW |
| EvO §3 | Evidence Verifiability | **P18** | NEW |
| EvO §4 | Evidence Sufficiency | P8 | = |
| EvO §5 | Assumption Elimination | P19 | ⊆ (strengthened) |
| EvO §6 | Traceability | P14 + P15 | ⊆ |
| EvO §7 | Explicit Uncertainty Separation | **P20** | NEW (strengthened by user §3) |
| EvO §8 | Deterministic Justification | P6 | = |
| CON §A.1 | Disclose assumption vs verification | P19 + P22 | behavioral |
| CON §A.2 | Disclose partial implementation | P22 | NEW (behavioral) |
| CON §A.3 | Disclose happy path only | P10 + P22 | ⊆ |
| CON §A.4 | Disclose narrow scope | P22 | NEW (behavioral) |
| CON §A.5 | Disclose selective context | P15 + P22 | ⊆ |
| CON §A.6 | Disclose false completeness | P8 + P22 | ⊆ |
| CON §A.7 | Disclose failure to propagate | P3 + P22 | ⊆ |
| CON §B (5 templates) | Format rules | P22 | = |
| CON §B.6 | False agreement | P22 + P23 | ⊆ |
| CON §B.7 | Competence boundary | P19 (UNKNOWN path) | ⊆ |
| CON §B.8 | Solo-verifier | **P23** | NEW |
| CON subagent (4 rules) | Transitive accountability | **P24** | NEW |
| User §1 | every decision evidence-based | P16 + P8 | = |
| User §2 | every claim classified | P19 | = |
| User §3 | every uncertainty blocks execution | **P20 (strengthened)** | = |
| User §4 | every critical risk disclosed | P22 | = |
| User §5 | every action gated | P7 | = |
| User §6 | every result traceable | P14 + P15 | = |
| User §7 | every assumption controlled | P19 + P17 | = |
| User §8 | every verification independent | P23 | = |

Total: 51 source conditions (some counted more than once across sources) mapped to 24 atomic properties. Seven properties are genuinely NEW in v2: P13 Invariant Preservation, P17 Evidence Source Constraint, P18 Evidence Verifiability, P20 Explicit Uncertainty Separation (with blocking), P21 Root Cause Uniqueness, P23 Verification Independence, P24 Transitive Accountability. One is upgraded (P3 from estimator to closure). The remainder is deduplicated v1 + theorem conditions.

---

## 11. Patch v2.1 (2026-04-22) — coverage strengthening + framework alignment

Deep-verify against `platform/app/services/scenario_generator.py` and `contract_validator.py:188-194` confirmed: v2 had a blind spot in **how** coverage is enumerated, and missed the CGAID framework layer entirely. Two changes below.

### 11.1 P10 strengthened — explicit scenario categories

The v2 text of P10 referred to "failure modes" abstractly. In practice `scenario_type` is the enforced enum and it has 4 values; three distinct failure categories are conflated or absent:

| Category | Current state | Strengthening |
|---|---|---|
| edge_case | **ENFORCED** — `contract_validator.py:193` FAIL if feature/bug lacks PASS on negative/edge_case | keep |
| boundary | **CONFLATED** with edge_case (`scenario_generator.py:33,117`) | split as distinct `scenario_type='boundary'` — require N-1/N/N+1 triple for numeric/size/time bounds |
| concurrent | **ABSENT** — only prose in CONTRACT §B.5 FAILURE SCENARIOS example | new `scenario_type='concurrent'` — state + interleaving / ordering + idempotency |
| malformed | **CONFLATED** with negative (shape errors only, not fuzz) | new `scenario_type='malformed'` — truncated / injection / binary / oversized / null-byte |
| regression | enum value exists, no gate | gate: any closed `Finding` tagged with a `FailureMode` creates a regression AC |

**Updated P10 binding.**
- `AcceptanceCriterion.scenario_type` enum extended: `{positive, negative, edge_case, boundary, concurrent, malformed, regression, performance, security}`. Last two come from existing `objective.scenarios.kind` vocabulary (`objective.py:39`) and are unified.
- `contract_validator` coverage rule per capability: a feature task must have coverage across categories proportional to the capability's risk profile (risk_weight per category per capability, calibrated in §7).
- `scenario_generator` extended with per-category heuristics (boundary → parametrize numeric/size/time; malformed → parametrize with fuzz set; concurrent → parametrize with interleave pattern).

**Acceptance signal.** For a canonical fixture (HTTP endpoint handling `POST /payments`), scenario generator emits ≥ 1 stub per applicable category automatically. Coverage report flags missing categories as risk-weighted gap.

### 11.2 New atomic property — P25 Deterministic test synthesis from contracts

$$\forall s \in \text{ContractSchema},\ \forall i \in \text{Invariants}(s):\ \exists t \in T :\ t = \text{synth}(s, i)$$

Reading: for every typed contract schema and every invariant registered against it, a property-based test is **automatically synthesized by construction**. Not by LLM, not by heuristic keyword-match — by structural walk of the type + the invariant's `check_fn`.

**Why this is structurally different from P10.** P10 is about **selection** — choosing the best subset of test scenarios given a fixed failure-mode taxonomy. P25 is about **synthesis** — generating the test fixture itself from the contract. P10 without P25 requires humans (or LLMs) to write tests per scenario_type; P25 auto-creates the test skeleton so humans only fill in domain-specific oracles.

**Binding in Forge.**
- `TestSynthesizer(contract_schema, invariants) → list[PropertyTest]` service.
- Walks `ContractSchema` (phase E) fields → generates `hypothesis` strategies per type.
- For each `Invariant` registered on the entity → generates an `assert invariant.check_fn(entity_after_op)` test.
- Output lands in `tests/synthesized/` (regeneratable, kept in repo for diffability).
- Extends existing `scenario_generator.py` pattern from AC-text → stub to schema+invariant → full test.

**Acceptance signal.** For a canonical `ContractSchema` with 3 fields and 2 invariants, `TestSynthesizer` emits ≥ 5 property-based tests; all pass on correct implementation; mutation of any field or invariant breaks ≥ 1 test.

**Mapping.**
- v2.1 patch adds P25 → total atomic properties rises to **25**.
- Source alignment: CGAID OPERATING_MODEL §9.4 "Deterministic Snapshot Validation" reference pattern specifies 5 components (Baseline / Capture / Comparator / Failure Contract / Refresh). P25 implements that pattern for property tests; snapshot-style validation is a subcase.

### 11.3 CGAID framework alignment declaration

Forge v2 is **not a new framework**. Forge is the **platform-level implementation** of CGAID (Contract-Governed AI Delivery, `ITRP/.ai/framework/FRAMEWORK.md` v2.0, 2026-04-19). Hierarchy:

```
CGAID Framework (MANIFEST + OPERATING_MODEL + DATA_CLASSIFICATION + PRACTICE_SURVEY + WHITEPAPER)
  └── CONTRACT.md implements OPERATING_MODEL §4.4 contract enforceability
       └── Theorems (Engineer_Soundness, Evidence_Only) formalize MANIFEST principles
            └── FORMAL_PROPERTIES_v2.md (this document) binds theorems to platform code
                 └── Forge platform/ implements the 25 properties
```

**Mapping of MANIFEST 10 principles → v2 atomic properties**: see `FRAMEWORK_MAPPING.md`. Nine principles map to atomic properties; the tenth ("we control our tools") is meta-reflexive — Forge's existence as a platform-owned toolchain satisfies it structurally.

**OPERATING_MODEL layers / stages / 11 artifacts / 7 metrics coverage**: see Phase G in `CHANGE_PLAN_v2.md`. v2.1 does **not** re-specify CGAID inside Forge; it binds Forge entities to CGAID concepts and closes identified gaps (Stage 0 Data Classification Gate, Contract Violation Log for Metric 4, metrics service, Rule Lifecycle, Steward role, Side-Effect Map) via Phase G.

### 11.4 Updated mapping additions

| Source | Condition | Atomic property | Relation |
|---|---|---|---|
| CGAID MANIFEST | 9 of 10 principles | P6-P24 (various) | binding |
| CGAID MANIFEST §10 "we control our tools" | — | meta (declared in §11.3) | reflexive |
| CGAID Operating Rules (Adaptive Rigor) | — | `Task.ceremony_level` mapping (Phase G) | platform binding |
| CGAID Operating Rules (Decision rule) | unknowns must be resolved | P20 | = |
| CGAID OM §4.3 Rule Lifecycle | rule creation / review / retirement | Phase G (new scope) | platform binding |
| CGAID OM §9.4 Deterministic Snapshot Validation | 5-component pattern | P25 + Phase G | binding |
| CGAID OM §5 seven metrics | M1–M7 | Phase G (metrics service) | platform binding |
| CGAID OM §2 Stage 0 | Data Classification Gate | Phase G (new entity + gate) | binding |
| CGAID 11 standardized artifacts | #1–#11 | Phase G (mapping to Forge entities) | mapping |

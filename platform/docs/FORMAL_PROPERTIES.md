# Forge Platform — Formal Properties

**Status:** normative. This document is the contract Forge must satisfy. Every other document (gap analysis, change plan, ADR) is measured against it.
**Scope:** `platform/` only. Everything outside `platform/` (legacy `core/`, `forge_output/`, external consumers) is out of scope for this spec.
**Version:** 2026-04-22-v1.

---

## 0. Intent

Forge is not a text generator with ceremony. It is a **governed operator that transforms delivery state with evidence**. Every property below exists so that a Forge execution is either (a) provably correct within its declared contract, or (b) explicitly flagged as a decision requiring human adjudication — never silently accepted.

The formulas are not decoration. Each one binds to an acceptance signal that can be checked by code, not by reading reasoning. If a property cannot be checked, it is not part of the contract.

---

## 1. Spaces and symbols

| Symbol | Meaning |
|---|---|
| $\mathcal{I}$ | intent / requirement space (what the user or upstream system asked for) |
| $\mathcal{C}$ | working context (projection of history + knowledge delivered to the agent) |
| $\mathcal{S}$ | delivery state (task graph, execution states, artifacts produced so far) |
| $\mathcal{E}$ | evidence artifacts (test outputs, validation results, git diffs, provenance records) |
| $\mathcal{D}$ | decisions (explicit, named, persisted) |
| $\mathcal{W}$ | execution paths / workflows (sequences of allowed transitions) |
| $\mathcal{O}$ | outcomes (declared goals, key results, objectives) |
| $\mathcal{X}$ | input/case space a test or scenario may cover |
| $\mathcal{M}$ | known failure modes |
| $\mathcal{T}$ | test scenarios actually configured |

## 2. System operator

The system is the operator

$$T : (I, C, S) \to (D, E, S')$$

reading intent $I \in \mathcal{I}$, context $C \in \mathcal{C}$ and current state $S \in \mathcal{S}$, producing a decision $D \in \mathcal{D}$, evidence $E \in \mathcal{E}$ and a successor state $S' \in \mathcal{S}$.

Nothing else Forge does is allowed to mutate $\mathcal{S}$. Anything that mutates state outside $T$ violates the model.

---

## 3. Dynamical properties

### 3.1 Idempotence

$$T(T(x)) = T(x)$$

for any operation classified as *stabilizing* (plan drafts, task graph reconciliation, artifact publication, decision recording).

**Operational meaning.** Re-running the same intent against the same state with the same policy constraints produces the same delivery state and no new side effect.

**Binding in Forge.**
- Every MCP tool mutating state (`forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`) takes an `idempotency_key`. A `(tool, key, args_hash)` tuple within a TTL returns the original result and produces zero new writes.
- The same `intent_hash + state_hash` presented to `/plan` returns the same plan reference.

**Acceptance signal.** Deterministic integration test: two identical calls within the idempotency window produce one row and one result.

---

### 3.2 Continuity

$$\forall \varepsilon>0\ \exists \delta>0:\ d\big((I,C,S),(I',C',S')\big)<\delta \Rightarrow d_O\big(T(I,C,S),T(I',C',S')\big)<\varepsilon$$

**Operational meaning.** A small semantic change in the intent, context or state produces a bounded change in the plan and in execution scope. No microscopic input change may rewrite the entire backlog.

**Binding in Forge.**
- `/change-request` is the only ingress for intent drift. It reports an `ImpactDiff`: tasks affected, AC invalidated, plan fraction changed.
- Plan regeneration preserves task IDs where requirements are unchanged.

**Acceptance signal.** For a canonical fixture (one plan, ten tasks), a one-line edit to one requirement mutates ≤ 2 tasks. A one-line edit nowhere near a task mutates 0 tasks. Tested via snapshot.

---

### 3.3 Operational differentiability

$$T(x + \Delta x) \approx T(x) + J_T(x)\,\Delta x$$

**Operational meaning.** For a proposed small change, Forge can estimate its effect before committing — blast radius in files, tests invalidated, review cost in tokens, risk delta.

**Binding in Forge.**
- `BlastRadiusEstimator` runs on every `/plan`, `/change-request`, and `forge_deliver` preview. Returns `{files_touched, tests_invalidated, risk_delta, review_cost_tokens, dependents_affected}`.
- The estimate is persisted and compared against actual post-execution diff; divergence > threshold is a `Finding`.

**Acceptance signal.** Estimator output is recorded; mean absolute error on files_touched across last 20 executions is below a configured bound.

---

### 3.4 Asymptotic autonomy

$$\lim_{n\to\infty} a_n = A_{\max}\quad\text{subject to}\quad \forall n\ Q_n \ge q_{\min}$$

where $a_n$ is autonomy scope after run $n$, $A_{\max}$ is full autonomy inside a declared capability envelope, and $Q_n$ aggregates evidence sufficiency, success rate, rollback rate and confabulation rate.

**Operational meaning.** Autonomy is not a switch. It is a limit of a quality-gated process. It may rise **or fall** at each step.

**Binding in Forge.**
- Extends existing `autonomy.py` (L1–L5) from discrete promotion to a continuous ledger per `(project, capability)`: `success_rate, rollback_rate, evidence_sufficiency, confabulation_rate`, each with a rolling window.
- Scope promotion is permitted only if all four exceed per-level floors; demotion is automatic on incident.
- Veto clauses (MUST-constraint conflict, budget 80%, flagged paths) always win.

**Acceptance signal.** After an induced regression, measured $Q_n$ drops and the policy degrades scope within one run. Synthetic drill.

---

### 3.5 Reversibility

$$T^{-1}(S') = S\quad\text{or, failing that,}\quad R\big(T(S)\big) \approx S$$

**Operational meaning.** Every mutation is classified and carries a compensation path where possible. Irreversible mutations are named as such and require explicit human ACK before being admitted.

**Binding in Forge.** Every `Change` row carries:
- `reversibility_class ∈ {REVERSIBLE, COMPENSATABLE, RECONSTRUCTABLE, IRREVERSIBLE}`
- `rollback_ref`: script id, operation id, snapshot path, or null for IRREVERSIBLE.
- Classification is automatic from diff shape; the default on ambiguity is IRREVERSIBLE (fail-safe conservative).

**Acceptance signal.** Disaster drill: `Rollback.attempt(change_id)` on a fixture replays prior state with byte-identical checksum for REVERSIBLE class.

---

## 4. Completeness properties

These three completeness statements are distinct. Each one names a different thing that must be complete.

### 4.1 Outcome surjectivity

$$\forall o \in \mathcal{O}\ \exists w \in \mathcal{W}:\ F(w) = o$$

**Meaning.** For every declared objective / key result the platform claims to support, there is at least one governed execution path that can reach it.

**Binding in Forge.**
- `ReachabilityCheck` runs on every `Objective`/`KeyResult` at approval time: at least one candidate plan template satisfies it.
- An `Objective` cannot transition to ACTIVE without reachability evidence recorded.

**Acceptance signal.** Any objective in DB with status ACTIVE has a non-empty `reachability_evidence` JSONB.

---

### 4.2 Evidence Completeness Theorem

$$\text{Gate}(a) = 1 \iff \big(\text{Req}(a) \subseteq \text{Prov}(a)\ \wedge\ \text{Verify}(a) = 1\ \wedge\ \text{Risk}(a) \le \tau\big)$$

where $\text{Req}(a)$ is the set of requirements the artifact $a$ must satisfy (derived from its contract), $\text{Prov}(a)$ is the set of provided evidences, $\text{Verify}(a)$ is the validator verdict, and $\text{Risk}(a) \le \tau$ is risk under policy bound.

**Meaning.** No artifact passes a gate without (a) every required evidence present, (b) deterministic verification passed, (c) risk within bound. The biconditional is strict: if all three hold, the gate passes; if any fails, it does not.

**Binding in Forge.**
- `EvidenceSet` is a first-class entity: `{artifact_ref, kind, provenance, checksum, sufficient_for: [rule_ids]}`.
- `Task.produces` + rule-bound `Req(a)` generate the required evidence shape at task creation.
- `VerdictEngine` evaluates the biconditional. No direct `execution.status = "ACCEPTED"` in application code.

**Acceptance signal.** Grep-level invariant: `execution.status = "ACCEPTED"` occurs in exactly one place, inside `VerdictEngine.commit()`. Property test: random $(a, E)$ pairs; gate PASS $\iff$ the three conditions hold.

---

### 4.3 Coverage completeness (case space)

$$\forall x \in \mathcal{X}\ \exists t \in T:\ \text{covers}(t, x)$$

In practice, since $|\mathcal{X}|$ is not enumerable, we weaken to **risk-weighted coverage** over failure modes:

$$\sum_{m \in \mathcal{M}} w_m \cdot \text{Cov}(T, m)\ \ge\ \alpha$$

with $\alpha$ set per capability and $w_m$ risk weight per failure mode.

**Meaning.** Tests do not chase line coverage. They cover *failure modes weighted by risk*. A known failure mode without a test is a `Finding`.

**Binding in Forge.**
- `FailureMode` entity. Every historical `Finding` that names a recurring mode links to a `FailureMode` row.
- `RiskWeightedCoverage` report in CI: `∑ w_m · Cov(T, m)` per capability; gate fails if below $\alpha$.

**Acceptance signal.** Fail a test for an existing failure mode → coverage drops → CI blocks merge.

---

### 4.4 Failure-oriented test selection

$$T^* = \arg\max_{T\subseteq \mathcal{X},\ |T|=n}\ P\big(\exists x \in T : F(x) \ne \text{Spec}(x)\big)$$

**Meaning.** Test scenarios are chosen to maximise falsification probability, not nominal path completeness. Targets: boundary values, adversarial inputs, metamorphic relations, property-based invariants, stateful sequences, idempotency violations, rollback failures.

**Binding in Forge.**
- `tests/property/` using `hypothesis` for invariants.
- `tests/metamorphic/` for relation-based tests (parse/render roundtrip, validator under paraphrase, gate under evidence permutation).
- `tests/adversarial/` built from `Finding` regression set.
- Deterministic harness: seeded random, frozen clock, hermetic DB.

**Acceptance signal.** Three consecutive CI runs produce identical results. Mutation-testing smoke: removing any single production rule fails at least one test.

---

## 5. Structural properties

### 5.1 Deterministic evaluation

$$V : (a, e(a), r) \to \{\text{accept}, \text{reject}\}$$

is a pure function of its inputs; same inputs $\Rightarrow$ same verdict.

**Binding.** `VerdictEngine` has no wall-clock read, no global mutable state, no network call. All non-determinism is pushed into evidence collection upstream. `plan_gate.py` and `contract_validator.py` become rule adapters behind this interface.

**Acceptance signal.** Replay test: execution logs → replay `VerdictEngine` against persisted `(a, E, r)` → bit-identical verdict.

---

### 5.2 Universal gating

$$S' = T_i(S) \iff G_i(S, T_i, E) = 1$$

No state transition occurs except through a named gate in the registry.

**Binding.**
- `GateRegistry` table: each transition (`PROMPT_ASSEMBLED → IN_PROGRESS`, `IN_PROGRESS → DELIVERED`, …) registered with its required evidence shape and rule set.
- `Execution.transition(to, evidence)` is the single entry. Direct `execution.status = "..."` assignments are banned by pre-commit grep.

**Acceptance signal.** Grep invariant: zero occurrences of `\.status\s*=\s*['\"]` outside `VerdictEngine.transition`. Today there are 30+ (see gap doc).

---

### 5.3 Architectural diagonalizability

$$T = P \Lambda P^{-1}$$

System dynamics decompose into independent modes: **planning, evidence, execution, validation, governance, autonomy**.

**Binding.**
- Physical separation: `app/{planning, evidence, execution, validation, governance, autonomy}/` modules.
- Cross-mode traffic goes through typed Pydantic schemas.
- Each mode is swappable (mock-compatible) without breaking others. Tested via per-mode contract tests.

**Acceptance signal.** Replacing the `execution/` module with a stub does not break `validation/` tests.

---

### 5.4 Operational self-adjointness

$$\langle T x, y \rangle = \langle x, T y \rangle$$

interpreted operationally: the **same contract structure** governs both execution (what the agent must produce) and validation (what the system must verify).

**Binding.**
- One `ContractSchema` per `Task.produces`. It derives simultaneously (a) a prompt constraint and (b) a validation check.
- A modification to the contract changes both sides in lock-step — there is no situation where prompt says X and validator expects Y.

**Acceptance signal.** Unit test: mutate a `ContractSchema` field; both prompt rendering and validator schema change; drift test fails.

---

### 5.5 Causal decision memory

History is stored as a directed acyclic graph

$$G = (V, E)$$

with nodes $V$ = {Decision, Change, Finding, AcceptanceCriterion, KeyResult, Execution, EvidenceSet} and edges $E$ encoding relations $\{\text{justifies}, \text{supersedes}, \text{evidences}, \text{produced\_by}\}$. Not a flat log.

**Binding.**
- `CausalEdge` table: `(src_type, src_id, dst_type, dst_id, relation, created_at)` with unique constraint on the tuple and an acyclicity check via $\text{src.created\_at} < \text{dst.created\_at}$.
- Every new `Decision`, `Change`, `Finding` creates at least one edge to an ancestor; insert without an edge is rejected by a database trigger.

**Acceptance signal.** For any $v \in V$, `ancestors(v, depth=∞)` returns a DAG; cycle check at insert time.

---

### 5.6 Context projection

For task $k$, the context delivered to the agent is

$$\pi_k : G \to C_k$$

— a projection of the causal graph containing the minimal justification frontier relevant to $k$, capped by a token budget.

**Binding.**
- `ContextProjector(task, budget_tokens)`: BFS from task over `CausalEdge`, filtered by relevance (scope tags + requirement refs), pruned to budget.
- The projection is persisted per `Execution` (`ContextProjection` table) for audit: what did the agent actually see?
- Replaces static `kb_scope` filtering in prompt assembly.

**Acceptance signal.** Given a task with a known minimal justification set $J$, $J \subseteq \pi_k(G)$. Budget respected: `sum(char_count) < budget`.

---

## 6. Non-goals

- Forge does not claim formal proof of code correctness. It raises falsification probability. The distinction matters.
- Formal symbols in this document describe **system-level** properties. Code-level correctness (null safety, SQL injection, etc.) lives in contract validators and lint rules, not here.
- `A_max` is per-capability, not global. Forge does not promise full autonomy everywhere.
- Continuity and differentiability are local approximations, not analytic properties. They are observable through bounded deltas, not through derivative computation.
- None of the above licenses removing a human from the loop for irreversible actions. Reversibility class IRREVERSIBLE always requires explicit ACK regardless of $Q_n$.

---

## 7. Consistency claims between properties

These are the non-obvious implications that tie the model together.

- **Evidence Completeness (4.2) + Universal Gating (5.2)** ⟹ state cannot advance without a fulfilled Req(a).
- **Causal Memory (5.5) + Context Projection (5.6)** ⟹ the agent's context is a subgraph of a verifiable justification record, not a summary the agent must trust.
- **Self-Adjointness (5.4) + Deterministic Evaluation (5.1)** ⟹ the agent cannot claim completion under a definition different from what the validator uses. Validator drift becomes impossible.
- **Reversibility (3.5) + Asymptotic Autonomy (3.4)** ⟹ autonomy may rise only where rollback is possible; IRREVERSIBLE classes cap $A_{\max}$.
- **Coverage Completeness (4.3) + Failure-Oriented Selection (4.4)** ⟹ risk weighting directs test synthesis; an uncovered high-$w_m$ mode blocks merge.

---

## 8. What this document does not pin

- Specific model versions, prompt wording, skill contents. Those live in versioned prompt manifests.
- UI affordances or routing. Those are orthogonal.
- Observability backend choice. Logfire vs Langfuse vs custom is a decision, not a property.
- Framework choice for orchestration. Property 5.3 says "separable modes"; it does not say "LangGraph".

Anything not pinned here is a decision to be recorded via `/decide`, not an assumption.

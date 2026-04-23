# Forge Platform — Epistemic Continuity & Information-Topology Preservation Assessment

**Status:** DRAFT — pending distinct-actor peer review per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Authored solo 2026-04-23; R-GOV-01 applies.
**Date:** 2026-04-23
**Theorem source:** *Epistemic Continuity and Information-Topology Preservation for AI Agent Systems* (12 conditions C1–C12, 3 theorems, 5 lemmas) — user-supplied formal specification.
**Scope:** `platform/` only.
**Measured against:** `FORMAL_PROPERTIES_v2.md` (25 atomic properties), `ARCHITECTURE.md`, `GAP_ANALYSIS_v2.md`, `docs/PIPELINE-CONTRACTS.md`, platform source (`app/services/`, `app/api/`).
**Relation to existing docs:** This document maps the theorem's 12 conditions onto the 25 atomic properties in `FORMAL_PROPERTIES_v2.md` and identifies which roadmap phases close each gap. It is a **cross-reference layer**, not a replacement for existing docs.

---

## 0. Theorem summary (operative version)

A multi-stage AI-agent process is **reliable if and only if**, at every stage i, the following all hold:

| ID | Condition | Short name |
|----|-----------|------------|
| C1 | `RequiredInfo(i) ⊆ P_i` | Stage completeness |
| C2 | `Suff(P_i, R_i, A_i, E_<i, T_i) = true` | Stage sufficiency |
| C3 | All information required by stage i is delivered before F_i executes | Timely delivery |
| C4 | `A_i` complete and explicit; ambiguity not hidden in fluent output | Ambiguity exposure |
| C5 | Output derived from P_i, R_i, A_i, E_<i — not from prior substitution | Evidence-grounded transformation |
| C6 | Decision-relevant dependency relations survive decomposition and transfer | Topology preservation |
| C7 | Small semantic refinements cause bounded downstream revision | Continuity of meaning |
| C8 | Each stage adds evidence, reduces ambiguity, increases testability, or refines scope | Additive progression |
| C9 | Explicit testable conditions T_i and deterministic gate G_i per stage | Deterministic evaluation |
| C10 | Incomplete/insufficient context → Stop or Escalate, not ContinueByGuess | Stop-or-escalate |
| C11 | No stage may consume only NL output of prior stages when structured transfer is available | Structured transfer |
| C12 | Every final artifact has a causal chain from documents → decisions → tests → verification → artifact | End-to-end proof trail |

**Degradation theorem (compact):** if any stage k allows prior substitution (missing critical info, process continues), then `Degradation(j) > 0` for all `j ≥ k`.

**Topology theorem:** local plausibility of each step does not imply global correctness if dependency relations are not preserved across stages.

---

## 1. Condition-by-condition assessment

### C1 — Stage completeness: `RequiredInfo(i) ⊆ P_i`

**Forge mapping:** P15 Context Projection

**Current state:** PARTIAL

**What exists:**
- `prompt_parser.py` assembles 7 sections (P0 Operational Contract, P1 Task+ACs, P2 Guidelines, P3 MicroSkills, P4 Knowledge via `kb_scope`, P5 Objectives+KRs, P7 Delivery format).
- `Task.requirement_refs` → SRC-NNN, `Task.origin` → Objective, `Task.completes_kr_ids` → KR.
- Operational contract is always last and never excluded.

**Gap:** `kb_scope` prunes source documents to a token budget without a hard guarantee that task-critical fragments are preserved. If a SRC-NNN fragment required by `requirement_refs` is pruned, `RequiredInfo(i) ⊄ P_i` silently. No pre-LLM alert is raised.

**Risk:** Prior substitution (Degradation theorem) activates at the pruning boundary — the agent fills the gap from statistical priors.

**Closes with:** Phase B Stage B.4 — `ContextProjector.project(task, budget)` replaces `kb_scope` with a causal-graph BFS that guarantees decision-relevant nodes are included before lower-priority content is pruned. Closes C1 fully when P15 is IMPLEMENTED.

**Roadmap phase:** B
**Atomic property:** P15
**Severity:** HIGH

---

### C2 — Stage sufficiency: `Suff(P_i, R_i, A_i, E_<i, T_i) = true`

**Forge mapping:** P8 Evidence Completeness Theorem + P20 Uncertainty Blocks

**Current state:** ABSENT (pre-call), PARTIAL (post-call)

**What exists:**
- `contract_validator` checks output sufficiency post-execution: reasoning length ≥ 100, "why" keyword, file path reference.
- Budget guard prevents call without resource capacity.

**Gap:** Context sufficiency is never verified *before* the LLM call. There is no pre-gate that checks whether `P_i` satisfies `R_i ∪ A_i ∪ T_i` before invoking the agent. Output validation is post-hoc — it catches insufficient *outputs*, not insufficient *inputs*.

**Consequence (Lemma 5):** stages that do not receive sufficient evidence push later stages to fill gaps from priors, increasing hallucination pressure.

**Closes with:**
- Phase F Stage F.4 — `[UNKNOWN]` → `BLOCKED` (P20): agent can surface insufficiency and halt, rather than guess.
- Phase A Stage A.1+A.3 — `EvidenceSet` + `VerdictEngine` with `Gate(a) = 1 ⟺ Req(a) ⊆ Prov(a)` (P8): biconditional enforced by gate, not validator.

**Roadmap phase:** A (gate shape), F (uncertainty block)
**Atomic properties:** P8, P20
**Severity:** HIGH

---

### C3 — Timely delivery

**Forge mapping:** P3 Impact Closure + P7 Universal Gating (sequencing)

**Current state:** SATISFIED (sequencing) / PARTIAL (closure)

**What exists:**
- Pipeline sequence is explicit: `assemble_prompt → budget_check → invoke_claude → validate → verify`.
- Plan gate blocks orchestration if plan has no traceability.
- Budget guard fires before every LLM call.

**Gap:** Timely delivery of *complete* impact information depends on P3 (Impact Closure) being implemented. Currently, a task can receive a prompt without transitive closure of dependencies — the prompt arrives on time, but without full dependency context.

**Closes with:** Phase C — `ImpactClosure(change)` ensures full transitive closure is available at prompt assembly time.

**Roadmap phase:** C (closure), A (sequencing complete with P7)
**Atomic properties:** P3, P7
**Severity:** LOW (sequencing), HIGH (closure completeness)

---

### C4 — Ambiguity exposure: `A_i complete and explicit`

**Forge mapping:** P19 Assumption Control + P20 Uncertainty Blocks

**Current state:** PARTIAL / CRITICAL gap

**What exists:**
- OPEN `Decision` rows created by `/analyze` from source document conflicts and open questions.
- `[CONFIRMED]/[INFERRED]/[ASSUMED]` tagging in deliveries (WARNING level, 3 WARNINGs in validator).
- Operational contract injected into every prompt includes ambiguity disclosure rules.

**Gap (three layers):**
1. `[UNKNOWN]` → WARNING, not BLOCK. Agent continues with missing critical information (direct violation of C10 and C4).
2. OPEN Decisions with `blocking=false` (default) do not prevent task CLAIMING. A task can start while a decision it depends on is unresolved.
3. Ambiguity from one stage does not propagate as an explicit `AmbiguityDependency` to downstream tasks — it is recorded as a `Decision` row but not linked to `Task.blocked_by_decisions` (which does not exist in the model, per GAP_ANALYSIS_v2 §0 correction).

**Consequence (Lemma 1):** stages that receive an ambiguity-stripped context produce falsely precise output — the agent treats unresolved questions as resolved because they are absent from context.

**Closes with:**
- Phase F Stage F.3 — promote WARNING to REJECT for non-trivial untagged claims (P19).
- Phase F Stage F.4 — `BLOCKED` state + uncertainty gate + `POST /executions/{id}/resolve-uncertainty` (P20).
- Phase B Stage B.4 — `ContextProjector` propagates OPEN Decision nodes as explicit ambiguity edges in causal graph (P14+P15).

**Roadmap phase:** F (primary), B (propagation)
**Atomic properties:** P19, P20, P14
**Severity:** CRITICAL

---

### C5 — Evidence-grounded transformation

**Forge mapping:** P16 Evidence Existence + P17 Evidence Source Constraint + P19 Assumption Control + P23 Verification Independence

**Current state:** PARTIAL — detection exists, blocking does not

**What exists:**
- `[CONFIRMED]/[INFERRED]/[ASSUMED]` confabulation check → WARNING on missing tags.
- Git diff gate: phantom files (declared without change) → REJECT.
- Pytest gate: Forge runs tests, maps to ACs.
- Cross-model challenger: independently verifies claims per execution.
- Plan traceability gate: tasks without `requirement_refs` to SRC-NNN → rejected.

**Gap (two critical failures):**
1. `[ASSUMED]` on a non-trivial claim → WARNING (not REJECT). Prior substitution is *detected and logged*, not *blocked*. This is the central failure mode of the degradation theorem.
2. Challenger produces `REFUTED` verdicts → recorded as `Finding` rows, does not re-queue task, does not prevent ACCEPTED. A refuted artifact enters the evidence chain as ACCEPTED.

**Evidence (from GAP_ANALYSIS_v2 §P19):** `IMPLEMENTATION_TRACKER.md:126`: "3 WARNINGs for missing tags" — explicitly WARNING, not FAIL.

**Closes with:**
- Phase F Stage F.3 — promote confabulation WARNING to REJECT (P19).
- Phase F Stage F.6 — ACCEPTED requires deterministic check OR challenge PASS (P23); challenger REFUTED → cannot reach ACCEPTED.
- Phase A Stage A.1+A.3 — `EvidenceSet.kind ∈ {data_observation, code_reference, ...}` rejects `kind=assumption` (P17).

**Roadmap phase:** F (primary), A (evidence shape)
**Atomic properties:** P16, P17, P19, P23
**Severity:** CRITICAL

---

### C6 — Information-topology preservation

**Forge mapping:** P7 Universal Gating + P14 Causal Decision Memory

**Current state:** CRITICAL violation

**What exists:**
- Schema has 10 FK-based causal relations (Task.origin_finding_id, Decision.execution_id, Decision.task_id, Change.execution_id, Change.task_id, Finding.execution_id, Finding.source_llm_call_id, AcceptanceCriterion.source_llm_call_id, AcceptanceCriterion.source_ref, Knowledge.source_ref).
- `Task.requirement_refs` → SRC-NNN traces to source documents.
- `Task.origin` → Objective.external_id preserves planning chain.

**Gap (primary — GAP_ANALYSIS_v2 §P7):** **75 direct `.status = "..."` assignments across 9 files** bypass `GateRegistry`. State transitions are not causal-edge-creating events. When a status changes without going through `VerdictEngine.commit()`:
- No `CausalEdge` row is created.
- No invariants are checked.
- No evidence requirement is verified.
- The topology of the decision-evidence-state graph is silently broken.

This is a direct instantiation of the topology theorem: *local plausibility of each step does not imply global correctness when dependency relations are not preserved*.

**Gap (secondary):** `CausalEdge` table does not exist. DAG structure is implicit in FKs, not queryable as a graph. `ContextProjector` (P15) cannot operate without it.

**Closes with:**
- Phase A Stage A.4 — enforcement cutover: 75 `.status=` sites wrapped through `VerdictEngine.commit()`. Pre-commit grep rejects new violations. **This is the single highest-leverage fix in the roadmap.**
- Phase B Stage B.1–B.3 — `CausalEdge` table + acyclicity + `CausalGraph` service.

**Roadmap phase:** A (primary — Stage A.4), B (graph layer)
**Atomic properties:** P7, P14
**Severity:** CRITICAL

---

### C7 — Continuity of meaning

**Forge mapping:** P2 Continuity

**Current state:** ABSENT

**What exists:**
- Task IDs are remapped at re-plan time to preserve references.
- `Task.requirement_refs` links to SRC-NNN, so requirement-unchanged tasks can be identified in principle.

**Gap:** `ImpactDiff(old, new) → {preserved_ids, changed, ac_invalidated, fraction_changed}` is specified in P2 but not implemented. No service computes the bounded revision set when intent changes. Without this, a one-line requirement edit can silently propagate to unrelated objectives, tasks, and ACs — violating C7.

**Closes with:** Phase C Stage C.1–C.3 — `ImpactClosure` provides the transitive closure needed for `ImpactDiff` to compute bounded revision sets.

**Roadmap phase:** C
**Atomic property:** P2
**Severity:** HIGH

---

### C8 — Additive epistemic progression

**Forge mapping:** P4 Asymptotic Autonomy (quality signal) + P10 Risk-Weighted Coverage

**Current state:** SATISFIED by design (each stage adds structure)

**Assessment:**

| Stage | Epistemic gain |
|-------|----------------|
| Ingest | NL docs → structured `Knowledge` rows with category + PII scan |
| Analyze | NL → `Objectives`, `KeyResults`, OPEN `Decision` rows |
| Plan | Objectives → `Tasks` with ACs, dependency DAG, requirement_refs, KR links |
| Orchestrate/Execute | Tasks → `Execution` with full prompt audit, `TestRun`, `Finding`, CLOSED `Decision`, ADR exports, KR measurement |

No stage paraphrases without structural gain. C8 is satisfied by architectural design.

**Partial risk:** Challenger phase is informational (produces Findings) but does not structurally enrich the artifact. If challenger produces only `NEEDS_REWORK` Finding without blocking, it adds evidence of a problem but does not force resolution — partial C8 non-additivity. Addressed by P23 fix in Phase F Stage F.6.

**Roadmap phase:** None required (satisfied); F Stage F.6 strengthens challenger's structural contribution
**Atomic properties:** P8, P10 (quality measurement)
**Severity:** LOW

---

### C9 — Deterministic stage evaluation

**Forge mapping:** P6 Deterministic Evaluation + P7 Universal Gating

**Current state:** PARTIAL — rule-based validators are deterministic; engine not yet instantiated; toggle risk

**What exists:**
- `plan_gate.py:42` `validate_plan_requirement_refs` — pure function.
- `contract_validator.py` `CheckResult` dataclass — pure-ish (no wall-clock, no randomness).
- `budget_guard` — deterministic threshold check.
- `rate_limiter` — deterministic counter.

**Gap:**
- `VerdictEngine` is specified (P6) but not instantiated — validators run as standalone functions, not as a unified deterministic gate. A gate registry does not exist.
- `VERDICT_ENGINE_MODE` toggle: if default is `off` or `shadow`, the gate is non-enforcing by default. Default value is not documented.
- 75 direct `.status=` sites (C6 gap) also violate C9 — transitions without explicit `T_i`.

**Closes with:**
- Phase A Stage A.2–A.4 — `GateRegistry` + `VerdictEngine` in shadow then enforce mode.
- Phase A Stage A.3 — replay harness for determinism verification.

**Roadmap phase:** A
**Atomic properties:** P6, P7
**Severity:** HIGH

---

### C10 — Stop-or-escalate on incomplete context

**Forge mapping:** P20 Uncertainty Blocks + P7 Universal Gating (hard stops)

**Current state:** PARTIAL — some hard stops exist; critical path (unknown → block) absent

**What exists (hard stops):**
- Budget guard → HTTP 402 before LLM call.
- Plan traceability gate → HTTP 400 on missing requirement_refs.
- `stop_on_failure=True` (default) → orchestration loop breaks on task failure.
- Rate limiter → HTTP 429.

**Gap:**
- `[UNKNOWN]` → WARNING, agent continues. Phase F (BLOCKED status) not implemented.
- No pre-gate checking context completeness or sufficiency before LLM invocation (beyond budget).
- Confabulation detected post-call, not pre-call — agent has already substituted priors by the time WARNING fires.

**Consequence (Degradation Theorem):** this is the primary activation point for epistemic degradation. When `MissingCriticalInfo(k) = true` and the process continues (`ContinueByGuess(k)`), `Degradation(j) > 0` for all `j ≥ k`.

**Closes with:** Phase F Stage F.4 — `BLOCKED` status + `uncertainty_state` JSONB + resolve-uncertainty endpoint (P20). **Highest priority for soundness.**

**Roadmap phase:** F (BLOCKED), A (gate architecture)
**Atomic properties:** P20, P7
**Severity:** CRITICAL

---

### C11 — Structured transfer (not summaries)

**Forge mapping:** P14 Causal Decision Memory + P15 Context Projection + P22 Disclosure Protocol

**Current state:** PARTIAL — intra-pipeline strong; challenger weak

**What exists:**
- Pipeline transfer between stages is entity-based: `Knowledge`, `Objective`, `Task`, `AcceptanceCriterion`, `Execution` rows. `prompt_parser` reconstructs context from entities, not from summaries of prior LLM outputs.
- `PromptSection` + `PromptElement` provide full audit trail of what was sent to each LLM call.

**Gap:**
- **Challenger** (Phase C in orchestration loop) receives the **NL delivery text** of the executor, not the structured entity chain. Per Lemma 3: summary-only transfer destroys second-order constraints (why a requirement exists, what risk it mitigates, which tests are mandatory, which tradeoff was chosen). The challenger cannot verify claims against structured evidence — it can only check internal consistency of prose.
- Without `CausalEdge` graph (C6 gap), `ContextProjector` cannot provide structured minimal-justification-frontier — `kb_scope` uses keyword-based scoping.

**Closes with:**
- Phase B Stage B.3–B.4 — `CausalGraph` + `ContextProjector`: challenger and subsequent stages receive structured projection, not NL summary.
- Phase F Stage F.6 — challenger required to verify against EvidenceSet, not delivery prose.

**Roadmap phase:** B (projection), F (challenger strengthening)
**Atomic properties:** P14, P15
**Severity:** HIGH

---

### C12 — End-to-end proof trail

**Forge mapping:** P14 Causal Decision Memory + P15 Context Projection + P12 Operational Self-Adjointness

**Current state:** PARTIAL — chain designed, C6 violations create gaps

**What exists:**
Chain exists in design:
```
Knowledge(SRC-NNN)
  → Task.requirement_refs
  → Task.acceptance_criteria
  → Execution (prompt audit: PromptSection + LLMCall)
  → TestRun (per-AC results)
  → Finding / Decision (extracted from delivery)
  → Decision.ADR (auto-exported to .ai/decisions/)
  → KR.current_value (updated by kr_measurer)
  → Objective.status
```

Every `LLMCall` is logged (prompt hash, full text, tokens, cost). ADR exports from CLOSED Decisions.

**Gap:**
- C6 gap (75 `.status=` violations) means some state transitions have no `CausalEdge` → proof trail has unexplained gaps between states.
- `CausalEdge` table does not yet exist — the chain above lives in FK relations, not in a queryable DAG.
- `CAUSAL_PROJECTION = false` (config toggle) disables the projection mechanism — the chain is not delivered to agents when this flag is off.
- Challenger REFUTED artifacts enter the chain as ACCEPTED without a blocking edge (C5 gap).

**Closes with:**
- Phase A Stage A.4 — closes the 75-violation gap in the chain.
- Phase B Stage B.1–B.3 — `CausalEdge` table makes the chain queryable.
- Phase F Stage F.6 — challenger REFUTED → cannot reach ACCEPTED (closes refuted-artifact gap in chain).

**Roadmap phase:** A (critical), B (graph), F (challenger)
**Atomic properties:** P14, P15, P7
**Severity:** HIGH (CRITICAL if proof trail is a compliance requirement)

---

## 2. Aggregate assessment

### 2.1 Summary table

| Condition | Status | Severity | Primary closes |
|-----------|--------|----------|----------------|
| C1 Stage completeness | PARTIAL | HIGH | Phase B (P15) |
| C2 Stage sufficiency | ABSENT | HIGH | Phase A+F (P8, P20) |
| C3 Timely delivery | SATISFIED (seq) / PARTIAL (closure) | LOW/HIGH | Phase C (P3) |
| C4 Ambiguity exposure | PARTIAL / CRITICAL GAP | CRITICAL | Phase F (P19, P20), Phase B (P14) |
| C5 Evidence-grounded | PARTIAL — detect not block | CRITICAL | Phase F (P19, P23), Phase A (P17) |
| C6 Topology preservation | CRITICAL — 75 violations | CRITICAL | Phase A Stage A.4 (P7), Phase B (P14) |
| C7 Continuity of meaning | ABSENT | HIGH | Phase C (P2) |
| C8 Additive progression | SATISFIED | LOW | — |
| C9 Deterministic evaluation | PARTIAL | HIGH | Phase A (P6, P7) |
| C10 Stop-or-escalate | PARTIAL | CRITICAL | Phase F Stage F.4 (P20) |
| C11 Structured transfer | PARTIAL | HIGH | Phase B (P14, P15) |
| C12 Proof trail | PARTIAL | HIGH | Phase A+B+F (P7, P14) |

**Tally:** 4 CRITICAL, 7 HIGH, 1 LOW. No condition fully satisfied. Two satisfied by design (C3 sequencing, C8).

### 2.2 Three systemic diseases

#### Disease 1 — Prior substitution detected, not blocked (C4, C5, C10)

The central failure mode of the degradation theorem: `[UNKNOWN]` and `[ASSUMED]` on non-trivial claims generate WARNINGs, not REJECTs. The agent continues with missing critical information. Downstream artifacts inherit epistemic degradation proportional to the missing information.

**Root:** Phase F Stage F.4 (`BLOCKED` state) and Stage F.3 (WARNING → REJECT) are unimplemented.

**Fix:** Phase F (highest priority for soundness).

#### Disease 2 — Universal Gating on paper, not in code (C6, C9, C12)

75 direct `.status=` assignments bypass `GateRegistry`. State transitions are not causal-edge-creating events. The topology theorem applies: *local plausibility of each step does not imply global correctness when dependency relations are not preserved*.

**Root:** Phase A Stage A.4 not yet executed.

**Fix:** Phase A Stage A.4 (highest leverage change — closes C6, contributes to C9 and C12).

#### Disease 3 — Challenger informational, not blocking (C5, C8, C12)

Cross-model verification (P23) exists but is optional and non-blocking. `REFUTED` verdict creates a Finding but does not prevent ACCEPTED. A refuted artifact enters the proof trail as accepted evidence — directly breaking C5 (evidence-grounded) and C12 (proof trail integrity).

**Root:** Phase F Stage F.6 not yet executed.

**Fix:** Phase F Stage F.6.

---

## 3. Priority order for soundness

The following order minimises time-to-sound-process. Each item is ordered by: (a) severity, (b) number of conditions it closes, (c) blast radius (smaller = earlier).

### Priority 1 — Fix 75 `.status=` violations (Universal Gating)

**Closes:** C6 (primary), C9 (partial), C12 (gap reduction)
**Atomic property:** P7
**Roadmap stage:** Phase A Stage A.4
**Why first:** This is the widest topology breach. Every state transition that bypasses VerdictEngine potentially breaks a causal edge, violates an invariant, and creates a gap in the proof trail. It is also mechanically testable with a grep invariant — zero ambiguity in the acceptance criterion.

**Prerequisite:** Phase A Stage A.1–A.3 (EvidenceSet entity, GateRegistry, VerdictEngine shadow mode). These must come first.

**Implementation path:**
1. Stage A.1: `EvidenceSet` entity + Alembic migration (additive, 0 blast radius).
2. Stage A.2: `GateRegistry` static dict (additive, 0 blast radius).
3. Stage A.3: `VerdictEngine` in shadow mode — 1 week of production traffic with divergence logging.
4. Stage A.4: enforce mode — wrap all 75 sites; pre-commit grep gate.

---

### Priority 2 — Implement Phase F Stage F.4: BLOCKED state for `[UNKNOWN]`

**Closes:** C4 (primary), C5 (partial), C10 (primary)
**Atomic property:** P20
**Roadmap stage:** Phase F Stage F.4
**Why second:** This closes the degradation theorem's primary activation trigger. Without BLOCKED status, the process structurally cannot satisfy C10. Agent continues by guess at every `[UNKNOWN]` → all downstream output epistemically degraded.

**Implementation:**
1. Add `BLOCKED` to `Execution.status` enum. Alembic migration (additive, down-migration: per ADR-011).
2. Add `Execution.uncertainty_state` JSONB.
3. Pipeline refuses ACCEPTED while `uncertain ≠ ∅` on non-trivial claims.
4. `POST /executions/{id}/resolve-uncertainty` — human ACK with `[ASSUMED: accepted-by=<role>, date=YYYY-MM-DD]`.

---

### Priority 3 — Promote confabulation WARNING to REJECT (Assumption Control)

**Closes:** C4 (partial), C5 (primary)
**Atomic property:** P19
**Roadmap stage:** Phase F Stage F.3
**Why third:** Closes prior substitution for the case where agent produces output with non-trivial untagged claims. Currently 3 WARNING paths in `contract_validator` that should be REJECT per CONTRACT §A.

**Implementation:** Single change in `contract_validator.py` — promote `CheckResult.WARNING` to `CheckResult.FAIL` for non-trivial claim + missing tag. Add non-trivial classifier (7-trigger definition from CONTRACT.md).

---

### Priority 4 — Make challenger blocking (Verification Independence)

**Closes:** C5 (partial), C8 (challenger contribution), C12 (proof trail)
**Atomic property:** P23
**Roadmap stage:** Phase F Stage F.6
**Why fourth:** Closes the "refuted-artifact-as-accepted-evidence" gap. ACCEPTED must require either deterministic check OR challenger PASS. Without this, REFUTED findings enter the proof trail without stopping the artifact.

**Implementation:**
1. Change orchestration loop: challenger `NEEDS_REWORK` or `FAIL` verdict → task re-queued with fix_hint (not just Finding row).
2. `Execution.status = ACCEPTED` requires `verified_by_check ∈ {"grep", "test", "typecheck"}` OR `forge_challenge` verdict `PASS`.

---

### Priority 5 — Set `VERDICT_ENGINE_MODE=enforce` as default

**Closes:** C9 (deterministic evaluation guarantee)
**Atomic property:** P6
**Roadmap stage:** Phase A Stage A.4 (part of enforcement cutover)
**Why fifth:** Without `enforce` as default, all other gate-level fixes are opt-in. One misconfigured deployment reduces the system to pre-A state.

**Implementation:** Change default in `app/config.py`. Document opt-out path. Note: depends on shadow mode running cleanly first (Stage A.3).

---

### Priority 6 — Ratify FORMAL_PROPERTIES_v2.md (ADR-003)

**Closes:** R-GOV-01 (foundational risk blocking all downstream)
**Roadmap stage:** Pre-flight Stage 0.1
**Why sixth (but logically first):** Without distinct-actor ratification, all 25 properties and this assessment are DRAFT. No phase A PR can be binding. However, ratification is a human governance step, not a code step — it can proceed in parallel with Priorities 1–5 being designed (but not merged).

**Implementation:** File `docs/reviews/review-ADR-003-by-<actor>-<date>.md`. Update ADR-003 status → RATIFIED.

---

### Priority 7 — Phase B: CausalEdge + ContextProjector

**Closes:** C1 (partial), C6 (graph layer), C11 (structured transfer), C12 (queryable chain)
**Atomic properties:** P14, P15
**Roadmap stage:** Phase B
**Why seventh:** Enables the full proof trail and replaces `kb_scope` with a graph-aware projector. Depends on Phase A (VerdictEngine must be the single write path before CausalEdge can be reliably populated).

---

## 4. Mapping: theorem conditions → atomic properties → roadmap phases

| Theorem condition | Closes atomic properties | Primary roadmap phase | Secondary |
|-------------------|--------------------------|-----------------------|-----------|
| C1 Stage completeness | P15 | B | — |
| C2 Stage sufficiency | P8, P20 | A, F | — |
| C3 Timely delivery | P3, P7 | C, A | — |
| C4 Ambiguity exposure | P19, P20, P14 | F | B |
| C5 Evidence-grounded | P16, P17, P19, P23 | F | A |
| C6 Topology preservation | P7, P14 | **A (Stage A.4)** | B |
| C7 Continuity of meaning | P2 | C | — |
| C8 Additive progression | P8, P10 | (satisfied) | F |
| C9 Deterministic evaluation | P6, P7 | A | — |
| C10 Stop-or-escalate | P20, P7 | **F (Stage F.4)** | A |
| C11 Structured transfer | P14, P15 | B | F |
| C12 Proof trail | P14, P15, P7 | A + B | F |

**Observation:** Phase A and Phase F are co-critical. Phase A closes the topology/gate layer (C6, C9) and Phase F closes the epistemic-discipline layer (C4, C5, C10). Neither alone is sufficient for soundness.

---

## 5. Lemma alignment

| Lemma | Description | Forge manifestation | Fix |
|-------|-------------|--------------------|----|
| L1 Missing ambiguity propagation → false determinacy | OPEN Decisions not linked to downstream tasks; `[UNKNOWN]` → WARNING | Phase F F.4 (BLOCKED) + B (CausalEdge propagation) |
| L2 Missing evidence propagation → synthetic justification | Challenger receives NL prose; EvidenceSet not yet linked to Decisions | Phase A (EvidenceSet) + B (ContextProjector) + F (F.6 blocking challenger) |
| L3 Summary-only transfer destroys high-order constraints | Challenger sees delivery text, not structured evidence chain | Phase B B.3–B.4 (CausalGraph + ContextProjector for challenger) |
| L4 Broken continuity amplifies revision cost | No ImpactDiff; one-line change can propagate unpredictably | Phase C C.1–C.3 (ImpactClosure + ImpactDiff) |
| L5 Non-additive stages increase hallucination pressure | Context pruning without guarantee (C1 gap); insufficient input context (C2 gap) | Phase B B.4 (ContextProjector), Phase F F.4 (BLOCKED) |

---

## 6. What is already sound (strengths)

The following elements are architecturally sound and do not require remediation:

| Element | Theorem support |
|---------|----------------|
| Operational contract injection into every prompt (never excluded) | C5 partial (behavioral) |
| Plan Traceability Gate (hard C10 for unanchored tasks) | C10 partial |
| Full prompt audit trail (`PromptSection`, `LLMCall`) | C12 partial |
| Entity-based inter-stage transfer (not NL summaries) | C11 (intra-pipeline) |
| ADR auto-export from CLOSED Decisions | C12 partial |
| Budget guard before every LLM invocation | C3 (resource gate) |
| `stop_on_failure=True` default | C10 (task-level stop) |
| `AcceptanceCriterion.scenario_type` 4-category taxonomy | C8 (partial testability) |
| Cross-model challenger architecture (direction correct) | C5 (direction), P23 (needs blocking enforcement) |
| 10 FK-based causal relations in schema | C12 (partial chain exists) |

---

## 7. Relationship to `FORMAL_PROPERTIES_v2.md` and `ROADMAP.md`

This document is **additive**, not a replacement:

- `FORMAL_PROPERTIES_v2.md` defines the 25 atomic properties that Forge must satisfy. It is the engineering spec.
- `GAP_ANALYSIS_v2.md` maps the gap between current state and those 25 properties.
- `ROADMAP.md` defines the 7-phase implementation plan closing those gaps.
- **This document** maps the formal theorem's 12 conditions (C1–C12) onto those properties and surfaces which conditions are critical, which phases close them, and in what order.

The theorem adds three structures not explicit in the existing docs:
1. **The degradation theorem** — a single prior-substitution event at stage k degrades all subsequent stages. This justifies making Phase F Stage F.4 (BLOCKED) a hard prerequisite for soundness claims, not just a "nice to have".
2. **The topology theorem** — local correctness of each step does not guarantee global correctness without topology preservation. This justifies treating the 75 `.status=` violations (Phase A Stage A.4) as the single highest-leverage fix before any other work.
3. **Lemma 3 (summary transfer)** — challenger receiving NL output instead of structured evidence is not a minor gap. It structurally prevents second-order constraint verification.

These three additions modify the *priority ordering* of the existing roadmap, not its content. See `ROADMAP.md §18` for the updated priority quickstart.

---

## 8. Open questions (require decisions before implementation)

| # | Question | Blocks | ADR |
|---|----------|--------|-----|
| Q1 | When `[UNKNOWN]` is declared on a non-trivial claim, what is the maximum TTL before auto-escalation to a named actor? | Phase F F.4 | ADR-011 |
| Q2 | Does challenger REFUTED require immediate task re-queue, or can a human reviewer accept the finding and override? | Phase F F.6 | ADR-013 (new) |
| Q3 | What is the token-budget priority order in `ContextProjector.project()`? (must-guidelines → recent decisions → evidence → knowledge is proposed but not fixed) | Phase B B.4 | ADR-004 (calibration) |
| Q4 | Does C2 sufficiency require a pre-LLM gate, or is the post-hoc contract_validator sufficient for the current maturity level? | Phase A exit | ADR-014 (new) |
| Q5 | Should `BLOCKED` be a terminal state requiring explicit human resolution, or can it auto-unblock after a TTL with an auto-`[ASSUMED]` annotation? | Phase F F.4 | ADR-011 |

---

*This document is DRAFT. Not binding until ADR-003 ratified and distinct-actor review filed in `docs/reviews/`.*

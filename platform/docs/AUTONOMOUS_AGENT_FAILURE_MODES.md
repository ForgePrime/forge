# Autonomous Agent Failure Modes

> **Status:** DRAFT per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Pending distinct-actor review.
>
> **Date:** 2026-04-23
> **Scope:** Failure analysis for a fresh autonomous Claude agent executing ROADMAP Pre-flight → Phase G without human-in-the-loop.
> **Theorems in scope:** `Engineer_Soundness_Completeness.md` §1–§8, `Evidence_Constrained_Planning_Theorem.md` §1–§17.
> **Purpose:** Input to ROADMAP Phase F structural requirements (§F.7–F.9) and Phase G.4 Rule Lifecycle.

---

## 0. Why this document exists

A solo-author agent executing the ROADMAP has no external check on its own gate design. Every gate it writes, it also passes — this is Pathology 2.1 Fluent Wrongness from `WHITEPAPER.md` applied to governance itself. This document maps where that failure manifests structurally, so that ROADMAP phases can close the gaps mechanically rather than through discipline.

Three root causes drive all failure modes below:

1. **Authority vacuum** — agent cannot distinguish "I have permission to decide this" from "I am filling a gap nobody else will fill."
2. **Skip economics** — skipping a governance step is cheaper in tokens than doing it; under budget pressure the wrong choice is the cheap one.
3. **Solo-verifier loop** — agent produces artifact, agent ratifies artifact, in the same session, from the same priors. CONTRACT §B.8.

---

## 1. Where the agent does not know what to do

### 1.1 Calibration constants undefined

`FORMAL_PROPERTIES_v2.md §7` requires: τ (risk bound), α (coverage floor per capability), W (rolling window for Q_n), q_min (autonomy floors, 4 values × 5 levels = 20 numbers), idempotency TTL, clock-skew tolerance, ImpactClosure review-cost threshold. ADR-004 does not exist yet.

**Failure pattern:** Agent fills plausible defaults without marking them `[ASSUMED]`. Later phases treat those defaults as `[CONFIRMED]` calibration. P19 violation invisible.

**Break condition:** Phase A.5 idempotency TTL, Phase D.5 α-gate, Phase E.3 q_min floors — all silently wrong.

### 1.2 Decision boundaries without rules

| Situation | Agent behaviour | Consequence |
|---|---|---|
| Change touches `validation/` + `governance/` simultaneously | Picks one owner arbitrarily | Review gap in the other mode |
| Conflicting invariants I1 ⟹ X and I2 ⟹ ¬X on same transition T | Both fail silently | No gate blocks the transition |
| Property P13 deprecated in v2.1 docs | Agent in 2027 reads FORMAL_PROPERTIES_v2 — no deprecation marker | Works against retired constraint |
| Forge Steward not staffed; quarterly audit demands a decision | Agent either stops (no progress) or fills authority (silent usurpation) | Governance theatre or unauthorized ADR |
| Delivery REJECTED → fix → REJECTED (loop) | Reaches budget cap; 10 identical attempts | No quality signal, just cost |

### 1.3 Non-trivial classifier under pressure

CONTRACT.md defines 7 triggers + 3 trivial exceptions. Uncovered edge cases:
- Renaming a private API field (public-ish? cascade-ish?)
- Adding `Optional` kwarg with default (changes contract? or trivial?)
- Changing retry count 3 → 5 (timing trigger? or trivial?)

Under session pressure, agent under-tags → P19 violation invisible in delivery log.

`Evidence_Constrained_Planning §5`: tagging requires `Decidable(claim)`. When decidability is uncertain, agent defaults to `[ASSUMED]` (allows proceeding) rather than `[UNKNOWN]` (blocks). This is the wrong default.

### 1.4 UNKNOWN escalation with no receiver

P20: `U ≠ ∅ ⟹ STOP`. In autonomous setup, STOP = stall with no resolution path. Agent resolves by converting `[UNKNOWN]` → `[ASSUMED: accepted-by=auto]` — which is CONTRACT §B.8 violation. No `ScheduleWakeup` equivalent exists for subagents spawned via `Agent` tool.

---

## 2. Where information is lost

### 2.1 Cross-session loss

- Conversation context does not persist. `MEMORY.md` entries are ~150-character pointers — they do not carry rationale from a 3-hour session.
- Cialdini-style self-rationalizations: session N catches "this is just a simple question" → skips a step → self-corrects. Session N+1 has no memory of the correction → re-rationalizes from scratch.
- Hallucination corrections: session N establishes "MINIMAL crosstalk" per ADR-002 §Premise Correction. Session N+1 reads outer CLAUDE.md first, re-hallucinates MINIMAL until ADR-002 is read. Memory entry says "treat as hallucination" — but memory ages and trust decays.

### 2.2 Incomplete projection

`Phase B.4 ContextProjector` cuts the causal graph to `budget_tokens`. A fact that is SUBTLE-relevant but not linked via `scope_tags ∪ requirement_refs` is silently discarded. Agent receives an incomplete projection **and does not know what is missing** — this violates `Evidence_Constrained_Planning §6` (Evidence Completeness) structurally, not just occasionally.

`PromptSection truncation`: P4 SHOULD-guidelines are truncatable under budget. Silent rule-loss.

### 2.3 Clock-dependent state

`last_executed_at`, `lease_expires_at`, rolling window W — all clock-dependent. Session at 10:00 vs 14:00 sees different state → different autonomy promotion decision → idempotency broken deterministically.

### 2.4 Implicit invariants not registered

- `"Task.DONE ⟹ all AC PASS"` — not in any Invariant entity until Phase E.2. Agent can mark Task DONE without checking all AC.
- Tribal knowledge (e.g. "settlement queries must use freeze date, not current date" — incident `6ee9561`) exists in `PRACTICE_SURVEY.md` but agent does not have to read PRACTICE_SURVEY to execute a task.

---

## 3. Where differentiability breaks (Continuity P2)

Small input change → uncontrolled large output change:

| # | Change | Effect |
|---|---|---|
| 1 | τ: 0.3 → 0.4 (~3% delta) | Many gates flip FAIL → PASS; all historical REJECTEDs become retroactively ambiguous |
| 2 | ADR-001 adds `scenario_type='concurrent'` | `contract_validator:193` rule requires PASS on `negative/edge_case` — concurrent-only task always fails; local enum change, global validator break |
| 3 | Model version bump | Zero prompt changes; 100% delivery quality change. Agent cannot distinguish model regression from its own error |
| 4 | Phase F adds P19 validator retroactively | Historical ACCEPTED executions (pre-F) pass; same executions post-F would FAIL. Temporal idempotency incomplete |
| 5 | CausalEdge backfill v1.0 → v1.1 (FK semantic change) | Same rows, different edge semantics; downstream graph queries return different results |
| 6 | Side-effect added to `plan_gate` (db.add inside) | `RuleAdapter` still treats it as pure; VerdictEngine purity assumption silently violated |

---

## 4. Where idempotency breaks (P1)

Theoretical: T(T(x)) = T(x). Practical failures:

| # | Source | Mechanism |
|---|---|---|
| 1 | LLM inherent non-determinism | temperature=0, same prompt, same model — different output across sessions. Forge pins model version; generation remains probabilistic |
| 2 | Retry/learn loop | REJECTED → fix_report → resubmit. Micro-context differences (lease_renewals, attempt_number) change reasoning output |
| 3 | Clock in autonomy ledger | Q_n rolling window depends on `now()`. 10:00 session vs 14:00 session → different success_rate → different promotion decision |
| 4 | CausalEdge insert order | Backfill order change + clock-based acyclicity trigger (`src.created_at < dst.created_at`) → different edges accepted/rejected |
| 5 | Budget guard state | `spent_usd` at 79% (morning) vs 81% (evening) — veto fires vs not. Same task, different verdict based on state outside input hash |
| 6 | IdempotentCall TTL boundary | Same `(tool, key, args_hash)` after TTL expiry = new execution. Idempotency is scoped, not absolute |

---

## 5. Where work degrades over time

Silent rot undetected by the system:

| # | Mode | Detection gap |
|---|---|---|
| 1 | **Doc rot** (R-HAL-01) | `file:line` citations in v2.1 docs; 15–30% stale after 3 months. Agent in Phase E.5 receives false premises. CHANGE_PLAN_v2 v1 had 2 hallucinations from this |
| 2 | **Test rot** | Property tests (Phase D.2) written against API shape at that moment. Phase E.1 ContractSchema refactor changes shape. Tests compile (mocked fixtures) but assert deprecated properties. Greenlight without guarantee |
| 3 | **Calibration drift** | ADR-004 sets α=0.8. Session N+50: agent sees 60% capabilities below α → silently adjusts to 0.6 "because production evidence suggests". No new ADR. P19 violation in a doc with no enforced validator |
| 4 | **Shadow mode permanence** | `VERDICT_ENGINE_MODE=shadow` is "safe". Zero divergence for 1 week = no risk to stay in shadow. Shadow becomes permanent theatre; VerdictEngine runs parallel without blocking anything |
| 5 | **Challenger capture** | Challenger is LLM of same model version as primary agent → shared blindspots. Both accept the same error. P23 Verification Independence degrades to P6 Determinism |
| 6 | **Metric 4 gaming** (R-PLAN-05) | Agents learn output structure to pass validator. `contract_violations.disclosed` drops to zero — but `detected_downstream` also drops (detection = validator, captured). Ratio appears healthy |
| 7 | **Rule bloat** (OM §4.3) | Phase G.4 Rule Lifecycle: rules retire when "no evidence of prevention in 12 months." Evidence of prevention is not tracked. Retirement never triggers. Rulebook unreadable in 18 months |
| 8 | **Partial phase compounding** | Phase A ships "75 sites wrapped" but misses site 76. Phase B.1 assumes VerdictEngine universality. Phase F.4 BLOCKED state assumes all rejections flow through VerdictEngine. Miss in Phase A = structural hole in Phase F |
| 9 | **Theorem drift** | `Engineer_Soundness` evolves from v1 → v2 (new properties). Agent that read v1 and was not alerted to update works against retired spec. No theorem versioning in `.ai/theorems/` |

---

## 6. Engineer_Soundness §1–§8 — failure map

| § | Property | Autonomous failure mechanism |
|---|---|---|
| §1 Deterministic Evaluation | Validation returns same result for same inputs | Breaks when: (a) LLM-in-loop review of rationale (inherent non-det); (b) calibration not closed (agent picks variable); (c) VerdictEngine rule has hidden clock/rand (e.g. `last_executed_at`); (d) scenario_generator heuristic edited by agent in Phase D |
| §2 Evidence Sufficiency | `Accept(h) ⟹ Suff(E(h), h)` | Breaks when: (a) "sufficient" is subjective (no mechanical check for `sufficient_for rule_id` match); (b) `IMPLEMENTATION_TRACKER [EXECUTED]` treated as `[CONFIRMED]` without §B.8 transitivity; (c) cross-session evidence loss before Phase A EvidenceSet |
| §3 Root Cause Uniqueness | `∃! h` consistent with Data | Breaks when: (a) parallel sessions generate conflicting `Decision(type=root_cause)`; (b) alternative rejection reasoning = fluent wrongness (agent self-serving); (c) domain expertise gap → agent fabricates confidence; (d) Phase F.5 requires ≥2 alternatives — validator does not check quality of rejection reasoning |
| §4 Impact Completeness | `Impact(Δ) = Closure(deps)` | Breaks when: (a) ImportGraph covers only static Python — dynamic dispatch (`getattr`), cross-service data-flow, cross-repo missed; (b) `@side_effect` requires manual tagging — new function without tag = silent gap; (c) closure stops at repo boundary — vendor deps invisible; (d) ordering side-effects (queue publish order) not modelled |
| §5 Invariant Preservation | `Invariant(x) ⟹ Invariant(F(x))` | Breaks when: (a) `check_fn` format not closed (R-SPEC-02); (b) implicit invariants not registered (`"Task.DONE ⟹ all AC PASS"`); (c) cross-entity invariants hard to formalize; (d) conflicting invariants without meta-rule; (e) clock-dependent invariants = non-idempotent |
| §6 Evidence Completeness | `RequiredEvidence(a) ⊆ ProvidedEvidence(a)` | Breaks when: (a) Required is JSONB free-form pre-Phase-E ContractSchema → agent interprets; (b) verifiability pre-Phase-F.2 not enforced → evidence can be a fabricated citation; (c) cross-session loss; (d) context projection miss (Phase B.4) → agent does not know what it does not have |
| §7 Failure-Mode Coverage | `∀ m ∈ FailureModes: Covered(m)` | Breaks when: (a) FailureMode registry seeded by humans — agent cannot invent modes it does not know; (b) `w_m` risk weights require calibration — agent fills plausible values; (c) unknown-unknowns: entire categories missed; (d) domain-specific modes (race in vendor driver) require a specialist; (e) coverage formula covers only KNOWN modes |
| §8 Proof of Correctness | `F(x) = Spec(x) ∀ valid x` | Breaks when: (a) Spec is DRAFT per ADR-003 — agent has no NORMATIVE target; (b) passing all gates ⟹ high confidence — but gates themselves have bugs (R-SPEC-03 hidden contradictions); (c) property tests sample infinite space — probability ≠ proof; (d) Spec silent on dimensions that matter (a11y, i18n, latency tail) |

---

## 7. Evidence_Constrained_Planning — additional failures

Five properties where autonomous agent breaks most severely:

**§3 Shortcut economics** (`Cost(skip) > Cost(step)`): in autonomous setup, skip is cheaper — a SKIP block costs ~15 tokens; doing the step costs ~500. Token economics defeats the rule. Structural fix: SKIP BLOCK must be *longer* than the work it skips — i.e. force a justification that exceeds the cost of doing the step.

**§6 UNKNOWN stop rule** (`U ≠ ∅ ⟹ STOP`): STOP = stall with no escalation path in subagent context. Agent resolves by converting `[UNKNOWN]` → `[ASSUMED: accepted-by=auto]`. This is CONTRACT §B.8 violation. Requires a mechanism to wake the user — not available in `Agent` tool invocations.

**§8 Prediction consistency** (`|Actual − Predicted| / Predicted > 0.5 ⟹ Explanation required`): explanation produced by the same agent = fluent wrongness risk. Without a distinct-actor cross-check, "discovered more during implementation" always self-satisfies.

**§9 Read-before-plan**: agent with hard budget limit reads only files in the projection. If a claim references `file.py` but projection excluded it — agent cites without reading. No validator checks whether the file was actually opened via a tool in this session.

**§13 Self-check honesty** (`∃ NotVerified(P) ∨ ProofOfNoUnverified(P)`): under pressure, agent writes "all verified" without proof. Structural fix: form must require an explicit NotVerified list with ≥1 entry, or a formal justification for an empty list. Without enforcement, agent will skip.

---

## 8. Three structural requirements to prevent collapse

These are the minimum mechanical changes. Discipline does not substitute for them.

### SR-1: AgentAuthorityCheck gate (pre-phase)

Before any phase begins, a gate must answer:

```
AgentAuthorityCheck(phase) → {authorized: bool, missing_premises: List[str]}
```

If `calibration not CLOSED`, `Steward not staffed`, or `user unreachable` → `FAIL FAST`, do not fabricate.

**Implements:** closes gap §1.1, §1.2 (Steward), §1.4.

### SR-2: Skip-cost enforcement

Every governance step output slot must be visible (filled or explicitly empty). A SKIP BLOCK must be structurally longer — in required justification — than executing the step. This is already partially in `/plan` skill; it must be echoed by the Forge VerdictEngine for every agent work step, not only during planning.

**Implements:** closes Evidence_Constrained_Planning §3, §13.

### SR-3: Distinct-actor mandatory for rationale ratification

An agent cannot ratify its own rationale in the same session. This is CONTRACT §B.8, R-GOV-01, ADR-003. In an autonomous loop, the agent MUST have a mechanism to spawn a distinct-actor review. Without this:

- §1 Deterministic Evaluation breaks (agent reviews its own verdicts)
- §3 Root Cause Uniqueness breaks (agent self-selects hypothesis)
- §8 Proof of Correctness breaks (agent passes gates it wrote)

**Implements:** closes R-GOV-01. Depends on ADR-003 ratification (Stage 0.1).

---

## 9. ROADMAP cross-reference

New stages added to ROADMAP.md per this document:

| Stage | Phase | Description |
|---|---|---|
| F.7 | F | `AgentAuthorityCheck` gate — pre-phase authority check per SR-1 |
| F.8 | F | Skip-cost structural enforcement in VerdictEngine per SR-2 |
| F.9 | F | Distinct-actor spawn mechanism in autonomous loop per SR-3 |
| G.4+ | G | Rule prevention tracking (closes §5.7 rule bloat) — log which rule blocked which rejection |
| ADR-012 | Pre-flight | Non-trivial classifier edge cases (§1.3) — closes ADR-010 gap for ambiguous cases |

---

## 10. Open questions (UNKNOWN — blocked per P20)

These cannot be resolved by this document alone. They require human decision before the dependent phase starts.

| # | Question | Blocks |
|---|---|---|
| Q1 | Who seeds FailureMode registry for domain-specific modes (§7)? What is the minimum set before Phase D.5 starts? | Phase D.5 |
| Q2 | What is the give-up policy for REJECTED → fix → REJECTED loops? Max N attempts? Quality threshold? | Phase F (delivery protocol) |
| Q3 | How does an autonomous agent escalate UNKNOWN when running as a subagent with no ScheduleWakeup? | SR-3, Phase F.4 |
| Q4 | Theorem versioning: who is responsible for updating `.ai/theorems/` when a theorem evolves? What is the notification mechanism? | All phases |

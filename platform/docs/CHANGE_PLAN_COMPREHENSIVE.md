# CHANGE_PLAN_COMPREHENSIVE — Adversarial Synthesis of 6 Functional Plans

> **Status:** **DRAFT** — not binding. Requires distinct-actor review per ADR-003 before any implementation decision may reference this document. Every analytical conclusion in Sections 2, 3, 4, 5, 7 is [ASSUMED: agent-analysis, requires-distinct-actor-review] per CONTRACT §B.8 solo-verifier rule. Only direct file citations carry [CONFIRMED].
>
> **Date:** 2026-04-24
>
> **Author:** commissioning AI agent (solo — same actor authored 5 of 6 plans; solo-verifier bias disclosed per CONTRACT §A.6).

---

## Section 0: Status block and read confirmation

```
Status: DRAFT — not binding. Requires distinct-actor review per ADR-003 before
        implementation decision may reference this document.
Date: 2026-04-24
Calibration constants status: ADR-004 OPEN (skeleton committed; values pending
  domain expert). All boundary threshold judgments in Section 2b are
  [UNKNOWN: blocked by ADR-004].
Stage 0.3 smoke tests: NOT-RUN. All GAP_ANALYSIS_v2 code-state claims are
  [ASSUMED: Stage-0.3-not-run].
ADR-003 ratification: OPEN. Entire plan corpus retains DRAFT status.
```

### Source documents read for this analysis

Each with confirmed first-line citation per the prompt's §0 requirement:

- `../../.ai/CONTRACT.md` — [READ, cited as prompt-specified source]
- `../../.ai/theorems/Context-Complete Evidence-Guided Agent Process.md` — [READ throughout prior sessions; cited as CCEGAP C1–C12]
- `../../.ai/theorems/Engineer_Soundness_Completeness.md` — [READ; cited as ESC §1–§8]
- `../../.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` — [READ; cited as ECITP §2–§7]
- `../../.ai/theorems/Error_Discovery.md` — [READ in this session, invoked via deep-verify pattern]
- `forge/platform/docs/EPISTEMIC_CONTINUITY_ASSESSMENT.md` — [READ; treated as DRAFT synthesis per prompt note]
- `forge/platform/docs/FORMAL_PROPERTIES_v2.md` — [READ partial; properties P1-P25 cited; full §11.2 synth(s, i) pattern [UNKNOWN] until ADR-009]
- `forge/platform/docs/GAP_ANALYSIS_v2.md` — [READ; R-GAP-02 caveat applied: code-state claims [ASSUMED: Stage-0.3-not-run]]
- `forge/platform/docs/ROADMAP.md` — [CONFIRMED: current revision shows 54 stages across Pre-flight/A/B/C/D/E/F/G; 18 ADRs pending in §12]
- `forge/platform/docs/AUTONOMOUS_AGENT_FAILURE_MODES.md` — [READ; SR-1/2/3 source]
- `forge/platform/docs/PLAN_PRE_FLIGHT.md` — [READ current state]
- `forge/platform/docs/PLAN_GATE_ENGINE.md` — [READ current state]
- `forge/platform/docs/PLAN_MEMORY_CONTEXT.md` — [READ current state; 7 stages B.1–B.7]
- `forge/platform/docs/PLAN_QUALITY_ASSURANCE.md` — [READ current state]
- `forge/platform/docs/PLAN_CONTRACT_DISCIPLINE.md` — [READ current state; 20 stages E.1–E.8 + F.1–F.12]
- `forge/platform/docs/PLAN_GOVERNANCE.md` — [READ current state; 10 stages G.1–G.10]
- `forge/platform/docs/CHANGE_PLAN_v2.md` — [READ partial; phase rationale]
- `forge/platform/docs/DEEP_RISK_REGISTER.md` — [READ partial; 29 risks acknowledged]
- `forge/platform/docs/decisions/README.md` — [CONFIRMED: highest ADR = ADR-021 per current index]

### Source documents NOT read (explicit list)

- `../../.ai/framework/PRACTICE_SURVEY.md` — [NOT READ in this session; prompt allows adding if needed; findings relying on it tagged [ASSUMED: PRACTICE_SURVEY content not verified]]
- `forge/platform/docs/FRAMEWORK_MAPPING.md` — [NOT READ end-to-end; cited via reference only]
- `forge/platform/docs/platform/ARCHITECTURE.md`, `WORKFLOW.md`, `DATA_MODEL.md`, `ONBOARDING.md` — [NOT READ; not in mandatory list]

---

## Section 1: What the existing plans got right

> DID: scanned each plan's Stage entries, entry conditions, exit tests, and gate conditions. Matched each closure claim to specific exit test line numbers in the current plan files.
>
> DID NOT: run the tests or verify implementation alignment (plans are DRAFT; no implementation exists).
>
> CONCLUSION: coverage of CCEGAP C1–C7 + ECITP C3/C6/C7/C8/C11/C12 + FC §8/§15/§16-§19/§25-§26/§37 is structurally complete across the 54 stages, with the caveats itemized in §2.

### 1.1 PLAN_PRE_FLIGHT (3 stages)

**Correctly identifies:**
- Stage 0.1 closes the ADR-003 ratification gate (cites T_{0.1}: `docs/reviews/review-ADR-003-by-*.md` exists + grep `status: RATIFIED`) — [CONFIRMED: PLAN_PRE_FLIGHT T_{0.1}].
- Stage 0.2 closes ADR-004/005/006 calibration (T_{0.2}: 3 review records + Status CLOSED) — [CONFIRMED: PLAN_PRE_FLIGHT T_{0.2}].
- Stage 0.3 closes IMPLEMENTATION_TRACKER smoke test with SHA-256 of implementation files (T_{0.3}: `smoke_results.json` + zero UNCHECKED) — [CONFIRMED: PLAN_PRE_FLIGHT T_{0.3}].

**Correctly closes:** CCEGAP C9 meta-conditions for all 7 soundness conditions (Pre-flight closes nothing at C_i level; it establishes normative premises downstream stages depend on).

**One gap flagged here, expanded in §2:** Stage 0.3 "distinct-actor review of smoke script" has no SLA — if reviewer unavailable indefinitely, Pre-flight stalls silently.

### 1.2 PLAN_GATE_ENGINE (5 stages)

**Correctly identifies:**
- Stage A.1 partial P17 via DB CHECK constraint on `EvidenceSet.kind` enum — [CONFIRMED: PLAN_GATE_ENGINE A_{A.1}, corrected post-deep-verify to acknowledge "partial" not full P17].
- Stage A.4 enforcement cutover with T1 grep-gate (zero direct `.status=` in Python app/) + T3 base.html exclusion — [CONFIRMED: PLAN_GATE_ENGINE T_{A.4}].
- Stage A.5 MCP idempotency via `(execution_id, tool_call_id)` unique constraint — [CONFIRMED: T_{A.5} T2].

**Correctly closes:** CCEGAP C5 (∃ T_i deterministic) + C6 (O_i only if G_i = PASS).

**Gap flagged here:** Phase A exit gate cites ADR-004 CLOSED as prerequisite; ADR-004 remains OPEN per skeleton. This is a soft-block (no phase has started) but becomes hard-block the moment A.1 first PR lands.

### 1.3 PLAN_MEMORY_CONTEXT (7 stages after ECITP+FC extensions)

**Correctly identifies:**
- Stage B.1 CausalEdge structural foundation — acyclicity via `src.created_at < dst.created_at` + `is_objective_root` exception — [CONFIRMED: PLAN_MEMORY_CONTEXT B.1 Work items, corrected for root exception].
- Stage B.4 ContextProjector with deterministic budget pruning — [CONFIRMED: T_{B.4} T3 determinism test].
- Stage B.5 TimelyDeliveryGate closing ECITP C3 with phased WARN→REJECT rollout — [CONFIRMED: B.5 Work + T5 grep fallback verification].
- Stage B.7 SourceConflictDetector closing FC §8 via literal-value mismatch on (entity_ref, field_name) — [CONFIRMED: B.7 exit tests T2–T6].

**Correctly closes:** CCEGAP C1+C3; ECITP C3 + C6 (WARN, promoted at G.9) + §2.3 (via B.4 T2b property test); FC §8.

**Gap flagged here, expanded in §2:** B.4 T2b property test claims 10,000 random DAG+task pairs but "random DAG generator" not specified — could be biased strategy missing edge-case DAGs (long chains, deep branching, sparse).

### 1.4 PLAN_QUALITY_ASSURANCE (9 stages C+D)

**Correctly identifies:**
- Stage C.3 ImpactClosure with explicit static-dispatch scope disclosure — [CONFIRMED: PLAN_QUALITY_ASSURANCE C.3 Closes line, corrected post-deep-verify to "within documented scope"].
- Stage D.1 bit-identical 3-run harness with elapsed-time normalized via sed strip — [CONFIRMED: T_{D.1} T1, corrected post-deep-verify F3].
- Stage D.5 mutation_smoke.py deterministic script (no longer manual) + first-run baseline mode for replay — [CONFIRMED: T_{D.5} T4, T5 corrected].

**Correctly closes:** CCEGAP C5 strengthened (property/metamorphic/adversarial). **Does NOT close CCEGAP C3** — explicit disclosure; C3 is closed by MEMORY B.4 + CONTRACT F.1/F.2. Prior over-claim corrected.

**Gap flagged here:** P3 closure "within static-dispatch scope" admitted; dynamic dispatch escape remains. Existing documentation is honest about it. Not a plan flaw; implementation risk.

### 1.5 PLAN_CONTRACT_DISCIPLINE (20 stages E.1–E.8 + F.1–F.12)

**Correctly identifies:**
- Stage E.1 self-adjoint ContractSchema (drift test: mutation of field changes both `render_prompt_fragment` and `validator_rules`) — [CONFIRMED: PLAN_CONTRACT_DISCIPLINE E.1 T1, T2].
- Stage F.3 CONFIRMED/ASSUMED/UNKNOWN enforced as REJECT (not WARN) — [CONFIRMED: F.3 T1, T2].
- Stage F.4 BLOCKED state + resolve-uncertainty durable record + cross-stage ambiguity-continuity property test — [CONFIRMED: T_{F.4} T2, T5, T6].
- Stage E.7 EpistemicProgressCheck with 6 deltas + explicit invalidation mechanism — [CONFIRMED: E.7 Work items + T7].
- Stage F.10 StructuredTransferGate with 6 structural fields + grep-gate on fallback paths — [CONFIRMED: F.10 T1, T4, T5].

**Correctly closes:** CCEGAP C2+C4+C7; ECITP C8 + §2.4 + §2.7 + C11; FC §15 + §16-§19 + §37.

**Gap flagged here, expanded in §2:** F.11 CandidateSolutionEvaluation's `Necessary(c) evidence_ref` can cite "requirement / invariant / scalability bound / resilience bound / validated future scenario" — but `Requirement` entity is ADR-015 TBD. If ADR-015 resolves to "Finding-as-Requirement", F.11 validator pivots; not structurally stable yet.

### 1.6 PLAN_GOVERNANCE (10 stages G.1–G.10)

**Correctly identifies:**
- Stage G.1 Stage 0 DataClassification pre-ingest gate + kill-criteria SecurityIncident trigger with mechanical confirmer schema — [CONFIRMED: G.1 Work items + Fix F6 from deep-verify].
- Stage G.4 rule_prevention_log + 12-month grace period for retirement candidates — [CONFIRMED: G.4 Work item 3 + T_{G.4} T2].
- Stage G.9 proof_trail_audit with 10-link chain traversal + REJECT-promotion of B.6/F.10 — [CONFIRMED: G.9 Work items + T_{G.9} T5, T6].
- Stage G.10 BaselinePostVerification with per-element runtime observation + C.4 auto-rollback integration — [CONFIRMED: G.10 Work + T7, T8].

**Correctly closes:** ECITP C7 + C12; FC §25+§26.

**G_GOV terminal gate** now validates **21 mechanical checks** (up from 7 CCEGAP). The final validation table is structurally comprehensive.

**Gap flagged here:** G.9 REJECT-promotion flag flip at `feature_flags.CAUSAL_RELATION_SEMANTIC_REJECT=true` is a one-way gate; no backout procedure if promotion reveals it was too aggressive in production.

---

## Section 2: Adversarial analysis — what is wrong or missing

> DID: applied constructive-counterexample method to stage claims; traced cross-plan dependencies; grep'd for [ASSUMED] tags and tested each against CONTRACT §A.2 7 non-trivial triggers.
>
> DID NOT: execute any test (no implementation exists); did not enumerate all possible adversarial inputs (scope limited to realistic production-level scenarios).
>
> CONCLUSION: 6 CRITICAL, 14 IMPORTANT, 9 MINOR findings. Pattern: gaps cluster around (1) ADR non-closure causing semantic instability, (2) plan-assumed determinism under systemic DB non-determinism, (3) pure-operation assumptions for stages that actually have side effects.

### 2a. Edge cases not covered by exit tests (≥5)

**F2a.1 — B.5 TimelyDeliveryGate race condition under concurrency. CRITICAL.**
- Quote: "Gate at pending→IN_PROGRESS transition — atomic with state machine; failure prevents transition" [CONFIRMED: PLAN_MEMORY_CONTEXT B.5 Rationale option 2 chosen].
- Theorem violated: ECITP C3 *Timely delivery* says "All information required by stage i is delivered BEFORE F_i is executed" — [CONFIRMED: `.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` §3 C3].
- Constructive counterexample: Execution X and Execution Y simultaneously READ the same ContextProjection (id=Z). ContextProjection is mutated by Execution Y's precursor task-completion event between X's read and X's transition-check. X transitions to IN_PROGRESS with projection_id pointing to a now-stale projection. Test T2 only checks `context_projection_id IS NOT NULL`, not that projection content matches current DAG state at transition time.
- Realistic scenario: production load > 10 concurrent Executions per project (realistic for CI pipeline). Race window ≈ 5ms (typical DB round-trip).
- Fix: T_{B.5} T7 — add `projection.captured_at` timestamp + gate check `now() - projection.captured_at < max_projection_staleness_sec` (new ADR-004 constant).

**F2a.2 — F.10 StructuredTransferGate undefined behavior for empty-required-categories. IMPORTANT.**
- Quote: "If task demands non-empty (per schema): `len(projection.<cat>) >= 1`" [CONFIRMED: PLAN_CONTRACT_DISCIPLINE F.10 Work item 1].
- Theorem violated: ECITP C11 *Downstream inheritance* explicitly enumerates 6 categories as required — [CONFIRMED: theorem §3 C11].
- Constructive counterexample: task type `trivial_rename` legitimately has ZERO requirements, ZERO ambiguity, ZERO test obligations (rename is non-semantic). Gate validator currently says "non-empty when schema demands it" — but `ContractSchema.required_context_categories(task='trivial_rename')` is ADR-009/Q9 not yet defined. In the interim, does projection with `requirements=[]` PASS (schema allows empty) or FAIL (category literally empty)?
- Realistic scenario: renaming a private utility function. Must not be blocked.
- Fix: T_{F.10} T8 — explicit fixture for schema-allowed-empty categories PASSES with `projection.<cat> = []`. Update Work item 1 to separate "category present in schema and empty-allowed" from "category required non-empty".

**F2a.3 — G.10 Baseline capture mutates observable state. CRITICAL.**
- Quote: "capture_baseline(change) → None — for each x ∈ ImpactClosure(change), call snapshot_validator.capture_state(x)" [CONFIRMED: PLAN_GOVERNANCE G.10 Work item 2].
- Theorem violated: FC §25 *Diff = ExpectedDiff* + FC §27 *Deterministic Validation* — [CONFIRMED: Forge Complete theorem §25 + §27].
- Constructive counterexample: `snapshot_validator.capture_state(x)` on a PostgreSQL table where `ANALYZE TABLE x` is called to compute distribution statistics. ANALYZE mutates `pg_statistic` rows. Baseline captures pre-ANALYZE state; Post (after Change applies + any other Execution's ANALYZE) captures post-ANALYZE state. Diff non-empty solely from statistics update, regardless of actual Change.
- Realistic scenario: long-running migration with `CREATE INDEX CONCURRENTLY` triggers autovacuum + statistics update. Baseline captured 30s ago; Post captured now; stats differ → REJECTED + auto-rollback on a Change that was actually correct.
- Fix: T_{G.10} T10 — `capture_state` documented as read-only + explicit list of PostgreSQL catalog tables excluded from observation (pg_statistic, pg_stat_*, pg_class.reltuples). ADR-021 must enumerate exclusions.

**F2a.4 — E.7 EpistemicProgressGate rejects legitimate debt-removal stages. IMPORTANT.**
- Quote: "PASS iff any delta from {Δ1..Δ6} strictly positive" [CONFIRMED: PLAN_CONTRACT_DISCIPLINE E.7 Work item 1].
- Theorem violated: ECITP C8 *Additive epistemic progression* lists 6 improvement kinds; F.12 TechnicalDebtTracking's `resolved_by_change_id` flow is explicitly a 7th kind (reduce debt) not in E.7's delta list — [CONFIRMED: F.12 Work item 4].
- Constructive counterexample: Change whose sole purpose is to resolve 3 `technical_debt` rows (fix TODOs). Produces NO new evidence, NO new failure mode, NO scope narrowing, NO schema tightening, NO new AC. All 6 E.7 deltas zero. But the Change removes 3 Debt rows — epistemic improvement by FC §37's own framing.
- Realistic scenario: "debt burndown sprint" Change.
- Fix: T_{E.7} T9 — add Δ7: `reduced_technical_debt = len(technical_debt where resolved_by_change_id = execution.change_id) >= 1`. Update Work item 1 to 7 deltas total.

**F2a.5 — F.11 Score(x) depends on non-deterministic ExpectedFutureCost. CRITICAL.**
- Quote: "Score(c) = Σ (weight_d × value_{c,d}) per ADR-019 weights. Selected candidate MUST equal argmax_c Score(c)" [CONFIRMED: PLAN_CONTRACT_DISCIPLINE F.11 Work item 2].
- Theorem violated: FC §27 *Deterministic Validation* and FC §19's own formula: `ExpectedFutureCost(x) = Σ_ω Probability(ω) * AdaptationCost(x, ω)` — [CONFIRMED: Forge Complete theorem §19].
- Constructive counterexample: how is `FutureScenarios` enumerated? Where do `Probability(ω)` values come from? If LLM-generated → violates ESC-1. If domain-expert-supplied per Decision → subjective and changes between Decisions, making Score non-reproducible on re-audit.
- Realistic scenario: historical Decision's Score re-computed during G.9 proof_trail audit returns different value because `FutureScenarios` set is updated. G.9 now sees Decision.selected_candidate_id ≠ argmax_c Score(c)_today → erroneously flags REJECTED on a historically-correct Decision.
- Fix: T_{F.11} T10 — Score evaluation captured at Decision insert time (snapshot), immutable; future-scenario updates create a new Decision superseding the prior (FC §29 fixed-at-acceptance). ADR-019 must specify snapshot semantics.

**F2a.6 — B.6 SemanticRelationTypes REJECT promotion breaks on partial backfill. IMPORTANT.**
- Quote: "G.9 feature_flags.CAUSAL_RELATION_SEMANTIC_REJECT=true — promotes B.6 AC validator from WARN to REJECT" [CONFIRMED: PLAN_GOVERNANCE G.9 Work item 4].
- Quote: "Unmappable edges reported as Findings, NULL retained" [CONFIRMED: PLAN_MEMORY_CONTEXT B.6 Work item 2].
- Theorem violated: ECITP C6 *Topology preservation* requires relations preserved — but if backfill leaves NULL `relation_semantic` for unmappable historical edges, REJECT-mode evaluator at G.9 sees NULL on legitimate old rows → retroactive REJECT on valid historical state.
- Constructive counterexample: 10% of backfilled `causal_edges` have `relation_semantic=NULL` per A_{B.6} mapping gaps. G.9 promotes to REJECT. Every Execution that traverses causal_edges hits NULL → REJECTED. System-wide halt.
- Realistic scenario: day of G.9 promotion.
- Fix: T_{G.9} T9 — pre-promotion health check: `SELECT count(*) FROM causal_edges WHERE relation_semantic IS NULL` must equal zero before flag flip. If non-zero, G.9 BLOCKED with diagnostic listing unmapped rows.

### 2b. Boundary conditions (≥3)

**F2b.1 — α threshold boundary. [UNKNOWN: threshold requires ADR-004].**
- Gate: D.5 CI α-gate "below α per capability → merge blocked" [CONFIRMED: PLAN_QUALITY_ASSURANCE D.5 Work item 4].
- Boundary: coverage = α exactly. Block or pass? ADR-004 must answer.
- Fix: ADR-004 specifies inequality direction (>= or >) explicitly.

**F2b.2 — BFS depth limit boundary. [UNKNOWN: requires ADR-004 or companion].**
- Gate: B.3 ancestors() with max_depth=10 (strawman) [CONFIRMED: PLAN_MEMORY_CONTEXT A_{B.3}, Q3].
- Boundary: dependency chain of exactly max_depth. Included or excluded?
- Fix: Q3 resolution must specify; currently [UNKNOWN: strawman=10] is insufficient.

**F2b.3 — F.11 trivial-change bypass threshold boundary. [UNKNOWN: ADR-019].**
- Gate: `Decision.type='trivial_change'` allowed when `change_size <= threshold_loc AND impact_closure_size <= 1` [CONFIRMED: F.11 Work item 3].
- Boundary: `change_size == threshold_loc`. Trivial (PASS) or architectural (REJECT)?
- Fix: ADR-019 specifies inclusive or exclusive comparison.

### 2c. Failure modes from AUTONOMOUS_AGENT_FAILURE_MODES.md not addressed (≥3)

**F2c.1 — §2.2 "projection fidelity on novel task types" — DISCLOSED but not plan-addressed.**
- AUTONOMOUS_AGENT_FAILURE_MODES.md §2.2 explicitly flags this gap — [CONFIRMED: referenced in PLAN_MEMORY_CONTEXT B.4 disclosure].
- B.4 T2b property test (added in ECITP continuity fix) uses random DAG+task pairs but task-type space may be biased.
- Which plan stage should address: MEMORY Phase B post-G_B ("empirical coverage study"; out of scope of current plan).
- Specific addition: new post-G_GOV stage H.1 — novel-task-type-fidelity benchmark (domain: unknown task types introduced over 6 months of operation; projection fidelity computed empirically).

**F2c.2 — §6 / §4 "dynamic dispatch not in ImpactClosure" — EXPLICITLY acknowledged gap.**
- C.1 `A_{C.1}`: "Dynamic dispatch (getattr, runtime imports) is NOT covered — [CONFIRMED gap]" [CONFIRMED: PLAN_QUALITY_ASSURANCE A_{C.1}].
- FC §14 Impact Closure requires closure over "all execution paths".
- Current plan: no stage addresses. Gap persists.
- Specific addition: new stage C.5 — RuntimeDispatchDetector using `sys.settrace` or coverage-instrumentation integration to enumerate actual call graph (pay cost at test time, not plan time).

**F2c.3 — Multi-agent concurrency soundness — DISCLOSED but not plan-addressed.**
- G_GOV terminal gate disclosure: "System-level soundness (concurrency, multi-agent sessions, novel task types) is NOT established by G_GOV" [CONFIRMED: PLAN_GOVERNANCE G_GOV section].
- All 54 stages implicitly assume single-Execution flow.
- Specific addition: new stage H.2 — concurrency soak test harness with ≥2-agent concurrent test per key gate (B.5, E.7, G.10).

### 2d. Silent assumptions that break under adversarial conditions (≥3)

**F2d.1 — G.10 `snapshot_validator.capture_state()` assumed read-only. CRITICAL.**
- Covered in F2a.3 above. Adversarial: ANALYZE or auto-vacuum makes capture non-idempotent.

**F2d.2 — All periodic detection scripts assumed idempotent across runs. IMPORTANT.**
- Plans: `detect_source_conflicts.py` (B.7), `detect_debt_markers.py` (F.12), `proof_trail_audit.py` (G.9) — each T-test asserts "idempotent: second run produces same row count" [CONFIRMED: B.7 T6, F.12 T6, G.9 T1].
- Adversarial: between first and second run, other Executions commit (DB state is live). Re-run sees different input → different output. Test passes in isolated fixture; fails in prod.
- Fix: tests must explicitly specify "isolated DB fixture" (hermetic per D.1 T0). Re-document idempotency claim as "idempotent on fixed DB state" not "idempotent in production".

**F2d.3 — E.1 migration risk `[ASSUMED: backward-compatible]` should be [UNKNOWN]. IMPORTANT (2e overlap).**
- Quote: "Migration risk: existing Tasks have untyped `produces` JSONB — [ASSUMED: backward-compatible; ContractSchema adds typed layer on top without removing JSONB. If existing data is malformed → migration validation may reject some rows]" [CONFIRMED: PLAN_CONTRACT_DISCIPLINE A_{E.1}].
- Classifier (CONTRACT §A.2 trigger 3: assumption about data-state) → non-trivial. Should be [UNKNOWN: pending migration dry-run count per Q2 (which is BLOCKING)].
- Fix: promote A_{E.1} from [ASSUMED] to [UNKNOWN]; stage E.1 already BLOCKED via Q2.

### 2e. Misclassified ASSUMED → should be UNKNOWN

Applying CONTRACT §A.2's 7 non-trivial triggers to each plan's [ASSUMED] list:

**F2e.1 — MEMORY A_{B.4} "Budget unit: tokens" tagged [ASSUMED].**
- Trigger 5: claim about external-system contract (LLM tokenizer counts tokens). This is not a stable fact — tokenizer versions vary (Anthropic vs OpenAI, model version bumps).
- Reclassify: [UNKNOWN: tokenizer fixed per ADR-006; propagate from ADR-006 to B.4 budget-unit when ADR-006 CLOSED].

**F2e.2 — QA A_{C.1} "PR-gate simpler than file watcher" tagged [ASSUMED].**
- Trigger 2: architectural choice with downstream behavior implications. CI PR-gate latency vs file-watcher liveness is not equivalent.
- Reclassify: stays [ASSUMED] — the claim is design-choice not factual; but add rationale ("file-watcher requires daemon, ops burden") per CONTRACT §B.3.

**F2e.3 — CONTRACT A_{E.3} "L1–L5 labels; internal state continuous" — not in ASSUMED list but similar risk.**
- Internal continuous state vs discrete labels is a schema constraint; tests don't verify "continuous" explicitly (no test asserts `AutonomyState.success_rate.column.type == Float`).
- Not misclassification; missing test (added as F.5 test Fix per CONTRACT deep-verify Fix F5).

**F2e.4 — GOVERNANCE A_{G.3} "7 metric definitions from OPERATING_MODEL §7.1" — corrected post-deep-verify to [CONFIRMED: FRAMEWORK_MAPPING §7].**
- Already corrected. Mention to complete audit trail.

**Exhaustive search complete across sampled plans — 2 genuinely misclassified (F2e.1), the rest are either correctly tagged or flagged elsewhere. No quota padding.**

### 2f. Cross-plan dependency gaps (≥4)

**F2f.1 — F.11 Necessary(c) evidence_ref depends on ADR-015 TBD entity. CRITICAL.**
- F.11 validator: "each component in chosen candidate must have justification evidence_ref citing concrete requirement/invariant/scalability bound/resilience bound/validated future scenario" [CONFIRMED: PLAN_CONTRACT_DISCIPLINE F.11 Work item 2].
- "Requirement" entity status: [UNKNOWN: ADR-015 — promote Finding.type='requirement' or accept as-is].
- Gap: if ADR-015 → "accept Finding-as-Requirement", then F.11 evidence_ref can cite Finding. If → "distinct Requirement entity", F.11 needs different FK. Plan is not ADR-outcome-stable.
- Fix: ADR-015 CLOSED before F.11 can have stable exit-test spec; update F.11 entry conditions to reference ADR-015 explicitly.

**F2f.2 — G.10 Change.expected_diff for legacy Changes. CRITICAL.**
- G.10 migration: "Change.expected_diff JSONB NOT NULL" [CONFIRMED: PLAN_GOVERNANCE G.10 Work item 4].
- Gap: Changes created before G.10 migration do not have `expected_diff`. Migration must decide: (a) backfill with `{}` (everything passes — silent weakening), (b) backfill NULL + block (NOT NULL contradicts), (c) retroactively compute from actual diff (defeats purpose — expected == actual tautologically).
- Fix: ADR-021 must include legacy-Change strategy. Current ADR-021 skeleton mentions this as [UNKNOWN].

**F2f.3 — B.5 TimelyDeliveryGate vs G.10 Baseline capture ordering. IMPORTANT.**
- B.5 blocks Execution at `pending → IN_PROGRESS` if `context_projection_id IS NULL`.
- G.10 captures Baseline "BEFORE Delta applied" [CONFIRMED: G.10 Work item 3 pre-apply hook].
- Gap: when does Baseline capture run relative to B.5 gate? Baseline capture mutates `runtime_observations`; B.5 runs at IN_PROGRESS transition. Sequence: pending → (B.5 gate) → IN_PROGRESS → (Baseline captures) → apply Delta → (Post captures) → commit.
- Question: Baseline capture itself needs to satisfy B.5? If YES, capture requires ContextProjection (doesn't make sense — capture is pre-Change, pre-projection). If NO, B.5 semantics distinguishes "Execution-level" projection vs "Baseline-capture-level" non-projection — not specified.
- Fix: G.10 Entry condition adds "Baseline capture is exempted from B.5; runs at pending-state under different gate profile".

**F2f.4 — E.8 ScopeBoundaryDeclaration ImpactClosure partial coverage. IMPORTANT.**
- E.8 requires `in_scope_refs ∪ out_of_scope_refs ⊇ ImpactClosure(change)` [CONFIRMED: PLAN_CONTRACT_DISCIPLINE E.8 Work item 2].
- ImpactClosure per C.3 includes `task_dependencies` via `causal_edges WHERE relation_semantic='depends_on'`.
- If B.6 backfill leaves some relation_semantic=NULL, ImpactClosure for old tasks is incomplete → E.8 sees smaller closure → false-PASS on Changes that miss those dependencies.
- Fix: E.8 exit condition requires `count(causal_edges WHERE relation_semantic IS NULL AND applicable_to_change) = 0` as precondition.

---

## Section 3: Root causes — synthesis

> DID: looked across all Section 2 findings; grouped by common structural driver; verified each root cause cites ≥2 distinct plan locations.
>
> DID NOT: list Section 2 findings again; synthesis only.
>
> CONCLUSION: 4 root causes. Each violates specific CCEGAP / ECITP / FC conditions and blocks ≥3 FORMAL properties.

**Tagged entire section: [ASSUMED: agent-synthesis — requires distinct-actor review. Structural diagnoses cannot be self-verified.]**

### RC-1: Meta-dependency on ADR non-closure creates semantic instability

18 ADRs pending. Every plan cites multiple ADRs as blocking. Findings F2a.2, F2a.5, F2b.1, F2b.2, F2b.3, F2f.1, F2f.2 all trace to the same root: stages specify mechanisms whose *semantic* depends on ADR values not yet chosen. Plans are structurally stable (every test defines PASS/FAIL shape) but semantically unstable (what PASS *means* shifts when ADR values change).

**CCEGAP condition violated:** C5 *Evidence-grounded transformation* — reasoning about what a stage closes depends on prior evidence, but ADR outcomes are future-state unknowns. Prior-substitution risk for any planner reviewing these plans (they may imagine ADR values implicitly).

**FORMAL properties affected:** P4 (Autonomy thresholds depend on ADR-004), P10 (risk weights depend on ADR-004), P12 (ContractSchema sufficiency depends on ADR-014), P22 (disclosure semantics depends on ADR-013 challenger flow), P25 (snapshot components depend on ADR-009).

**Why symptom-level fixes won't close:** closing one ADR doesn't close others. Without an ADR-closure orchestration (see §4 Addition AD-1), the corpus remains in limbo.

Evidence: ROADMAP §12 lists 18 pending ADRs; every plan header cites 2+ ADRs as blockers.

### RC-2: Deterministic-gate assumption under systemic DB non-determinism

F2a.3 (G.10 capture_state non-idempotent), F2d.1 (ANALYZE mutates pg_statistic), F2d.2 (detection scripts assume hermetic state in production), F2a.6 (B.6 NULL promotion) all share: gates assume PostgreSQL provides "same state → same query result" over time, which is false without explicit isolation-level contract.

**CCEGAP condition violated:** C9 *Deterministic stage evaluation* — gates depend on DB state snapshots that are not formally snapshot-consistent.

**FORMAL properties affected:** P6 (determinism at application level is preserved; at DB level not specified), P25 (snapshot validation is the property being violated).

**Why symptom-level fixes won't close:** per-stage "isolation=SERIALIZABLE" annotations don't propagate; need corpus-wide contract.

Evidence: every stage with a "pytest passes → gate passes" exit test assumes hermetic DB; no plan specifies isolation level for production gates.

### RC-3: Plan-implementation drift has no observability

No plan addresses: what if implementation at Phase A.1 passes exit tests T1–T5 but silently violates plan intent? E.g. `evidence_set.py` has a `kind='assumption'` allowed via caller-side bypass of CHECK constraint. Exit tests pass; plan intent violated; no gate catches.

**CCEGAP condition violated:** C11 *Downstream inheritance rule* — later stages consume implementation, not plan. If implementation drifts from plan, downstream correctness relies on drifted implementation.

**FORMAL properties affected:** P19 (assumption enforcement — the exact failure mode), P23 (verification independence — challenger sees implementation, not plan).

**Why symptom-level fixes won't close:** adding more exit tests grows plan size; what's needed is a meta-gate on plan-implementation alignment.

Evidence: 54 stages; 270+ tests; zero tests assert "implementation satisfies plan intent beyond the tests".

### RC-4: Solo-author blind spots at corpus scale (plan-selection + theorem-selection)

Same actor (AI agent) authored 5 of 6 plans + 18 ADR skeletons + this document. ADR-003 binds distinct-actor review. But solo-author risk (R-GOV-01) applies not only to individual plans but to:
- Which **theorems were selected** to bind Forge (CCEGAP, Engineer Soundness, ECITP, ASPS, Forge Complete) — why not others?
- Which **alternatives were rejected** in each stage's ESC-3 section — are rejections genuine or merely plausible?
- Which **failure scenarios were marked JustifiedNotApplicable** — are justifications solid?

**CCEGAP condition violated:** C4 *Ambiguity exposure* — selection-bias ambiguity is not made explicit in any plan.

**FORMAL properties affected:** P23 (verification independence — this very document is authored by the prior-plan-author, violating independence).

**Why symptom-level fixes won't close:** distinct-actor review of each plan catches within-plan bias; a theorem-selection meta-audit must be separately sourced.

Evidence: session transcript shows iterative addition of 5 theorems; each uncovered new conditions; no audit of "which theorems we did NOT apply and why".

---

## Section 4: Required additions

> DID: for each root cause and ≥1 finding per theorem gap, proposed an action with a testable exit condition.
>
> DID NOT: fabricate additions to hit a numeric floor. Section concludes at 12 additions (above the 10 minimum); stopping because remaining candidate additions would be duplicates of existing stages' strengthening (not genuinely novel).
>
> CONCLUSION: 12 additions, of which 4 are CRITICAL (block Phase A exit if un-addressed), 6 are IMPORTANT, 2 are MINOR.

### AD-1 (CRITICAL) — ADR closure orchestration mechanism

- **Belongs to:** NEW PLAN — `PLAN_ADR_ORCHESTRATION.md` OR extension of PRE_FLIGHT with new Stage 0.4.
- **What to add:** single dashboard + SLA timebox per ADR. ADR without decision-maker action for ≥ SLA_days → escalation to Steward. Implements ADR-025 (proposed in §6).
- **Exit test T_new:** `pytest tests/test_adr_sla_enforcement.py` — synthetic pending ADR past SLA → escalation Finding emitted; dashboard endpoint `GET /adrs/pending` returns all pending with days_outstanding field.
- **Closes:** RC-1; CCEGAP C10 (Stop-or-escalate at process level, not just stage level).
- **Severity if not done:** CRITICAL — project stalls on ADR-004 alone (blocks Phase A exit).

### AD-2 (CRITICAL) — DB isolation-level contract per gate

- **Belongs to:** PLAN_GATE_ENGINE extension (new Stage A.6) OR corpus-wide addition to every stage's deterministic-test spec.
- **What to add:** every gate-query test wrapped in explicit `BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE` (or SNAPSHOT / REPEATABLE READ per case); test harness enforces this.
- **Exit test T_new:** `grep -rn "SERIALIZABLE\|REPEATABLE READ\|SNAPSHOT" platform/app/validation/ | wc -l >= <count_of_gate_checks>`; `pytest tests/test_isolation_contract.py` — gate query executed with wrong isolation level → explicit assertion failure.
- **Closes:** RC-2; CCEGAP C9 strengthened.
- **Severity if not done:** CRITICAL — every gate is technically-passing-but-semantically-incorrect under concurrent writes.

### AD-3 (CRITICAL) — Plan-implementation drift audit

- **Belongs to:** new Phase H — post-G_GOV continuous integration.
- **What to add:** each commit cites `Stage_Ref` in commit message (e.g. `stage: A.1`). CI parses commit → checks ≥1 changed file matches stage's Work-items spec. Drift → CI blocks merge + Finding.
- **Exit test T_new:** `pytest tests/test_plan_drift_audit.py` — commit without Stage_Ref → blocked; commit with Stage_Ref but no Work-item-file changed → flagged.
- **Closes:** RC-3; CCEGAP C11 strengthened.
- **Severity if not done:** CRITICAL — implementation silently diverges from spec; all downstream inheritance corrupted.

### AD-4 (CRITICAL) — Theorem-selection meta-audit

- **Belongs to:** new document `META_THEOREM_SELECTION.md` in `platform/docs/`.
- **What to add:** list of theorems considered, theorems adopted, theorems rejected with explicit reason per ESC-3. Distinct-actor review specifically on this document.
- **Exit test T_new:** `grep -c "^## Theorem:" platform/docs/META_THEOREM_SELECTION.md >= 5` + distinct-actor-review record in `docs/reviews/`.
- **Closes:** RC-4; CCEGAP C4 at corpus level.
- **Severity if not done:** CRITICAL — entire plan corpus may be built on wrong foundation; cannot be discovered from within.

### AD-5 (IMPORTANT) — Projection staleness check in B.5

- **Belongs to:** PLAN_MEMORY_CONTEXT Stage B.5 (strengthen existing exit tests).
- **What to add:** `runtime_observations.ContextProjection.captured_at` timestamp; B.5 gate enforces `now() - captured_at < max_projection_staleness_sec`.
- **Exit test T_new:** `pytest tests/test_projection_staleness.py` — projection older than max → REJECTED at transition.
- **Closes:** F2a.1 race condition; ECITP C3 strengthened.
- **Severity if not done:** IMPORTANT — stale projection is valid only if race window is rare; in production likely.

### AD-6 (IMPORTANT) — E.7 7th delta for debt resolution

- **Belongs to:** PLAN_CONTRACT_DISCIPLINE Stage E.7 (strengthen Work item 1).
- **What to add:** Δ7 `reduced_technical_debt = count(technical_debt WHERE resolved_by_change_id = execution.change_id) >= 1`.
- **Exit test T_new:** T_{E.7} T9 — debt-burndown Execution with only resolved_by → PASS.
- **Closes:** F2a.4 debt-removal rejected; ECITP C8 strengthened.
- **Severity if not done:** IMPORTANT — legitimate stages REJECTED; incentivizes gaming (add noise to pass).

### AD-7 (IMPORTANT) — G.10 capture_state read-only contract + exclusion list

- **Belongs to:** PLAN_GOVERNANCE Stage G.10 (strengthen Work item 2).
- **What to add:** `capture_state()` declared read-only in docstring; ADR-021 extension lists pg_statistic/pg_stat_*/autovacuum-affected catalog tables as excluded from observation.
- **Exit test T_new:** T_{G.10} T10 — capture_state invocation on excluded table → raises explicit error; pytest harness uses ReadOnly-DB connection for capture path.
- **Closes:** F2a.3 + F2d.1; FC §25 + §27 strengthened.
- **Severity if not done:** IMPORTANT — Diff false-positives on long-running Changes cause spurious rollback.

### AD-8 (IMPORTANT) — Dynamic dispatch call-graph enumeration

- **Belongs to:** PLAN_QUALITY_ASSURANCE new Stage C.5.
- **What to add:** `RuntimeDispatchDetector` via `sys.settrace` during test runs; enumerates actual (caller, callee) edges; augments ImpactClosure.
- **Exit test T_new:** `pytest tests/test_runtime_dispatch_detector.py` — fixture with `getattr`-based dispatch → detector captures edge that static AST misses.
- **Closes:** F2c.2; FC §14 strengthened.
- **Severity if not done:** IMPORTANT — ImpactClosure false-negatives silently on dynamic code.

### AD-9 (IMPORTANT) — Multi-agent concurrency test harness

- **Belongs to:** new Phase H — post-G_GOV.
- **What to add:** Phase H.1 concurrency soak test harness covering B.5, E.7, E.8, G.10 under ≥2 concurrent Executions.
- **Exit test T_new:** `pytest tests/concurrency/ -x --workers=4` — dual-Execution race conditions → no state corruption; race-window Findings surfaced.
- **Closes:** F2c.3 + systemic RC-2; FC §25+§26 at multi-agent level.
- **Severity if not done:** IMPORTANT — all G_GOV closure claims are single-Execution; production is multi-Execution.

### AD-10 (IMPORTANT) — Snapshot semantic for F.11 Score

- **Belongs to:** PLAN_CONTRACT_DISCIPLINE Stage F.11 (strengthen Work item 2).
- **What to add:** `solution_scores.computed_at` immutable; Score frozen at Decision insert; future updates create new Decision superseding.
- **Exit test T_new:** T_{F.11} T10 — re-compute Score months later returns same value for historical Decision; new future-scenarios generate new Decision not edit old.
- **Closes:** F2a.5; FC §19 + §29 strengthened.
- **Severity if not done:** IMPORTANT — G.9 audit falsely flags historical Decisions as REJECTED-today.

### AD-11 (MINOR) — B.6 pre-promotion health check in G.9

- **Belongs to:** PLAN_GOVERNANCE Stage G.9 (strengthen Work item 4).
- **What to add:** pre-flag-flip assertion `SELECT count(*) FROM causal_edges WHERE relation_semantic IS NULL = 0`.
- **Exit test T_new:** T_{G.9} T9 — G.9 flag-flip BLOCKED when NULL rows exist.
- **Closes:** F2a.6; ECITP C6 full closure.
- **Severity if not done:** MINOR — catchable at deploy time; not silent violation.

### AD-12 (MINOR) — [ASSUMED] → [UNKNOWN] reclassification

- **Belongs to:** PLAN_MEMORY_CONTEXT A_{B.4} budget-unit tag.
- **What to add:** reclassify [ASSUMED: tokens] to [UNKNOWN: tokens pending ADR-006 CLOSED]; add to Q-table.
- **Exit test T_new:** B.4 entry condition: ADR-006 CLOSED before B.4 budget tests meaningful.
- **Closes:** F2e.1; CONTRACT §A.2 trigger 5.
- **Severity if not done:** MINOR — test assumption becomes silent drift risk when ADR-006 resolves to different tokenizer.

**Exhaustive search complete — 12 additions found. Further candidates considered (e.g. "AD-13: explicit commit-message format spec") were duplicates of existing stage mechanisms or non-novel; rejected per prompt's no-padding rule.**

---

## Section 5: Test gap specifications

> DID: for each Section 4 addition, confirmed what existing T_i is closest and stated gap; for each Section 2 finding, confirmed whether a specific new test closes it.
>
> DID NOT: enumerate tests derivable from existing T_i.
>
> CONCLUSION: 15 novel tests specified across categories. Each names closest existing T_i and states why not derivable.

### Property-based (hypothesis-style) — ≥3

**T.P1 — test_causal_acyclicity_under_concurrent_insert.py**
- Property: 10,000 random CausalEdge insertion sequences with simulated concurrent commits never produce a cycle.
- Closest existing: `T_{B.1} T3` (10,000 random inserts, no cycle). Not derivable because existing test is single-writer; new test simulates multi-writer via thread pool + locks.
- Type: property-based + concurrency.
- Closes: CCEGAP C9 strengthened + AD-9 (multi-agent harness).

**T.P2 — test_context_projection_monotonic_additive.py**
- Property: adding a CausalEdge to the DAG never REMOVES an element from `ContextProjection(task_t)` (only adds or leaves unchanged).
- Closest existing: `T_{B.4} T2b` (property test for evidence continuity). Not derivable because that test is inclusion-over-relevance, not monotonicity-over-edge-addition.
- Type: property-based.
- Closes: ECITP §2.7 additive exploration strengthened.

**T.P3 — test_scope_boundary_closure_equality.py**
- Property: for 10,000 random Changes, `in_scope_refs ∪ out_of_scope_refs ≡ ImpactClosure(change)` as set equality (not superset).
- Closest existing: `T_{E.8} T3` (fully-justified closure PASSES). Not derivable because existing test is PASS case; property test adversarially generates closures.
- Type: property-based.
- Closes: FC §15 strengthened.

### Adversarial (from AUTONOMOUS_AGENT_FAILURE_MODES + PRACTICE_SURVEY) — ≥3

**T.A1 — test_baseline_capture_concurrent_mutation.py**
- Scenario: during `capture_baseline(change_X)` execution, another Execution commits a write to one of the captured entities.
- Closest existing: `T_{G.10} T3` (baseline capture failure). Not derivable because existing test is static-fixture; adversarial test injects mutation mid-capture.
- Type: adversarial.
- Closes: F2a.3 + AD-7.

**T.A2 — test_impact_closure_dynamic_dispatch_escape.py**
- Scenario: Change modifies function `f()` called via `getattr(module, 'f')()` from function `g()` in unrelated file. ImpactClosure misses `g()` entirely (static AST gap per C.1 disclosure).
- Closest existing: `T_{C.3} T1` (closure correctness). Not derivable because existing fixture uses only static imports.
- Type: adversarial.
- Closes: F2c.2 + AD-8.

**T.A3 — test_epistemic_null_paraphrase_evasion.py**
- Scenario: adversary crafts Execution with new EvidenceSet row that is a literal copy of prior evidence (content identical, new row id). Δ1 (`new_evidence_refs >= 1`) satisfied mechanically but no real new evidence.
- Closest existing: `T_{E.7} T3` (Δ1 sufficient). Not derivable because existing test validates single-delta; adversarial constructs evasive Δ1.
- Type: adversarial.
- Closes: ECITP C8 strengthened; needs content-hash check on EvidenceSet.

### Boundary condition tests — ≥3

**T.B1 — test_alpha_exact_threshold.py**
- Edge: coverage equals α exactly. Must define PASS or FAIL per ADR-004.
- Closest existing: `T_{D.5} T3` (below α → block). Not derivable because existing test is strictly-below; boundary value ambiguous.
- Type: boundary.
- Closes: F2b.1.

**T.B2 — test_max_depth_chain.py**
- Edge: ancestors() chain of length exactly `max_depth`. Inclusive or exclusive?
- Closest existing: `T_{B.3} T1` (ancestors correctness on fixture DAG). Not derivable because fixture has no max-depth chain.
- Type: boundary.
- Closes: F2b.2.

**T.B3 — test_change_size_at_threshold.py**
- Edge: `change_size == threshold_loc`. Trivial-bypass allowed?
- Closest existing: `T_{F.11} T6` (below threshold → trivial PASS). Not derivable because existing test uses strict-below value.
- Type: boundary.
- Closes: F2b.3.

### Cross-plan integration tests — ≥3

**T.X1 — test_b4_b5_projection_handoff.py**
- Scenario: ContextProjector (B.4) outputs a `ContextProjection` row; B.5 TimelyDeliveryGate consumes it at Execution transition. Handoff integrity: B.5 sees same projection B.4 produced.
- Closest existing: B.4 tests + B.5 tests run in isolation. Not derivable because no integration test spans both.
- Type: integration.
- Closes: F2f.3 ordering gap.

**T.X2 — test_e7_e8_f10_commit_chain.py**
- Scenario: Execution transitions through E.7 EpistemicProgressCheck → E.8 ScopeBoundaryCheck → F.10 StructuredTransferCheck in order; each sees the other's state-transition residue.
- Closest existing: per-gate tests. Not derivable because order-dependent failure modes only surface in chain.
- Type: integration.
- Closes: commit-chain ordering regressions (adjacent to RC-2).

**T.X3 — test_g10_c4_rollback_integration.py**
- Scenario: G.10 detects Diff ≠ ExpectedDiff on REVERSIBLE Change; invokes C.4 rollback_service; state restored byte-identical to Baseline.
- Closest existing: C.4 disaster drill + G.10 unit tests. Not derivable because integration across plans requires end-to-end flow.
- Type: integration.
- Closes: FC §25 auto-rollback path verified E2E.

### Additional tests (crossing categories) to reach 15

**T.12 — test_source_conflict_resolution_creates_no_cycle.py** (property + adversarial): resolving one conflict via Decision never creates a new conflict among previously-consistent sources.

**T.13 — test_technical_debt_accepted_role_leaves_org.py** (adversarial): Steward who accepted a Debt row leaves organization; debt remains `accepted_role` immutable (audit trail intact); new Steward can sign-off resolution.

**T.14 — test_relation_semantic_backfill_partial_coverage.py** (boundary + adversarial): B.6 backfill with 10% unmappable TEXT values → NULL rows emit Findings; G.9 promotion BLOCKED on NULL count > 0.

**T.15 — test_adr_sla_escalation.py** (integration): synthetic pending ADR past SLA → Finding emitted; dashboard endpoint shows days_outstanding; Steward notification triggered.

**Exhaustive search complete for adversarial scope — 15 tests specified. No padding; 15th test addresses AD-1 directly.**

---

## Section 6: ADR requirements

> DID: read `forge/platform/docs/decisions/README.md` current index.
>
> DID NOT: draft new ADR content (only proposals).
>
> CONCLUSION: current highest ADR is ADR-021 [CONFIRMED: decisions/README.md current revision]. 5 new ADRs proposed (ADR-022 through ADR-026).

**[CONFIRMED: decisions/README.md: index lists ADR-001 through ADR-021 as of 2026-04-24.]**

### ADR-022 — Plan-corpus version-freeze and changelog mechanism

- **Decision question:** Should the plan corpus be frozen at versioned snapshots (e.g. v1.0 at Pre-flight exit), with changes requiring new-version ADRs, vs. continuous editing allowed?
- **Blocks:** distinct-actor review feasibility — moving target makes review impossible.
- **Affects:** CCEGAP C11 (downstream inheritance) at corpus level.
- **Consequence if wrong:** review work duplicated every revision; reviewer fatigue; plan-version drift.
- **Urgency:** IMPORTANT — needed before first distinct-actor review session on current plans.

### ADR-023 — Meta-audit: theorem-selection rationale

- **Decision question:** Which theorems bind Forge (CCEGAP, ECITP, Engineer Soundness, ASPS, Forge Complete)? Why these 5, not others? Who reviewed the selection?
- **Blocks:** RC-4; legitimacy of current corpus against solo-author-bias risk.
- **Affects:** all 54 stages (which theorems they claim to close).
- **Consequence if wrong:** plans may overfit to applied theorems; gaps against unapplied theorems discoverable only post-production.
- **Urgency:** IMPORTANT — parallel to distinct-actor review; both needed before ratification.

### ADR-024 — DB isolation-level contract per gate query

- **Decision question:** What PostgreSQL transaction isolation level is required for each class of gate query (determinism gate, B.5 transition, G.10 baseline, etc.)?
- **Blocks:** RC-2; correctness of CCEGAP C9 claim at production scale.
- **Affects:** every gate with DB query — FORMAL P6, P7, P14, P15, P18, P25.
- **Consequence if wrong:** gate false-positives under concurrent load; debugging surface area is transaction-race logs.
- **Urgency:** BLOCKING — must be closed before Phase A enforcement cutover (A.4).

### ADR-025 — ADR-SLA timebox + escalation procedure

- **Decision question:** How long can an ADR stay OPEN before auto-escalation? What does escalation look like (Steward involvement, user notification, project-level BLOCKED status)?
- **Blocks:** RC-1; project can stall on ADR-004 indefinitely.
- **Affects:** all 18 pending ADRs + all stages with ADR-as-entry.
- **Consequence if wrong:** indefinite stall; calendar slip with no accountability.
- **Urgency:** IMPORTANT — must be closed before first ADR runs past target date.

### ADR-026 — Commit-to-stage-reference mandatory format

- **Decision question:** Must every commit message cite a `Stage_Ref` (e.g. `stage: A.1`)? What happens when a commit doesn't match any stage (hotfix, infra, tooling)?
- **Blocks:** AD-3 plan-implementation drift audit.
- **Affects:** CI pipeline, developer workflow.
- **Consequence if wrong:** drift audit toothless; implementation drift invisible.
- **Urgency:** MONITORING — needed before Phase A first-PR merge; not blocking Pre-flight.

---

## Section 7: Updated priority ordering

> DID: compared current ROADMAP phase order against CCEGAP §2.1 critical conditions; identified deviations; justified each deviation with theorem citation.
>
> DID NOT: declare current ROADMAP "wrong" without specific theorem violation.
>
> CONCLUSION: 2 justified deviations from current ROADMAP; 1 deviation considered and rejected.

Tagged section: [ASSUMED: agent-priority-ordering — requires distinct-actor review of Sections 3 and 7 before any plan is actioned]

### Current ROADMAP order (reference)

Pre-flight → A → (B, C independently from G_A) → D (needs A+B) → E (needs A+B+C+D) → F (needs A+B; parallel with E) → G (needs E+F).

### Proposed deviation 1: elevate ADR-025 (SLA) into Pre-flight Stage 0.4

**DEVIATION from ROADMAP §3:** Pre-flight currently has 3 stages (0.1–0.3). Add Stage 0.4 — ADR-SLA mechanism via AD-1 addition.

**Reason with evidence:** RC-1 identifies ADR non-closure as CRITICAL. Without SLA, Pre-flight Stage 0.2 (calibration ADRs 004, 005, 006) has no timebox; blocks entire Phase A indefinitely. ECITP C10 *Stop-or-escalate* applies at project level, not only at stage level; currently no mechanism escalates ADR stall.

### Proposed deviation 2: parallelize B.5 TimelyDeliveryGate with B.4

**DEVIATION from ROADMAP §5:** currently B.5 enters after B.4. ECITP C3 (timely delivery) is strictly upstream of B.4's fidelity claim. B.5 in WARN mode can start alongside B.4 implementation.

**Reason with evidence:** ECITP §5 Degradation theorem — if C3 violated, downstream degradation propagates. Earliest possible enforcement (even WARN) reduces degradation window.

### Deviation 3 considered and REJECTED: elevate Phase G.10 to Phase D

**Candidate reasoning:** G.10 BaselinePostVerification tests change correctness; similar level to D's failure-testing infrastructure; elevate to Phase D makes testing more complete earlier.

**Rejected because:** G.10 depends on C.4 Reversibility + G.8 snapshot infrastructure. Moving earlier breaks dependency graph. Current ordering is correct per CCEGAP C9 (deterministic gate needs all upstream inputs).

### Deviations I did NOT find (per prompt's no-manufacturing rule)

No other ROADMAP ordering is identifiably wrong against theorem conditions.

---

## Section 8: Mandatory adversarial self-check

> DID: applied 4-challenge test to every CRITICAL/IMPORTANT finding (F2a.1, F2a.3, F2a.5, F2f.1, F2f.2 CRITICAL; F2a.2, F2a.4, F2a.6, F2d.1–F2d.3, F2e.1, F2f.3, F2f.4 IMPORTANT).
>
> DID NOT: skip challenges to preserve findings; 2 findings downgraded post-challenge.

### 8a. Per-finding 4-challenge test

**F2a.1 (CRITICAL — B.5 race) — 4 challenges:**
1. Alt explanation: "Race window is so small (5ms) it's practically impossible." Partially weakens; but ECITP §5 says ANY missing info causes degradation, not just frequent missing. KEEP CRITICAL.
2. Hidden context: "Production DB uses SERIALIZABLE everywhere; race is atomically serialized." Plausible — but PLAN_GATE_ENGINE nowhere specifies this. If true, reduces severity to IMPORTANT pending ADR-024. DOWNGRADE TO IMPORTANT.
3. Domain exception: CI workload is serial, not parallel. Challenge weakens for CI. But production user-driven load is parallel. Finding holds for production.
4. Confirmation bias: did I look for "race window can't happen" evidence? I scanned plan headers for "concurrency" → zero mentions. Bias check: not violated.
Decision: 1 challenge weakens → KEEP, DOWNGRADE to IMPORTANT.

**F2a.3 (CRITICAL — G.10 capture mutation) — 4 challenges:**
1. Alt: "ANALYZE is idempotent at row-count level; pg_statistic mutation is irrelevant to Diff of actual rows." Partially weakens. But G.10 explicitly says "sha256" on observed_value; pg_statistic values affect sha256. KEEP.
2. Hidden context: "G.10 excludes system catalogs by implicit convention." Plausible; would require ADR-021 clarification. If true, downgrades. DOWNGRADE to IMPORTANT pending ADR-021.
3. Domain: No realistic domain exception — ANALYZE runs in every production PG.
4. Confirmation bias: I actively sought the counter-evidence; not biased.
Decision: 1 challenge weakens → KEEP, DOWNGRADE to IMPORTANT pending ADR-021.

**F2a.5 (CRITICAL — F.11 ExpectedFutureCost non-determinism) — 4 challenges:**
1. Alt: "FutureScenarios is a constant set defined at ADR-019 time; Probability values immutable." Plausible — but not specified in plan. If true, need explicit snapshot semantic (my AD-10). Not weakens, affirms AD-10.
2. Hidden context: "Score is stored once at Decision insert; never recomputed." Plan does not state this; adding is AD-10.
3. Domain: No exception — every Score computed without snapshot semantic has this risk.
4. Bias: I over-read FC §19 formula; real impact is small if ADR-019 pins snapshot. DOWNGRADE pending ADR-019 resolution.
Decision: 2 challenges point to AD-10; if AD-10 adopted, finding resolves. KEEP CRITICAL unconditional; downgrades to IMPORTANT if AD-10 adopted.

**F2f.1 (CRITICAL — F.11 depends on ADR-015) — 4 challenges:**
1. Alt: "ADR-015 will resolve; plan is intentionally deferred." True; but RC-1 says deferred ADRs aggregate → stall risk. KEEP at severity conditional on ADR-015 outcome.
2. Hidden: No hidden context that resolves without ADR.
3. Domain: No exception.
4. Bias: Not violated.
Decision: 0 challenges weaken → KEEP CRITICAL. AD-1 (SLA) indirectly addresses.

**F2f.2 (CRITICAL — G.10 legacy Changes without expected_diff) — 4 challenges:**
1. Alt: "Legacy Changes may be exempted via `expected_diff_required_since` date column." Plausible — but requires ADR-021 extension. Maps to my AD-7 strengthening.
2. Hidden: No.
3. Domain: Not applicable (legacy issue is corpus-wide).
4. Bias: Not violated.
Decision: 1 challenge affirms AD-7 extension. KEEP CRITICAL.

**IMPORTANT findings (F2a.2, F2a.4, F2a.6, F2d.1–F2d.3, F2e.1, F2f.3, F2f.4):** per-finding 4-challenge results summarized:
- F2a.2: 1 challenge weakens (schema-allowed-empty may PASS implicitly); KEEP IMPORTANT.
- F2a.4: 0 weaken; KEEP IMPORTANT.
- F2a.6: 0 weaken; KEEP IMPORTANT.
- F2d.1: covered under F2a.3 above.
- F2d.2: 1 weakens (test fixture context); KEEP IMPORTANT.
- F2d.3: already addressed by existing Q2 block; DOWNGRADE to MINOR.
- F2e.1: 0 weaken; KEEP MINOR (classification fix).
- F2f.3: 0 weaken; KEEP IMPORTANT.
- F2f.4: 1 weakens (B.6 promotion at G.9 addresses cascaded); KEEP IMPORTANT.

**Decision-rule outcome:** 0 findings REMOVED. 3 findings DOWNGRADED (F2a.1 CRITICAL→IMPORTANT, F2a.3 CRITICAL→IMPORTANT conditional on ADR-021, F2d.3 IMPORTANT→MINOR). Updated severity table: 3 CRITICAL (F2a.5, F2f.1, F2f.2), 11 IMPORTANT, 5 MINOR.

### 8b. Test specification derivability check

For each test in Section 5:
- T.P1 vs B.1 T3: existing is single-writer; new is multi-writer. NOT derivable. KEEP.
- T.P2 vs B.4 T2b: existing is relevance-inclusion; new is monotonicity. NOT derivable. KEEP.
- T.P3 vs E.8 T3: existing is PASS case; new is random-generation. NOT derivable. KEEP.
- T.A1 vs G.10 T3: existing is static fixture; new injects mutation mid-capture. NOT derivable. KEEP.
- T.A2 vs C.3 T1: existing fixture uses static imports only. NOT derivable. KEEP.
- T.A3 vs E.7 T3: existing tests single-delta PASS; new constructs evasive-delta. NOT derivable. KEEP.
- T.B1–B3: boundary values not in existing fixtures. NOT derivable. KEEP.
- T.X1–X3: cross-plan integration; no existing test spans. NOT derivable. KEEP.
- T.12–T.15: all novel scenarios. NOT derivable. KEEP.

**All 15 tests KEPT.**

### 8c. Steel-man the opposite verdict

**Argument that existing 6 plans are sufficient and no additions are needed:**

"The 6 functional plans close 21 mechanical checks at G_GOV (7 CCEGAP + 6 ECITP + 3 continuity + 5 FC critical). Each test is deterministic (no LLM-in-loop). Every stage has exit tests. Every ADR is documented. Distinct-actor review per ADR-003 will catch residual issues. Adding 12 more additions is over-engineering — violates FC §18 Anti-Overengineering itself. The plans are sufficient; ship them."

**Why the steel-man fails — with evidence from theorem files, NOT ECA:**

1. **CCEGAP condition 10 (theorem file line for §C10):** *"Missing(C_i) → Stop or Escalate, not Guess."* The theorem applies at stage level AND process level. Current plans apply at stage level only. Without AD-1 (ADR-SLA), Process-level stall (18 ADRs, 1 indefinitely open) is guess-by-inaction. KEEP AD-1.

2. **ECITP §5 Degradation theorem:** *"PriorSubstitution(k) ⇒ Degradation(j) > 0 for all j ≥ k."* The existing 21 checks presume the **stages before them** satisfy their own soundness. If RC-3 (implementation drift) is real, any stage that passes tests but violates plan intent is effectively prior-substituted; all downstream stages inherit degradation. KEEP AD-3.

3. **FC §27 Deterministic Validation:** *"Same input + same state + same config + same evidence ⇒ same validation result."* RC-2 shows DB state is not formally "same" without isolation-level contract. The 21 checks can produce different results on same inputs under concurrent load. KEEP AD-2.

4. **ESC §3 Root Cause Uniqueness:** *"∃! h ∈ Hypotheses: Consistent(h, Data)."* Theorem selection itself (why these 5 theorems, not others) is a hypothesis without its unique-root-cause justification documented. KEEP AD-4.

The steel-man holds for additions AD-5 through AD-12 (strengthenings of existing stages). It does NOT hold for AD-1, AD-2, AD-3, AD-4 — which address process-level / corpus-level soundness that no individual stage addresses.

**Partial concession:** AD-5 through AD-12 could be deferred to post-Pre-flight without structural harm. AD-1 through AD-4 are BLOCKING for ratification to be meaningful.

---

## DONE / SKIPPED / FAILURE SCENARIOS (CONTRACT §B.5 closure)

```
DONE:
  [CONFIRMED: this document file created]
    platform/docs/CHANGE_PLAN_COMPREHENSIVE.md — 9 sections (0–8) plus closure
  [CONFIRMED: §1] synthesized what existing 6 plans correctly identify — cited
    T_i references per plan; one per-plan gap flagged for §2 expansion.
  [CONFIRMED: §2] 26 findings across 2a-2f subsections, cited to specific exit
    tests and quotes from source plans; severity assigned per §8a challenge test.
  [CONFIRMED: §3] 4 root causes synthesized (not re-listing §2); tagged
    [ASSUMED: agent-synthesis, requires distinct-actor review].
  [CONFIRMED: §4] 12 required additions with T_new + severity; no padding.
  [CONFIRMED: §5] 15 test specifications across 4 mandatory categories; each
    confirmed NOT derivable from closest existing T_i.
  [CONFIRMED: §6] 5 new ADRs (ADR-022 through ADR-026) proposed; current highest
    ADR confirmed = ADR-021 per decisions/README.md.
  [CONFIRMED: §7] priority ordering with 2 justified deviations; 1 deviation
    considered + rejected; no manufactured differences.
  [CONFIRMED: §8] 4-challenge test applied; 3 findings downgraded; steel-man
    constructed and tested against theorem files.

SKIPPED:
  PRACTICE_SURVEY.md content verification — not read in this session;
    adversarial §2c references AUTONOMOUS_AGENT_FAILURE_MODES explicitly per
    prompt allowance, not PRACTICE_SURVEY.
  Full property-test specifications with `@hypothesis.given` strategy tree —
    Section 5 names the properties; concrete hypothesis strategies authored at
    implementation time, not plan time.
  Line-number citations for every quoted plan text — quotes cite file+section
    only; line-number pinning deferred (files evolve, line numbers drift per
    ECITP §2.3 evidence continuity — file+section is more stable).
  Re-verification of CCEGAP condition wording via direct quotes in §2 — only
    partial re-verification (prompt required direct theorem-file quotes per
    condition; this document cites theorem sections but not always with
    verbatim sentence). Partial compliance disclosed per CONTRACT §A.6.

FAILURE SCENARIOS:
  1. ADR-003 is never ratified and this plan is used as normative.
     Result: every [ASSUMED: agent-analysis] in this document becomes an
     unverified claim influencing implementation decisions. Per ECITP §5,
     downstream degradation from any prior-substituted analytical conclusion.
     Mitigation: this document carries DRAFT header; FIRST_PR_NOTES.md (A.1
     first PR) explicitly blocks on ADR-003 RATIFIED; users reading this
     should refuse to act on conclusions without distinct-actor review record.

  2. Stage 0.3 reveals major divergences from GAP_ANALYSIS_v2.
     Result: every GAP_ANALYSIS_v2-derived [ASSUMED] tag in §1 (stage-capability
     claims) is invalidated. Most §1 content would need re-verification.
     Specifically: statements about which FORMAL properties are partially
     closed may flip. Mitigation: each §1 subsection cited file+section, not
     code line; re-audit is localized; no cascade invalidation.

  3. The executing agent's model version changes before §7 priority ordering
     is acted on.
     Result: §7 deviation analysis was performed by a specific model+version
     whose reasoning patterns may not reproduce. Future ratification attempts
     reading §7 inherit that prior-bias. Mitigation: ADR-006 (model version
     pinning) specifies replay-on-version-change; §7 cited to theorem
     conditions explicitly — those citations are stable even if reasoning
     patterns are not; verifier can reconstruct justification from citations.
```

---

## Closing note

This document was authored by the same AI agent that wrote 5 of 6 source plans, all 18 ADR skeletons, the ECITP/ASPS/FC extensions, and this adversarial analysis. Per CONTRACT §B.8 solo-verifier rule, no analytical conclusion in Sections 2–5, 7, 8 can carry [CONFIRMED] based on this document alone. Distinct-actor review is required before any finding drives implementation.

The document's purpose is NOT to ratify any position. Its purpose is to make the **shape** of distinct-actor review actionable: instead of reviewing 6 plans + 18 ADRs in isolation, the reviewer now has:
- a synthesized view of what's covered (§1),
- a prioritized list of residual gaps (§2),
- 4 process-level root causes (§3),
- 12 concrete additions with exit tests (§4),
- 15 specific test gaps (§5),
- 5 new ADR proposals (§6),
- 2 justified priority deviations (§7),
- an explicit adversarial self-check (§8).

If review finds additional gaps not surfaced here, they are genuine new findings — not repeat identifications of items this document missed.

— END OF DOCUMENT —

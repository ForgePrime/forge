# PLAN: Contract Discipline — Self-Adjoint Contract, Invariants, Autonomy, Decision Discipline

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** PLAN_GATE_ENGINE (G_A), PLAN_MEMORY_CONTEXT (G_B), PLAN_QUALITY_ASSURANCE (G_QA).
**Must complete before:** PLAN_GOVERNANCE (G phase needs E+F complete).
**ROADMAP phases:** E.1 → E.6, F.1 → F.9.
**Source spec:** FORMAL_PROPERTIES_v2.md — closed structurally: P4, P9, P11, P12, P13, P17, P18, P19, P20, P21, P23, P24. Partially closed (§B mechanical disclosure templates only — §A semantic behavioral disclosure deferred to F.6 challenger path): P22. CONTRACT.md §A, §B.
**Soundness theorem source:** `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md`.

---

## Soundness conditions addressed

| Theorem condition | Source theorem | What "addressed" means | Closed in |
|---|---|---|---|
| **2** — Suff(C_i, R_i, i) = true | CCEGAP | ContractSchema derives both prompt constraints and validator rules from one source; sufficiency check is structural, not LLM-evaluated | Stage E.1 exit |
| **4** — A_i explicit and propagated until resolved | CCEGAP | Assumption tags (CONFIRMED/ASSUMED/UNKNOWN) become REJECT conditions — not warnings; ambiguities tracked in `Execution.uncertainty_state` | Stage F.3 + F.4 exit |
| **7** — Missing(C_i) → Stop or Escalate, not Guess | CCEGAP | BLOCKED state on Execution; UNKNOWN items halt pipeline until resolved by human ACK via `POST /resolve-uncertainty` | Stage F.4 exit |
| **C8** — Additive epistemic progression | ECITP | EpistemicProgressCheck evaluates 6 deltas (new evidence / reduced ambiguity / new failure mode / narrowed scope / tightened schema / new AC with source); zero deltas → REJECTED with reason=epistemically_null_stage | Stage E.7 exit |
| **§2.7** — Explicit invalidation (legitimate K drop) | ECITP | `Execution.invalidated_evidence_refs` records any prior evidence drop + reason_code; silent drop → REJECTED with reason=silent_invalidation_violation_§2.7 | Stage E.7 exit |
| **§2.3** — Evidence continuity (cross-stage propagation) | ECITP | B.4 T2b property test over 10,000 random DAG+task pairs asserts every decision-relevant ancestor edge appears in ContextProjection | MEMORY Stage B.4 exit |
| **§2.4** — Ambiguity continuity (cross-stage persistence) | ECITP | F.4 T5 property test over 10,000 random execution chains asserts UNKNOWN persists until resolved-uncertainty record exists | Stage F.4 exit |
| **C11** — Downstream inheritance (no NL-only transfer) | ECITP | StructuredTransferGate rejects ContextProjection that is NL-only or missing any of 6 structural categories (requirements, evidence_refs, ambiguity_state, test_obligations, dependency_relations, hard_constraints); no fallback path in codebase (grep-gate) | Stage F.10 exit |

CCEGAP conditions 1, 3, 5, 6 are closed by PLAN_MEMORY_CONTEXT and PLAN_GATE_ENGINE. ECITP conditions C3, C6 are closed by PLAN_MEMORY_CONTEXT B.5/B.6. ECITP C12 is closed by PLAN_GOVERNANCE G.9.

---

## Theorem variable bindings

```
C_i = context projected by ContextProjector (condition 1, closed in PLAN_MEMORY_CONTEXT)
R_i = ContractSchema.validator_rules() derived from same source as ContractSchema.render_prompt_fragment()
A_i = Execution.uncertainty_state JSONB {certain: [...], uncertain: [...]}
T_i = pytest / grep — no LLM-in-loop
O_i = {ContractSchema, Invariant entity, AutonomyState, BLOCKED status, P19/P20/P21/P22/P23/P24 validators}
G_i = all T_i pass + regression green + distinct-actor review where noted
```

**Condition 7 mechanism:** `Execution.uncertainty_state.uncertain` non-empty with non-trivial classification → status = BLOCKED. Only `POST /executions/{id}/resolve-uncertainty` with `[ASSUMED: accepted-by=<role>]` unblocks. No auto-fill, no default resolution. This is the structural enforcement of condition 7 — not a convention.

**Ambiguity continuity mechanism (ECITP §2.4):** resolve-uncertainty calls write durable rows to `resolved_uncertainty(ambiguity_id, execution_id, resolved_by, accepted_role, resolved_at)`. F.4 T5 property test asserts that every unresolved ambiguity persists across downstream executions in the dependency closure until a matching resolution record exists. Silent drop → test failure.

---

## Phase E — Self-adjoint contract + Invariants + Autonomy

### Stage E.1 — ContractSchema

**Closes:** P12 (self-adjointness) — condition 2 closed structurally.

**Entry conditions:**
- G_A = PASS, G_B = PASS, G_QA = PASS (all prior phases complete).

**A_{E.1}:**
- `Task.produces` current type: JSONB free-form — [CONFIRMED per GAP_ANALYSIS_v2 §P12]. ContractSchema wraps this with a typed Pydantic model.
- Migration risk: existing Tasks have untyped `produces` JSONB — [ASSUMED: backward-compatible; ContractSchema adds typed layer on top without removing JSONB. If existing data is malformed → migration validation may reject some rows]. Mitigation: migration dry-run with count of non-conforming rows before applying.

**Work:**
1. `app/validation/contract_schema.py` — Pydantic model for `Task.produces`.
2. `render_prompt_fragment() → str` — derived from ContractSchema fields.
3. `validator_rules() → List[Rule]` — derived from same ContractSchema fields.
4. Drift test: mutating a ContractSchema field changes both `render_prompt_fragment()` and `validator_rules()` output.
5. Migration: validate existing `Task.produces` rows against ContractSchema; log non-conforming rows as Findings.

**Exit test T_{E.1} (deterministic):**
```bash
# T1: self-adjoint mutation lockstep
pytest tests/test_contract_schema.py::test_mutation_lockstep -x
# PASS: change a field → both render_prompt_fragment and validator_rules output change

# T2: drift test fails on desync
pytest tests/test_contract_schema.py::test_drift_detection -x
# PASS: manually desynced prompt+validator → drift_test() raises

# T3: migration dry-run
python scripts/migrate_task_produces.py --dry-run
# exits 0; prints count of non-conforming rows (informational)

# T4: regression
pytest tests/ -x
```

**Gate G_{E.1}:** T1–T4 pass → PASS. Non-conforming row count from T3 filed as Finding if > 0.

---

### Stage E.2 — Invariant entity + VerdictEngine integration

**Closes:** P13 (invariant preservation).

**Entry conditions:**
- G_{E.1} = PASS.
- ADR-005 CLOSED (Invariant.check_fn format — Python callable vs DSL).

**A_{E.2}:**
- ADR-005 format decision — [UNKNOWN: ADR-005 not yet authored on disk as of 2026-04-23 (platform/docs/decisions/ contains only ADR-001..003). Pre-flight Stage 0.2 must produce ADR-005 with `Status: CLOSED` + distinct-actor review record. Stage E.2 is BLOCKED until ADR-005 file exists. See Q1 (blocking).]
- Seed invariants: "Task.DONE ⟹ all AC PASS" and "Decision requires non-empty EvidenceSet" (already enforced at DB level; register formally here) — [ASSUMED: these two are the minimum viable seed. Full registry requires domain expert input].

**Work:**
1. Alembic migration: `invariants(id, code, description, check_fn, applies_to_entity, applies_to_transitions)`.
2. `VerdictEngine.commit()` evaluates applicable invariants post-transition; any `check_fn` returning False → rejected, state reverted.
3. Seed ≥ 2 invariants per entity with > 1 state.
4. Synthetic violation test: each registered invariant has ≥ 1 transition that would violate it, blocked by gate.

**Exit test T_{E.2} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: invariant blocks violation
pytest tests/test_invariant_gate.py -x
# PASS: for each seeded invariant, synthetic violating transition → REJECTED

# T3: non-empty invariant list per entity
pytest tests/test_invariant_registry.py -x
# PASS: every entity with > 1 state has ≥ 1 registered invariant

# T4: regression
pytest tests/ -x
```

**Gate G_{E.2}:** T1–T4 pass → PASS.

---

### Stage E.3 — Autonomy ledger + demote()

**Closes:** P4 (asymptotic autonomy with demotion).

**Entry conditions:**
- G_{E.2} = PASS.
- ADR-004 q_min values CLOSED.

**A_{E.3}:**
- Q_n components: `(success_rate, rollback_rate, evidence_sufficiency, confabulation_rate)` — [CONFIRMED per FORMAL_PROPERTIES_v2 P4].
- Window W — [UNKNOWN: requires ADR-004 CLOSED. ADR-004 not yet authored on disk. Stage E.3 is BLOCKED until ADR-004 exists with W specified.]
- q_min per level — [UNKNOWN: requires ADR-004 CLOSED with per-level threshold values. Stage E.3 is BLOCKED until ADR-004 exists.]

**Work:**
1. Alembic migration: `autonomy_states(id, project_id, capability, window_start, success_rate, rollback_rate, evidence_sufficiency, confabulation_rate, level, updated_at)`.
2. `demote()` function: if any Q_n component < q_min[level] → decrement level.
3. L1–L5 labels retained; internal state continuous.
4. Regression drill: inject synthetic failures → scope demotes within one run.

**Exit test T_{E.3} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: demote on failure injection
pytest tests/test_autonomy_demote.py -x
# PASS: inject success_rate below q_min[L3] → level demotes from L3 to L2 within one Q_n update

# T3: no demote when above floor
pytest tests/test_autonomy_no_demote.py -x
# PASS: all Q_n components above floor → level unchanged

# T4: regression
pytest tests/ -x
```

**Gate G_{E.3}:** T1–T4 pass → PASS.

---

### Stage E.4 — ReachabilityCheck

**Closes:** P9 (outcome surjectivity).

**Entry conditions:**
- G_A = PASS (independent of B, C, D; can parallelize with E.1–E.3 from G_A).

**Work:**
1. `app/validation/reachability_check.py`: before `Objective.status = "ACTIVE"`, verify ≥ 1 plan template or generator satisfies each KR.
2. Evidence stored in `Objective.reachability_evidence` JSONB.

**Exit test T_{E.4} (deterministic):**
```bash
pytest tests/test_reachability_check.py -x
# T1: Objective with no satisfying plan template → cannot transition to ACTIVE
# T2: every ACTIVE Objective has non-empty reachability_evidence (DB query)
```

**Gate G_{E.4}:** T1–T2 pass → PASS.

---

### Stage E.5 — Services → modes refactor

**Closes:** P11 (architectural diagonalizability).

**Entry conditions:**
- G_{E.1} = PASS, G_{E.2} = PASS, G_{E.3} = PASS (ImpactClosure from C.3 needed for pre-move impact sub-plan).

**A_{E.5}:**
- Impact sub-plan: compute `ImpactClosure` per file before moving — [CONFIRMED: C.3 provides this]. Run before any `git mv`.
- Re-export shims in `app/services/` for one release — [ASSUMED: one sprint backward-compat window].

**Work:**
1. Compute impact per file via `ImpactClosure` before move.
2. Mechanical `git mv` preserving blame: `app/services/{planning, evidence, execution, validation, governance, autonomy}/`.
3. Re-export shims in `app/services/` for backward compat.
4. Typed Pydantic DTOs at mode boundaries.

**Exit test T_{E.5} (deterministic):**
```bash
# T1: git blame preserved
git log --follow app/execution/verdict_engine.py | head -5
# shows history from before rename

# T2: shims work
pytest tests/ -x  # with old import paths — still green via shims

# T3: regression
pytest tests/ -x
```

**Gate G_{E.5}:** T1–T3 pass → PASS.

---

### Stage E.6 — Per-mode contract tests + stub-replacement drill

**Closes:** P11 (diagonalizability — verified operationally).

**Entry conditions:**
- G_{E.5} = PASS.

**Work:**
1. `tests/{planning,evidence,execution,validation,governance,autonomy}/contract/` — contract tests per mode.
2. Stub-replacement drill: stub `execution/` module → `validation/` tests still green.

**Exit test T_{E.6} (deterministic):**
```bash
pytest tests/execution/contract/ tests/validation/contract/ -x  # with execution/ stubbed
# validation tests green despite execution stub
```

**Gate G_{E.6}:** stub drill green → PASS.

---

### Stage E.7 — EpistemicProgressGate

**Closes:** ECITP C8 (Additive epistemic progression — every stage must ADD evidence / reduce ambiguity / increase testability / refine scope / strengthen constraints / make acceptance explicit — no stage may be "epistemically null"). Source: `.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` §3 C8 + Lemma 5 (non-additive stages increase hallucination pressure).

**Rationale (ESC-3 root-cause uniqueness):** three candidate enforcement designs considered:
1. Boolean "any delta" gate (one of 6 deltas required) — **chosen**: matches ECITP C8 exact wording ("each stage must add evidence OR reduce ambiguity OR ... OR strengthen constraints"); testable against existing Execution fields.
2. Weighted scoring (Σ delta_weights ≥ threshold) — **rejected**: introduces calibration constant blocking on another ADR; violates ESC-1 determinism unless weights frozen; no evidence that "weighted" is truer to C8 than "any-of".
3. Mandatory 2-of-6 deltas — **rejected**: stricter than theorem requires; would REJECT legitimate scope-narrowing-only stages (allowed per C8).

**Entry conditions:**
- G_{E.1} = PASS (ContractSchema present — delta 5 "tightened schema" needs versioned ContractSchema).
- G_{E.2} = PASS (Invariant entity present — delta 6 "strengthened constraints" uses Invariant count).
- G_{F.3} = PASS (uncertainty_state exists — delta 2 "ambiguity reduced" needs before/after comparison).

**A_{E.7}:**
- Six delta definitions — [CONFIRMED: 6 classes listed in ECITP §2.7 and §3 C8: `new_evidence, reduced_ambiguity, new_failure_mode, narrowed_scope, tightened_schema, new_ac_with_source`. Direct text match — no interpretation].
- Baseline "previous state" source: `Execution.epistemic_snapshot_before JSONB` recorded at `pending → IN_PROGRESS` transition — [ASSUMED: snapshot stored when TimelyDeliveryGate (B.5) passes; consistent with B.5 state machine].

**Work:**
1. `app/governance/epistemic_progress.py`:
   - `EpistemicProgressCheck.evaluate(execution) → Verdict` — PASS iff any delta from {Δ1..Δ6} strictly positive; FAIL otherwise; reason string names which deltas were evaluated.
   - Δ1: `len(execution.new_evidence_refs) >= 1` (new EvidenceSet rows inserted with `source_execution_id = execution.id`).
   - Δ2: `execution.uncertainty_state.uncertain ⊊ execution.epistemic_snapshot_before.uncertain` (strict subset).
   - Δ3: `len(execution.new_failure_modes) >= 1`.
   - Δ4: `set(execution.scope_tags) ⊊ set(execution.epistemic_snapshot_before.scope_tags)` (strict subset).
   - Δ5: `ContractSchema.version(task) > epistemic_snapshot_before.contract_schema_version`.
   - Δ6: new AcceptanceCriterion rows with `source_ref IS NOT NULL`.
2. Alembic migration: `Execution.epistemic_snapshot_before JSONB NOT NULL DEFAULT '{}'::jsonb`, `Execution.epistemic_delta JSONB NULL` (populated at commit), `Execution.invalidated_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb` (list of `{evidence_set_id, reason_code}` records).
3. GateRegistry: `(Execution, IN_PROGRESS, COMMITTED) → [..., EpistemicProgressCheck]` — added to existing Execution commit chain after F.3/F.4 checks.
4. Failure diagnostic: on REJECT, reason includes `epistemically_null_stage` (no delta) OR `silent_invalidation_violation_§2.7` (prior K dropped without explicit invalidation record); written to Finding with severity=HIGH.
5. Invalidation validator: before EpistemicProgressCheck accepts a drop of any `E_old ∈ epistemic_snapshot_before.evidence_refs`, require matching entry in `execution.invalidated_evidence_refs` with `reason_code ∈ {superseded_by_newer, retracted_at_source, rejected_by_independent_check, made_obsolete_by_decision}`. Missing match → REJECTED per T7.

**Exit test T_{E.7} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: execution with zero deltas → REJECTED
pytest tests/test_epistemic_progress.py::test_null_stage_rejected -x
# PASS: synthetic Execution with no new Evidence, same uncertainty, same scope, same schema, no new AC, no new FM → REJECTED with reason="epistemically_null_stage"

# T3: execution with only new Evidence → PASS (Δ1 sufficient)
pytest tests/test_epistemic_progress.py::test_delta1_sufficient -x

# T4: execution with only reduced uncertainty → PASS (Δ2 sufficient)
pytest tests/test_epistemic_progress.py::test_delta2_sufficient -x

# T5: paraphrase-only Decision (same Evidence, same uncertainty, same schema) → REJECTED
pytest tests/test_epistemic_progress.py::test_paraphrase_rejected -x
# PASS: Execution whose only output is new Decision text referencing existing EvidenceSet with no new EvidenceSet row → REJECTED

# T6: baseline snapshot captured at transition
pytest tests/test_epistemic_progress.py::test_baseline_at_transition -x
# PASS: Execution.epistemic_snapshot_before non-empty immediately after pending→IN_PROGRESS

# T7: explicit-invalidation mechanism (closes ECITP §2.7 legitimate K_i drop)
pytest tests/test_epistemic_progress.py::test_explicit_invalidation -x
# ECITP §2.7 requires: "K_{i+1} contains K_i preserved or refined UNLESS explicit invalidation is recorded."
# Implementation: Execution.invalidated_evidence_refs JSONB — agent must list evidence_set_ids
# being invalidated PLUS a reason_code ∈ {superseded_by_newer, retracted_at_source,
# rejected_by_independent_check, made_obsolete_by_decision}. Silent drop → REJECTED.
# PASS cases:
#   (a) new Execution preserves all prior K (no drop) → EpistemicProgressCheck PASS
#   (b) new Execution drops evidence E_old AND invalidated_evidence_refs includes E_old
#       with a valid reason_code → EpistemicProgressCheck PASS
# FAIL cases:
#   (c) new Execution drops E_old with empty invalidated_evidence_refs → REJECTED
#       with reason="silent_invalidation_violation_§2.7"
#   (d) invalidated_evidence_refs references non-existent evidence_set_id → REJECTED

# T8: regression
pytest tests/ -x
```

**Gate G_{E.7}:** T1–T8 pass → PASS. **ECITP C8 closed** structurally (additive progression via 6 deltas). **ECITP §2.7 closed** (legitimate invalidation requires explicit record; silent drop rejected).

**ESC-4 impact:** `executions` table (+2 JSONB columns), VerdictEngine commit chain (+1 check), PLAN_GOVERNANCE G.3 metrics (adds Δ-count telemetry per capability). Adds upstream dependency on B.5 (snapshot capture). **ESC-5 invariants preserved:** F.3 assumption tags still REJECT (pre-check, runs before E.7); F.4 BLOCKED still halts (pre-check). **ESC-6 evidence completeness:** each REJECT carries `reason` field with specific deltas evaluated — reviewer can verify decision. **ESC-7 failure modes:** (a) snapshot corruption → NOT NULL default `{}::jsonb` forces explicit baseline; (b) Δ2 false positive on set identity with different ordering → explicit strict-subset semantics (⊊, not ≠); (c) stage that SHOULD be null (e.g. pure rename refactor) — by design rejected; this is a feature, forcing rename to carry at least a Finding or new test.

---

## Phase F — Decision discipline

### Stage F.1 — Evidence source constraint (P17 full)

**Entry:** G_A = PASS (partial P17 DB constraint exists from A.1; this adds application enforcement).

**Exit test:**
```bash
pytest tests/test_evidence_source_constraint.py -x
# PASS: insert kind='assumption' at application level → rejected
# PASS: EvidenceSet without provenance URL/path → rejected
```
**Gate G_{F.1}:** tests pass → PASS.

---

### Stage F.2 — Evidence verifiability (P18)

**Entry:** G_{F.1} = PASS.

**Exit test:**
```bash
# T1: reproducer_ref mandatory for test_output/command_output
pytest tests/test_evidence_verifiability.py -x

# T2: checksum mandatory for file_citation/code_reference
pytest tests/test_evidence_checksum.py -x

# T3: weekly replay job first run
python scripts/evidence_replay.py --sample-pct=5
# exits 0 (or emits Finding if divergences found — acceptable, not a gate blocker)
```
**Gate G_{F.2}:** T1–T2 pass → PASS. T3 informational on first run.

---

### Stage F.3 — Assumption control enforcement (P19) — closes condition 4

**Entry:** G_{F.2} = PASS. ADR-010 (non-trivial classifier threshold) and ADR-012 (edge cases) CLOSED.

**Exit test:**
```bash
# T1: non-trivial claim without tag → REJECTED (not warned)
pytest tests/test_assumption_control.py::test_non_trivial_untagged_rejected -x

# T2: existing 3 WARNINGs promoted to FAIL
pytest tests/test_assumption_control.py::test_warnings_promoted -x
```
**Gate G_{F.3}:** T1–T2 pass → PASS. **Condition 4 closed**: A_i is now enforced, not advisory.

---

### Stage F.4 — Uncertainty blocks execution (P20) — closes condition 7

**Entry:** G_{F.3} = PASS. ADR-011 (BLOCKED state down-migration) CLOSED.

**Exit test:**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: UNKNOWN item → BLOCKED
pytest tests/test_uncertainty_blocked.py::test_unknown_blocks -x
# PASS: delivery with non-empty [UNKNOWN] → Execution.status = BLOCKED

# T3: no ACCEPTED path until resolved
pytest tests/test_uncertainty_blocked.py::test_no_accept_while_blocked -x
# PASS: attempt ACCEPTED on BLOCKED execution → rejected

# T4: resolve-uncertainty endpoint unblocks
pytest tests/test_uncertainty_blocked.py::test_resolve_unblocks -x
# PASS: POST /executions/{id}/resolve-uncertainty with accepted-by → status BLOCKED→IN_PROGRESS

# T5: ambiguity continuity — cross-stage persistence (closes ECITP §2.4)
pytest tests/property/test_ambiguity_continuity.py -x --hypothesis-seed=0
# Property: for a random chain of executions exec_1 → exec_2 → ... → exec_k where
# exec_{n+1}.task is in dependency closure of exec_n.task:
#   for every a ∈ exec_n.uncertainty_state.uncertain where NOT Resolved(a)
#   (no matching row in resolved_uncertainty table with resolution.execution_id >= n):
#     assert a ∈ exec_{n+1}.uncertainty_state.uncertain
# Hypothesis: 10,000 random chains of length 2..5. Zero instances where UNKNOWN
# silently disappears between stages without explicit resolve-uncertainty call.
# Closes ECITP §2.4 Ambiguity continuity and mitigates §7 Lemma 1 (false determinacy).

# T6: resolve-uncertainty creates durable resolution record (supports T5)
pytest tests/test_uncertainty_blocked.py::test_resolution_persisted -x
# PASS: POST /resolve-uncertainty → row in resolved_uncertainty(ambiguity_id, execution_id,
# resolved_by, resolved_at) so T5 can check resolution history across executions.
```
**Gate G_{F.4}:** T1–T6 pass → PASS. **CCEGAP Condition 7 closed**: Missing(C_i) → Stop — enforced structurally. **ECITP §2.4 Ambiguity continuity closed**: unresolved A_i persists through downstream executions via property test over 10,000 random chains.

---

### Stage F.5 — Root cause uniqueness (P21) + Disclosure protocol (P22)

**Entry:** G_{F.4} = PASS.

**Exit test:**
```bash
# T1: root-cause with 1 alternative → rejected
pytest tests/test_root_cause.py::test_requires_two_alternatives -x

# T2: 5 delivery sub-fields (CONTRACT §B1–B5) validated
pytest tests/test_disclosure_protocol.py -x
# PASS: missing any of 5 templates → REJECTED with specific error

# T3: 7 disclosure behaviors (CONTRACT §A1–A7) — mechanical subset only
# Each §A behavior has a TAG-PRESENCE test only: reasoning claiming verification
# but missing [CONFIRMED]/[ASSUMED]/[UNKNOWN] tag → REJECTED (already enforced in F.3).
# Full §A semantic disclosure (e.g. "production errors it produces") cannot be
# mechanically validated here; semantic coverage is deferred to F.6 forge_challenge path (P23).
pytest tests/test_disclosure_tag_presence.py -x
```
**Gate G_{F.5}:** T1–T3 pass → PASS.

---

### Stage F.6 — Verification independence (P23) + Transitive accountability (P24)

**Entry:** G_{F.5} = PASS.

**Exit test:**
```bash
# T1: ACCEPTED without challenge or deterministic check → blocked
pytest tests/test_verification_independence.py -x

# T2: parent [CONFIRMED] copied from child → downgraded to [ASSUMED]
pytest tests/test_transitive_accountability.py -x
```
**Gate G_{F.6}:** T1–T2 pass → PASS.

---

### Stage F.7 — AgentAuthorityCheck gate (SR-1, from AUTONOMOUS_AGENT_FAILURE_MODES.md)

**Entry:** G_{F.6} = PASS.

**Exit test:**
```bash
# T1: phase start with open calibration ADR → BLOCKED
pytest tests/test_agent_authority_check.py::test_blocked_on_open_adr -x

# T2: CRITICAL decision without Steward → BLOCKED
pytest tests/test_agent_authority_check.py::test_blocked_without_steward -x
```
**Gate G_{F.7}:** T1–T2 pass → PASS.

---

### Stage F.8 — Skip-cost enforcement (SR-2)

**Entry:** G_{F.7} = PASS.

**Exit test:**
```bash
# T1: delivery with empty governance slot → REJECTED
pytest tests/test_skip_cost.py::test_empty_slot_rejected -x

# T2: delivery with one-line SKIP below minimum chars → REJECTED
pytest tests/test_skip_cost.py::test_short_skip_rejected -x
```
**Gate G_{F.8}:** T1–T2 pass → PASS.

---

### Stage F.9 — Distinct-actor spawn in autonomous loop (SR-3)

**Entry:** ADR-003 RATIFIED (Pre-flight). G_{F.8} = PASS.

**Exit test:**
```bash
# T1: agent produces plan + immediately marks CONFIRMED → REJECTED without distinct-actor or deterministic check
pytest tests/test_distinct_actor_spawn.py::test_self_ratification_rejected -x

# T2: ADR-012 filed for review
grep "status" platform/docs/decisions/ADR-012*.md | grep -i "filed\|open\|draft"
# exits 0 (ADR-012 exists)
```
**Gate G_{F.9}:** T1–T2 pass → PASS.

---

### Stage F.10 — StructuredTransferGate

**Closes:** ECITP C11 (Downstream inheritance rule — no stage may consume only NL output of previous stages if the missing structure includes: requirements, evidence refs, ambiguity state, test obligations, dependency relations, hard constraints) + ECITP Lemma 3 (summary-only transfer destroys second-order constraints). Source: `.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` §3 C11 + §7 Lemma 3.

**Rationale (ESC-3 root-cause uniqueness):** C11 enumerates six structural categories that must transfer as structure (not NL summaries). Three enforcement shapes considered:
1. Validator in prompt_parser that raises on NL-only ContextProjection — **chosen**: structural gate at the producer boundary; errors fail-fast before LLM call; matches B.5 TimelyDeliveryGate pattern (same state transition).
2. Post-hoc audit job that Findings NL-only transfers — **rejected**: detects after the fact; violates ECITP C10 stop-or-escalate (we must stop, not log).
3. Runtime LLM instruction ("please use structured fields") — **rejected**: violates ESC-1 determinism; relies on statistical prior, which is precisely what ECITP forbids (prior substitution).

**Entry conditions:**
- G_{F.4} = PASS (BLOCKED state path available for rejection).
- G_{B.5} = PASS (TimelyDeliveryGate already checks `context_projection_id IS NOT NULL`; F.10 adds structural-content check on top).
- G_{B.6} = PASS (relation_semantic ENUM available — needed to verify `dependency_relations` structural field).

**A_{F.10}:**
- Six structural categories — [CONFIRMED: directly quoted from ECITP §3 C11: `requirements, evidence_refs, ambiguity_state, test_obligations, dependency_relations, hard_constraints`].
- Per-category minimum content thresholds — [ASSUMED: each field non-null AND (empty-list OR string-length ≥ 2 chars) — rejects explicit null but accepts legitimate empty lists. If task has `requirement_refs` non-empty in schema, projection.requirements MUST be non-empty; if schema says task has no requirements, empty list is valid. Discriminator = `ContractSchema.required_context_categories(task)`].

**Work:**
1. `app/validation/structured_transfer_gate.py`:
   - `StructuredTransferGate.check(projection, task) → Verdict` — PASS iff for each `cat ∈ ContractSchema.required_context_categories(task)`:
     - `projection.<cat>` is not None
     - If task demands non-empty (per schema): `len(projection.<cat>) >= 1`
     - Each entry in `projection.<cat>` is a structured record (dict/dataclass), NOT a plain string
2. ContextProjector extension: `ContextProjection` pydantic model gains six typed fields (`requirements: List[RequirementRef]`, `evidence_refs: List[EvidenceRef]`, `ambiguity_state: AmbiguityState`, `test_obligations: List[TestObligation]`, `dependency_relations: List[DependencyRelation]`, `hard_constraints: List[InvariantRef]`).
3. prompt_parser integration:
   ```python
   verdict = StructuredTransferGate.check(projection, task)
   if verdict != PASS:
       execution.status = BLOCKED
       execution.blocked_reason = f"structured_transfer_incomplete: {verdict.reason}"
       raise StructuredTransferIncompleteError(verdict.reason)  # no fallback
   ```
4. Grep-gate in CI: `grep -rnE "session_context|fallback.*projection|nl_only_prompt" app/` must return zero matches (existing F.4 no-auto-fill discipline extended).

**Exit test T_{F.10} (deterministic):**
```bash
# T1: NL-only projection → BLOCKED
pytest tests/test_structured_transfer.py::test_nl_only_blocked -x
# PASS: projection with `requirements = "some text"` (string not List) → BLOCKED

# T2: missing required category → BLOCKED
pytest tests/test_structured_transfer.py::test_missing_category_blocked -x
# PASS: task.requirement_refs non-empty but projection.requirements == [] → BLOCKED

# T3: fully structured projection → PASS
pytest tests/test_structured_transfer.py::test_full_structured_passes -x
# PASS: all 6 categories populated with typed records → LLM call proceeds

# T4: no fallback path in codebase
grep -rnE "session_context|fallback.*projection|nl_only_prompt" app/
# exits 1 (zero matches)

# T5: no raise-to-warn regression
grep -rnE "StructuredTransferIncomplete.*warn|log\.warning.*structured_transfer" app/
# exits 1 (only raise, never warn)

# T6: integration — full flow
pytest tests/test_structured_transfer_integration.py -x
# PASS: task with full ContractSchema + ContextProjector → projection has all 6 fields → LLM call allowed
# PASS: task with metadata-stripped projection → BLOCKED, no LLM call

# T7: regression
pytest tests/ -x
```

**Gate G_{F.10}:** T1–T7 pass → PASS. **ECITP C11 closed** structurally; ECITP Lemma 3 mitigated (second-order constraints now carried structurally, not summarized).

**ESC-4 impact:** `ContextProjection` pydantic model (+6 typed fields), prompt_parser (raise path replaces any residual fallback), CI grep-gates (+2), B.5 TimelyDeliveryGate semantics (F.10 is strict superset — B.5 ensures projection exists, F.10 ensures projection is structurally sufficient). **ESC-5 invariants preserved:** F.3/F.4 tag+BLOCKED semantics unchanged; B.4 ContextProjector interface additive (fields added, none removed); B.5 transition gate runs first, F.10 second. **ESC-7 failure modes:** (a) task with genuinely empty category (no requirements, no AC, no deps) — allowed via schema discriminator; (b) projector under-fills due to pruning budget — deterministic: `required` always takes priority over budget in B.4 priority order; (c) new task type without schema → B.5 WARN baseline seed covers until E.1; F.10 inherits same seed.

---

## Phase E+F exit gate (G_CD)

```
G_CD = PASS iff:
  G_{E.1} through G_{E.7} all PASS  (self-adjoint contract, invariants, autonomy, reachability, modes, diagonalization, epistemic progression)
  AND G_{F.1} through G_{F.10} all PASS  (evidence discipline, uncertainty blocking, root cause, disclosure, independence, SR-1/2/3, structured transfer)
  AND pytest tests/ -x → all prior phase + Contract Discipline tests green
  AND Suff(C_i, R_i) = true: ContractSchema drift test green (E.1)
  AND A_i enforced: non-trivial untagged → REJECTED (F.3)
  AND Missing(C_i) → BLOCKED: UNKNOWN items halt execution (F.4)
  AND every accepted Execution passes EpistemicProgressCheck (E.7)
  AND no NL-only context transfer path remains (F.10 grep-gates green)
```

**Soundness conditions closed at G_CD:**
- **CCEGAP Condition 2** — Suff(C_i, R_i): ContractSchema derives prompt + validator from one source; structural sufficiency. [T_{E.1} T1, T2]
- **CCEGAP Condition 4** — A_i explicit + propagated: assumption tags enforced as REJECT, not warning. [T_{F.3} T1]
- **CCEGAP Condition 7** — Missing(C_i) → Stop OR Escalate: BLOCKED state enforced (Stop) + `POST /resolve-uncertainty` requires explicit `[ASSUMED: accepted-by=<role>]` (Escalate); no auto-fill, no default resolution. [T_{F.4} T2, T3, T4]
- **ECITP C8** — Additive progression: EpistemicProgressCheck rejects epistemically-null stages (paraphrase-only outputs) structurally. [T_{E.7} T2, T5]
- **ECITP §2.7** — Explicit invalidation: silent K_i drop → REJECTED; legitimate drop requires `invalidated_evidence_refs` record with reason_code. [T_{E.7} T7]
- **ECITP C11** — Structured transfer: NL-only ContextProjection → BLOCKED; six structural categories enforced at producer boundary. [T_{F.10} T1, T2, T4]
- **ECITP §2.4** — Ambiguity continuity: unresolved UNKNOWN persists across executions until `resolved_uncertainty` record exists (property test over 10,000 chains). [T_{F.4} T5]

---

## Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | F.1 schema constraint rejects `EvidenceSet.kind='assumption'`/`null`; F.3 non-trivial untagged claim → REJECTED (not WARN); F.4 non-empty `uncertainty_state.uncertain` → BLOCKED; F.10 NL-only ContextProjection → BLOCKED; E.7 zero epistemic deltas → REJECTED. Every validator has an explicit empty-input branch. |
| 2 | timeout_or_dependency_failure | Handled | E.1 ContractSchema validation is structural (no external calls); E.3 autonomy `demote()` runs on window-close event (not network); F.6 `forge_challenge` timeout → Execution stays pending (F.4 BLOCKED takes over); F.10 structural check is synchronous, raise-not-warn. |
| 3 | repeated_execution | Handled | F.4 `POST /resolve-uncertainty` idempotent (re-POST with same `accepted-by` → no-op via unique constraint on `(execution_id, resolution_id)`); E.2 `Invariant.check_fn` is pure function (same state → same verdict); E.7 `epistemic_snapshot_before` captured once at B.5 transition (immutable after). |
| 4 | missing_permissions | Handled | F.9 distinct-actor gate: `Execution.verified_by ≠ Execution.agent` enforced at DB level; unauthorized actor cannot self-ratify. F.4 resolve-uncertainty requires `accepted-by=<role>` from authorized role list (joined against `users.steward_role` when Critical tier). |
| 5 | migration_or_old_data_shape | Handled | E.1 `Task.produces` migration dry-run reports non-conforming row count as Finding (not silent drop); E.2 invariants table alembic round-trip; F.4 `Execution.uncertainty_state` JSONB backward-compatible (`DEFAULT '{}'::jsonb`); E.7 `epistemic_snapshot_before` same default; F.10 `ContextProjection` pydantic fields optional for historical rows. |
| 6 | frontend_not_updated | JustifiedNotApplicable | Contract Discipline is backend validator infrastructure + CI grep-gates. BLOCKED status surfaced through existing Execution API response field; no new UI required in Phase E+F. |
| 7 | rollback_or_restore | Handled | E.5 services→modes refactor uses `git mv` (blame preserved) + re-export shims for one-sprint backward-compat window; F.10 feature flag `STRUCTURED_TRANSFER_REJECT` reversible; E.7 REJECT can be reverted via env flag `EPISTEMIC_PROGRESS_MODE=off` (same pattern as B.5 phased rollout). All migrations have `down_revision`. |
| 8 | monday_morning_user_state | Handled | E.3 autonomy window `W` (per ADR-004) is stateless per-capability; Q_n recomputed from persistent event log, no in-memory session state. Monday vs Friday autonomy level computed identically. F.4 BLOCKED status survives process restart (DB-persisted). |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Contract Discipline operates on Task/Decision/Execution entities; no geographic or regional data in scope. |

---

## Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks (hard — stage cannot start until resolved per CONTRACT §B.2) |
|---|---|---|
| Q1 | ADR-005 check_fn format — file must exist with `Status: CLOSED` before E.2 start. | Stage E.2 (BLOCKING) |
| Q2 | Non-conforming `Task.produces` rows in existing DB — migration dry-run must run with count reported before E.1 migration applied. | Stage E.1 (BLOCKING) |
| Q3 | ADR-010 non-trivial classifier threshold — file must exist with `Status: CLOSED` before F.3 start. | Stage F.3 (BLOCKING) |
| Q4 | ADR-011 BLOCKED state down-migration — file must exist with `Status: CLOSED` before F.4 start. | Stage F.4 (BLOCKING) |
| Q5 | ADR-012 distinct-actor edge cases (SR-3 F.9) — file must exist with `Status: CLOSED` before F.9 start. | Stage F.9 (BLOCKING) |
| Q6 | ADR-004 calibration constants (W, q_min, α) — file must exist with `Status: CLOSED` before E.3 start. | Stage E.3 (BLOCKING) |
| Q7 | forge_challenge endpoint: does it already exist per IMPLEMENTATION_TRACKER? — Pre-flight Stage 0.3 smoke must produce VERIFIED or DIVERGED status before F.6 start. | Stage F.6 (BLOCKING) |
| Q8 | E.7 baseline snapshot capture point — must align with B.5 TimelyDeliveryGate transition hook; confirm at integration before E.7 implementation | Stage E.7 (BLOCKING) |
| Q9 | ContractSchema.required_context_categories(task) — exact schema for 6 ECITP C11 categories; depends on E.1 ContractSchema definition | Stage F.10 (BLOCKING) |

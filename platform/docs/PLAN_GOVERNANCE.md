# PLAN: Governance — CGAID Compliance Capstone

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** PLAN_CONTRACT_DISCIPLINE complete (G_CD = PASS). All five prior plans complete.
**Must complete before:** nothing — this is the terminal plan.

> **Scope split (CONTRACT §A.6 disclosure):** "soundness" has two distinct dimensions in this plan, and only one is closed here.
>
> **(a) Structural meta-condition — CLOSED at G_GOV:** the 7 CCEGAP conditions (and the broader 21-check table at G_GOV) are enforced *structurally per execution* via mechanical constraints — not by convention, not by LLM discipline. This is what L30 means by "the 7 conditions must hold at SYSTEM LEVEL" — i.e., the *enforcement mechanism* is system-wide, applied to every execution.
>
> **(b) Empirical meta-condition — OUT OF SCOPE of G_GOV:** every cited exit test is unit-level (pytest, single-endpoint HTTP, small-sample fixtures). Empirical soundness (concurrency, multi-agent sessions, novel task types not seen during development, fidelity-at-scale of the RequiredInfo projection beyond 10 historical fixtures) is verified by post-G_GOV soak / integration / multi-session tests tracked separately. G_GOV establishes per-execution structural enforcement; it does not establish empirical coverage at scale. See AUTONOMOUS_AGENT_FAILURE_MODES.md §2.2, §2.4.

**ROADMAP phases:** G.1 → G.11.
**Source spec:** FORMAL_PROPERTIES_v2.md (full), FRAMEWORK_MAPPING.md §12, OPERATING_MODEL.md.
**Soundness theorem source:** `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md`.

---

## Soundness conditions addressed

At this point in the sequence, all 7 soundness conditions are closed by prior plans:

| Condition | Closed by plan | Stage |
|---|---|---|
| 1 — RequiredInfo ⊆ C_i | PLAN_MEMORY_CONTEXT | B.4 |
| 2 — Suff(C_i, R_i) | PLAN_CONTRACT_DISCIPLINE | E.1 |
| 3 — O_i derived from E_<i | PLAN_GATE_ENGINE + PLAN_MEMORY_CONTEXT | A.1 + B.1 + B.4 |
| 4 — A_i explicit, propagated | PLAN_CONTRACT_DISCIPLINE | F.3 |
| 5 — ∃ T_i deterministic | PLAN_GATE_ENGINE + PLAN_QUALITY_ASSURANCE | A.3 + D.5 |
| 6 — O_i only if G_i = pass | PLAN_GATE_ENGINE | A.4 |
| 7 — Missing → Stop | PLAN_CONTRACT_DISCIPLINE | F.4 |

This plan closes a different dimension: **the 7 conditions must hold at SYSTEM LEVEL across all stages, not just within a single execution.** CGAID compliance verifies this meta-claim.

**Meta-condition addressed by PLAN_GOVERNANCE:**

> The system as a whole — over time, across sessions, with real agents — satisfies the soundness theorem structurally, not just in unit tests.

This requires: data classification (Stage 0 compliance), metrics collection, rule lifecycle (so rules don't accumulate and degrade condition 5), Steward role (so condition 4 is governed, not just enforced by code), and deterministic snapshot validation.

---

## Theorem variable bindings

```
C_i = full platform state after all prior plans + FRAMEWORK_MAPPING.md §12 acknowledged gaps
R_i = CGAID compliance requirements (MANIFEST, OPERATING_MODEL, DATA_CLASSIFICATION)
A_i = FRAMEWORK_MAPPING.md §12 acknowledged gaps (each must be RESOLVED or formally accepted)
T_i = deterministic: endpoint HTTP checks, DB query counts, grep, pytest — no LLM-in-loop
O_i = {DataClassification gate, ContractViolation log, 7 metrics, Rule lifecycle, Steward role, 11 artifacts mapped, AdaptiveRigor, SnapshotValidator}
G_i = all T_i pass + Steward sign-off where required
```

---

## Stage G.1 — Stage 0 Data Classification Gate

**Closes:** CGAID Stage 0 compliance. Closes R-FW-02 escalation path.

**Entry conditions:**
- G_A = PASS, G_{F.4} = PASS (BLOCKED state exists — needed for kill-criteria trigger).

**A_{G.1}:**
- Existing data retroactive classification strategy — ADR-008 (pending). [UNKNOWN: what to do with pre-existing unclassified Knowledge rows? Must read ADR-008 when CLOSED]. Block G.1 start until ADR-008 CLOSED.
- DLP mechanism for Confidential+ tier — [UNKNOWN: not specified in FRAMEWORK_MAPPING.md]. Resolution: either (a) ADR-018 "DLP mechanism for Confidential+ tier — technology choice" (per ROADMAP §12) is authored and CLOSED before G.1 routing-matrix config work starts, OR (b) marked as `ACKNOWLEDGED_GAP` per FRAMEWORK_MAPPING §12 with Steward sign-off record on file. Q4 in the Q-table reflects this binary resolution. Stage G.1 is BLOCKED until one of the two resolution paths completes.

**Work:**
1. `DataClassification` entity migration.
2. Pre-ingest gate on `Knowledge`, `Decision.reasoning` with external quote — checks tier before persisting.
3. Routing matrix config per tier × capability.
4. UI banner for Confidential+ data without DLP record.
5. Steward sign-off gate for Confidential+ ingest.
6. Kill-criteria trigger: a `SecurityIncident` row with `tier ≥ Confidential` AND `confirmed_by_steward = true` AND `confirmed_at IS NOT NULL` → Execution BLOCKED system-wide (R-FW-02). Confirmation actor and evidence schema defined in ADR-008 (or a new ADR if ADR-008 is retroactive-data only — tracked in Q2).

**Exit test T_{G.1} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: pre-ingest gate
pytest tests/test_data_classification_gate.py -x
# PASS: ingest Confidential+ without DLP record → rejected

# T3: routing matrix configured
python -c "from app.governance.data_classification import routing_matrix; assert len(routing_matrix) > 0"
# exits 0

# T4: kill-criteria trigger
pytest tests/test_kill_criteria.py -x
# PASS: inject simulated leak → all new Executions BLOCKED

# T5: regression
pytest tests/ -x
```

**Gate G_{G.1}:** T1–T5 pass + ADR-008 CLOSED + Steward sign-off for first Confidential+ ingest → PASS.

---

## Stage G.2 — Contract Violation Log

**Closes:** CGAID Metric 4 (contract violations trackable).

**Entry conditions:**
- G_{F.5} = PASS (P22 disclosure validators at F.5 generate REJECTED deliveries that feed the log; F.6 verification independence runs *after* rejection, so F.6 is not the source). G_{F.3} = PASS (upstream assumption-tag validators — non-trivial untagged → REJECTED — are another population source).

**Work:**
1. `ContractViolation` table migration: `(id, execution_id, rule_id, violation_type, detected_at, disclosed)`.
2. Phase F validators auto-populate log on REJECTED delivery.
3. `GET /projects/{slug}/contract-violations` endpoint.

**Exit test T_{G.2} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: validator populates log
pytest tests/test_contract_violation_log.py -x
# PASS: synthetic rejected delivery → row in contract_violations table

# T3: endpoint returns data
pytest tests/test_contract_violation_endpoint.py -x

# T4: regression
pytest tests/ -x
```

**Gate G_{G.2}:** T1–T4 pass → PASS.

---

## Stage G.3 — 7 Metrics Collection Service

**Closes:** CGAID metrics compliance (OPERATING_MODEL §7.1 7 metrics).

**Entry conditions:**
- G_{G.2} = PASS (M4 depends on ContractViolation log).
- G_{B.4} = PASS (M1, M3 depend on causal memory).

**A_{G.3}:**
- 7 metric definitions — [CONFIRMED: FRAMEWORK_MAPPING.md §7 binds M1–M7 to Forge signals (lines 138–148)]. Verify OPERATING_MODEL §7.1 matches on implementation (drift check); discrepancy → file Finding.

**Work:**
1. `app/governance/metrics_service.py` — 7 collectors.
2. Scheduled runs (daily/weekly via cron or Celery).
3. `GET /projects/{slug}/metrics` endpoint.
4. Quarterly aggregate → Steward audit report.

**Exit test T_{G.3} (deterministic):**
```bash
# T1: all 7 collectors run without error
pytest tests/test_metrics_service.py -x
# PASS: each collector returns a numeric value (not None, not error)

# T2: endpoint returns all 7
pytest tests/test_metrics_endpoint.py -x
# PASS: response contains all 7 metric keys

# T3: first quarterly snapshot
python scripts/metrics_quarterly_snapshot.py
# exits 0; snapshot persisted

# T4: regression
pytest tests/ -x
```

**Gate G_{G.3}:** T1–T4 pass → PASS.

---

## Stage G.4 — Rule Lifecycle + Prevention Tracking

**Closes:** CGAID Rule Lifecycle (OM §4.3). Closes AUTONOMOUS_AGENT_FAILURE_MODES.md §5.7 (rule bloat).

**Entry conditions:**
- G_{E.2} = PASS (Invariant entity exists). Note: `Rule` and `Invariant` are distinct entities; this stage's `Rule` migration adds `Rule.invariant_id` FK (nullable) for rules derived from Invariants. MicroSkill/Guideline-derived rules have `invariant_id = NULL`. "Shared lifecycle" means shared retirement workflow (G.4 step 4), not shared schema.

**Work:**
1. `Rule` entity migration + auto-populate from `MicroSkill`, `Guideline`, validator rules.
2. `rule_prevention_log(rule_id, execution_id, rejection_timestamp)` — populated by VerdictEngine on every REJECTED delivery, logging which rule triggered the rejection.
3. `GET /projects/{slug}/rules/review` — retirement candidates = rules where `now() - rule.created_at >= 12 months` AND 0 entries in `rule_prevention_log` in the trailing 12-month window. Rules younger than 12 months are never candidates regardless of log emptiness (12-month grace period for new systems).
4. Retirement workflow: proposal → Steward review → archive.
5. Auto-proposal: new Finding with `severity ≥ HIGH` → propose adversarial fixture + rule candidate.

**Exit test T_{G.4} (deterministic):**
```bash
# T1: rule_prevention_log populated on rejection
pytest tests/test_rule_prevention_log.py -x
# PASS: synthetic REJECTED delivery → row in rule_prevention_log

# T2: retirement candidates query
pytest tests/test_rule_retirement_candidates.py -x
# PASS: rule with no prevention log entries in 12 months → appears in /rules/review

# T3: rules/review endpoint
pytest tests/test_rules_review_endpoint.py -x

# T4: regression
pytest tests/ -x
```

**Gate G_{G.4}:** T1–T4 pass → PASS.

---

## Stage G.5 — Framework Steward role

**Closes:** CGAID Steward role (OPERATING_MODEL §6). Requires ADR-007.

**Entry conditions:**
- ADR-007 CLOSED (Steward rotation for Forge project — who, how many, rotation period).

**A_{G.5}:**
- ADR-007 content — [UNKNOWN: not yet written. Block G.5 until CLOSED. This is the Steward dispute resolution gap from AUTONOMOUS_AGENT_FAILURE_MODES.md §1.2].

**Work:**
1. `User.steward_role` + rotation columns migration.
2. `AuditLog.reviewed_by_steward`, `Decision.steward_sign_off_by` for Critical tier.
3. Quarterly audit report generator.

**Exit test T_{G.5} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: Critical Decision without Steward → blocked
pytest tests/test_steward_gate.py -x

# T3: audit report generates
python scripts/steward_quarterly_report.py --dry-run
# exits 0

# T4: regression
pytest tests/ -x
```

**Gate G_{G.5}:** T1–T4 pass + ADR-007 CLOSED + first Steward identified → PASS.

---

## Stage G.6 — 11 Artifacts mapping

**Closes:** CGAID 11 artifacts (FRAMEWORK_MAPPING.md §6).

**Entry conditions:**
- G_{G.5} = PASS (Steward needed to sign off acknowledged gaps).

**A_{G.6}:**
- FRAMEWORK_MAPPING.md §6 lists 11 artifacts with current status — [ASSUMED: read §6 before implementing; some may be EXISTS already, some are ACKNOWLEDGED_GAP]. Each ACKNOWLEDGED_GAP needs Steward sign-off.

**Work:**
1. Verify each of 11 artifacts: either EXISTS with endpoint/view OR file `status=ACKNOWLEDGED_GAP` with Steward sign-off record.
2. Side-Effect Map (#11) linked to Phase C `SideEffectRegistry` output.
3. Business-Level DoD field added to `Objective`.

**Exit test T_{G.6} (deterministic):**
```bash
# T1: all 11 artifacts accounted for
python scripts/audit_11_artifacts.py
# exits 0; prints: EXISTS count + ACKNOWLEDGED_GAP count = 11
# any UNRESOLVED → exits 1

# T2: Side-Effect Map linked
pytest tests/test_side_effect_map_artifact.py -x

# T3: regression
pytest tests/ -x
```

**Gate G_{G.6}:** T1–T3 pass + all ACKNOWLEDGED_GAP entries have Steward sign-off records → PASS.

---

## Stage G.7 — Adaptive Rigor alignment

**Closes:** ADR-002 operational enforcement (CGAID ceremony tiers).

**Entry conditions:**
- ADR-002 CLOSED (already per decisions/).

**Work:**
1. `app/governance/adaptive_rigor.py` with `CEREMONY_TO_CGAID_TIER` mapping per ADR-002.
2. Per-tier artifact requirements (OM §7.1) encoded in `output_contracts` seed.
3. Fast Track preconditions validator (4 conditions OM §7.2).

**Exit test T_{G.7} (deterministic):**
```bash
pytest tests/test_adaptive_rigor.py -x
# T1: ceremony_level maps to correct CGAID tier per ADR-002
# T2: Fast Track with unmet precondition → blocked
# T3: per-tier artifact requirements enforced
```

**Gate G_{G.7}:** T_{G.7} pass → PASS.

---

## Stage G.8 — Deterministic Snapshot Validation

**Closes:** OPERATING_MODEL §9.4 5-component snapshot pattern (Baseline / Capture / Comparator / Failure Contract / Refresh). **Extends** PLAN_CONTRACT_DISCIPLINE E.10 P25 with the snapshot-style subcase per FORMAL §11.2 ("snapshot-style validation is a subcase" of P25). P25 main-case closure (TestSynthesizer auto-synthesizing property tests from ContractSchema + Invariants) is at E.10; G.8 applies the same pattern to runtime snapshot observations (Stage 1 volume / Stage 3 output shape / Stage 4 business outcome).

**Entry conditions:**
- G_{D.1} = PASS (snapshot pattern from deterministic harness).
- ADR-009 CLOSED (snapshot validation 5 components).

**A_{G.8}:**
- 5 components — [UNKNOWN: ADR-009 not yet written. Block G.8 until CLOSED].

**Work:**
1. `app/validation/snapshot_validator.py` with 5 components per ADR-009.
2. Applied to: Stage 1 volume check, Stage 3 output shape, Stage 4 business-outcome.
3. ≥ 3 gates use snapshot validation.

**Exit test T_{G.8} (deterministic):**
```bash
# T1: 3 gates use snapshot validation
grep -rn "snapshot_validator" app/validation/ | wc -l
# output ≥ 3

# T2: snapshot detects mutation
pytest tests/test_snapshot_validator.py -x
# PASS: mutated output fails snapshot check

# T3: regression
pytest tests/ -x
```

**Gate G_{G.8}:** T1–T3 pass → PASS.

---

## Stage G.9 — ProofTrailCompleteness + ECITP C6/C11 promotion

**Closes:** ECITP C12 (End-to-end proof trail — causal chain `documents → analysis → ambiguities → objectives → tasks → requirements → AC → tests → verification → artifact` with evidence preserved) + ECITP C7 (Continuity of meaning — small refinements cause bounded downstream revision). Also promotes B.6 relation_semantic and F.10 structured-transfer from WARN to REJECT mode system-wide. Source: `.ai/theorems/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` §3 C12 + C7.

**Rationale (ESC-3 root-cause uniqueness):** ECITP C12 requires that "for every final artifact Z, there must exist a causal chain with evidence references preserved across the chain." Three enforcement shapes considered:
1. Inline trail validation on every Change commit — **rejected**: expensive per-commit traversal; violates ESC-1 determinism under high concurrency (long lock on causal_edges). Also duplicates E.7 commit-chain overhead.
2. Periodic audit script + Finding-on-gap — **chosen**: deterministic batch; runs nightly + on-demand via CLI; emits Finding per missing link with severity=HIGH so B.6/F.10 REJECT-promotion gates these before they accumulate.
3. On-demand only (no scheduled run) — **rejected**: violates ECITP §7 Lemma 4 (broken continuity amplifies revision cost) — gaps accumulate undetected between manual runs.

**Entry conditions:**
- G_{G.8} = PASS (snapshot validation in place — needed for C7 bounded-revision test).
- G_{B.6} = PASS, G_{F.10} = PASS (WARN-mode mechanisms exist; G.9 promotes to REJECT).
- G_{E.7} = PASS (EpistemicProgressCheck available — G.9 audit references epistemic_delta to mark stages that degraded continuity).

**A_{G.9}:**
- Two entity gaps — [UNKNOWN: the 10-link chain requires `Requirement` as distinct entity from `Finding`, and `Test` as distinct entity from `AcceptanceCriterion`. These are not yet in the schema.]. Resolution paths:
  - **ADR-015 (proposed, per ROADMAP §12): Requirement entity** — either (a) promote `Finding.type = 'requirement'` to explicit `Requirement` table with FK from AC, OR (b) document `Finding.type='requirement'` as the canonical chain link with no new entity and adjust G.9 audit to accept both. G.9 is BLOCKED until ADR-015 CLOSED.
  - **ADR-016 (proposed, per ROADMAP §12): Test entity** — either (a) promote `AcceptanceCriterion.scenario_type` into a `Test` table with FK from AC, OR (b) treat AC+scenario_type as the chain's test link. G.9 is BLOCKED until ADR-016 CLOSED.
- Promotion semantic for B.6/F.10 WARN→REJECT — [CONFIRMED: promotion triggers a `feature_flags` row `CAUSAL_RELATION_SEMANTIC_REJECT=true` and `STRUCTURED_TRANSFER_REJECT=true`; prior plan validators read this flag at runtime per B.5/F.10 phased-rollout pattern].

**Work:**
1. `scripts/proof_trail_audit.py`:
   - For every `Change` in DB, traverses backward via `CausalEdge`:
     ```
     Change → Execution → AcceptanceCriterion → (Test per ADR-015) → Requirement per ADR-014 → Task → Objective → Finding → Knowledge
     ```
   - For each missing link, emits `Finding(severity=HIGH, kind='proof_trail_gap', change_id=..., missing_link='...')`.
   - Exit code: 0 if all Changes have complete chains, 1 if any gap.
2. CI integration: nightly cron runs audit; failure creates a P0 ticket.
3. CLI command: `forge audit proof-trail --change-id=<uuid>` for on-demand per-Change validation.
4. B.6/F.10 REJECT promotion: G.9 migration sets `feature_flags` rows enabling REJECT mode on AC-topology validator (B.6) and structured-transfer gate (F.10).
5. C7 bounded-revision test: `tests/test_c7_bounded_revision.py` — for 10 historical minor-edit PRs, assert `len(ImpactClosure) ≤ threshold` (threshold from ADR-004 `w_m` weights).
6. **Main-task satisfaction audit (AI-SDLC §16 + #18, closes AI-SDLC Tier-2 partial #18):**
   - Schema addition: `Task.is_main_task BOOLEAN DEFAULT false`; `decisions.satisfies_ac_id INT FK REFERENCES acceptance_criteria(id) NULL` + `changes.satisfies_ac_id INT FK NULL`.
   - Validator logic per main Task m with m.status=DONE:
     - `satisfied_acs = {AC.id | ∃ D ∈ descendant_decisions(m): D.satisfies_ac_id = AC.id OR ∃ C ∈ descendant_changes(m): C.satisfies_ac_id = AC.id}`
     - `required_acs = {AC.id | AC.task_id ∈ descendant_tasks(m) ∪ {m.id}}`
     - `missing = required_acs - satisfied_acs`
     - If `missing ≠ ∅` → emit `Finding(kind='main_task_incomplete', severity=HIGH, parent_task_id=m.id, missing_ac_ids=list(missing))` + `Objective.status='BLOCKED_MAIN_TASK_INCOMPLETE'`.
   - Runs as part of `scripts/proof_trail_audit.py` nightly pass.
   - Re-audit on Decision/Change insert with `satisfies_ac_id` populated (lazy un-block).

**Exit test T_{G.9} (deterministic):**
```bash
# T1: audit script runs on clean DB
python scripts/proof_trail_audit.py
# exits 0 (no gaps in seed fixtures) OR exits 1 with explicit Finding count

# T2: synthetic gap detection
pytest tests/test_proof_trail_audit.py::test_missing_link_detected -x
# PASS: Change with no linked Execution → Finding(kind='proof_trail_gap', missing_link='Execution')

# T3: complete 10-link chain on fixture
pytest tests/test_proof_trail_audit.py::test_complete_chain_passes -x

# T4: CLI per-change audit
forge audit proof-trail --change-id=$(psql -tc "SELECT id FROM changes LIMIT 1")
# exits 0 on complete, 1 on gap

# T5: B.6 REJECT-promotion active
psql -c "SELECT value FROM feature_flags WHERE name='CAUSAL_RELATION_SEMANTIC_REJECT'" | grep -q true
# exits 0

# T6: F.10 REJECT-promotion active
psql -c "SELECT value FROM feature_flags WHERE name='STRUCTURED_TRANSFER_REJECT'" | grep -q true
# exits 0

# T7: bounded revision (C7)
pytest tests/test_c7_bounded_revision.py -x
# PASS: 10 minor-edit PR fixtures → ImpactClosure size ≤ threshold from ADR-004

# T8: regression
pytest tests/ -x

# T9: main-task satisfaction check (AI-SDLC §16 + #18)
pytest tests/test_proof_trail_audit.py::test_main_task_subtask_satisfaction -x
# For every completed main Task m (m.is_main_task=true AND m.status=DONE):
#   let subtask_outcomes = union of Decisions + Changes across descendant Tasks
#   for every AC ∈ m.acceptance_criteria:
#     assert exists matching outcome O in subtask_outcomes with
#       O.satisfies_ac_id = AC.id (explicit satisfaction flag) OR
#       O.produced_artifact matches AC.scenario_type pattern
# FAIL: any AC of m without matching subtask outcome → Finding(
#   kind='main_task_incomplete', severity=HIGH, parent_task_id=m.id)
#   AND Objective.status='BLOCKED_MAIN_TASK_INCOMPLETE'
```

**Gate G_{G.9}:** T1–T9 pass + ADR-015 CLOSED + ADR-016 CLOSED → PASS. **ECITP C12 closed** structurally (per-Change chain auditable); **ECITP C7 closed** (bounded-revision test); **B.6/F.10 promoted from WARN to REJECTED**; **AI-SDLC §16+#18 closed** (main-task satisfaction mechanically verified — union of subtask outcomes must cover all AC of main task); **AIOS A9 closed transitively** — "t = ⋃ Subtasks(t)" set-equality is satisfied by T9 covering `⋃ Subtasks(t) ⊇ t` (satisfaction direction) combined with E.8 ScopeBoundaryDeclaration covering `⋃ Subtasks(t) ⊆ t` (scope-creep prevention direction); together these two stages enforce set equality required by AIOS Axiom 9.

**ESC-4 impact:** `scripts/proof_trail_audit.py` (new CLI + cron); `feature_flags` (+2 rows); AC-topology validator (WARN→REJECT — existing code, flag flip); StructuredTransferGate (WARN→REJECT — same); schema impact depends on ADR-014/015 outcome (either +2 tables or zero). **ESC-5 invariants preserved:** B.1 CausalEdge structure unchanged; B.6 ENUM values unchanged (promotion is enforcement change, not schema); F.10 raise-not-warn semantic unchanged at code level (flag only toggles active enforcement, never falls back to warn). **ESC-6 evidence completeness:** every Finding emitted by audit carries `source='proof_trail_audit'`, `trace_to_condition='ECITP_C12'`, `correctness_evidence=<traversal_query_text>`, `test_evidence='T_{G.9}_T2'`, `validation_evidence='CI_cron_run'`. **ESC-7 failure modes:** (a) missing Requirement entity → ADR-014 blocks gate entry; (b) false-positive gap due to orphan root Decision → B.1 `is_objective_root` exception honored; (c) concurrent audit+write race → audit runs against snapshot `SET TRANSACTION SNAPSHOT` to avoid partial-DAG reads.

---

## Stage G.10 — BaselinePostVerification (runtime diff enforcement)

**Closes:** FC §25 Baseline/Post/Diff verification (`Diff = ExpectedDiff ∧ UnexpectedDiff = empty`) + FC §26 Runtime Impact Verification per element (`∀ x ∈ Impact: ∃ runtime_check rc: Observes(rc, x)`). Source: Forge Complete theorem §25 + §26.

**Rationale (ESC-3 root-cause uniqueness):** four enforcement shapes considered for runtime change verification:
1. Trust post-change code review — **rejected**: violates FC §27 deterministic validation + ECITP §2.8 prior substitution (reviewer opinion ≠ runtime evidence).
2. Post-only snapshot (capture after change, compare to ExpectedDiff) — **rejected**: cannot detect baseline drift that preceded the change; false negatives on environment contamination.
3. Per-Execution (every Execution captures baseline+post) — **rejected**: pure-read executions have no diff; overhead waste.
4. Per-Change with state mutation (captures Baseline before applying Delta, Post after; Diff = ExpectedDiff enforced, auto-rollback on mismatch) — **chosen**: scoped to state-mutating Changes; matches C.4 Reversibility integration (rollback on FAIL).

**Entry conditions:**
- G_{C.3} = PASS (ImpactClosure provides the per-element reference set for §26).
- G_{C.4} = PASS (Reversibility classifier + Rollback service — required for auto-rollback on Diff mismatch).
- G_{G.8} = PASS (snapshot validation infrastructure from P25 — provides the observation primitive).
- ADR-021 CLOSED (ExpectedDiff schema per Change.type). Stage G.10 is BLOCKED until ADR-021 exists.

**A_{G.10}:**
- Observation primitives — [CONFIRMED: snapshot_validator from G.8 provides `capture_state(scope) → checksum + observed_values JSONB`; reuse not reinvent].
- ExpectedDiff schema — [UNKNOWN: ADR-021 per Change.type specifies shape; e.g. for `Change.type='migration'`: `{tables_created: [...], columns_added: [...], rows_affected: <int>}`; for `Change.type='code'`: `{files_added: [...], files_modified: [...], symbols_affected: [...]}`. Schema finalization is ADR-021 scope].
- Per-element runtime check — [CONFIRMED: every element in ImpactClosure gets one row in `runtime_observations` per phase; missing observation for any element → REJECTED].

**Work:**
1. Alembic migration: `runtime_observations(id, change_id FK, phase ENUM{'baseline','post'}, impact_element_ref TEXT, check_type ENUM, check_ref TEXT, observed_value JSONB, observed_at TIMESTAMP, sha256 TEXT)`. Unique on `(change_id, phase, impact_element_ref)`.
2. `app/validation/baseline_post_verifier.py`:
   - `capture_baseline(change) → None` — for each `x ∈ ImpactClosure(change)`, call `snapshot_validator.capture_state(x)` and insert `runtime_observations(phase='baseline')` row.
   - `capture_post(change) → None` — same for phase='post' after Delta applied.
   - `diff(change) → DiffResult` — compare baseline vs post per element; returns `{matches_expected: bool, unexpected_changes: [...], unexpected_identities: [...]}`.
   - `BaselinePostCheck.evaluate(change) → Verdict` — PASS iff:
     - Every `x ∈ ImpactClosure(change)` has `runtime_observations` row with `phase='baseline'` AND one with `phase='post'`.
     - `diff(change).unexpected_changes = ∅` (everything that changed was in ExpectedDiff).
     - `diff(change).unexpected_identities = ∅` (everything that should have changed did — ExpectedDiff ⊆ actual Diff).
3. VerdictEngine integration:
   - Pre-apply hook: `capture_baseline(change)` runs; if any element unreachable → REJECTED with reason=`baseline_capture_failed: <element>`.
   - Apply: Delta executed.
   - Post-apply hook: `capture_post(change)` runs; `BaselinePostCheck.evaluate(change)` runs; if REJECTED → auto-invoke `rollback_service.attempt(change)` (per C.4) + mark Change.status=`diff_mismatch_rolled_back`.
4. ExpectedDiff declaration: `Change.expected_diff JSONB NOT NULL` per ADR-021 schema. Change insert without ExpectedDiff → REJECTED at insert.

**Exit test T_{G.10} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: Change without ExpectedDiff declared → REJECTED at insert
pytest tests/test_baseline_post.py::test_missing_expected_diff_rejected -x
# PASS: INSERT INTO changes without expected_diff → IntegrityError / Verdict REJECTED

# T3: Change with Baseline capture failure → REJECTED
pytest tests/test_baseline_post.py::test_baseline_capture_failure -x
# PASS: ImpactClosure includes unreachable element (e.g. deleted table) → REJECTED
# with reason='baseline_capture_failed: <element_ref>'

# T4: Change with Diff = ExpectedDiff → PASS
pytest tests/test_baseline_post.py::test_matching_diff_passes -x
# PASS: Baseline and Post captured for every ImpactClosure element; observed diff
# equals expected_diff; zero unexpected_changes AND zero unexpected_identities

# T5: Change with Diff ≠ ExpectedDiff → REJECTED + auto-rollback triggered
pytest tests/test_baseline_post.py::test_unexpected_diff_rollback -x
# PASS: synthetic Change where actual diff includes extra table creation not in
# expected_diff → REJECTED, Change.status='diff_mismatch_rolled_back',
# rollback_service.attempt invoked, state restored to Baseline checksum

# T6: per-element coverage — missing runtime_observation for any ImpactClosure element → REJECTED
pytest tests/test_baseline_post.py::test_missing_element_observation_rejected -x
# PASS: ImpactClosure = {a, b, c}; runtime_observations only for {a, b} → REJECTED
# with reason='missing_runtime_check: c'

# T7: integration with C.4 Reversibility on REVERSIBLE Change
pytest tests/test_baseline_post.py::test_c4_integration_reversible -x
# PASS: REVERSIBLE Change with diff mismatch → rollback succeeds + Post' checksum
# matches Baseline checksum exactly (byte-identical state restore)

# T8: integration with C.4 on IRREVERSIBLE Change → explicit incident, no silent drop
pytest tests/test_baseline_post.py::test_c4_integration_irreversible -x
# PASS: IRREVERSIBLE Change with diff mismatch → Change.status='diff_mismatch_irreversible';
# Incident filed with severity=CRITICAL; no automatic rollback attempt (by design)

# T9: regression
pytest tests/ -x
```

**Gate G_{G.10}:** T1–T9 pass + ADR-021 CLOSED → PASS. **FC §25 + §26 closed** structurally: every state-mutating Change captures Baseline before + Post after for every ImpactClosure element; observed Diff must equal declared ExpectedDiff; mismatch triggers auto-rollback (REVERSIBLE) or CRITICAL incident (IRREVERSIBLE); silent drift mechanically impossible.

**ESC-4 impact:** `runtime_observations` table (new); Change schema (+`expected_diff JSONB NOT NULL`); VerdictEngine pre/post-apply hooks (+2); integrates with G.8 snapshot_validator (consumer-side reuse) + C.4 rollback_service (consumer-side reuse); ADR-021 (new). **ESC-5 invariants preserved:** C.4 Reversibility classification semantics unchanged; G.8 snapshot_validator interface additive; E.2 Invariant.check_fn still runs at commit (orthogonal to Diff verification — invariants check state validity, BaselinePost checks change correctness). **ESC-7 failure modes:** (a) ImpactClosure false-positive causes baseline capture of irrelevant state → captured but never in Diff (no impact); (b) concurrent change during observation window → Change.status='concurrent_mutation_detected' + REJECTED (new Change.lock mechanism required, or retry at lower-level); (c) IRREVERSIBLE Change with unexpected diff → no silent rollback (by design per C.4); CRITICAL incident triggers Steward sign-off for recovery; (d) ExpectedDiff schema evolution → ADR-021 versioning; old Changes retain old schema via `expected_diff_schema_version` field.

---

## Stage G.11 — ErrorPropagationMechanism (AIOS A18 + AI-SDLC §19+#20)

**Closes:** AIOS Axiom 18 (Err(x) → Err(Dep(x))) + AI-SDLC §19 (invalidation of dependent artifacts) + Forge Complete §14 (Impact closure completeness). Source: ADR-024 Error propagation mechanism.

**Rationale (ESC-3 root-cause uniqueness):** see ADR-024 §Alternatives. Two-mechanism approach (Finding inheritance + Execution invalidation) chosen — preserves audit trail + blocks new work until resolved.

**Entry conditions:**
- G_{C.3} = PASS (ImpactClosure provides descendant closure).
- G_{B.2} = PASS (causal_edges with relation_semantic).
- G_{F.4} = PASS (BLOCKED state pattern extended with BLOCKED_UPSTREAM_FAILURE).
- ADR-024 CLOSED.

**A_{G.11}:**
- `max_depth=5` cascade limit — [ASSUMED: typical Forge Objective DAGs < 50 nodes deep; cap prevents runaway in pathological case]. Calibration per ADR-004 supersession.
- Propagation kinds (`direct_dependency`, `data_flow`, `shared_state`, `test_coverage_gap`) — [CONFIRMED: ADR-024 enumeration].

**Work:**
1. Alembic migrations: `findings.parent_finding_id`, `propagation_depth`, `propagates_to_task_ids`, `inheritance_kind`; `executions.invalidated_by_finding_id` + companions; `Task.status` enum adds `BLOCKED_UPSTREAM_FAILURE`.
2. Hook `propagate_finding_on_rejection` in VerdictEngine REJECTED path for Execution with severity ≥ HIGH Finding.
3. GateRegistry entry: `(Execution, IN_PROGRESS, COMMITTED)` chain — `ErrorPropagationCheck` gate blocks commit if any upstream Task has unresolved HIGH Finding.
4. Resolution path: `Decision(type='finding_resolution')` + Evidence → cascade un-invalidation; `resolved_by_cascade_resolution_id` populated on all inherited Findings.
5. G.3 metrics: `M_propagation_blast_radius` = avg number of affected Tasks per HIGH Finding; `M_unresolved_cascade_count` = count of open cascades > 14 days.
6. Dashboard: `GET /findings/{id}/cascade-view` visualizes propagation tree.

**Exit test T_{G.11} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: cascade on synthetic upstream failure
pytest tests/test_error_propagation.py::test_cascade_on_upstream_rejected -x
# synthetic: Task A has 3 descendants {B, C, D}. A Execution REJECTED with
# HIGH Finding → B, C, D get inherited Findings + status=BLOCKED_UPSTREAM_FAILURE

# T3: cascade depth cap respected
pytest tests/test_error_propagation.py::test_max_depth_5 -x
# synthetic: chain A→B→C→D→E→F→G (depth 6). REJECTED at A → cascade reaches E;
# F and G NOT auto-flagged; Steward manual extension required

# T4: ErrorPropagationCheck gate blocks new Execution commit
pytest tests/test_error_propagation.py::test_gate_blocks_on_upstream_unresolved -x
# Execution for Task C (whose ancestor A has unresolved Finding) → REJECTED

# T5: resolution cascades un-invalidation
pytest tests/test_error_propagation.py::test_resolution_cascades -x
# Decision(type='finding_resolution', resolves_finding_id=A.finding_id) →
# all inherited Findings get resolved_by_cascade_resolution_id;
# affected Tasks transition back to READY

# T6: challenged propagation (contest-propagation endpoint)
pytest tests/test_error_propagation.py::test_contest_propagation -x
# Task_y author POST /findings/{id}/contest-propagation → Steward review
# queue entry created; propagation persists until Steward decision

# T7: regression
pytest tests/ -x
```

**Gate G_{G.11}:** T1–T7 pass + ADR-024 CLOSED → PASS. **AIOS A18 closed** + **AI-SDLC §19 + #20 closed** + **FC §14 error-propagation aspect closed**.

**ESC-4 impact:** `findings` schema (+5 columns), `executions` schema (+3 columns), `Task.status` enum extension, VerdictEngine REJECTED-path hook, GateRegistry chain extension, G.3 metrics (+2), dashboard endpoint. **ESC-5 invariants preserved:** F.4 BLOCKED semantics unchanged (BLOCKED_UPSTREAM_FAILURE is new sibling status); G.9 proof-trail audit extended but doesn't change traversal logic; existing Finding.severity enum unchanged. **ESC-7 failure modes:** (a) false propagation (over-broad) → contest-propagation endpoint for Task authors; (b) cascade depth cap at 5 leaves deeper dependents unflagged → Steward manual extension with signed record; (c) performance on large cascades → `max_depth=5` + indexed FK; benchmark pending.

---

## Phase G exit gate (G_GOV) — Terminal gate

**Total mechanical conditions enforced at G_GOV:** 7 CCEGAP conditions + 6 ECITP conditions (C3, C6, C7, C8, C11, C12) + 3 ECITP continuity definitions (§2.3, §2.4, §2.7) + 5 FC critical gaps (§8, §15, §16-§19, §25+§26, §37) + 2 Tier-1 cross-theorem gaps (AIOS A18 + AI-SDLC §19/#20 at G.11; AIOS A8 + AI-SDLC #10 at D.6 — counted in earlier plans) = **21 mechanical checks** in the validation table below. The "23 total" in the prior version inadvertently double-counted the Tier-1 gaps that are already closed in upstream plans (D.6 at PLAN_QUALITY_ASSURANCE; G.11 below). Reconciled count = **21**.

```
G_GOV = PASS iff:
  G_{G.1} through G_{G.11} all PASS  (incl. G.9 ProofTrailCompleteness + ECITP C6/C11 REJECT-promotion + G.10 BaselinePostVerification + G.11 ErrorPropagationMechanism)
  AND pytest tests/ -x → all 6 prior plans' tests + Governance tests green
  AND FRAMEWORK_MAPPING.md §12: every acknowledged gap is RESOLVED or has Steward-signed ACKNOWLEDGED_GAP record
  AND 7 metrics live: GET /projects/{slug}/metrics returns all 7 non-null
  AND Rule review report produced: ≥ 1 retirement candidate identified
  AND every HIGH/CRITICAL Decision has Steward sign-off (DB query: count = 0 violations)
  AND rule_prevention_log mechanism verified: T_{G.4} T1 generalized to all rule classes — for each rule class a synthetic REJECTED delivery produces a log row. (Production log may be empty on day 1; this gate tests the pipeline, not accumulated production data.)
  AND proof_trail_audit.py exits 0: every Change has complete 10-link causal chain (G.9)
  AND feature_flags CAUSAL_RELATION_SEMANTIC_REJECT=true (G.9 promotes B.6)
  AND feature_flags STRUCTURED_TRANSFER_REJECT=true (G.9 promotes F.10)
  AND every state-mutating Change has Baseline + Post runtime observations for every ImpactClosure element AND Diff = ExpectedDiff (G.10)
```

**Final soundness validation table — 21 mechanical checks (7 CCEGAP + 6 ECITP conditions + 3 ECITP continuity definitions + 5 FC critical gaps):**

| # | Theorem / Condition | Mechanism at G_GOV | Evidence |
|---|---|---|---|
| 1 | CCEGAP — RequiredInfo ⊆ C_i | ContextProjector active (B.4); fidelity tested on 10 historical | T_{B.4} T2 in CI |
| 2 | CCEGAP — Suff(C_i, R_i) | ContractSchema drift test in CI | T_{E.1} T1, T2 |
| 3 | CCEGAP — O_i derived from E_<i | CausalEdge insert gate + ImpactClosure gate in VerdictEngine | T_{B.1} T4, T_{C.3} T2 |
| 4 | CCEGAP — A_i explicit, propagated | CONFIRMED/ASSUMED/UNKNOWN enforced as REJECT | T_{F.3} T1 |
| 5 | CCEGAP — ∃ T_i deterministic | CI α-gate + mutation smoke in CI | T_{D.5} T3, T4 |
| 6 | CCEGAP — O_i only if G_i = pass | grep invariant: 0 direct .status= in CI | T_{A.4} T1 |
| 7 | CCEGAP — Missing → Stop | BLOCKED state + no auto-fill path | T_{F.4} T2, T3 |
| 8 | ECITP C3 — Timely delivery | TimelyDeliveryGate at pending→IN_PROGRESS transition; no F_i without materialized P_i | T_{B.5} T2, T3 |
| 9 | ECITP C6 — Topology preservation | relation_semantic ENUM + CausalGraph relation-typed queries; REJECT-promoted at G.9 | T_{B.6} T4, T5 + G.9 feature_flag |
| 10 | ECITP C7 — Continuity of meaning | Bounded-revision test on 10 minor-edit PRs ≤ threshold | T_{G.9} T7 |
| 11 | ECITP C8 — Additive progression | EpistemicProgressCheck rejects null stages (6 deltas) | T_{E.7} T2, T5 |
| 12 | ECITP C11 — Structured transfer | StructuredTransferGate: NL-only projection → BLOCKED; grep-gate on fallback paths | T_{F.10} T1, T4 |
| 13 | ECITP C12 — End-to-end proof trail | proof_trail_audit.py: every Change has complete 10-link chain | T_{G.9} T1, T3 |
| 14 | ECITP §2.3 — Evidence continuity | Property test: 10,000 random DAG+task pairs; every decision-relevant ancestor edge in projection | T_{B.4} T2b |
| 15 | ECITP §2.4 — Ambiguity continuity | Property test: 10,000 random execution chains; UNKNOWN persists until `resolved_uncertainty` record exists | T_{F.4} T5 |
| 16 | ECITP §2.7 — Explicit invalidation | Silent prior-K drop → REJECTED; explicit `invalidated_evidence_refs` with reason_code → PASS | T_{E.7} T7 |
| 17 | FC §8 — Source Consistency | SourceConflictDetector: literal-value mismatches on `(entity_ref, field_name)` → `source_conflicts` row + Finding; unresolved in task ancestor closure → BLOCKED | T_{B.7} T2, T4 |
| 18 | FC §15 — Change Set Completeness | `Execution.in_scope_refs ∪ out_of_scope_refs ⊇ ImpactClosure`; unjustified elements → REJECTED | T_{E.8} T2, T3 |
| 19 | FC §16+§17+§18+§19 — Candidate Solution Evaluation | architectural Decisions: ≥2 candidates, 14-dim Score, argmax selection, Necessary(c) evidence | T_{F.11} T2-T5, T8 |
| 20 | FC §37 — No unaccepted Technical Debt | Debt markers in Change.diff require `technical_debt` row with authorized `accepted_by` | T_{F.12} T2, T3 |
| 21 | FC §25+§26 — Baseline/Post/Diff + per-element runtime verification | Every state-mutating Change: Baseline + Post observations per ImpactClosure element; Diff = ExpectedDiff; mismatch → auto-rollback | T_{G.10} T4, T5, T6 |

When G_GOV = PASS, the platform satisfies the seven soundness conditions **structurally at the per-execution level** via enforced mechanical constraints (not by convention, not by LLM discipline). **System-level soundness** (across sessions, under concurrency, with novel task types not seen during development) is **NOT** established by G_GOV and requires separate post-G_GOV work: soak tests, multi-agent concurrency tests, fidelity-at-scale tests, and empirical coverage of the RequiredInfo projection beyond the 10 historical fixtures in T_{B.4} T2. See AUTONOMOUS_AGENT_FAILURE_MODES.md §2.2, §2.4.

---

## Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | G.1 pre-ingest gate rejects Confidential+ without DLP record; G.2 `ContractViolation.violation_type` NOT NULL; G.3 metrics collectors T1 asserts every collector returns numeric (not None, not error); G.9 `proof_trail_audit.py` emits Finding on any missing link in 10-link chain. |
| 2 | timeout_or_dependency_failure | Handled | G.3 scheduled metrics job has retry-on-failure semantics (cron + exponential backoff); G.9 `proof_trail_audit.py` uses `SET TRANSACTION SNAPSHOT` to avoid partial-DAG reads under concurrent writes; G.4 `rule_prevention_log` writes synchronous during REJECT flow (not fire-and-forget). |
| 3 | repeated_execution | Handled | G.1 DataClassification insert idempotent (same source+tier → upsert no-op); G.2 `ContractViolation` unique on `(execution_id, rule_id)`; G.9 audit re-runnable (deterministic BFS traversal; same DAG state → same Findings). |
| 4 | missing_permissions | Handled | G.5 Steward sign-off required for Critical tier (`AuditLog.reviewed_by_steward` and `Decision.steward_sign_off_by` NOT NULL at tier=Critical); G.1 Confidential+ ingest requires Steward sign-off pre-write; G.6 ACKNOWLEDGED_GAP entries require Steward sign-off record on file. |
| 5 | migration_or_old_data_shape | Handled | Every G-stage with schema change has alembic round-trip (G.1 T1, G.2 T1, G.5 T1). G.1 ADR-008 (pending) specifies retroactive Stage 0 strategy for pre-existing unclassified Knowledge rows; G.6 11 artifacts accounting accepts EXISTS + ACKNOWLEDGED_GAP + Steward sign-off for legacy state. |
| 6 | frontend_not_updated | Handled | G.6 `11 Artifacts mapping` explicitly includes UI-surfaced artifacts (endpoint/view per each of 11); Artifact #11 Side-Effect Map linked to C.3 `SideEffectRegistry` output with admin UI binding; G.1 adds UI banner for Confidential+ data without DLP record. Frontend updates tracked as part of each artifact status check. |
| 7 | rollback_or_restore | Handled | G.9 feature flags `CAUSAL_RELATION_SEMANTIC_REJECT` and `STRUCTURED_TRANSFER_REJECT` reversible (WARN←REJECT via flag flip); G.4 rule retirement uses proposal→Steward review→archive workflow (not destructive delete — archived rules recoverable). All G-stage migrations have `down_revision`. |
| 8 | monday_morning_user_state | Handled | G.1 kill-criteria trigger is durable (`SecurityIncident.confirmed_at IS NOT NULL` persists across restarts); system-wide BLOCKED state survives process restart. G.3 metrics aggregator uses persistent `metrics_snapshots` table, not in-memory; Monday/Friday same baseline. G.5 Steward sign-off records are DB rows not session-bound. |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Governance operates on platform-level compliance (CGAID Stage 0, Steward role, 7 metrics, Rule lifecycle, 11 artifacts, snapshot validation, proof trail). No geographic or regional data dimension. |

---

## Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks (hard — stage cannot start until resolved per CONTRACT §B.2) |
|---|---|---|
| Q1 | ADR-007 Steward rotation — who, how many, rotation period? ADR must exist with `Status: CLOSED` before G.5 start. | Stage G.5 (BLOCKING) |
| Q2 | ADR-008 Retroactive Stage 0 strategy for pre-existing data AND SecurityIncident confirmation schema (kill-criteria §G.1 step 6). ADR must exist with `Status: CLOSED` before G.1 start. | Stage G.1 (BLOCKING) |
| Q3 | ADR-009 Snapshot Validation 5 components — must align with FORMAL_PROPERTIES_v2 §11.2 synth(s, i) pattern. ADR file must exist with `Status: CLOSED` before G.8 start. | Stage G.8 (BLOCKING) |
| Q4 | DLP mechanism for Confidential+ tier — either (a) ADR-018 (per ROADMAP §12) authored + CLOSED with technology choice, OR (b) marked `ACKNOWLEDGED_GAP` per FRAMEWORK_MAPPING §12 with Steward sign-off record on file. | Stage G.1 (BLOCKING — one of two paths) |
| Q5 | OPERATING_MODEL §7.1 seven metrics: cross-check that FRAMEWORK_MAPPING.md §7 bindings match §7.1 definitions before G.3 collectors implemented. | Stage G.3 (drift check — informational if bindings match; BLOCKING if discrepancy → file Finding and escalate to Steward) |
| Q6 | ADR-015 Requirement entity — either (a) promote `Finding.type='requirement'` to distinct `Requirement` table, OR (b) accept Finding-as-Requirement in proof-trail audit. ADR file must exist with `Status: CLOSED` before G.9 start. | Stage G.9 (BLOCKING — ECITP C12) |
| Q7 | ADR-016 Test entity — either (a) promote `AcceptanceCriterion.scenario_type` to distinct `Test` table, OR (b) accept AC+scenario_type as the chain's test link. ADR file must exist with `Status: CLOSED` before G.9 start. | Stage G.9 (BLOCKING — ECITP C12) |
| Q8 | ADR-021 ExpectedDiff schema per Change.type — shape of `Change.expected_diff` JSONB for migrations, code changes, config changes. ADR file must exist with `Status: CLOSED` before G.10 start. | Stage G.10 (BLOCKING — FC §25+§26) |

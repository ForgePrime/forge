# PLAN: Governance — CGAID Compliance Capstone

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** PLAN_CONTRACT_DISCIPLINE complete (G_CD = PASS). All five prior plans complete.
**Must complete before:** nothing — this is the terminal plan.

> **Known unverified claim (CONTRACT §A.6 disclosure):** this plan's "terminal gate" label implies *system-level* soundness, but every cited exit test is unit-level (pytest, single-endpoint HTTP, small-sample fixtures). System-level soundness (concurrency, multi-agent sessions, novel task types not seen during development) is **out of scope** of G_GOV and must be verified by post-G_GOV soak / integration / multi-session tests tracked separately. G_GOV establishes per-execution structural enforcement; it does not establish empirical coverage at scale. See AUTONOMOUS_AGENT_FAILURE_MODES.md §2.2, §2.4.

**ROADMAP phases:** G.1 → G.8.
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

**Closes (conditional):** P25 iff ADR-009's 5 components align with FORMAL_PROPERTIES_v2 §11.2 `synth(s, i)` pattern. If ADR-009 diverges from §11.2, P25 remains open and a new ADR supersession is required before G.8 can claim closure.

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
```

**Gate G_{G.9}:** T1–T8 pass + ADR-015 CLOSED + ADR-016 CLOSED → PASS. **ECITP C12 closed** structurally (per-Change chain auditable); **ECITP C7 closed** (bounded-revision test); **B.6/F.10 promoted from WARN to REJECT**.

**ESC-4 impact:** `scripts/proof_trail_audit.py` (new CLI + cron); `feature_flags` (+2 rows); AC-topology validator (WARN→REJECT — existing code, flag flip); StructuredTransferGate (WARN→REJECT — same); schema impact depends on ADR-014/015 outcome (either +2 tables or zero). **ESC-5 invariants preserved:** B.1 CausalEdge structure unchanged; B.6 ENUM values unchanged (promotion is enforcement change, not schema); F.10 raise-not-warn semantic unchanged at code level (flag only toggles active enforcement, never falls back to warn). **ESC-6 evidence completeness:** every Finding emitted by audit carries `source='proof_trail_audit'`, `trace_to_condition='ECITP_C12'`, `correctness_evidence=<traversal_query_text>`, `test_evidence='T_{G.9}_T2'`, `validation_evidence='CI_cron_run'`. **ESC-7 failure modes:** (a) missing Requirement entity → ADR-014 blocks gate entry; (b) false-positive gap due to orphan root Decision → B.1 `is_objective_root` exception honored; (c) concurrent audit+write race → audit runs against snapshot `SET TRANSACTION SNAPSHOT` to avoid partial-DAG reads.

---

## Phase G exit gate (G_GOV) — Terminal gate for 7 CCEGAP + 6 ECITP soundness conditions

```
G_GOV = PASS iff:
  G_{G.1} through G_{G.9} all PASS  (incl. G.9 ProofTrailCompleteness + ECITP C6/C11 REJECT-promotion)
  AND pytest tests/ -x → all 6 prior plans' tests + Governance tests green
  AND FRAMEWORK_MAPPING.md §12: every acknowledged gap is RESOLVED or has Steward-signed ACKNOWLEDGED_GAP record
  AND 7 metrics live: GET /projects/{slug}/metrics returns all 7 non-null
  AND Rule review report produced: ≥ 1 retirement candidate identified
  AND every HIGH/CRITICAL Decision has Steward sign-off (DB query: count = 0 violations)
  AND rule_prevention_log mechanism verified: T_{G.4} T1 generalized to all rule classes — for each rule class a synthetic REJECTED delivery produces a log row. (Production log may be empty on day 1; this gate tests the pipeline, not accumulated production data.)
  AND proof_trail_audit.py exits 0: every Change has complete 10-link causal chain (G.9)
  AND feature_flags CAUSAL_RELATION_SEMANTIC_REJECT=true (G.9 promotes B.6)
  AND feature_flags STRUCTURED_TRANSFER_REJECT=true (G.9 promotes F.10)
```

**Final soundness validation — CCEGAP 7 conditions + ECITP 6 additional conditions:**

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

When G_GOV = PASS, the platform satisfies the seven soundness conditions **structurally at the per-execution level** via enforced mechanical constraints (not by convention, not by LLM discipline). **System-level soundness** (across sessions, under concurrency, with novel task types not seen during development) is **NOT** established by G_GOV and requires separate post-G_GOV work: soak tests, multi-agent concurrency tests, fidelity-at-scale tests, and empirical coverage of the RequiredInfo projection beyond the 10 historical fixtures in T_{B.4} T2. See AUTONOMOUS_AGENT_FAILURE_MODES.md §2.2, §2.4.

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

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

| Theorem condition | What "addressed" means | Closed in |
|---|---|---|
| **2** — Suff(C_i, R_i, i) = true | ContractSchema derives both prompt constraints and validator rules from one source; sufficiency check is structural, not LLM-evaluated | Stage E.1 exit |
| **4** — A_i explicit and propagated until resolved | Assumption tags (CONFIRMED/ASSUMED/UNKNOWN) become REJECT conditions — not warnings; ambiguities tracked in `Execution.uncertainty_state` | Stage F.3 + F.4 exit |
| **7** — Missing(C_i) → Stop or Escalate, not Guess | BLOCKED state on Execution; UNKNOWN items halt pipeline until resolved by human ACK via `POST /resolve-uncertainty` | Stage F.4 exit |

Conditions 1, 3, 5, 6 are closed by PLAN_MEMORY_CONTEXT and PLAN_GATE_ENGINE.

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
```
**Gate G_{F.4}:** T1–T4 pass → PASS. **Condition 7 closed**: Missing(C_i) → Stop — enforced structurally.

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

## Phase E+F exit gate (G_CD)

```
G_CD = PASS iff:
  G_{E.1} through G_{E.6} all PASS  (self-adjoint contract, invariants, autonomy, reachability, modes, diagonalization)
  AND G_{F.1} through G_{F.9} all PASS  (evidence discipline, uncertainty blocking, root cause, disclosure, independence, SR-1/2/3)
  AND pytest tests/ -x → all prior phase + Contract Discipline tests green
  AND Suff(C_i, R_i) = true: ContractSchema drift test green (E.1)
  AND A_i enforced: non-trivial untagged → REJECTED (F.3)
  AND Missing(C_i) → BLOCKED: UNKNOWN items halt execution (F.4)
```

**Soundness conditions closed at G_CD:**
- **Condition 2** — Suff(C_i, R_i): ContractSchema derives prompt + validator from one source; structural sufficiency. [T_{E.1} T1, T2]
- **Condition 4** — A_i explicit + propagated: assumption tags enforced as REJECT, not warning. [T_{F.3} T1]
- **Condition 7** — Missing(C_i) → Stop OR Escalate: BLOCKED state enforced (Stop) + `POST /resolve-uncertainty` requires explicit `[ASSUMED: accepted-by=<role>]` (Escalate); no auto-fill, no default resolution. [T_{F.4} T2, T3, T4]

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

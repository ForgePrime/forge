# PLAN: Quality Assurance — Impact Closure, Reversibility, Failure-Oriented Testing

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** PLAN_GATE_ENGINE complete (G_A = PASS). PLAN_MEMORY_CONTEXT (B.2 CausalEdge) needed for C.3 closure walk, but C.1–C.2 can start from G_A.
**Must complete before:** PLAN_CONTRACT_DISCIPLINE (E stages need ImpactClosure, ContractSchema, Invariants).
**ROADMAP phases:** C.1 → C.4, D.1 → D.5.
**Source spec:** FORMAL_PROPERTIES_v2.md P2, P3, P5, P10, P18, P25.
**Soundness theorem source:** `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md`.

---

## Soundness conditions addressed

| Theorem condition / Forge property | What "addressed" means | Closed in |
|---|---|---|
| **Theorem condition 5** (strengthened) — ∃ T_i deterministic | Property-based, metamorphic, adversarial test suite establishes the falsification infrastructure; CI gate blocks merge below α | Stage D.5 exit |
| **FORMAL P3** (Impact Closure) — NOT theorem condition 3 | ImpactClosure provides a deterministic rejection gate for under-declared `modifying` lists. Closes Forge-internal property P3 (structural change closure) **within documented static-dispatch scope only** — dynamic dispatch and untagged side-effect functions remain explicit gaps (see A_{C.1}, A_{C.2}). **This is NOT theorem condition 3** (epistemic provenance of O_i from E_<i, which is closed by PLAN_MEMORY_CONTEXT B.4 + PLAN_CONTRACT_DISCIPLINE F.1/F.2 on evidence source + verifiability). | Stage C.3 exit |

Conditions 1, 2, 3, 4, 6, 7 of the soundness theorem are addressed in PLAN_PRE_FLIGHT, PLAN_GATE_ENGINE, PLAN_MEMORY_CONTEXT, and PLAN_CONTRACT_DISCIPLINE.

This plan strengthens theorem condition 5 from "VerdictEngine is deterministic" (Gate Engine) to "the full test suite maximises falsification probability across risk-weighted failure modes." It does **not** strengthen condition 3 — that conflation with P3 was corrected after deep-verify found it violated the theorem's definition of condition 3.

---

## Theorem variable bindings

```
C_i = codebase after previous stage
R_i = FORMAL_PROPERTIES_v2 P2, P3, P5, P10, P18, P25
A_i = listed per stage
T_i = pytest / hypothesis / grep / disaster drill — no LLM-in-loop
O_i = {ImportGraph, SideEffectRegistry, ImpactClosure, Reversibility, test suites, FailureMode entity, coverage CI gate}
G_i = all T_i pass + regression green + distinct-actor review where noted
```

---

## Phase C — Impact Closure + Reversibility

### Stage C.1 — ImportGraph service

**Closes:** P3 prerequisite — static dependency closure.

**Entry conditions:**
- G_A = PASS.

**A_{C.1}:**
- Static AST walk scope: `app/` Python files only — [CONFIRMED: per CHANGE_PLAN_v2 §5.1]. Dynamic dispatch (`getattr`, runtime imports) is NOT covered — [CONFIRMED gap per AUTONOMOUS_AGENT_FAILURE_MODES.md §6 §4]. Document exclusion explicitly in service docstring.
- Cache invalidation trigger: file watcher vs PR-gate — [ASSUMED: PR-gate (CI check) simpler than file watcher daemon; document choice].

**Work:**
1. `app/validation/import_graph.py`:
   - Static AST walk of `app/` producing reverse-dep graph.
   - `reverse_deps(module) → Set[module]` — transitive closure.
   - Cache in memory; invalidated on any `app/*.py` change (CI check re-runs).
2. Known exclusion: dynamic dispatch (`getattr`), cross-service, cross-repo — documented in module docstring as explicit scope boundary.

**Exit test T_{C.1} (deterministic):**
```bash
# T1: closure correctness on fixture
pytest tests/test_import_graph.py::test_transitive_closure -x
# Fixture: f() called by g(), g() called by k(); reverse_deps(f) = {g, k}

# T2: no dynamic dispatch false-positive
pytest tests/test_import_graph.py::test_no_getattr_false_positive -x
# PASS: module with only getattr-based imports returns empty reverse_deps

# T3: regression
pytest tests/ -x
```

**Gate G_{C.1}:** T1–T3 pass → PASS.

---

### Stage C.2 — SideEffectRegistry + `@side_effect` decorator

**Closes:** P3 prerequisite — side-effect closure.

**Entry conditions:**
- G_{C.1} = PASS.

**A_{C.2}:**
- Minimum tagging target: ≥ 20 known side-effecting functions — [ASSUMED: sampling from `audit_log.add`, `metrics_service` writes, external API calls. Full coverage impossible without exhaustive audit]. Gap is acceptable; gap size is tracked.
- `@side_effect(kind=...)` kind values — [ASSUMED: `{db_write, audit_log, external_api, metrics, queue_publish}`; document in decorator].

**Work:**
1. `app/validation/side_effect_registry.py`: `@side_effect(kind=...)` decorator + registry.
2. Tag ≥ 20 functions across `app/` (list documented in migration PR description).
3. `callers_in_path(modules) → Set[function]` — union of registered callers of any function in modules.
4. Coverage report: % of state-mutating functions tagged (baseline measurement, not a gate).

**Exit test T_{C.2} (deterministic):**
```bash
# T1: decorator registers
pytest tests/test_side_effect_registry.py::test_decorator_registers -x

# T2: callers_in_path
pytest tests/test_side_effect_registry.py::test_callers_in_path -x
# PASS: for fixture with @side_effect fn called by g() → {g} in callers_in_path({fn_module})

# T3: coverage report runs
python scripts/side_effect_coverage_report.py
# exits 0; prints: tagged/total ratio (informational, not a gate)

# T4: regression
pytest tests/ -x
```

**Gate G_{C.2}:** T1–T4 pass + ≥ 20 functions tagged (count verifiable via registry) → PASS.

---

### Stage C.3 — ImpactClosure

**Closes:** FORMAL P3 (Impact Closure) **within documented static-import + ≥20-tagged-side-effect scope**. Dynamic dispatch (getattr, runtime imports, eval) and untagged side-effecting functions remain explicit gaps per A_{C.1} and A_{C.2}. Does NOT close theorem condition 3 (epistemic provenance) — that is closed by PLAN_MEMORY_CONTEXT B.4 + PLAN_CONTRACT_DISCIPLINE F.1/F.2.

**Entry conditions:**
- G_{C.1} = PASS, G_{C.2} = PASS.
- G_{B.2} = PASS (CausalEdge backfill MUST include `task_dependencies` per cross-plan fix — PLAN_MEMORY_CONTEXT Stage B.2 T2b verifies `task_dependencies` rows have corresponding `causal_edges` rows with relation='depends_on'. C.3 walks `causal_edges WHERE relation='depends_on'`, not the raw `task_dependencies` table).

**A_{C.3}:**
- Closure = `ImportGraph.reverse_deps ∪ SideEffect.callers_in_path ∪ task_dependencies` — [CONFIRMED per FORMAL_PROPERTIES_v2 P3 binding].
- Gate: "delivery whose declared `modifying` files ⊄ ImpactClosure ∪ change.files → REJECTED" — [ASSUMED: ImpactClosure is computed at delivery time, not pre-delivery; performance is acceptable for current codebase size. If wrong at scale → cache closure per task, invalidate on dependency change].

**Work:**
1. `app/validation/impact_closure.py`:
   - `ImpactClosure(change) → Set[File]` = union of ImportGraph + SideEffect callers + task_dependencies transitive closure.
2. VerdictEngine rule: delivery's `modifying` list ⊄ `ImpactClosure(change) ∪ change.files` → REJECTED with list of missing files.

**Exit test T_{C.3} (deterministic):**
```bash
# T1: closure correctness
pytest tests/test_impact_closure.py::test_closure_correctness -x
# Fixture: change to f(); g() calls f(); g() has @side_effect; k() calls g()
# ImpactClosure = {f, g, k, side_effect_target}

# T2: gate rejects under-declared
pytest tests/test_impact_closure.py::test_gate_rejects_underdeclared -x
# PASS: delivery declaring modifying=[f] for change that affects {f,g,k} → REJECTED

# T3: gate accepts fully-declared
pytest tests/test_impact_closure.py::test_gate_accepts_full -x
# PASS: delivery declaring modifying=[f,g,k] → PASS

# T4: plan stability
pytest tests/test_impact_closure.py::test_plan_stability -x
# PASS: one-line edit mutates ≤ 2 task IDs (snapshot test per FORMAL_PROPERTIES_v2 P2)

# T5: regression
pytest tests/ -x
```

**Gate G_{C.3}:** T1–T5 pass → PASS.

---

### Stage C.4 — Reversibility classification + Rollback service

**Closes:** P5 (Reversibility).

**Entry conditions:**
- G_{C.3} = PASS.

**A_{C.4}:**
- Default on ambiguity = IRREVERSIBLE (fail-safe) — [CONFIRMED per FORMAL_PROPERTIES_v2 P5 binding].
- Disaster drill scope: 5 REVERSIBLE historical changes — [UNKNOWN: which 5? Must query `Changes` table after C.3 ships and identify REVERSIBLE candidates. If no REVERSIBLE changes exist yet → create synthetic fixture]. Resolution: if empty, use synthetic; document.

**Work:**
1. Alembic migration: `Change.reversibility_class ENUM('REVERSIBLE','COMPENSATABLE','RECONSTRUCTABLE','IRREVERSIBLE')`, `Change.rollback_ref TEXT`.
2. `app/validation/reversibility_classifier.py`: heuristic — add-only → REVERSIBLE; DROP/DELETE → IRREVERSIBLE; default → IRREVERSIBLE.
3. `app/validation/rollback_service.py`: `Rollback.attempt(change_id)` — applies rollback_ref; returns checksum.
4. VerdictEngine: every Change insert assigned a `reversibility_class` (cannot be NULL).

**Exit test T_{C.4} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: classifier heuristic
pytest tests/test_reversibility_classifier.py -x
# PASS: add-only → REVERSIBLE; DROP → IRREVERSIBLE; ambiguous → IRREVERSIBLE

# T3: disaster drill
pytest tests/test_rollback_drill.py -x
# PASS: 5 REVERSIBLE changes (real or synthetic): Rollback.attempt → state checksum byte-identical

# T4: no NULL class
pytest tests/test_reversibility_not_null.py -x
# PASS: Change insert without reversibility_class → rejected

# T5: regression
pytest tests/ -x
```

**Gate G_{C.4}:** T1–T5 pass → PASS.

---

## Phase D — Failure-oriented testing

### Stage D.1 — Deterministic test harness

**Closes:** Prerequisite for all property/metamorphic/adversarial tests. No formal property closed directly — infrastructure only.

**Entry conditions:**
- G_A = PASS (can run in parallel with C.1–C.4 from G_A).

**A_{D.1}:**
- `freezegun` vs `time-machine` — [ASSUMED: freezegun per existing ecosystem; check `pyproject.toml` for conflicts before adding].
- Hermetic DB: docker-compose test profile — [ASSUMED: already partially exists per platform setup. Verify before duplicating].

**Work:**
1. `tests/conftest.py`: pin random seed (e.g. `random.seed(42)`, `numpy.random.seed(42)`).
2. `freezegun` for deterministic clock in tests.
3. Hermetic DB fixture: docker-compose test profile (separate DB, no shared state).
4. Verify: 3 consecutive `pytest` runs produce bit-identical output.

**Exit test T_{D.1} (deterministic):**
```bash
# T0: freezegun compatibility pre-check (F9 fix)
grep -E "^(freezegun|time-machine)" pyproject.toml
# exits 0 (package declared); if missing, D.1 is BLOCKED until pyproject.toml update merged

# T1: three consecutive runs produce bit-identical test outcomes (elapsed time stripped).
# pytest's own summary includes wall-clock "in Xs" which freezegun cannot freeze;
# so normalize the output before diffing. Failure of this test indicates flaky state, not clock noise.
pytest tests/ --tb=no -q --no-header 2>&1 | sed -E 's/ in [0-9.]+s/ in <TIME>/g; s/[0-9]+\.[0-9]+s call/<TIME>s call/g' > run1.txt && \
pytest tests/ --tb=no -q --no-header 2>&1 | sed -E 's/ in [0-9.]+s/ in <TIME>/g; s/[0-9]+\.[0-9]+s call/<TIME>s call/g' > run2.txt && \
pytest tests/ --tb=no -q --no-header 2>&1 | sed -E 's/ in [0-9.]+s/ in <TIME>/g; s/[0-9]+\.[0-9]+s call/<TIME>s call/g' > run3.txt && \
diff run1.txt run2.txt && diff run2.txt run3.txt
# exits 0 (identical test outcomes; elapsed time excluded)

# T2: clock frozen in tests
pytest tests/test_harness_clock.py -x
# PASS: datetime.now() inside test returns frozen time, not wall-clock
```

**Gate G_{D.1}:** T1–T2 pass → PASS.

---

### Stage D.2 — Property tests

**Closes:** P6 (determinism — strengthened), P1 (idempotency — verified via hypothesis).

**Entry conditions:**
- G_{D.1} = PASS, G_A = PASS, G_{B.1} = PASS (CausalEdge for acyclicity test).

**Work:**
1. `tests/property/test_verdict_determinism.py` — same `(artifact, evidence)` → same verdict.
2. `tests/property/test_causal_acyclicity.py` — random inserts, no cycle.
3. `tests/property/test_idempotent_call.py` — two calls, same key, no additional side effect.
4. `tests/property/test_reversibility_roundtrip.py` — REVERSIBLE changes round-trip.
5. `tests/property/test_invariant_preservation.py` — every `Invariant.check_fn` holds across applicable transitions (Phase E adds Invariants; stub test for now).

**Exit test T_{D.2} (deterministic):**
```bash
pytest tests/property/ -x --hypothesis-seed=0
# all 5 property tests pass with fixed seed
```

**Gate G_{D.2}:** all property tests pass with `--hypothesis-seed=0` → PASS.

---

### Stage D.3 — Metamorphic tests

**Closes:** P6 (determinism — symmetry invariants).

**Entry conditions:**
- G_{D.1} = PASS, G_A = PASS (validators available).

**Work:**
1. `tests/metamorphic/test_validator_paraphrase.py` — reasoning A vs paraphrase A' → same verdict.
2. `tests/metamorphic/test_ac_permutation.py` — AC order doesn't change verdict.
3. `tests/metamorphic/test_evidence_permutation.py` — EvidenceSet order doesn't change verdict.

**Exit test T_{D.3} (deterministic):**
```bash
pytest tests/metamorphic/ -x
# all 3 metamorphic tests pass
```

**Gate G_{D.3}:** T_{D.3} pass → PASS.

---

### Stage D.4 — Adversarial fixtures

**Closes:** P10 prerequisite (regression coverage from historical Findings).

**Entry conditions:**
- G_{D.3} = PASS.

**A_{D.4}:**
- Which historical Findings qualify as adversarial fixtures — [ASSUMED: Finding.severity ≥ HIGH per ROADMAP D.4]. Steward reviews proposals.

**Work:**
1. `scripts/build_adversarial_fixtures.py` — reads `Finding` rows + `PRACTICE_SURVEY.md` incidents; emits regression test cases in `tests/adversarial/`.
2. Each new Finding with `severity ≥ HIGH` auto-proposes a fixture (Steward/distinct-actor review required before it becomes blocking).
3. Seed: ≥15 of 18 incidents from `PRACTICE_SURVEY.md` converted to adversarial test cases. 3-incident margin allowed for non-convertible incidents (e.g. incidents requiring infrastructure not yet in place); each exclusion needs a Steward-reviewed rationale line in `tests/adversarial/exclusions.md`.

**Exit test T_{D.4} (deterministic):**
```bash
# T1: script runs
python scripts/build_adversarial_fixtures.py --dry-run
# exits 0; prints count of proposed fixtures

# T2: adversarial suite green
pytest tests/adversarial/ -x
# all fixtures pass (they test that KNOWN past failures are caught)

# T3: ≥ 18 fixtures from PRACTICE_SURVEY
python -c "import json; d=json.load(open('tests/adversarial/manifest.json')); assert len(d) >= 15, f'got {len(d)}'"
# exits 0 (allows 3-incident margin; exclusions must be documented in tests/adversarial/exclusions.md)
```

**Gate G_{D.4}:** T1–T3 pass → PASS.

---

### Stage D.5 — FailureMode entity + RiskWeightedCoverage CI gate

**Closes:** P10 (risk-weighted coverage) — condition 5 fully strengthened.

**Entry conditions:**
- G_{D.2} = PASS, G_{D.3} = PASS, G_{D.4} = PASS.
- ADR-004 α value CLOSED (required for CI gate threshold).

**A_{D.5}:**
- FailureMode seed source: `AcceptanceCriterion` rows with `scenario_type ∈ {negative, edge_case, regression}` — [CONFIRMED: per GAP_ANALYSIS_v2 §P10, `objective.py:39`, `tier1.py:703`].
- α per capability — [UNKNOWN: ADR-004 not yet authored on disk as of 2026-04-23. Stage D.5 is BLOCKED until ADR-004 file exists with `Status: CLOSED` and α values specified per capability. See Q-table Q1.]
- `w_m` risk weights per FailureMode — [ASSUMED: initially uniform (w_m = 1/|M|) pending domain expert input; ADR-004 may specify or defer. Read ADR-004 before implementing weighting].

**Work:**
1. Alembic migration: `failure_modes(id, code, description, risk_weight, capability)`.
2. Seed from existing `AcceptanceCriterion` rows with failure-oriented `scenario_type`.
3. `scripts/coverage_report.py` — computes `∑ w_m Cov(T, m)` per capability.
4. CI gate in `pyproject.toml` / `.github/workflows/`: below α per capability → merge blocked.
5. Weekly evidence-verifiability replay job (P18): random sample 5% of `EvidenceSet` rows; re-execute reproducer_ref; divergences → Finding.

**Exit test T_{D.5} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: coverage report runs
python scripts/coverage_report.py
# exits 0; prints per-capability coverage (informational on first run)

# T3: CI gate blocks below α
pytest tests/test_coverage_ci_gate.py -x
# PASS: synthetic coverage below α → CI exits non-zero

# T4: mutation smoke (automated, not manual)
# scripts/mutation_smoke.py picks one named canonical rule from app/validation/verdict_engine.py,
# disables it via monkeypatch, runs pytest, asserts ≥1 failure, restores the rule,
# verifies restoration via SHA-256 of the file. Exits non-zero on any step's failure.
python scripts/mutation_smoke.py --rule=evidence_set_non_empty
# exits 0 only if: (a) disabled rule caused ≥1 failure; (b) rule restored; (c) file checksum matches baseline

# T5: replay job — divergences are blocking, not informational
# First run: baseline mode accepts divergences, writes manifest file.
# Subsequent runs: any divergence → emit Finding AND exit non-zero.
python scripts/evidence_replay.py --sample-pct=5 --first-run  # only on very first invocation; writes replay_baseline.json
python scripts/evidence_replay.py --sample-pct=5              # subsequent runs; exits non-zero on divergence
```

**Gate G_{D.5}:** T1–T3 automated + T4 mutation_smoke.py exits 0 (disabled rule caused failure, rule restored, checksum verified) + T5 replay job: baseline run produced manifest (first-run only) OR subsequent run exits 0 with zero divergences → PASS.

---

## Phase C+D exit gate (G_QA)

```
G_QA = PASS iff:
  G_{C.1} = PASS  (ImportGraph)
  AND G_{C.2} = PASS  (SideEffectRegistry)
  AND G_{C.3} = PASS  (ImpactClosure, gate rejects under-declared)
  AND G_{C.4} = PASS  (Reversibility + disaster drill)
  AND G_{D.1} = PASS  (deterministic harness, 3 runs bit-identical)
  AND G_{D.2} = PASS  (property tests with fixed seed)
  AND G_{D.3} = PASS  (metamorphic tests)
  AND G_{D.4} = PASS  (≥18 adversarial fixtures)
  AND G_{D.5} = PASS  (FailureMode entity, CI α-gate, replay job)
  AND pytest tests/ -x → all existing + Gate Engine + Memory + QA tests green
  AND mutation smoke: removing any VerdictEngine rule fails ≥ 1 test
  AND ImpactClosure gate active in VerdictEngine
```

**Soundness conditions closed at G_QA:**
- **Theorem condition 5 (within static-dispatch scope)** — ∃ T_i deterministic, risk-weighted: property tests (D.2), metamorphic (D.3), adversarial (D.4), CI α-gate (D.5). [T_{D.5} T3, T4]
- **FORMAL P3 (within documented scope)** — ImpactClosure rejects under-declared `modifying` lists for static imports and ≥20 tagged side-effecting functions. Dynamic dispatch and untagged side effects remain explicit gaps. [T_{C.3} T2]

**NOT closed by this plan:** theorem condition 3 (epistemic provenance of O_i from E_<i) — that is closed by PLAN_MEMORY_CONTEXT B.4 + PLAN_CONTRACT_DISCIPLINE F.1/F.2/F.3 (evidence-source constraint, verifiability, assumption control). The deep-verify-corrected scoping ensures this plan does not over-claim.

---

## Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks |
|---|---|---|
| Q1 | ADR-004 `w_m` risk weights — uniform default acceptable? Read ADR-004 before D.5 | Stage D.5 |
| Q2 | Are there REVERSIBLE historical Changes in DB for disaster drill, or must fixture be synthetic? Query DB before C.4 | Stage C.4 |
| Q3 | `freezegun` compatible with current `pyproject.toml`? Check before D.1 | Stage D.1 |
| Q4 | Dynamic dispatch coverage — any `getattr`-based state mutations in `app/` that ImpactClosure would miss? Grep `getattr` in `app/` before C.3 ships | Stage C.3 (disclosure) |

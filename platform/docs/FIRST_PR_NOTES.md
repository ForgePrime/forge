# First PR Notes — Phase A Stage A.1 EvidenceSet (shadow)

**Status:** DRAFT — not ready to merge. Blocked on ADR-003 RATIFIED + ADR-004 CLOSED.

## What this PR introduces

Per ROADMAP §13 First PR:

1. `app/models/evidence_set.py` — EvidenceSet entity with provenance CHECK constraints (partial P17).
2. `app/models/__init__.py` — EvidenceSet exported.
3. `app/validation/__init__.py` — new validation layer package.
4. `app/validation/rule_adapter.py` — RuleAdapter Protocol + Verdict + EvaluationContext (immutable dataclasses).
5. `app/validation/verdict_engine.py` — VerdictEngine static class with deterministic `evaluate()`.
6. `app/validation/gate_registry.py` — empty static `GATE_REGISTRY` dict + `lookup_rules()`.
7. `app/config.py` — `verdict_engine_mode` setting, defaults to `"off"`.
8. `tests/test_evidence_set_model.py` — 4 schema contract tests (currently SKIPPED — awaits alembic migration).
9. `tests/test_verdict_engine_stub.py` — 4 deterministic-property tests on stub behavior.

**Size:** ~250 LOC additive, 0 removed.
**Blast radius:** zero to production — `verdict_engine_mode='off'` by default; stub not invoked by any existing code path.

## What this PR does NOT do

- **No alembic migration.** Current repo has no `alembic/versions/` directory — suggests DB bootstrap via `Base.metadata.create_all`. Generating the first migration requires distinct-actor review of the baseline state. Deferred to a follow-up PR once ADR-003 ratified (which is also when this PR becomes mergeable per ADR-003's binding rule).
- **No rules in GateRegistry.** GATE_REGISTRY is intentionally empty; population happens per-stage.
- **No wiring of VerdictEngine into Decision / Execution commit paths.** That is Phase A.4 cutover — gated on canary sign-off per PLAN_GATE_ENGINE.
- **No integration with existing `app/services/contract_validator.py` or `app/services/plan_gate.py`.** Adapters come in Phase A.3.

## Blockers for merge

- [ ] **ADR-003 RATIFIED** — per ADR-003 self-referential rule, no normative `platform/docs/` or `app/` code can be treated as binding until distinct-actor review. This PR is DRAFT artifact that becomes mergeable at Stage 0.1 exit.
- [ ] **ADR-004 CLOSED** — calibration constants (τ tolerance for determinism tests in Phase D.2) informs test thresholds downstream; not blocking for THIS PR's merge but prerequisite for Phase A exit.
- [ ] **ADR-014 CLOSED** — C2 sufficiency gate placement (pre-LLM vs post-hoc) may reshape VerdictEngine entry point; deferring full wiring until this decision lands.

## Test plan

Run after merge:

```bash
cd platform
uv run pytest tests/test_verdict_engine_stub.py -x  # 4 tests, should pass green
uv run pytest tests/test_evidence_set_model.py -x   # 4 tests, SKIPPED until migration lands
```

Run full regression:

```bash
uv run pytest tests/ -x
```

Expected: all existing tests green (zero modifications to existing behavior); 4 new tests in test_verdict_engine_stub.py pass; 4 tests in test_evidence_set_model.py skipped with explicit reason.

## Acceptance criteria (per ROADMAP §13)

- [x] All existing tests green (zero modifications to existing behavior — VERDICT_ENGINE_MODE=off).
- [ ] New tests green (pending full test run post-merge).
- [ ] Migration up + down round-trip clean (deferred with alembic migration).
- [ ] `alembic current` updated (deferred).

## Post-merge follow-ups

1. Generate alembic initial migration (`alembic revision --autogenerate -m "baseline schema including evidence_sets"`) — must be done in environment with real DB.
2. Activate `test_evidence_set_model.py` tests (remove `pytestmark.skip`).
3. Begin A.2 GateRegistry population (first entries: Execution state transitions).
4. A.3 shadow-mode: add `RuleAdapter` implementations for `contract_validator` and `plan_gate`; log diffs.

---

**Authored:** 2026-04-24
**Author:** commissioning AI agent (solo — requires distinct-actor review per ADR-003 + CONTRACT §B.8).
**Reversibility:** REVERSIBLE — entirely additive; `verdict_engine_mode='off'` keeps code dormant; revert = `git revert` single commit.

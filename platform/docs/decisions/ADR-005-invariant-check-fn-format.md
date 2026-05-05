# ADR-005 — Invariant.check_fn format (Python callable vs DSL vs SQL)

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003)
**Date:** 2026-04-24
**Decided by:** user (decision) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage E.2, FORMAL_PROPERTIES_v2 P13, ADR-014 (orthogonal), ADR-017 (integrates).

## Context

E.2 introduces `Invariant` entity with a `check_fn` column that evaluates whether a state-transition preserves a system invariant. The field's *format* determines expressiveness, performance, auditability, and ability to version invariants.

## Decision

**Option A — Python callable, with hardening**:

Schema:
- `Invariant.check_fn TEXT NOT NULL` — stores **module+function import path** (e.g. `"app.invariants.inv_task_done_requires_all_ac_passed"`), NOT raw code.
- Insert-time validation: regex `^app\.invariants\.inv_[a-z_]+_[a-z_]+$` (naming: `inv_<entity>_<predicate>`); reject otherwise.
- `ast.parse` validation of the target module against allowed-import whitelist (stdlib read-only, `app.models`, `app.evidence.causal_graph`); forbidden: `os`, `subprocess`, `eval`, `exec`, `__import__` dynamic, `open` for write.

Runtime:
- `importlib.import_module(module_path) → getattr(module, fn_name)` at Invariant registration time (lazy cache).
- Execute inside **read-only DB session** (`session.execute("SET TRANSACTION READ ONLY")` or equivalent).
- `@invariant_check` decorator wraps registered functions; decorator asserts:
  - Returns `bool` or raises explicit `InvariantViolation(reason=...)`.
  - No `session.is_modified` mutations during call (checked via SQLAlchemy session before/after).
  - Pure function: same (entity_state, ctx) → same Verdict on 3 consecutive invocations.

Exit-test contract (enforced at PLAN_CONTRACT_DISCIPLINE Stage E.2 T2+):
- `pytest tests/test_invariant_purity.py` — for every registered invariant: call 3× with identical argument → identical Verdict + zero session mutations.

Seed invariants (day-1):
- `inv_task_done_requires_all_ac_passed` — Task.DONE ⟹ all AC.status=PASS
- `inv_decision_requires_non_empty_evidence_set` — Decision insert ⟹ ≥ 1 EvidenceSet FK

Cross-entity graph predicates (e.g. "AC traceable to Requirement via CausalGraph") are addressable via `from app.evidence.causal_graph import requirements_of` in invariant function body — impossible in SQL-only, the key reason Python callable wins.

## Alternatives considered

- **A. Python callable reference** (`app.invariants.fn_name`): full expressiveness, imports any app code — rejected as default: couples invariants to code revision, hard to version/backport; security-sensitive (arbitrary Python); auditability requires reading source.
- **B. Typed DSL / Pydantic predicate tree** (`{"and": [{"eq": ["task.status", "DONE"]}, {"all_pass": "task.acceptance_criteria"}]}`): structurally verifiable, versioned as JSONB, inspectable in DB; limited expressiveness — complex invariants require DSL extension.
- **C. Parameterized SQL expression** (WHERE-clause template executed against an entity row): fast at scale, DB-native; limited to tabular expressions, cannot express cross-entity graph properties.

## Consequences

### Immediate
- Chosen format dictates E.2 migration schema (TEXT/JSONB/SQL_fragment column type) and invariant-runner implementation effort.

### Downstream
- All future Invariants carry this format; format change = breaking migration.

### Risks
- **A (Python)**: arbitrary code surface risk; requires sandbox or code-review discipline.
- **B (DSL)**: DSL grows over time into an ad-hoc language; needs clear extension rules.
- **C (SQL)**: cross-DB-engine portability; complex graph predicates impossible.

### Reversibility
COMPENSATABLE — migration from one format to another requires re-authoring all seeded Invariants; plan for cost.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE.md Stage E.2]** ADR-005 blocks E.2 start.
- **[UNKNOWN]** current codebase existing `app/validation/*.py` — do we already have a predicate pattern to extend?
- **[UNKNOWN]** performance budget for check_fn evaluation per Execution commit.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option A (Python callable + import-path storage + ast.parse whitelist + @invariant_check decorator + read-only session execution); content DRAFT pending distinct-actor review.

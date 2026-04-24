# ADR-005 — Invariant.check_fn format (Python callable vs DSL vs SQL)

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering
**Related:** PLAN_CONTRACT_DISCIPLINE Stage E.2, FORMAL_PROPERTIES_v2 P13.

## Context

E.2 introduces `Invariant` entity with a `check_fn` column that evaluates whether a state-transition preserves a system invariant. The field's *format* determines expressiveness, performance, auditability, and ability to version invariants.

## Decision

[UNKNOWN — one of three options must be chosen and justified by distinct-actor review.]

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

- v1 (2026-04-24) — skeleton.

# ADR-011 — BLOCKED state down-migration handling

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.4, FORMAL_PROPERTIES_v2 P20.

## Context

F.4 adds `BLOCKED` to `Execution.status` enum. The alembic migration must handle:
1. **Up migration** — straightforward (add enum value).
2. **Down migration** — what happens to rows currently in `BLOCKED` state when the column is reverted to the old enum? Options: convert to `ERROR`, `PENDING`, DELETE row, or MIGRATION FAIL with diagnostic.

## Decision

[UNKNOWN — pick one down-migration strategy.]

## Alternatives considered

- **A. Convert BLOCKED → `ERROR` on down-migration** — preserves row, loses distinction (ERROR is terminal, BLOCKED is resolvable).
- **B. Convert BLOCKED → `PENDING`** — preserves "may resume" semantic but loses the "blocked by UNKNOWN" reason; could re-execute incorrectly.
- **C. Migration FAIL with diagnostic** — safest: admin must manually resolve or drop BLOCKED rows before down-migration. Candidate.
- **D. DELETE BLOCKED rows** — rejected: silent data loss; violates FC §37 (no silent discard).

## Consequences

### Immediate
- Down-migration script fixed by chosen strategy.
- Strategy C requires operational runbook ("before down-migration, query BLOCKED rows, resolve or delete explicitly").

### Downstream
- Any future schema evolution involving Execution.status must consider BLOCKED rows.

### Risks
- Strategy A/B: silent state corruption if BLOCKED rows had resolve-uncertainty callbacks outstanding.
- Strategy C: operational friction if down-migration is emergency rollback and BLOCKED rows exist.

### Reversibility
REVERSIBLE — strategy revisable via new ADR.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage F.4]** ADR-011 blocks F.4 start.
- **[CONFIRMED: FORMAL_PROPERTIES_v2 P20]** BLOCKED semantics specified.
- **[UNKNOWN]** down-migration frequency expectation — rare (rollback only) or routine?

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

# ADR-011 — BLOCKED state down-migration handling

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003)
**Date:** 2026-04-24
**Decided by:** user (decision) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.4, FORMAL_PROPERTIES_v2 P20, FC §37 (no silent discard).

## Context

F.4 adds `BLOCKED` to `Execution.status` enum. The alembic migration must handle:
1. **Up migration** — straightforward (add enum value).
2. **Down migration** — what happens to rows currently in `BLOCKED` state when the column is reverted to the old enum? Options: convert to `ERROR`, `PENDING`, DELETE row, or MIGRATION FAIL with diagnostic.

## Decision

**Option C — Migration FAIL with diagnostic** (safest; explicit operator intervention required; no silent state loss).

Implementation:
- Down-migration script contains pre-check query:
  ```sql
  SELECT count(*), array_agg(id ORDER BY id LIMIT 10) AS sample_ids
  FROM executions
  WHERE status = 'BLOCKED';
  ```
- If `count > 0` → `raise alembic.util.CommandError(...)` with message listing count + sample IDs + remediation command.
- Forward-migration (up) is straightforward (adds `BLOCKED` to enum); no pre-check needed.

Operational runbook:
- Before emergency down-migration, admin runs `scripts/resolve_or_purge_blocked_executions.py` which:
  - Prints current BLOCKED row count + sample.
  - Requires explicit flag: `--confirm-resolve-all` (invokes resolve-uncertainty with `accepted-by=<current_user>`) OR `--confirm-delete-all` (hard DELETE with audit-log entry).
  - No default; dry-run without flag just prints diagnostic.
- Document runbook entry in `platform/docs/platform/OPERATIONS.md` (follow-up creation).

Exit-test contract (PLAN_CONTRACT_DISCIPLINE F.4 T1 strengthening):
- `pytest tests/test_blocked_down_migration.py` — fixture with 3 BLOCKED rows → down-migration raises CommandError with exact sample IDs in message (not just generic "constraint violation").

Rationale against rejected alternatives:
- **A (BLOCKED → ERROR)**: violates FC §37 — silent workaround converts "recoverable state" to "terminal state"; future resolve-uncertainty calls on previously-BLOCKED rows would fail unpredictably.
- **B (BLOCKED → PENDING)**: violates ECITP §2.8 prior substitution — PENDING means "ready to execute"; Execution with unresolved UNKNOWN items would re-enter execution loop, exactly what F.4 BLOCKED state is designed to prevent.
- **D (DELETE rows)**: violates P22 disclosure protocol + FC §37 — silent data loss; audit trail destroyed.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option C (migration FAIL with diagnostic + operator-tool pre-step); content DRAFT pending distinct-actor review.

# ADR-021 — ExpectedDiff schema per Change.type + IRREVERSIBLE recovery procedure

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering + governance
**Related:** PLAN_GOVERNANCE Stage G.10, Forge Complete theorem §25 (Baseline/Post/Diff) + §26 (per-element runtime verification).

## Context

G.10 requires every state-mutating Change to declare `expected_diff` pre-commit. After apply, observed Diff is compared; Diff ≠ ExpectedDiff → REJECTED + auto-rollback (REVERSIBLE) or CRITICAL Incident (IRREVERSIBLE). Two decision groups:

1. **Schema of `Change.expected_diff` per Change.type** — migration vs code vs config each need different shape.
2. **IRREVERSIBLE recovery procedure** — what happens when irreversible Change produces unexpected Diff (auto-rollback impossible)?

## Decision

[UNKNOWN — two decisions:]

### Part 1: ExpectedDiff schemas

Candidate per Change.type (NOT a decision — starting point):
- `migration`: `{tables_created: [...], tables_dropped: [...], columns_added: [...], columns_dropped: [...], indexes_added: [...], rows_affected_estimate: int}`
- `code`: `{files_added: [paths], files_modified: [paths], files_removed: [paths], public_api_added: [names], public_api_removed: [names]}`
- `config`: `{env_vars_added: [...], env_vars_modified: [...], feature_flags_changed: [...]}`
- `data`: `{tables_touched: [...], rows_inserted_estimate: int, rows_updated_estimate: int, rows_deleted_estimate: int}`

Questions:
- Exact/approximate for row counts (±%)?
- How is "rows_affected_estimate" validated post-apply?

### Part 2: IRREVERSIBLE recovery procedure

G.10 design: IRREVERSIBLE Change with Diff mismatch → no auto-rollback, CRITICAL Incident, Steward sign-off required. Need:
- Incident-response runbook fields (investigator, decision-ownership, approved-next-action).
- Approved recovery options: (a) manual rollback via new compensating Change; (b) accept the deviation with Steward sign-off + new Decision explaining; (c) system-wide BLOCKED until resolved.
- SLA for recovery (how long can IRREVERSIBLE-mismatch sit unresolved before escalation?).

## Alternatives considered

- **A. Per-Change.type typed schemas (above) + detailed recovery runbook** — candidate: thorough but needs maintenance.
- **B. Single generic `{added: [...], modified: [...], removed: [...]}` schema for all Change types** — rejected: loses type-specific validation semantics.
- **C. Free-form JSONB ExpectedDiff** — rejected: not validatable; violates FC §27 determinism.
- **D. ExpectedDiff mandatory only for migrations; other types optional** — rejected: §26 requires per-element check for all Impacts.

## Consequences

### Immediate
- G.10 migration adds `Change.expected_diff JSONB NOT NULL` with CHECK constraint per schema (A).
- `baseline_post_verifier.py` has per-type validation.

### Downstream
- Changes without ExpectedDiff are impossible (insert rejected) — pre-existing Changes (legacy) need backfill decision.
- IRREVERSIBLE runbook becomes operational dependency.

### Risks
- Schema mismatch with actual Change shape → valid Changes rejected at insert (friction).
- Runbook untested → real incident exposes gaps.

### Reversibility
- Schema: COMPENSATABLE via superseding ADR.
- Recovery procedure: tested via tabletop exercises post-G.10.

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE Stage G.10]** ADR-021 blocks G.10 start.
- **[UNKNOWN]** historical Change.diff distribution — which Change.type dominates?
- **[UNKNOWN]** existing incident-response infrastructure (integration point for IRREVERSIBLE recovery).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

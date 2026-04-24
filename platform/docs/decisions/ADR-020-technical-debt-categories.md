# ADR-020 — Technical debt category enum + accepted_by role allowlist

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.12, Forge Complete theorem §37, ADR-007 (Steward role), ADR-013 (override metric parallel).

## Context

F.12 tracks deferred work via `technical_debt` table. Two decisions required:

1. **Category enum** — what categories classify debt entries (needed for audit, metrics, retirement).
2. **`accepted_by` role allowlist** — which roles can authorize debt acceptance (determines governance posture).

## Decision

**Option A (extended) — 8-category enum + 3-role allowlist with co-sign threshold.**

### Part 1: Category enum

Finalized enum (8 canonical per FC §37):
```sql
CREATE TYPE technical_debt_category AS ENUM (
  'incomplete_validation',    -- gap in a validator; known edge not handled
  'duplicated_logic',         -- copy-paste; refactor deferred
  'weak_contract',            -- optional field that should be required, etc.
  'temporary_workaround',     -- patch for acute issue; root-fix pending
  'deferred_refactor',        -- structural improvement accepted for later
  'untested_edge_case',       -- code exists, test does not
  'missing_monitoring',       -- prod behavior not observable
  'known_regression'          -- accepted partial rollback of prior capability
);
```

Extensions: new categories require superseding ADR. Common additions deferred to v2 based on production learning (candidates: `gaming_coverage_threshold` from ADR-004 risk, `sdk_constraint` for upstream-forced suboptimal patterns).

### Part 2: `accepted_by` role allowlist + co-sign threshold

Allowed roles (enum `debt_acceptance_role`): `{steward, platform_engineer, tech_lead}`.

Acceptance rules:
- **Single-sign**: `platform_engineer` OR `tech_lead` may unilaterally accept debt UP TO `debt_severity_threshold`:
  - `change_size_loc ≤ 100 AND estimated_deferral_weeks ≤ 4` → single-sign allowed
- **Co-sign required**: if debt exceeds either threshold:
  - `change_size_loc > 100` OR `estimated_deferral_weeks > 4` → co-sign from 2-of-3 roles required
  - Steward counted as 1 role; co-sign = 2 distinct `debt_acceptance_role` values
- **Steward-only categories**: `known_regression` and `gaming_coverage_threshold` (if added in v2) require Steward signature regardless of size

`accepted_role` captured at acceptance time as immutable audit value. If accepter leaves org, historical `technical_debt.accepted_role_at_time` preserved separately from `accepted_by` user FK.

Metric: `M_debt_count_by_category` per G.3 — dashboard shows open-debt count per category. Steward quarterly audit flags categories with growth > 20% quarter-over-quarter.

Rejected alternatives:
- **B (12-category extended)**: more granular audit valuable but premature; let production signal justify.
- **C (free-form TEXT category)**: violates §27 determinism; not queryable for metrics.
- **D (strict co-sign for all debt regardless of size)**: too heavy for small debt; deters legitimate acceptance workflow.

## Alternatives considered

- **A. 8-category enum (FC §37 list as-is) + 3-role allowlist** — minimum viable.
- **B. Extended 12-category enum + 3-role** — more granular audit; more ADR maintenance.
- **C. Free-form category TEXT + 3-role** — rejected: not queryable for metrics; violates §27 determinism.
- **D. Strict 3-role allowlist requiring co-sign for >N hours of debt** — candidate: scales governance to cost.

## Consequences

### Immediate
- F.12 migration fixes enum values.
- Detector tests expect specific categories.

### Downstream
- Metrics (per G.3): open-debt count per category; becomes visible dashboard element.
- Rule Lifecycle (G.4): debt retirement via resolved_at when Change addresses debt.

### Risks
- Too-narrow categories → debt mis-classified → gaming.
- Too-permissive allowlist → rubber-stamp acceptance.

### Reversibility
COMPENSATABLE — enum extension via new ADR; allowlist tightening possible.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage F.12]** ADR-020 blocks F.12.
- **[CONFIRMED: FC §37]** candidate category list.
- **[UNKNOWN]** historical debt record (for calibration).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option A (8-category enum + 3-role allowlist + size-based co-sign threshold LOC>100 OR deferral>4w + Steward-only for known_regression); content DRAFT.

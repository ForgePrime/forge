# ADR-020 — Technical debt category enum + accepted_by role allowlist

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering + governance
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.12, Forge Complete theorem §37 No Technical Debt Rule.

## Context

F.12 tracks deferred work via `technical_debt` table. Two decisions required:

1. **Category enum** — what categories classify debt entries (needed for audit, metrics, retirement).
2. **`accepted_by` role allowlist** — which roles can authorize debt acceptance (determines governance posture).

## Decision

[UNKNOWN — specify enum + allowlist.]

### Part 1: Category enum (candidate list per FC §37)
`{incomplete_validation, duplicated_logic, weak_contract, temporary_workaround, deferred_refactor, untested_edge_case, missing_monitoring, known_regression}`

Questions:
- Add `gaming_coverage_threshold` category (per ADR-004 risk)?
- Add `sdk_constraint` for cases where upstream SDK forces suboptimal code?
- Granularity trade-off: few broad categories (8) vs many narrow categories (20+)?

### Part 2: `accepted_by` role allowlist
Candidate: `{steward, platform_engineer, tech_lead}`

Questions:
- Can `platform_engineer` alone accept debt, or requires co-sign with `tech_lead`?
- Is `steward` override-only (for blocks rejected by engineers)?
- Does `accepted_role` get captured at acceptance time and become immutable (audit trail)?

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

- v1 (2026-04-24) — skeleton.

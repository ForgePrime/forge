# ADR-016 — Test entity — promote AC.scenario_type or accept as-is

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering + architecture
**Related:** PLAN_GOVERNANCE Stage G.9, ECITP C12, FC §22 Test Completeness.

## Context

ECITP C12 proof-trail chain includes `AC → tests → verification`. Current Forge: `AcceptanceCriterion.scenario_type` enum encodes test-intent (positive, negative, edge_case, boundary, regression, etc. per ADR-001). **No distinct `Test` entity exists.** Analogous to ADR-015 Requirement decision.

## Decision

[UNKNOWN — requires:]

### Option A: Promote `AC.scenario_type` to distinct `Test` table
- `tests` table with FK to AC; one-to-many (one AC can have multiple Tests — unit + integration + property-based).
- Pro: multiple tests per AC; Test can have own evidence_ref, execution record, coverage_weight.
- Con: migration + backfill; doubles entity count in proof-trail chain.

### Option B: Accept AC + scenario_type as canonical "test link" in chain
- G.9 audit accepts `AC.scenario_type` values as test-link representation.
- Pro: zero migration.
- Con: can only express 1:1 AC-to-Test; cannot represent AC with both unit + property tests.

## Alternatives considered

- **A** (see above)
- **B** (see above)
- **C. Virtual view: Test = (AC × scenario_type_enum × exec_method)** synthesized at query time — rejected: complex to implement, no stable ID.

## Consequences

### Immediate
- G.9 proof_trail_audit chain traversal depends on chosen option.
- D.4 adversarial fixtures (from PRACTICE_SURVEY) become Test rows (A) or remain as fixture files (B).

### Downstream
- P10 risk-weighted coverage calculation references tests — A allows per-Test weight, B uses AC-level aggregation only.
- FC §23 Failure-Oriented Test Selection `argmax P(detect failure)` — A enables Test-level ranking, B constrained to AC-level.

### Risks
- A: backfill complexity (which existing tests map to which AC?).
- B: coarser granularity limits future optimization.

### Reversibility
- A: IRREVERSIBLE (backfill).
- B: REVERSIBLE (promote later).

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE G.9 A_{G.9}]** ADR-016 blocks G.9.
- **[CONFIRMED: ADR-001]** scenario_type expanded to 9 values.
- **[UNKNOWN]** test-per-AC cardinality in practice (if >1 common, A is forced).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

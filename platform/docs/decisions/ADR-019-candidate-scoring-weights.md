# ADR-019 — Candidate Solution scoring weights (14 dimensions) + trivial-change bypass thresholds

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform + architecture lead
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.11, Forge Complete theorem §19 Optimal Solution Selection.

## Context

F.11 requires `Score(x) = Σ (weight_d × value_{c,d})` over 14 dimensions (9 positive + 5 negative). Per FC §19 the scoring needs weights AND tie-breaker rule. F.11 also specifies a trivial-change bypass (single-candidate allowed if change is small) requiring LOC threshold + impact_closure_size limit. Without ADR-019 numbers, F.11 validator has no argmax rule to enforce.

## Decision

[UNKNOWN — three decision groups:]

### Group 1: Weights for 14 dimensions
Positive (9): `business_fit, determinism, consistency, traceability, testability, runtime_verifiability, evolvability, resilience, justification_completeness`
Negative (5): `complexity, coupling, duplication, technical_debt, operational_risk, expected_future_cost`

Required: weight per dimension (sum-to-1 convention OR ordinal priority tiers).

### Group 2: Trivial-change bypass thresholds
- `change_size_loc_limit = ??` (candidate: 20? 50? 100?)
- `impact_closure_size_limit = ??` (candidate: 1? 2?)

### Group 3: Tie-breaker rule
- Lowest complexity? Lowest expected_future_cost? Candidate ID (lexicographic)? Explicit rule needed for determinism.

## Alternatives considered

- **A. All weights equal (1/14 each)** — rejected: encodes implicit prior "all dimensions equally important" which is almost certainly wrong (business_fit = evolvability? no).
- **B. Prioritization tiers (P0=5x weight, P1=3x, P2=1x, P3=0.5x)** — candidate: simpler to calibrate than 14 unique weights.
- **C. Context-dependent weights (infra change weights vs product change weights)** — rejected at start: too complex before calibration data; can add later.
- **D. Delphi-method calibration with platform + architecture leads** — candidate process: 2-3 iteration survey to stabilize weights.

## Consequences

### Immediate
- F.11 scoring function pinned to chosen weights.
- Every architectural Decision Score calculation uses these.

### Downstream
- Weight recalibration = new ADR + Decisions accepted under old weights retain their verdict (fixed-at-acceptance).

### Risks
- Weights encode values implicitly; wrong values → systematically bad decisions.
- Trivial-change thresholds too high → avoids multi-candidate discipline entirely.

### Reversibility
COMPENSATABLE — new ADR supersedes.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage F.11]** ADR-019 blocks F.11 start.
- **[UNKNOWN]** historical architectural Decisions to test-calibrate weights against.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

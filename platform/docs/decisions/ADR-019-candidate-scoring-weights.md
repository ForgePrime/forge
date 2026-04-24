# ADR-019 — Candidate Solution scoring weights (14 dimensions) + trivial-change bypass thresholds

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation with prioritization-tier starting weights, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.11, Forge Complete §19, ADR-004 (calibration parallel; recalibrate together).

## Context

F.11 requires `Score(x) = Σ (weight_d × value_{c,d})` over 14 dimensions (9 positive + 5 negative). Per FC §19 the scoring needs weights AND tie-breaker rule. F.11 also specifies a trivial-change bypass (single-candidate allowed if change is small) requiring LOC threshold + impact_closure_size limit. Without ADR-019 numbers, F.11 validator has no argmax rule to enforce.

## Decision

**Option B — Prioritization tiers (P0=5×, P1=3×, P2=1×, P3=0.5×).** Simpler to calibrate than 14 unique weights; explicit priority statement; evolves via tier reassignment (superseding ADR) rather than float-tuning.

### Group 1: Weights via tier assignment

**P0 (weight = 5×) — critical strategic dimensions:**
- `business_fit` — primary justification for any architectural choice
- `traceability` — ECITP C12 proof-trail requirement
- `determinism` — CCEGAP C9; non-negotiable

**P1 (weight = 3×) — essential engineering dimensions:**
- `testability`
- `runtime_verifiability` — FC §24
- `consistency`
- `resilience`

**P2 (weight = 1×) — desirable dimensions:**
- `evolvability`
- `justification_completeness`

**P3 (weight = 0.5×) — negative dimensions (subtracted from Score; low weight means we tolerate them while tracking):**
- `complexity`
- `coupling`
- `duplication`
- `technical_debt` (parallel to ADR-020 tracking)
- `operational_risk`
- `expected_future_cost`

**Formula:**
```
Score(c) =
  5 × (business_fit + traceability + determinism)
+ 3 × (testability + runtime_verifiability + consistency + resilience)
+ 1 × (evolvability + justification_completeness)
- 0.5 × (complexity + coupling + duplication + technical_debt + operational_risk + expected_future_cost)
```

Dimension values normalized to [0, 1] via ADR-019 v2-specified rubrics (not in this v2 scope; follow-up).

### Group 2: Trivial-change bypass thresholds
- `change_size_loc_limit = 50` (LOC)
- `impact_closure_size_limit = 1` (single file, no cross-file impact)

**Both conditions must hold** for trivial bypass: change ≤ 50 LOC AND ImpactClosure size = 1. Any larger/wider → architectural; requires ≥2 candidates.

### Group 3: Tie-breaker rule
If `|Score(c_1) - Score(c_2)| < ε = 0.5` (negligible difference):
1. **Primary**: lowest `complexity` dimension value
2. **Secondary**: lowest `expected_future_cost`
3. **Tertiary**: candidate UUID lexicographic (deterministic final tie-break)

### Supersession plan
After 6 architectural Decisions executed, review whether tier assignments match observed outcome quality. If misaligned (e.g., Decisions winning Score but leading to post-hoc regrets) → tier-reassignment ADR.

Rejected alternatives:
- **A (all weights equal)**: violates §19 "best total value"; encodes implicit all-equal prior.
- **C (context-dependent weights)**: too complex before calibration data; defer.
- **D (Delphi-method calibration)**: requires 2-3 humans; not available at current team size; tier-based approximates without full Delphi.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option B (P0-P3 tier multipliers + trivial-bypass 50 LOC AND 1-file + tie-breaker by complexity then cost then UUID); content DRAFT; tier reassignment after 6 architectural Decisions.

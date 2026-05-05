# ADR-016 — Test entity — promote AC.scenario_type or accept as-is

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.9, ECITP C12, FC §22 Test Completeness, ADR-001 (scenario_type enum), ADR-015 (parallel Requirement decision).

## Context

ECITP C12 proof-trail chain includes `AC → tests → verification`. Current Forge: `AcceptanceCriterion.scenario_type` enum encodes test-intent (positive, negative, edge_case, boundary, regression, etc. per ADR-001). **No distinct `Test` entity exists.** Analogous to ADR-015 Requirement decision.

## Decision

**Option B — Accept `AcceptanceCriterion + scenario_type` as canonical test-link in chain; no new entity.**

Rationale (parallel to ADR-015 Finding-as-Requirement decision): zero migration cost; reversible via future supersession if test-per-AC cardinality > 1 becomes common in practice. Matches existing Forge pattern (ADR-001 already expanded scenario_type enum to 9 values covering positive/negative/edge_case/boundary/concurrent/malformed/regression/performance/security — sufficient granularity for initial test-intent expression).

Implementation:
- No migration required for ADR-016.
- G.9 proof-trail audit chain: `Change → Execution → AcceptanceCriterion (scenario_type in range) → Finding (type=requirement)` — AC IS the test-link, scenario_type encodes test intent.
- FC §22 Test Completeness coverage: each AC's `scenario_type` bitmap must span `{nominal, boundary, edge, exception}` per the plan's test completeness requirement; enforced via FailureMode coverage (D.5 α-gate) and adversarial fixture seed (D.4).
- If empirical data later shows AC needs multiple independent Test executions (e.g., same AC verified by unit + property + integration in parallel), supersede ADR-016 with Option A (distinct Test table + FK).

Rejected alternative:
- **A (distinct Test table + FK migration)**: correct if test-per-AC > 1 common; defer until empirical signal; premature migration adds complexity without proven need.
- **C (virtual view)**: complex FK semantics; defer.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option B (AC + scenario_type as test-link, zero-migration); content DRAFT.

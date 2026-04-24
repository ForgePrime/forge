# ADR-015 — Requirement entity — promote from Finding.type or accept as-is

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.9 ProofTrailCompleteness, ECITP C12 (10-link proof trail), FC §10, FC §11, ADR-016 (parallel Test-entity decision), ADR-017 (relation mapping consumers).

## Context

ECITP C12 requires a 10-link causal chain for every artifact: `documents → analysis → ambiguities → objectives → tasks → requirements → AC → tests → verification → artifact`. Current Forge schema has: `Knowledge → Finding → Objective → Task → AcceptanceCriterion → Execution → Change`. **There is no distinct `Requirement` entity.** Two viable options:

## Decision

**Option B — Accept `Finding.type = 'requirement'` as canonical chain link; no new entity.**

Rationale: zero migration cost; reversible (can promote to distinct Requirement table later via superseding ADR); avoids touching AC+task_dependencies schemas; matches existing Forge pattern where Finding is the generic "discovered/declared artifact" entity. G.9 proof-trail audit walks `Finding` rows where `type='requirement'` as the canonical chain link.

Implementation:
- No migration required for ADR-015.
- Finding type discriminator enforced at insert: `Finding.type ∈ {'requirement', 'ambiguity', 'risk', 'decision_candidate', 'observation'}` — extend existing enum.
- FC §11 completeness fields (ClearInput, ClearOutput, BusinessRule, VerificationMethod) live as typed JSONB field `Finding.type_specific_fields` with schema validation per `type` value.
- G.9 chain traversal: `Change → Execution → AcceptanceCriterion → (AC.source_ref → Finding WHERE type='requirement')` satisfies the 10-link ECITP C12 chain.

Rejected alternative:
- **A (distinct Requirement table + FK migration)**: correct long-term if test-per-Requirement cardinality > 1 becomes common; defer until empirical signal justifies migration cost.
- **C (virtual view)**: complex FK semantics; defer.

If empirical data later shows requirement-management distinct from Finding discovery (e.g., requirements carry own approval workflow independent of Finding close status) → supersede with v2 promoting to Option A.

## Alternatives considered

- **A** (see above)
- **B** (see above)
- **C. Hybrid: Finding.type='requirement' retained + virtual Requirement view** (DB view materialized as Requirement) — candidate: no migration, but view-based FK semantics complex.

## Consequences

### Immediate
- G.9 proof_trail_audit.py implementation depends on chosen option.

### Downstream
- Future FC §11 completeness enforcement (per partial-gap list) on Requirement needs fields — either new Requirement columns (A) or Finding.type='requirement' validator (B).

### Risks
- A: backfill data-integrity risk.
- B: type overloading, fragile validators.

### Reversibility
- A: IRREVERSIBLE once backfill applied (would need inverse migration).
- B: REVERSIBLE (can always promote later).

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE G.9 A_{G.9}]** ADR-015 blocks G.9 start.
- **[CONFIRMED: ECITP §3 C12]** 10-link chain specified.
- **[UNKNOWN]** count of existing `Finding.type='requirement'` rows (affects backfill cost).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option B (Finding-as-Requirement, zero-migration); content DRAFT.

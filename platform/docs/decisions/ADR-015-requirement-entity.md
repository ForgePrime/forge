# ADR-015 — Requirement entity — promote from Finding.type or accept as-is

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering + architecture
**Related:** PLAN_GOVERNANCE Stage G.9 ProofTrailCompleteness, ECITP C12 (10-link proof trail), FC §10 (BR↔TR traceability), FC §11 (Requirement completeness).

## Context

ECITP C12 requires a 10-link causal chain for every artifact: `documents → analysis → ambiguities → objectives → tasks → requirements → AC → tests → verification → artifact`. Current Forge schema has: `Knowledge → Finding → Objective → Task → AcceptanceCriterion → Execution → Change`. **There is no distinct `Requirement` entity.** Two viable options:

## Decision

[UNKNOWN — requires:]

### Option A: Promote `Finding.type = 'requirement'` to distinct `Requirement` table
- New migration: `requirements` table; `AcceptanceCriterion.requirement_id` FK added.
- Backfill: move rows where `Finding.type='requirement'` → new table; link AC via scope_tags.
- Pro: clear entity separation; `Finding` stays a discovery-time artifact, `Requirement` becomes normative.
- Con: migration touches multiple tables; backfill risk per GAP_ANALYSIS_v2.

### Option B: Accept `Finding.type='requirement'` as canonical; no new table
- G.9 proof-trail audit accepts Finding-as-Requirement in the chain.
- Pro: zero migration cost.
- Con: `Finding` carries two semantically distinct roles (ambiguity/risk vs requirement); FC §11 completeness fields (ClearInput, ClearOutput) need to live on Finding (type-specific validation).

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

- v1 (2026-04-24) — skeleton.

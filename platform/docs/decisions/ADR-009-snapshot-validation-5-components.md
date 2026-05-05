# ADR-009 — Deterministic Snapshot Validation 5 components

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.8, FORMAL_PROPERTIES_v2 §11.2 (P25), OPERATING_MODEL §9.4, ADR-021 (consumed by G.10 BaselinePost).

## Context

P25 specifies snapshot validation with 5 components per OM §9.4. Stage G.8 builds `snapshot_validator.py` that implements these 5 components. Without exact component definitions, G.8 cannot mechanically close P25 (violates CCEGAP C9).

Per PLAN_GOVERNANCE G.8 post-fix: "Closes P25 iff ADR-009's 5 components align with FORMAL_PROPERTIES_v2 §11.2 `synth(s, i)` pattern. If ADR-009 diverges, P25 remains open."

## Decision

**Option A — 5-component literal enumeration per candidate list.**

Five components of `snapshot_validator.capture_state(scope) → SnapshotResult`:

1. **Structural** — row counts per affected table; schema hash of `pg_catalog.pg_class + pg_attribute` for scope entities.
2. **Distribution** — distinct-value cardinalities per indexed column; value-range `{min, max, median}` per numeric column; top-10 mode values per enum column.
3. **Invariant** — results of every `Invariant` whose `applies_to_entity` intersects scope (per ADR-005 Python callable; read-only execution).
4. **Cross-entity** — FK-consistency: for each FK in scope, `count(child WHERE parent NOT EXISTS)` must equal 0 (dangling refs flagged).
5. **Temporal** — `max(created_at), max(updated_at)` per table; ordering validity: `created_at < updated_at` for all rows (no time-travel).

Per-component output: `{component_name: str, value: JSONB, sha256: str}`. SnapshotResult is the 5-tuple with a composite sha256 over the ordered concatenation.

Alignment with FORMAL §11.2 synth(s, i): structural + distribution + invariant + cross-entity are the 4 state-check dimensions; temporal is the *progression* dimension making synth(s, i) well-defined over time. 5 total matches §11.2 intent; if §11.2 enumeration differs on distinct-actor read, supersede with v2 preserving the 5-count shape.

Exclusions from observation (per AD-7 correction in CHANGE_PLAN_COMPREHENSIVE):
- `pg_statistic`, `pg_stat_*`, `pg_class.reltuples`, `pg_stat_user_tables.*` — mutable by autovacuum + ANALYZE, not part of semantic state.
- Explicit exclusion list in `platform/app/validation/snapshot_validator.py` docstring; grep-gate tests for forbidden catalog reads.

Rationale against rejected alternatives:
- **B (3-component minimal)**: violates "5" specification in OM §9.4.
- **C (variable per entity-type)**: violates FC §27 determinism (same inputs → same result impossible if component count varies).

## Alternatives considered

- **A. Literal 5-component enumeration above** — candidate: matches common data-quality framework structure.
- **B. 3-component minimal** (structural + invariant + temporal) — rejected: §11.2 text says "5", fewer = spec violation.
- **C. Variable-component per entity-type** — rejected: violates FC §27 deterministic validation (components must be same input → same result).

## Consequences

### Immediate
- G.8 `snapshot_validator.py` implementation scope fixed by chosen 5 components.
- Applied to Stage 1 volume check + Stage 3 output shape + Stage 4 business-outcome (≥ 3 gates use it).

### Downstream
- P25 closure conditional on alignment (see Context quote).
- Future entities inherit same 5-component signature.

### Risks
- Components under-specified → silent drift unrelated to the 5.
- Components over-specified → performance cost on every snapshot.

### Reversibility
COMPENSATABLE — component revision via superseding ADR; historical snapshots retain original-format evidence.

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE G.8]** ADR-009 blocks G.8 start.
- **[UNKNOWN]** FORMAL_PROPERTIES_v2 §11.2 exact text — must be read before finalizing to ensure alignment.
- **[UNKNOWN]** OPERATING_MODEL §9.4 source of "5" — why 5 specifically?

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option A (5 components: structural + distribution + invariant + cross-entity + temporal); mutable-catalog exclusions per AD-7; content DRAFT.

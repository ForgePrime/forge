# ADR-009 — Deterministic Snapshot Validation 5 components

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering
**Related:** PLAN_GOVERNANCE Stage G.8, FORMAL_PROPERTIES_v2 §11.2 (P25), OPERATING_MODEL §9.4.

## Context

P25 specifies snapshot validation with 5 components per OM §9.4. Stage G.8 builds `snapshot_validator.py` that implements these 5 components. Without exact component definitions, G.8 cannot mechanically close P25 (violates CCEGAP C9).

Per PLAN_GOVERNANCE G.8 post-fix: "Closes P25 iff ADR-009's 5 components align with FORMAL_PROPERTIES_v2 §11.2 `synth(s, i)` pattern. If ADR-009 diverges, P25 remains open."

## Decision

[UNKNOWN — requires enumeration of 5 components consistent with FORMAL §11.2 synth(s, i) pattern.]

Candidate components (placeholder):
1. **Structural** — row counts, schema hash
2. **Distribution** — key cardinalities, value-range histograms
3. **Invariant** — Invariant.check_fn results per applicable entity (integrates with E.2)
4. **Cross-entity** — FK-consistency snapshot
5. **Temporal** — timestamp-ordering validity

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

- v1 (2026-04-24) — skeleton.

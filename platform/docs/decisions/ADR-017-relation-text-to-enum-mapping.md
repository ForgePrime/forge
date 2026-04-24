# ADR-017 — Canonical `relation TEXT → relation_semantic ENUM` mapping for B.6 backfill

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering
**Related:** PLAN_MEMORY_CONTEXT Stage B.6, ECITP C6, FORMAL_PROPERTIES_v2 P14.

## Context

B.6 adds `causal_edges.relation_semantic ENUM('requirement_of', 'risk_of', 'ac_of', 'test_of', 'mitigates', 'derives_from', 'produces', 'blocks', 'verifies')`. Existing `relation TEXT` column has free-form values. Backfill requires a **canonical mapping** TEXT → ENUM. Without this mapping, backfill is either non-deterministic (LLM-based) or silent (NULL defaults), both violating ESC-1 + ECITP §2.8.

## Decision

[UNKNOWN — canonical mapping table needed.]

Example shape (illustrative only — NOT a decision):
```yaml
mapping:
  depends_on: derives_from
  implements: ac_of
  produced_by: produces
  mitigates_risk: mitigates
  validates: verifies
  ...
unmappable_strategy: NULL + Finding(kind='unmapped_relation_semantic', severity=HIGH)
```

## Alternatives considered

- **A. Exhaustive mapping table in YAML / Python dict, grep-derived from existing `relation TEXT` values** — candidate: deterministic, reviewable, extensible.
- **B. Regex-pattern mapping** — rejected: false matches; hard to audit.
- **C. LLM-based mapping** — rejected: violates ESC-1 + ECITP §2.8 (exactly the mode B.6 is intended to prevent).
- **D. Manual row-by-row labeling by Steward** — rejected at scale; acceptable only for ambiguous cases (after A runs).

## Consequences

### Immediate
- B.6 `scripts/backfill_relation_semantic.py` implementation scope.
- Query DB for distinct `relation TEXT` values pre-mapping to size the table.

### Downstream
- New relation_semantic values require superseding ADR.

### Risks
- Incomplete mapping → backfill leaves rows with NULL + Finding (by design); requires iterative mapping updates.
- Wrong mapping → semantic topology violation; hard to detect until downstream uses it.

### Reversibility
COMPENSATABLE — mapping revision; re-backfill script idempotent.

## Evidence captured

- **[CONFIRMED: PLAN_MEMORY_CONTEXT Stage B.6]** ADR-017 blocks B.6 backfill.
- **[UNKNOWN]** current distinct `causal_edges.relation` values — query needed before drafting mapping.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

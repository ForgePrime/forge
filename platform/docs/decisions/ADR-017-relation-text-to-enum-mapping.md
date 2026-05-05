# ADR-017 — Canonical `relation TEXT → relation_semantic ENUM` mapping for B.6 backfill

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept with AI recommendation) + AI agent (draft)
**Related:** PLAN_MEMORY_CONTEXT Stage B.6, ECITP C6, FORMAL_PROPERTIES_v2 P14, ADR-005 (Invariants consume CausalGraph), ADR-015/016 (entity outcomes affect extension).

## Context

B.6 adds `causal_edges.relation_semantic ENUM('requirement_of', 'risk_of', 'ac_of', 'test_of', 'mitigates', 'derives_from', 'produces', 'blocks', 'verifies')`. Existing `relation TEXT` column has free-form values. Backfill requires a **canonical mapping** TEXT → ENUM. Without this mapping, backfill is either non-deterministic (LLM-based) or silent (NULL defaults), both violating ESC-1 + ECITP §2.8.

## Decision

**Option A — Exhaustive YAML mapping table + Finding on unmappable.**

Source of truth file: `platform/docs/mappings/relation_semantic_mapping.yaml` (to be authored in B.6 implementation PR).

Canonical mapping (v1):
```yaml
version: 1
schema_version: "relation_semantic_v1"
mapping:
  # Dependency / ordering → derives_from / blocks
  depends_on: derives_from
  requires: derives_from
  needs: derives_from
  precedes: blocks
  blocks: blocks
  blocked_by: blocks            # direction-normalized at insert (src/dst swap)
  # Production / implementation → produces
  produced_by: produces         # direction-normalized
  implements: produces
  generates: produces
  # Requirement / AC linkage → requirement_of / ac_of
  specifies: requirement_of
  required_by: requirement_of
  satisfies: ac_of
  covers: ac_of
  # Risk / mitigation → risk_of / mitigates
  mitigates: mitigates
  mitigates_risk: mitigates
  addresses_risk: mitigates
  risks: risk_of
  # Test / verification → test_of / verifies
  tests: test_of
  verified_by: verifies         # direction-normalized
  validates: verifies
  # Derivation (explicit)
  derives_from: derives_from
  based_on: derives_from
```

Unmappable TEXT → `relation_semantic = NULL` + `Finding(kind='unmapped_relation_semantic', severity=HIGH, evidence_ref=edge.id)`. Extensions require superseding ADR (not in-place edit).

Pre-implementation prerequisite: `scripts/query_distinct_relations.py` reports actual distinct `causal_edges.relation` values vs YAML mapping; any missing → ADR-017 v2 required before B.6 backfill. Runs as part of Pre-flight Stage 0.3 smoke.

New column: `causal_edges.relation_semantic_version INT DEFAULT 1` — preserves historical mapping version for audit when mapping evolves.

Rationale against rejected alternatives:
- **B (regex)**: false-positive rate + audit-hostile (which pattern won?); exhaustive list avoids.
- **C (LLM)**: violates ESC-1 determinism + ECITP §2.8; B.6 exists to prevent exactly this mode.
- **D (manual Steward labeling at scale)**: rejected as default but retained as escalation path for NULL-emitted Findings.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option A (exhaustive YAML + Finding on unmappable + per-Change versioning via relation_semantic_version column); content DRAFT.

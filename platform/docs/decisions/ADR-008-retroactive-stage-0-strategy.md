# ADR-008 — Retroactive Stage 0 Data Classification + SecurityIncident schema

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform + security + governance
**Related:** PLAN_GOVERNANCE Stage G.1, DATA_CLASSIFICATION.md (CGAID Stage 0), R-FW-02.

## Context

Stage G.1 introduces a pre-ingest DataClassification gate. **Existing Knowledge rows in DB have no classification** — they were created before the gate existed. Two questions must be answered before G.1 migration runs:

1. How are legacy unclassified Knowledge rows handled (migrate / grandfather / require reclassification)?
2. What is the `SecurityIncident` schema that the kill-criteria trigger uses (per PLAN_GOVERNANCE G.1 step 6: `tier ≥ Confidential AND confirmed_by_steward=true AND confirmed_at IS NOT NULL` → system-wide BLOCKED)?

## Decision

[UNKNOWN — requires:]

### Part 1: Retroactive classification strategy
- **Option A:** Migrate-default (all legacy rows → `tier='Internal'`), flag for Steward review within N days. Risk: false classification.
- **Option B:** Mandatory reclassification — all legacy rows tagged `tier='unclassified'`, Execution that touches unclassified Knowledge → BLOCKED until classified. Risk: pipeline halt.
- **Option C:** Hybrid — Migrate-default, but any Confidential+ data discovered later (via DLP scan) triggers retroactive incident + Steward review.

### Part 2: SecurityIncident schema
Required columns: `id, detected_at, detected_by (ENUM {dlp_scan, audit, steward_report, automated_check}), tier (ENUM Public/Internal/Confidential/Secret), leaked_knowledge_id FK, evidence_ref, confirmed_at NULL, confirmed_by_steward FK NULL, confirmed_by_steward_signature_ref NULL, resolved_at NULL, resolution_decision_id FK NULL`

## Alternatives considered

See Decision section — A/B/C for retroactive strategy; single schema shape for SecurityIncident.

## Consequences

### Immediate
- G.1 migration depends on chosen strategy: Option A = simplest migration, B = added `unclassified` enum value, C = both.

### Downstream
- Kill-criteria trigger semantics inherits from SecurityIncident schema — any schema change = migration.

### Risks
- Option A: silently mis-classifies real Confidential data as Internal → regulatory exposure.
- Option B: implementation halts until Steward triages every unclassified row → calendar slip.
- Option C: combines both risks at reduced magnitude.

### Reversibility
COMPENSATABLE — reclassification allowed via new Knowledge+Classification row; old row retained for audit.

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE Stage G.1 A_{G.1}]** ADR-008 blocks G.1 start.
- **[CONFIRMED: PLAN_GOVERNANCE G.1 step 6]** kill-criteria trigger references SecurityIncident.confirmed_by_steward.
- **[UNKNOWN]** volume of unclassified legacy Knowledge rows (query needed before choosing A/B/C).
- **[UNKNOWN]** regulatory regime — GDPR/SOC2/industry-specific affects choice.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

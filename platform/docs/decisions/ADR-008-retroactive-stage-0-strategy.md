# ADR-008 — Retroactive Stage 0 Data Classification + SecurityIncident schema

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.1, DATA_CLASSIFICATION (CGAID Stage 0), R-FW-02, ADR-018 (DLP decision parallel), ADR-021 (IRREVERSIBLE recovery pattern reused).

## Context

Stage G.1 introduces a pre-ingest DataClassification gate. **Existing Knowledge rows in DB have no classification** — they were created before the gate existed. Two questions must be answered before G.1 migration runs:

1. How are legacy unclassified Knowledge rows handled (migrate / grandfather / require reclassification)?
2. What is the `SecurityIncident` schema that the kill-criteria trigger uses (per PLAN_GOVERNANCE G.1 step 6: `tier ≥ Confidential AND confirmed_by_steward=true AND confirmed_at IS NOT NULL` → system-wide BLOCKED)?

## Decision

**Option C (hybrid) + finalized SecurityIncident schema.**

### Part 1: Retroactive classification strategy — Option C hybrid

Legacy Knowledge rows (created before G.1 DataClassification gate):
1. **Migrate-default**: migration sets `tier = 'Internal'` for all existing rows without classification. Fast path; no operational halt.
2. **Steward review window**: 30 days from G.1 deployment for Steward to spot-audit sampled legacy rows (10% random sample). Any Confidential+ discovered → per Part 3 retroactive incident.
3. **Post-window**: all legacy rows assumed correctly classified as Internal unless later evidence suggests otherwise.
4. **Ongoing discovery**: any time post-window, if DLP scan OR Steward review OR user report identifies Confidential+ in legacy row → triggers `SecurityIncident(tier ≥ Confidential)` regardless of elapsed time (retroactive always possible).

### Part 2: SecurityIncident schema (finalized)

```sql
CREATE TYPE incident_detection_method AS ENUM (
  'dlp_scan', 'audit', 'steward_report', 'automated_check', 'user_report'
);
CREATE TYPE data_tier AS ENUM ('Public', 'Internal', 'Confidential', 'Secret');

CREATE TABLE security_incidents (
  id SERIAL PRIMARY KEY,
  detected_at TIMESTAMP NOT NULL,
  detected_by incident_detection_method NOT NULL,
  tier data_tier NOT NULL CHECK (tier IN ('Confidential', 'Secret')),  -- only Confidential+ are incidents
  leaked_knowledge_id INT FK → knowledge(id) NOT NULL,
  evidence_ref TEXT NOT NULL,  -- pointer to DLP output / audit finding
  confirmed_at TIMESTAMP NULL,
  confirmed_by_steward_id INT FK → users(id) NULL,
  confirmed_by_steward_signature_ref TEXT NULL,  -- AuditLog entry
  resolved_at TIMESTAMP NULL,
  resolution_decision_id INT FK → decisions(id) NULL,
  system_blocked BOOLEAN NOT NULL DEFAULT false,  -- G.1 kill-criteria flag
  notes TEXT
);

CREATE INDEX ix_security_incidents_unresolved ON security_incidents (confirmed_at)
WHERE resolved_at IS NULL;
```

### Part 3: Retroactive incident procedure

When legacy row identified as Confidential+:
1. `SecurityIncident` row inserted with `tier ≥ Confidential`, `leaked_knowledge_id`, `detected_by`.
2. Steward notified (email + dashboard badge).
3. Steward within 48h: `UPDATE security_incidents SET confirmed_at = NOW(), confirmed_by_steward_id = ..., confirmed_by_steward_signature_ref = ...` (captured in AuditLog).
4. **If confirmed AND tier in ('Confidential', 'Secret')**: G.1 kill-criteria triggers `system_blocked = true` → new Executions cannot touch Confidential+ data (or system-wide BLOCKED depending on spread).
5. Resolution: per incident-response runbook (compensation, quarantine, revocation per tier); `resolution_decision_id` populated; `resolved_at` set.

Legacy-row exemption tracking:
- Column `Knowledge.classified_retroactively BOOLEAN DEFAULT false` — rows migrated in default-Internal are flagged.
- Dashboard query `GET /governance/legacy-unreviewed` lists rows with `classified_retroactively=true AND NOT audited_by_steward_at IS NOT NULL` so Steward can batch-review.

Rejected alternatives:
- **A (migrate-default, no follow-up review)**: silent mis-classification risk; too permissive.
- **B (mandatory reclassification)**: operational halt; all Executions touching legacy Knowledge blocked until human reviews every row; untenable at scale.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option C hybrid (migrate-default Internal + 30d Steward spot-audit + retroactive incident via security_incidents table) + finalized SecurityIncident schema + legacy-row audit dashboard; content DRAFT.

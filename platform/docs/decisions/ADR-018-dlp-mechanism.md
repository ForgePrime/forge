# ADR-018 — DLP mechanism for Confidential+ tier

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation based on Forge's current role as LLM-orchestration platform, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.1, FRAMEWORK_MAPPING R-FW-02, DATA_CLASSIFICATION.md, ADR-008 (SecurityIncident schema consumer).

## Context

G.1 DataClassification Gate blocks Confidential+ data ingest without DLP record. The DLP **mechanism** (which technology, which policies, which detection rules) is not specified. Two resolution paths:

## Decision

**Path B — Formal ACKNOWLEDGED_GAP per FRAMEWORK_MAPPING §12 with explicit Forge-scope contract.**

Rationale: Forge is an **LLM-orchestration platform operating on structured development artifacts** (tickets, code, plans, decisions, findings). It is **NOT a primary data-ingestion system**. The data flowing into Forge is:
- Ticket/issue descriptions (text, usually Internal tier)
- Code snippets (Internal or Confidential if proprietary; scope-bound)
- Architecture docs (Internal to Confidential)
- Developer-authored specs (Internal)

Forge does NOT typically ingest:
- Customer PII
- Payment data (PCI scope)
- Health records (PHI scope)
- Mass end-user data feeds

Given this scope, running a DLP engine inside Forge duplicates upstream org DLP at disproportionate cost.

### Contract (explicit)

Forge's ACKNOWLEDGED_GAP contract:
1. **Forge assumes**: upstream adopting organization runs DLP at data-source boundary BEFORE data reaches Forge. Adopting org responsibility.
2. **Forge provides**: DataClassification gate (G.1) + SecurityIncident infrastructure (ADR-008) to record, trigger kill-criteria, and audit IF Confidential+ data is nonetheless detected.
3. **Forge detects (partial)**: basic tier-tag validation at ingest (no tier = rejected; Confidential+ without DLP record = rejected per G.1). Does NOT perform semantic PII-detection.
4. **Steward ACKNOWLEDGED_GAP sign-off**: required at each quarterly audit (G.5) — Steward re-confirms that upstream DLP assumption still holds for current use case.

### Trigger for supersession (switch to Path A)

Mandatory supersession with Path A if ANY of:
- Adopting org lacks upstream DLP (detected via security review).
- Forge use case expands to direct end-user data ingestion.
- ≥1 `SecurityIncident(tier ≥ Confidential, detected_by='dlp_scan')` emitted by any mechanism (indicates DLP is being done somewhere but not governed).
- Regulatory regime (GDPR/HIPAA/PCI) requires Forge's direct DLP per audit.

At supersession: ADR-018 v2 chooses from `{Presidio (Python, open-source, extensible), AWS Macie (if cloud), commercial SaaS}` based on deployment context.

### ACKNOWLEDGED_GAP record format

```sql
INSERT INTO acknowledged_gaps (
  gap_kind, signed_by_steward_id, signed_at, expires_at, rationale
) VALUES (
  'dlp_mechanism',
  <steward_user_id>,
  NOW(),
  NOW() + INTERVAL '1 quarter',  -- must re-sign quarterly
  'Forge operates on structured dev artifacts; upstream org DLP handles primary data boundary. See ADR-018 v2 triggers for supersession.'
);
```

Rejected alternatives:
- **A (technology-backed DLP, e.g. Presidio)**: valid; but premature given current scope. Ready-to-activate via supersession on any trigger.
- **C (bespoke DLP)**: reinvents wheel; maintenance cost unjustified.

## Alternatives considered

- **A. Technology-backed DLP (Presidio default)** — candidate: open-source, Python-native, extensible policy set.
- **B. Formal ACKNOWLEDGED_GAP** — candidate if org already has DLP at data-source boundary; zero build cost; requires explicit Steward-signed gap record.
- **C. Build bespoke DLP regex engine** — rejected: reinvents wheel, maintenance cost.

## Consequences

### Immediate
- G.1 pre-ingest gate wires to either DLP service (A) or accepts ACKNOWLEDGED_GAP marker (B).
- Kill-criteria trigger (G.1 step 6) references `SecurityIncident` — requires DLP to detect such incidents (A) or relies on external incident reporting (B).

### Downstream
- Regulatory posture depends heavily on this decision.

### Risks
- A: DLP false-negatives (real PII slips through); false-positives (noise, user friction).
- B: silent PII leaks if assumption about upstream DLP is wrong.

### Reversibility
REVERSIBLE — can start with B, add A later via superseding ADR.

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE G.1]** ADR-018 blocks G.1 DLP integration.
- **[CONFIRMED: FRAMEWORK_MAPPING R-FW-02]** risk explicitly listed.
- **[UNKNOWN]** org's existing data-boundary DLP posture (affects B feasibility).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Path B (ACKNOWLEDGED_GAP with explicit contract: Forge = dev-artifact orchestration, not primary data ingestion; upstream org DLP assumed; quarterly Steward re-sign-off; mandatory supersession triggers listed); content DRAFT.

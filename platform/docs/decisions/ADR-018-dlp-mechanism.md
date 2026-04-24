# ADR-018 — DLP mechanism for Confidential+ tier

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform + security + governance
**Related:** PLAN_GOVERNANCE Stage G.1, FRAMEWORK_MAPPING R-FW-02, DATA_CLASSIFICATION.md.

## Context

G.1 DataClassification Gate blocks Confidential+ data ingest without DLP record. The DLP **mechanism** (which technology, which policies, which detection rules) is not specified. Two resolution paths:

## Decision

[UNKNOWN — choose one:]

### Path A: Technology-backed DLP
- Choose technology (e.g. Presidio, AWS Macie, Google Cloud DLP, commercial SaaS).
- Define detection policies (PII patterns, PHI patterns, credential regex, etc.).
- Integrate scan at ingest boundary.

### Path B: Formal ACKNOWLEDGED_GAP
- Mark DLP as "out of scope for current phase" per FRAMEWORK_MAPPING §12 with Steward sign-off record.
- Forge relies on adopting-org's existing DLP at the data boundary before data reaches Forge.
- Must be accompanied by clear contract: Forge does NOT perform DLP, expects sanitized input.

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

- v1 (2026-04-24) — skeleton.

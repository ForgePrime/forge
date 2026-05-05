# CGAID Regulatory Alignment

**Audience:** legal, compliance, Data Protection Officers, Framework Stewards interfacing with regulators
**Status:** framework self-assessment — **not legal advice**
**Source:** extracted from `OPERATING_MODEL.md` v1.4 Appendix B during the v2.0 reorganization

---

## Positioning

This document maps CGAID elements to the principal regulatory frameworks most likely to apply in client engagements. It is **not legal advice**. It is a framework self-assessment intended to be validated by qualified legal counsel for each adopting organization and each regulated client engagement.

The mapping is updated on a 6-month cadence (see §"Legal Review Commitment" below). All disagreement between this mapping and counsel opinion is resolved in favor of counsel opinion; this document is then updated to reflect the resolution.

---

## §1 EU AI Act (Regulation (EU) 2024/1689)

The EU AI Act establishes obligations based on AI system risk classification. AI-assisted software *development* for general-purpose business systems typically falls under **limited-risk** or **minimal-risk** categories. However, **high-risk** classification applies when:
- the software being produced is itself a high-risk AI system (e.g., used in employment decisions, credit scoring, critical infrastructure, law enforcement, biometrics), or
- the development process is embedded within a regulated sector that attracts sector-specific AI obligations.

| EU AI Act Article / Obligation | CGAID Element | Alignment |
|---|---|---|
| Art. 13 — Transparency and provision of information to deployers | AI Operational Contract (`.ai/CONTRACT.md`); epistemic tagging `CONFIRMED` / `ASSUMED` / `UNKNOWN` | **Direct** — every AI claim carries an explicit epistemic state |
| Art. 14 — Human oversight | Mandatory PR review; Stage 4 Verify gate; closed verification loop against business outcome | **Direct** — AI never closes its own delivery loop |
| Art. 15 — Accuracy, robustness, cybersecurity | Edge-case test planning (artifact #6); verification against business-level Definition of Done | **Partial** — CGAID addresses correctness; cybersecurity requires supplementary controls outside this framework |
| Art. 17 — Quality management system | Framework versioning and changelog; quarterly adoption audit; annual external peer review | **Direct** — CGAID is a quality management system for AI-assisted delivery |
| Art. 26 — Obligations on deployers of high-risk AI systems | DELIVERY §5 Data Handling Requirements; Stage 0 Data Classification Gate | **Direct** |

**Known gap for high-risk contexts:** CGAID does not currently produce an EU AI Act *conformity assessment* artifact. For high-risk deployment contexts, supplementary documentation (technical file, risk management system, post-market monitoring plan) is required in addition to CGAID artifacts.

### §1.1 AI Liability Directive (proposed — status as of 2026-04)

The EU AI Liability Directive (proposal COM(2022) 496) modifies the burden of proof in civil liability cases involving AI systems. As of April 2026 the directive remains in legislative process; its enactment is expected to materially shift civil liability exposure for AI-assisted software:

- **Disclosure obligations** — under the directive, a claimant can compel disclosure of information about a high-risk AI system's operation. CGAID's artifact trail (ADRs, Handoff Documents, classification log, Skill Change Log) materially reduces the cost of compelled disclosure — the evidence is already organised.
- **Presumption of causality** — the directive introduces a rebuttable presumption of causality between AI defect and damage in specified circumstances. Strong pre-code Evidence Packs and explicit Stage 2 Side-Effect Maps (artifact #11) support rebuttal of the presumption by demonstrating reasonable engineering care.
- **Residual exposure** — CGAID does not eliminate liability. It produces the documentation trail that would be introduced in a defense.

Adopting organizations should track directive enactment at each 6-month legal review and update this section with the enacted text reference when it is available.

---

## §2 GDPR (Regulation (EU) 2016/679)

| GDPR Article | CGAID Element | Alignment |
|---|---|---|
| Art. 5 — Principles (lawfulness, minimization, storage limitation) | DELIVERY §5 Data Handling (retention windows, PII scanning) | **Direct** |
| Art. 6 — Lawful basis for processing | Stage 0 classification routing includes legal basis field | **Direct**, when the Data Classification Rubric records legal basis per item |
| Art. 17 — Right to erasure | DELIVERY §5 erasure procedure (72h SLA, per-system confirmation, vendor capability flagging) | **Direct** |
| Art. 25 — Data protection by design and by default | Stage 0 Data Classification Gate as hard prerequisite before AI access | **Direct** |
| Art. 32 — Security of processing | DELIVERY §5 PII scanning (automated + quarterly manual audit) | **Partial** — organizational security controls required in addition |
| Art. 35 — DPIA for high-risk processing | Framework audit trail supports DPIA inputs | **Facilitative** — the DPIA itself is a separate artifact owned by the Data Protection Officer |

---

## §3 Sectoral Regulations (apply per client context)

**Financial services** (MiFID II, **DORA** in the EU, SOX in the US, UK FCA regimes): audit trail and traceability align well with CGAID artifacts. Specific requirements around change management for trading and settlement systems may require supplementary controls — see active project context in `.ai/PROJECT_PLAN.md`.

**DORA specifically (Digital Operational Resilience Act — Regulation (EU) 2022/2554, in force January 2025):** establishes ICT operational-resilience obligations for financial entities. Implications for CGAID adoption in financial-services contexts:

- **Art. 5–10 (ICT risk management framework)** — CGAID's Stage 0 Data Classification plus DELIVERY §5 Data Handling partially implement required data/ICT risk controls; DORA requires additional risk-management framework artifacts beyond CGAID.
- **Art. 11–13 (ICT-related incident management)** — CGAID's incident-to-rule loop (DELIVERY §3 Rule Lifecycle) aligns with DORA incident classification and reporting; DORA's mandatory reporting timelines (4h initial, 72h intermediate, 1-month final) are not implemented by CGAID alone.
- **Art. 28–30 (third-party risk management)** — CGAID's AI vendor DPA requirements (DATA_CLASSIFICATION.md routing matrix) provide partial coverage; full DORA compliance requires vendor register, exit strategies, and critical-third-party tracking beyond CGAID.

**Digital services and AI-generated output** (EU Digital Services Act — Regulation (EU) 2022/2065): if CGAID-delivered software generates content shown to end users (not only code), DSA obligations may apply to that content — particularly around AI-generated content disclosure, illegal-content handling, and transparency reporting. CGAID artifacts do not directly produce DSA compliance documentation; adopting organizations producing user-facing AI output must supplement the framework with DSA-specific artifacts.

**Healthcare** (HIPAA in the US, EU Medical Device Regulation, local health data frameworks): Stage 0 classification must recognize Protected Health Information (PHI) as its own category. Default posture in the Data Classification Rubric should elevate PHI from Confidential to **Secret by default** (excluded from AI workflows) unless a specific Business Associate Agreement or equivalent authorizes otherwise.

**Public sector** (procurement regulations, national security classifications): the four-tier Rubric may need extension to align with government classification schemes. Many AI vendor Data Processing Agreements are incompatible with certain public-sector contracts — this must be verified per engagement before Stage 0 routing decisions.

**Employment and labor** (relevant whenever the engagement touches HR/staffing/workforce systems): AI systems used in employment decisions are classified as high-risk under Art. 6 of the EU AI Act. For any CGAID engagement producing AI features that influence hiring, performance management, or worker treatment, the "high-risk" pathway applies and conformity assessment artifacts become mandatory.

---

## §4 Legal Review Commitment

Every **six months**, a designated counsel reviews:

1. Regulatory changes since the last review (EU AI Act secondary legislation, GDPR enforcement guidance, sectoral updates)
2. The active client portfolio and which regulations apply
3. Framework amendments affecting compliance posture

Findings are incorporated into the framework changelog (DELIVERY §11) with cross-reference to this document. Legal review findings that require framework change follow the standard change process (observed evidence + Lead Steward + peer Steward sign-off).

---

## §5 Disclaimer

This document represents the framework owners' good-faith mapping of CGAID to major regulatory frameworks **as of the framework v2.0 reorganization (date in commit log)**. Regulations, enforcement guidance, and case law evolve. This mapping is a starting point for legal review, not a substitute for it.

Adopting organizations must obtain their own legal review before using CGAID:
- with data subject to regulatory requirements,
- in regulated sectors,
- across jurisdictions with local AI, data protection, or sectoral requirements that diverge from the EU frameworks described here.

---

## Governance of this document

- **Owners:** Framework Stewards in coordination with designated legal counsel
- **Review cadence:** every 6 months (legal review) + at every regulatory enactment affecting active client portfolio
- **Change process:** counsel opinion supersedes self-assessment; updates to this doc require Lead Steward sign-off after counsel review
- **Kill criterion link:** see DELIVERY §10 K5 (Regulatory obsolescence) — if scheduled review finds >50% of mapping invalidated, this document triggers framework-level review

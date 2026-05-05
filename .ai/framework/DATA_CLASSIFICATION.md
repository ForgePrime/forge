# Data Classification Rubric

**CGAID Artifact #10 — The Stage 0 Gate Instrument**

Version 1.0 · Owner: Framework Stewards · Status: Operational

---

## Purpose

This Rubric is the operational instrument of **Stage 0 — Data Classification Gate** in the CGAID framework. Every piece of client material — documents, meeting notes, specifications, data samples, emails, prompts — must be classified under this Rubric before it enters the Solutioning Cockpit, the codebase, or any AI-accessible memory.

Stage 0 has one purpose: prevent irreversible exposure of client IP or personal data to AI vendors. This Rubric is the mechanism.

---

## The Four Tiers

### Tier 1 — **PUBLIC**

*Material already published or intended for public disclosure.*

- **Routing:** any AI system under default terms. No restrictions.
- **Typical examples:**
  - Published case studies, marketing materials, public financial reports
  - Openly licensed code, public API documentation
  - Published technical articles, conference talks
  - Information that appears on the client's public website
- **Do not treat as Public:** material that is "shareable internally" but not yet published. That is Internal.

### Tier 2 — **INTERNAL**

*Client or internal business information that is not sensitive but not public.*

- **Routing:** enterprise AI tier with standard Data Processing Agreement. Avoid free/consumer AI tiers that train on user data.
- **Typical examples:**
  - Internal team organization, process documentation
  - Generic code patterns, framework configurations, tooling choices
  - Non-sensitive architectural diagrams
  - Anonymized or aggregated operational data
- **Edge cases:** if a document describes internal processes *with named individuals*, the named-individual portion is Confidential; the rest may remain Internal.

### Tier 3 — **CONFIDENTIAL**

*Client business-sensitive material, including business logic, integration details, non-PII personal data, and any content the client reasonably expects to remain protected.*

- **Routing:** **enterprise AI tier with zero-retention DPA ONLY.** Requires:
  - *Client consent recorded* (contract clause or explicit email confirmation)
  - *Active DPA on file* for the AI vendor
  - *Vendor must support zero retention* (content not stored beyond the session, not used for training)
  - *Right-to-erasure must be operationally available* at the vendor
- **Typical examples:**
  - Client business rules, pricing logic, commercial terms
  - Integration specifications, API keys in descriptive form (not raw), system topology
  - Meeting notes containing contact names, emails, decisions
  - **project-specific:** settlement logic, legal entity mappings, Warsaw office data feed specs, asset-type configurations
  - Non-public financial data aggregated at entity or account level
- **When in doubt between Internal and Confidential:** choose Confidential. Downgrading is possible after review; upgrading after exposure is not.

### Tier 4 — **SECRET**

*Material whose exposure is legally, contractually, or commercially prohibited. Processed by humans only. AI is excluded.*

- **Routing:** **NO AI system, without exception.** Not "AI with strong DPA" — AI is simply not in the processing pipeline for this tier.
- **Mandatory examples:**
  - Credentials, API keys (raw), private keys, passwords, session tokens
  - Personal Identifying Information at scale (customer databases, employee records, ID documents)
  - Protected Health Information (PHI) — unless specific Business Associate Agreement authorizes otherwise
  - Financial account data, payment card data, national ID numbers
  - Content under national security classification
  - Content under legal privilege (attorney-client, attorney work product)
  - Trade secrets explicitly marked by client as such
  - **project-specific:** raw bank transaction data, individual settlement records with payer/payee PII, employee personal records
- **If you are unsure whether something is Secret:** treat it as Secret and escalate to a Framework Steward for re-classification. The asymmetry of risk justifies the caution.

---

## Classification Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│ Is the material already public                              │
│ OR intended for imminent public release?                    │
└─────────────────────────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
       YES                   NO
        │                    │
        ▼                    ▼
     PUBLIC         ┌────────────────────────────────────────┐
                    │ Does it contain any of:                 │
                    │  - credentials / keys / tokens          │
                    │  - PII at scale (>1 individual)         │
                    │  - PHI / medical data                   │
                    │  - financial account numbers            │
                    │  - legal privilege material             │
                    │  - client-marked trade secrets          │
                    └────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                   YES                   NO
                    │                    │
                    ▼                    ▼
                 SECRET         ┌──────────────────────────────┐
                                │ Does it contain client       │
                                │ business logic, specs,       │
                                │ integration details, or      │
                                │ named individuals?           │
                                └──────────────────────────────┘
                                          │
                                ┌─────────┴─────────┐
                               YES                   NO
                                │                    │
                                ▼                    ▼
                           CONFIDENTIAL          INTERNAL
```

When the tree leads to an ambiguous answer, the default is to escalate one tier (more restrictive). Document the ambiguity in the classification log — it drives Rubric refinement.

---

## Routing Matrix

| Tier | Anthropic Claude (enterprise) | OpenAI (enterprise) | Google Gemini (enterprise) | Microsoft Copilot (enterprise) | GitHub Copilot (enterprise) | Consumer AI tiers | Human-only |
|---|---|---|---|---|---|---|---|
| Public | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Internal | ✅ (standard DPA) | ✅ (standard DPA) | ✅ (standard DPA) | ✅ (standard DPA) | ✅ (standard DPA) | ❌ (trains on data) | ✅ |
| Confidential | ✅ only with zero-retention DPA, erasure capability, and client consent recorded | ✅ only with zero-retention DPA, erasure capability, and client consent recorded | ✅ only with zero-retention DPA, erasure capability, and client consent recorded | ✅ only with zero-retention DPA, erasure capability, and client consent recorded | ✅ only with zero-retention DPA, erasure capability, and client consent recorded | ❌ | ✅ |
| Secret | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **ONLY** |

**This matrix must be validated by each adopting organization against current vendor DPAs.** Vendors update terms; a ✅ here is an architectural position, not a legal warranty. Legal review (per Appendix B of `OPERATING_MODEL.md`) verifies the per-vendor, per-tier status every 6 months.

---

## Classification Log Template

Each classification decision is logged. Minimum fields:

| Field | Purpose | Example |
|---|---|---|
| **Log ID** | Unique identifier | `CLS-2026-04-0142` |
| **Item description** | What was classified (not the content itself) | "Meeting notes 2026-04-17 — Client Treasury, settlement detection review" |
| **Classifier** | Person making the decision (Steward, engineer, or delegated) | `lukasz.krysik` |
| **Classification date** | When the decision was made | `2026-04-19` |
| **Assigned tier** | Public / Internal / Confidential / Secret | `Confidential` |
| **Routing destination** | Where the item is allowed to go | `Cockpit; Claude Enterprise (zero-retention)` |
| **Legal basis** (for PII) | Consent / Contract / Legitimate Interest / Legal Obligation | `Contract with <Client> — DPA §4.2` |
| **Client consent reference** (Confidential+) | Contract clause or email ID | `Contract §7.3; email from client business owner 2026-04-12` |
| **Provenance marker** | Tag propagated with downstream artifacts | `[CONF-0142]` |
| **Review due date** | When re-classification is triggered | `2026-10-19` (6 months) or `on project close` |
| **Notes** | Ambiguity, dispute, escalation trail | "Initially Internal — upgraded after review surfaced stakeholder emails in body" |

The log lives in a controlled location (`.ai/classification_log/YYYY-MM.md` or equivalent secure system). The log itself is **Confidential** — it references items but does not contain their content.

---

## Edge Cases and Common Errors

### "I'm not sure, I'll just run it through AI and decide after"

This is the failure mode Stage 0 exists to prevent. Once Confidential+ material has been sent to an AI system, its exposure is (for practical purposes) irreversible even if the session ends. Classification happens **before** AI processing, not after.

### "This document is mixed — some parts are Public, some are Confidential"

Split the document. Extract the sensitive portions into separate items, classify each. Route each to its appropriate tier. The combined document's classification is the highest tier of any portion.

### "The client said it's fine to use AI on this"

Client consent is necessary but not sufficient. Consent authorizes Confidential routing; it does not promote the item to a less-restrictive tier. Record the consent (email, contract clause) in the log entry — the tier does not change.

### "This is a public press release but references ongoing negotiations"

The press release itself is Public. References to ongoing, non-public negotiations are Internal or Confidential depending on sensitivity. Keep them separate in AI workflows; do not bundle.

### "Memory from last session has old client data in it"

Memory content is subject to the same Rubric. At memory write time, the content was classified. At retention expiry (per §5.6 of the Framework), the content is archived or deleted. If the Rubric has been updated since the write, re-classification is triggered during the next audit.

### "A new item arrives that doesn't fit any tier cleanly"

Escalate to a Framework Steward. Document the ambiguity. The Steward's decision updates this Rubric if the case is general; remains a log annotation if it is specific.

---

## Escalation and Dispute Resolution

**Ambiguous classifications** — default to the more restrictive tier; escalate to a Framework Steward for formal decision. Steward resolution is logged; if the case is general, the Rubric is updated with an example.

**Client challenges to a classification** — documented in the log. If the client requests downgrade, the Steward reviews against the Rubric criteria; downgrade is permitted only when criteria support it, not on request alone.

**Re-classification of historical items** — when the Rubric is updated, existing items in active memory and Cockpit are reviewed against the new criteria at the next quarterly audit. Items whose tier changes are re-routed; items whose tier upgrades to Secret are erased from AI systems and flagged in the incident log.

**Detected mis-classification** (post-exposure) — trigger §5.6 PII-findings protocol: erasure where technically possible, incident log entry, client notification if contractually required, review of root cause (why did it pass the initial gate?). Feeds framework changelog.

---

## Relationship to Other Framework Elements

- **Operational Contract (`.ai/CONTRACT.md`):** the Rubric operates *before* the Contract. An item that fails Stage 0 never reaches the stage where the Contract applies.
- **Memory System:** every memory write is a classification event. Memory content inherits the tier of its source material plus any new sensitivity introduced by the writing context.
- **Solutioning Cockpit:** Cockpit content is classified on entry. The Cockpit tool must be configured to reject Secret-tier material and warn on Confidential-tier material without recorded consent.
- **§5.6 Data Handling Requirements:** retention, PII scanning, and erasure apply per tier — Confidential items have shorter retention defaults than Internal, Secret items are not in AI-accessible storage at all.
- **Appendix C — Regulatory Alignment:** the Rubric's legal basis field is the operational link to GDPR Art. 6 and EU AI Act Art. 10 data governance obligations.

---

## Governance of This Rubric

- **Owners:** Framework Stewards (shared; Lead Steward responsible each quarter)
- **Review cadence:** quarterly (alongside the framework adoption audit); additionally on any regulatory change identified during the 6-month legal review
- **Change process:** Rubric changes follow the framework change process — observed evidence, Lead Steward plus one peer sign-off, logged in the changelog below
- **Audit artifact:** the classification log is the primary audit artifact; random samples are reviewed in each quarterly audit

### Changelog

- **v1.0 (2026-04-19)** — Initial version. Four tiers with operational definitions, classification decision tree, routing matrix across major AI vendors, log template with 11 required fields, edge-case handling, escalation procedures. Created as CGAID artifact #10 in support of Stage 0 Data Classification Gate (see `OPERATING_MODEL.md` §2).

---

## Disclaimer

This Rubric is an operational instrument. It is not legal advice. For any engagement where regulatory, contractual, or jurisdictional requirements may diverge from the four-tier scheme, qualified legal counsel must review the applicable requirements and either (a) confirm the Rubric applies, or (b) produce an engagement-specific extension.

Vendor routing capabilities change. A tier's ✅ or ❌ in the Routing Matrix reflects the architectural position as of v1.0; the 6-month legal/regulatory review verifies current vendor terms and updates the Matrix accordingly.

---

*End of Rubric v1.0.*

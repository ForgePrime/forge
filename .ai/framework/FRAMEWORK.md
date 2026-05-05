# CGAID — Contract-Governed AI Delivery

**A Framework for Industrializing AI-Assisted Software Delivery**

Index · Version 2.0 · 2026-04-19

---

## What CGAID Is

Contract-Governed AI Delivery (CGAID) is an **operating model for software delivery in which AI is a co-producer under contract** — not an assistant, not a tool. It combines spec-driven, test-driven, and business-driven development with a formal AI operational contract, custom tooling, and enforced verification into a single reproducible discipline.

This document is the **index**. The framework lives in six documents, each with one audience and one job.

---

## The Six Documents

### 📜 [MANIFEST.md](MANIFEST.md) — The Cultural Foundation

*Audience: everyone. Read first. Print it out.*

Ten principles, three operational rules, one Definition of Done. What is true and what is required. Roughly one page. This is the document that goes on the wall, into onboarding, into the shared vocabulary.

> **Core thesis:** *AI will write our code. We decide under what discipline it operates.*

### 📊 [WHITEPAPER.md](WHITEPAPER.md) — The Public Case

*Audience: management, sponsors, clients, sales. Read when presenting.*

Why this matters now. The industry crisis with cited data (Stack Overflow, Sonar, Veracode, Apiiro, McKinsey, DORA). The six named pathologies of ungoverned AI delivery. The economic reframing — why cost structures have fundamentally changed. The gap in the market and the Linux Kernel precedent. Deck-ready signature statements.

### ⚙️ [OPERATING_MODEL.md](OPERATING_MODEL.md) — The Operational Detail

*Audience: engineering, Framework Stewards, adoption teams. Read when working.*

How the framework runs day to day. Four layers (Principles / Tooling / Delivery / Control). Stage 0 gate plus four delivery stages with entry/exit criteria. Ten standardized artifacts. The AI operational contract (7 disclosure behaviors, 3 epistemic states). Seven metrics with explicit collection playbooks and honest infrastructure gaps. Data handling requirements. Enforceability properties. 90-day adoption path. 12–24 month horizon. Kill criteria for when the framework should be abandoned. Governance with three rotating Stewards. Regulatory alignment notes (EU AI Act, GDPR, sectoral).

### 🛠️ [REFERENCE_PROCEDURE.md](REFERENCE_PROCEDURE.md) — The Procedural Layer

*Audience: every contributor executing CGAID work. Read when starting a task.*

The procedural twin of OPERATING_MODEL. Where OPERATING_MODEL describes WHAT must hold (layers, stages, artifacts, metrics), REFERENCE_PROCEDURE describes HOW work executes step by step. Procedural Cards keyed by `(task_type, ceremony_level)`. Six action types — `direct_skill`, `meta_prompt`, `opinion_prime`, `theorem_check`, `rubric_check`, `risk_probe`. `evidence_obligation` schema with T1/T2/T3 tier system. Six auditable invariant rules. Implementation-agnostic — executable by human, by Forge, or by alternative tooling. Routing entry point: `/forge` skill. Adopted via `platform/docs/decisions/ADR-029`.

### 📋 [DATA_CLASSIFICATION.md](DATA_CLASSIFICATION.md) — The Stage 0 Instrument

*Audience: Framework Stewards, classifiers, legal. Read when material enters the pipeline.*

The operational instrument of Stage 0. Four tiers (Public / Internal / Confidential / Secret). Decision tree. Routing matrix across major AI vendors. Log template with 11 required fields. Edge cases, escalation, dispute resolution.

### 🔍 [PRACTICE_SURVEY.md](PRACTICE_SURVEY.md) — The Empirical Foundation

*Audience: Framework Stewards, methodology reviewers, external auditors. Read when challenged.*

The framework is not extrapolation from opinion — it is retrofit analysis of real practice. Actual delivery work, each classified against the ten principles. Four framework gaps identified for v1.5. Honest negatives reported. The evidentiary spine against the claim that this framework is theoretical.

---

## How They Relate

```
┌───────────────────────────────────────────────────────────────┐
│                        MANIFEST.md                             │
│              (What is true. What is required.)                 │
│              Ten principles. One page. Cultural.               │
└─────────────────────────┬─────────────────────────────────────┘
                          │ grounded in real practice
                          ▼
                 ┌──────────────────────┐
                 │ PRACTICE_SURVEY.md   │
                 │ (Empirical evidence) │
                 └──────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────────────┐
│  WHITEPAPER.md   │ │ OPERATING_MODEL │ │ DATA_CLASSIFICATION  │
│  (Why now.       │ │ .md             │ │ .md                  │
│   Industry case. │ │ (How it runs.   │ │ (Stage 0 instrument) │
│   Sales.)        │ │  Engineering.)  │ │                      │
└──────────────────┘ └────────┬────────┘ └──────────────────────┘
                              │ procedural extension
                              ▼
                     ┌────────────────────────┐
                     │ REFERENCE_PROCEDURE.md │
                     │ (Step-by-step skill —  │
                     │  6 action types,       │
                     │  T1/T2/T3 evidence,    │
                     │  6 invariant rules)    │
                     └────────────────────────┘
```

Also referenced throughout:

- **`.ai/CONTRACT.md`** — the AI Operational Contract itself. Source of the 7 disclosure behaviors and 3 epistemic states.
- **`.ai/standards.md`** — Engineering standards orthogonal to CGAID (Firestore / BigQuery / React / testing conventions).
- **`.ai/PROJECT_PLAN.md`** — project-specific project context (modules, business rules).

---

## Reading Order

| If you are… | Read first | Then | Then |
|---|---|---|---|
| Engineer about to execute a task | **REFERENCE_PROCEDURE** | OPERATING_MODEL §7 (Adaptive Rigor) | CONTRACT.md |
| New team member onboarding | MANIFEST | OPERATING_MODEL §1–2 | DATA_CLASSIFICATION |
| Management / sponsor | WHITEPAPER | MANIFEST | OPERATING_MODEL §10 (Kill Criteria) |
| Framework Steward | OPERATING_MODEL (full) | DATA_CLASSIFICATION | PRACTICE_SURVEY |
| External reviewer / auditor | PRACTICE_SURVEY | MANIFEST | OPERATING_MODEL (full) |
| Client / adopting organization | WHITEPAPER | MANIFEST | OPERATING_MODEL §8 (Adoption Path) |

---

## Version Trail

This document (FRAMEWORK.md) was previously a single ~700-line document containing the whitepaper, operating model, appendices, and signature statements. It is preserved at this file path as an index to maintain stable URLs and git history continuity.

### Pre-refactor history (FRAMEWORK.md v1.0 – v1.4)

- **v1.0 (2026-04-19)** — Initial published version. Four layers, four stages, nine artifacts, seven disclosure behaviors, three epistemic states, seven metrics, three-horizon roadmap.
- **v1.1 (2026-04-19)** — Hero manifesto section added ("We do not X. We do Y." format). Six pathologies of ungoverned AI delivery formalized and cited. Economic reframing section added. Linux Kernel 2026 AI policy incorporated as the legal and organizational anchor. McKinsey, Thoughtworks, Stack Overflow, and Sonar citations verified and integrated. Deck-ready slide texts added.
- **v1.2 (2026-04-19)** — Calibration pass following `deep-verify` audit. Metric thresholds 2 & 3 converted from fixed ratios (10:1, 20:1) to baseline-driven quarterly review. Metric 5 (skill changes) given operational definition via defect/rework rate over 30-day window. Section 6 enforceability softened from "satisfies" to "is designed to satisfy" with empirical validation path stated. Section 7 90-day projection softened from "has" to "is positioned to have." Section 3 "execution is now cheap" nuanced to distinguish generation cost from validation/integration/maintenance cost, with domain caveats. Section 2.3 "AI sprawl" sourcing softened from "even mature organizations report" to "increasingly referenced in industry commentary." Section 1.3 Forrester figure annotated with secondary-source disclosure.
- **v1.3 (2026-04-19)** — Production-hardening pass following `deep-risk` audit. Top operational risks identified: framework maintainer dependency (R-CHAMPION, composite 29), client IP exposure (R-CLIENT-IP, composite 27, R=5 irreversible), EU AI Act alignment (R-EUACT, composite 25), GDPR obligations (R-GDPR, composite 25), framework theater and erosion (R-THEATER/R-EROSION, composite 23–24). Four non-negotiable additions: Stage 0 Data Classification Gate, three Framework Stewards with rotating Lead, Appendix C Regulatory Alignment Notes with 6-month legal review cadence, §5.6 Data Handling Requirements. Operational additions: quarterly adoption audit, changelog-with-evidence change-process rule, annual external peer review. Standardized artifact count updated from nine to ten with addition of Data Classification Rubric (artifact #10).
- **v1.4 (2026-04-19)** — Blocker-clearance pass following methodological review (self-conducted as acknowledged conflict of interest). Four T1 blockers addressed: Practice Survey created, Stage 0 honesty statement added, Metric Infrastructure Playbook expanded, Kill Criteria section introduced.

### Refactor

- **v2.0 (2026-04-19)** — Architecture refactor. Single 700-line FRAMEWORK.md split into four audience-specific documents (MANIFEST, WHITEPAPER, OPERATING_MODEL, DATA_CLASSIFICATION) plus PRACTICE_SURVEY as empirical foundation. This file becomes a slim index preserving URL and git-history continuity. No content deleted — redistributed. Operational history continues in OPERATING_MODEL.md changelog.

---

## Status

**CGAID v2.0** is the current form of the framework. All active work references MANIFEST (culture), OPERATING_MODEL (operations), DATA_CLASSIFICATION (Stage 0), PRACTICE_SURVEY (evidence), WHITEPAPER (public case). This index is updated only when the document set itself changes (new document added, document retired, renamed).

Framework Stewards Engineering. Contact: `lukasz.krysik`.

---

*End of Index.*

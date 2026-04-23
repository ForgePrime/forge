# CGAID — Contract-Governed AI Delivery

**A Framework for Industrializing AI-Assisted Software Delivery**

Index · Version 2.0 · 2026-04-19

---

## What CGAID Is

Contract-Governed AI Delivery (CGAID) is an **operating model for software delivery in which AI is a co-producer under contract** — not an assistant, not a tool. It combines spec-driven, test-driven, and business-driven development with a formal AI operational contract, custom tooling, and enforced verification into a single reproducible discipline.

This document is the **index**. The framework lives in five documents, each with one audience and one job.

---

## The Five Documents

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

### 📋 [DATA_CLASSIFICATION.md](DATA_CLASSIFICATION.md) — The Stage 0 Instrument

*Audience: Framework Stewards, classifiers, legal. Read when material enters the pipeline.*

The operational instrument of Stage 0. Four tiers (Public / Internal / Confidential / Secret). Decision tree. Routing matrix across major AI vendors. Log template with 11 required fields. Edge cases, escalation, dispute resolution.

### 🔍 [PRACTICE_SURVEY.md](PRACTICE_SURVEY.md) — The Empirical Foundation

*Audience: Framework Stewards, methodology reviewers, external auditors. Read when challenged.*

The framework is not extrapolation from opinion — it is retrofit analysis of real practice. Eighteen incidents from actual delivery work, each classified against the ten principles. Four framework gaps identified for v1.5. Honest negatives reported. The evidentiary spine against the claim that this framework is theoretical.

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
└──────────────────┘ └─────────────────┘ └──────────────────────┘
```

Also referenced throughout:

- **`.ai/CONTRACT.md`** — the AI Operational Contract itself. Source of the 7 disclosure behaviors and 3 epistemic states.
- **`.ai/standards.md`** — Engineering standards orthogonal to CGAID (Firestore / BigQuery / React / testing conventions).
- **`.ai/PROJECT_PLAN.md`** —  project context (modules, business rules).

---

## Reading Order

| If you are… | Read first | Then | Then |
|---|---|---|---|
| New team member onboarding | MANIFEST | OPERATING_MODEL §1–2 | DATA_CLASSIFICATION |
| Management / sponsor | WHITEPAPER | MANIFEST | OPERATING_MODEL §10 (Kill Criteria) |
| Framework Steward | OPERATING_MODEL (full) | DATA_CLASSIFICATION | PRACTICE_SURVEY |
| External reviewer / auditor | PRACTICE_SURVEY | MANIFEST | OPERATING_MODEL (full) |
| Client / adopting organization | WHITEPAPER | MANIFEST | OPERATING_MODEL §8 (Adoption Path) |

---

## Version Trail

This document (FRAMEWORK.md) was previously a single ~700-line document containing the whitepaper, operating model, appendices, and signature statements. It is preserved at this file path as an index to maintain stable URLs and git history continuity.


### Refactor

- **v2.0 (2026-04-19)** — Architecture refactor. Single 700-line FRAMEWORK.md split into four audience-specific documents (MANIFEST, WHITEPAPER, OPERATING_MODEL, DATA_CLASSIFICATION) plus PRACTICE_SURVEY as empirical foundation. This file becomes a slim index preserving URL and git-history continuity. No content deleted — redistributed. Operational history continues in OPERATING_MODEL.md changelog.

---

## Status

**CGAID v2.0** is the current form of the framework. All active work references MANIFEST (culture), OPERATING_MODEL (operations), DATA_CLASSIFICATION (Stage 0), PRACTICE_SURVEY (evidence), WHITEPAPER (public case). This index is updated only when the document set itself changes (new document added, document retired, renamed).


---

*End of Index.*

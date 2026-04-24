# PRODUCT_VISION.md — Forge Product Strategy

> **Status:** DRAFT — pending distinct-actor review per ADR-003.
> **Parent:** MASTER_IMPLEMENTATION_PLAN.md.

## 1. One-line pitch

Forge is the AI coding platform that produces **audit-ready evidence trails** for every code change, built for teams where compliance and correctness matter more than speed.

## 2. Who Forge is for (ICP — Ideal Customer Profile)

### Primary ICP (Tier 1 — paying customer day 1)

**Regulated-industry backend engineering teams:** fintech, healthtech, govtech, insuretech, energy trading, telecom billing.

Company profile:
- 20-200 engineers
- Ships software under regulatory scrutiny (PCI-DSS, HIPAA, SOC2, SOX, GDPR with significant PII volume)
- Already has compliance team + external audits
- Dev velocity bottlenecked by compliance requirements (every PR requires manual review, traceability docs, test evidence)
- Current pain: 30-50% of eng time goes to compliance overhead, not features

Buyer persona: VP Engineering or Director of Platform, champion = Security/Compliance Lead.

### Secondary ICP (Tier 2 — expansion targets post-MVP)

**AI-first SaaS teams** (scale-ups, Series B+) that deploy AI features themselves and therefore face:
- AI system auditability demands from enterprise customers
- Own AI evaluation + safety procedures
- Need to document why AI-generated code is trustworthy

**Platform teams at large enterprises** not directly regulated but internally require rigorous code-change governance (e.g., big banks' non-consumer-facing teams, research labs).

### Who Forge is NOT for (explicitly excluded)

- Individual developers / hobbyists — overhead too high, no compliance pressure
- Move-fast-break-things startups — governance friction conflicts with velocity-first culture
- Teams that reject AI coding tools on principle
- Non-engineering domains (marketing, product, design)

## 3. Value proposition

### The core insight

Every existing AI coding tool optimizes for **developer productivity** (write more code faster). None optimize for **compliance-grade traceability** (prove code is correct + auditable + built on evidence).

**Forge trades 10-20% velocity for 80% reduction in compliance-review time** because the evidence the auditor needs is generated automatically during development, not reconstructed afterwards.

### Concrete value delivered

**For the developer:**
- Receives fully-structured Task (Objective + AC + evidence + test spec) instead of ambiguous ticket
- Proposed code change comes with: rationale, alternatives considered, test cases, evidence of correctness
- PR already has half the audit materials prepared — just review + merge

**For the compliance lead:**
- Every code change has verifiable evidence trail (10-link causal chain: documents → finding → objective → task → AC → test → execution → decision → change → runtime evidence)
- Change reversibility classified + rollback path documented
- Audit report generator produces regulator-ready artifacts from live data

**For the VP Eng / Director:**
- Governance overhead drops from manual to automated
- Evidence quality improves (consistent discipline, not reviewer-dependent)
- New engineers onboard faster (process is explicit, not tribal knowledge)

## 4. Positioning vs competitors

### vs Cursor / GitHub Copilot / Zed AI

**They are:** AI pair-programmers — autocomplete, inline suggestions, natural-language-to-code.
**They optimize for:** typing speed, cognitive load during coding.
**They lack:** structured governance, evidence trail, compliance-ready output.

**Forge is complementary, not replacement.** Developer still uses Cursor for local coding. Forge governs the Task-to-PR workflow around the Cursor-aided edits.

### vs Devin / Cognition / Magnetic

**They are:** autonomous AI engineers — "give a task, AI writes code, opens PR".
**They optimize for:** autonomy, breadth of task types.
**They lack:** structured evidence, compliance discipline, distinct-actor verification, cross-stage soundness.

**Forge is the "governance wrapper" around autonomous AI.** If Devin is the engineer, Forge is the company's SDLC process + compliance infrastructure the engineer works inside.

Design-partner story: "We want our team's AI engineer (Devin-like) to produce audit-ready work. Forge is the layer on top."

### vs Aider / Continue.dev / Pearl

**They are:** CLI-based AI coding tools for local dev.
**They optimize for:** flexibility, developer control, local-first.
**They lack:** organizational discipline, multi-actor governance, audit trail.

**Forge overlaps minimally** — different audience (individual dev vs team process).

### vs "build your own" (OpenAI Agents SDK + custom infrastructure)

**They offer:** primitives to build agents, no out-of-box governance.
**They lack:** 58 stages of proven governance discipline, 27 ADRs codifying tradeoffs, integration with regulatory frameworks.

**Forge is the "Stripe for AI-coding governance"** — don't build it yourself, buy the proven layer.

## 5. Use case scenarios (concrete)

### Scenario A — Healthtech patient-data pipeline

**Company:** Series C healthtech, 80 engineers, handles 10M patient records, HIPAA-compliant.

**Pain:** Every code change touching patient-data pipeline requires:
- Threat model review (security team)
- HIPAA impact assessment (compliance)
- Rollback plan documentation
- Test evidence including PII-adjacent edge cases
- Traceability from change to originating requirement

Current flow: 2-5 business days per change for compliance review.

**With Forge:**
- Requirement from Jira ticket → Forge auto-extracts actors (patients, clinicians, admin), processes (data ingestion, query, export)
- Tasks decomposed with AC explicitly covering security edge cases (per ADR-001 9-value scenario_type including `security`)
- Proposed Change has structured Decision with threat-model reasoning as rationale
- Runtime verification records baseline/post diff with patient-data access patterns unchanged
- Audit trail generator produces HIPAA-compliance-ready documentation in minutes

Compliance review drops from 3 days to 30 minutes per change.

### Scenario B — Fintech payment processor

**Company:** Series B fintech, 40 engineers, PCI-DSS Level 1, $500M GMV.

**Pain:** Every payment-path code change is Critical tier:
- Steward (VP Eng) must sign off
- Dual control on approvals
- Documented rationale for chosen implementation vs alternatives
- Reversibility plan tested

**With Forge:**
- ADR-007 Steward role formalized + signed-off on every Critical Decision
- F.11 CandidateSolutionEvaluation forces ≥ 2 candidates with 14-dim Score — Steward reviews the argmax selection
- ADR-012 distinct-actor check enforced: challenger must be different model + different session
- G.10 BaselinePostVerification auto-rollback on diff mismatch
- Every change ships with reversibility classification + tested rollback_ref

Dual-control workflow reduces from 2-day ceremony to hours.

### Scenario C — Govtech benefits system

**Company:** Government contractor, 30 engineers, operates benefits eligibility platform for state agency.

**Pain:**
- FISMA compliance
- State audit every 6 months
- Every change requires full traceability from regulation text → requirement → test
- Team turnover causes institutional knowledge loss

**With Forge:**
- Knowledge layer captures regulation text with source_ref
- Requirements (Finding.type='requirement') link to regulation via actor_refs + process_refs + business_justification (ADR-025 + AI-SDLC #8 closure)
- Every code change traceable to regulation section
- G.9 proof-trail audit runs nightly — auto-flags regulations without implementing Changes
- Institutional knowledge persists in structured Knowledge entities, not tribal memory

Audit preparation time drops from 2 weeks to 2 days.

### Scenario D — Enterprise platform team

**Company:** Fortune 500 retailer, internal platform team of 50 engineers, serves 2000 downstream dev teams.

**Pain:**
- Platform changes affect thousands of consumers
- Cross-team review expensive
- Impact analysis ad-hoc
- Rollback decisions taken under time pressure

**With Forge:**
- ImpactClosure (C.3) computes full blast radius per platform change
- ErrorPropagationMechanism (ADR-024 / G.11) auto-cascades invalidation through dependent consumer teams
- C.4 Reversibility classification mandatory pre-merge
- Architecture components (ADR-026 / E.9) maintain living architecture doc

Platform change risk drops measurably; mean-time-to-detect-impact drops from hours to minutes.

### Scenario E — Open-source project with compliance dependents

**Project:** OSS database or crypto library used by regulated-industry customers.

**Pain:**
- PRs from community contributors
- Maintainers struggle to assess compliance impact of each PR
- Downstream customers need audit-ready changelogs

**With Forge:**
- Forge integrates with GitHub PR flow
- Every community PR triggers Forge analysis: impact closure, AC coverage, security scenario tests
- Output: structured PR body with evidence trail
- Maintainers approve with context, not just code diff

Not primary ICP but potential open-source adoption driver.

## 6. Pricing model (framework)

### Tier 1: Starter (free, MVP-era only)

- Single project
- Up to 50 Executions / month
- GitHub integration only
- Community support

**Purpose:** design-partner acquisition, product-market-fit discovery.

### Tier 2: Team ($X/engineer/month, post-MVP)

- Up to 10 projects
- Unlimited Executions within budget guardrails
- All integrations (GitHub/GitLab/Jira/Linear/Slack)
- Dashboard for team
- Steward role support
- Community + email support

Target: $150-300/engineer/month (anchor: compliance tools like Drata are $50-100/user + value of 1 FTE saved on compliance overhead).

### Tier 3: Enterprise (custom, post-PMF)

- Unlimited projects
- Self-hosted option
- SSO / SAML
- Custom integrations
- On-prem deployment
- Dedicated Steward advisor (consulting)
- SLA + priority support
- Compliance framework mapping (HIPAA / PCI / FedRAMP / ISO27001 templates)

Target: $100k-1M ARR per enterprise customer.

### Usage-based add-ons

- LLM call costs pass-through (transparent)
- Budget guardrails per Project
- Cost attribution dashboard

## 7. Go-to-market (GTM) sequence

### Stage 1 (MVP + Phase 1-2): Design partners

- 5-10 design-partner customers from direct network
- Free or heavy-discount in exchange for:
  - 2-week weekly feedback interviews
  - Case study rights
  - Logo use
- Acquisition: founder-led, from existing relationships in regulated-industry networks

### Stage 2 (Phase 3-4): Paid pilot program

- 20-30 paid pilot customers
- Tier 2 pricing, quarterly commitment
- Activation metric: ≥ 10 Changes shipped through Forge per customer in first quarter
- Retention: after Q1, discussion of Tier 3 Enterprise upgrade

### Stage 3 (post-launch): Inbound + partnerships

- Content: "Compliance-grade AI coding" thought leadership (conferences: StrictlyVC, HIMSS, Money20/20)
- Partnerships: integrations with:
  - Drata (compliance automation) — cross-sell
  - Snyk (security) — embedded scan results in Forge evidence
  - GitLab Enterprise — native extension
  - Big 4 consulting (compliance advisory — Forge as recommended tooling)

## 8. North star metric

**Compliance-ready Changes shipped per week per customer.**

Why:
- Captures both velocity AND compliance discipline (unlike alternatives: "PRs merged" ignores compliance, "audits passed" is too retrospective)
- Directly tied to customer value (replaces manual compliance work)
- Increases as adoption deepens within customer

Secondary metrics:
- Cost per Change (descending — Forge optimization effective)
- Quality score trend (ascending — LLM + governance learning)
- Customer NPS (target > 40)
- Gross margin (target > 70% at Tier 3 pricing)

## 9. Competitive moat

**Not the AI model** — anyone can use Claude/GPT.

**Not the coding assistant** — Cursor is well-capitalized.

**The moat:**
1. **Theorem-proven governance framework** (8 theorems composed, 58 stages, 27 ADRs) — impossible for competitor to replicate quickly without similar multi-year investment
2. **Compliance framework library** (growing mapping from HIPAA/PCI/GDPR/SOC2 to Forge stages) — network effect as customers contribute mappings
3. **Evidence trail data moat** — aggregated (anonymized) Change + Finding data becomes training signal for quality prediction models
4. **Steward network** — certified Forge Stewards as human-in-loop experts; hard to recreate

**Threats to moat:**
- GitHub / GitLab building native governance features — probable medium-term; Forge must either integrate as premium layer or establish multi-repo cross-cutting position
- Regulatory changes making current compliance framework obsolete — ongoing maintenance cost
- LLM providers (OpenAI / Anthropic) building vertical compliance products — less likely given platform vs application distinction

## 10. Key strategic questions (open)

1. **Build alone vs fund raised?** Current: solo-with-AI-pair. Decision point after Phase 1 MVP: if strong customer signal, raise seed; else extend bootstrapping.

2. **Open-source components?** Consider open-sourcing L1 governance layer (theorem framework) to establish thought leadership + community contribution; keep L2-L7 proprietary.

3. **Self-hosted vs SaaS?** MVP is SaaS; enterprise Tier 3 requires self-hosted option. Decision point Phase 3: architecture refactor for self-hosted or wait for clear enterprise pull.

4. **Vertical specialization?** Start general in regulated industries, or pick 1 vertical (fintech or healthtech) and dominate? Leaning: start general, specialize based on design-partner fit patterns.

5. **Build proprietary LLM evals vs buy tooling?** L7 Quality can be built or bought (Braintrust, Weights & Biases). MVP: build minimal; post-PMF: evaluate buy-vs-build.

## 11. Success indicators (phase-gated)

### After MVP (Phase 1 end)
- 1 real paying design-partner
- 10 real Changes shipped through Forge
- Benchmark score ≥ 0.7

### After Phase 2 (horizontal expansion)
- 5 paying customers
- $50k ARR
- 100 Changes/week aggregate
- 2 compliance-framework mappings validated by customer audit

### After Phase 3 (depth)
- 20 paying customers
- $500k ARR
- 1 customer case study with regulator acceptance
- 0 P0 data incidents

### After Phase 4 (production-ready)
- 50 paying customers
- $2M ARR
- Enterprise Tier 3 contracts signed
- Profitable unit economics at Tier 2

## 12. Authorship + versioning

- v1 (2026-04-24) — initial product vision + ICP + competitive positioning + GTM framework + north star.
- Updates post-design-partner feedback likely after MVP.

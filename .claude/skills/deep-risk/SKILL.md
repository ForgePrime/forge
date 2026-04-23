---
name: deep-risk
id: SKILL-DEEP-RISK
description: >
  Use when user asks about risks, what could go wrong, threat assessment, or
  risk analysis. Triggers: "what are the risks", "what could go wrong",
  "risk assessment", "threat analysis", "how risky is this".
version: "1.0.0"
allowed-tools: [Read, Glob, Grep, WebSearch]
---

> **Provenance**: Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-risk` v1.0.0.
> Forge integration: findings recorded as Forge decisions/lessons. See Forge Integration section below.

# Deep Risk

5-dimensional risk scoring with cascade analysis and Cobra Effect checking.

## What This Adds (Beyond Native Capability)

- 5D scoring: probability, impact, velocity, detectability, reversibility
- Cascade/interaction mapping between risks (risks that amplify each other)
- Cobra Effect check: does the mitigation create or worsen other risks?
- Explicit risk vs uncertainty distinction

## Procedure

### Step 1: Context

Establish scope before identifying risks.

**Output Step 1 (required before proceeding):**

```
- Subject: [what is being assessed]
- Boundary in: [what's in scope]
- Boundary out: [what's explicitly excluded]
- Stakes: [what's at risk — data, money, users, operations]
- Horizon: [time frame]
```

Write this explicitly. Without it, "Not Assessed" in the output is incomplete — unclear whether omissions were intentional or oversight.

### Step 2: Identify

Find risks through multiple lenses:

| Lens | Ask |
|------|-----|
| Technical | What can break, fail, or not work as expected? |
| Organizational | What people/process/politics risks exist? |
| Temporal | What risks emerge over time or from timing? |
| Dependency | What do we depend on that could fail? |
| Knowledge | What don't we know that could hurt us? |
| Financial/Compliance | What regulatory or data accuracy risks exist? (BQ data loss, wrong settlement, GDPR) |
| Integration | What if an external system (Warsaw data feed, Apigee, bank) changes format or goes down? |

For each risk: assign a short name, description, and category.

Distinguish **risks** (known probability distribution) from **uncertainties**
(unknown probability — we don't even know the shape of the problem).

### Step 3: Score (5 Dimensions)

Score each risk on 5 dimensions (1-5 scale). See `references/scoring.md` for
detailed rubrics.

| Dimension | What It Measures |
|-----------|-----------------|
| Probability (P) | How likely is this to occur? |
| Impact (I) | How bad is it if it occurs? |
| Velocity (V) | How fast does it hit? (1=slow onset, 5=instant) |
| Detectability (D) | How hard to detect early? (1=obvious, 5=invisible) |
| Reversibility (R) | How hard to undo? (1=easily reversed, 5=permanent) |

**Composite score** = (P x I) + V + D + R

This weights probability-impact as the core, with velocity, detectability,
and reversibility as aggravating factors.

**ITRP calibration** (financial data / production system — conservative thresholds):
- 3-8: Monitor (low risk)
- 9-12: Plan mitigation
- 13+: Prioritize / escalate
- **Any R=5 (irreversible) risk requires explicit approval regardless of composite score.**

### Step 4: Interact

Map risk interactions:

- Which risks **amplify** each other? (Risk A makes Risk B more likely or worse)
- Which risks **cascade**? (Risk A triggers Risk B)
- Which risks **share root causes**? (fixing one fixes another)

For each proposed mitigation, run a **Cobra Effect check**:
> "If we implement this mitigation, does it create a new risk or amplify
> an existing one?"

Named after the colonial bounty on cobras that led to cobra farming — the fix
made the problem worse.

### Step 5: Report

Compile the full risk assessment using the output format below.

## Output Format

```
# Risk Assessment: {subject}
Scope: {what's assessed} | Horizon: {time frame}

## Risk Register
  | # | Risk | P | I | V | D | R | Composite | Category |
  |---|------|---|---|---|---|---|-----------|----------|

## Top 5 Risks (by composite score)
  ### 1. {Risk Name} — Composite: {score}
  Description: {what happens}
  Why it ranks high: {which dimensions drive the score}
  Mitigation: {what to do about it}

## Risk Interactions
  | Risk A | Risk B | Type | Mechanism | Cascade? |
  |--------|--------|------|-----------|----------|
  Types: AMPLIFIES / TRIGGERS / SHARES_ROOT / MASKS

## Mitigations + Cobra Effect Check
  | Mitigation | Fixes | Could Cause/Amplify | Cobra? |
  |------------|-------|---------------------|--------|

## Uncertainties (distinct from risks)
  {things where we don't even know the probability shape}

## Not Assessed
  - Lenses not applied: [list from Step 2 — which were skipped and why]
  - Interactions not mapped: [risk pairs not checked]
  - Assumptions about scope: [what was assumed but not verified]
```

## Counter-Checks

- [ ] Did you use all 5 identification lenses (not just technical)?
- [ ] Are velocity, detectability, and reversibility scored (not just P and I)?
- [ ] Did you check every mitigation for Cobra Effect?
- [ ] Did you separate risks from uncertainties?
- [ ] Does "Not Assessed" honestly list scope gaps?

---

## Integration with other skills

- **Input from:** `/plan` Faza 6 (initial risk identification) — use as starting point
- **Output to:** `/plan-deploy` Go/No-Go — critical risks become deployment blockers
- **High/Critical risks →** add to `/plan-deploy` Phase checklist as pre-conditions

## Provenance

Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-risk` v1.0.0. ITRP-specific additions: financial/compliance lens, integration lens, conservative calibration thresholds, MASKS interaction type.

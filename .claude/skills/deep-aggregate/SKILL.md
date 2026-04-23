---
name: deep-aggregate
id: SKILL-DEEP-AGGREGATE
description: >
  Use when user has multiple analysis outputs (risk, feasibility, architecture,
  verification) and needs a combined decision. Triggers: "combine these analyses",
  "decision brief", "GO/NO-GO", "aggregate results", "what's the overall verdict".
version: "1.0.0"
allowed-tools: [Read, Glob, Grep]
---

> **Provenance**: Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-aggregate` v1.0.0.
> Forge integration: findings recorded as Forge decisions/lessons. See Forge Integration section below.

# Deep Aggregate

Combine multiple analysis outputs into a structured GO/NO-GO decision brief.

## What This Adds

Claude already summarizes. This skill adds:
- **Structured GO/NO-GO verdict** from disparate inputs
- **Cross-process contradiction detection**: finds where analyses disagree
- **Confidence-weighted recommendations**: not all inputs are equal
- **5-10 page brief from 100+ pages**: ruthless compression with traceability

## Procedure

### Step 1: Collect

Read all available analysis outputs. Produce an inventory:

| # | Source | Type | Pages/Size | Completeness |
|---|--------|------|------------|--------------|
| 1 | risk-analysis.md | Risk Assessment | 15 pages | Full |
| 2 | feasibility.md | Feasibility Study | 8 pages | Missing cost section |
| ... | ... | ... | ... | ... |

Also list what is **missing**:
- Expected but not provided (e.g., "No security review found")
- Partially complete inputs (e.g., "Feasibility study has no cost analysis")

### Step 2: Cross-Check

Compare findings across all inputs. Look for:

**Contradictions** — where one analysis says X and another says NOT-X:
- Risk says "database is the bottleneck" but architecture says "database scales horizontally"
- Feasibility says "team can deliver in 3 months" but verification found 6 months of tech debt

**Gaps** — what no analysis addresses:
- Nobody assessed regulatory compliance
- No analysis covers the migration path

**Agreements** — where multiple analyses converge (these are high-confidence):
- Both risk and architecture flag the auth service as critical

For each contradiction, determine:
- Which source is more authoritative for this specific claim?
- Can both be true in different contexts?
- Does resolution change the verdict?

### Step 3: Synthesize

Weight each input:

| Source | Weight | Reason |
|--------|--------|--------|
| Architecture review | 0.9 | Complete, by domain expert |
| Risk analysis | 0.7 | Thorough but missing ops risks |
| Feasibility study | 0.5 | Incomplete cost section |

Classify signals:

**GO signals:**
- Technical feasibility confirmed
- Acceptable risk profile
- Team capability sufficient
- ROI positive

**NO-GO signals:**
- Unmitigated critical risks
- Technical impossibility found
- Cost exceeds budget by >2x
- Team lacks critical skills with no path to acquire

**Binding constraints** — any single one of these forces NO-GO:
- Legal/regulatory blocker
- Technical impossibility
- Unacceptable security exposure
- Budget hard cap exceeded

### Step 4: Render

Produce the decision brief.

## Output Format

```markdown
# Decision Brief: {topic}

## VERDICT: {GO | CONDITIONAL GO | NO-GO}

{2-3 sentence justification referencing the strongest evidence}

## Evidence Summary

| Source | Verdict | Confidence | Key Finding |
|--------|---------|------------|-------------|
| {name} | {GO/CAUTION/NO-GO} | {High/Med/Low} | {one sentence} |
| ... | ... | ... | ... |

## Cross-Process Contradictions

| Source A | Source B | Contradiction | Resolution |
|----------|----------|---------------|------------|
| {name} | {name} | {what conflicts} | {which is right and why} |

*If no contradictions: "No contradictions found across {N} sources."*

## Key Factors

1. **{Factor}** ({source}): {evidence and why it matters}
2. **{Factor}** ({source}): {evidence and why it matters}
3. **{Factor}** ({source}): {evidence and why it matters}
{3-5 factors, ranked by impact on verdict}

## Conditions

*For CONDITIONAL GO — what must be true to proceed:*
- [ ] {Condition 1} — {which analysis raised this}
- [ ] {Condition 2} — {which analysis raised this}

*For GO — residual risks to monitor:*
- {Risk to watch}

*For NO-GO — what would change the verdict:*
- {What would need to change}

## Unknown

{What no analysis addressed — these are blind spots:}
- {Gap 1}: no source assessed this
- {Gap 2}: partially addressed but inconclusive
```

## Rules

- Never upgrade a NO-GO signal without explicit justification
- Contradictions must be listed even if resolved — transparency matters
- Weight inputs by completeness and specificity, not by optimism
- "Unknown" section is mandatory — decision-makers need to know blind spots
- If fewer than 2 inputs are available, state that the aggregate has low confidence
- Do not add findings not present in the source analyses

---

## Integration with other skills

- **Input from:** `/deep-risk`, `/deep-explore`, `/deep-architect`, `/deep-verify` outputs
- **Output to:** `/plan` (GO → proceed to planning) or `/plan-deploy` (GO/NO-GO for deployment)

## Provenance

Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-aggregate` v1.0.0.

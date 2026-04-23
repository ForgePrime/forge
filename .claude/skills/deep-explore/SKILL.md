---
name: deep-explore
id: SKILL-DEEP-EXPLORE
description: >
  Use when user is stuck on a decision, has too many options, or needs to think
  through a problem systematically. Triggers: "should we", "what are our options",
  "I don't know what to do", "help me think through", "explore options".
version: "1.0.0"
allowed-tools: [Read, Glob, Grep, WebSearch]
---

> **Provenance**: Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-explore` v1.0.0.
> Forge integration: findings recorded as Forge decisions/lessons. See Forge Integration section below.

# Deep Explore

Structured decision exploration and knowledge expansion. Turns "I don't know
what to do" into a clear option map with consequence tracing.

## What This Adds (Beyond Native Capability)

- Structured option mapping with explicit dimensions (not just pros/cons lists)
- Consequence tracing per option: 2nd and 3rd order effects
- Knowledge audit: separating known facts from assumptions from gaps
- Decision readiness assessment: are you ready to decide, or do you need more info?

## Procedure

### Step 1: Knowledge Audit

Separate what the user actually knows from what they assume and what they don't know.

Ask or infer:
- **Known facts**: What is confirmed and evidence-based?
- **Assumptions**: What is treated as true but not verified?
- **Unknown gaps**: What information is missing that would change the decision?

Flag any assumption that, if wrong, would invalidate an option entirely.

### Step 2: Research

Fill knowledge gaps identified in Step 1.

- Use WebSearch if available and gaps are factual
- Use Read/Glob/Grep if gaps relate to existing codebase or documents
- If gaps cannot be filled now, mark them as "unresolved" for the synthesis

### Step 3: Option Map

Build a structured comparison table. Every option gets scored on the same dimensions.

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| ...    | ...         | ...   | ...      | ...         |

Include at minimum 3 options. If the user presents a binary choice, find a third
option (hybrid, phased, alternative framing).

### Step 4: Consequence Trace

For the top 2-3 options, trace consequences beyond the immediate:

- **1st order**: Direct, immediate results
- **2nd order**: What happens because of 1st order effects
- **3rd order**: What happens because of 2nd order effects

Focus on non-obvious 2nd and 3rd order effects. The obvious ones don't need tracing.

### Step 5: Challenge

For each viable option:
- What is the **strongest argument against** it?
- What would need to be **true for this to fail**?
- Who would **disagree** with this choice and why?

Do not soften the challenges. The point is to stress-test, not validate.

### Step 6: Synthesis

Assess decision readiness:
- **Ready to decide**: Recommend a path with reasoning
- **Not ready**: Specify exactly what information is needed and how to get it

Do not force a recommendation if critical unknowns remain.

## Output Format

```
# Exploration: {topic}

## Knowledge Audit
  Known: {confirmed facts}
  Unknown: {gaps that matter}
  Assumed: {beliefs treated as fact — flag if fragile}

## Options
  | Option | Requirements | Risks | Benefits | Key Unknown |
  |--------|-------------|-------|----------|-------------|

## Consequence Trace
  ### Option: {name}
  1st order: {direct effects}
  2nd order: {downstream effects}
  3rd order: {systemic effects}

## Challenge Round
  ### Option: {name}
  Strongest counter-argument: {argument}
  Failure condition: {what must be true for this to fail}

## Recommended Path
  {recommendation with reasoning}
  — or —
  NOT READY — need: {specific info required, how to get it}

## What Was NOT Explored
  {scope limitations, perspectives not considered, data not available}
```

## Counter-Checks

- [ ] Did you find at least 3 options (not just the two the user presented)?
- [ ] Are 2nd/3rd order consequences non-obvious (not just restating the benefit/risk)?
- [ ] Does the challenge section contain genuinely uncomfortable arguments?
- [ ] Is the knowledge audit honest about assumptions vs facts?
- [ ] Does "What Was NOT Explored" list real limitations?

---

## Integration with other skills

- **Output to:** `/deep-risk` (option risks), `/deep-architect` (chosen option → design), `/plan` (recommended path → implementation)

## Provenance

Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-explore` v1.0.0.

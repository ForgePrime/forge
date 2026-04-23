---
name: deep-verify
id: SKILL-DEEP-VERIFY
description: >
  Use when user asks to verify, fact-check, validate, or check correctness of
  code, documents, specs, claims, or LLM-generated artifacts. Triggers: "verify
  this", "is this correct", "check against spec", "find contradictions",
  "review this document". Do NOT use for code review (style/quality) — this is
  for logical/factual verification.
version: "1.0.0"
allowed-tools: [Read, Glob, Grep, Bash]
---

> **Provenance**: Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-verify` v1.0.0.
> Forge integration: findings recorded as Forge decisions/lessons. See Forge Integration section below.

# Deep Verify

Structured verification of artifacts (code, documents, specs, claims).
Produces scored findings with evidence, adversarial self-review, and a verdict.

## Why this exists

Claude verifies well natively. This skill adds what Claude does NOT do on its own:

1. **Numeric scoring** — findings get severity points, verdict has a threshold
2. **Mandatory counter-checks** — every serious finding gets challenged before inclusion
3. **Scope transparency** — explicit section on what was NOT checked
4. **Pattern matching** — known impossibility patterns (CAP theorem, halting problem, etc.)
5. **Standardized output** — same report format every time

## Execution Modes

| Mode | When | Depth |
|------|------|-------|
| **Quick** | Low stakes, fast answer | 1 scan pass, lighter adversarial |
| **Standard** | Default | Full scan + targeted + adversarial |
| **Deep** | High stakes, critical decisions | Everything + extended challenge |

If user doesn't specify mode, ask. If artifact is short (<100 lines), default Quick.

---

## Procedure

### Step 1 — Setup

1. Identify the artifact (file path, pasted text, URL)
2. Read the artifact fully
3. Determine mode (Quick/Standard/Deep) — ask user if unclear
4. State scope: what you WILL check and what you will NOT
5. Declare assumptions: anything you're inferring about context, domain, intent

Output:
```
SETUP
  Artifact: {path or description}
  Mode: {Quick|Standard|Deep}
  Scope: {what's in / what's out}
  Assumptions: {list}
```

### Step 2 — Scan

Extract from the artifact:
- **Core claims** — what does it promise, guarantee, or assert?
- **Key terms** — are they used consistently? Same word = same meaning?
- **Structure** — do high-level promises match low-level details?

For each, apply these three lenses:
- **First Principles**: What must be fundamentally true for each claim to work? Is it stated?
- **Vocabulary Consistency**: Same concept = same word? Same word = same meaning everywhere?
- **Abstraction Coherence**: Do goals (high) match design (mid) match implementation (low)?

Check findings against the **Pattern Library** (see `references/patterns.md`).
A pattern match significantly increases confidence in the finding.

**DO NOT assign severity yet.** This step is pure extraction.

### Step 3 — Targeted Analysis (Standard + Deep only)

Based on signals from Step 2, select 1-3 analysis methods:

| Signal | Method |
|--------|--------|
| Absolute claims ("always", "never", "100%") | Check against known theorems/impossibilities |
| Complex dependencies | Look for circular dependencies, missing links |
| Claims without evidence | Trace each claim to its supporting evidence |
| Vocabulary inconsistency | Map term meanings across sections, find contradictions |
| "Something feels off" but can't pinpoint | Invert claims (if X is true, what must also be true?) |

Now assign severity to each finding:

| Severity | Points | Meaning |
|----------|--------|---------|
| **CRITICAL** | +3 | Fatal flaw. This alone justifies rejection. Theorem violation, definitional contradiction, impossibility. |
| **IMPORTANT** | +1 | Serious issue. 2-3 of these together = rejection. Inconsistency, ungrounded claim, undefined core concept. |
| **MINOR** | +0.3 | Worth noting. Only matters if other problems exist. |

Clean method pass (found nothing): **-0.5** points.

**Every finding MUST cite exact text from the artifact.** No quote = no finding.

### Step 4 — Adversarial Self-Review

For every CRITICAL or IMPORTANT finding, answer these four challenges:

1. **Alternative Explanation** — What if the author meant something different?
2. **Hidden Context** — What unstated assumption would make this actually correct?
3. **Domain Exception** — Would a domain expert disagree with my finding?
4. **Confirmation Bias** — Would I reach the same conclusion reading in different order?

Decision:
- 0-1 challenges weaken the finding → **KEEP**
- 2-3 challenges weaken it → **DOWNGRADE** one severity level
- All 4 weaken it → **REMOVE** the finding

Then **steel-man the opposite verdict**: construct the strongest possible argument
that your current verdict is wrong. If the steel-man holds, note it in the report.

### Step 5 — Verdict

Calculate final score:

```
S = sum(finding_points) + sum(bonuses) - (clean_passes * 0.5) - adjustments
```

| Score | Verdict |
|-------|---------|
| S >= 6 | **REJECT** — artifact contains fatal flaws |
| S <= -3 | **ACCEPT** — artifact appears sound |
| -3 < S < 6 | **UNCERTAIN** — cannot determine, recommend specific follow-up |

Assign confidence: **HIGH** (|S| > 10, methods agree) / **MEDIUM** (6-10) / **LOW** (near threshold or methods disagree).

If UNCERTAIN + high stakes → recommend human expert review with specific questions.

### Step 6 — Report

Output the report using the format in `references/report-format.md`.

Key sections:
- Verdict line (verdict + score + confidence)
- Executive summary (2-3 sentences)
- Findings table (severity, description, quote, counter-check result)
- What was NOT checked
- Recommendations

---

## Rules

1. **No quote = no finding.** Every finding must cite exact text from the artifact.
2. **No severity before Step 3.** Step 2 extracts, Step 3 judges.
3. **Every CRITICAL/IMPORTANT survives adversarial or gets downgraded/removed.** No exceptions.
4. **Scope transparency.** Always state what you did NOT examine.
5. **Counter-check the steel-man.** Don't just state it — actually test it against evidence.

---

## References

- `references/patterns.md` — Known impossibility patterns (theorems, definitions, regulations)
- `references/methods.md` — Analysis method procedures
- `references/report-format.md` — Output report template

---

## Integration with other skills

- **Used by:** `/review` (adversarial methodology), `/develop` Phase 4 (self-review)
- **Input from:** any artifact — code, spec, plan, meeting notes
- **Output to:** `/fix` (if REJECT with code findings), `/plan` (if REJECT with spec findings)

## Provenance

Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-verify` v1.0.0.

# Report Format

Use this template for the Step 6 output. Fill all sections. Remove nothing.

---

## Full Report

```
# Verification Report

## VERDICT: {ACCEPT|REJECT|UNCERTAIN} — Score: {S} — Confidence: {HIGH|MEDIUM|LOW}

## Executive Summary

{2-3 sentences: what was verified, key finding, verdict justification}

## Configuration

- Artifact: {path or description}
- Mode: {Quick|Standard|Deep}
- Stakes: {LOW|MEDIUM|HIGH}
- Methods applied: {list of methods used in Steps 2-3}

## Findings

| # | Severity | Description | Quote | Counter-check | Survived? |
|---|----------|-------------|-------|---------------|-----------|
| F1 | CRITICAL | {description} | "{exact text}" | {counter-hypothesis tested} | {YES/DOWNGRADED/REMOVED} |
| F2 | IMPORTANT | {description} | "{exact text}" | {counter-hypothesis tested} | {YES/DOWNGRADED/REMOVED} |
| ... | | | | | |

## Score Breakdown

| Source | Points |
|--------|--------|
| F1: {description} | +{N} |
| F2: {description} | +{N} |
| Pattern match: {pattern ID} | +1 |
| Clean pass: {method name} | -0.5 |
| Phase 4 adjustment: {finding} downgraded | -{N} |
| **Total** | **{S}** |

## Adversarial Review

### Steel-man for {opposite verdict}
{Strongest argument that your verdict is wrong. 3+ points.}

### Steel-man assessment
{Did it hold? Why or why not?}

## Not Checked

{Explicit list of what was out of scope or not examined:}
- {item 1}
- {item 2}

## Recommendations

{Specific, actionable next steps based on verdict:}

### If REJECT:
- Fix {specific finding} by {specific action}
- Re-verify after fixes

### If ACCEPT:
- {Minor observations to address if time permits}

### If UNCERTAIN:
- {Specific questions for human expert review}
- {What additional information would resolve uncertainty}

## Metadata

- Session: DV-{timestamp}
- Assumptions declared: {count}
- Findings: {total} ({critical} CRITICAL, {important} IMPORTANT, {minor} MINOR)
- Methods: {count} applied, {clean_passes} clean passes
- Adversarial: {removed} removed, {downgraded} downgraded, {survived} survived
```

---

## Compact Report

Use when user asks for compact/short output, or for Quick mode by default.

```
# Verification: {ACCEPT|REJECT|UNCERTAIN} (S={score}, {confidence} confidence)

{2-3 sentence conclusion}

## Critical Issues
{List only CRITICAL findings that survived adversarial review, or "None."}

## Important Findings
{List only IMPORTANT findings that survived, or "None."}

## Recommendations
{1-3 specific actions}

## Not Checked
{What was out of scope}
```

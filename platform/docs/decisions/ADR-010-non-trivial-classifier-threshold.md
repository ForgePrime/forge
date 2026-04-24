# ADR-010 — Non-trivial claim classifier threshold

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.3, CONTRACT §A.2 non-trivial definition, FORMAL_PROPERTIES_v2 P19.

## Context

CONTRACT §A.2 defines "non-trivial" claim via 7 triggers + 3 trivial exceptions. F.3 enforces: non-trivial untagged → REJECTED (not WARN). The operationalization requires a **classifier** that reliably identifies non-trivial claims in agent output. Without threshold/rules, F.3 either:
- over-rejects (trivial claims flagged) → friction halts useful work
- under-rejects (non-trivial claims pass) → prior substitution violation (ECITP §2.8)

## Decision

[UNKNOWN — must specify:]

1. **Classifier mechanism:** regex-based (grep patterns for "the X is Y", "this always Z", etc.) / AST-based (extract predicates) / ML-based classifier / hybrid.
2. **Threshold / confidence:** if probabilistic, P(non-trivial) ≥ ?? to trigger REJECT.
3. **False-positive handling:** author override path (explicit `[TRIVIAL: reason]` tag) vs no-override.
4. **Calibration dataset:** labeled corpus of ~100 historical claims with ground truth.

## Alternatives considered

- **A. Regex-based with explicit trigger patterns from CONTRACT §A.2** — candidate: deterministic (ESC-1), auditable, extensible via new patterns; false-positive rate depends on pattern precision.
- **B. AST-based predicate extraction + heuristic** — more accurate but more complex; requires language parser.
- **C. LLM classifier** — rejected: violates ESC-1 determinism + ECITP §2.8 (exactly the failure mode F.3 aims to prevent — LLM deciding whether an LLM-generated claim needs evidence).
- **D. All claims tagged by default (no classifier)** — rejected: trivializes CONTRACT §A.2 by inflating tag noise; violates cascade-compression purpose.

## Consequences

### Immediate
- F.3 validator implementation depends on chosen mechanism.
- Calibration dataset curation (if ML-based) adds one prerequisite sprint.

### Downstream
- False-positive rate sets friction cost per Execution; high cost → teams bypass F.3 culturally.

### Risks
- Regex brittle → new phrasings escape detection.
- Any classifier can be gamed by explicit `[TRIVIAL: bypass]` — mitigate via audit of override usage.

### Reversibility
COMPENSATABLE — classifier swap via supersedes-by ADR; historical Executions retain their original pass/fail verdict.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage F.3]** ADR-010 blocks F.3.
- **[CONFIRMED: CONTRACT §A.2]** 7 triggers + 3 exceptions enumerated.
- **[UNKNOWN]** calibration dataset availability — do we have labeled historical reasoning claims?

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

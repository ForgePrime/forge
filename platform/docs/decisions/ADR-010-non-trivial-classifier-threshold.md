# ADR-010 — Non-trivial claim classifier threshold

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.3, CONTRACT §A.2 non-trivial definition, FORMAL_PROPERTIES_v2 P19.

## Context

CONTRACT §A.2 defines "non-trivial" claim via 7 triggers + 3 trivial exceptions. F.3 enforces: non-trivial untagged → REJECTED (not WARN). The operationalization requires a **classifier** that reliably identifies non-trivial claims in agent output. Without threshold/rules, F.3 either:
- over-rejects (trivial claims flagged) → friction halts useful work
- under-rejects (non-trivial claims pass) → prior substitution violation (ECITP §2.8)

## Decision

**Option A — Regex-based classifier with CONTRACT §A.2 trigger patterns + explicit author override + production-calibrated dataset.**

Mechanism:
- **Regex trigger library** per CONTRACT §A.2 seven non-trivial triggers: claims about state transitions, cascade effects, cross-module dependencies, external system contracts, assumptions about code behavior, side effects, invariant preservation. Each trigger has ≥3 canonical regex patterns (e.g., `"\\bthe\\s+system\\s+(?:will|always|never)\\b"`, `"\\bif\\s+.*\\bthen\\b.*\\bdata\\b"`).
- **Trivial exceptions** (CONTRACT §A.2 three exceptions): explicit enumerated phrasings (e.g., "1 + 1 = 2", "this file exists at path X", "function Y returns None") — short explicit-exception list; non-matches fall to non-trivial by default.
- **No probabilistic threshold**: classifier output is binary (match any trigger = non-trivial; no trigger match AND no explicit exception = **non-trivial by default** per ECITP §2.8 prior-substitution prohibition — better to over-flag than under-flag).
- **Author override**: explicit tag `[TRIVIAL: <reason>]` in claim text bypasses classifier; `<reason>` free-form but audited (G.4 rule prevention log tracks override usage; if same author > 5× overrides per week → Steward flags for review).

Calibration:
- **v1 dataset**: CONTRACT §A.2 canonical examples + 20 hand-labeled historical claims from existing Findings (if available) — minimum viable to seed test suite.
- **Post-launch calibration**: first 3 months of production Findings reviewed by Steward; false-positive rate target ≤ 10%, false-negative rate target ≤ 2% (prefer over-flagging per above). If target missed → regex library extension via superseding ADR.

Exit-test contract (F.3 T1 strengthening):
- `pytest tests/test_non_trivial_classifier.py` — labeled corpus of 40 claims (20 non-trivial + 20 trivial + 20 edge) → classifier output matches labels within stated error bounds.

Rejected alternatives:
- **B (AST-based predicate extraction)**: more accurate but requires language parser + predicate grammar; complexity not justified before regex calibration data exists.
- **C (LLM classifier)**: **rejected categorically** — violates ESC-1 determinism + ECITP §2.8 (exactly the failure mode F.3 is designed to prevent: LLM deciding whether LLM-generated claim needs evidence).
- **D (all claims tagged by default, no classifier)**: rejected — trivializes CONTRACT §A.2's distinction (cascade-compression purpose); inflates tag noise; defeats assumption-discipline signal.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option A (regex library + [TRIVIAL] author override + 3-month calibration); content DRAFT.

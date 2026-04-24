# ADR-013 — Challenger REFUTED verdict handling

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.6, FORMAL_PROPERTIES_v2 P23 (verification independence), EPISTEMIC_CONTINUITY_ASSESSMENT §8 Q2.

## Context

F.6 introduces `forge_challenge` endpoint where a distinct actor (challenger) reviews a candidate verdict. If challenger returns REFUTED, what happens to the Execution:

- Auto re-queue for a new Execution attempt?
- Permanent REJECTED, author must start fresh?
- Human override path (Steward can overrule a REFUTED)?

## Decision

[UNKNOWN — requires: re-queue policy + human override policy + retry limits.]

## Alternatives considered

- **A. Mandatory re-queue: REFUTED → new Execution with challenger findings as UNKNOWN items** — preserves work, forces resolution; risk: infinite loop if challenger keeps refuting.
- **B. Permanent REJECTED: REFUTED → terminal; fresh Execution required from scratch** — hard reset; risks losing valid partial work.
- **C. Human override allowed: Steward can RATIFY over REFUTED with signed override record** — balances challenger authority with human judgment; requires ADR-007 Steward.
- **D. Hybrid: re-queue allowed up to N times, then REJECTED, then Steward override possible** — candidate.

## Consequences

### Immediate
- F.6 state machine semantics fixed.
- Retry limit N (if D) is a calibration constant — likely tied to ADR-004.

### Downstream
- All F.6 verdicts depend on this rule.
- Steward override path (if C/D) integrates with G.5 Steward role.

### Risks
- A: infinite loop if challenger-agent has fixed-point disagreement; mitigate via N-retry limit (D).
- B: lost work incentivizes "game the challenger" behavior.
- C/D: Steward burden proportional to REFUTED rate.

### Reversibility
REVERSIBLE — policy change; in-flight REFUTED Executions retain original rule.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage F.6]** ADR-013 blocks F.6 completion.
- **[CONFIRMED: EPISTEMIC_CONTINUITY_ASSESSMENT §8 Q2]** open question listed.
- **[UNKNOWN]** expected REFUTED rate (affects Steward load in C/D).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

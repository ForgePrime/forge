# ADR-007 — Framework Steward role + rotation policy for Forge project

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — organizational leadership
**Related:** PLAN_GOVERNANCE Stage G.5, OPERATING_MODEL §6, AUTONOMOUS_AGENT_FAILURE_MODES §1.2.

## Context

CGAID Framework mandates a Steward role accountable for: quarterly audit review, Critical-tier Decision sign-off, Rule Lifecycle retirement approvals, ACKNOWLEDGED_GAP sign-off, DLP violation confirmation (per ADR-018). PLAN_GOVERNANCE Stage G.5 cannot start without this decision. AUTONOMOUS_AGENT_FAILURE_MODES §1.2 identifies "Steward authority gap" as a Structural Requirement blocker.

## Decision

[UNKNOWN — organizational: who, how many, rotation period, backup/delegation.]

Required decisions:
1. **Who** — individual name(s) + role title(s)
2. **Headcount** — 1 (single point of failure) / 2 (primary + backup) / rotation council ≥3
3. **Rotation period** — quarterly / annual / term-limited / none
4. **Delegation** — Steward OOO handling; explicit backup or BLOCKED until return?
5. **Succession** — how next Steward is selected (appointment / election / criteria-based)

## Alternatives considered

- **A. Single Steward, no rotation** — rejected: single point of failure; burnout risk; violates AUTONOMOUS_AGENT_FAILURE_MODES §1.2 recommendation.
- **B. Dual Stewards (primary + backup), annual rotation** — candidate: redundancy + fresh perspective; adds coordination overhead.
- **C. Rotation council ≥3, quarterly rotation with 1 stepping down per cycle** — candidate: maximum resilience; highest governance overhead.
- **D. External Steward (outside Forge team) — independence** — rejected by default: too expensive; context-gap for domain decisions.

## Consequences

### Immediate
- Stage G.5 migration adds `User.steward_role`, rotation columns; values populated with chosen individual(s).

### Downstream
- Every Critical Decision post-G.5 requires sign-off from current Steward.
- Every ACKNOWLEDGED_GAP record per FRAMEWORK_MAPPING §12 requires Steward signature.

### Risks
- Steward unavailable → Critical Decisions blocked → implementation halt.
- Steward-turnover context loss → mitigate via mandatory handover review per rotation cycle.

### Reversibility
REVERSIBLE — new ADR supersedes rotation rules; in-flight sign-offs retain original Steward attribution.

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE Stage G.5]** ADR-007 blocks G.5.
- **[CONFIRMED: AUTONOMOUS_AGENT_FAILURE_MODES §1.2]** Steward dispute resolution gap documented.
- **[UNKNOWN]** organizational authority to name Steward(s).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

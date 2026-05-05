# ADR-007 — Framework Steward role + rotation policy for Forge project

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003; Steward identity pending user confirmation) [ASSUMED: AI-recommendation with interim-solo configuration, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept with interim config) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.5, OPERATING_MODEL §6, AUTONOMOUS_AGENT_FAILURE_MODES §1.2, ADR-013 + ADR-020 (Steward authorities).

## Context

CGAID Framework mandates a Steward role accountable for: quarterly audit review, Critical-tier Decision sign-off, Rule Lifecycle retirement approvals, ACKNOWLEDGED_GAP sign-off, DLP violation confirmation (per ADR-018). PLAN_GOVERNANCE Stage G.5 cannot start without this decision. AUTONOMOUS_AGENT_FAILURE_MODES §1.2 identifies "Steward authority gap" as a Structural Requirement blocker.

## Decision

**Option B (modified) — interim solo Steward + formal ACKNOWLEDGED_GAP on backup; re-evaluate at team-growth milestone.**

Configuration:
1. **Primary Steward (interim)**: project owner (currently single user operating Forge).
2. **Backup Steward**: **ACKNOWLEDGED_GAP** per FRAMEWORK_MAPPING §12 — no backup named while team = 1 engineer. Requires Steward-signed acknowledgment at each quarterly review until resolved.
3. **Rotation period**: **none while team ≤ 2 engineers**; formal rotation policy triggered at team growth to ≥3 engineers (to be specified via superseding ADR at that time).
4. **Delegation (OOO handling)**: with single Steward, OOO = project BLOCKED on Steward-required decisions. SLA: OOO > 7 days → Critical Decisions queue must be resolved by project owner's return OR escalation per ADR-025 (proposed SLA framework).
5. **Succession (interim)**: project owner's departure = immediate superseding ADR required; no auto-succession path. This is a **known single point of failure** explicitly accepted via ACKNOWLEDGED_GAP.

Schema:
- `User.steward_role BOOLEAN DEFAULT false` — primary-Steward flag (only one row TRUE at a time per project via partial unique index).
- `AuditLog.reviewed_by_steward FK → users.id NULL` — captures Steward at review time.
- `Decision.steward_sign_off_by FK → users.id NULL` — mandatory for severity ≥ HIGH per G.5.
- `acknowledged_gaps(id, gap_kind, signed_by_steward_id, signed_at, expires_at, rationale)` — tracks this ADR's ACKNOWLEDGED_GAP for backup-Steward.

Kill criteria / escalation triggers (for interim config):
- If Steward unavailable > 14 days AND ≥1 CRITICAL Decision queued → project enters EXECUTION_HALT state (per G.1 kill-criteria pattern).
- Re-evaluation trigger: **team grows to ≥ 3 engineers** → ADR-007 v2 with rotation council.

Rejected alternatives for current team size:
- **A (single, no gap acknowledgment)**: violates FC §37 "no silent workaround" — SPOF must be explicit.
- **B (dual Stewards, annual rotation)**: no backup person available; aspirational.
- **C (rotation council ≥ 3)**: same — not available at current team size.
- **D (external Steward)**: expensive; context-gap for domain-specific decisions; reconsider if budget allows later.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option B modified (interim solo Steward = project owner, backup ACKNOWLEDGED_GAP, re-evaluate at team ≥3; kill-criteria Steward-OOO > 14 days with queued CRITICAL); content DRAFT.

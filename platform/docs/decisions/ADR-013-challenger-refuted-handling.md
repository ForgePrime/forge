# ADR-013 — Challenger REFUTED verdict handling

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.6, FORMAL_PROPERTIES_v2 P23, EPISTEMIC_CONTINUITY_ASSESSMENT §8 Q2, ADR-007 (Steward override path), ADR-012 (challenger must satisfy distinct-actor).

## Context

F.6 introduces `forge_challenge` endpoint where a distinct actor (challenger) reviews a candidate verdict. If challenger returns REFUTED, what happens to the Execution:

- Auto re-queue for a new Execution attempt?
- Permanent REJECTED, author must start fresh?
- Human override path (Steward can overrule a REFUTED)?

## Decision

**Option D — Hybrid with bounded retry + Steward override**:

Policy:
1. **Bounded re-queue**: REFUTED verdict → new Execution spawned with challenger findings injected as UNKNOWN items (via `Execution.uncertainty_state.uncertain`). Counter `Execution.refuted_retry_count` incremented. Allowed up to `max_refuted_retries = 3` (per ADR-004 calibration; starting default = 3).
2. **Terminal REJECTED** at N=3: after 3 failed attempts, Execution status = REJECTED with reason=`challenger_refuted_terminal`; Change (if any) reverted per C.4 Reversibility; Finding filed with severity=HIGH.
3. **Steward override path**: for terminal-REJECTED Executions, Steward may issue a signed override via `POST /executions/{id}/steward-override` with:
   - `override_reason` (mandatory free-text)
   - `override_evidence_ref` (mandatory — ≥1 EvidenceSet citing independent basis)
   - `steward_sign_off_by` (Steward user-id + timestamp)
   Result: Execution.status → ACCEPTED_WITH_OVERRIDE; Change proceeds; AuditLog row mandatory.
4. **Override audit**: G.3 metrics include `M_challenger_override_rate` — if > 10% of REJECTED lead to override, quarterly Steward audit (G.5) flags systemic issue.

Rationale:
- N=3 strikes balance between author-correction opportunity and challenger authority. Higher N → challenger becomes advisory; lower N → one disagreement kills valuable work.
- Steward override path prevents deadlock while preserving audit trail + violation log (G.2).
- Infinite retry (Option A alone) risks fixed-point disagreement loop → budget waste + tech debt accumulation.

Implementation:
- Schema: `Execution.refuted_retry_count INT NOT NULL DEFAULT 0`; `Execution.steward_override_reason TEXT NULL`, `steward_override_evidence_ref UUID NULL`, `steward_override_at TIMESTAMP NULL`.
- F.6 T3 test: synthetic challenger always-REFUTED → Execution retries 3× then terminal-REJECTED; Steward override test confirms bypass works with signed record.

Rejected alternatives:
- **A (infinite re-queue)**: risk of fixed-point disagreement loop; budget unbounded.
- **B (permanent REJECTED, no retry, no override)**: hard reset wastes partial work; no recovery path.
- **C (Steward override without retry attempts)**: bypasses challenger authority entirely; challenger becomes advisory-only.

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

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option D (hybrid: N=3 retry + terminal REJECT + Steward override with signed record + M_challenger_override_rate metric); content DRAFT.

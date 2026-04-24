# ADR-014 — C2 sufficiency gate placement: pre-LLM vs post-hoc validator

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003)
**Date:** 2026-04-24
**Decided by:** user (decision) + AI agent (draft)
**Related:** Phase A exit, CCEGAP Condition 2, PLAN_CONTRACT_DISCIPLINE Stage E.1, EPISTEMIC_CONTINUITY_ASSESSMENT §8 Q4.

## Context

CCEGAP C2 requires `Suff(P_i, R_i, A_i, E_<i, T_i) = true` — context sufficient to perform the step. E.1 ContractSchema provides structural sufficiency via self-adjoint prompt+validator derivation. Two enforcement points possible:

1. **Pre-LLM gate** — before LLM is invoked, verify `Suff(C_i, R_i)` via ContractSchema.validate(projection, required_fields). Fail → Execution BLOCKED, no LLM call.
2. **Post-hoc validator** — LLM called, then validator on its output verifies sufficiency retroactively. Fail → REJECTED.

## Decision

**Option C — Both pre-LLM AND post-hoc validation** (per FORMAL P11 diagonalizability).

- **Pre-LLM gate**: `ContractSchema.validate_required(projection, task)` runs in `prompt_parser` BEFORE the LLM call. Integrates with B.5 TimelyDeliveryGate chain — same pending→IN_PROGRESS transition, one atomic gate set. Fail → Execution BLOCKED with `blocked_reason='input_sufficiency_missing'`, no LLM cost incurred.
- **Post-hoc gate**: `ContractSchema.validate_output(decision.result)` runs in VerdictEngine at Decision commit. Fail → REJECTED with `reason='output_shape_insufficient'`.
- **Shared validator module**: `app/validation/contract_schema_validator.py` exposes both entry points from single source (DRY; no duplicate logic).

The two gates are **orthogonal layers** per P11 — pre-LLM catches input insufficiency (structural precondition), post-hoc catches output insufficiency (structural postcondition). Neither alone suffices: pre-only misses output-shape bugs; post-only wastes LLM cost on inputs known to fail.

## Alternatives considered

- **A. Pre-LLM only** — rejected alone: cannot catch insufficiency that only manifests in output shape (e.g. "ContractSchema says task has 3 required outputs but LLM produced 2").
- **B. Post-hoc only** — rejected alone: wastes LLM call on prepared-to-fail input (cost + latency + noise).
- **C. Both pre + post** — candidate: pre catches inputs, post catches outputs; independent layers per FORMAL P11 diagonalizability.
- **D. Pre with "pending validation" flag, post confirms** — middleweight; adds state.

## Consequences

### Immediate
- E.1 validator implementation scope depends on chosen placement.
- B.5 TimelyDeliveryGate (ECITP C3) already has pre-LLM blocking path — C/D integrates with it.

### Downstream
- All `Suff(C_i, R_i)` checks inherit chosen pattern.

### Risks
- A alone: output insufficiency slips through.
- B alone: cost/latency waste.
- C: more code paths; duplicate logic risk (mitigate via shared validator module).

### Reversibility
REVERSIBLE — placement change; historical Executions retain original-rule verdict.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage E.1]** E.1 mentions structural sufficiency.
- **[CONFIRMED: EPISTEMIC_CONTINUITY_ASSESSMENT §8 Q4]** open question.
- **[UNKNOWN]** historical rate of post-hoc insufficiency findings (informs C vs D cost).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option C (pre+post dual-gate); content DRAFT pending distinct-actor review per ADR-003.

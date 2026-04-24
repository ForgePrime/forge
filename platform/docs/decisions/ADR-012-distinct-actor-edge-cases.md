# ADR-012 — Distinct-actor edge cases for SR-3 autonomous loop

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.9 (SR-3), AUTONOMOUS_AGENT_FAILURE_MODES §1.3, ADR-003, ADR-006 (model pinning provides basis for model_id distinct check).

## Context

SR-3 (F.9) requires `Execution.verified_by ≠ Execution.agent` OR a deterministic check. Edge cases need mechanical definition:

- Same agent process, different session (restart between rationale + ratification) — distinct or same?
- Agent spawning subagent of same model — distinct or same?
- Different model at same provider (Opus vs Sonnet) — distinct or same?
- Same agent with human-in-loop approval — does human constitute distinct actor?
- Identical model at different provider instance (e.g. Anthropic API vs AWS Bedrock) — distinct or same?

## Decision

**Option D — Hybrid: distinct iff (different trace_id) AND (different model_id OR human_in_loop = true).**

Formal definition of "distinct actor" for SR-3:
```
distinct(actor_A, actor_B) iff
  actor_A.trace_id ≠ actor_B.trace_id
  AND (
    actor_A.model_id ≠ actor_B.model_id
    OR actor_A.is_human = true
    OR actor_B.is_human = true
  )
```

Edge-case classification per this rule:

| Scenario | trace_id | model_id | is_human | distinct? |
|---|---|---|---|---|
| Same process, different session (restart between rationale + ratification) | SAME | same | false | **NOT distinct** — process restart cannot bypass |
| Agent spawning subagent of same model | different | same | false | **NOT distinct** — subagent shares prior |
| Different model at same provider (Opus vs Sonnet) | different | different | false | **DISTINCT** — different statistical prior |
| Same agent with human approval | different | same | true | **DISTINCT** — human breaks same-prior dependency |
| Identical model-id at different provider instance (Anthropic vs Bedrock) | different | same | false | **NOT distinct** — prior identical regardless of hosting |

Implementation:
- Schema: `Execution.verified_by_category ENUM ('human', 'distinct_agent', 'deterministic_check', 'self_same_actor')`; SR-3 REJECTS if category = 'self_same_actor' AND no deterministic check.
- `Execution.verified_by_trace_id`, `verified_by_model_id`, `verified_by_is_human` captured at ratification time (immutable audit).
- F.9 T1 test: synthetic ratification with `(trace_id=X, model_id=Y, human=false)` matching rationale author → REJECTED with reason=`self_actor_ratification_prohibited`.

Dependency on ADR-006: distinct model_id requires stable model-id values; ADR-006 pinning provides this. Without ADR-006, "model_id" is fuzzy (provider updates silently). Hence ADR-012 is partial-blocked on ADR-006.

Rejected alternatives:
- **A (process-based)**: allows process-restart gaming trivially.
- **B (model-identity only)**: allows same-model-same-trace self-ratification (subagent pattern).
- **C (trace-id only)**: allows different-trace same-model (subagent) to pass — violates spirit of SR-3 "distinct statistical prior".

## Alternatives considered

- **A. Strict same-process = same, different-process = distinct** — simple but allows process-restart gaming.
- **B. Model-identity based: same model-id+version = same, different = distinct** — candidate: aligns with ADR-006 pinning; allows Opus→Sonnet as distinct.
- **C. Session-trace-id based: any session sharing a trace_id = same** — candidate: matches CONTRACT §B.8 solo-verifier spirit; distinct = different trace.
- **D. Hybrid: distinct iff (different trace_id) AND (different model_id OR human_in_loop = true)** — strongest guarantee but highest friction.

## Consequences

### Immediate
- F.9 T1 test assertion depends on chosen rule.
- `Execution.verified_by_category ENUM {human, distinct_agent, deterministic_check}` may be needed.

### Downstream
- Every auto-ratified Execution's legitimacy depends on this rule.

### Risks
- Weak rule (A) = gaming via process restart; strong rule (D) = bottleneck on human reviewers.

### Reversibility
COMPENSATABLE — rule tightening requires invalidating prior auto-ratifications? No — fixed-at-acceptance per FC §29.

## Evidence captured

- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE Stage F.9]** ADR-012 blocks F.9.
- **[CONFIRMED: AUTONOMOUS_AGENT_FAILURE_MODES §1.3]** edge cases documented.
- **[UNKNOWN]** operational frequency of each edge case (which ones happen in practice).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option D (hybrid trace_id AND (model_id OR human) distinctness); content DRAFT; partially blocks on ADR-006.

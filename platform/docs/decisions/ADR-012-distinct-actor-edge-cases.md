# ADR-012 — Distinct-actor edge cases for SR-3 autonomous loop

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform engineering + governance
**Related:** PLAN_CONTRACT_DISCIPLINE Stage F.9 (SR-3), AUTONOMOUS_AGENT_FAILURE_MODES §1.3, ADR-003.

## Context

SR-3 (F.9) requires `Execution.verified_by ≠ Execution.agent` OR a deterministic check. Edge cases need mechanical definition:

- Same agent process, different session (restart between rationale + ratification) — distinct or same?
- Agent spawning subagent of same model — distinct or same?
- Different model at same provider (Opus vs Sonnet) — distinct or same?
- Same agent with human-in-loop approval — does human constitute distinct actor?
- Identical model at different provider instance (e.g. Anthropic API vs AWS Bedrock) — distinct or same?

## Decision

[UNKNOWN — classify each edge case into {distinct, same, requires_deterministic_check_instead}.]

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

- v1 (2026-04-24) — skeleton.

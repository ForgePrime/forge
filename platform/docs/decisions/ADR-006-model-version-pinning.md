# ADR-006 — LLM model version pinning + canary eval procedure

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — platform owner + governance steward
**Related:** R-SPEC-05 (model drift risk), PRACTICE_SURVEY incidents of silent model upgrade causing behavioral drift, FORMAL_PROPERTIES_v2 P6 determinism, CCEGAP C9.

## Context

Forge executions invoke LLMs. Without version pinning + canary evaluation, a provider-side model update can silently change platform behavior — violates CCEGAP C9 deterministic gate (same inputs → same result) and ECITP §2.8 prior substitution (different model ≠ same priors).

## Decision

[UNKNOWN — requires: (a) pinning strategy, (b) canary dataset, (c) go/no-go criteria for model version bumps.]

Required decisions:
1. **Pinning granularity:** model-id + version-tag (e.g. `claude-opus-4-7:2026-04`) vs model-family (e.g. `claude-opus-4`) — stricter = more stable, more vendor-change friction.
2. **Canary dataset size + scope:** N historical executions replayed against new version; divergence threshold D%.
3. **Approval flow:** canary PASS → automatic bump? Or always requires Steward sign-off?

## Alternatives considered

- **A. No pinning, use provider-latest** — rejected: R-SPEC-05 explicit risk; violates P6 determinism.
- **B. Strict pinning to specific model-id + date tag; canary on fixed 100-execution replay; automatic bump if divergence ≤ 1%** — minimum viable.
- **C. Strict pinning + canary + MANDATORY Steward sign-off on every bump regardless of divergence** — safest but adds governance load.

## Consequences

### Immediate
- Pinning string added to `app/config.py` or env var; canary replay script needed.

### Downstream
- Provider deprecates pinned version → forced bump → canary + sign-off ceremony.

### Risks
- Canary dataset stale → false-positive "no divergence" on workloads not in canary.
- Canary dataset contains PII → leak risk.

### Reversibility
REVERSIBLE — pin string change + redeploy.

## Evidence captured

- **[CONFIRMED: ROADMAP.md §12]** ADR-006 Model version pinning listed as pending.
- **[UNKNOWN]** current model pinning state — grep `app/` for model-id strings.
- **[UNKNOWN]** canary dataset availability.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton.

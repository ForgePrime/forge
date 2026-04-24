# ADR-004 — Calibration constants (α, τ, W, q_min, risk weights)

**Status:** OPEN
**Date:** 2026-04-24
**Decided by:** pending — requires domain expert + platform owner + (per ADR-003) distinct-actor review
**Related:** Phase A exit (A.3 VerdictEngine, A.4 cutover), Phase D.5 (RiskWeightedCoverage CI α-gate), Phase E.3 (Autonomy demote thresholds), FORMAL_PROPERTIES_v2 P4/P10, ROADMAP §12.

## Context

Five numeric constants are referenced across PLAN_GATE_ENGINE, PLAN_QUALITY_ASSURANCE, PLAN_CONTRACT_DISCIPLINE as `[UNKNOWN]` preconditions blocking their respective stages. Without concrete values these stages cannot define their exit gates mechanically (violates CCEGAP C9 + ASPS §12).

The constants:
1. **α per capability** — minimum risk-weighted failure-mode coverage threshold below which CI blocks merge (D.5 α-gate).
2. **τ (tau)** — tolerance band for validator determinism checks (P6 strengthened in D.2).
3. **W (window)** — observation window length for autonomy Q_n aggregation (E.3 demote logic).
4. **q_min per level** — per-autonomy-level minimum floors for `(success_rate, rollback_rate, evidence_sufficiency, confabulation_rate)`; any component below floor → demote (E.3).
5. **w_m risk weights per FailureMode** — weighting in `Σ w_m Cov(T, m)` coverage calculation (D.5). Uniform default is strawman per ECITP §2.8 (avoid implicit priors).

## Decision

[UNKNOWN: concrete numeric values — domain-expert + platform-owner decision required.]

Required values with example placeholder shapes (NOT decisions):
- `α = {capability_X: 0.??, capability_Y: 0.??, ...}` — per-capability dict, values in [0, 1]
- `τ = ??` — single tolerance, typically float in [0, 0.1]
- `W = ??` days or executions — observation window
- `q_min = {L1: {success_rate: ??, rollback_rate: ??, evidence_sufficiency: ??, confabulation_rate: ??}, L2: {...}, L3: {...}, L4: {...}, L5: {...}}` — per-level floor dict
- `w_m = {failure_mode_code: weight, ...}` — per-FailureMode weight; normalization convention must be specified (sum=1? max=1?)

## Rationale

[UNKNOWN — populate after decision-maker meeting. Rationale must cite: historical incident data, industry benchmarks, regulatory thresholds, or explicit risk-appetite statement per CGAID §OM-6.]

## Alternatives considered

- **A. Uniform defaults (α=0.8 everywhere, τ=0.05, W=30 days, q_min=0.7 on all components, w_m=1/|M|)** — rejected as a *decision* (but acceptable as *starting point for calibration study*): defaults encode an implicit prior that every capability has the same risk profile and every failure mode is equally consequential, which violates ECITP §2.8 prior-substitution prohibition and FC §19 "best total value" (best requires weighting).
- **B. Per-capability tables populated from historical failure data** — preferred path: run calibration study on last N months of Findings/Changes, fit α per capability such that α matches observed "good quarter" coverage; fit w_m weights such that top-5 historical severe incidents cluster above threshold.
- **C. Defer to ADR-022 (not yet authored)** — rejected: circular — ADR-022 would need to cite ADR-004 values.

## Consequences

### Immediate
- Phase A cannot exit until α is set (A.3 VerdictEngine uses τ in determinism check; A.4 CI α-gate references α).
- Phase D.5 FailureMode coverage report cannot meaningfully assert PASS/FAIL without α.
- Phase E.3 Autonomy demote cannot trigger without q_min + W.

### Downstream
- All 54 stages downstream of Phase A inherit α-gate coupling; bad calibration = spurious blocks OR silent gaps.
- α too high → merge paralysis; α too low → regression tolerance (both violate FC §23 "maximize P(detect failure)").

### Risks
- **Calibration drift:** α/W/q_min calibrated at ratification may become stale as codebase grows; mitigate via quarterly re-calibration ADR review (new ADR each cycle).
- **Gaming:** if α fixed and low, teams may pad failure-mode catalog to artificially meet coverage — mitigated by ADR-023 technical-debt category `gaming_coverage_threshold` (proposed).

### Reversibility
COMPENSATABLE — values revisable via new ADR superseding this one. But historical Changes accepted under old α should not be retroactively re-evaluated (fixed-at-acceptance semantics; see FC §29 idempotence).

## Evidence captured

- **[CONFIRMED: ROADMAP.md:690]** ADR-004 is listed as P1 per deep-risk; must be CLOSED before Phase A exit.
- **[CONFIRMED: PLAN_QUALITY_ASSURANCE.md A_{D.5}]** α per capability entry-blocker for D.5 (post-fix: tagged [UNKNOWN] after deep-verify correction).
- **[CONFIRMED: PLAN_CONTRACT_DISCIPLINE.md A_{E.3}]** Window W + q_min entry-blockers for E.3 (post-fix: tagged [UNKNOWN]).
- **[UNKNOWN]** calibration-study dataset availability — do we have sufficient historical Finding/Change data for statistically meaningful α fit?
- **[UNKNOWN]** risk-appetite policy — is there an organizational document stating acceptable Pr(undetected-severe-failure)?

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton; awaits domain-expert population of numeric values.

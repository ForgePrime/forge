# ADR-004 — Calibration constants (α, τ, W, q_min, risk weights, idempotency TTL)

**Status:** CLOSED (content DRAFT — engineering defaults pending calibration-study supersession + distinct-actor review per ADR-003) [ASSUMED: engineering-default values, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept of engineering-default starting values) + AI agent (draft)
**Related:** Phase A exit, Phase D.5, Phase E.3, FORMAL_PROPERTIES_v2 P4/P10, ADR-013 (N=3 retry limit tied), ADR-019 (scoring weights parallel).

## Context

Five numeric constants are referenced across PLAN_GATE_ENGINE, PLAN_QUALITY_ASSURANCE, PLAN_CONTRACT_DISCIPLINE as `[UNKNOWN]` preconditions blocking their respective stages. Without concrete values these stages cannot define their exit gates mechanically (violates CCEGAP C9 + ASPS §12).

The constants:
1. **α per capability** — minimum risk-weighted failure-mode coverage threshold below which CI blocks merge (D.5 α-gate).
2. **τ (tau)** — tolerance band for validator determinism checks (P6 strengthened in D.2).
3. **W (window)** — observation window length for autonomy Q_n aggregation (E.3 demote logic).
4. **q_min per level** — per-autonomy-level minimum floors for `(success_rate, rollback_rate, evidence_sufficiency, confabulation_rate)`; any component below floor → demote (E.3).
5. **w_m risk weights per FailureMode** — weighting in `Σ w_m Cov(T, m)` coverage calculation (D.5). Uniform default is strawman per ECITP §2.8 (avoid implicit priors).

## Decision

**Engineering-default starting values** tagged [ASSUMED: engineering-default-pending-calibration-study]. Mandatory supersession after 3 months of production operation per calibration-study ADR.

### α per capability (D.5 CI α-gate threshold)
- **Starting value**: `α = 0.8 uniform across all capabilities` (`{capability_X: 0.8 for all X}`)
- **Convention**: coverage < α → merge blocked; coverage ≥ α → merge allowed (strict less-than at boundary = pass per ADR-004 v2 tie-breaker).
- **Supersession trigger**: 3 months of production Findings → per-capability α recalibrated to match observed "healthy quarter" coverage rate.
- **[ASSUMED: 0.8 is strawman based on common engineering intuition; real value requires historical failure-rate data not currently available.]**

### τ (determinism tolerance)
- **Starting value**: `τ = 0.01` (1% tolerance for floating-point comparisons in D.2 determinism tests)
- **Applies to**: numeric comparisons in property-based tests where exact-equality is not achievable (e.g., LLM embedding similarity scores).
- **[CONFIRMED: τ = 0.01 matches typical float32 epsilon-scale engineering practice]**

### W (autonomy observation window, E.3)
- **Starting value**: `W = 30 days` (one standard operational cycle)
- **Computation**: Q_n metrics aggregated over last 30 calendar days of Executions.
- **Supersession trigger**: if demote() triggers too frequently (< 1 demote per 90 days expected baseline), widen W; if demote() never triggers while incidents grow, narrow W.
- **[ASSUMED: 30 days balances responsiveness with statistical stability]**

### q_min per autonomy level (E.3 demote thresholds)
- **Starting values** (per component `(success_rate, rollback_rate, evidence_sufficiency, confabulation_rate)`):
  - L1: floor = 0.5 (loose)
  - L2: floor = 0.6
  - L3: floor = 0.7
  - L4: floor = 0.8
  - L5: floor = 0.9 (strict)
- **Logic**: ANY component below floor → demote to previous level.
- **Note on rollback_rate + confabulation_rate**: these are INVERSE metrics (lower is better). Stored as `1 - observed_rate` for uniform floor comparison.
- **[ASSUMED: linear 0.1 per level is strawman; real curve likely steeper at L4→L5; recalibrate after production data]**

### w_m (per-FailureMode risk weights, D.5 coverage)
- **Starting value**: `w_m = 1/|M| uniform` across all FailureModes (equal-weight).
- **Normalization**: `Σ w_m = 1` (sum-to-1 convention).
- **Supersession trigger**: post-launch Steward reviews top-10 severe historical incidents; any FailureMode representing ≥20% of incident severity gets weight ≥ 2× average. Superseding ADR.
- **[ASSUMED: uniform is worst-calibration starting point acknowledged per ADR-004 §Alternatives B; intentionally starts "wrong" to force recalibration via signal accumulation]**

### idempotency_ttl (A.5 MCP idempotency)
- **Starting value**: `idempotency_ttl = 86400 seconds (24 hours)`
- **Applies to**: TTL boundary on `idempotent_calls.expires_at` per (tool, idempotency_key, args_hash) cache entry. Within TTL, duplicate calls return cached result; after TTL, the entry is stale and the next call re-executes (overwriting the entry with a new TTL).
- **Computation**: `expires_at = now() + idempotency_ttl` at the moment of cache write.
- **Rationale**: 24h covers typical retry windows (CI re-runs, manual operator retries, webhook re-deliveries from GitHub) without indefinitely caching stale state. Most Executions complete in < 15 min per MVP_SCOPE latency target; 24h is ~100x that = comfortable safety margin.
- **Per-tool override path**: future ADR may specify different TTL per tool (e.g. `forge_decision` longer than `forge_finding`); for MVP a single global value suffices.
- **Supersession trigger**: if observed cache hit rate after expiry shows users actually want longer caching (analytics from `idempotent_calls` row counts vs. observed retries), widen. If stale-result complaints surface, narrow.
- **[ASSUMED: 86400s is engineering-default per common HTTP idempotency-key conventions (Stripe = 24h); real value pending production-traffic calibration]**

### ADR-013 N=3 retry limit
- Not originally in ADR-004 scope but linked here: challenger-refuted retry limit = 3 (per ADR-013). Tracked as calibration constant.

### Supersession plan
- **T+3 months** (post Phase A production): mandatory ADR-004 v2 with production-derived values. Calibration study script `scripts/calibrate_alpha_and_weights.py` runs on historical Finding data to propose per-capability α and w_m.
- **Interim lockout**: current values [ASSUMED] tag remains on every downstream test / gate until v2 CLOSED.

Rejected alternatives:
- **A (uniform defaults treated as final decision)**: violates ECITP §2.8 — implicit prior without justification.
- **C (defer all values to ADR-022)**: circular dependency; blocks all Phase A.
- **B (per-capability from historical data)**: preferred long-term but data not available now; adopted as supersession path.

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

## Quick reference — machine-grepable constant table

Each constant appears in `- key: value` bullet form so PLAN_PRE_FLIGHT
T_{0.2} grep predicates can verify presence deterministically. All
values [ASSUMED: engineering-default-pending-calibration-study] unless
noted.

- W: 30 days
- q_min[L1.success_rate]: 0.5
- q_min[L1.rollback_rate]: 0.5
- q_min[L1.evidence_sufficiency]: 0.5
- q_min[L1.confabulation_rate]: 0.5
- q_min[L2.success_rate]: 0.6
- q_min[L2.rollback_rate]: 0.6
- q_min[L2.evidence_sufficiency]: 0.6
- q_min[L2.confabulation_rate]: 0.6
- q_min[L3.success_rate]: 0.7
- q_min[L3.rollback_rate]: 0.7
- q_min[L3.evidence_sufficiency]: 0.7
- q_min[L3.confabulation_rate]: 0.7
- q_min[L4.success_rate]: 0.8
- q_min[L4.rollback_rate]: 0.8
- q_min[L4.evidence_sufficiency]: 0.8
- q_min[L4.confabulation_rate]: 0.8
- q_min[L5.success_rate]: 0.9
- q_min[L5.rollback_rate]: 0.9
- q_min[L5.evidence_sufficiency]: 0.9
- q_min[L5.confabulation_rate]: 0.9
- tau: 0.01
- alpha[capability_default]: 0.8
- idempotency_ttl: 86400
- clock_skew_tolerance: 5
- impact_closure_review_cost_threshold: 100

(Note: `q_min` has 20 entries = 4 components × 5 levels; PLAN_PRE_FLIGHT
T_{0.2} grep `^- q_min\[` expects ≥20 matches. Same convention extends
when adding per-capability `alpha[<capability>]` bullets — current MVP
uses single uniform `alpha[capability_default]`.)

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on engineering-default values tagged [ASSUMED: pending-calibration-study]; α=0.8 uniform, τ=0.01, W=30d, q_min linear 0.5→0.9 per L1-L5, w_m=1/|M| uniform sum-to-1; mandatory supersession after 3 months production data. Content DRAFT.
- v2.1 (2026-04-25) — added `idempotency_ttl = 86400s` to close PLAN_GATE_ENGINE A.5 entry-condition gap. Tagged [ASSUMED: engineering-default per Stripe-style 24h convention]. Added quick-reference section in machine-grepable `- key: value` form so PLAN_PRE_FLIGHT T_{0.2} grep predicates verify deterministically. Also added explicit values for `clock_skew_tolerance: 5 seconds` and `impact_closure_review_cost_threshold: 100` (referenced by FORMAL §7 but missing from v2 enumeration). Same content-DRAFT status.

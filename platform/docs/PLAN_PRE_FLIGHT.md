# PLAN: Pre-flight — Governance Prerequisites

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** nothing — this plan is the entry gate for all others.
**Must complete before:** PLAN_GATE_ENGINE, PLAN_MEMORY_CONTEXT, PLAN_QUALITY_ASSURANCE, PLAN_CONTRACT_DISCIPLINE, PLAN_GOVERNANCE.

---

## Soundness conditions addressed

This plan does not close runtime soundness conditions 1–7 directly.
It closes the **meta-condition**: that conditions 1–7 *can be verified* — i.e., that the calibration constants, normative spec, and distinct-actor review mechanism exist before any other plan starts.

Without this plan, every downstream test is measuring against an undefined target (conditions 2, 5 require closed thresholds; condition 6 requires a normative spec; condition 7 requires a human-reachable escalation path).

| Pre-condition | Required by | Closed in |
|---|---|---|
| ADR-003 ratified (distinct-actor mechanism) | Conditions 6, 7 (gate sign-off mechanism + escalation path; distinct-actor review also confirms that T_i predicates are deterministic, contributing to 5) | Stage 0.1 |
| ADR-004 closed (τ, α, W, q_min, TTL) | Condition 2 (sufficiency threshold), 5 (α-gate) | Stage 0.2 |
| ADR-005 closed (Invariant.check_fn format) | Condition 5 (determinism of invariant T_i — callable vs DSL affects testability) | Stage 0.2 |
| ADR-006 closed (model version pinning) | Condition 5 (determinism across sessions) | Stage 0.2 |
| IMPLEMENTATION_TRACKER claims verified | All conditions (C_i cannot be trusted without this) | Stage 0.3 |

---

## Theorem variable bindings

```
C_0 = platform/docs/ + platform/app/ + IMPLEMENTATION_TRACKER.md
R_0 = "platform has a verified, reviewed, normative foundation before Phase A begins"
A_0 = { ADR-003 unratified, calibration constants unknown, TRACKER claims unverified }
T_0 = "all A_0 items resolved and recorded"
G_0 = pass iff T_0 satisfied
```

**Condition 4 (A_i explicit):** A_0 above is the ambiguity set. Each item must be resolved — not assumed — before stage exits.

**Condition 7 (Missing→Stop):** if any item in A_0 remains UNKNOWN at end of Pre-flight, downstream plans **may not start**. No plausible default fills.

---

## Stage 0.1 — Ratify ADR-003

**Closes:** meta-condition: distinct-actor mechanism exists.

**Entry conditions:**
- `docs/decisions/ADR-003-human-reviewer-normative-transition.md` readable.

**Work:**
- File a review record in `docs/reviews/review-ADR-003-by-<actor>-<date>.md` per `reviews/_template.md`.
- Distinct actor re-verifies each claim in ADR-003 via grep/read (not by accepting author's summary).
- ADR-003 transitions OPEN → RATIFIED.

**Exit test T_{0.1} (deterministic):**
```
PASS iff:
  file exists: docs/reviews/review-ADR-003-by-*.md
  AND grep "status: RATIFIED" docs/decisions/ADR-003-human-reviewer-normative-transition.md
  AND review record has field "reviewed_by" that names a human listed in
      docs/decisions/README.md eligible reviewers — NOT the commissioning user
      (CONTRACT §B.8: user cannot solo-verify their own ADR)
  AND grep "Status.*NORMATIVE" platform/docs/FORMAL_PROPERTIES_v2.md → match
  AND grep -E "ADR-003.*RATIFIED" docs/decisions/README.md → match
      (ADR index reflects the new status; prevents README drift from ADR state)
```

**"Original author" definition:** For AI-generated artifacts (ADR-003 was produced by a Claude session), "original author" = the commissioning user who directed that session. A distinct actor must be a different human, not the same user acting again.

**Gate G_{0.1}:** all five grep conditions true → PASS.
**Soundness:** condition 6 — output (normative spec) propagates only after gate passes.

---

## Stage 0.2 — Close calibration ADRs (004, 005, 006)

**Closes:** meta-condition: numeric thresholds defined; Invariant format decided; model version pinned.

**Entry conditions:**
- Stage 0.1 complete (ADR-003 RATIFIED).

**Work per ADR:**

**ADR-004** (calibration constants):
- Decide and record: W (rolling window for Q_n), q_min (4 values × 5 autonomy levels), τ (risk bound), α (coverage floor per capability), idempotency TTL, clock-skew tolerance, ImpactClosure review-cost threshold.
- All values are DECISIONS, not defaults. Each value has a rationale sentence.
- Distinct-actor review filed.

**ADR-005** (Invariant.check_fn format):
- Decide: Python callable vs DSL.
- Rationale: if invariants must be serialized cross-service → DSL; if platform-only → callable.
- Distinct-actor review filed.

**ADR-006** (model version pinning):
- Decide: which model versions; how to update; canary eval frequency.
- Required for condition 5 (determinism depends on model stability).
- Distinct-actor review filed.

**Exit test T_{0.2} (deterministic):**
```
PASS iff:
  grep "status: CLOSED" docs/decisions/ADR-004*.md  → match
  grep "status: CLOSED" docs/decisions/ADR-005*.md  → match
  grep "status: CLOSED" docs/decisions/ADR-006*.md  → match
  AND each ADR has review record in docs/reviews/
  AND ADR-004 contains all 7 required constants, verified by explicit greps
      (no LLM interpretation, no "contains" heuristic):
        grep -E "^- W:\s"                                docs/decisions/ADR-004*.md  → match
        grep -E "^- q_min\["                             docs/decisions/ADR-004*.md  → ≥20 matches
                                                                                         (4 Q-fields × 5 autonomy levels)
        grep -E "^- tau:\s"                              docs/decisions/ADR-004*.md  → match
        grep -E "^- alpha\["                             docs/decisions/ADR-004*.md  → ≥1 match
                                                                                         (per-capability table)
        grep -E "^- idempotency_ttl:\s"                  docs/decisions/ADR-004*.md  → match
        grep -E "^- clock_skew_tolerance:\s"             docs/decisions/ADR-004*.md  → match
        grep -E "^- impact_closure_review_cost_threshold:\s"
                                                         docs/decisions/ADR-004*.md  → match
```

**Note on the 7 constants vs FORMAL_PROPERTIES_v2 §7 (which lists 8 rows):** the eighth row in §7 ("Impact-estimate error tolerance") is explicitly annotated `P3 (hint)` — advisory, not required. The closure set above is the minimum required set; the hint may be recorded but is not gated.

**Gate G_{0.2}:** all conditions true → PASS.
**Soundness:** condition 7 — these are the UNKNOWN items from A_0. Remaining UNKNOWN → STOP, not default-fill.

---

## Stage 0.3 — Smoke-test IMPLEMENTATION_TRACKER claims

**Closes:** meta-condition: C_1 (context for Phase A) is grounded in verified evidence, not self-reported [ASSUMED].

**Entry conditions:**
- Stage 0.2 complete.
- Forge platform running (port 8012 or test port).

**Work:**
- For every `[EXECUTED]` claim in `platform/IMPLEMENTATION_TRACKER.md`: make an HTTP call or run a pytest that directly exercises the claimed behavior.
- Record result as: VERIFIED (behavior matches) or DIVERGED (behavior differs from claim).
- DIVERGED → open a `Finding` in Forge with `severity=HIGH` + patch note in `GAP_ANALYSIS_v2.md`.
- `[ASSUMED]` tags on TRACKER claims: either remove (if VERIFIED) or promote to explicit gap.

**Exit test T_{0.3} (deterministic):**
```
PASS iff:
  smoke_test_tracker.py reviewed by distinct actor
    (code review record: docs/reviews/review-smoke-script-by-<actor>-<date>.md)
  AND script smoke_test_tracker.py exits 0
  AND output file smoke_results.json exists with:
    - every [EXECUTED] claim has status: VERIFIED or DIVERGED (no status: UNCHECKED)
    - DIVERGED count recorded
    - every DIVERGED has a Finding row in DB (query: SELECT count(*) FROM findings WHERE source="tracker_smoke" AND severity="HIGH")
```

**Gate G_{0.3}:** review record filed + script exit 0 + no UNCHECKED claims → PASS.
**Note:** DIVERGED findings do NOT block gate — they are disclosed, not hidden. Gate blocks only on unchecked claims.
**Soundness:** condition 3 — O_1 (Phase A output) must be derived from verified evidence, not tracker self-reports.

---

## Pre-flight exit gate (G_0)

All three stages must be PASS:

```
G_0 = PASS iff:
  G_{0.1} = PASS  (ADR-003 RATIFIED, review record filed)
  AND G_{0.2} = PASS  (ADR-004, 005, 006 all CLOSED with reviews)
  AND G_{0.3} = PASS  (zero UNCHECKED tracker claims)
```

**What this enables:** C_1 for PLAN_GATE_ENGINE is now:
- normative spec (FORMAL_PROPERTIES_v2 → NORMATIVE after ADR-003 review)
- closed calibration constants
- verified implementation baseline

**What remains ASSUMED (disclosed):**
- DIVERGED tracker claims are disclosed as Findings, not hidden — downstream plans reference them.
- Distinct-actor reviews for ADR-004–006 may surface new UNKNOWN items — each must be resolved or explicitly escalated before the plan that depends on them starts.

---

## Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | Stage 0.3 T1 rejects `smoke_results.json` with any status=UNCHECKED; empty review record at Stage 0.1 → gate fails (grep finds no `reviewed_by:` field). |
| 2 | timeout_or_dependency_failure | Handled | ADR review has no auto-close; if distinct actor never files review → Stage 0.1 stays BLOCKED (explicit, not silent). ADR-004 domain-expert timeout handled same way — no default values substituted. |
| 3 | repeated_execution | Handled | ADR ratification is an idempotent file-state change (`Status: RATIFIED` set-once via PR + review record; re-application is no-op). Smoke test re-runs deterministic (SHA-256 of implementation files checked). |
| 4 | missing_permissions | Handled | Stage 0.1 T1 requires reviewer listed in `docs/decisions/README.md` eligible-reviewers set; CI checks via git commit author; unauthorized reviewer → gate fails. |
| 5 | migration_or_old_data_shape | JustifiedNotApplicable | Pre-flight produces only ADR markdown + smoke-result JSON; no DB schema changes. If a future Pre-flight stage adds data migration → revisit this row. |
| 6 | frontend_not_updated | JustifiedNotApplicable | Pre-flight artifacts are governance documents (ADRs) and CI reports; Forge has no end-user frontend in scope at this phase. |
| 7 | rollback_or_restore | Handled | ADR ratification reversible via Status transition back to `OPEN` per ADR-003 §5 process. Calibration ADRs (004-006) reversible by superseding ADR with `supersedes-by` reference. |
| 8 | monday_morning_user_state | JustifiedNotApplicable | Pre-flight has no per-user or per-session state; all state in version-controlled ADR files + smoke-results artifact. Day-of-week irrelevant. |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Forge is an LLM-orchestration platform, not a geographic or data-ingestion system; scenario imported from a sibling project context does not apply. |

---

## Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks |
|---|---|---|
| Q1 | Who is the distinct actor for ADR-003 review? (Not the ROADMAP author.) | Stage 0.1 |
| Q2 | What are the concrete values for τ and α? (Domain decision, not a model choice.) | Stage 0.2 / ADR-004 |
| Q3 | What is the canary eval procedure for model version changes? | Stage 0.2 / ADR-006 |

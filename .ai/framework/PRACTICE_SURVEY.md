# CGAID Practice Survey — Retrofit Analysis

**v1.0 · 2026-04-19 · Owner: Framework Stewards · Status: Foundational Evidence**

---

## Purpose

This document is the **empirical foundation** of CGAID. The framework was developed through conversation between engineer and AI; without a retrofit pass, it would be extrapolation from opinion rather than distillation from practice. This survey addresses that gap.

**Method:** review of ITRP git history (2026-04-10 through 2026-04-19 on `features/data_pipeline` branch and merged PRs), plus relevant feedback memory entries. 18 incidents and decisions selected as representative of the larger set (~100 commits). Each classified against CGAID's 10 principles.

**Classification scheme:**

| Code | Meaning |
|---|---|
| **WOULD-PREVENT** | CGAID principle, strictly applied, would have caught the issue pre-code |
| **WOULD-AID** | CGAID principle improves likelihood of catching but doesn't guarantee prevention |
| **ALIGNED** | Practice already exhibits CGAID-like discipline; framework formalizes what's working |
| **EVOLUTION** | Meta-work on the toolkit itself (Zasada 9 and 10 in action) |
| **NEUTRAL** | Orthogonal to framework (UX polish, cosmetic, trivially correct) |
| **CONTRADICTED** | Practice actively violates or contradicts a CGAID principle |

---

## Findings Overview

**Tally across 18 representative incidents:**

| Classification | Count | % | Assessment |
|---|---|---|---|
| WOULD-PREVENT | 3 | 17% | Framework has direct leverage |
| WOULD-AID | 6 | 33% | Framework improves odds |
| ALIGNED | 4 | 22% | Practice is already CGAID-like |
| EVOLUTION | 2 | 11% | Toolkit-on-toolkit (Zasada 10) |
| NEUTRAL | 3 | 17% | Outside framework scope |
| CONTRADICTED | 0 | 0% | No active contradictions in sample |

**Key numbers for framework credibility:**

- **61% of incidents** have non-trivial CGAID leverage (WOULD-PREVENT + WOULD-AID + EVOLUTION). This is the framework's addressable surface.
- **22% of incidents** show practice already doing what CGAID recommends — validation that the framework reflects reality, not wishful thinking.
- **0% contradictions** in this sample — practice and framework are not actively in conflict. This is a credibility signal, but sample is small.
- **"Fix X found by Y" antipattern appears in 8 commits** — the single most common pattern. Framework must address this specifically.

---

## Top Patterns (What Actually Happens Here)

### Pattern A — Post-hoc discovery ("Fix X found by Y")

**Incidence:** 8+ commits in 10 days. The single most common pattern.

**Evidence:**
- `3846290` Fix 4 issues found by deep-verify of restore-related files
- `0c368b7` Fix 2 critical bugs found by integration tests
- `2bf5f2d` Fix misleading ERROR logs found by production audit
- `b4a0f84` Fix 2 bugs found by stateful integration tests
- `6ee9561` Fix settlement report: remove incorrect date filter that excluded 96% of settlements
- `3996b9a` Fix double-counting: revert beginning_balance and PP to RAW amounts
- `5ece52f` Auto load disabled for all countries — no data will be loaded until fixed
- `f6d24dc` Fix: cascade_restore now invalidates reports (Phase 5 TODO resolved)

**What it means:** the bug was in code; test/audit found it. This is *better* than production finding it — testing is working. But CGAID's Zasadas 3 (understanding precedes implementation), 4 (plan exposes risk), and 5 (tests target failure) target the *earlier* surface: planning and risk analysis, not post-hoc testing.

**Honest assessment:** practice has strong reactive discipline (tests, audits, deep-verify). The framework's unique contribution would be **shifting discovery from post-hoc testing to pre-code planning** — especially for issues rooted in filter logic, CTEs, cascade invalidation, and error reporting.

**Framework action (T2.x):** Stage 2 artifact "Execution Plan" should include explicit **"What could give misleading signals?"** subsection covering log correctness, filter coverage ranges, CTE row volumes. Applied to `6ee9561`: would the date filter have passed a pre-code sanity check *"does this filter exclude more than 10% of known volume?"*? Likely yes.

### Pattern B — Cascade / propagation / idempotency bugs

**Incidence:** 5+ commits.

**Evidence:**
- `f6d24dc` Fix: cascade_restore now invalidates reports (Phase 5 TODO resolved)
- `318f74a` Cascade idempotency
- `71fa577` Remove auto-reactivation in override restore (was breaking idempotency)
- `c31b116` Fix: supplier_codes not in scope for timeline BUY write
- `bf66299` Fix: restore now finds buy_run by execution_id field (not just doc ID)

**What it means:** these are the hardest bugs. Cascade implications aren't visible until tested against stateful scenarios. `71fa577` explicitly says "auto-reactivation was breaking idempotency" — an assumption about safety turned out wrong when composed with other operations.

**CGAID gap — identified:** the framework's kontrakt operacyjny says "every non-trivial assumption tagged." In cascade scenarios with 20+ dependent decisions, strict application floods the output. Framework does not have a pattern for **cascade decision compression** — representing a family of related assumptions as one tagged statement.

**Framework action (T2.x):** add to `.ai/CONTRACT.md` guidance: "Assumptions in cascade/propagation contexts may be tagged at the invariant level (e.g., 'ASSUMED: restore preserves idempotency across N>1 invocations') rather than per-step."

### Pattern C — Data correctness in financial reporting

**Incidence:** 6+ commits focused on settlement calculation and report accuracy.

**Evidence:**
- `6ee9561` Fix settlement report: date filter excluded 96% of settlements
- `3996b9a` Fix double-counting: revert beginning_balance and PP to RAW amounts
- `482312f` Fix PP report: show all outstanding with NET amounts
- `05376c1` Fix ITRP beginning balance: use NET outstanding
- `2247357` Fix settlement Row Type 1/2: include all purchased document types
- `4450ff1` Fix settlement Row Type 1: include collected_amount via LEFT JOIN

**What it means:** settlement logic touches client financial reality. Most were caught because user or client verified behavior and it didn't match expectation — this is **Zasada 6 in action** ("Code is not the outcome. Verified behavior is."). Practice already embodies this.

**Honest observation:** `6ee9561` (96% of settlements excluded) is the incident most directly addressed by a stricter Stage 1. An inconsistency hunt comparing filter output volume to known settlement volume from source data would have caught it in planning.

**Framework action (T1):** add to Stage 1 Evidence checklist: "For any filter, CTE, or aggregation introduced, state expected output volume range. Flag any assumption that would exclude >10% of input." This is a single-bullet addition with high leverage.

### Pattern D — Meta-practice evolution (skill / tooling)

**Incidence:** 4+ commits in 10 days.

**Evidence:**
- `a7bb4ab` Harden skills: mandatory data flow trace + evidence requirement
- `f6ff5c0` Add mandatory py_compile syntax check to preflight and develop skills
- `2498976` Skills
- `0caaaf5` Clean up skills
- `bef09eb` Pattern

**What it means:** the toolkit is evolving continuously. This is **Zasada 9 ("We control our tools") + Zasada 10 ("Every failure improves the system")** manifest in real practice, without framework yet existing to name them.

**Honest observation:** this pattern is the **strongest evidence that CGAID is distilled from real practice, not imposed from above**. The behaviors Zasada 9 and 10 describe were already happening. Framework formalization adds governance (Skill Change Log as artifact #8) but does not create the behavior.

### Pattern E — Live side-effects in edge-case tests (from memory)

**Source:** `feedback_live_side_effects.md` — "Never hit mutating endpoints on live env for edge-case tests; read full side-effect graph first (refresh_*, disable_*, audit) — fake IDs still trigger unconditional flag flips."

**What happened:** a test against a supposedly-safe endpoint with a fake ID triggered real flag flips on the live environment. The plan did not trace the full side-effect graph before testing.

**CGAID response:** **Zasada 4 (the plan exposes risk, not just work).** Applied to this incident: Stage 2 Execution Plan should include a **"side-effect graph"** artifact before any test against a real environment — enumerating every function the call path touches and which of them mutate state, external systems, or flags.

**Framework action (T2.x):** add to Stage 2 artifacts: **"Side-effect map"** for any feature that interacts with external systems, production data, or mutating operations. Required for Standard and Critical tiers; optional for Fast Track (though the incident shows this is risky — fake-ID test was presumed Fast Track).

**This incident alone justifies a framework amendment.** It's the kind of failure that memorialized itself into a permanent feedback rule — which is exactly what Zasada 10 describes.

### Pattern F — Naming, UX, cosmetic

**Incidence:** 10+ commits.

**Evidence:**
- `176f08b` Asset type "Other" configurator of the name
- `ac9a665` Countries alphabetic sorting
- `28c382f` Country / currency dropdown UI fix
- `831df8e` Dashboard spinner during refresh
- `a590aac` Reporting dates - showing only one date

**What it means:** these are Fast Track candidates. Framework is orthogonal; Zasada 7 (review) applies but full ceremony would be overhead.

**Framework action:** confirmed Adaptive Rigor's Fast Track tier is correct. These commits validate that the tiering scheme has real-world application, not just theoretical merit.

---

## Eighteen Representative Incidents (Classified)

| # | Commit | Date | Description | Class | Principle(s) | Notes |
|---|---|---|---|---|---|---|
| 1 | `6ee9561` | 04-13 | Fix settlement report: date filter excluded 96% of settlements | **WOULD-PREVENT** | 1, 4, 5 | Volume sanity-check in Stage 1 would catch |
| 2 | `3996b9a` | 04-13 | Fix double-counting: revert beginning_balance and PP to RAW | WOULD-AID | 6, 8 | Stage 4 verify against known totals |
| 3 | `f6d24dc` | 04-14 | Fix: cascade_restore now invalidates reports | **WOULD-PREVENT** | 4 | Side-effect graph in Stage 2 |
| 4 | `71fa577` | 04-11 | Remove auto-reactivation in override restore (broke idempotency) | WOULD-AID | 3 | "Assumption that behavior is safe" should tag |
| 5 | `c31b116` | 04-11 | Fix: supplier_codes not in scope for timeline BUY write | WOULD-AID | 8 | End-to-end traceability flagged scope issue |
| 6 | `351ac6a` | 04-10 | Fix: rows_per_supplier fallback used table name instead of supplier code | NEUTRAL | — | Subtle bug; caught by observation, framework orthogonal |
| 7 | `3846290` | 04-11 | Fix 4 issues found by deep-verify of restore-related files | ALIGNED | 7 | Practice already using verification skill |
| 8 | `0c368b7` | 04-11 | Fix 2 critical bugs found by integration tests | ALIGNED | 5 | Tests target failure — already in practice |
| 9 | `2bf5f2d` | 04-11 | Fix misleading ERROR logs found by production audit | **WOULD-PREVENT** | 6 | Logs were fluent but wrong — Zasada 6 directly |
| 10 | `a7bb4ab` | 04-10 | Harden skills: mandatory data flow trace + evidence requirement | EVOLUTION | 9, 10 | Zasada 10 in real time |
| 11 | `f6ff5c0` | 04-10 | Add mandatory py_compile syntax check to preflight skills | EVOLUTION | 10 | Incident → tooling improvement, textbook |
| 12 | *live side-effects* | recent | Fake-ID test triggered real flag flips on live | WOULD-AID | 4, 5 | Side-effect graph required |
| 13 | `176f08b` | 04-18 | Asset type "Other" configurator of the name | NEUTRAL | — | Fast Track candidate |
| 14 | `6d4160a` | 04-14 | Legal entities - list fixed | NEUTRAL | — | UX fix, Fast Track |
| 15 | `69a50cb` | 04-18 | New legal entities only when name starts with country name | WOULD-AID | 3 | Client requirement clarification — Stage 1 could surface earlier |
| 16 | `dbe7966` | 04-11 | Add integration tests for restore + override versioning | ALIGNED | 5 | Edge cases first-class in practice |
| 17 | `318f74a` | 04-11 | Cascade idempotency | WOULD-AID | 4 | Plan would surface idempotency as risk |
| 18 | `b4a0f84` | 04-11 | Fix 2 bugs found by stateful integration tests + add 5 stateful scenarios | ALIGNED | 5 | Practicing Zasada 5 directly |

---

## CGAID Alignment Assessment (Per Principle)

### Strong principles (evidence of real leverage)

- **Zasada 1 (AI under contract)** — incidents #1, #4 show untagged assumptions becoming bugs. Framework would have forced surfacing.
- **Zasada 4 (plan exposes risk)** — incidents #3, #12, #17 directly addressed. Side-effect tracing and cascade reasoning both need explicit Stage 2 artifact support.
- **Zasada 5 (tests target failure)** — incidents #7, #8, #16, #18 show practice already does this well. Framework formalizes.
- **Zasada 6 (verified behavior)** — incident #9 (misleading logs) is textbook Zasada 6 application.
- **Zasada 9 + 10 (toolkit evolution / system improves)** — incidents #10, #11 are these principles in real time. Framework describes what's already happening.

### Principles needing more operational support

- **Zasada 3 (understanding precedes)** — applied weakly across incidents. Practice relies on fast iteration + testing more than upfront clarity. Risk: Stage 1 Evidence becomes the weakest gate because pressure favors coding over clarification.
- **Zasada 8 (end-to-end traceable)** — incidents #2, #5 involve scope/propagation. Practice does this retrospectively (via tests) more than proactively (via traceability artifacts).

### Principles with no incident evidence in this sample

- **Zasada 2 (evidence over fluent output)** — no incident in this window is specifically about AI-generated code that looked right but wasn't. This may be because kontrakt is already enforced, or because sample is too small.
- **Zasada 7 (review mandatory)** — no incident shows review breakdown; all commits went through PR flow (visible in merge patterns).

---

## Identified Framework Gaps (From Real Practice)

### Gap 1 — Cascade decision compression

**Evidence:** Pattern B (5+ cascade/idempotency commits).
**Gap:** kontrakt operacyjny requires "every non-trivial assumption tagged." In cascade scenarios, strict application floods output.
**v1.4 action:** amend `.ai/CONTRACT.md` with cascade-level tagging guidance (invariant-level rather than step-level).

### Gap 2 — Side-effect graph as Stage 2 artifact

**Evidence:** Pattern E (live side-effects incident), incident #3 (cascade_restore).
**Gap:** framework's 10 artifacts do not include side-effect mapping. Zasada 4 names the risk but doesn't instrument it.
**v1.4 action:** add **artifact #11 "Side-Effect Map"** — required for Standard and Critical tiers when feature touches external systems, production data, or mutating operations.

### Gap 3 — Volume/coverage sanity for filters and aggregations

**Evidence:** Pattern C, especially incident #1 (96% of settlements excluded).
**Gap:** Stage 1 Evidence does not explicitly require volume checks for newly-introduced filters, CTEs, or aggregations.
**v1.4 action:** add to Evidence checklist: *"For any filter, CTE, or aggregation introduced: state expected output volume range; flag if assumption would exclude >10% of input."*

### Gap 4 — Stage 1 under deadline pressure

**Evidence:** many fixes arrive post-hoc because initial implementation did not surface the edge case.
**Gap:** no operational mechanism makes skipping Stage 1 costly when deadline pressure rises. Adaptive Rigor's Fast Track is the escape valve.
**v1.4 action:** formalize the trade. Fast Track permissible only when: (a) change is local (single function, no cross-module), (b) no external-system interaction, (c) test coverage exists. Any condition failing → Standard tier.

---

## Evidence Against the Framework (Honest Negative Findings)

A complete retrofit must report what the framework does *not* explain.

**Negative 1 — Framework offers no guidance for SQL-heavy, report-generation domains.**
Pattern C is 6+ commits in 10 days. They cluster around CTEs, filters, JOIN logic, aggregation correctness. This is a specific technical domain (financial reporting SQL) where CGAID's principles apply in general but do not help in particular. A SQL-aware companion document (`.ai/SQL_PATTERNS.md`?) would be useful.

**Negative 2 — Framework is silent on UX/cosmetic work.**
Pattern F is 10+ commits. Framework has Fast Track tier but says nothing about how to discipline UX decisions (consistency with design system, accessibility, responsive behavior). This is a gap if ITRP becomes a UX-heavy engagement.

**Negative 3 — Short observation window.**
18 incidents over 10 days is a small sample. A 6-month retrospective would likely surface patterns not visible here (seasonal client behavior, quarterly report generation, etc.). This survey is directional, not definitive.

**Negative 4 — No incident in sample showed AI behavior failure.**
All incidents are human-engineer + AI collaborative work. None show AI failing in a way the kontrakt would prevent. Either kontrakt is already working, or sample is too small to reach base rate of AI-specific failures. Framework's central claim (AI under contract) is not *refuted* but also not *demonstrated* in this sample.

---

## Recommendations (Tiered)

### T1 — Into v1.4 immediately

1. **Add Stage 1 volume check bullet** for filters/CTEs/aggregations (addresses Pattern C, incident #1).
2. **Add artifact #11 Side-Effect Map** to Framework (addresses Pattern E, incident #12).
3. **Cascade-level tagging guidance** in `.ai/CONTRACT.md` (addresses Pattern B).
4. **Fast Track preconditions** explicit (addresses Pattern A / Gap 4).

### T2 — v1.5+

5. SQL-specific companion patterns (`.ai/SQL_PATTERNS.md`).
6. 6-month longitudinal resurvey (baseline for metric comparisons).
7. AI-behavior incident log (separate from general incidents) to measure kontrakt effectiveness directly.

### T3 — Ongoing

8. Quarterly practice survey as part of adoption audit.
9. Pattern catalog maintained — each new pattern name gets entry (A, B, C, D, E, F currently).

---

## Honest Limitations of This Survey

- **Observer bias:** I (Claude) am the same agent that wrote the framework. My classification of "WOULD-PREVENT" vs. "WOULD-AID" is not blind.
- **Sample size:** 18 incidents, 10-day window. Claims of percentages are indicative, not statistically valid.
- **Missing context:** I don't have full PR discussions, review comments, or client interaction logs. Some "Fix X" commits may have deeper stories not visible in commit messages.
- **No counterfactual data:** I cannot prove any incident would have been prevented by CGAID; I can only reason about likelihood.
- **Git log does not reveal cultural patterns:** how engineers actually prioritize, what pressure they feel, which decisions they mute — none of this is in commits.

Framework Stewards should commission a **second survey by a human engineer** familiar with the codebase but uninvolved with framework authorship to verify or refute findings.

---

## Changelog

- **v1.0 (2026-04-19)** — Initial survey. 18 incidents from 10-day window on `features/data_pipeline` branch, classified against 10 principles. 4 framework gaps identified (cascade compression, side-effect map, volume check, Fast Track preconditions). 4 honest negatives reported. Recommendations tiered T1–T3. Limitations section included.

---

*End of Practice Survey v1.0. This document is the evidence foundation for CGAID. It should be re-run quarterly and on major framework version changes.*

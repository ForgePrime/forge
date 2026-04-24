# QUALITY_EVALUATION.md — L7 Quality & Outcome Evaluation Specification

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-25
**Depends on:** PLAN_QUALITY_ASSURANCE (D.5 FailureMode + α-gate), PLAN_LLM_ORCHESTRATION (cost from `llm_calls`), PLAN_MEMORY_CONTEXT (B.4 fidelity test foundation), PLAN_GOVERNANCE (G.3 7 metrics service), MVP_SCOPE.md §L7 (3 benchmark tasks).
**Source spec:** MASTER_IMPLEMENTATION_PLAN §3 L7 (5 outcomes); MVP_SCOPE.md §L7 (Task-bench-01/02/03).
**Scope:** end-to-end outcome evaluation. The five outcomes per MASTER §3 L7 are: **Quality, Cost, Latency, UX, Reliability**. This doc operationalizes each into measurable signals + thresholds + auto-graders.

> **Known unverified claim (CONTRACT §A.6):** Quality is empirical. This doc specifies the *measurement infrastructure* (benchmark harness, auto-graders, outcome thresholds), not the absolute quality of LLM outputs. Quality scores depend on (a) the benchmark task quality, (b) the reference solutions, (c) the auto-grader's ability to score correctness — each of these is a calibration concern. Phase 1 MVP exit gate requires score ≥ 0.6; that threshold is itself based on an `[ASSUMED]` calibration that needs Phase 2 design-partner data to verify.

---

## 1. The 5 outcomes (MASTER §3 L7)

| Outcome | What it measures | Target (MVP) | Target (Phase 2) | Source signals |
|---|---|---|---|---|
| **Quality** | Does the Change satisfy the Issue's intent and pass tests? | ≥ 0.6 on 3-task bench | ≥ 0.7 average across 10+ design-partner Tasks | benchmark auto-grader; design-partner accept rate |
| **Cost** | USD per Task (Issue → merged PR) | < $2.00 P95 | < $1.00 P95 | `llm_calls.cost_usd` aggregated per Execution chain |
| **Latency** | Wall-clock from Issue creation to PR open | < 15 min P95 | < 8 min P95 | `Execution.created_at` to `Change.pr_url_set_at` |
| **UX** | Onboarding time + error-recovery time | Onboarding < 1h | < 30 min average | Design-partner timed runs + friction log |
| **Reliability** | % Executions completing without unhandled error | ≥ 99% | ≥ 99.9% | `Execution.status terminal != 'failed'` over rolling window |

**No outcome is independent.** Cost trades against Quality (cheaper model = lower Quality typically). Latency trades against Quality (more retries = better Quality but worse Latency). UX trades against Reliability (faster onboarding may skip safety checks). The L7 dashboard surfaces all 5 simultaneously so trades are visible.

---

## 2. Benchmark harness

### 2.1 The 3 MVP benchmark Tasks (per MVP_SCOPE §L7)

**Task-bench-01:** Add a boundary check to an existing endpoint.
- **Starting state:** git commit hash `bench01-start` on branch `bench01-base`.
- **Issue text:** "The `/api/users/{id}/orders` endpoint should return 404 when user_id does not exist, instead of empty array."
- **Target AC:** Endpoint returns 404 on `GET /api/users/9999/orders` where user 9999 does not exist; existing behavior preserved for valid user IDs.
- **Reference solution:** `tests/benchmarks/bench01-reference.diff` — modifies route handler + adds 3 test cases.
- **Auto-grader:** runs all tests; computes pass rate + AST similarity to reference solution.

**Task-bench-02:** Fix a bug in a pure function.
- **Starting state:** branch `bench02-base` contains an off-by-one error in pagination logic.
- **Issue text:** "Pagination at `/api/items?page=2` returns items 11-20, but should return items 11-21 inclusive (1-indexed pages with page_size=10)."
- **Target AC:** Existing failing test `tests/test_pagination.py::test_page_2_inclusive` transitions FAIL → PASS; no other test regresses.
- **Reference solution:** `tests/benchmarks/bench02-reference.diff` — single-line fix in `pagination.py`.
- **Auto-grader:** test pass rate before/after; AST similarity to reference.

**Task-bench-03:** Add input validation to a form handler.
- **Starting state:** branch `bench03-base` contains route `POST /signup` with no validation.
- **Issue text:** "Signup endpoint should reject email addresses without `@` and passwords < 8 chars."
- **Target AC:** New tests `tests/test_signup.py::test_invalid_email_rejected` and `test_short_password_rejected` PASS; existing `test_signup_happy_path` still passes.
- **Reference solution:** `tests/benchmarks/bench03-reference.diff` — adds Pydantic validators.
- **Auto-grader:** all tests pass; AST similarity.

### 2.2 Auto-grader specification

```python
class BenchmarkAutoGrader:
    def grade(task: BenchmarkTask, forge_output_diff: str) -> BenchmarkScore:
        # 1. Apply forge_output_diff to bench-base branch in disposable worktree
        # 2. Run pytest tests/ on resulting state
        # 3. Compute test_pass_rate = passed / total
        # 4. Compute ast_similarity = ts(forge_diff, reference_diff)
        #    where ts() uses difflib + AST normalization (whitespace/comment-insensitive)
        # 5. Score = 0.6 * test_pass_rate + 0.4 * ast_similarity
        # 6. Return BenchmarkScore(score, breakdown, evidence_refs)
```

**Determinism:**
- Same `(task, forge_output_diff)` → same `BenchmarkScore` (pure function over fixed inputs).
- Pytest invoked with fixed seed via D.1 deterministic test harness.
- AST normalization removes formatting noise so Forge can use any equivalent code style.

**Output evidence:**
- Per-Task: pytest output verbatim, AST similarity computation, final score breakdown.
- All persisted to `EvidenceSet(kind='test_output')` with reproducer_ref pointing at the grader script.
- `forge audit <change-id>` includes benchmark scores when Change came from a benchmark Task.

### 2.3 Adding new benchmark Tasks (Phase 2+)

Phase 2 adds 7+ Tasks to widen coverage:
- Add property-test driven (hypothesis fuzzes inputs, Forge writes the property).
- Multi-file refactor (Forge edits 5+ files coordinatedly).
- Bug fix from real production incident (anonymized PRACTICE_SURVEY-style).
- New endpoint with full CRUD.
- Migration with backfill.
- Type-error fix (mypy regression).
- Performance regression fix.

Each new Task carries:
- Starting commit hash.
- Issue text (≤ 200 words; reflects realistic dev request).
- Auto-gradable AC.
- Reference solution with explanatory README.

Adding a Task requires PR + distinct-actor review (CONTRACT §B.8).

---

## 3. Outcome measurement infrastructure

### 3.1 Quality measurement

**MVP signal:** benchmark score from §2.

**Phase 2 signals:**
- Design-partner thumbs-up/down on PR review (binary per Change).
- Post-merge regression rate (Findings emitted within 7 days of merge per Change).
- AC-satisfaction rate (per E.7 EpistemicProgressCheck deltas + G.9 main-task audit).

**Quality dashboard:**
- Histogram of benchmark scores over time (rolling 30-day window).
- Acceptance rate by ICP segment (Phase 2 — when multiple design partners).
- Per-capability quality trend (e.g., "Forge is good at boundary checks but weak on multi-file refactors").

### 3.2 Cost measurement

**Source:** `llm_calls.cost_usd` aggregated per Execution chain per Task.

**Cost-per-Task formula:**
```
cost_per_task = SUM(llm_calls.cost_usd
                   WHERE execution_id IN executions_for_task(task_id))
```

**Cost dashboard (L3.6):**
- Per-Task histogram + P50/P95/P99.
- Cost-per-PR-merged (vs cost-per-Task — accounts for BLOCKED/abandoned).
- Cost trend over time (rolling 30-day window).
- Cost by model (Haiku / Sonnet / Opus mix per L3.4 routing).
- Cost overrun rate (BudgetGuard-blocked Executions / total Executions).

**Pre-flight cost prevention:** L3.6 BudgetGuard halts before τ_cost (per ADR-004) exceeded. This means cost overrun is mechanically capped, not measured-and-mourned.

### 3.3 Latency measurement

**Source:** timestamps on Execution and Change entities.

**Latency-per-Task formula:**
```
latency_per_task = MAX(Change.pr_url_set_at) - MIN(Execution.created_at)
                   WHERE task_id matches
```

**Component breakdown (Phase 2):**
- Webhook → Execution.started: typically < 5s; > 30s indicates webhook backlog.
- Execution.started → first LLM call: typically < 10s; > 60s indicates context budget thrashing.
- LLM call total time: median ~30s with Sonnet; > 5min indicates retry storm.
- Test run time: depends on repo; budget < 5 min on MVP-scope repos.
- PR open: < 10s typical.

**Latency dashboard:** P50/P95/P99 trend; outliers flagged for forensic.

### 3.4 UX measurement

**Onboarding signal:** timed design-partner runs.
- 5 runs per release; record time to first Execution.
- Friction log captures every error encountered + resolution time.
- Pass criterion: ≥ 3/5 runs under 1h on first attempt.

**Error-recovery signal (Phase 2):**
- For each BLOCKED Execution, time from BLOCKED → unblocked.
- Median, P95.
- Categorize by `blocked_reason`: ambiguity, cost overrun, auth, etc.
- Aim: median resolution time per category < 5 min.

### 3.5 Reliability measurement

**MVP signal:** Execution-level success rate.
```
reliability = 1 - (count(Execution WHERE status='failed') /
                   count(Execution WHERE status terminal))
```

Excludes BLOCKED state — BLOCKED is *expected* behavior (system halted on uncertainty), not a failure.

**Phase 2 signal:** SLO-level reliability — for each "promise" Forge makes (e.g., "every accepted Change has full evidence trail"), measure compliance rate. Promises:
- Every accepted Change has complete G.9 10-link causal chain (audited nightly).
- Every llm_calls row has cost + tokens + model recorded.
- Every BLOCKED Execution has `blocked_reason` populated.
- Every Decision has ≥ 1 EvidenceSet link.
- Every architectural Decision has ≥ 2 candidates with argmax selection.

Reliability per promise tracked separately; aggregate is min over all.

---

## 4. Feedback loop (closes Implementation Closure Theorem L7 — MEASURED + RECOVERABLE)

The five outcomes feed back into the system as follows:

```
Outcome signal → Threshold check → Action

Quality < 0.6:    →  Open Finding(severity=HIGH, kind='quality_regression')
                     → Adversarial fixture proposed (D.4)
                     → Rule candidate proposed for prevention (G.4)
                     → Steward review queue

Cost > τ_cost:     →  L3.6 BudgetGuard pre-flight halts new Executions
                     → Finding(severity=HIGH, kind='cost_overrun')
                     → Routing weights re-tuned (ADR-006 supersession path)

Latency > 15 min:  →  Finding(severity=MEDIUM, kind='latency_regression')
                     → Forensic via tracing (Phase 2 OTel)
                     → ContextBudget tuning candidate

UX onboarding > 1h: →  Friction log entry
                     → UX_DESIGN.md error message updates
                     → Runbook updates (OPERATIONS.md §7)

Reliability < 99%: →  Per-promise diagnostic
                     → Root-cause Decision (P21: ≥2 alternatives)
                     → Invariant added (E.2) if root cause is structural
```

**Implementation Closure Theorem L7 mapping:**
- **EXIST:** the 5 outcomes are concretely defined (§1) with measurement infrastructure (§3).
- **CONNECTED:** each outcome flows from L1+L2 entities (Executions, Changes, llm_calls, etc.).
- **CONTROLLED:** thresholds set; pre-flight controls (BudgetGuard) prevent breach where possible.
- **MEASURED:** dashboards + signals defined; G.3 7 metrics service implements aggregations.
- **RECOVERABLE:** feedback loop above triggers concrete recovery actions per outcome class.

---

## 5. Phase 1 MVP exit criteria (this layer)

- [ ] Benchmark harness operational: `python scripts/run_benchmarks.py` exits 0 with score for each of Task-bench-01/02/03.
- [ ] Auto-grader deterministic: same input → same score across 10 runs (T1 in `tests/benchmarks/test_grader_deterministic.py`).
- [ ] All 3 benchmark Tasks score ≥ 0.6 on Forge MVP via Sonnet-only routing.
- [ ] Cost P95 < $2.00 measured over the 3 benchmark Tasks × 10 runs each = 30 data points.
- [ ] Latency P95 < 15 min measured over the same 30 runs.
- [ ] Onboarding < 1h verified on 5 design-partner sessions per UX_DESIGN.md §6.
- [ ] Reliability ≥ 99% on benchmark runs (29/30 Executions terminal-non-failed; 1 fail acceptable as outlier).
- [ ] G.3 7 metrics endpoint returns numerics (not None) for all 7 (per PLAN_GOVERNANCE.md G.3).
- [ ] Quality, Cost, Latency dashboards return data (UX scaffolded, Reliability counts visible).

---

## 6. Phase 2 expansion criteria

Phase 2 extends:
- Benchmark Tasks: 3 → 10 (add the 7 categories from §2.3).
- Quality threshold: 0.6 → 0.7.
- Cost: $2 → $1 P95.
- Latency: 15min → 8min P95.
- Onboarding: 1h → 30min average.
- Reliability: 99% → 99.9%.

Phase 2 also adds:
- Per-ICP-segment quality breakdown (regulated industry vs OSS vs internal team).
- Cost regression alerts (week-over-week 20% increase → Finding).
- Quality regression alerts (rolling 7-day average drop > 0.05 → Finding).

---

## 7. Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | Auto-grader rejects empty diff with explicit `BenchmarkScore(score=0, reason='empty_diff')`; benchmark Tasks all have positive starting state (no missing branches); empty `llm_calls` for a Task → cost reported as 0, not crash |
| 2 | timeout_or_dependency_failure | Handled | Benchmark harness has per-Task timeout (`FORGE_BENCH_TIMEOUT_SEC` default 1800); timeouts captured as `BenchmarkScore(score=0, reason='timeout', partial_evidence=...)`; metric aggregation tolerates missing data points (P95 over available samples) |
| 3 | repeated_execution | Handled | Benchmark Tasks are reproducible from fixed git commits; `run_benchmarks.py --task=T --runs=N` produces N evidence-recorded runs; auto-grader is pure function over diff so same Task+diff → same score |
| 4 | missing_permissions | Handled | Local benchmarks run without external auth (no GitHub call); MVP_SCOPE benchmarks designed to run in worktrees without provider keys; failure of LLM provider → benchmark score `0` with reason='llm_unavailable' rather than abort |
| 5 | migration_or_old_data_shape | Handled | Benchmark reference solutions versioned per branch; AST similarity uses normalized form so harmless format changes don't regress score; `BenchmarkScore` JSON shape versioned per ADR-013 (same ADR as `forge audit`) |
| 6 | frontend_not_updated | Handled | Quality/Cost/Latency dashboards specified in UX_DESIGN.md §5.1; their absence in MVP is acknowledged; benchmark scores accessible via CLI `forge bench show` (Phase 2) |
| 7 | rollback_or_restore | Handled | Benchmarks reproducible from base commits — no permanent state to roll back; auto-grader changes versioned in repo |
| 8 | monday_morning_user_state | Handled | Benchmark harness stateless per run; produces fresh worktree, runs grader, tears down; no overnight accumulation |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Benchmarks are code-level; no geographic data dimension |

---

## 8. Open questions

| # | Question | Blocks |
|---|---|---|
| Q1 | AST similarity tooling: `difflib` baseline vs tree-sitter-based AST diff? Trade-off: difflib simpler, AST-diff more accurate. MVP defaults to difflib + AST normalization | Phase 2 grader accuracy |
| Q2 | Quality threshold 0.6 is `[ASSUMED]` — must be re-calibrated when first 5 design partners produce real-world Tasks (Phase 2). Document in `tests/benchmarks/threshold_calibration.md` | Phase 2 calibration |
| Q3 | Per-ICP quality segmentation requires multiple design partners — when do we have enough data to slice meaningfully? Tentative: ≥ 3 partners × ≥ 5 Tasks each = 15 data points minimum | Phase 2 reporting |
| Q4 | Cost P95 < $2 calibration: is this a reasonable target on Sonnet-only? Initial spec from MVP_SCOPE; needs verification on 30+ runs | MVP exit gate |
| Q5 | Latency P95 < 15 min: same calibration concern. Includes test-run time which varies by repo | MVP exit gate |
| Q6 | Reliability denominator (terminal Executions) — should BLOCKED count as "intervention required" rather than purely-non-failure? Currently excluded from numerator, included in denominator. Argue both ways | Phase 2 metric refinement |
| Q7 | Auto-grader pseudonymization for shared benchmarks — if Phase 2 publishes benchmark Tasks publicly, do we sanitize for any leakage risk? Likely no since Tasks are synthetic | Phase 2 publish |

---

## 9. Implementation Closure Theorem mapping (the 7 layers, 5 attributes)

| Layer | EXIST | CONNECTED | CONTROLLED | MEASURED | RECOVERABLE |
|---|---|---|---|---|---|
| L1 Governance | ✓ (PLAN corpus) | ✓ (CausalEdge) | ✓ (Gates per stage) | ✓ (G.3 7 metrics) | ✓ (G.4 rule retirement) |
| L2 Execution Engine | ✓ (VerdictEngine) | ✓ (RuleAdapter) | ✓ (every transition) | ✓ (verdict_divergences) | ✓ (BLOCKED state) |
| L3 LLM Orchestration | ✓ (PLAN_LLM_ORCHESTRATION) | ✓ (consumes B.4, E.1) | ✓ (authority gate) | ✓ (llm_calls) | ✓ (FailureRecovery) |
| L4 UX | ✓ (UX_DESIGN.md) | ✓ (consumes L1+L2 entities) | ✓ (form validation) | ✓ (UX outcome §3.4) | ✓ (error messages, BLOCKED form) |
| L5 Integration | ✓ (INTEGRATIONS.md) | ✓ (adapter pattern) | ✓ (authority levels) | ✓ (per-adapter health) | ✓ (failure classification) |
| L6 Operations | ✓ (OPERATIONS.md) | ✓ (12-factor) | ✓ (env var validation) | ✓ (logs + /metrics) | ✓ (14 failure classes §5) |
| L7 Quality Eval | ✓ (this doc) | ✓ (consumes all L1-L6) | ✓ (thresholds) | ✓ (5 outcomes) | ✓ (feedback loop §4) |

All 7 layers × 5 attributes = 35 cells, all marked ✓ structurally. **Empirical** verification of each ✓ is the work of the implementation phase + Phase 1 MVP exit gate, not this doc.

---

## 10. Authorship + versioning

- v1 (2026-04-25) — initial L7 spec; 5 outcomes; 3 MVP benchmark Tasks; auto-grader; feedback loop; Implementation Closure 7×5 mapping.
- Updates require explicit version bump + distinct-actor review per ADR-003.

# Service Level Objectives — Forge Platform v1.0

**Status:** draft-published · **Review cadence:** monthly for first 3 months, then quarterly

SLOs define what "good" means numerically. Forge has not yet been load-tested
at scale, so the v1.0 numbers below are **aspirational targets** based on
engineering intent, not measured baselines. They WILL change once the load
test baseline lands (Roadmap Phase 2 week 6).

Every SLO here must be:
- **Measurable** — tied to a metric that exists or a test that can be run
- **Realistic** — achievable with current Forge architecture (not wishful)
- **Operationally meaningful** — breaching it triggers action, not just an alert

---

## SLO-1 — UI availability

**Target:** 99.5% of HTTP requests to `/ui/**` routes succeed (2xx/3xx) over a rolling 30-day window.

**Metric source:** app access log / FastAPI route counters.
**Error budget:** 3.6 hours/month downtime allowed.

**Breach action:**
- First minor breach (< 2h below target): retrospective, no alert escalation.
- Sustained breach (> 4h continuous): incident ticket, pause non-critical
  feature merges, focus on stability fix.

Out of scope: /api/v1/** — separate SLO (SLO-2).

---

## SLO-2 — API correctness

**Target:** 99.0% of `/api/v1/**` requests return a *semantically correct* response (2xx where success, expected 4xx where client error, 5xx NEVER except documented maintenance windows).

**Metric source:** response code distribution + structured error taxonomy.
**Error budget:** 1% of requests can be unexpected 5xx (bugs surfacing); > 1% triggers regression investigation.

**Breach action:** same as SLO-1.

---

## SLO-3 — Orchestrate p95 latency (simple feature task)

**Target:** p95 end-to-end `/orchestrate` run for a single-feature task with ≤ 3 AC completes under **120 seconds**.

**Metric source:** `OrchestrateRun.finished_at - started_at` aggregated weekly.
**Error budget:** N/A — this is a capacity/efficiency SLO, not an availability one.

**Breach action:**
- Drift > 180s p95 → audit Claude CLI duration trends + test_runner execution; likely cause is bloated context (retries growing prompt).
- Drift > 240s p95 → treat as regression; roadmap re-prioritization.

Out of scope: complex multi-objective runs, crafted-mode tasks, or objectives with > 10 KR.

---

## SLO-4 — Cost per task (guardrail)

**Target:** Mean cost of a successful feature/bug task delivery < **$1.50**.
**Hard ceiling:** no single task exceeds $10 without owner approval (enforced by `budget_guard.veto_check` today).

**Metric source:** `LLMCall.cost_usd` summed per `Execution`, filtered to
`Execution.status='ACCEPTED'`.

**Breach action:** if weekly average crosses $2.00, inspect cache-hit rate
and skill attachment load; likely prompt bloat.

---

## SLO-5 — Contract violation disclosure rate (trust SLO)

**Target:** ≥ 95% of contract violations (missing `[EXECUTED]` tag, silent
assumption, happy-path-only AC) are disclosed by the AI itself (visible
in delivery.reasoning or delivery.assumptions) BEFORE `contract_validator`
catches them.

**Metric source:** count of `WARNING` and `FAIL` rows in `ValidationResult`
that weren't anticipated by delivery.* sections. Computed manually until a
structured detector ships.

**Rationale:** this is THE CGAID-style trust SLO. A validator catching 5%
of drift is a healthy backstop; catching 50% means the AI is operating
un-disclosed and the validator is the entire safety net — too brittle.

**Breach action:** skills or prompt-parser tuning; not a system-quality
issue per se, but a contract-compliance one.

---

## SLO-6 — Backup + restore cycle

**Target:**
- **RPO (Recovery Point Objective):** 24 hours — at worst, last 24h of
  data can be lost.
- **RTO (Recovery Time Objective):** 4 hours — from incident declared
  to platform serving.

**Metric source:** dated pg_dump file age (from `platform/scripts/backup.sh`
output) + monthly restore verification (see `docs/DEPLOY.md`).

**Breach action:**
- RPO miss (no valid backup within 24h): P1 alert, fix backup pipeline
  before any new feature work.
- RTO miss (restore not completable in 4h in staging drill): review
  runbook, simplify steps, re-drill.

---

## SLO-7 — CI pipeline green on main

**Target:** 95% of pushes to `main` result in a green CI run (.github/workflows/ci.yml) within 15 minutes.

**Metric source:** GitHub Actions run success rate (once CI is activated).
**Error budget:** 1 failing main per 20 pushes (≈ 1-2 per week at typical cadence).

**Breach action:** investigate top failure categories; likely culprits
based on current audit: transient DB races in integration tests (already
known flaky), cold SQLAlchemy starts.

---

## What is NOT an SLO today (but probably should be)

- **Security vulnerability TTR** (time-to-remediate): no SLO because no
  baseline; start tracking after first pip-audit sweep completes.
- **GDPR subject request response time**: regulated (1 month max per
  Article 12(3)); operationally target 7 days.
- **Incident MTTR**: no aggregated data yet. Promote to SLO after 3 incidents.
- **Deploy frequency**: covered by DORA metrics; currently manual deploy
  = metric not meaningful.

---

## How to adjust

Changes to these SLOs require:
1. Problem statement (current target is wrong because…)
2. Proposed new target + rationale
3. At least one incident or load test that motivates the change
4. Update this file + CHANGELOG entry

Owner: engineering lead. Review cadence stated at the top.

---

## Changelog

- **v1.0 (2026-04-19, autonomous session)** — Initial draft-published
  SLO set. 7 SLOs covering availability (UI + API), latency (orchestrate
  p95), cost (per-task guardrail), trust (contract violation disclosure
  rate), DR (RPO/RTO), CI health. All v1.0 numbers are aspirational
  targets pending load test baseline (Roadmap Phase 2 week 6). Needs
  user review + adjustment to reflect real capacity envelope.

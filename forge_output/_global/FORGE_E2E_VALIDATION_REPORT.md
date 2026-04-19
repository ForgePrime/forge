# Forge E2E Validation Report — post-P1-P5 fixes

**Date:** 2026-04-19
**Scenario:** WarehouseFlow inputs (same SOW + email + glossary + NFR as the 2026-04-17 pilot)
**Forge state:** P1.1-P1.4 + P2.1-P2.6 + P3.1-P3.5 + P5.1-P5.3 shipped (343 unit tests green)
**Cost:** **$1.53** (analyze $0.16 + plan $0.25 + orchestrate $1.12)
**Outcome:** **partial — 0/2 tasks DONE, 1 FAILED** (T-001 rejected by P0-P99 contract validator after 3 attempts)

---

## 1. What this validation was designed to prove

The 2026-04-17 pilot accepted 3 false-positive deliveries (`available_qty` formula not actually computed in the service). The repair plan stacks defenses across P1-P5. This run tests the live pipeline after those fixes.

Setup (controlled bounded run):
- Fresh project `wh-validate-1776591084`, fresh signup, fresh org
- Ingested the 4 source docs from the original pilot (SRC-001..SRC-004, 6.5 KB total)
- Pre-configured 1 `challenger_check` on O-001 + 1 hook (`after_develop → MS-pytest-parametrize`) + budget caps ($1/task, $3/run)
- Capped at `max_tasks=2` to bound spend

---

## 2. Live observations — what fired vs. what didn't

| Fix | Exercised live? | Evidence |
|---|---|---|
| **P5.3** plan traceability gate | ✅ exercised, **passed correctly** | Claude's 7-task plan included `requirement_refs` for every task (e.g. `T-001`: `["SRC-001 §Funkcje punkt 1", "SRC-003 §Min stan alarmowy", "SRC-003 §SKU"]`). Gate didn't fire because the data was well-formed — exactly the "happy path" we want. |
| **P5.1** deps bootstrap | ✅ wired, no-op path | `result.workspace_infra.deps = {attempted: false, ...}` — workspace had no `requirements.txt` yet (Claude was supposed to create it in T-001 but never reached commit). The skip-path returned cleanly without error. Couldn't exercise the `pip install` happy-path without a successful prior task. |
| **P1.4** Execution.mode badge | ✅ persisted on the FAILED execution | DB query returned `Execution.mode='direct'` for T-001's only execution. Mode is captured even when status=FAILED. |
| **P1.2** hooks fire on task DONE | ❌ not exercised | No task reached DONE. `HookRun` count = 0 — confirms the hook is wired correctly (DONE-only) but couldn't be live-validated this run. Unit tests (9/9) cover the firing path. |
| **P1.3** challenger_checks injection | ❌ not exercised | Phase C runs only after a task is ACCEPTED. Zero challenger LLM calls. Unit tests (11/11) cover prompt injection. |
| **P1.1** pause/resume in loop | ❌ not exercised | Auto-pause was conditional on `tasks_completed=1`. Never reached. Unit tests (10/10) cover the gate + endpoint round-trip. |
| **P5.2** KR measurement findings | ❌ not exercised | Same — DONE-only. Unit tests (11/11) cover the failure-classification logic. |

---

## 3. Why T-001 failed all 3 attempts (the new finding)

**`fail_reason: Max retries (3) reached. Last fix_hint: AC evidence [2] must reference file path or test name`**

T-001 spec (Schema bazy danych: products, warehouses, warehouse_alarm_levels):
- AC-0: migration creates the 3 tables → verification=`test`
- AC-1: duplicate `(product_id, warehouse_id)` rejected → verification=`test`
- AC-2: `alembic downgrade -1 && alembic upgrade head` is reversible → verification=`command`

Claude's deliveries provided "evidence" for AC-2 (the command-verification AC) without a concrete file path or test name. The P0-P99 contract validator's `must_reference_file_or_test` check rejected every attempt.

**This is correct behavior.** The validator is doing its job — refusing self-reported "verified manually" evidence. But it's TOO strict for `verification='command'` ACs where the evidence naturally is "command output", not a file path.

### New gap surfaced — **P5.5 in the repair plan**

**The validator's `must_reference_file_or_test` rule should soften for `verification='command'` ACs.** It should accept:
- Output excerpt that includes the command name (e.g. "alembic downgrade output: ... OK")
- File path of the migration / script being exercised

Without this, command-verifiable ACs become an unfixable bottleneck — Claude can't satisfy a check that's structurally impossible for the AC type.

---

## 4. Per-call cost ledger

| # | Purpose | Cost | Duration | Tokens (in/out) | Outcome |
|---|---|---:|---:|---:|---|
| 280 | analyze | $0.162 | 121s | 2 / 7,168 | 7 objectives + 14 KRs extracted |
| 282 | plan O-001 | $0.254 | 197s | 2 / 13,166 | 7 tasks generated, all with `requirement_refs` |
| 306 | execute T-001 attempt 1 | $0.729 | 537s | 19 / 17,879 | REJECTED by validator |
| 307 | execute T-001 attempt 2 | $0.258 | 114s | — | REJECTED by validator |
| 308 | execute T-001 attempt 3 | $0.131 | 66s | — | REJECTED by validator |
| **TOTAL** | | **$1.534** | **17m** | | T-001 FAILED |

Comparison to 2026-04-17 pilot (T-001 only): **$1.74 / 4 attempts.** Roughly the same cost profile; this run was 1 attempt fewer.

---

## 5. Verdict per repair-plan KR

| KR | Status | Note |
|---|---|---|
| KR1 — P1 items DONE 4/4 | ✅ done (unit-tested) | Live: only P1.4 actively exercised |
| KR2 — P2 items DONE 6/6 | ✅ done (unit-tested) | Live: P2.4 budget config consulted (not breached, so no enforcement seen) |
| KR3 — mockup functional coverage ≥ 85% | ✅ ~90% | Live: confirmed plan-side flows work end-to-end; orchestrate-side flows failed before deeper layers ran |
| **KR4 (new)** — pilot fail-throughs caught | 🟡 inconclusive | The 3 stock-service fail-throughs from the pilot don't exist anymore (service was fixed offline). This run failed *before* running tests, so we couldn't reproduce the pilot scenario. |

---

## 6. New repair-plan items surfaced by this run

### P5.5 — Validator's `must_reference_file_or_test` is too strict for command ACs

**What:** AC-2 of T-001 has `verification='command'`. The contract validator demands evidence reference a "file path or test name". Command outputs don't naturally include either. Result: Claude can't satisfy the check, retries until Max(3), task FAILED.

**Where:**
- `platform/app/api/pipeline.py` — the `contract_def` literal (~line 778) sets `must_reference_file_or_test: True` on `ac_evidence`.
- The validator implementation (probably in `app/services/delivery_validator.py` or similar — TBD).

**Why:** false negatives like this make Forge unusable for any AC where the verification mechanism is a CLI/script (alembic, terraform plan, k6 load test). It's the worst kind of failure: the validator does the wrong thing AND doesn't tell Claude how to fix it (the fix_hint is the same vague rule, not a path forward).

**How:**
1. Per-AC contract: read each AC's `verification` field. For `verification='command'`, replace the rule with `must_reference_command_or_output` — accept evidence that mentions the command stem (`alembic`, `pytest`, `npm`, `terraform`) OR a non-empty `stdout_excerpt` field.
2. Update fix_hint to be specific: when rejecting AC-N, include "AC-N is verification='command'; provide command output or migration file path."
3. Test: feed a delivery with command-style evidence, confirm validator accepts.

### P5.6 — Orchestrate run summary should explain partial-success path

**What:** `progress_message: "Completed 1 tasks (0 done)"` is misleading — "completed 1" sounds positive but it's a failed task. UI shows status=DONE but tasks_failed=1. Confusing.

**Where:** `pipeline.py` end-of-loop summary; `_orchestrate_panel.html` rendering.

**How:** when `tasks_failed > 0`, override status to `PARTIAL_FAIL` (new CHECK constraint value) or change the progress_message to "Stopped after T-001 FAILED (max retries reached)." Don't claim DONE when the only task failed.

---

## 7. What to do next

1. **Fix P5.5** — relax `must_reference_file_or_test` for command ACs. ~30 min. Worth it before the next live retry.
2. **Re-run validation with P5.5 in place.** Same scope (max_tasks=2). Expected: T-001 actually completes → triggers P1.2 hook + P1.3 challenger + Phase A test_runner → genuine end-to-end signal.
3. **If T-001 succeeds in run #2:** validates the full happy path. Estimated cost ~$2-3.

---

## TL;DR

Live run: spent $1.53, T-001 failed 3 attempts due to validator over-strictness on command-verification ACs. Plan-side fixes (P5.3) confirmed working. Orchestrate-side defenses (P1.2/P1.3/P5.2/P1.1) wired correctly but couldn't be live-exercised because no task reached DONE. **One new bug surfaced (P5.5)** — fixing it unblocks the next validation cycle.

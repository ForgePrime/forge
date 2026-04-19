# Autonomous session decisions log — 2026-04-19

User authorized autonomous work while driving. Each decision below is one I made
without confirmation; future me (or the user post-drive) should be able to read
this and either accept or reverse each call.

## Format

```
## D-N — short title
**Context:** what triggered the decision
**Options considered:** A / B / C
**Chosen:** X
**Why:** the reasoning
**Reversibility:** trivial | medium | high (cost to undo)
**Status:** decided | superseded | reversed
```

---

## D-1 — Sequencing P5.5 → P5.6 → live re-run

**Context:** User said "wykonuj jak najwięcej". Three workstreams ready: P5.5 fix, P5.6 status hygiene, P5.4 round-2 live validation.

**Options considered:**
- A: P5.5 → P5.6 → re-run (mechanical fix → polish → exercise)
- B: P5.6 → P5.5 → re-run (cosmetic first)
- C: skip P5.6 entirely, jump to live re-run after P5.5

**Chosen:** A.

**Why:**
- P5.5 unblocks the live test (T-001 was failing on this exact rule). High value per effort.
- P5.6 changes the OrchestrateRun CHECK constraint (PARTIAL_FAIL) — if I do it second, the round-2 live run will exhibit the new status, so I can validate both fixes in one shot.
- Skipping P5.6 means the round-2 report would still say "Completed N tasks (0 done)" which is wrong.

**Reversibility:** trivial — re-order is just shell command order.

**Status:** decided.

---

## D-2 — P5.5 scope: per-AC verification map vs. delivery self-report

**Context:** The validator needs to know each AC's `verification` mode to swap rules. Two ways to get it: (A) caller passes a map, (B) Claude's delivery self-reports per-AC verification.

**Options:**
- A: Add `ac_verifications` parameter to `validate_delivery`, caller (pipeline.py) builds it from `task.acceptance_criteria`.
- B: Require Claude to include `verification` on each `ac_evidence` item.

**Chosen:** A.

**Why:**
- The AC's verification mode is ground truth in the DB (set at plan time). Trusting Claude to re-declare it opens a trivial bypass: Claude claims `verification='manual'` for everything → no checks fire.
- Option A is also backwards-compat for legacy callers that don't provide the map — default `{}` → strict 'test' rule.

**Reversibility:** medium. If we later add B, we can merge both (DB wins over delivery claim).

**Status:** decided + shipped.

---

## D-4 — Restarting Forge server kills in-flight orchestrate runs (BUG / OPERATIONAL HAZARD)

**Context:** Mid-session I appended new lessons.py SELF_ANTI_PATTERN_SEED entries and restarted uvicorn to load them. Run #281 was in flight (T-001 attempt 1/3). The restart killed its `BackgroundTasks` worker. The run is stuck in `status=RUNNING` forever (no thread reads `cancel_requested`).

**Decision:** Manually mark run #281 as CANCELLED via DB UPDATE with note "killed by autonomous-session server restart 12:00; see D-4". Start fresh round-2.

**Why this is a real bug — needs P5.7 entry:** Forge orchestrate uses FastAPI BackgroundTasks (in-process). Any restart kills the worker. There's no resurrect-on-startup logic. For long runs (~15 min like T-001), this is fragile.

**P5.7 — Resurrect orphan RUNNING orchestrate runs on app startup:** add startup hook that scans `OrchestrateRun.status='RUNNING'` AND `started_at < (now - 30 min)` (heuristic for "no progress message change in last N min"); flip to `INTERRUPTED` (new status) so user can manually retry; OR: re-spawn the worker for any RUNNING row whose params are still resumable.

**Reversibility:** medium — needs schema migration + startup logic; low risk.

**Status:** decided to (a) mark run 281 cancelled now, (b) record P5.7 in repair plan for later, (c) NOT restart server again until live runs are terminal.

---

## D-5 — Pre-existing bug at pipeline.py:1026 (`val.model_used` — only reachable post-P5.5)

**Context:** Round-2b live run ended with `status=FAILED` / `error=AttributeError: 'ValidationResult' object has no attribute 'model_used'`. This line `model_used=val.model_used if val else ...` was dead code until today — round 1 never passed validation, so this branch was never executed. P5.5 made validation pass → we reached the git-commit trailer builder → hit the typo.

**Decision:** Fix `val.model_used` → `cli.model_used` (CLIResult). Documented inline with a bugfix comment crediting the autonomous session.

**Why this matters (P5.8 worth noting):** a whole post-validation branch (~80 lines: git commit, test_runner invocation, Phase B extraction, Phase C challenger) has never been exercised under real conditions because round-1-style validator over-rejection blocked access to it. There may be MORE latent bugs in that branch. Need extensive live validation to flush them out.

**Reversibility:** trivial.

**Status:** patched. Waiting for round-2c live run to confirm no further bugs in the post-accept branch.

---

## D-6 — Tests using global-scope mutators are dangerous (incident with run 390)

**Context:** Round 2c run #390 advanced through Phase A (validator → git commit → tests → KR) and Phase B (extract) and was mid-Phase-C (challenger) when my freshly-added `test_shutdown_flips_running_to_interrupted` test fired `mark_running_runs_interrupted_on_shutdown(db)` *unscoped*. That global flip stomped every RUNNING row in the DB — including run #390. The worker kept executing in-memory and finished T-001 successfully (status DONE in the task table, mode=direct on Execution #390 = ACCEPTED), but the OrchestrateRun row stayed at status=INTERRUPTED. Monitor saw INTERRUPTED → terminated → I lost the auto-pause/resume + T-002 demo.

**Decision:**
1. Add `project_id: int | None = None` parameter to BOTH `release_in_progress_tasks` and `mark_running_runs_interrupted_on_shutdown`. Production shutdown calls without it (everything dies). Tests MUST pass it.
2. Add explicit "scope-leak" tests for each helper that seed a second project + verify it's untouched.
3. Hidden silver lining: T-001 actually completed — first end-to-end success in this validation session. P5.5 fix confirmed working live.

**Why this is also a real lesson:** Any global mutation helper called from tests is a hidden weapon. The shutdown path is correct in production (all data is sliced together), but a test treating the live DB as scratch space corrupts ANY in-flight session.

**Reversibility:** trivial (add an optional param + scoping clause). Done.

**Status:** patched + 10 tests including 2 scope-leak guards.

---

## D-7 — STOP point: SA 2.0.30 + Python 3.13 environmental issue (not my code)

**Context:** Near the end of the session, `import sqlalchemy` started failing even in a fresh subprocess with `TypeError: Can't replace canonical symbol for '__firstlineno__'` at SA's `compiler.py:615`. This is a well-known SA 2.0.30 bug with Python 3.13's new dunder enforcement ([SA#11774](https://github.com/sqlalchemy/sqlalchemy/issues/11774)), fixed in SA 2.0.35+.

**Decision:** STOP committing more code. I could `pip install --upgrade "sqlalchemy>=2.0.41"` to fix it, but:
1. Upgrading a dep is a change worth your approval (even though patch-version bump is low-risk, the user's explicit drive-mode scope didn't cover env changes).
2. The bug is NOT caused by my code. Last captured test suite run was 507/507 passing. Every P5.x edit has test coverage that passed in sequence.

**Why 507 is probably still valid:** I made no model/enum changes after the 507 test count except adding two regression test files (test_p5_hook_timeout.py, test_post_accept_branch.py) which themselves passed standalone. The SA issue is import-time and would affect all tests equally — so either the suite is green or it won't even collect. It was green twice in a row.

**Status:** stopped. The user can:
1. Run `pip install --upgrade "sqlalchemy>=2.0.41"` in the venv.
2. Restart the uvicorn server.
3. Run the suite to confirm the 507 count still holds.

**Server state:** killed at 13:57 by my last test attempt. To restart: `cd platform && python -m uvicorn app.main:app --host 127.0.0.1 --port 8063 &`.

---

## D-3 — COMMAND_PATTERN scope: which CLI tools to allow

**Context:** Need a regex that recognizes "command evidence" without being so lax that "verified" passes.

**Options:**
- A: Enumerate common tools (alembic, pytest, npm, docker, kubectl, terraform, curl, ab, wrk, locust, k6, psql, etc.) — ~35 tools
- B: Match *any* lowercase word of 3+ chars followed by `-` flag — too permissive
- C: Require shell prompt markers only (`$`, `>>>`) — too strict for multi-line evidence

**Chosen:** A plus output markers (`exit code`, `stdout`, `stderr`, `rc=`).

**Why:** matches real-world evidence shapes I've seen in Claude's outputs while still rejecting pure "verified" self-reports. Tradeoff: a new tool (e.g. `rustfmt`) might be rejected unfairly; easy to add to the list.

**Reversibility:** trivial — regex edit.

**Status:** decided + shipped.

---

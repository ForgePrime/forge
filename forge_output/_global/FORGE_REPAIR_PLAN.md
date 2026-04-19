# Forge Platform — Repair Plan

**Source:** mockup ↔ code element-by-element audit (01, 02v2, 03v2, 04, 05v2, 07, 09, 10, 11, 12, 16).
**Baseline:** 148/148 tests green · ~65% functional coverage of mockup spec.
**Scope:** close gaps where mockup promises behaviour that code does not deliver. Each item: **What · Where · Why · How**.

Priority legend:
- **P1** — UI shows control, backend stores state, but pipeline never honours it. User thinks it works, it silently doesn't.
- **P2** — mockup promises a view/widget that does not exist in code yet; spec is clear enough to build now.
- **P3** — enhancement that sharpens trust signal; nice-to-have, not blocking.
- **P4** — requires design decisions (streaming, async refactor); scope TBD with user first.

---

## P1 — Broken features (silent no-ops)

These are the most trust-damaging: the UI and DB columns suggest the feature works, but the execution path ignores them. Fix first.

### P1.1 Pause button does nothing inside orchestrate loop

**What:** mockup 10 (orchestrate run) has a `⏸ Pause` button. We wrote `OrchestrateRun.pause_requested` bool and an endpoint `POST /runs/{id}/pause` that flips it, but the actual execution loop never checks it. A paused run keeps consuming tasks + budget until it finishes.

**Where:**
- `platform/app/api/pipeline.py` — the `run_orchestrate()` function (approx. the long `while` loop over queued tasks).
- `platform/app/models/orchestrate_run.py` — `pause_requested`, `paused_at`, `resumed_at` columns already exist.
- UI: `platform/app/templates/orchestrate_run.html` — button + `POST` wired.

**Why:** our skeptical contract promises the user "you are in control". A pause control that silently fails is worse than no control — it builds false confidence.

**How:**
1. At the top of each loop iteration in `run_orchestrate()`, `SELECT pause_requested FROM orchestrate_runs WHERE id = :id` (fresh read; not the cached ORM obj).
2. If true: set `status='paused'`, set `paused_at=now()`, emit SSE event `{type:'paused'}`, `break` out of the loop. Do **not** start the next task.
3. Add a resume endpoint `POST /runs/{id}/resume` that clears `pause_requested`, sets `resumed_at`, re-queues the run by spawning a new executor picking up at the next queued task (status-driven, not index).
4. Test: `test_pause_stops_before_next_task` — start a 3-task run, pause after task 1 completes, assert `status='paused'` and task 2 stayed `queued` (not `started`).

---

### P1.2 Hooks never fire on task complete / run complete

**What:** mockup 09 (hooks tab) lets users declare hooks: `on_task_complete`, `on_run_complete`, `on_finding_created`, etc. Model `ProjectHook` + CRUD API exist; executor never fires them.

**Where:**
- `platform/app/models/project_hook.py` — model with `stage`, `command`, `enabled`, `timeout_sec`.
- `platform/app/api/hooks.py` — CRUD endpoints.
- Executor: `platform/app/api/pipeline.py` (task transition to DONE) and `run_orchestrate()` terminal branch.

**Why:** hooks are the user's escape hatch for custom validation (e.g. "curl my CI after every run"). Silent no-op means their validation never runs and they discover it only after shipping bad code.

**How:**
1. New service `platform/app/services/hooks_runner.py` with `fire_hooks(db, project_id, stage, context: dict)`:
   - Query `ProjectHook` rows for that project + stage + enabled=True.
   - For each: `subprocess.run(shlex.split(hook.command), timeout=hook.timeout_sec, env={'FORGE_CONTEXT': json.dumps(context)})`.
   - Capture exit_code, stdout, stderr. Persist to a new `HookRun` table (project_id, hook_id, stage, exit_code, stdout_tail, stderr_tail, duration_ms, at).
2. Call sites:
   - Task DONE transition → `fire_hooks(db, proj_id, 'on_task_complete', {task_id, status, diff_stats})`.
   - `run_orchestrate()` end → `fire_hooks(..., 'on_run_complete', {run_id, tasks_done, tasks_failed})`.
   - Finding creation → `fire_hooks(..., 'on_finding_created', {finding_id, severity})`.
3. UI: hooks tab adds a "Last fired" column pulling latest `HookRun.at` per hook + a failing-hooks pill count.
4. Test: seed a hook `echo "{\"task\":\"$FORGE_CONTEXT\"}" > /tmp/forge-hook-test`, run a task to DONE, assert file exists and HookRun row inserted with exit_code=0.

---

### P1.3 `Objective.challenger_checks` stored but never injected

**What:** objective editor (mockup 03v2) lets the user write extra challenger checks per objective (e.g. "verify the user flow works end-to-end, not just unit pass"). Stored as `Objective.challenger_checks` JSONB. Phase C challenger prompt never reads them.

**Where:**
- `platform/app/models/objective.py` — `challenger_checks` column.
- `platform/app/services/challenger.py` — the prompt builder used in Phase C.

**Why:** challenger checks are how the user encodes domain-specific suspicion ("I've been burned by X before"). Without injection, the stored checks are inert — the opposite of what "skeptical platform" means.

**How:**
1. In `challenger.py`, resolve objective chain for the task (task.origin → Objective → dependency ancestors).
2. Collect `challenger_checks` from every objective in the chain (dedupe by text).
3. Append to the system prompt section `## Extra challenger rules from objectives:` as a bulleted list.
4. Persist the injected rules in the `LLMCall.full_prompt` (already does, automatic) + add a structured `LLMCall.injected_checks` JSON field for audit.
5. Test: create objective with `challenger_checks=["must return 403 on expired token"]`, run Phase C on a task linked to it, assert LLMCall.full_prompt contains that string.

---

### P1.4 Execution mode badge not rendered in task report

**What:** `Execution.mode` column ('plan' | 'execute' | 'shadow') exists and is set by executor. Task report template does not read it. User cannot distinguish a real execution from a dry plan.

**Where:**
- `platform/app/templates/task_report.html` — header badges block.
- `platform/app/api/pipeline.py` — `task_report()` returns `latest_exec` dict but doesn't expose `mode`.

**Why:** shadow/plan mode is core to autonomy L1-L2 (execute without touching). If the user can't see the mode, they can't trust the badge "this was a shadow run" vs "this actually wrote files".

**How:**
1. In `task_report()`: extend `latest_exec` dict with `mode=exec.mode`, `started_at=exec.started_at`, `ended_at=exec.ended_at`.
2. In `task_report.html`: next to the status pill, render `<span class="pill bg-{{ mode_color }}">{{ mode }}</span>` where mode_color = `indigo` (execute), `sky` (plan), `slate` (shadow).
3. Add to run-list rows on project page as well (currently shows status only).
4. Test: seed Execution with mode='shadow', GET /ui/tasks/{ext}/report, assert 'shadow' text + `bg-slate-100` class in response.

---

## P2 — Missing but clearly specified

Mockup promises a view or action that does not exist in code yet. Spec is concrete enough to build without new decisions.

### P2.1 Finding → Task one-click conversion

**What:** mockup 05v2 findings table has a `→ Task` button that creates a `chore` task to fix the finding. Button is not wired.

**Where:**
- `platform/app/api/tier1.py` — no create-task-from-finding endpoint.
- `platform/app/templates/task_report.html` — findings section has link but no POST.

**How:**
1. New endpoint `POST /api/v1/tier1/findings/{external_id}/create-task`:
   ```python
   def create_task_from_finding(ext, db, user):
       f = db.query(Finding).filter_by(external_id=ext).first_or_404()
       t = Task(project_id=f.project_id, type='chore',
                title=f"Fix: {f.title}",
                description=f.description,
                origin_finding_id=f.id,
                status='queued')
       db.add(t); db.commit()
       return {'task_external_id': t.external_id}
   ```
2. Add `Task.origin_finding_id` column (nullable FK → findings.id) via schema_migrations `ADD COLUMN IF NOT EXISTS`.
3. Button in findings section: `<button hx-post=".../create-task" hx-target="#findings-toast">→ Task</button>`.
4. Task detail page: if `origin_finding_id` set, show "Created from F-NNN" link chip.
5. Test: POST on a finding, assert new Task row with origin_finding_id set and status=queued.

---

### P2.2 Test code inline-expand in AC rows

**What:** mockup 07 shows AC row with `▸` caret to reveal test source code next to the ✓/✗ status. We show pass/fail only.

**Where:**
- `platform/app/templates/task_report.html` — AC table.
- `platform/app/services/workspace_browser.py` — already can read workspace files.

**How:**
1. For each AC with `verification='test'` + `test_path`: add a disclosure `<details>` containing `<pre>{{ code }}</pre>` where code is fetched from workspace file at test_path.
2. Read happens server-side in `task_report()` view — cache in template context as `ac.test_code` (first 200 lines, enough for a pytest function).
3. If `test_path` points to a symbol (`tests/test_x.py::test_y`), slice the function body via `ast.parse` + walk.
4. Test: AC with test_path, GET report, assert `<details>` wrapping test source present.

---

### P2.3 Side-by-side diff toggle

**What:** mockup 12 (files tab) promises unified ↔ split diff toggle. We render unified only.

**Where:**
- `platform/app/templates/_diff_viewer.html` — unified HTML block.
- `platform/app/services/diff_renderer.py` — builds the unified diff.

**How:**
1. Extend `diff_renderer.render(path, mode='unified'|'split')` to emit a 2-column table for split.
2. Use existing `difflib.ndiff` → group into pairs of (left, right) per hunk.
3. UI: toggle button above diff updates a query param `?view=split`, server re-renders the fragment.
4. Test: GET diff with view=split, assert `<table class="split-diff">` with both `td.old` and `td.new` present.

---

### P2.4 Budget configuration UI

**What:** mockup 11 (contract/config) surfaces per-task + per-run USD budgets. Currently stored in `project.config` dict, no form to set them.

**Where:**
- `platform/app/templates/project.html` — contract/config tab.
- `platform/app/api/projects.py` — config patch endpoint exists.

**How:**
1. Add form block in contract tab:
   - `budget_task_usd` (default 1.00)
   - `budget_run_usd` (default 5.00)
   - `budget_hard_cap_pct` (150 = warn at 150% of run budget)
2. Form `POST /api/v1/projects/{slug}/config` with CSRF.
3. Enforcement: in `invoke_claude` wrapper inside executor, pass `max_budget_usd = min(task_budget, remaining_run_budget)`; if remaining < 0 → block task with status='blocked_budget' + finding.
4. Show current spend meter "$1.23 / $5.00 this run — 24.6%".
5. Test: set budget=0.10, run an expensive task, assert it blocks before 2nd LLM call.

---

### P2.5 Veto configuration UI

**What:** mockup 09 shows Veto panel (paths that must never be touched, hard budget cap). Stored in project.config, no UI.

**Where:** same config form (P2.4). Add:
- `veto_paths` (textarea, one glob per line, e.g. `migrations/**`, `.env*`, `infra/prod/**`).
- `veto_budget_hard_cap_pct` (150).

**How:**
1. On every executor file-write or git-diff, `fnmatch.fnmatch(path, veto_pattern)` → if match, abort with finding kind='veto_violation'.
2. Render current veto rules with a small "X" to delete.
3. Test: seed veto `app/secrets/**`, run a task that writes `app/secrets/foo.py`, assert finding created + task failed.

---

### P2.6 TOC sidebar for Documentation tab

**What:** mockup 16 docs page has sticky left TOC generated from H1/H2 headers. We render flat list of docs only.

**Where:** `platform/app/templates/_docs_tab.html`.

**How:**
1. In `docs_tab_view()`: for each polished doc, `markdown.markdown(text, extensions=['toc'])` with `TocExtension(toc_depth='1-2')`.
2. Emit `<aside class="toc sticky top-4">{{ toc_html }}</aside>` next to the doc body.
3. For the aggregate "All docs" view: concat all TOCs grouped by doc title.
4. Test: doc with `# Intro` + `## Step 1`, assert `<a href="#intro">` + `<a href="#step-1">` present.

---

## P3 — Enhancements (trust-sharpening polish)

### P3.1 Relative timestamps helper

Every page shows absolute ISO timestamps. Humans need "3m ago". Add a Jinja filter `|reltime` using `humanize.naturaltime()`. Apply across templates (project list, runs, LLM calls, findings).

### P3.2 Skill success-lift stats

Mockup 02v2 skills tab promises "+12% pass rate when attached" column. Compute: for each skill, compare avg task-pass rate when skill attached vs not attached on same project, rolling 30 days. Add column + sort.

### P3.3 Kanban + Timeline view toggles

Tasks tab currently table-only. Mockup 01 shows Kanban columns (Queued / In progress / Blocked / Done) + Timeline (Gantt-like). Add view=kanban and view=timeline query params with new partial templates.

### P3.4 Per-objective KB scoping

New column `Objective.kb_focus_ids ARRAY(Integer)`. Objective editor gets multi-select of KB sources. When resolving context for a task linked to an objective with kb_focus_ids, restrict KB queries to those sources only. Prevents noise from unrelated docs.

### P3.5 Per-source "last read by Claude" timestamp

`Knowledge.last_read_at` column, updated when KB source is injected into a prompt. Source list shows "Last used 2h ago" to help user prune stale entries.

---

## P4 — Design decisions required (do not start without user sign-off)

### P4.1 Real-time tool-call stream during execution

Currently we parse the final transcript. Mockup 10 shows tool calls appearing live. Requires: asyncio subprocess + line-buffered Claude CLI output + SSE pushing each tool_use block as parsed. **Question for user:** is the extra complexity worth it, or is "refresh every 2s" acceptable?

### P4.2 Live stdout tail during orchestrate

Related to P4.1. Broader refactor: the executor needs to be async (or threaded + queue) so the request handler can stream while execution runs. **Question for user:** do we rewrite the executor now, or defer until post-pilot?

---

## Suggested sequencing

1. **Week 1 (P1):** pause, hooks, challenger checks, mode badge. Each independently testable. Unblocks trust.
2. **Week 2 (P2.1 – P2.3):** finding→task, test-code expand, split diff. Same code area (task report + diff).
3. **Week 3 (P2.4 – P2.6):** budget, veto, docs TOC. Contract/config tab consolidation.
4. **Week 4 (P3):** polish pass — timestamps, skill stats, views. Ship behind feature flags if needed.
5. **Post-pilot:** P4 design spike. Write an ADR, then implement.

## Test-first discipline (non-negotiable)

For each item:
- Add the failing test **before** the implementation.
- Use `conftest_populated.py` (populated project) — never trust fresh-fixture only.
- Register the bug pattern as an AntiPattern via `/anti-patterns` if the fix reveals a systemic issue.

## Tracking

Each item becomes one Forge task with `type=bug` (P1) or `type=feature` (P2/P3). Origin = new objective `O-REPAIR-MOCKUP-PARITY` with KRs:
- `KR1: P1 items DONE = 4/4` — ✅ **ACHIEVED** (2026-04-19)
- `KR2: P2 items DONE = 6/6` — ✅ **ACHIEVED** (2026-04-19)
- `KR3: mockup functional coverage ≥ 85%` — ~**90%** (P4 items remaining)

---

## Pilot-validation addendum (2026-04-19)

After shipping P1-P3, we checked whether the fixes actually prevent the 3 fail-throughs from the **WarehouseFlow pilot (2026-04-17)**:

| Pilot fail-through | Who catches it now |
|---|---|
| `test_available_qty_equals_physical_minus_reserved` declared PASSED, actually FAIL | **Phase A `test_runner`** — already in `pipeline.py:1027`; rejects delivery when `test_verify.all_pass=False`. Pre-existed P1-P3. |
| `test_alarm_flag_at_exact_boundary_values` same pattern | same |
| `test_missing_stock_level_returns_zeros_not_null` same pattern | same |

**Forge's mechanical test gate already defended against these.** Our P1-P3 work stacks *additional* defenses on top — none of them replace the mechanical gate, they tighten it at different layers:

- **P1.3 challenger_checks** — user can encode `"verify the formula is actually in the code, not just declared"` on the objective; Opus reads the diff + checks. Probabilistic, but catches cases where tests don't exist for a requirement.
- **P1.2 hooks** — user can wire `after_develop → SK-security-owasp` (or any skill) to run a secondary LLM review on every develop task. HookRun audit trail proves it fired.
- **P1.1 pause** — budget bleed control. If user sees orchestrate going off-rails, Pause actually stops the loop (previously: flag flipped, loop ignored it).
- **P1.4 mode badge** — distinguishes shadow/plan (no code written) from direct/crafted (code written + committed). Previously invisible.
- **P2.1 finding → task** — if challenger surfaces a finding, one-click creates a chore task to fix it.
- **P2.2 test-code expand** — post-mortem aid: user opens the report, expands inline, sees the failing assertion next to the AC text.

### Mechanical re-check on current workspace state

Ran Forge's own `app.services.test_runner.run_pytest` against `forge_output/warehouseflow/workspace` for the 3 previously-failing tests:

```
rc=0  coll=3  pass=3  fail=0  err=0  all_passed=True
  PASSED   tests/stock/test_service.py::test_available_qty_equals_physical_minus_reserved
  PASSED   tests/stock/test_service.py::test_alarm_flag_at_exact_boundary_values
  PASSED   tests/stock/test_service.py::test_missing_stock_level_returns_zeros_not_null
```

The service was fixed between 2026-04-17 and now. What we validated mechanically today:
1. `run_pytest` correctly parses per-test outcomes (would have `tests_failed>0` and `all_passed=False` if they failed today).
2. The orchestrate loop's gate at `pipeline.py:1027` sets `verification_issue=tests_failed: ...` on any fail → task flips to `REJECTED` → retry or `FAILED`.

### Verdict — did P1-P3 change the answer to the pilot?

Partially. The deterministic block was already in Phase A. Our work:
- ✅ Fixed the UX claim — "control in the loop" (pause) actually works now.
- ✅ Added user-driven extra verification (challenger_checks + hooks + kb_focus).
- ✅ Closed audit loops (HookRun, mode badge, origin_finding_id chips).
- ❌ Did **not** address the two infra fails from the pilot (`locust` missing) — those stay in the gap list below.

---

## P5 — newly-surfaced gaps from pilot re-check (not in original plan)

**Status (2026-04-19 autonomous session end):**
- P5.1 ✅ shipped  (9 tests)
- P5.2 ✅ shipped  (11 tests)
- P5.3 ✅ shipped  (26 tests)
- P5.4 ✅ **4 live rounds executed** — see `FORGE_E2E_VALIDATION_REPORT_R2C.md`. Round 2d reached DONE terminal cleanly.
- P5.5 ✅ shipped  (24 tests)  — validator per-AC verification, proven live round-2c
- P5.6 ✅ shipped  (9 tests)   — PARTIAL_FAIL status + accurate msg, proven live round-2d
- P5.7 ✅ shipped  (18 tests)  — orphan recovery + graceful shutdown
- P5.8 ✅ shipped  (3 tests)   — hook timeout 90→180s, per-skill override, proven live round-2d
- P5.9 ✅ shipped  (2 tests)   — removed over-broad "done" reject-pattern
- P5.10 🟡 partially fixed — hooks_runner LLMCall persistence wrapped in its own try/commit with visible failure surface; root cause (why was INSERT silently failing) not yet diagnosed.

**Last known-good test count:** 507/507. End-of-session SA 2.0.30 + Py 3.13 import issue blocks further test execution — user should `pip install --upgrade "sqlalchemy>=2.0.41"` before next suite run. See `AUTONOMOUS_SESSION_DECISIONS.md` D-7.

### P5.1 Workspace dependency bootstrap

**What:** pilot's load-tests failed with `No module named locust` — Claude generated a `locustfile.py` but never installed the tool. Forge's workspace infra sets up Postgres/Redis but doesn't `pip install -r requirements.txt` in the workspace venv.

**Where:**
- `platform/app/services/workspace_infra.py`
- Add a step after container-start: `subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"])` if `requirements.txt` exists.

**Why:** delivery claims `test_product_list_p95_under_3000ms PASSED` got accepted because the test errored (not failed), and ERROR != FAIL in pytest's --json-report. Phase A doesn't treat ERROR the same as FAIL.

**How:** add `tests_error` to the gate — `not all_pass = tests_failed > 0 OR tests_error > 0`. Already modelled (`TestRunResult.tests_error`); just wire into the gate.

**Test:** seed a workspace with a test that imports a missing module, confirm `test_verify.all_pass=False` and task status = FAILED.

### P5.2 KR measurement actually runs

**What:** 4/4 numeric KRs in the pilot stayed `NOT_STARTED` with `current_value=null`. The `measurement_command` for KR0 (`ab -n 100 -c 30`) was defined and never executed.

**Where:** `platform/app/services/kr_measurer.py` + call site in `pipeline.py` (looks like it's already called on lines 1038-1050 but maybe short-circuits when commands fail silently).

**How:** audit `kr_measurer` for silent-fail paths (missing `ab`, missing `locust`, exit code ≠ 0). Convert to `WARNING` findings when measurement fails — don't silently leave `current_value=null`.

**Test:** seed a KR with `measurement_command="exit 1"`, run a task linked to the objective, confirm a Finding is created with `kind='kr_measurement_failed'`.

### P5.3 Requirement → Task linking in plan prompt

**What:** pilot plan produced 10 tasks, 0 of them declaring "this task implements SRC-001 §2.4". Task has `origin` to Objective, but requirement drill-down is missing. Phase B was supposed to add it but isn't in scope of this repair.

**Where:** `platform/app/services/prompt_assembler.py` (plan prompt) + plan output schema.

**How:** add `requirement_refs: list[str]` to plan output schema, prompt Claude to fill each task's refs to `SRC-XXX §Y.Z` tokens from the ingested knowledge. `draft-plan` gate rejects plans where any task has empty `requirement_refs` when the objective was built from source documents.

**Test:** given objective built from SRC-001, plan with 3 tasks, assert each has non-empty `requirement_refs`. Plan gate rejects when empty.

### P5.10 hooks_runner persists HookRun but silently drops the LLMCall row (PARTIALLY FIXED 2026-04-19)

**Partial fix shipped same-day autonomous session:**
- Wrapped `LLMCall` save in its OWN try/commit. Rolls back on failure so the hook can still persist its HookRun audit row.
- On persist failure, `HookRun.summary` gets a `[LLMCall persist failed: TypeName: msg]` prefix so the bug is visible in the UI, not silent.
- This does NOT fix the ROOT cause (why was the LLMCall disappearing?), but it makes the failure loud instead of silent.

**Still needs investigation on next session (SA 2.0 environment permitting):**


**What:** When a hook fires successfully (e.g. T-003 in 2026-04-19 round 2d: status=fired, summary contains the actual LLM response "Done. Here's what changed..."), the corresponding `LLMCall` row is never persisted. Global query `LLMCall.purpose LIKE 'hook%'` returns 0 rows across the entire DB. `HookRun.llm_call_id` stays NULL even when status=fired. This means: cost is invisible (no contribution to per-project ledger), the user can't open the prompt+response from the audit page, the replay endpoint can't re-run hook calls.

**Where:** `platform/app/services/hooks_runner.py` line 138-156 (the LLMCall constructor + db.add + db.flush). Both the timeout/error path AND the happy path are affected.

**Why:** Three hypotheses to explore:
1. SQLAlchemy session is being externally rolled back between `db.flush()` and `db.commit()` — possibly by a parallel _update_run from the orchestrate loop sharing the same Session.
2. The LLMCall constructor silently fails on some required attribute we missed — but P1.2 unit tests pass with the same code paths, so this is unlikely.
3. The `db.add(llm)` adds to identity map but flush succeeds without INSERT (e.g. `cascade='none'` weirdness, or `expire_on_commit` interaction).

**How:**
1. Wrap LLMCall construction + flush in its OWN try/except, logging the exception. If it fails, continue creating the HookRun with llm_call_id=None — but at least we'll know.
2. Add a focused live test: mock invoke_claude, fire a hook, assert BOTH HookRun AND LLMCall rows are created.
3. Investigate hypothesis 1 by passing a fresh `db = SessionLocal()` into hooks_runner instead of sharing the orchestrate loop's session.

**Test:** see #2 above. Should be a unit test using the existing `MagicMock(invoke_claude)` pattern from P1.2 tests, but with an assertion that `db.query(LLMCall).filter(purpose=='hook:after_develop').count() == 1` after fire_hooks_for_task returns.

---

### P5.9 REJECT_PATTERNS_REASONING substring-matched "done" everywhere

**What:** `contract_validator.REJECT_PATTERNS_REASONING` listed `"done"` as a rejected phrase. The match logic is `pattern.lower() in reasoning.lower()` — substring. Any reasoning containing the word "done" in ANY context ("the migration is done because...", "task is now done", "well-done refactor of X") triggered FAIL, then 3-attempt retry, then task FAILED.

**Where:** `platform/app/services/contract_validator.py` line 16-19.

**Why:** the other phrases are clear self-report shortcuts ("verified manually", "looks good", "everything works"). "done" is just a normal English past participle. Same false-positive class as P5.5: rule too broad for the intent.

**Status:** ✅ Removed during 2026-04-19 autonomous session. Documented here for traceability.

**Test added (recommended):** `test_validator_accepts_reasoning_with_word_done` in test_p5_validator_per_ac.py — feed reasoning "The migration is done because we tested..." and assert no reject_pattern fail.

---

### P5.8 Hook LLM-call timeout is hard-coded at 90s (too short for SKILL invocations)

**What:** `hooks_runner.py` calls `invoke_claude(..., timeout_sec=90)`. Round 2c live run: HookRun #1 fired correctly for `after_develop` on T-001, picked SK-pytest-parametrize, attempted the LLM call — **timed out at 90s.** Status flipped to `error`. The wiring works; the budget doesn't.

**Where:** `platform/app/services/hooks_runner.py` line ~110.

**Why:** SKILL/OPINION skills wrap full delivery review (~7 KB prompt; Sonnet typically 60-120s). 90s is below the median. MICRO skills are faster but inherit the same timeout.

**How:**
1. Bump default to 180s.
2. Even better: read per-skill from `Skill.cost_impact_usd` proxy or add `Skill.recommended_timeout_sec` column. Skills with cost_impact_usd >= 0.10 get 240s; smaller ones keep 90s.
3. Surface the timeout error more loudly: `HookRun.status='error'` with summary='timeout' should bubble up to the project hooks tab as an amber pill, not just the audit row.

**Test:** mock `invoke_claude` to raise `TimeoutExpired`, confirm `HookRun.status='error'` and `summary` contains 'timeout'. With the new column, set Skill.recommended_timeout_sec=240, confirm invoke_claude is called with timeout_sec=240.

### P5.7 Resurrect orphan RUNNING orchestrate runs after server restart

**What:** FastAPI's `BackgroundTasks` runs the orchestrate worker in-process. Any uvicorn restart (deploy, crash, dev reload) kills the worker mid-task. The `OrchestrateRun` row stays `status='RUNNING'` forever — `cancel_requested` is unread, `current_task` stays as the dying task. Discovered live in 2026-04-19 autonomous session (D-4 in `AUTONOMOUS_SESSION_DECISIONS.md`).

**Where:**
- `platform/app/main.py` — needs a startup hook.
- `platform/app/api/pipeline.py` `_run_orchestrate_background` — the worker entrypoint.
- `platform/app/models/orchestrate_run.py` — likely needs new `INTERRUPTED` status (or reuse PARTIAL_FAIL).

**Why:** every server restart silently corrupts the run state. User has no way to recover except manually editing the DB. For real production with deploys, this is a daily occurrence.

**How (two-tier):**
1. **Cheap (this PR):** startup hook scans for `status='RUNNING'` rows older than 30 minutes (heuristic: `updated_at < now - 30min`). Marks them `INTERRUPTED` with error="server restarted; orphaned worker". User retries the task manually.
2. **Better (later):** persist enough state to **resume**. The orchestrate loop's params + last-known-task already gives enough — just re-spawn `_run_orchestrate_background` for any RUNNING row whose project still exists. The DAG-aware candidate finder (`Task.status='TODO' + deps DONE`) naturally picks up where the worker died.

**Test:**
1. Seed an OrchestrateRun row with status='RUNNING' + updated_at = 2 hours ago. Call `mark_orphans_interrupted()`. Assert status flipped to INTERRUPTED + error message set.
2. Boundary: row updated 5 min ago → still RUNNING (within heuristic window).

### P5.4 Live E2E re-validation — separate exercise

**Not a code fix.** To prove end-to-end that the post-P1-P3 Forge handles WarehouseFlow better than the Apr 17 pilot did, we need to:
1. Reset the workspace (git clean, drop DB).
2. Re-run `/ingest → /analyze → /plan → /orchestrate-async`.
3. Observe: pause actually pauses, hooks fire, challenger_checks get injected, mode badge shows per task.
4. Compare cost + time + test pass rate against the pilot numbers.

**Estimated cost:** ~$10 (was $10.52 for the same scope). **Time:** ~90 min wall clock. **Not started** — pending user sign-off on spending the API credits. Would validate the narrative claim of "65% → 90% mockup coverage" empirically, not just by unit test.

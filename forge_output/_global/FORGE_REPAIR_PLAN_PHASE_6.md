# Forge Repair Plan — Phase 6 (Mockup-vs-Code audit, 2026-04-19)

**Source:** four parallel agent audits of all 15 mockups + walkthrough.md + flow.html against the running platform (post P1-P5 + P5.x ship).

**Scope of this plan:** the gaps the agents surfaced AND the process holes (states the walkthrough describes but no UI exists for). Items I personally verified against the code are marked `(VERIFIED)`. Items based purely on agent reports are marked `(AGENT)` — some agents got facts wrong (e.g. claimed objective reopen endpoint missing when it exists at `tier1.py:488`); I corrected those before listing.

**Current platform state:** ~70% mockup parity (per agent B), gaps cluster around: (a) progress-tracking visuals, (b) per-task mode/skill scoping, (c) data-model-exists-but-no-UI features (skill ROI, veto enforcement, etc.), (d) process holes that strand the user.

Priority legend:
- **P6.1-P6.3 BLOCKING** — user gets stuck and can't continue
- **P6.4-P6.10 USABILITY** — user completes flow but with friction
- **P6.11-P6.17 POLISH** — visual fidelity to mockup
- **P6.18-P6.25 LARGER** — design/engineering investment, separate sign-off

---

## P6.1 — BLOCKING — re-analyze trigger after answering ambiguities (VERIFIED)

**What:** Walkthrough Scenario 1 §19: "Clicks 'Continue with my answers'. Re-analysis fires." Today: user resolves a Decision (via `tier1.py:1090 finding_dismiss` and decision-resolve endpoints), but **no button anywhere** triggers Forge to re-run /analyze with the user's answers folded in.

**Where:**
- `app/api/pipeline.py` — `analyze_documents()` exists; needs an idempotent re-analyze path that includes resolved decisions in the prompt.
- `app/templates/objective_detail.html` — needs a "▶ Re-analyze with my answers" button that POSTs to a new endpoint.

**How:**
1. Add `POST /api/v1/projects/{slug}/objectives/{ext}/re-analyze` — gathers all CLOSED decisions for this objective + the original source-doc context, re-invokes the analyze prompt with the resolved decisions appended.
2. Button in objective_detail.html (visible only when there are CLOSED decisions linked to this objective and the objective hasn't been reanalyzed since).
3. Tests: seed an objective with 2 OPEN decisions, resolve them, POST re-analyze, assert objective fields updated + AI Interaction row recorded.

---

## P6.2 — BLOCKING — cross-objective conflict detection + dashboard alert (VERIFIED MISSING)

**What:** Walkthrough Scenario 2 §4-5: "Cross-objective conflict alert pops on dashboard" when O-002 and O-004 hold contradictory assumptions. No code today scans for this; the existing `/kb/conflicts` endpoint detects only KB-source conflicts, not objective-assumption conflicts.

**Where:**
- New `app/services/objective_conflicts.py` with `scan_assumption_conflicts(db, project_id) -> list[ConflictPair]`.
- `app/templates/index.html` — top-of-dashboard banner when conflicts found.
- `app/api/tier1.py` — new `GET /projects/{slug}/objective-conflicts`.

**How:** heuristic v0 — for each pair of ACTIVE objectives, extract decision recommendations + business_context keywords, flag pairs where a `must_X` from one matches `must_not_X` from the other. Trigger via post-analyze hook (after both objectives have decisions resolved). Findings shown as a dashboard banner + on each conflicting objective's detail page.

---

## P6.3 — BLOCKING — decisions block planning as modal, not soft tab (VERIFIED MISSING)

**What:** Mockup `03-project-post-analyze.html` shows a **forced overlay modal**: "2 decisions need your input" — user can't click `/plan` until resolved. Code has decisions in a tab (`project.html` decisions tab); user can ignore them and call `/plan` anyway, undermining the whole skeptical-UX contract.

**Where:**
- `app/templates/project.html` — add modal that fires on tab=objectives load when `open_decisions > 0`.
- `app/api/pipeline.py plan_from_objective` — add gate: HTTP 412 if any OPEN decisions reference the objective.

**How:**
1. Add `GET /projects/{slug}/blocking-decisions?objective={ext}` returning OPEN decisions with `recommendation_provided` (Claude's pick).
2. JS modal opens automatically when objective tab/page loads + open decisions exist.
3. plan endpoint pre-flight check rejects with 412 + the list of unresolved decisions.

---

## P6.4 — USABILITY — per-task mode selector modal (mockup 07) (VERIFIED PARTIAL)

**What:** Mockup 07 shows a modal opening when user clicks "Plan →" on an objective: choose direct vs crafted **for this task**, with model dropdown + KB scoping checkboxes + "Why recommended" justification card showing 23% better quality stat. Code has only project-wide `execution_mode` (set in contract tab) — no per-task choice, no recommendation, no KB scoping.

**Where:**
- New endpoint `POST /projects/{slug}/objectives/{ext}/recommend-mode` returning `{mode: 'direct'|'crafted', reason: str, stats: {...}}`.
- `objective_detail.html` quickTask() function — open modal instead of immediate POST.
- Task model needs an explicit `execution_mode_override` field (or use `Task.alignment` JSON).

**How:** straightforward but invasive; touches task creation flow. Recommend deferred until Phase 6 main items ship.

---

## P6.5 — USABILITY — visual progress bars + budget meter on orchestrate (VERIFIED MISSING)

**What:** Mockup 04 shows triple-color progress bar (green done / red failed / blue pending) + dual budget bars ("$4.20 / $10.00 spent · est. $3.80 remaining"). Code shows raw counts only (`tasks_completed`, `tasks_failed`); forecast endpoint exists but template renders JSON text instead of bars.

**Where:** `app/templates/_orchestrate_panel.html` — add `<div class="bar">` rendering. The forecast JSON parser is already in JS (line ~145); convert to bar widths.

**How:** ~80 LOC HTML + Alpine-style JS. No new endpoints needed.

---

## P6.6 — USABILITY — Approve / Rollback buttons on task report (VERIFIED MISSING)

**What:** Mockup 05/05v2 shows three buttons inline next to DONE badge: `✓ Approve`, `↻ Retry`, `↶ Rollback`. Code has only Retry + Re-open. No `Approve` (would mark the task as "user-acknowledged, no further action needed"). No Rollback (would `git revert` the task's commit + reset task to TODO).

**Where:**
- `app/api/tier1.py` — new `POST /projects/{slug}/tasks/{ext}/approve` (sets a new column `Task.approved_at`/`Task.approved_by_user_id`).
- `app/services/git_verify.py` — new `revert_task_commits(workspace, task_external_id) -> bool`.
- `app/api/pipeline.py` — new `POST /projects/{slug}/tasks/{ext}/rollback`.
- `task_report.html` — three buttons with confirm dialogs.

**How:** Approve is trivial. Rollback is dangerous → require typed confirmation matching task ext_id (like GitHub's "type X to delete").

---

## P6.7 — USABILITY — Skills tab: surface ROI / lift / promote-to-org (VERIFIED MISSING UI)

**What:** Endpoints exist (`/api/v1/skills/{ext}/roi`, `/projects/{slug}/lift`, `/skills/{ext}/promote-to-org`) but skills tab only shows the catalog. Three columns missing in the rendered table: Invocations · ROI USD · Δpp success-lift. No "Promote to org" button. No marketplace view (separate org-scoped catalog).

**Where:** `app/templates/project.html` skills tab (around line 980+). The HTMX target loads `/api/v1/skills/projects/{slug}` — extend the response or fetch ROI separately.

**How:**
1. Server-side: extend `/api/v1/skills/projects/{slug}` to include ROI + lift inline.
2. JS in skills tab: render 3 new columns + conditional "🚀 Promote to org" button when ≥3 projects + ≥10 invocations met.

---

## P6.8 — USABILITY — KB sources toggleable per objective + per-source last_read display (VERIFIED PARTIAL)

**What:** Mockup 09 shows checkboxes: SRC-001..004 ✓, SRC-005 ✗ excluded. Code has `kb_focus_ids` model column (P3.4) + endpoints but no inline checkbox UI on objective detail. Also: P3.5 added `last_read_at` to Knowledge but it's not displayed anywhere in the UI.

**Where:** `app/templates/objective_detail.html` — KB sources panel needs to switch from read-only list to interactive checkboxes that PUT to `/objectives/{ext}/kb-focus`. Add `last_read_at` (relative time via |reltime filter from P3.1) to each row.

**How:** ~50 LOC template change + JS to toggle.

---

## P6.9 — USABILITY — `/analyze` re-trigger UX visibility (VERIFIED PARTIAL)

**What:** Same as P6.1 but specifically: walkthrough Scenario 1 §17 says user "clicks Continue → re-analysis fires". The `re-analyze` endpoint from P6.1 needs UI. Bundling into P6.1.

---

## P6.10 — USABILITY — Description SRC pills on objective + AC source attribution visible inline (VERIFIED PARTIAL)

**What:** Mockup 09 shows: in objective description, each fact gets a `📎 SRC-004` pill inline. Same for ACs in mockup 09 §246-279. Code stores `AcceptanceCriterion.source_ref` (P-B2 work) but renders it as a small badge, not as inline-text pills near the relevant phrase. Description has zero source attribution rendering.

**Where:** Two code edits:
- `objective_detail.html` description rendering — parse `[SRC-NNN]` markers in description text and convert to clickable pills.
- `_ac_row.html` — when source_ref starts with SRC-, render with the SRC fragment inline rather than as a separate pill.

**How:** simple regex post-processor in template.

---

## P6.11 — POLISH — empty-state hero + 4-step pipeline preview (VERIFIED MISSING)

**What:** Mockup 02 shows immersive "Welcome! Let's get started." hero with step circles "Upload → Analyze → Plan → Execute" + drag-drop zone + sample-project link. Code has only a small contextual banner. Onboarding suffers — new users don't see the journey.

**Where:** `app/templates/project.html` — when `len(knowledge) == 0 and len(objectives) == 0`, render hero block before tabs.

**How:** ~120 LOC HTML/CSS (Tailwind), no backend.

---

## P6.12 — POLISH — KB source metadata: auto-refresh schedule, last crawled, auth status, token count (VERIFIED MISSING)

**What:** Mockup 02v2 shows per-source: `🔐 authed as sp-reader@acme · auto-refresh weekly · last crawled 2h ago · 12 pages indexed · 4.2K tokens`. Code shows source title + description + remove button. Missing: auth status display, refresh schedule, last_crawled time, token count.

**Where:**
- `app/models/knowledge.py` — add columns: `auto_refresh_cron VARCHAR`, `last_crawled_at TIMESTAMP`, `token_estimate INT`, `auth_status JSONB`.
- `app/services/kb_crawl.py` — populate these on every crawl.
- `app/templates/project.html` KB tab — render metadata.

**How:** schema migration + service update + template update. Half day.

---

## P6.13 — POLISH — SOW citation in decisions: "SOW says: [quote]" + Claude-recommended option (VERIFIED MISSING)

**What:** Mockup 03 decision modal shows a quote box: "SOW says: 'must support multi-tenant isolation' (SRC-001 §3.2)" + Claude's pre-selected recommendation with rationale: "Recommended by Claude — multi-tenant matches your existing infrastructure pattern". Code shows decision text + manual selection only.

**Where:**
- `app/services/delivery_extractor.py` (analyzer prompt) — extract `source_quote` + `recommendation_reasoning` per decision and persist to Decision JSONB column.
- `app/templates/_decision_card.html` — render quote box + recommended-by-Claude pill.

**How:** schema addition (`Decision.source_quote`, `Decision.recommendation_reasoning`) + analyze-prompt extension + template.

---

## P6.14 — POLISH — Challenger "REFUSED to verify" scope list on task report (VERIFIED MISSING)

**What:** Mockup 05v2 shows distinct section: "What the challenger REFUSED to verify: ❌ Security review (out of scope) ❌ Load test under 1000 concurrent users (no infra) ❌ KB alignment with SRC-007 (didn't read)". Code persists `injected_checks` but not `refused_to_verify`. The challenger prompt doesn't ask for it.

**Where:**
- `app/services/challenger.py` — extend CHALLENGE_PROMPT_TEMPLATE to require `refused_to_verify: list[str]` in the JSON output. Add to ChallengeResult.
- `app/templates/task_report.html` — render the list as a separate red-bordered section.

**How:** prompt edit + template addition. ~30 min.

---

## P6.15 — POLISH — Skill picker inline in AI sidebar (mockup 16) (VERIFIED MISSING)

**What:** Mockup 16 shows "🧩 add skill" button next to chat input — attach a skill for the next message only, without going to project config. Code has zero per-message skill attach.

**Where:**
- `app/services/ai_chat.py` — `chat()` accepts `transient_skills: list[str]` kwarg, appends each skill's `prompt_text` to system prompt.
- `app/templates/_ai_sidebar.html` — dropdown of user's available skills next to input.

**How:** small touch.

---

## P6.16 — POLISH — Copy / Download buttons on SSE log console (VERIFIED MISSING)

**What:** Mockup 04 shows two buttons above the dark log panel: `📋 Copy` + `⬇ Download`. Code has the panel but no copy/download.

**Where:** `app/templates/_orchestrate_panel.html` — add 2 buttons + small JS.

**How:** trivial.

---

## P6.17 — POLISH — Auto-attach rule display in skills library (VERIFIED MISSING)

**What:** Mockup 11 shows on each skill card: "auto-attach if `task.type=='develop' AND diff touches auth/`". Code stores `Skill.auto_attach_rule` JSONB but doesn't render it.

**Where:** `app/templates/project.html` skills tab — render `auto_attach_rule` formatted as readable text.

**How:** template-only.

---

## P6.18 — LARGER — real tool-call execution in AI sidebar (VERIFIED PARTIAL)

**What:** Mockup 16 shows the LLM actually invoking `read_entity`, `grep_sources`, `run_skill` tools and rendering each call's result inline. Code parses tool-call markers from LLM response (`ai_chat.py:200`) but never executes them — Claude is on its own.

**Where:** new `app/services/ai_tools.py` with whitelisted tool implementations + Claude CLI tool-use config.

**Why deferred:** real tool execution requires careful sandboxing + permission contract + UX for confirmation. Design needed before implementation. Same risk class as P4 from the original repair plan.

---

## P6.19 — LARGER — interrupt + redirect mid-orchestrate (walkthrough Scenario 6) (VERIFIED MISSING)

**What:** Walkthrough §6 promises: user clicks `interrupt` mid-LLM call, gets modal "interrupt at phase X? cost so far: $1.20", then redirects KB scope and resumes from cache. Today: pause works between tasks (P1.1) but cannot pause inside a Phase A/B/C call.

**Why deferred:** requires async LLM subprocess — same blocker as P4.1 from the original repair plan.

---

## P6.20 — LARGER — replay batch admin UI (walkthrough Scenario 8) (VERIFIED MISSING)

**What:** "Admin runs replay batch: take 10 archived tasks from `auth-rewrite` project, re-run them with v2 of `risk-weighted-verify` skill, side-by-side comparison." Replay endpoint exists per-call (`tier1.py /llm-calls/{id}/replay`); no batch + no comparison UI.

**Why deferred:** new admin route + comparison renderer + cost-cap discipline. Half-week of work.

---

## P6.21 — LARGER — L3 autonomy promotion preview + replay-as-if-L3 (Scenario 3) (VERIFIED MISSING)

**What:** Walkthrough: dashboard shows L3 criteria status (clean_runs_required: 7/3 ✓, contract_chars_min: 1840/1500 ✓). Click "Preview L3" → replays last 3 objectives with L3 autonomy applied to show what would have been auto-decided.

**Why deferred:** depends on real replay harness (P6.20).

---

## P6.22 — LARGER — share-link capability URL with expiry + client-facing reverse-trace (Scenario 10) (VERIFIED PARTIAL)

**What:** L4 share-link exists in code (project-scope, business view) — but mockup wants per-task share-link + expiry control + client-facing reverse-trace (read-only audit chain).

**Why deferred:** new auth scope + read-only template tree + expiry middleware. Worth a small ADR.

---

## P6.23 — LARGER — digest notifications for L5 autonomous runs (Scenario 9) (VERIFIED MISSING)

**What:** Walkthrough: "Digest at 08:00: 'O-012 ACHIEVED overnight, $4.20 spent, 2 findings open for review'". No notification subsystem today.

**Why deferred:** needs cron infra + email/Slack integration + template tree. Substantial.

---

## P6.24 — LARGER — SharePoint OAuth flow (Scenario 1 §7) (VERIFIED MISSING)

**What:** Walkthrough: user pastes SharePoint URL → Forge prompts for auth → user pastes token → crawler indexes 12 pages. Today: KB URL endpoint exists but no auth-prompt UI.

**Why deferred:** SharePoint API integration + secret storage with rotation + token refresh. Whole feature.

---

## P6.25 — LARGER — DOCUMENTATION task type spawn from objective + LLM-polished sections (mockup 10) (PARTIALLY VERIFIED)

**What:** Mockup 10 shows two-layer docs: auto-generated (working) + LLM-polished (missing). The "+ Documentation task" button exists in `objective_detail.html:482` (good — agent C was wrong here). What's missing: the docs tab UI to surface the polished output, the Edit/Regenerate buttons per section.

**Where:**
- `app/templates/project.html` docs tab — add "polished sections" subview reading from completed Documentation tasks.
- Per-section Edit + Regenerate buttons (the latter re-invokes the documentation task).

---

## Tier 1 — VETO ENFORCEMENT GAP (VERIFIED — already noted in P5 but worth bumping)

**P5 had P5.x for budget+veto config; P5 shipped only the CONFIG, not the enforcement.** Verified:
- `app/services/budget_guard.py:60 veto_match()` is defined.
- Zero call sites in `app/api/pipeline.py` or anywhere in the orchestrate loop.
- Result: user configures veto_paths, Forge happily writes to `migrations/**` or `.env*` anyway.

**Fix:** in `pipeline.py` `commit_all()` or right before, iterate `delivery.changes[*].file_path` and check `veto_match()` against project config. If match → REJECT delivery + create HIGH-severity finding.

**Severity:** Tier 1 (BLOCKING for any user who configured veto). Bumping to **P6.0** as it's a security/safety regression.

---

## Suggested execution order

**Round A (this week):** P6.0 veto enforcement, P6.1 re-analyze, P6.6 approve, P6.7 skills ROI surface — all small, all unblock visible value.

**Round B:** P6.3 decision-blocker modal, P6.5 progress bars, P6.8 KB toggles, P6.10 SRC pills — make the UX feel complete.

**Round C:** P6.11 hero + stepper, P6.12 KB metadata, P6.13 SOW citation, P6.14 challenger refuse-to-verify, P6.15 skill picker, P6.16 copy/download, P6.17 auto-attach display — visual fidelity to mockup.

**Round D (sign-off needed):** P6.18-P6.25 — async refactors, admin tools, OAuth, notifications.

## Process holes (mockup itself doesn't show)

These need NEW mockups before code:
1. **L3 promotion preview UI** — what does the "Preview L3" replay screen look like?
2. **Replay batch comparison** — side-by-side or diff?
3. **SharePoint auth modal** — token paste vs OAuth handshake?
4. **Notification preferences** — where in config does user opt into digest emails?
5. **Mid-orchestrate interrupt modal** — what state does it show?

Until these mockups exist, items P6.18-P6.25 should NOT be built — we'd be guessing at intent.

---

## Honest scoring vs. mockup

| Mockup | Pre-P1-P5 estimate | Post-P5 (claimed) | Agent re-audit (actual) |
|---|---|---|---|
| 01 dashboard | ~70% | ~85% | ~70% — still missing org banner + search |
| 02 / 02v2 KB | ~60% | ~85% | ~60% — empty hero + metadata gone |
| 03 / 03v2 objectives | ~75% | ~90% | ~75% — modal regression, no Kanban/Timeline |
| 04 orchestrate | ~65% | ~85% | ~65% — no progress bars, no copy/download |
| 05 / 05v2 task | ~70% | ~90% | ~70% — no approve/rollback, no scope-refusal |
| 07 mode | ~50% | ~70% | ~40% — per-task modal entirely missing |
| 09 objective detail | ~85% | ~95% | ~85% — KB toggle missing, SRC pills missing |
| 10 docs | ~60% | ~80% | ~50% — DOC layer not surfaced |
| 11 skills | ~55% | ~75% | ~45% — ROI/lift/promote orphaned |
| 12 config | ~80% | ~90% | ~70% — autonomy radar static, veto unenforced |
| 16 AI sidebar | ~85% | ~95% | ~90% — only skill picker missing |
| flow.html | ~80% | ~85% | ~70% — 3 endpoint gaps |

**Average reality: ~67% mockup parity** (vs. our 90% claim post-P5). The agents found ~13 features that the data model supports but the UI never surfaces — these are the cheapest to ship.

# Forge platform — backlog of remaining changes

This is the authoritative list of work NOT yet implemented in the running platform
(host: http://127.0.0.1:8063). Updated 2026-04-18.

---

## Part A — AI sidebar fixes (next batch)

These are user-flagged gaps in the just-shipped AI sidebar.

### A1. Per-page capability contract — task report page incomplete
**Symptom:** http://127.0.0.1:8063/ui/projects/{slug}/tasks/{ext} sidebar shows only 2 actions (Retry, View diff). Missing: Add AC, Add comment, Edit AC, Delete AC, Edit task instruction, Skip task, Approve, Reject, Re-run challenger, Convert finding → task, Triage finding, Re-execute manual scenario, View execution logs, Edit dependencies.

**What to do:** expand `_task_report_context()` in `app/services/page_context.py` to enumerate every API endpoint actually exposed for that page. Cross-check against routes in `pipeline.py`, `ui.py` related to a single task.

### A2. Per-page visible-data — task report page is empty
**Symptom:** sidebar context strip shows nothing meaningful. User cannot ask "what does deliverable summary say?" because LLM has no clue what's on the page.

**What to do:** in `task_view` route handler (ui.py), populate `request.state.page_ctx.visible_data` with: deliverable_summary (status, tests_passed, tests_total, challenger_verdict, findings_count, scope_limits_disclosed, ac_unsourced_count), requirements_covered (count + ids), objective (external_id + status), challenger (verdict + claims_verified + claims_refuted), findings_auto_extracted (count by severity). All as a compact JSON snapshot.

### A3. Sidebar persistence across navigation
**Symptom:** open sidebar → click any link → page reload → sidebar collapsed again. Bad UX.

**What to do:** persist open/closed state in `localStorage["forge-ai-sidebar"]`. JS reads on init, applies before first paint to avoid flash.

### A4. True sidebar layout (push content, don't overlay)
**Symptom:** sidebar overlays page content (`position: fixed` + `transform`) — user cannot read the page while chatting.

**What to do:** restructure base.html as flex container `<body class="flex">` where `<main>` flexes and `<aside>` takes ~440px when open. When closed, `<aside>` is `display: none` or `width: 0`. The toggle button stays in fixed position but body layout shifts.

---

## Part B — Skeptical UX (high-impact, partly designed in mockups)

### B1. Trust-debt counters on dashboard
Replace happy-progress tiles with: Unaudited approvals · Manual scenarios unrun · Findings dismissed without reason · Stale analyses (>7d). Each clickable to filter view.

**Schema:** need `Finding.dismissed_reason` (TEXT), `Finding.dismissed_at`, `AcceptanceCriterion.last_executed_at`. Migrate.

### B2. Source attribution mandatory on AC
**Schema:** `AcceptanceCriterion.source_ref` TEXT NULL. UI badge "INVENTED BY LLM · no source" if null. Skill `SK-cite-src-enforcer` post-check on analysis output.

### B3. "Not executed" prominence on task report
Visually elevate AC marked manual or never-run. Today they blend in. Add red counter at top of task card.

### B4. Reasoning trace ("Why did you write this?")
Each LLM-generated artifact (AC, task, finding) keeps a pointer to its source LLMCall. UI exposes a `?` button that opens a modal showing the prompt + raw response + skills attached + tool calls.

---

## Part C — Knowledge model rework (project as initiative)

### C1. Knowledge sources of 4 types with descriptions
**Schema:** rename `Knowledge.category="source-document"` to a richer `KnowledgeSource` model with `source_type` enum: `file | url | folder | manual`. Add `description` TEXT (user-written), `focus_hint` TEXT, `auto_refresh` BOOL, `last_crawled_at`. URL: store URL + auth credentials encrypted. Folder: store path + include/ignore globs.

### C2. KB tab redesign
Replace "Files" tab with **"Knowledge Base"** tab with 4 add buttons (file/URL/folder/note), source cards with descriptions, conflict-pair detection.

### C3. Per-objective KB scoping
On objective page, multi-select which sources are relevant + exclude conflicting ones. Persisted in `Objective.kb_focus_ids`.

### C4. URL crawler service
New service `app/services/kb_crawl.py` — fetch URL, extract text, handle SharePoint OAuth/cookie, recrawl on schedule. Stubs first, real crawler later.

### C5. Folder scanner service
Walk path recursively, respect ignore patterns, register each file as nested KB source with parent reference.

---

## Part D — Task model rework (4 types, DAG, re-open)

### D1. 4 task types
**Schema:** extend `Task.type` enum to include `analysis | planning | develop | documentation` (currently only generic). Each type has different default AC structure, different skills attached, different challenger prompt.

### D2. Re-open objective with gap notes
**Schema:** new `ObjectiveReopen` table — `objective_id`, `user_id`, `gap_notes` TEXT, `created_at`, `prior_state` JSONB. Status flips from `ACHIEVED` to `ACTIVE`. UI: button on objective detail "↶ Re-open with notes" (already in mockup 09v2).

### D3. Re-open task (preserve history)
Already partly done (retry endpoint). Extend: add `gap_notes` field, preserve previous result as `Execution.archived_at` so timeline shows v1, v2, v3...

### D4. Cross-objective ambiguity bubbling
When PLAN or DEVELOP task surfaces ambiguity, create new `Decision` row linked to the objective (not just the task). UI strip on objective shows "ambiguities raised by downstream tasks: N".

---

## Part E — Execution modes

### E1. Direct vs Prompt-Crafted mode selector
On every "run task" CTA, dropdown: Direct (current) vs Crafted (new). Crafted = first invokes `_craft_prompt(seed, kb, code)` returning detailed prompt, then invokes executor with crafted prompt.

**Schema:** `Execution.mode` enum `direct | crafted`. `Execution.crafter_call_id` FK to LLMCall.

### E2. Cost preview before any LLM call
Pre-flight estimate function `estimate_cost(task, mode, skills)` → `(min_usd, max_usd)`. Show as tooltip + confirmation modal before commit.

---

## Part F — Skills

### F1. Skill model (3 categories)
**Schema:** new `Skill` table — `id`, `external_id` (`SK-*`, `MS-*`, `OP-*`), `category` enum, `name`, `prompt_text`, `auto_attach_rule` JSONB, `applies_to_phases` array, `created_by` (user_id or NULL for built-in).

### F2. Project ↔ Skill many-to-many
`ProjectSkill` join table — `project_id`, `skill_id`, `attach_mode` enum (`auto | manual | default`).

### F3. Skill effectiveness scoring
Track per-skill: `total_invocations`, `total_cost_usd`, `findings_caught_count`, `user_overrides_count`. Background job computes ROI score weekly.

### F4. Skill marketplace (org-level)
Skills with `created_by IS NULL` or `org_id IS NULL` are global; org admins can promote project-level skills to org marketplace.

### F5. Phase defaults
Project config has `default_skills_per_phase` JSONB — applied if user picks none. UI in project config page (mockup 12 already designed).

### F6. Auto-attach rule engine
For each LLM call, evaluate skills' auto_attach_rule against task metadata (type, phase, files touched). Attached skills inject their prompt_text into the system prompt.

---

## Part G — Operational contract

### G1. Per-project contract storage
**Schema:** `Project.contract_md` TEXT default to org template. `ProjectContractRevision` audit table (every save preserved).

### G2. Contract editor UI
Tab "Operational contract" on project (mockup 12). Markdown editor + preview + revert + LLM-suggest-improvements (read-only suggestions).

### G3. Contract injection in prompts
Modify `prompt_parser.py` to prepend contract_md (truncated to ~2000 tokens) to every analysis/planning/develop/doc prompt.

---

## Part H — Post-stage hooks

### H1. Hook config per project
**Schema:** `ProjectHook` table — `project_id`, `stage` (`after_analysis | after_planning | after_develop | after_doc`), `skill_id`, `enabled`, `purpose_text`.

### H2. Hook execution
After any task of given type completes, fire all enabled hooks for that stage. UI in project config (mockup 12).

---

## Part I — Autonomy levels

### I1. Org/project autonomy state
**Schema:** `Project.autonomy_level` enum `L1 | L2 | L3 | L4 | L5`. `AutonomyAudit` table tracking promotions, overrides, veto triggers.

### I2. Promotion criteria engine
Service computes: clean_runs_count, override_count, audit_pass since last promotion. When threshold reached → enable next level (still requires explicit user confirm).

### I3. Watchlist
`Objective.autonomy_optout` BOOL — flagged objectives stay manual even at L5.

### I4. Veto clauses
Configurable stopwords: budget %, file path patterns, decision reversal. Enforced in orchestrator before each step.

### I5. Digest mode for autonomous runs
At L3+ collect events, send daily digest instead of per-event notification.

---

## Part J — Forensics & memory

### J1. Cost forensic page
Per-task drill: phase cost, retries, context growth across retries, root cause classifier. URL: `/ui/projects/{slug}/tasks/{ext}/cost-forensic`.

### J2. Mid-run trajectory forecast
During orchestrate run, compute projected cost based on rolling avg per task. Display on live panel. Pulse red if projected > budget.

### J3. Reverse-trace UI page
URL: `/ui/projects/{slug}/reverse-trace?from=...`. Walk back: code symbol → execution → task → planning task → objective → ambiguity → SRC. Visual graph.

### J4. Lessons log
After objective ACHIEVED, run skill `SK-extract-lessons` → store as `ProjectLesson` rows. Inject lessons into future analysis prompts on this project.

### J5. Anti-pattern registry
On objective re-open: extract "what was wrong" → `ProjectAntiPattern`. Future planning prompts include "do not repeat: ...".

### J6. Replay harness
For any historical task, store full prompt + skills + contract version. Endpoint to re-execute with current config and diff outputs.

---

## Part K — Triage / cross-project

### K1. Org-wide triage dashboard
URL: `/ui/org/triage`. Lists across all projects: open ambiguities, failed tasks, dismissed findings, stale analyses. Sortable.

### K2. Cross-project pattern promotion
Skills used by ≥3 projects with positive ROI promoted to org marketplace.

### K3. Org budget overview
Aggregate cost per project, per skill, per user. Trend lines.

---

## Part L — Documentation deliverable

### L1. Auto-draft docs from code (deterministic)
Extract API routes from FastAPI router definitions, DB schema from SQLAlchemy models, changelog from task DONE events. Render as markdown in Documentation tab.

### L2. DOCUMENTATION task type execution
When task.type=documentation, special prompt template: "use deliverables + code, write [section_type] doc". Output is markdown stored on objective.

### L3. Per-objective rollup
For each ACHIEVED objective, generate a 1-page rollup: inputs (KB sources used) → outputs (ADRs, tasks, findings) → cost+time → lessons.

### L4. Share-link client view (business view, not technical)
Share-link page strips internal data, shows: objectives + KR met + timeline + budget. Hides code, raw findings, internal IDs.

---

## Implementation order (suggested)

**Tier 0 — sidebar fixes (now):**
A1, A2, A3, A4

**Tier 1 — small impactful:**
B1 (trust-debt counters), B2 (source attribution AC), G1+G3 (contract storage + injection), D2 (re-open objective), D1 (4 task types), L1 (auto-draft docs)

**Tier 2 — medium:**
C1+C2 (KB rework), B4 (reasoning trace), J1+J2 (cost forensic + forecast), J3 (reverse-trace UI), F1+F2+F5 (skills v0)

**Tier 3 — large:**
E1 (Crafted mode), I1-I5 (autonomy), C4+C5 (URL/folder crawl), J6 (replay harness)

**Tier 4 — org-scale:**
F3+F4 (skill ROI + marketplace), K1-K3 (triage + cross-project), L4 (client view)

---

## Stable tracking

Each item has a stable code (e.g. `B1`, `J3`). Use these in PR titles and commits.
This file is the single source of truth for "what's left in Forge platform".
Update on every merge.

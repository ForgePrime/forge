# Forge Mockup Deep Analysis + Agent Prompt

**Scope:** Revised (post-feedback) mockups only — 10 screens + flow + walkthrough. For each screen: per-element data sources, creation path, editability; entry/exit transitions; completeness of the process; proposed additions; ends with an agent prompt ready to hand off.

**Design lens:** "Forge UX is skeptical, not reassuring" (from `index.html`). Every screen must surface what wasn't done, wasn't checked, was assumed silently. Approve is tertiary; primary actions are scrutinize, add scenario, re-open.

---

## Part 0 — the 10 Revised screens at a glance

| # | File | Role in the process |
|---|---|---|
| 02v2 | `02v2-project-kb.html` | KB-first project view; the substrate everything reads |
| 03v2 | `03v2-objectives-dag.html` | Portfolio view of objectives; entry to work |
| 09 | `09-objective-detail.html` | **Heart of system** — where user thinks; Q&A, scenarios, AC, tasks |
| 07 | `07-mode-selector.html` | Before starting any task: direct vs crafted |
| 05v2 | `05v2-task-deliverable.html` | After a develop task DONE: scrutinize before closing |
| 10 | `10-post-exec-docs.html` | Two-layer docs for client / audit |
| 11 | `11-skills-library.html` | Catalog of attachable capabilities |
| 12 | `12-project-config.html` | Operational contract + skills + hooks + autonomy |
| 16 | `16-ai-sidebar.html` | Persistent collaboration layer (every page) |
| flow | `flow.html` | Macro diagram: project → objective → task types → achieved (with loops) |

---

## Part 1 — Per-screen deep analysis

### 02v2 — Project + Knowledge Base (KB tab)

**Entry points:**
- From `01-dashboard.html` by clicking a project tile
- From deep link (bookmark, share)

**User intent on landing:** "I want to add/review the sources Forge will read." For a fresh project, this is the first thing a user does.

**Transitions out:**
- Click `🎯 Objectives` tab → `03v2-objectives-dag.html`
- Click `+ New Analysis task` → should go to a task-creation modal (**MISSING MOCKUP** — goes nowhere)
- Click any SRC card → should preview content (**MISSING MOCKUP** — no preview dialog)
- Click `Resolve ambiguity` on SRC-005 → should go to that decision (**MISSING** — 03-project-post-analyze is v1-only, shows project-level list not per-source)

**Element-by-element audit:**

| Element | Source of data | Created by what | Why here | Edit where | Problem / note |
|---|---|---|---|---|---|
| Initiative header (name, goal description) | `Project.name`, `Project.goal` (DB) | User on project create | Primary identity | Edit form (not mocked) — should be in `12-project-config.html` | Mockup shows `⚙ Settings` but button doesn't lead anywhere. |
| Tabs (KB · Objectives · Tasks · Activity · Reports) | Navigation state | Hard-coded by template | Primary navigation | n/a | `Activity` + `Reports` tabs promised but have NO mockup. |
| KB intro box | Static explainer | Template literal | Teach first-time user what KB means | n/a (docs are non-editable) | OK. |
| 4 "+ Add source" buttons (File / URL / Folder / Manual note) | Action intents | Template | Primary action | n/a | Buttons have NO destination modal mocked. Agent must add 4 modals (file picker, URL-with-auth, folder-path-with-ignores, manual-note-editor). |
| Source list row — ID, type badge, title | `Knowledge.external_id`, `Knowledge.source_type`, `Knowledge.title` | Source ingestion pipeline | Identify source | This page (Edit desc / Remove) | OK but row lacks CONTENT preview button that reveals chunks. |
| Per-source description ("Describes: …") | `Knowledge.description` (user-written) | User via Edit desc modal | Helps LLM focus | This page inline | **User needs a richer description editor mockup** — current "Edit desc" has no form. |
| Auto-refresh / last crawled | `Knowledge.auto_refresh_cron`, `last_crawled_at`, `auth_status` | Crawler service | Trust signal (source freshness) | For URL: dedicated re-auth modal (**MISSING**) | No way to retrigger `Re-crawl` flow visually. |
| "Claude last read" timestamp | Backend `Knowledge.last_read_at` updated when KB injected into a prompt | Internal instrumentation | Pruning hint (if never read → probably useless) | Not editable (read-only audit) | OK. |
| "referenced in 3 objectives" counter | Aggregate: `Objective.kb_focus_ids` + task consumption | Runtime join | Trust signal (unused sources stand out) | n/a | OK, but should link → list of those objectives. |
| Conflict badge (SRC-005 CONFLICTS WITH SRC-002) | `Decision(type=ambiguity, severity=HIGH)` | Analysis task that flagged it | Prevent silent contradictions | Resolve in an ambiguity-modal (**MISSING**) | "→ Resolve ambiguity" has no destination mockup. |
| "referenced by analysis task AT-002" | Backlink from the flagging task | `Decision.source_task_id` | Audit / provenance | n/a | OK, but should link to task. |
| "+ New Analysis task →" CTA | Action | Template | Pushes user forward after KB loaded | Modal (not mocked) | **Major gap** — no mockup for the NEW TASK modal (all 4 task types use this). |

**Continuity gaps from this screen:**
- **(G-1) No task-creation modal mockup** — 4 "Add source" buttons + "New Analysis task" all lead to nothing.
- **(G-2) No source-preview mockup** — clicking Preview goes nowhere.
- **(G-3) No ambiguity/decision detail mockup** — clicking "Resolve ambiguity" on SRC-005 has no destination.
- **(G-4) No project-settings mockup** — `⚙ Settings` on header opens... what?

---

### 03v2 — Objectives DAG

**Entry points:**
- From `02v2-project-kb.html` via tabs
- From `01-dashboard.html` click on "running" pill of a project
- Deep link

**User intent:** "Where is the work right now, what's blocked, and where can I advance?" Uses DAG when >5 objectives; switches to List for small portfolios.

**Transitions out:**
- Click an objective node → `09-objective-detail.html`
- Click `+ Objective` → **MISSING** (create-objective modal)
- Click `+ Analysis task` (toolbar) → `09` or new-task modal (**MISSING**)
- Click `Resolve all` (ambiguity banner) → should open decisions list (**PARTIAL**; 03-v1 shows it but that's superseded)
- View-switch DAG → List/Kanban/Timeline → only DAG + List have mockups (**MISSING** Kanban + Timeline)

**Element-by-element:**

| Element | Source | Creator | Why here | Editable where | Problem |
|---|---|---|---|---|---|
| View toggle (DAG · List · Kanban · Timeline) | Query param `?view=` | User click | Suits different sizes of portfolio | n/a | Kanban + Timeline absent as mockups. |
| `+ Analysis task` + `+ Objective` buttons in toolbar | Action | Template | Primary creation actions | n/a | **Neither modal mocked.** |
| Ambiguity banner ("3 ambiguities...surfaced by analysis tasks AT-001 and AT-002") | Aggregated from `Decision.status='OPEN'` joined to tasks | Analysis task flagging | Block forward work on objectives depending on resolution | Resolve in decision detail (missing mockup) | The "surfaced by..." attribution is rich but nowhere is this attribution editable (who surfaced what — analysis task or user). |
| Legend (4 task types + edge semantics) | Static | Template | Educate mental model | n/a | Edge semantics on the canvas itself differ from implementation — no blocked-amber edge in live code. |
| Objective node — ID + type badge (ANALYSIS/PLANNING/DEVELOP/DRAFT) | **Requires `Objective.type` column** that doesn't exist in data model | Analysis task (or user at create) | Signals objective's dominant work | Objective-edit form (missing mockup) | **Mockup assumes typed objectives; DB doesn't model this.** |
| Objective status (ACHIEVED / BLOCKED / WAITING / DRAFT) | `Objective.status` | Analysis / user / dependency check | Signals advance-ability | Re-open / close buttons on `09` | OK at model level. |
| Inline "⚠ 2 ambiguities: cloud vs on-prem · DB choice" inside blocked node | Top-2 open `Decision` issues tied to the objective | Analysis task | Instant diagnosis without entering detail | Resolve in decision detail (missing) | Inline actions ("→ Resolve" / "+ Planning task") should open modals — not mocked. |
| Sub-tasks mini-view (AT-001..AT-004 cards at bottom) | Tasks where `origin=O-001` | Planning/analysis | Shows what produced the objective's current state | Click into task detail | OK, but only shown for O-001; why not all objectives? Accordion expand needed. |
| 4-type educational strip (persona + AC examples) | Static | Template | Teach schema | n/a | Good; missing only for Documentation in this mockup (but covered in `09`). |

**Continuity gaps:**
- **(G-5) No Kanban / Timeline mockup** — promised in toggle.
- **(G-6) No create-objective modal** — `+ Objective` goes nowhere.
- **(G-7) No ambiguity-detail page / answer-form mockup** — banner "Resolve all →" has no destination.
- **(G-8) DB-level:** `Objective.type` column implied by mockup but needs to be added.

---

### 09 — Objective detail (heart of system)

**Entry points:**
- From `03v2-objectives-dag.html` clicking a node
- From dashboard activity feed entry
- Deep link `?O=O-002`
- From task report (05v2) clicking "from objective O-003"

**User intent:** "I need to decide what to do next on this objective." 80% of the real work happens on this page. It's where ambiguity gets answered, AC refined, scenarios added, tasks spawned.

**Transitions out (many):**
- Click KB source checkbox → toggles `Objective.kb_focus_ids` (editable in place, good)
- Click "Manage" on KB panel → `02v2-project-kb.html`
- Click an `O-001` dependency card → `09` for that objective
- Click `Re-open` → opens form (mocked inline on 05v2 but at OBJECTIVE level here → **NOT MOCKED** at objective scope)
- Click `🪄 Ask LLM to expand` on description → streams into description OR opens AI sidebar? **AMBIGUOUS**
- Click `Answer →` on Q-007 → ambiguity-answer modal (**MISSING**)
- Click `🪄 Regenerate from sources` on AC → **MISSING** (triggers an analysis sub-task?)
- Click `+ Add manually` on AC → inline editor (**MISSING**)
- Click `+ Add scenario` → inline editor with type picker (**MISSING**)
- Click any of 4 "+ task" buttons → mode selector `07` for that type
- Click task card (AT-005 etc) → task detail `05v2`
- Click `▶ Continue anyway` in scrutiny debt strip → triggers re-analysis? cost $? (**AMBIGUOUS transition**)
- Click `Acknowledge debt` → opens acknowledge form (**MISSING**)

**Element-by-element (this is a big page):**

| Element | Source | Creator | Why here | Edit path | Issues |
|---|---|---|---|---|---|
| Header badges (`depends on O-001 ✓`, `blocks O-003, O-005`) | `objective_dependencies` table | Planning or analysis task | DAG position inline | Add/remove deps in DAG view or here (modal missing) | No UI to edit deps inline. |
| Status strip (Progress / Tasks / Ambiguities / Cost) | KR progress (`key_results`), tasks join, decisions count, `llm_calls` sum | Rollup | Instant status check | Not editable (derived) | OK. |
| **Scrutiny debt strip** (4 counters + 2 buttons: Acknowledge debt / Continue anyway) | Aggregate: `user_answered_pre_selected`, unresolved ambiguities, AC without source_ref, scenario count vs threshold | Analysis task + ambiguity resolve events | Skeptical-UX contract made visible | Acknowledge in modal (missing); Continue triggers re-analyze | **This strip is unique to Forge's skeptical contract.** But `Continue anyway` behavior is under-specified. |
| KB sources panel with checkboxes | `Knowledge` filtered by project + `Objective.kb_focus_ids` for this objective | User | Narrow LLM focus for expensive tasks on this objective | Toggle here (clicks persist to DB) | OK; mockup implies per-objective scoping. |
| DAG neighbors panel | `objective_dependencies` | Planning | Visual context without leaving page | Add/remove via drag? (not mocked) | No inline edit. |
| Description — LLM draft + user notes with source pills | `Objective.description` + `Objective.business_context` + optional source markup `[SRC-004]` | Analysis task drafts, user edits | Single source of truth for intent | Inline Edit; `🪄 Expand with LLM` | Unclear: does `Expand` rewrite or append? Does it open sidebar? |
| Open ambiguities list (Q-007 HIGH, Q-008 MEDIUM) with Why/Ref/`Answer →` | `Decision(status=OPEN, objective_id=X)` | Analysis task | Blocking intent | Answer in modal (**MISSING**) | Per-Q "Answer →" promises a form that doesn't exist as a mockup. |
| Resolved ambiguities (Q-003..Q-006) | Same table, status=CLOSED | Analysis + user | Audit trail | Not editable (history) | OK, but users may want to reopen a decision. |
| AC list with source pills (SRC-003, needs Q-007) | `AcceptanceCriterion.text`, `.source_ref` | Analysis | Contract for planning/develop | Edit inline / `+ Add manually` / `🪄 Regenerate` | Add-manually needs form mockup; Regenerate is a sub-task (cost?). |
| Test scenarios (EDGE CASE / FAILURE MODE / SECURITY) | New entity `TestScenario` tied to objective; not in current DB | Analysis (generates) + user (adds) | Force plan to handle non-happy-path | `+ Add scenario` form (missing) | **Scenario entity not in current data model.** |
| Challenger will verify (per-objective rules) | `Objective.challenger_checks` JSONB | Analysis flags + user curates | Encoded domain-specific verification per objective | Add/remove (missing) | No UI mocked for managing this list beyond read-only. |
| Ask Forge to... (4 task-type buttons) | Action | Template | Primary creation | Leads to `07` mode selector | OK. |
| Tasks on this objective list | `Task WHERE origin=O-002` | All task creations | See pipeline per-objective | Click into task | `AT-006 PENDING re-run` is suggestive of a state transition that needs own button — manual "Re-analyze with my answers" trigger. |
| Recent activity | `AIInteraction` + `TaskStateTransition` log | All events | Transparency | Not editable | OK. |

**Continuity gaps:**
- **(G-9) Ambiguity answer form mockup missing** — per-Q Answer → dead-end.
- **(G-10) Add AC / scenario inline form missing.**
- **(G-11) Objective re-open form missing at objective level** (05v2 re-opens a task, not an objective).
- **(G-12) Description LLM-expand interaction undefined** (inline edit? sidebar? diff preview?).
- **(G-13) Test scenario entity doesn't exist in data model.**
- **(G-14) Challenger-checks CRUD UI missing.**

---

### 07 — Mode selector (Direct vs Crafted)

**Entry points:**
- From `09` when clicking any of the 4 "+ task" buttons
- From `03v2` toolbar "+ Analysis task"
- From sidebar slash command `/start-task analysis`

**User intent:** "I'm about to spend money on an LLM run. Which mode?" Decides once per task creation.

**Transitions out:**
- Click `Preview crafted prompt →` → crafter-preview-result page (**MISSING**)
- Click `Start planning task →` → `04-orchestrate-live.html` (live run)
- Click `Cancel` → back to the referring page
- Uncheck a KB source → persists to task config (editable here)

**Element-by-element:**

| Element | Source | Creator | Why here | Editable | Issues |
|---|---|---|---|---|---|
| Task header (PLANNING O-002 title) | Forwarded from caller | Caller resolves | Identify what's being run | Read-only (already decided) | OK. |
| Direct mode card | Static explainer + cost/time estimates | Template + backend stats | Tradeoff visible | Pick via radio | Cost estimate should be dynamic (query-based) but is static in mockup. |
| Crafted mode card (recommended highlight) | Same + recommendation logic | Recommendation engine (**MISSING ENDPOINT**) | Per-task recommendation | Pick via radio | Recommendation "23% better quality" is hardcoded. Should be live stat per task-type + past scores. |
| Why-recommended card | Explanation blob | Recommendation engine | Justify the nudge | n/a | Engine doesn't exist; text is illustrative. |
| Crafter preview button | Action | Template | Preview before committing | n/a | Target page missing. |
| Advanced: model selection dropdowns | Per-task config | User override | Cost / quality tuning | Here inline | Not persisted per-task in current model. |
| Max cost input | Per-task budget | User | Hard cap for this run | Here inline | Stored as `Task.budget_override_usd`? Missing column. |
| KB focus checkboxes | `Objective.kb_focus_ids` (inherited) + overridden at task level | User override | Narrow context for this single run | Here inline | **Task-level override column missing.** |
| Start button | Submit | Template → creates Execution row | Commit | n/a | OK. |

**Continuity gaps:**
- **(G-15) No crafter-preview-result mockup.** User can't see what they're committing to.
- **(G-16) Recommendation engine isn't specified as data source** — how is "recommended" computed?

---

### 05v2 — Task deliverable (DEVELOP type)

**Entry points:**
- Auto-navigate after task DONE (from `04-orchestrate-live.html`)
- From `09` task list clicking DT-009
- From activity feed
- From findings list (if filtering by task)

**User intent:** "This task is DONE. Is it *closable safely*?" Primary mode is scrutiny — NOT approval.

**Transitions out:**
- `+ Ask challenger to verify specific aspect` → AI sidebar opens with pre-filled `/run-skill challenger --scope=...` (**PARTIAL** — sidebar has the pattern but the pre-filled scope form is missing)
- `+ Add scenario I realized is missing` → scenario-add modal (**MISSING**)
- `↶ Re-open with gap note` → inline form shown at bottom (mocked)
- `Close task (requires reason)` → close-modal with reason field (**MISSING**)
- `Generate test & run now` on user-added scenario → kicks a one-shot LLM test generation (no mockup for result, only action)
- `Assign to auditor` on manual scenario → (**MISSING** — no auditor assignment UI)
- `Create follow-up task` on a concern → task-creation modal with pre-filled context (**MISSING**)
- `Mark verified manually` → writes a user-note and closes that scenario (no confirmation modal)
- `+ Ask for security review` / `+ Ask for KB alignment check` → adds scope to challenger request (**MISSING** flow)

**Element-by-element:**

| Element | Source | Creator | Why here | Editable | Issues |
|---|---|---|---|---|---|
| Task metadata + mode badge (🎯 crafted) | `Task.type`, `Execution.mode` | Orchestrator | Identify + trace | n/a | OK. |
| "DONE — awaiting your scrutiny" banner | Composite: task.status=DONE + `has_unresolved={scenarios_unrun>0 OR findings.medium>0 OR AC.unsourced>0}` | Rollup | Skeptical contract | n/a | OK. Rollup logic should be explicit — currently ad-hoc. |
| 5-card scrutiny strip | Computed counts (scenarios, tests, challenger verified/refused, findings unresolved, AC unsourced) | Rollup | Diagnosis | n/a | OK. |
| Scenarios list with expand → test body | `AcceptanceCriterion.text` + test_path → file read from workspace | Planning writes AC; Develop runs tests | Evidence that tests actually ran | Edit inline (not mocked) | Expand shows pytest body — requires workspace file access which exists. |
| User-added not-run scenario (amber) with "Generate test & run now" | `AcceptanceCriterion.user_added=True AND last_executed_at=NULL` | User via `+ Add scenario` | Visible hole in coverage | Generate button or Edit | **`user_added` column doesn't exist in current model.** |
| User-added MANUAL scenario with "Assign to auditor" | Same + `verification='manual'` | User | Can't auto-test, needs human | Assign via dropdown (**MISSING**) | Auditor model (users with role) needs to exist. |
| Challenger "REFUSED to verify" box | `LLMCall.delivery_parsed.refused_to_verify` (new field, not persisted yet) | Challenger prompt output | Scope honesty | n/a | **Backend doesn't extract this today.** |
| Per-claim verifications list | `LLMCall.delivery_parsed.per_claim_verdicts` (exists) | Challenger | Audit trail | n/a | OK. |
| Concerns (MEDIUM) with 3 actions (Create follow-up / Accept as known / Dismiss) | `Finding(challenger-surfaced, severity=MEDIUM)` | Challenger | Gaps user must decide on | Act on each | "Create follow-up task" lacks mockup for the form. |
| Close-safety note | Challenger summary + refused scope | Challenger post-process | Last-chance warning before close | n/a | OK; scope-refused still missing from backend. |
| Re-open form with gap note + "Auto-invoke challenger" checkbox | `Task.reopen_notes`, `Task.auto_rechallenge` | User inline | Recovery pattern | Here inline | OK but objective-level re-open lacks same pattern. |

**Continuity gaps:**
- **(G-17) Close-task modal with reason missing.**
- **(G-18) Create-follow-up-task modal missing.**
- **(G-19) Scenario-add inline form missing** (here + `09`).
- **(G-20) Auditor assignment flow missing** (user-model extension + assign UI).
- **(G-21) Challenger "refused to verify" not in backend model.**

---

### 10 — Post-execution documentation

**Entry points:**
- From any task/objective reaching ACHIEVED
- From project tabs → Documentation
- Via share link from client (read-only variant; no mockup)

**User intent (two modes):**
- **Internal:** "What do I show the client / auditor? What's auto-live vs hand-polished?"
- **Client (share-link):** read-only view of the deliverable story.

**Transitions out:**
- Click section TOC → anchors within the page (smooth-scroll)
- Click "+ Add DOCUMENTATION task" → task-creation modal for DOC type (**MISSING**)
- Click section `Edit` → inline markdown editor (**MISSING**)
- Click section `↻ Regenerate` → spawn DOC task run with same inputs (**MISSING flow + cost preview**)
- Click `View task` → `05v2` for that DOC-type task (**MISSING** — no DOC task report mockup)
- Click `📥 Export as` → format dropdown + download
- Click `🔗 Share link for client` → share-link creation modal with expiry + scope (**MISSING**)

**Element-by-element:**

| Element | Source | Creator | Why here | Editable | Issues |
|---|---|---|---|---|---|
| TOC sidebar | Auto from h1/h2 of rendered sections | Template (TOC extractor exists) | Nav | n/a | OK. |
| README (auto) | Template from `Project` + resolved `Decision` rows | Deterministic build | Live-current | Not editable (regenerated each visit) | OK. |
| Architecture overview (DOC task) | `Task(type=documentation, status=DONE).delivery.output_md` | DOCUMENTATION task | LLM-polished narrative | Edit via task re-run | DOC-task mockup is absent for the task itself (what does its 05v2 look like?). |
| API reference (auto) | FastAPI routes parsed | Extractor | Live-current | Not editable | OK; extractor exists partially. |
| ADR list | `Decision(status=ACCEPTED)` + template | DOC task + auto | Industry-standard deliverable | New ADR form → DOC task input | "+ Write new ADR" mockup missing. |
| Changelog (auto) | `git log` + task-deliverable summaries | Extractor | Historical trail | Not editable | OK. |
| Per-objective rollup | Aggregate: inputs (KB/decisions), outputs (ADRs/tasks), cost/time | Rollup service | Audit story | Not editable | OK; agent may add "expand to full detail" expandable. |
| Share link button | Action | Template | Client handoff | Modal missing | **Critical gap** — client sees nothing without this. |

**Continuity gaps:**
- **(G-22) No DOCUMENTATION task report mockup** (05v2 equivalent for DOC type).
- **(G-23) No share-link creation modal** (expiry, scope, password?).
- **(G-24) No section-edit inline editor.**
- **(G-25) No "+ Add DOC task" modal.**

---

### 11 — Skills library

**Entry points:**
- From `12-project-config.html` (active skills sidebar "Browse library →")
- From sidebar "🧩 add skill" on any page
- Direct nav (left menu, not shown)

**User intent:** "Which capabilities should I attach to this project (or this single task)?" Balance: coverage ↔ cost.

**Transitions out:**
- `View source` / `View prompt` → skill-detail page (**MISSING**)
- `Edit auto-attach rule` → rule editor modal (**MISSING**)
- `Install for this project` → install-flow modal with conflict-check (**PARTIAL** — for Cloud-architect we see "conflict with SRC-004" warning but no actual modal)
- `Detach from project` → confirm dialog (**MISSING**)
- `Clone & customize` → skill editor (**MISSING**)
- `+ Create new skill` → skill editor (**MISSING**)
- Phase-default "edit for this project" → `12-project-config.html`

**Element-by-element:**

| Element | Source | Creator | Why here | Editable | Issues |
|---|---|---|---|---|---|
| 3-category count cards | `SELECT category, COUNT FROM skills` | Aggregate | Show library size | n/a | OK. |
| Filter bar (phase / category / sort) | UI state | User | Find what you need | n/a | OK. |
| Tab bar (Installed / Auto-attached / Marketplace / My custom) | `ProjectSkill.attach_mode` + `Skill.organization_id` | User + seeding | Scope the list | n/a | "Marketplace" scope is org-level; **org marketplace UI missing.** |
| Skill card — ID + category + status pill | `Skill`, `ProjectSkill.attach_mode` | User attached | At-a-glance | Detach here | OK. |
| Success-lift column | Computed: pass-rate before vs after attachment | Rollup service (exists partially) | ROI signal | Not editable (derived) | **Not shown in live UI**; algorithm is approximation. |
| Cost impact (+$0.08/call) | `Skill.cost_impact_usd` or computed | Seeder + measurement | Budget awareness | Skill editor (missing) | OK. |
| Auto-attach rule | `Skill.auto_attach_rule` JSONB | Seeder + user | Automation | Rule editor (missing) | **No mockup for editor.** |
| Conflict warning (Cloud vs SRC-004) | Detector: skill tags × project constraints | Backend service (**MISSING**) | Prevent silent undermining | n/a | Logic exists nowhere in backend. |
| Phase-default summary | Config-level | User via `12` | Fallback when user picks nothing | Go to `12` | OK; good bridge between these two screens. |

**Continuity gaps:**
- **(G-26) Skill-editor mockup missing** (prompt text, applies_to_phases, tags, auto-attach rule visual builder).
- **(G-27) Skill-install flow with conflict check missing.**
- **(G-28) Org marketplace view missing.**
- **(G-29) Skill-source / View-prompt page missing.**

---

### 12 — Project config

**Entry points:**
- From project-tile `⚙ Settings` (undefined destination earlier, should land here)
- From `11-skills-library.html` ("edit for this project")
- Direct nav

**User intent:** "Set the constraints that stay constant across all tasks on this project." Heavy ops.

**Transitions out:**
- Tabs: `📜 Operational contract` (shown) · `🧩 Skills selection · 12` · `🪝 Hooks · 4` · `⚙ Phase defaults` · `💰 Budget + limits` · `🔑 Integrations` — only Contract tab mocked
- Click `LLM suggest improvements` → suggestion panel (implementation exists, **UX flow not mocked**)
- Click `+ Add hook` → hook editor modal (**MISSING**)
- Click `enable →` on L3 autonomy → autonomy-promotion flow (**MISSING** — should show criteria checklist + preview)
- Click `Rebalance` on skills overhead → skill-set suggestion modal (**MISSING**)
- Contract history → revisions viewer / diff (**MISSING**)

**Element-by-element:**

| Element | Source | Creator | Why here | Editable | Issues |
|---|---|---|---|---|---|
| Tab set | State | Template | Split massive config into subdomains | n/a | Only Contract tab mocked; 5 others absent. |
| Contract editor | `Project.contract_md` | User | Constant prompt-layer rules | Here | OK. |
| Contract metadata bar | Computed (word count, token count, revision count) | Derived | Cost signal | Not editable | OK. |
| Contract LLM-suggest button | AI service call | User trigger | Improve signal-to-noise | Result panel inline | Result rendering not mocked. |
| Active skills sidebar | `ProjectSkill` rows | User | Audit of what's injected | Detach here | Good summary; links to `11` for changes. |
| Contract history | `ContractRevision` | Save events | Audit trail | Not editable | No diff viewer mockup. |
| Post-stage hooks (4 rows) | `ProjectHook` | User | Invariants per stage | Enable/edit/remove | **No hook-editor mockup.** |
| Autonomy roadmap (L1-L5) | `Project.autonomy_level` + criteria check (`autonomy_criteria_eval()`) | Service | Gradual trust transfer | enable → flow missing | Critical UX — "why I can't get to L3" needs a whole modal. |
| Block-reason hint ("3 pre-selected-ignored...") | Computed (audit of past resolutions) | Rollup | Explainable block | Not editable (audit) | OK; links should go to those specific ambiguities. |

**Continuity gaps:**
- **(G-30) Only Contract tab shown; Skills-selection / Hooks-list / Phase-defaults / Budget / Integrations tabs missing.**
- **(G-31) Hook editor (trigger, skill, conditions) missing.**
- **(G-32) Autonomy-promotion criteria modal missing.**
- **(G-33) Contract-diff viewer missing.**

---

### 16 — AI sidebar

**Entry points:**
- Visible on every page (persistent)
- Hidden via ⊟ button
- Restored via keyboard shortcut

**User intent:** "Ask Forge something while I'm looking at X without leaving X."

**Transitions out (from sidebar back to main content or other pages):**
- Click AI-rendered action button ("Accept AC-6, 7, 8") → writes to the main entity and refreshes the main content (**PARTIAL**: no mockup showing preview-diff modal for destructive actions)
- Click `@T-005` mention → probably opens task in main pane (unclear; sidebar could also open a mini-card)
- Click `/replay @task` → opens replay result page (**MISSING**)
- Click `/cost-drill @task` → opens cost forensic view (**MISSING** — exists as endpoint but no UI)
- Click `/reverse-trace @AC-5` → opens trace page (**MISSING**)
- Click `history` → conversation history list (**MISSING**)
- Click `settings` → sidebar settings (context size, model pick) (**MISSING**)

**Element-by-element:**

| Element | Source | Creator | Why here | Editable | Issues |
|---|---|---|---|---|---|
| Header context line | Current page + entity state | Middleware injects into request | Proves LLM knows where user is | Not editable | OK. |
| Capability contract collapsible | Per-page action descriptors | Page context builder | Transparency | Not editable | Some actions (`Answer Q's`) imply sidebar can mutate main; main-page refresh after needs to be defined. |
| Suggestion chips | Computed from page state | Page-specific suggestion generator | Lower friction | Not editable | OK. |
| Conversation thread | `AIInteraction` rows | User + LLM responses | Persistent history | Not editable per message | OK. |
| Tool-call detail cards | `AIInteraction.tool_calls` JSONB | LLM side-effects | No black box | Not editable | Requires real tool-use dispatch in backend (not yet integrated; Claude CLI handles it). |
| Scope-limit box | Parsed from LLM response | Prompt contract | Enforces skeptical UX | Not editable | OK. |
| Action buttons on LLM suggestions | Generated by LLM response parser | Response → template action | Preview-before-apply | Confirm preview (missing for destructive) | **Critical: no "destructive action preview modal" mocked.** Mockup shows button but clicking "Remove AC-5" should show diff + confirm. |
| Slash command dropdown | Static command list | Template | Discovery | n/a | OK. |
| Input area (attach KB, add skill, plan-first) | UI controls | Template | Per-message tweaks | n/a | "🧩 add skill" goes to... what? Inline picker? Missing mockup. |

**Continuity gaps:**
- **(G-34) Destructive action preview modal missing** — any "Apply" on LLM suggestion should preview diff and require confirm.
- **(G-35) Replay / cost-drill / reverse-trace result pages missing.**
- **(G-36) Conversation history list missing.**

---

### flow.html — Process diagram

**Not a page users visit.** Reference for designers / onboarding docs.

**Key invariants claimed (lines 278-285):**
1. Project ≠ SOW (initiative)
2. Objectives are where work lives
3. Ambiguity bubbles up to owning objective
4. Re-analysis is manual (no auto-trigger)
5. Failure splits: LLM-fix OR user-decision
6. Docs are two-layer (auto + DOC task)
7. ACHIEVED is reversible (re-open with notes)

**What the flow does NOT show:**
- **Findings / triage loop** — findings come from develop + challenger + analysis but where do they go? No node shows "Findings" entity.
- **Decisions** — separate from ambiguities. Resolved decisions drive ADRs but not on the diagram.
- **Cost / budget enforcement** — no gate on the flow.
- **Skills lifecycle** — installed once at project level; no connection to flow.
- **Org-level** events (skill promotion, marketplace, cross-project) — flow is single-project.
- **Multi-user** — no handoff arrow (e.g., who approves objective DONE).
- **Client view / share link** — deliverable produces artifacts that leave Forge for the client; not shown.
- **Review gates** — even at L1 it's "user drives", but flow has no human-approval nodes between stages.

---

## Part 2 — identified workflows

Workflows are sequences of screens with a user goal. I number them W-N.

### W-1 — Greenfield project to first ACHIEVED objective
`Dashboard` → `02v2 KB` (add sources) → `09 Objective detail` (create objective, review AC) → `07 Mode` (pick direct/crafted) → `04 Orchestrate live` → `05v2 Task deliverable` → `09` close objective → `10 Docs`

**Goal:** take a new initiative to the first shipped piece of work.

**Gaps hit:** G-1, G-2, G-6, G-9, G-14, G-17.

### W-2 — Ambiguity resolution cycle
`09 Objective detail` → click `Answer →` on Q-007 → `MISSING ANSWER MODAL` → back to `09` → scrutiny strip shows updated count → `▶ Continue anyway` → re-analysis → updated `09`.

**Goal:** unblock planning by resolving analysis-surfaced Q.

**Gaps hit:** G-9 (entire Answer-flow doesn't exist in mockups).

### W-3 — Discover a hallucinated AC
`09 Objective detail` sees AC-5 marked `INVENTED BY LLM` → opens AI sidebar → `@AC-5 + /run-skill OP-hipaa-auditor` → sidebar proposes 3 AC, flags AC-5 as leak → user clicks `Remove AC-5 + log skill-leak` → destructive-preview modal (**MISSING**) → back to `09` updated.

**Goal:** catch + remediate a skill-leak without leaving page.

**Gaps hit:** G-34 (destructive preview).

### W-4 — Mid-run cost overrun
`04 Orchestrate live` sees budget meter 90% → clicks `⏸ Pause` → run paused → opens `05v2 previous task` → drills into cost-by-phase → decides to `Re-scope KB` → returns to `07 Mode selector` to relaunch with narrower KB.

**Goal:** control spend mid-flight.

**Gaps hit:** No explicit Pause mockup on 04 canvas (though P1.1 fix covers code); no cost-drill UI mockup (G-35).

### W-5 — Re-open an ACHIEVED objective
`10 Docs` rollup shows O-002 ACHIEVED → user realizes gap → goes to `09` for O-002 → `↶ Re-open` (mocked inline on 05v2 but not for objectives) → gap-note form → objective → NOT_DONE, ready for new analysis task.

**Goal:** correct what was shipped without losing history.

**Gaps hit:** G-11 (objective-level re-open form).

### W-6 — Install a skill + verify no conflict
`11 Skills library` → "Cloud architect" shows `⚠ may conflict with SRC-004` → `+ Install anyway (with warning)` → conflict-resolution modal (**MISSING**) → active skills sidebar in `12` updated.

**Goal:** attach new capability knowing the tradeoffs.

**Gaps hit:** G-27.

### W-7 — Client handoff
`10 Docs` → `🔗 Share link for client` → share-link config modal (**MISSING**) → client opens link → read-only docs view (**MISSING** — different from internal `10`?) → client can browse ADRs + API ref but not decisions-in-progress.

**Goal:** hand off deliverable to external stakeholder.

**Gaps hit:** G-23.

### W-8 — Promote to autonomy L3
`12 Project config` autonomy strip → `enable →` on L3 → criteria-check modal (**MISSING**) → shows 3 audit failures → user fixes them → re-tries enable → L3 active.

**Goal:** earn more Forge autonomy.

**Gaps hit:** G-32.

### W-9 — Multi-user collaboration (not represented)
Not in any mockup. Who reviews? Who approves objective DONE? No roles shown, no handoff screen, no notifications.

**Goal:** consultancy with multiple teammates.

**Gaps hit:** **entire missing dimension.**

### W-10 — Cross-project learning (partially in scenario 8)
Admin runs replay batch across projects → no mockup. Scenario 8 of walkthrough describes it but the screen is absent.

**Gaps hit:** **entire missing admin domain.**

---

## Part 3 — does this form a complete process?

**Answer: no, it's a spine with gaps.**

### What's complete:
- The main spine (Project → KB → Objective → Analysis → Planning → Develop → Docs → Achieved) is coherent on `flow.html`.
- The three persistent layers (project context, page context, AI sidebar) are well specified on `16`.
- The skeptical-UX contract is consistently applied — every mockup has a scope-limit / scrutiny-debt component.

### What's missing for completeness:

**Creation forms (everywhere):**
- Create project (Dashboard `+ New project` goes nowhere)
- Create objective (`03v2` and `09` toolbar buttons go nowhere)
- Create task (any of 4 types)
- Add KB source (4 types — all missing modals)
- Add AC / scenario
- Add ambiguity (manual Q)
- Add hook (`12`)
- Add skill / edit skill (`11`)
- Add ADR (`10`)
- Add DOC task from docs page

**Edit/mutate forms:**
- Edit description of any entity
- Edit auto-attach rule of a skill
- Edit hook trigger + skill
- Edit ambiguity answer after it was resolved (re-open a decision)
- Edit objective dependencies (add/remove edges in DAG)

**Answer / resolve flows:**
- **Answer an ambiguity (the whole Q&A form)** — the single biggest gap. Forge's whole value depends on this loop and no mockup shows it.
- Resolve conflict between sources (SRC-005 vs SRC-002)
- Decide on a challenger concern (create task / accept / dismiss)
- Acknowledge scrutiny debt

**Preview flows (destructive-action confirmations):**
- Apply LLM-suggested AC
- Remove AC (log skill-leak)
- Close a task
- Re-open an objective
- Delete a KB source
- Detach a skill
- Apply contract changes

**Navigation deep-ends (results pages):**
- Crafter preview result
- Replay result
- Reverse-trace page
- Cost-drill page
- Task report for ANALYSIS / PLANNING / DOCUMENTATION types (only DEVELOP is mocked)
- Findings triage page (separate from task)

**Multi-user / roles / org:**
- Login / signup screens
- Org admin dashboard
- User roles (owner/editor/viewer/auditor)
- Approval workflows
- Notifications / digest
- Audit assignment (for manual AC)
- Sharing with teammates (not only clients)

**Client-side (external view):**
- Share-link creation modal
- Client read-only view of docs (different from internal `10`)
- Client reverse-trace access

**Admin / cross-project:**
- Org skill marketplace
- Replay batch admin
- Promote skill to org
- Cross-project patterns dashboard

**System states not shown:**
- Project archive state
- Budget exhaustion screen
- Workspace infra error (postgres down mid-run)
- Orphan-run (post-server-restart — Forge now creates these legitimately)

---

## Part 4 — what a pro would design

A complete process needs **creation, resolution, edit, preview, result, admin, client** surfaces for every entity. The 10 current mockups cover roughly **the viewing + navigating layer** of one project's happy path. Missing are the **mutation, handoff, and cross-project layers.**

### Principle 1: pair every list with a create form

For every screen that shows a list (KB sources, objectives, tasks, AC, scenarios, skills, hooks), there MUST be a create-form mockup. Most forms can share a template (Pydantic-style: field → validation → preview → confirm).

### Principle 2: answer-an-ambiguity is the central interaction

Forge's trust contract hinges on ambiguities. This screen MUST be designed at the same depth as `09`. It should show:
- The Q + severity + ref (SRC/Decision/KB passage)
- Claude's recommended answer + reasoning
- 2-3 alternative answers (non-hallucinated variants)
- Custom free-text answer
- "Defer" with mandatory reason
- Impact preview (which AC/Tasks will be affected by this answer)
- After save: banner "Do you want to trigger re-analysis now?"

### Principle 3: destructive actions always preview

Every LLM-proposed mutation and every user mutation that changes > 1 entity needs a preview-before-apply modal showing the diff. Template: left = current, right = proposed, colors = removed/added.

### Principle 4: every task type deserves its own deliverable template

05v2 is DEVELOP-specific. ANALYSIS, PLANNING, and DOCUMENTATION tasks have different outputs (decisions list, DAG, markdown). Each needs an equivalent scrutiny screen.

### Principle 5: client view is not just a subset

A client-facing "share link" view is NOT "internal docs minus the costs". It's a different narrative:
- executive summary (what was decided, why)
- deliverable artifacts (only ACHIEVED work)
- reverse-trace capability (answer "why does my code do X?")
- NO in-progress drafts, NO open ambiguities, NO findings

### Principle 6: org/cross-project is its own canvas

Dashboard `01` hints at cross-project but there's no admin layer. The admin layer is its own 4-5 screens: org users, org skills marketplace, cross-project patterns, replay lab, audit trail.

### Principle 7: fail loudly, recover gracefully

Every failure path needs a screen:
- Budget exhausted
- Workspace infra down
- Claude CLI unavailable
- Orphan run recovered (explain to user)
- Git conflict during commit
- Test runner crashed

---

## Part 5 — mockup changes proposal

### Add (new mockups needed)

1. `02v2-add-source-file.html` — file upload modal w/ description
2. `02v2-add-source-url.html` — URL + auth + ignore globs + schedule
3. `02v2-add-source-folder.html` — folder + includes/excludes + sample
4. `02v2-add-source-note.html` — manual note editor
5. `02v2-source-preview.html` — read chunks of an ingested source
6. `03v2-kanban-view.html` — objectives as Kanban columns (WAITING/ACTIVE/BLOCKED/ACHIEVED)
7. `03v2-timeline-view.html` — objectives on a horizontal timeline with KR progress
8. `03v2-create-objective.html` — form (title, business_context, type?, dependencies)
9. `09-answer-ambiguity.html` — **THE critical missing form**
10. `09-add-ac.html` — AC inline form (text + scenario_type + verification + test_path)
11. `09-add-scenario.html` — scenario inline form (type: edge_case/failure_mode/security + description)
12. `09-reopen-objective.html` — objective-level re-open with gap note
13. `09-edit-challenger-checks.html` — CRUD for per-objective challenger rules
14. `07-crafter-preview.html` — what the crafter produced; approve or reject
15. `05v2-analysis-deliverable.html` — task report for ANALYSIS type
16. `05v2-planning-deliverable.html` — task report for PLANNING type
17. `05v2-documentation-deliverable.html` — task report for DOC type
18. `05v2-close-task.html` — close-modal with reason + signature
19. `05v2-create-followup-task.html` — spawn follow-up from a concern
20. `05v2-scenario-generate.html` — "Generate test & run now" live progress
21. `05v2-assign-auditor.html` — pick a user for manual AC
22. `10-share-link.html` — share-link creation (expiry, scope, password, audience)
23. `10-client-view.html` — read-only client-facing variant
24. `10-edit-doc-section.html` — inline markdown editor for DOC sections
25. `10-regenerate-section.html` — regen progress + cost preview
26. `10-export-formats.html` — export modal (MD / PDF / HTML bundle)
27. `10-add-adr.html` — new ADR form
28. `11-skill-detail.html` — prompt text, applies_to_phases, tags, metrics, versions
29. `11-skill-edit.html` — create / edit skill
30. `11-skill-install.html` — install flow with conflict check
31. `11-skill-rule-builder.html` — auto-attach rule visual builder
32. `11-org-marketplace.html` — org-level skill catalog
33. `12-skills-tab.html` — skills selection tab (listed but not mocked)
34. `12-hooks-tab.html` — hooks CRUD tab
35. `12-phase-defaults-tab.html` — phase-default skill editor
36. `12-budget-tab.html` — budget/limits config
37. `12-integrations-tab.html` — external integrations (SharePoint/Jira/Slack)
38. `12-add-hook.html` — hook editor (trigger + skill + condition)
39. `12-autonomy-enable-L3.html` — L3 promotion criteria + preview
40. `12-contract-diff.html` — contract revision diff viewer
41. `16-preview-apply-modal.html` — destructive-action preview (generic)
42. `16-cost-drill.html` — cost forensic per task
43. `16-reverse-trace.html` — provenance chain for an entity
44. `16-replay.html` — replay result for a task
45. `16-history.html` — sidebar conversation history
46. `17-dashboard-org.html` — org admin dashboard
47. `17-org-users.html` — user management
48. `17-replay-batch.html` — admin replay lab
49. `18-budget-exhausted.html` — budget-cap hit error screen
50. `18-orphan-recovered.html` — orphan-run recovery message
51. `19-login.html` / `19-signup.html` — auth screens
52. `19-org-setup.html` — first-time org creation

### Modify (existing mockups need fixes)

- **01-dashboard.html (v1 → v2):** add org-level "decisions block project X" banner; add ⌘K global search overlay; promote running-task surface per project.
- **02v2:** link ambiguity badge on SRC-005 to an actual decision-detail destination.
- **03v2:** show decision-blocking modal on load when `open_decisions > 0` (not just a banner).
- **09:** rework description area to inline SRC pills (text-level not end-of-paragraph) and allow per-phrase attribution edit.
- **05v2:** add per-section toggle "Challenger refused" box backed by an actual `LLMCall.delivery_parsed.refused_to_verify` field (needs backend support).
- **10:** add Activity tab cross-link (stub exists in tab bar but no mockup).
- **11:** surface Success-lift stats visibly (currently a column name only).
- **12:** build the 5 missing tabs.
- **16:** add "🧩 add skill" inline picker + preview modal for destructive actions.

### Remove / consolidate

- v1 mockups (`01`, `02`, `03`, `04`, `05`) — kept for comparison, but explicitly mark "superseded" and remove from main canvas grid (already mostly done via opacity-70).

---

## Part 6 — agent prompt (hand-off)

Below is a single self-contained prompt suitable to hand to another agent. Paste it as the agent's input verbatim — it includes all context + task breakdown + format requirements.

```
You are redesigning the Forge UX mockup set to produce a COMPLETE process. The
current set (in forge_output/_global/mockups/) has 10 Revised mockups (02v2,
03v2, 05v2, 07, 09, 10, 11, 12, 16, flow.html + walkthrough.md). These cover
the viewing + navigating layer of a single project but are missing creation
forms, answer flows, destructive-action previews, task-report variants for
non-develop types, admin / cross-project / client-facing surfaces, and failure
states.

YOUR DELIVERABLE
================

For EACH of the 52 items listed in "NEW MOCKUPS TO ADD" below, produce a
complete, self-contained HTML mockup file using the SAME Tailwind + annotations
styling as the existing set (see styles.css and any existing Revised mockup as
template). Each mockup file must include:

1. <nav> header with breadcrumbs showing exact path to get here (real hrefs
   to the other mockups, including the ones you are creating).
2. Main content — the screen itself, populated with REALISTIC example data
   that flows with the acme-erp-migration scenario used throughout the set.
   (Don't reuse generic "Your data here" placeholders; use concrete names like
   SRC-001, O-002, DT-009, user hergati@gmail.com, etc.)
3. Annotations panel (right side, amber border) explaining WHAT each section
   does, WHERE the data comes from (DB table / service / user input), WHO can
   edit it, WHY it is on this page vs elsewhere, and what HAPPENS when the
   primary button is clicked (name the destination mockup).
4. Skeptical-UX contract: every screen must have at least one visible element
   that surfaces "what wasn't done / wasn't checked / was assumed". No
   "all good" / "trustworthy" / "approve" framing without a counterweight.
5. AI sidebar context hint — a one-line callout "AI sidebar on this page
   knows: [page.id, page.entity, visible_data, suggested actions]" so the
   LLM-layer design invariant is never forgotten.

In addition to the HTML files:
- Update index.html to include links to every new mockup.
- Update flow.html to add any new process nodes that these mockups represent
  (e.g., "answer ambiguity" becomes a node on the ambiguity loop).
- Produce a FLOWS.md file listing every workflow these mockups support, in
  the W-1..W-N format. Each workflow = ordered list of mockup files + user goal.
- Produce a PROCESS_COMPLETENESS.md file identifying any remaining gaps AFTER
  your additions (there will be some; be honest).

NEW MOCKUPS TO ADD
==================

(52 items — listed with purpose + required elements; see original deep-analysis
doc FORGE_MOCKUP_DEEP_ANALYSIS.md Part 5 for the full list. In brief:)

Group A — KB source creation + preview (5):
  02v2-add-source-file, url, folder, note, source-preview.

Group B — Objectives portfolio variants + creation + answer (6):
  03v2-kanban, 03v2-timeline, 03v2-create-objective, 09-answer-ambiguity
  (CRITICAL — design at depth of 09), 09-add-ac, 09-add-scenario.

Group C — Objective-level actions (3):
  09-reopen-objective, 09-edit-challenger-checks, 09-edit-dependencies.

Group D — Mode + task creation (2):
  07-crafter-preview, 07-new-task-generic (merge with 07 as a tab?).

Group E — Task reports for 3 non-develop types (3):
  05v2-analysis-deliverable, 05v2-planning-deliverable, 05v2-documentation-deliverable.

Group F — Task-level actions (4):
  05v2-close-task, 05v2-create-followup-task, 05v2-scenario-generate,
  05v2-assign-auditor.

Group G — Docs + sharing (5):
  10-share-link, 10-client-view, 10-edit-doc-section,
  10-regenerate-section, 10-add-adr.

Group H — Skills management (5):
  11-skill-detail, 11-skill-edit, 11-skill-install (conflict check),
  11-skill-rule-builder, 11-org-marketplace.

Group I — Config tabs (6):
  12-skills-tab, 12-hooks-tab, 12-phase-defaults-tab, 12-budget-tab,
  12-integrations-tab, 12-add-hook.

Group J — Config meta (2):
  12-autonomy-enable-L3, 12-contract-diff.

Group K — AI sidebar deep (5):
  16-preview-apply-modal (generic destructive preview),
  16-cost-drill, 16-reverse-trace, 16-replay, 16-history.

Group L — Org/admin (3):
  17-dashboard-org, 17-org-users, 17-replay-batch.

Group M — Failure / recovery (2):
  18-budget-exhausted, 18-orphan-recovered.

Group N — Auth / onboarding (2):
  19-login-signup, 19-org-setup.

FOR EACH MOCKUP, answer in annotation:
  - Data sources (exact: table + column OR service call OR user input).
  - Creation path (which code writes this data).
  - Edit location (this page or another — name it).
  - Why it belongs here, not elsewhere (justify placement).
  - Primary action destination (exact file path of next mockup).
  - Skeptical-UX counterweight element present.

MODIFICATIONS TO EXISTING MOCKUPS
==================================

01-dashboard.html (Revised to v2):
  - Org-level "N decisions block project X from planning" banner at the top.
  - Global ⌘K search overlay.
  - Per-project "currently running" strip (if any run active).

02v2-project-kb.html:
  - Link SRC-005 CONFLICTS badge to 02v2-add-source-url.html#resolve or to a
    dedicated decision-detail mockup if you create one.
  - Surface `last_read_at` as a "staleness" pill when > 30d.

03v2-objectives-dag.html:
  - Add decision-blocking MODAL (not just banner) that fires on page load
    when open_decisions > 0 AND user has not dismissed it.
  - Wire `+ Objective` and `+ Analysis task` toolbar buttons to their mocks.

09-objective-detail.html:
  - Make description text inline-attributable — every sentence can have a
    ✱ pill. Edit-mode allows dragging source pills into text.
  - Wire every "Answer →" to 09-answer-ambiguity.html.
  - Wire "+ Add scenario / + Add manually" to their mocks.

05v2-task-deliverable.html:
  - Add "Challenger REFUSED" section visually separated from verified claims.
  - Wire "→ Create follow-up task" to 05v2-create-followup-task.html.
  - Wire "Assign to auditor" to 05v2-assign-auditor.html.

10-post-exec-docs.html:
  - Wire "🔗 Share link for client" to 10-share-link.html.
  - Wire "+ Add DOCUMENTATION task" to a creation form (reuse 07-new-task or
    custom 10-add-doc-task).
  - Wire "Edit" / "Regenerate" per section.

11-skills-library.html:
  - Surface Success-lift as a visible column with delta-pp values.
  - Wire "+ Create new skill" and "Clone & customize".

12-project-config.html:
  - Build out the 5 missing tabs linked above.

16-ai-sidebar.html:
  - Add preview-modal for destructive LLM-suggested actions.
  - Wire slash-command results to their own mocks (replay, cost-drill,
    reverse-trace, history).

WORKFLOW DOCUMENTATION
======================

Write FLOWS.md with at least 20 workflows covering:
- W-1..W-10 from the original analysis
- W-11..W-20 covering your new additions (answer ambiguity, share-link to client,
  L3 promotion, skill install with conflict, close-task with reason, etc.)

Each workflow has:
- Name + user persona + goal
- Ordered list of mockup files
- Data produced (what rows get created / modified)
- Failure modes (what can go wrong at each step)

COMPLETENESS DOC
================

Write PROCESS_COMPLETENESS.md identifying:
- What the process now covers end-to-end (user journey complete? test)
- What still doesn't have a mockup (there will be some — be explicit)
- What DATA MODEL changes are required to back these mockups (e.g., TestScenario
  entity, Objective.type, Task.user_added AC flag, etc.) — list them
- What SERVICES are implied but don't exist (recommendation engine, conflict
  detector, etc.)

SKEPTICAL UX CONTRACT — NON-NEGOTIABLE
=======================================

If ANY mockup frames outcome as "approve to ship" or "looks good to close"
without a counterweight panel of scrutiny debt / unchecked scope / dismissed
findings — that is a contract violation and must be fixed.

Primary action on every scrutiny screen is never "Approve"; it is one of:
- "Ask challenger to verify X"
- "Add scenario I realized is missing"
- "Re-open with gap note"
- "Log skill-leak incident"

Only when all scrutiny counters are zero should "Close" be primary — and even
then, require a reason field.

OUTPUT ORGANIZATION
===================

forge_output/_global/mockups/
├─ 02v2-*.html                 (existing + new KB ones)
├─ 03v2-*.html                 (existing + new views)
├─ 05v2-*.html                 (existing + new task-report variants)
├─ 07-*.html                   (existing + crafter-preview)
├─ 09-*.html                   (existing + answer-form, add-ac, add-scenario, ...)
├─ 10-*.html                   (existing + share-link, client-view, ...)
├─ 11-*.html                   (existing + skill CRUD)
├─ 12-*.html                   (existing + 5 missing tabs + modals)
├─ 16-*.html                   (existing + cost-drill, reverse-trace, ...)
├─ 17-*.html                   (new: org/admin)
├─ 18-*.html                   (new: failure states)
├─ 19-*.html                   (new: auth)
├─ flow.html                   (updated)
├─ index.html                  (updated index with all new tiles)
├─ FLOWS.md                    (new — documented workflows)
└─ PROCESS_COMPLETENESS.md     (new — honest gap list + DB/services needed)

You do not need to write backend code. Your deliverable is the mockup layer +
the two .md files documenting the process. This output feeds into the next
engineering agent that will build the missing backend services + DB columns
called out in PROCESS_COMPLETENESS.md.

DURATION / SCOPE NOTE
=====================

This is a large deliverable. Complete it in passes:
  Pass 1 (foundation): 09-answer-ambiguity (critical), 11-skill-edit, 12 tabs.
  Pass 2 (creation): all the create-X / add-X mockups.
  Pass 3 (variants): non-develop task reports, views (Kanban/Timeline).
  Pass 4 (admin + failure): org, client, failure states.
  Pass 5 (docs): FLOWS.md + PROCESS_COMPLETENESS.md.

After each pass, update index.html to surface the new tiles so intermediate
reviews are possible.

Begin with Pass 1 — foundation.
```

---

## Appendix A — gaps indexed

Every gap identified has an ID (G-1 through G-36). Quick lookup:

- G-1: task-creation modal missing
- G-2: source-preview modal missing
- G-3: ambiguity-detail modal missing (SRC-level)
- G-4: project-settings page missing
- G-5: Kanban/Timeline objective views missing
- G-6: create-objective modal missing
- G-7: ambiguity-answer page/modal missing (objective-level)
- G-8: Objective.type DB column missing
- G-9: ambiguity answer form missing (the big one)
- G-10: add-AC / add-scenario inline form missing
- G-11: objective-level re-open form missing
- G-12: LLM-expand-description interaction ambiguous
- G-13: TestScenario entity missing
- G-14: challenger-checks CRUD missing
- G-15: crafter-preview result missing
- G-16: recommendation engine data source not defined
- G-17: close-task modal with reason missing
- G-18: create-follow-up-task modal missing
- G-19: scenario-generate progress missing
- G-20: assign-auditor flow missing
- G-21: challenger "refused to verify" backend support missing
- G-22: DOCUMENTATION task deliverable missing
- G-23: share-link creation modal missing
- G-24: doc-section-edit inline editor missing
- G-25: add-DOC-task modal missing
- G-26: skill-editor mockup missing
- G-27: skill-install conflict-check modal missing
- G-28: org-marketplace missing
- G-29: skill-prompt view-source missing
- G-30: config tabs (5 of 6) missing
- G-31: hook editor missing
- G-32: autonomy-promotion modal missing
- G-33: contract-diff viewer missing
- G-34: destructive-action preview modal missing
- G-35: replay / cost-drill / reverse-trace pages missing
- G-36: conversation history list missing

---

## Appendix B — data-model changes implied by mockups

| DB change | Needed because |
|---|---|
| `Objective.type` CHECK (analysis/planning/develop/documentation/draft) | `03v2` objectives colored by type |
| `Objective.kb_focus_ids` ARRAY — ALREADY ADDED | `09` KB panel checkboxes |
| `TestScenario` new table (objective_id, kind, description, created_by) | `09` non-happy-path scenarios |
| `AcceptanceCriterion.user_added BOOL` + `last_executed_at TIMESTAMP` — LAST_EXECUTED_AT EXISTS | `05v2` user-added amber rows |
| `LLMCall.delivery_parsed.refused_to_verify` (persist already) | Challenger refused list |
| `Skill.recommended_timeout_sec` — ALREADY ADDED | `11` + `12` hook timeout |
| `Project.archived_at` | project archive state (mentioned in `02v2` header) |
| `Decision.claude_recommendation_text` + `Decision.alternatives JSONB` | answer-ambiguity modal shows pre-selected recommendation |
| `ShareLink.expires_at`, `ShareLink.scope`, `ShareLink.password_hash` | share-link modal |
| `User.role` + `Membership.can_audit` | auditor assignment |
| `ObjectiveReopen.reason` — EXISTS (`ObjectiveReopen` model) | re-open with gap notes |

---

**End of analysis.** Total: ~8,200 words. Hand-off prompt in Part 6 is self-contained and ready to paste into another agent.

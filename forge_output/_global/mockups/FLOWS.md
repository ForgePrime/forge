# FLOWS — Pass 1 mockups

For each of the 9 new Pass-1 mockups: where the user comes from, what they're trying to accomplish, where they go next, what DB rows get touched, and what can go wrong. Keep this file in sync when adding new mockups.

Scenario constants used throughout: project `acme-erp-migration`, user `hergati@gmail.com`, objectives `O-001..O-007`, sources `SRC-001..SRC-005` (SRC-005 excluded as conflicting), tasks `AT-001..AT-006` analysis · `PT-001..PT-003` planning · `DT-001..DT-010` develop · `DOC-001` docs.

---

## 1. `09-answer-ambiguity.html` — answer Q-007

**Entry**
- `09-objective-detail.html` → "Answer →" button on any open Q row
- `16-ai-sidebar.html` → suggestion chip "Answer Q-007"
- Direct deep link from notification email / digest
- `02v2-project-kb.html` → ambiguity badge on a SRC card

**Primary goal**
User resolves a HIGH/MEDIUM ambiguity flagged by an analysis task, with full visibility into the source conflict, alternatives extracted from sources (not invented), per-option downstream impact, and the gaps Claude did not check.

**Exit**
- Save + re-analyze → `09-objective-detail.html#ac-2` with re-analysis pending pill on AT-006
- Save only → `09-objective-detail.html` (no auto re-run, user can trigger later)
- Cancel → previous page (browser back / referrer)
- Defer → stays on `09-objective-detail.html`, new task AT-007 created

**Data produced/modified**
- `decision.user_answer` set (option label or free-text)
- `decision.user_answer_source` = "claude_recommended" | "alternative_b" | "alternative_c" | "custom" | "deferred"
- `decision.answered_at`, `decision.answered_by` populated
- `decision.status` → CLOSED (or DEFERRED)
- `ac.status` for AC-2/AC-3 → recomputed (UNBLOCKED if all dependencies resolved)
- New `task` row AT-006 (re-analyze) flipped from PENDING to QUEUED
- If deferred: new `task` AT-007 type=analysis, instruction "re-ask Q-007 with reason: {reason}"
- `audit_log` entry: who answered what, when, with what reasoning chain

**Failure modes**
- Free-text answer contradicts SRC-004 hard constraints → server returns 422 with conflict list, modal shown before commit
- Defer reason &lt; 50 chars → 422 inline error
- Re-analysis spawned but task fails (LLM timeout) → AT-006 marked FAILED with retry option; decision stays CLOSED (the answer is recorded, only the downstream analysis broke)
- Concurrent edit: another user answered Q-007 between page load and submit → 409, show diff, force user to re-pick
- LLM cost exceeds project cap mid-re-analysis → re-analysis halted, decision stays CLOSED

---

## 2. `09-add-scenario.html` — add non-happy-path scenario

**Entry**
- `09-objective-detail.html` → "+ Add scenario" in the Test scenarios card
- `05v2-task-deliverable.html` → "+ Add scenario I realized is missing" button
- AI sidebar `/generate-scenarios` slash command → modal lands here pre-filled

**Primary goal**
User adds a single edge case / failure mode / security / regression scenario to an objective so it flows into every develop task's challenger claims and AC verification coverage.

**Exit**
- Add scenario → `09-objective-detail.html#scenarios` with new scenario highlighted 3s
- Save as draft → `09-objective-detail.html` (scenario in DRAFT state, not surfaced to challenger)
- Cancel → `09-objective-detail.html`

**Data produced/modified**
- New `scenario` row: kind, description, expected_behavior, rationale, status (ACTIVE | DRAFT)
- `scenario.linked_ac_ids[]` updated for each checked AC
- `ac.verification_coverage[]` for linked ACs gets `{scenario_id, kind}` appended
- `audit_log` entry: scenario added, who, link to objective

**Failure modes**
- Description &lt; 20 chars → 422 inline
- All 4 kind options unchecked → 422 (kind required)
- LLM-suggest 3 button used but cost cap exceeded → suggestion endpoint returns 402, modal pops "increase cap or pick kind manually"
- Linked AC removed by another user between mount and submit → scenario saved without that link, warning flash on redirect

---

## 3. `09-add-ac.html` — add or refine an acceptance criterion

**Entry**
- `09-objective-detail.html` → "+ Add manually" in the AC card
- `09-objective-detail.html` → "🪄 Regenerate from sources" (loads form pre-filled)
- `05v2-task-deliverable.html` → "+ Add AC / scenario" → AC tab
- AI sidebar suggestion "Add AC for X" → modal here

**Primary goal**
User adds a verifiable acceptance criterion with explicit source attribution. INVENTED ACs allowed but flagged as scrutiny debt.

**Exit**
- Save AC → `09-objective-detail.html#ac-6` (new AC highlighted)
- Save as draft → same redirect, AC in DRAFT state (not yet a gate for tasks)
- Cancel → `09-objective-detail.html`

**Data produced/modified**
- New `ac` row: text, scenario_type, verification_method, test_path/command (conditional), source_ref (FK or 'INVENTED'), source_passage, status (ACTIVE|DRAFT), objective_id
- If source_ref='INVENTED' → `ac.is_unsourced=true` → triggers scrutiny_debt counter on parent objective
- If verification=test and test_path doesn't exist → `task` flagged (next develop task gets test scaffold instruction)
- If verification=manual → `manual_verification_task` row pre-created
- `audit_log` entry

**Failure modes**
- Text &lt; 20 chars → 422
- Source picker empty AND not "INVENTED" → 422
- Duplicate AC (fuzzy match against existing on same objective) → 422 with "did you mean to refine AC-X?"
- Test path malformed (not pytest::test) → warning, not blocking — Forge will scaffold
- LLM regenerate exceeded cost cap → button greys, modal explains

---

## 4. `07-new-task.html` — wizard step 1 (task details)

**Entry**
- `09-objective-detail.html` → any of 4 "+ task" buttons (type pre-selected from button)
- `03v2-objectives-dag.html` → context menu "Add task to O-002"
- AI sidebar suggestion "Create develop task for X"
- `04-orchestrate-live.html` → "+ task" inline

**Primary goal**
User defines a new task on an objective with title, instruction, dependencies, AC inheritance choice, and KB-scope override. Task type is locked from the entry button.

**Exit**
- Continue → `07-mode-selector.html?task=DT-NNN` (DRAFT task created first)
- Save as draft + close → `09-objective-detail.html` (DRAFT visible in task list w/ resume button)
- Cancel → `09-objective-detail.html`, draft discarded (localStorage cleared)

**Data produced/modified**
- New `task` row in DRAFT status: type, title, instruction, depends_on[], objective_id, kb_scope[]
- `task.kb_scope_overrides[]` stores deviations from objective's default
- If task-specific AC added: new `ac` rows linked to task_id (not objective_id)
- `audit_log` entry on Continue (when task moves to DRAFT)

**Failure modes**
- Title &gt; 120 chars → 422
- Instruction empty → 422
- Dependency cycle (this task depends on something that depends on it) → 422 with cycle path
- KB-scope unchecks SRC-004 (hard-constraint source) → continue to mode selector but warning banner travels with the wizard
- localStorage quota exceeded (long instruction) → fallback to server-side draft save on every keystroke (with debounce)

---

## 5. `07-crafter-preview.html` — inspect crafted prompt before run

**Entry**
- `07-mode-selector.html` → "Preview crafted prompt →" button (when crafted mode selected)
- `04-orchestrate-live.html` → "view crafted prompt" link on a running crafted task
- Direct link from cost-forensic drilldown

**Primary goal**
Before paying ~$0.42 on the executor run, user inspects what the crafter produced — what KB chunks were read, what code files inspected, what skills consulted, what the crafted prompt looks like, and what the crafter explicitly did NOT do.

**Exit**
- Run with this prompt → `04-orchestrate-live.html?task=DT-010` (executor starts)
- Re-craft with different KB scope → stays on page, crafter re-runs (~$0.08 again), trace updates
- Edit manually → switches prompt textarea to editable mode
- Back to mode selector → `07-mode-selector.html`

**Data produced/modified**
- On Run: `task.status` → QUEUED, `task.executor_started_at` set, `llm_call` row created for executor
- On Re-craft: previous `task.crafted_prompt_text` archived to `task.crafted_history[]`, new `llm_call` row for crafter, new prompt stored
- On manual edit: `task.crafted_prompt_manual_override` set; flag prevents prompt-cache reuse on next crafted task w/ same params
- `audit_log` entry on each transition

**Failure modes**
- Crafter run timed out → preview shows partial trace + "re-craft" cta enabled, "run with this prompt" disabled
- Cost cap exceeded by crafter run → preview shows what it managed before halting, user sees how to raise cap
- KB source removed between crafter and preview render → trace shows "[deleted]" placeholder
- Edit manually then run: prompt cache miss → cost ~30% higher (warning banner)

---

## 6. `12-skills-tab.html` — project config: skills

**Entry**
- `12-project-config.html` → tab nav "Skills"
- `11-skills-library.html` → "View this project's skill set" link
- AI sidebar suggestion "rebalance skills" → lands here w/ rebalance modal open

**Primary goal**
User audits which skills are attached to this project, their cost impact, and detaches/edits them. Distinguished from hooks (when skills fire after a stage) and phase defaults (which skills run if nothing overrides).

**Exit**
- Edit on row → `11-skill-edit.html?id=X&project=acme-erp-migration`
- Detach on row → confirmation modal → POST detach → stays on page w/ flash + counter updated
- + Add from library → `11-skills-library.html?mode=install&project=acme-erp-migration`
- Rebalance → AI sidebar opens w/ rebalance suggestions
- Tab switch → `12-project-config.html` / `12-hooks-tab.html` / `12-phase-defaults-tab.html`

**Data produced/modified**
- On Detach: `project_skill` row deleted (or soft-deleted with `detached_at` for audit)
- Past tasks unaffected (their `task.skills_used[]` snapshot preserved)
- Cost-impact recomputed on next page load (no row update — derived field)
- `audit_log` entry per detach

**Failure modes**
- Detach a skill referenced by an active hook → confirmation modal warns "this will also disable hook X"
- Detach a skill mid-run task → task continues with the skill (snapshotted at start), but warning shown
- Filter dropdowns out-of-sync after detach → URL state preserved on redirect

---

## 7. `12-hooks-tab.html` — project config: post-stage hooks

**Entry**
- `12-project-config.html` → tab nav "Post-stage hooks"
- `12-skills-tab.html` → "View hook" link on a row that's hook-attached
- Audit log → "view hook that fired here"

**Primary goal**
Manage which skills fire automatically after each stage (ANALYSIS / PLANNING / DEVELOP / DOC) and what they do on failure. View firing history + cost.

**Exit**
- Edit on hook → `12-add-hook.html?id={hook_id}` (same form, edit mode)
- History on hook → `/hook/{id}/firings` list page (not in Pass 1)
- Remove → confirmation → POST delete → stays on page
- + Add hook → `12-add-hook.html` (new mode)
- Toggle Enabled / Block on failure / Run on replays → instant POST + flash

**Data produced/modified**
- Inline toggles → PATCH `hook` row
- Remove → DELETE hook row (soft delete preserved for firing history)
- Add → POST creates new hook row, see `12-add-hook.html` flow
- `audit_log` entry per change

**Failure modes**
- Disable a hook mid-stage (after task completes but before hook fires) → hook still fires (snapshotted), warning on re-render
- Remove hook with active firings → blocked w/ "wait for hook to finish" message
- Condition expression on existing hook becomes invalid after schema change → row marked broken in red, hook auto-disabled

---

## 8. `12-phase-defaults-tab.html` — project config: phase defaults

**Entry**
- `12-project-config.html` → tab nav "Phase defaults"
- `11-skills-library.html` → "edit for this project" link in phase-default cards
- Onboarding wizard step "configure your phase defaults"

**Primary goal**
For each of 4 phases, set the skills that run if no task-level config overrides. Distinguishes org-default from project-level customization.

**Exit**
- + Add skill to X defaults → modal picker → POST → stays on page
- × on a skill → POST remove → stays on page
- Reset to org defaults → confirmation modal → POST reset → stays on page
- Save defaults → POST bulk → stays on page
- Tab switch → siblings

**Data produced/modified**
- `project_phase_default` table: rows {project_id, phase, skill_id, source: 'org' | 'project'}
- + adds row w/ source=project
- × on project-source row deletes it (org-source rows can be hidden but not deleted)
- Reset deletes all source=project rows for the phase
- `audit_log` entry on save

**Failure modes**
- Add skill that's not installed in project → 422 "install first via library"
- Remove an org-default → blocked (only override allowed, not delete)
- Concurrent edit: another user changed defaults → 409, show diff modal

---

## 9a. `12-add-hook.html` — add post-stage hook

**Entry**
- `12-hooks-tab.html` → "+ Add hook" button
- `12-skills-tab.html` → "create hook with this skill" inline action (URL pre-fills skill)
- AI sidebar suggestion "this should be a hook"

**Primary goal**
Create a new post-stage hook with stage, skill, condition, failure behavior, and replay setting — with a visible cost projection.

**Exit**
- Create hook (enabled) → `12-hooks-tab.html` w/ flash + new row
- Save as disabled → same redirect, hook row created but `enabled=false`
- Cancel → `12-hooks-tab.html`

**Data produced/modified**
- New `hook` row: stage, skill_id, condition_expression, on_failure, run_on_replays, enabled, severity (default 'normal'), project_id
- `audit_log` entry

**Failure modes**
- Stage not picked → 422
- Skill not picked → 422
- Condition expression syntactically invalid (parser fails) → 422 with line/col error
- Cost projection exceeds remaining budget → soft warning, not blocking, but visible red badge on Create
- Skill not in any of stage's compatible phases → 422 "skill X doesn't support after-{stage}"

---

## 9b. `11-skill-edit.html` — edit a skill

**Entry**
- `11-skills-library.html` → click on skill card "Edit"
- `12-skills-tab.html` → "Edit" link on a skill row
- AI sidebar deep link from drilldown
- "+ Create new skill" → same form in CREATE mode (URL: no id)

**Primary goal**
Edit (or create) a skill: basics, prompt template, applies-to-phases, tags, auto-attach rule (visual builder + JSON), cost impact estimate. Live conflict-check shows how rule changes affect existing projects.

**Exit**
- Save + publish → `11-skills-library.html#SK-{id}` (new version live)
- Save as draft → same redirect, draft version visible
- Cancel → `11-skills-library.html`

**Data produced/modified**
- New `skill_version` row (immutable per version) capturing all fields
- `skill.current_version_id` updated (publish only)
- `skill.draft_version_id` updated (save as draft)
- Auto-attach rule change triggers re-evaluation cache invalidation across projects using the skill
- `audit_log` entry

**Failure modes**
- Ext ID change while skill is referenced → 422 "remove references first"
- Auto-attach rule schema invalid → 422
- Prompt template references undefined variable → 422 "{{foo}} is not in allowed-vars list"
- Save during conflict-check still loading → button disabled until check completes (prevents accidental publish without seeing impact)
- Publish from draft creates new version even if no diff (intentional — supports "force re-publish")

---

## 9c. `16-preview-apply-modal.html` — generic destructive preview

**Entry (any of)**
- AI sidebar suggestion w/ destructive action button → modal pops in-context
- "Detach skill" confirmation → modal
- "Re-open task" with notes → modal
- "Promote autonomy L2→L3" → modal
- "Bulk reject AC suggestions" → modal
- Any user-initiated mutation tagged as destructive

**Primary goal**
Before applying a state-mutating action, user sees: source (who/what proposed), current → proposed diff, scope of change (entities affected), explicit list of what the action does NOT do, and reversibility info.

**Exit**
- Apply → executes mutation → modal closes → flash on parent page → audit log entry visible
- Save as draft → mutation queued as draft, NOT applied; visible on user's draft list and on the entity itself
- Cancel → modal closes, no state change

**Data produced/modified (varies by action)**
- For "Remove AC + log incident": `ac` row deleted (or `status=ARCHIVED`), new `lessons_learned` row, `objective.scrutiny_debt_count` decrement
- For "Detach skill": `project_skill` row removed, dependent hooks possibly disabled
- For "Re-open task": `task.status` → NOT_DONE, history snapshot retained, optional new sub-task created
- Always: `audit_log` row, `action_record` row (so undo can locate it within the 24h window)

**Failure modes**
- Apply fails mid-tx (e.g., FK conflict because another user already deleted referenced row) → entire action rolled back, modal stays open with error
- Idempotency key collision (user double-clicks) → second click is a no-op, returns same audit_log id
- Action's preview goes stale (visible state changed since modal opened) → re-render with fresh diff and a "state changed since you opened this" banner
- Reversibility window expired (action applied 25h ago) → undo button hidden, "irreversible" badge shown in audit log

---

---

# FLOWS — Pass 2 mockups (creation forms + object-level mutations)

13 new mockups across 3 groups: KB source intake (5), objective creation + mutation (4), task-level actions (4). Cross-link Pass 1 flows above.

---

## W-11. `02v2-add-source-file.html` — file upload to KB

**Entry**
- `02v2-project-kb.html` → "+ Add file" button on KB header
- `02v2-source-preview.html` → "Add another file" inline link
- AI sidebar suggestion "ingest this PDF"

**Primary goal**
User uploads a single document, attaches description (≥30 chars), focus hint, scopes; sees parse preview + overlap detection vs existing SRC-NNN before queuing for analysis reuse.

**Exit**
- Add + queue → `02v2-project-kb.html?flash=SRC-006-added` w/ ambiguity raised on affected objectives
- Add only → same, no analysis re-queue
- Cancel → discard upload_token, back to KB

**Data produced/modified**
- New `source` row: type=file, description, focus_hint, scopes[], extracted_text_preview
- `source_chunks` rows generated post-commit (~24 chunks for 9k tokens)
- `decision` row(s) auto-opened if overlap-check found contradiction (e.g., Q-007 spawn from SRC-001 conflict)
- `task` row queued for analysis re-run on each affected objective if "queue for analysis" checked
- `audit_log` entry

**Failure modes**
- File > 50 MB → 422 at upload
- Parse failure (corrupt PDF) → 422 inline w/ "try a different format"
- Description < 30 chars → 422
- Embedding cost would exceed project budget → soft warning, blocks "Add + queue"
- PII auto-scan disabled by default — no failure mode here

---

## W-12. `02v2-add-source-url.html` — URL + auth + crawl schedule

**Entry**
- `02v2-project-kb.html` → "+ Add URL" button
- `02v2-source-preview.html` → "Add similar URL" link
- AI sidebar "ingest this SharePoint folder"

**Primary goal**
User registers a URL source with auth (none/basic/token/SharePoint OAuth), crawl scope (single/recursive/same-domain) + path globs, schedule; sees test-connect, dry-run preview of first 3 URLs that would be indexed, robots.txt indicator.

**Exit**
- Add + crawl now → OAuth redirect (if SharePoint) → first crawl runs → `02v2-project-kb.html?flash=SRC-007-crawling`
- Save as draft → row created, no OAuth, no crawl
- Cancel → discard

**Data produced/modified**
- New `source` row: type=url, auth_kind, credentials (encrypted), crawl.{kind, max_depth, include[], exclude[]}, recrawl_cadence
- On first crawl: `source_chunks` rows for each URL fetched
- `audit_log` entry per crawl + per OAuth grant

**Failure modes**
- Test-connect timeout / 4xx → inline error
- OAuth redirect fails or user denies → no source row created
- robots.txt forbids → soft warning, can override w/ acknowledgment checkbox
- Schedule cron parse error (custom expressions in Pass 4) → 422
- First crawl exceeds budget → halts, source stays REGISTERED-but-empty

---

## W-13. `02v2-add-source-folder.html` — local / mounted folder

**Entry**
- `02v2-project-kb.html` → "+ Add folder" button
- Onboarding wizard "register code repo"
- AI sidebar "index legacy codebase folder"

**Primary goal**
User registers a folder path with include/exclude globs, recursive flag, gitignore respect, and re-scan schedule. Sees sample scan preview + sensitive-file warning.

**Exit**
- Add + first scan → first scan runs → `02v2-project-kb.html?flash=SRC-008-scanning`
- Add without scan → row created, no scan
- Cancel → discard

**Data produced/modified**
- New `source` row: type=folder, path, recursive, follow_symlinks, respect_gitignore, include_patterns[], exclude_patterns[], rescan_cadence
- On first scan: `source_chunks` rows per matched file
- `audit_log` entry

**Failure modes**
- Path outside `project.folder_sandbox_root` → 422
- No read permission → test-access fails inline
- 0 matched files → soft warning ("did your globs miss?")
- Symlink loop detected mid-scan → scan halts, partial chunks committed
- Includes file matching `**/.env*` and excludes don't cover it → soft warning, allow override w/ ack

---

## W-14. `02v2-add-source-note.html` — manual note editor

**Entry**
- `02v2-project-kb.html` → "+ Add note" button
- `09-objective-detail.html` → "+ Add context note" inline action
- `09-answer-ambiguity.html` → "Save reasoning as note" suggestion

**Primary goal**
User writes a manual note (markdown) with title, category, "describes" intent, and optional links to existing decisions/objectives. No external source — purely user content.

**Exit**
- Save note → `02v2-project-kb.html?flash=SRC-009-saved`
- Save as draft → same, status=DRAFT (not visible to analysis)
- Cancel → discard

**Data produced/modified**
- New `source` row: type=note, body_md, description, category, scopes[], linked_decisions[], linked_objectives[]
- `source_chunks` row(s) — usually just 1 chunk for short notes
- `audit_log` entry
- **No LLM cost** at save time (embeddings are async + cheap)

**Failure modes**
- Description < 30 chars → 422
- Body empty → 422
- Linked decision/objective doesn't exist (race w/ delete) → 422 w/ "remove dead link"
- Markdown render fails (rare) → save proceeds, preview shows raw

---

## W-15. `02v2-source-preview.html` — read chunks of an ingested source

**Entry**
- `02v2-project-kb.html` → click on SRC card → "View chunks"
- Citation link in any task deliverable / decision / ADR
- AI sidebar "show me SRC-002 chunk 4"

**Primary goal**
User browses post-extraction chunks of a source, with search-within-source, per-chunk freshness ("Claude last read this 2d ago"), citations list (which entities cited what), and source-level actions (re-crawl, edit metadata, archive).

**Exit**
- Re-crawl now → optimistic UI then POST → page re-renders w/ new last_crawled_at
- Edit metadata → `02v2-edit-source.html` (Pass 4 — referenced)
- Archive → `16-preview-apply-modal.html` flow
- Citation link → jumps to entity (decision / objective / task / doc)

**Data produced/modified**
- Read-only by default; actions (re-crawl, archive) modify `source` + `source_chunks`
- `audit_log` entry per action

**Failure modes**
- Source archived mid-view → flash "this source was archived by another user" + read-only banner
- Chunk index out-of-bounds (after re-chunk) → 404, redirect to chunk 1
- Citation pointed at deleted entity → shows "[deleted]" placeholder

---

## W-16. `03v2-create-objective.html` — create new objective

**Entry**
- `03v2-objectives-dag.html` → "+ New objective" button
- AI sidebar suggestion from analysis "create objective for X"
- `/objective` slash command in sidebar

**Primary goal**
User defines a new objective: title, business_context (≥100 chars), priority, type, scopes, dependencies (with live DAG preview + cycle prevention), KB focus, ≥1 measurable Key Result. Save is BLOCKED while any KR is unmeasurable.

**Exit**
- Create objective → `09-objective-detail.html?id=O-008` (or auto-spawn analysis task → `04-orchestrate-live.html`)
- Save as draft → `03v2-objectives-dag.html` w/ DRAFT badge
- Cancel → discard

**Data produced/modified**
- New `objective` row: title, business_context, priority, type, owner_id, scopes[], depends_on[] (w/ kind), kb_scope[], key_results[] (JSONB)
- If auto-spawn checked: new `task` row type=analysis on this objective
- `audit_log` entry

**Failure modes**
- KR unmeasurable (no target_value AND no measurement_command AND no attestation_source) → save disabled
- business_context < 100 chars → 422
- Dependency cycle → 422 (prevented client-side, double-checked server-side)
- Owner not in project_members → 422
- Scopes contain forbidden tag (e.g., `internal-only` for client-shared project) → soft warning

---

## W-17. `09-reopen-objective.html` — re-open ACHIEVED objective

**Entry**
- `09-objective-detail.html` → "Re-open" button (visible only when status=ACHIEVED)
- `05v2-task-deliverable.html` → "Re-open parent objective" inline action when challenger flags drift
- Cross-objective conflict detector → "Re-open with gap note" link

**Primary goal**
User re-opens an ACHIEVED objective with a mandatory gap note (≥50 chars) + auto-spawn analysis toggle. History (tasks DONE, ADRs, decisions) is preserved; KR statuses re-evaluate; downstream blockers re-block.

**Exit**
- Re-open with notes → `09-objective-detail.html` w/ ACTIVE status + new AT-NNN highlighted
- Re-open without analysis task → same, no auto-spawn
- Cancel → back to objective

**Data produced/modified**
- `objective.status` ACHIEVED → ACTIVE
- New entry in `objective.reopen_history[]` JSONB: {reopened_at, reopened_by, gap_note, prev_status, auto_spawned_task_id}
- Affected `objective.key_results[].status` ACHIEVED → IN_PROGRESS
- Downstream `objective.status` ACTIVE → BLOCKED (cascade)
- If auto-spawn: new `task` row type=analysis with origin=O-NNN, instruction template-built from gap note
- `audit_log` entry

**Failure modes**
- Gap note < 50 chars → 422
- Concurrent re-open by another user → 409, refresh
- Cost cap exceeded for auto-spawn analysis task → re-open succeeds, AT- creation deferred + flash warning
- Downstream cascade re-blocks objectives that have running tasks → those tasks continue (snapshotted) but warning shown

---

## W-18. `09-edit-challenger-checks.html` — CRUD per-objective challenger rules

**Entry**
- `09-objective-detail.html` → "Edit challenger checks" link in challenger card
- AI sidebar "this should be a standing check"
- `12-project-config.html` → "view challenger checks per objective"

**Primary goal**
User views existing checks (text + severity + scope), removes low-signal checks, adds new ones (free text or "suggest from scenarios"), sees Phase C prompt-injection preview + per-task cost impact.

**Exit**
- Inline edit/remove → instant PATCH, stays on page
- Add check → instant PATCH, stays on page
- Reset to org defaults → `16-preview-apply-modal.html` flow
- Done → `09-objective-detail.html`

**Data produced/modified**
- `objective.challenger_checks[]` JSONB modified (add/remove/edit)
- `audit_log` entry per change

**Failure modes**
- Check text > 300 chars → soft warning (cost impact)
- Adding check would push challenger prompt over hard token cap (10k) → 422
- Removing a "mandatory" check that was authored by org-policy → blocked w/ explanation
- Suggest-from-scenarios returns 0 (no eligible scenarios) → indigo panel hidden

---

## W-19. `09-edit-dependencies.html` — DAG edit inline

**Entry**
- `09-objective-detail.html` → "Edit dependencies" inline action
- `03v2-objectives-dag.html` → right-click "edit deps" on a node
- AI sidebar "should O-002 depend on O-006?"

**Primary goal**
User views the focused objective in DAG context (centered, upstream/downstream), removes/adds upstream deps (hard or soft), sees cycle prevention inline, sees impact preview for hypothetical changes.

**Exit**
- Inline add/remove/toggle → PATCH, stays on page (DAG re-renders)
- Done → `09-objective-detail.html`
- View full DAG → `03v2-objectives-dag.html`
- Edit downstream deps → recursive same page w/ different focus

**Data produced/modified**
- `objective.depends_on[]` JSONB array modified (each entry {objective_id, kind: hard|soft})
- Computed `objective.blocks[]` re-derived on next read
- `audit_log` entry per change

**Failure modes**
- Cycle detected → add disabled w/ tooltip showing the forming path
- Hard-dep on a non-existent / archived objective → 422
- Removing the last hard-dep when downstream tasks are running → soft warning, allow w/ ack

---

## W-20. `05v2-close-task.html` — close task with mandatory reason

**Entry**
- `05v2-task-deliverable.html` → "Close task" button (visible when status≠DONE and findings exist)
- AI sidebar "you can close DT-009 if you defer F-2"
- `04-orchestrate-live.html` → "Close mid-flight" link

**Primary goal**
User closes a NOT_DONE task that has unresolved findings. Each finding gets explicit address-or-defer (with reason ≥30 chars). User writes ≥100-char close reason and signs with full name typed.

**Exit**
- Close (signed) → `05v2-task-deliverable.html` w/ CLOSED status + findings updated
- Pre-create follow-up first → `05v2-create-followup-task.html?source_finding=F-X`
- Cancel → back to task

**Data produced/modified**
- `task.status` → CLOSED
- `task.close_reason` set, `task.close_signature` set
- For each deferred finding: `finding.defer_reason`, `finding.deferred_by_task_id`, status stays OPEN
- For each addressed finding: status → IN_PROGRESS or DONE depending on linked-action
- Parent objective re-checks: if all tasks done, may auto-ACHIEVE (KR check)
- `audit_log` entry w/ signature

**Failure modes**
- Close reason < 100 chars → 422
- Signature doesn't match user.display_name (case-insensitive) → 422
- A finding has no action chosen → 422
- A defer reason < 30 chars → 422
- Concurrent close by another user → 409, refresh

---

## W-21. `05v2-create-followup-task.html` — spawn follow-up from concern

**Entry**
- `05v2-task-deliverable.html` → "Create follow-up" on a finding row
- `05v2-close-task.html` → "Pre-create DT-012 follow-up" footer button
- AI sidebar "spawn task for F-2"

**Primary goal**
User creates a new task pre-filled from a finding's text: title + instruction + draft AC + auto-attached skills. Edits before commit. Cost preview shown.

**Exit**
- Create task → `07-new-task.html?task=DT-012` (continues wizard) or directly `04-orchestrate-live.html`
- Save + pick mode → `07-mode-selector.html?task=DT-012`
- Cancel → back to source task

**Data produced/modified**
- New `task` row w/ `task.linked_findings[]` containing source finding id
- New `ac` rows attached to the new task
- `finding.addressed_by_task_id` set (status: pending — flips to ADDRESSED when task DONE)
- `audit_log` entry

**Failure modes**
- Title or instruction empty (after editing draft) → 422
- AC list empty (user removed all) → 422 (feature/bug tasks require AC)
- Source finding doesn't exist (race w/ delete) → 422
- LLM draft endpoint fails → form opens with empty fields + error banner

---

## W-22. `05v2-scenario-generate.html` — live progress for "generate test & run now"

**Entry**
- `09-add-scenario.html` → "🪄 Generate test for this scenario now" submit
- `05v2-task-deliverable.html` → scenario row "Generate test + run" inline
- AI sidebar "generate test for S-011 now"

**Primary goal**
Show live phase tracker (1. LLM drafts test, 2. Save to workspace, 3. Run test, 4. Report back) with streaming console, cost meter, drafted code preview. Cancellable at phase boundaries.

**Exit**
- Auto-redirect on phase 4 complete → `05v2-task-deliverable.html#S-011` w/ scenario in passed/failed state
- Cancel → `05v2-task-deliverable.html?flash=S-011-cancelled` (test code preserved if phase 1 done)
- Error in any phase → page stays w/ error banner + retry

**Data produced/modified**
- New `scenario_generation_run` row w/ phases JSONB, draft_artifacts JSONB
- On phase 2: file written to workspace
- On phase 3: `test_run` row created (existing schema)
- On phase 4: `scenario.last_run_status`, `scenario.last_run_at` updated
- Multiple `llm_call` rows
- `audit_log` entry per phase + cancel

**Failure modes**
- Phase 1 LLM error → halt, no file written
- Phase 2 file conflict → halt w/ "file exists, overwrite?"
- Phase 3 fixtures missing → test errors, scenario marked failed
- Cost cap exceeded mid-run → halt at next phase boundary, partial state preserved
- User cancels mid-phase → stops at boundary, state preserved

---

## W-23. `05v2-assign-auditor.html` — pick user/external for manual AC

**Entry**
- `05v2-task-deliverable.html` → "Assign auditor" on AC with verification=manual
- `09-objective-detail.html` → "Assign manual review" on AC card
- AI sidebar "who can audit AC-6?"

**Primary goal**
User assigns AC-6 verification to internal user with `can_audit` role OR external auditor by email. Writes verification notes (≥1 instruction). Picks due-by + reminder cadence. Sees notification preview + past-audit history for assignee.

**Exit**
- Send assignment → `05v2-task-deliverable.html?flash=AC-6-assigned`, notification fires
- Save as draft → row created, no notification
- Cancel → back to task

**Data produced/modified**
- New `manual_verification_task` row: ac_id, task_id, assignee_id_or_email, instructions, due_at, reminder_cadence, status=ASSIGNED
- AC status flips PENDING → AWAITING_AUDITOR
- Notification email + in-app fires async
- `audit_log` entry

**Failure modes**
- Internal user lost can_audit permission between page load + submit → 422
- External email malformed → 422
- Notes empty → 422
- Due-by in the past → 422
- Notification delivery fails → assignment saved, flash "notification failed, retry?"

---

---

---

# FLOWS — Pass 3 mockups (non-develop deliverables + auditor surfaces)

5 new mockups: 3 task-type-specific deliverable variants (analysis / planning / documentation) and the auditor's side of the assign-auditor loop (inbox + review-with-evidence).

Scenario constants extended in Pass 3: added tasks `AT-005` (analysis — architecture KB research), `PT-003` (planning — O-002 decomposition), `DOC-001` (documentation — O-002 architecture overview). User roster extended: `jpatel@acme.com` (external auditor), `aczajka@acme.com` (internal reviewer).

---

## W-24. `05v2-analysis-deliverable.html` — ANALYSIS task report

**Entry**
- `09-objective-detail.html` → "View AT-005 deliverable" link on the analysis-task row
- `04-orchestrate-live.html` → task complete event → navigate here
- `03v2-objectives-dag.html` → click on AT-005 node in DAG

**Primary goal**
User scrutinizes what an analysis task produced: sources read (per-source chunks + citations), ambiguities surfaced (resolved vs. escalated), AC drafted (with source attribution; INVENTED flagged), scenarios generated, challenger verification of extraction fidelity, and the refused-to-verify scope limits. Decides whether to answer open Q's, re-run with different KB scope, spawn planning, or close.

**Exit**
- Answer Q-007 / Q-008 → `09-answer-ambiguity.html?q=Q-007` (or Q-008)
- Spawn PLANNING → `07-new-task.html?type=planning&objective=O-002` (task stays BLOCKED until Q's close)
- Re-run analysis → `02v2-add-source-file.html` (then AT-005-v2 auto-spawns on that source)
- Close → `05v2-close-task.html?task=AT-005` (requires reason; Q's persist regardless)
- Drop AC-5 / Accept as INVENTED → PATCH ac + stays on page w/ flash

**Data produced/modified**
- Read-only view by default. Actions mutate:
- Drop AC → `ac.status='ARCHIVED'` + reason
- Accept INVENTED → `ac.is_unsourced=true` + `ac.acceptance_reason`
- `audit_log` entry per action

**Failure modes**
- Some `source_reads` entries stale (source archived since task ran) → show "[archived]" placeholder
- Challenger re-run exceeds budget → "re-run" button greys w/ tooltip
- Q-007 answered in another tab between page mount and action → 409 on next submit, refresh required
- Spawning PLANNING when Q's still OPEN → task created in BLOCKED state (not a failure — expected)

---

## W-25. `05v2-planning-deliverable.html` — PLANNING task report

**Entry**
- `09-objective-detail.html` → "View PT-003 deliverable" on planning-task row
- `04-orchestrate-live.html` → planning task complete → here
- `03v2-objectives-dag.html` → click PT-003 node

**Primary goal**
User audits the planning output before approve-all: DAG structure (acyclic, critical-path), task list with cost/risk/deps, AC coverage matrix (every objective-AC → ≥1 task), fanout warnings, challenger concerns about velocity + missing DOC tasks. Decides approve-all, start-single, edit, re-plan, or close (discards drafts).

**Exit**
- Approve all → POST `/plan/PT-003/approve` → drafts DRAFT→QUEUED → `03v2-objectives-dag.html?flash=12-spawned`
- Start DT-001 only → drafts other rows stay DRAFT, DT-001 → QUEUED → `04-orchestrate-live.html?task=DT-001`
- Inspect/edit task → `07-new-task.html?task=DT-NNN` (wizard in edit mode on the draft row)
- Re-plan → re-runs PT-003 with new constraints (prompt)
- Close → `05v2-close-task.html?task=PT-003` (drafts discarded unless saved-as-plan)

**Data produced/modified**
- Approve-all: `task.status` DRAFT→QUEUED for 12 drafts; creates `execution_attempt` placeholders
- Start single: 1 task → QUEUED, others remain DRAFT
- Edit: PATCH draft task row (title/instruction/AC/deps)
- Close: drafts deleted OR moved to `draft_plan_archive` with 30d TTL
- `audit_log` entry per transition

**Failure modes**
- Approve-all budget exceeds cap → partial spawn + halt w/ "5 of 12 spawned, cap hit" banner
- Draft stale (source AC changed since PT-003 ran) → warning on approve-all, user must re-plan
- Cycle introduced by edit (user changes deps in wizard) → 422 at save
- Concurrent edit of same draft by another planner → 409

---

## W-26. `05v2-documentation-deliverable.html` — DOC task report

**Entry**
- `09-objective-detail.html` → "View DOC-001 deliverable" on doc-task row
- `10-post-exec-docs.html` → "View task that produced this" back-reference
- `04-orchestrate-live.html` → doc task complete → here

**Primary goal**
User reviews produced artifacts (markdown, ADR, README updates) with citation heatmap per paragraph, identifies unsourced claims (LLM filler), runs challenger review for section completeness + link resolution. Decides to edit inline, regenerate, share with client, or freeze as snapshot.

**Exit**
- Edit artifact → opens in-IDE / web editor at file path
- Regenerate artifact → re-runs DOC-001 for that single artifact (not all)
- Share link for client → `10-post-exec-docs.html?task=DOC-001&share=true`
- Spawn DOC-002 → `07-new-task.html?type=doc&objective=O-002`
- Close → `05v2-close-task.html?task=DOC-001` (artifacts stay regeneratable unless frozen)

**Data produced/modified**
- Edit: file write in workspace + `artifact.last_modified` updated + `audit_log`
- Regenerate: new `llm_call`, artifact version bumped, old version archived
- Freeze: `artifact.is_frozen=true` + `artifact.freeze_kind` (adr_accepted | pdf_export | folder_rule)
- Share: new `share_link` row with TTL + scope filters
- `audit_log` entry per action

**Failure modes**
- Regenerate hits cost cap → halts with partial edit preserved, banner warns
- File modified externally between DOC-001 run and view → diff banner, user chooses merge/discard
- Share link generation fails (missing client-view template) → flash error, no link created
- Editor target path doesn't exist (workspace moved) → 404 with "restore from git"

---

## W-27. `05v2-auditor-inbox.html` — auditor's inbox

**Entry**
- Notification email link to auditor's Forge login
- Bookmark `/auditor-inbox` for users with `external_auditor` role
- In-app nav for users with any `can_audit` project membership
- Deep link from assigner's page ("View J. Patel's inbox") — restricted to admins

**Primary goal**
Auditor (J. Patel) sees all active AC verifications assigned to them across projects, prioritized by due date + priority. Filter by project / status / priority. Manage notification preferences (digest cadence, reminders, Slack). Set OOO so assigner sees re-route banner. Understand "how auditing works in Forge" + explicit list of what they CANNOT do.

**Exit**
- Review → `05v2-auditor-review.html?assignment_id=...&ac=AC-NN`
- Show history → same page, expanded w/ completed audits
- Save prefs → PATCH `user.notification_prefs` → stays on page w/ flash
- Set OOO → modal (not mocked) → PATCH `user.ooo_dates`

**Data produced/modified**
- Read-heavy. Mutations:
- Prefs save: PATCH `user.notification_prefs` JSONB
- OOO: PATCH `user.ooo_dates[]`
- No changes to assignments themselves from this surface (auditor only acts via W-28)

**Failure modes**
- User lost `can_audit` role since assignment → row shows "access revoked — request re-activation"
- Project archived since assignment → row shows "project archived" w/ archived-state explanation
- Notification delivery pref change fails (email provider down) → save succeeds, warning flash "will retry"
- Filter returns 0 results → empty state w/ "no audits match" + clear-filter link

---

## W-28. `05v2-auditor-review.html` — auditor reviewing one AC (HIGH-risk #4 mitigation)

**Entry**
- `05v2-auditor-inbox.html` → "Review →" on assignment row
- Notification email w/ per-assignment deep link
- Bookmark saved during prior draft-save

**Primary goal**
Auditor forms and submits verdict (PASSED_WITH_EVIDENCE / PASSED_ATTESTATION / REJECTED / NEEDS_CLARIFICATION) with mandatory evidence for the PASSED_WITH_EVIDENCE path (≥1 file OR ≥200 chars text). PASSED_ATTESTATION shows skeptical-UX warning + requires ≥100-char reason. Forensic capture (auditor name + timestamp + IP + evidence hash + typed signature) stored permanently.

**This mockup directly mitigates Pass 2 HIGH risk #4 (evidence-chain).**

**Exit**
- Submit review → confirmation modal → type display_name to sign → POST `/manual-verification/{id}/submit` → `05v2-auditor-inbox.html?flash=AC-6-submitted`
- REJECTED branch → DT-009 auto-re-opens w/ finding F-NN, notification fires to assigner
- NEEDS_CLARIFICATION branch → decision Q-NNN spawned, AC stays AWAITING_AUDITOR, notification fires
- Save as draft → POST w/ status=DRAFT, no notification, visible only to auditor
- Cancel → back to inbox

**Data produced/modified**
- `manual_verification_task.verdict` (ENUM extended in Pass 3: PASSED_WITH_EVIDENCE, PASSED_ATTESTATION, REJECTED, NEEDS_CLARIFICATION)
- `manual_verification_task.evidence_artifacts[]` JSONB — {url, sha256, mime, size, uploaded_at}
- `manual_verification_task.evidence_text` + `evidence_text_hash`
- `manual_verification_task.method`, `executed_at`, `environment`
- `manual_verification_task.signature_text`, `signature_ip`, `signature_user_agent`, `signed_at`
- `manual_verification_task.attestation_reason` (only for PASSED_ATTESTATION, ≥100 chars)
- On REJECTED: new `finding` row + `task.status` re-opens
- On NEEDS_CLARIFICATION: new `decision` row w/ kind=clarification + originating_auditor_id
- `ac.status` AWAITING_AUDITOR → PASSED | PASSED_ATTESTATION | REJECTED_BY_AUDITOR | AWAITING_CLARIFICATION
- `audit_log` entry signed by Forge service key

**Failure modes**
- Submit PASSED_WITH_EVIDENCE without file AND without ≥200-char text → 422 inline + button disabled
- Submit PASSED_ATTESTATION with &lt;100-char reason → 422 inline
- Submit REJECTED with &lt;100-char reason → 422 inline
- Typed signature doesn't match `user.display_name` (case-insensitive) → 422 on modal submit
- Evidence file upload > 25 MB → 413 at upload step, file rejected
- Evidence file fails virus scan → 422 + file quarantined, user must replace
- Auditor loses `can_audit` role between page mount + submit → 403 at submit
- Concurrent assigner-override: if assigner closes DT-009 while auditor drafts → draft preserved, submit returns 410 Gone

---

## How Pass 2 W-11..W-23 connect to Pass 3 W-24..W-28

- **W-13 (`05v2-assign-auditor.html`) → W-27 (`05v2-auditor-inbox.html`) → W-28 (`05v2-auditor-review.html`) → back to W-13 task deliverable updated.** The full manual-verification loop: assigner picks auditor + sends notification → auditor sees assignment in inbox → auditor reviews + submits verdict → task deliverable re-renders with verdict + evidence link (PASSED_WITH_EVIDENCE) or finding (REJECTED) or decision (NEEDS_CLARIFICATION).
- **W-24 (analysis deliverable) exposes ambiguities** that lead to `09-answer-ambiguity.html` (W-1 from Pass 1). Answering unblocks planning tasks.
- **W-25 (planning deliverable) spawns develop tasks** via `07-new-task.html` (W-4 from Pass 1). Approve-all is a batch variant.
- **W-26 (DOC deliverable) feeds** `10-post-exec-docs.html` for client-share link generation.
- **W-24, W-25, W-26 all share the close-task path** `05v2-close-task.html` (W-20) but with task-type-specific close-safety notes explaining what closing does/doesn't lock.
- **Every deliverable variant** feeds back to `09-objective-detail.html` which aggregates the per-objective audit trail.

---

## Cross-mockup link integrity (Pass 1 + Pass 2 + Pass 3)

Every breadcrumb in Pass 1 + Pass 2 + Pass 3 mockups resolves to an existing file. The destination column in each annotation panel uses one of:

**Pass 1 destinations:** `01-dashboard.html`, `02v2-project-kb.html`, `03v2-objectives-dag.html`, `04-orchestrate-live.html`, `05v2-task-deliverable.html`, `07-mode-selector.html`, `07-new-task.html`, `07-crafter-preview.html`, `09-objective-detail.html`, `09-answer-ambiguity.html`, `09-add-scenario.html`, `09-add-ac.html`, `10-post-exec-docs.html`, `11-skills-library.html`, `11-skill-edit.html`, `12-project-config.html`, `12-skills-tab.html`, `12-hooks-tab.html`, `12-phase-defaults-tab.html`, `12-add-hook.html`, `16-ai-sidebar.html`, `16-preview-apply-modal.html`.

**Pass 2 destinations:** `02v2-add-source-file.html`, `02v2-add-source-url.html`, `02v2-add-source-folder.html`, `02v2-add-source-note.html`, `02v2-source-preview.html`, `03v2-create-objective.html`, `09-reopen-objective.html`, `09-edit-challenger-checks.html`, `09-edit-dependencies.html`, `05v2-close-task.html`, `05v2-create-followup-task.html`, `05v2-scenario-generate.html`, `05v2-assign-auditor.html`.

**Pass 3 destinations (new):** `05v2-analysis-deliverable.html`, `05v2-planning-deliverable.html`, `05v2-documentation-deliverable.html`, `05v2-auditor-inbox.html`, `05v2-auditor-review.html`.

Pages NOT YET BUILT but referenced (forward references — fine for Pass 4+):
- `02v2-edit-source.html` — re-ingest, edit metadata, archive
- `02v2-source-conflict-resolver.html` — picker for SRC-001 vs SRC-002 contradictions
- `03v2-edit-objective.html` — full objective edit (different from dependency-edit)
- `12-edit-contract.html`
- `05v2-task-failed.html` — failed-state variant of deliverable
- `05v2-task-replay.html` — replay historical task against new skill version
- Hook firing history page (`/hook/{id}/firings`)
- Cost forensic drilldown
- Audit log full view
- Action draft inbox

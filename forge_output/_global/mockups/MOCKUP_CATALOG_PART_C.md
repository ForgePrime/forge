# Mockup catalog — Part C (task execution + deliverables)

## 07-new-task.html

- **Function:** First step of task creation wizard. User defines a new task (title, instruction, AC inheritance, dependencies, KB scope) for an objective. Task type is locked from entry button. Form is 3-step: task details → mode selection → confirm + start.

- **Actions:** Fill Title, Write Instruction (LLM rewrite button), Toggle AC inheritance, Add task-specific AC, Search dependencies, Override KB scope per-source, Continue to mode selection, Save as draft, Cancel

- **Data shown:** Wizard progress (1 of 3), Task type badge (locked), AC list (inherited + task-specific), Dependencies with cycle detection, KB sources with checkboxes, Scrutiny sidebar ("what NOT checked yet"), Cost/complexity hint

- **Linked mockups:**
  - Inbound: 09-objective-detail.html → "+ task" buttons; 03v2-objectives-dag.html → context menu
  - Outbound: 07-mode-selector.html → Continue (creates DRAFT); 09-objective-detail.html → Cancel/Save as draft

- **Pros:** Clear 3-step wizard structure; AC inheritance reduces boilerplate; dependency cycle detection; KB scope override per-source is flexible; "What NOT checked" transparency; LLM rewrite available inline

- **Cons:** Dependency search doesn't show status (BLOCKED tasks not flagged); KB scope warning only for "primary" sources; no validation that instruction references AC/KB sources; localStorage fallback behavior unclear; single AC type selector misses task-specific patterns

- **What I would want (for AI + user):** (1) Auto-detect KB sources in instruction text and pre-check them. (2) Live dependency status + acyclic check with upstream blocker labels. (3) Show actual AC text, not just count. (4) Cost estimate before mode selector. (5) Task-type-specific instruction templates. (6) Lint instruction for missing AC refs, vague phrasing.

---

## 07-mode-selector.html

- **Function:** Second step of task creation. User chooses Direct (fast/cheap, parser builds prompt) vs. Prompt-Crafted (crafter inspects code + KB, produces detailed prompt). Side-by-side comparison with cost/time estimates, per-task recommendation logic, and KB scoping.

- **Actions:** Select mode (radio), Read "Why Forge recommends", Preview crafted prompt ($0.08, not executor), Advanced options (model picker, max cost, KB sources), Start task

- **Data shown:** Two mode cards (recommended highlighted), Flow diagrams per mode, Best-for/weak-for bullets, Cost + time estimates, "Why recommended" with metrics ("23% better scores"), Crafter preview collapsed, Advanced section collapsed

- **Linked mockups:**
  - Inbound: 07-new-task.html → Continue
  - Outbound: 07-crafter-preview.html; 04-orchestrate-live.html (Start); back to 07-new-task.html

- **Pros:** Mode choice visual + explained; "Why recommended" with concrete numbers; cost + time upfront; Advanced hidden by default; flow diagrams demystify process

- **Cons:** Recommendation logic not shown (user doesn't know inputs); Cost estimates are ranges (hard to plan); KB scoping separated from task form; no Direct-mode prompt preview (asymmetric); Model defaults not justified

- **What I would want (for AI + user):** (1) Show recommendation rationale ("complexity=high, legacy=yes, 5 sources → crafted"). (2) Deterministic cost calculator (show formula). (3) KB source preview inline (freshness, size). (4) Direct-mode prompt preview as collapsible. (5) Cost cap validation with context. (6) Skill attachment info with per-skill cost impact.

---

## 07-crafter-preview.html

- **Function:** Before execution, user inspects what crafter LLM produced: crafted prompt (2,850 tokens, prompt-cache eligible), trace of inspections (KB chunks, code files, skills), and explicit scope limits (what it did NOT do). Lets user re-craft, edit manually, or run. Cost shown ($0.08 crafter, ~$0.42 executor to follow).

- **Actions:** Copy prompt, Edit manually (enables textarea), Re-craft (re-run crafter, $0.08), Run with this prompt → 04-orchestrate-live.html, Back to mode selector

- **Data shown:** Header (task ID, mode pill, model pair, $0.08 cost), Crafted prompt (left 65%, full text monospace), Inspection trace (right 35%: KB sources with chunk counts, code files with ranges, skills consulted, entities referenced), Scope limits card (red: what did NOT do), Footer (cost breakdown, prompt cache note)

- **Linked mockups:**
  - Inbound: 07-mode-selector.html → "Preview crafted prompt"
  - Outbound: 04-orchestrate-live.html → "Run"; 07-mode-selector.html → Back; stays on page for re-craft

- **Pros:** Detailed + honest trace; "What NOT do" crucial transparency; prompt readable (pseudo-code, not JSON); cost meter + cache reuse note; manual edit gives control before executor cost

- **Cons:** Scope limits prose not machine-readable; re-craft doesn't re-open scope picker; code files show path not reasoning; no skill cost breakdown; no link to crafter LLM call log; prompt diff viewer missing for re-runs

- **What I would want (for AI + user):** (1) Scope limits as structured, editable data. (2) Code file inspection reasoning ("grep for X"). (3) Per-skill cost breakdown. (4) "Remove skill" button inline. (5) Deep link to crafter LLM call log. (6) Prompt diff viewer (if re-run, show what changed).

---

## 05-task-deliverable.html

- **Function:** Legacy (Pass 1) DONE task view. Compact one-screen summary: "All 8 tests pass. Challenger agrees. Deliverable trustworthy." Shows test results (8/8), challenger verdict (5✓/0✗ claims), findings (2 medium), code diff side-by-side. Quick Approve/Retry/Rollback buttons. Simplified predecessor to 05v2.

- **Actions:** Approve, Retry, Rollback, View side-by-side diff, Create task from finding, Accept/Dismiss finding

- **Data shown:** Narrative header (one-sentence summary), 4 summary cards (Tests 8/8, Challenger 5✓/0✗, Findings 2 med, Delivery 3 files), Code diff, AC list, Findings panel, Challenger quote (testimonial style)

- **Linked mockups:**
  - Inbound: 04-orchestrate-live.html → task complete
  - Outbound: inline actions

- **Pros:** Compact one-screen scan; findings → create task closes loop; Challenger quote format builds trust

- **Cons:** Doesn't track task-type behaviors; no re-open; no scenarios tracking; doesn't show finding resolution detail

- **What I would want (for AI + user):** Replaced by 05v2 with type specificity; legacy file should be deprecated and removed from index.

---

## 05v2-task-deliverable.html

- **Function:** Detailed DONE/scrutiny DEVELOP task view. Narrative ("8 of 10 scenarios passed, 2 deferred; Challenger verified 5, refused 3 scopes; 1 AC unsourced"), scenarios + AC with test bodies, challenger detail (refused scope + per-claim + concerns), re-open/close options. Main surface for "is this task actually done?"

- **Actions:** Ask challenger verify aspect, Add missing scenario, Re-open with gap notes, Close task (reason required), View test body, Mark scenario verified manually, Generate test & run now, Assign to auditor, Re-run challenger

- **Data shown:** Narrative header (amber "DONE — awaiting scrutiny"), "Is it safe to close?" box with checklist, Scrutiny strip (5 cards: scenarios 8 run/2 defer, tests 8/8, challenger 5 verified/3 refused, findings 2 unresolved, AC 1 unsourced), Scenarios & AC card (full width, ✓/⏸ badges, type badge, description, test body expandable, user-added amber rows), User-added scenarios ("Generate test & run now"), Challenger detail (refused scope, per-claim checklist, concerns + severity), Re-open section (textarea + auto-challenger toggle)

- **Linked mockups:**
  - Inbound: 04-orchestrate-live.html → task complete
  - Outbound: 09-add-scenario.html, 05v2-scenario-generate.html, 05v2-assign-auditor.html, 05v2-close-task.html, back to same page for re-open

- **Pros:** "Is it safe to close?" explicit risk awareness; full test/scenario body visible; user-added scenarios (amber) clearly separated; Challenger close-safety note concrete ("did not verify: security, KB alignment, load"); re-open with notes preserves history; followup link from findings

- **Cons:** Scenarios list long (scrolls); Challenger refused-scope not actionable (no inline re-run button); AC-5 unsourced flagged but can't drop from deliverable; Findings count no severity breakdown; "Generate test & run" no cost guard modal

- **What I would want (for AI + user):** (1) Scenarios grouped by status (✓ Passed / ⏸ Deferred / ✗ Failed) with collapse/expand. (2) Inline challenge re-run buttons on refused-scope items with cost. (3) AC-5 "Drop AC" button inline. (4) Findings breakdown by severity ("2 unresolved: 1 HIGH + 1 MED"). (5) "Generate & run" guard modal. (6) Task-type-specific close-safety notes.

---

## 05v2-analysis-deliverable.html

- **Function:** ANALYSIS task deliverable (AT-005 "Research KB for architecture decisions"). Shows analysis output: sources consulted (4 of 5, per-source chunks + citations), ambiguities surfaced (table: Q-ID, severity, status, path), AC drafted (5, 1 INVENTED flagged), scenarios (4 non-happy-path), challenger review (extraction fidelity verified, scope limits), "what NOT done" template. Blocks PLANNING tasks until open Q's resolved.

- **Actions:** Answer Q-007/Q-008, Re-run analysis w/ new KB scope, Close task (reason required), Drop AC-5/Re-source/Accept as INVENTED, Re-run challenger, Ask challenger specific aspect

- **Data shown:** Narrative header (blue, "2 ambiguities unresolved → blocks planning"), "What AT-005 did" sentence, Scrutiny strip (Ambiguities 6 flagged, AC 5 drafted/1 unsourced, Sources 4 of 5, Scenarios 4 generated, Decisions 3 CLOSED), Sources consulted (expandable per-source with chunks + citations; SRC-005 excluded with reason), Ambiguities table (Q-ID, Question, Severity, Status, Path), AC proposed (AC-1..4 sourced, AC-5 rose/red INVENTED with warning + 3 action buttons), Scenarios generated (4 with kind/description/expected/rationale), Challenger review (refused scope, per-claim, close-safety note), "What NOT done" template

- **Linked mockups:**
  - Inbound: 04-orchestrate-live.html → analysis task complete
  - Outbound: 09-answer-ambiguity.html?q=Q-007/Q-008, 02v2-add-source-file.html (re-run), 05v2-close-task.html

- **Pros:** Source consulted with per-source chunk counts + citation list transparent; Ambiguities table scannable; AC-5 INVENTED flagged prominently with 3 action buttons; SRC-005 exclusion reason stated + risk note; Challenger candid; "What NOT done" explicit

- **Cons:** "Re-run with different scope" UX unclear; Ambiguities blocked-on-PLANNING shown in header, not table; AC-5 link to excluded source not clickable; Scenarios list long; no visual link between ambiguities and AC dependencies

- **What I would want (for AI + user):** (1) "Re-run analysis" inline modal KB scope picker with cost. (2) Ambiguities table visual blocking indicator column. (3) AC-5 unsourced "Reason for accepting" textarea + batch operation. (4) SRC-005 exclusion side-by-side excerpt comparison. (5) Scenarios collapse/expand by kind. (6) KB coverage gauge.

---

## 05v2-planning-deliverable.html

- **Function:** PLANNING task deliverable (PT-003 "Decompose O-002 into develop tasks"). Shows planning output: 12 develop + 1 doc task drafted (all DRAFT), DAG (critical path amber, parallel blue), AC coverage matrix (5 AC → 12 tasks), DAG acyclic passed, fanout warning (DT-001 blocks 7). Lets user approve-all, start-single, edit drafts, re-plan, or close.

- **Actions:** Approve all (spawn 12 → QUEUED), Start DT-001 only, Inspect/edit task (wizard mode), Re-plan w/ constraints, Close task (discards drafts), Re-run challenger

- **Data shown:** Narrative header (purple, "12 develop + 1 doc drafted, none yet spawned"), "What PT-003 did" (took 5 AC + 3 decisions → 12-task DAG + 1 doc, 6-task critical path, 4-week est), Scrutiny strip (Tasks 12+1, DAG acyclic ✓, AC coverage 5/5, Task size max 5 OK, Fanout risk DT-001 blocks 7), DAG preview (SVG: critical amber, parallel blue, doc grey, edges + dependencies, legend, fanout warning), Task list table (13 rows: ID | Title | Deps | AC | Est cost | Risk | Inspect, amber critical path rows, totals row), AC coverage matrix (rows = AC, cols = tasks), Challenger review (refused: team skills/capacity/timeline/identical scope), per-claim (5 verified), concerns (2 MEDIUM), Close-safety (planning is contract), "What NOT done"

- **Linked mockups:**
  - Inbound: 04-orchestrate-live.html → planning complete
  - Outbound: Inspect → 07-new-task.html?task=DT-NNN (edit), Approve-all → 03v2-objectives-dag.html?flash=12-spawned, Start → 04-orchestrate-live.html?task=DT-001, Re-plan → constraints modal

- **Pros:** DAG visual clear + fanout warning; AC coverage matrix right structure; Challenger refuses team-capacity/timeline; critical path duration + cost totals help planning; fanout warning specific w/ split suggestion

- **Cons:** Task list 13 rows (scrolls); no filtering; AC-5 INVENTED context missing; Cost estimate ($0.52) is LLM cost not human-hour equivalent; Re-plan doesn't show current constraints; DAG export .dot not previewed

- **What I would want (for AI + user):** (1) Task list filtering. (2) AC-5 unsourced callout in plan. (3) Re-plan constraints visible. (4) Cost with labor equivalent context. (5) .dot file inline preview. (6) "Estimate accuracy" note from Challenger.

---

## 05v2-documentation-deliverable.html

- **Function:** DOC task deliverable (DOC-001 "Write architecture overview"). Shows documentation output: 3 artifacts (architecture.md 2,400 words 18 citations, ADR-001 accepted 7 citations, README update 4 citations), citation heatmap per paragraph (green = cited, red = unsourced), challenger verification (section completeness, link resolution, 2 unsourced paragraphs flagged), actions (edit, regenerate, share with client, spawn DOC-002).

- **Actions:** Edit artifact (IDE), Regenerate artifact (single), Regenerate ADR-001 w/ template, Share link for client, Spawn DOC-002, Close task, Re-run challenger

- **Data shown:** Narrative header (slate, "3 artifacts · 2 unsourced claims"), "What DOC-001 produced", Scrutiny strip (Artifacts 3, Citations 29 total, Unsourced 2, Stale links 0, Reading time 9 min), architecture.md (file preview, citation heatmap ¶1-¶12 color-coded, unsourced ¶ identified + reasoning, action buttons), ADR-001 (preview, section completeness grid, action buttons), README section (preview, cross-links check, backward-compat note), Challenger review, per-claim, concerns, close-safety, "What NOT done"

- **Linked mockups:**
  - Inbound: 04-orchestrate-live.html → DOC task complete
  - Outbound: 10-post-exec-docs.html?task=DOC-001&share=true, 07-new-task.html?type=doc, 05v2-close-task.html

- **Pros:** Citation heatmap visual; Unsourced claims identified + reasoned; ADR section grid scannable; README cross-links validated; Challenger refuses subjective checks (honest)

- **Cons:** Citation heatmap doesn't show *which* sources per citation; Unsourced claim flagged but can't inline fix; ADR "accepted" status unclear; No word count / readability score; Share link flow not shown; No version history

- **What I would want (for AI + user):** (1) Citation popover (hover ¶2 → "SRC-001 §3, SRC-002, D-010"). (2) Unsourced inline fix modal. (3) Readability metrics. (4) Share link preview (mock read-only client view). (5) Version history sidebar. (6) Artifact freeze state ("Lock as client deliverable").

---

## 05v2-scenario-generate.html

- **Function:** Live progress tracker for "generate test & run now" on user-added scenarios. 4-phase flow: (1) LLM drafts test (Sonnet, 18s, $0.07), (2) Save to workspace (formatter, 3s), (3) Run test (pytest, 30s, no cost), (4) Report (parse, 2s, $0.05). Live console + drafted code + cost meter. Can cancel at boundaries.

- **Actions:** Watch progress, Cancel after phase 2, View drafted test code (read-only)

- **Data shown:** Header ("Phase 2 of 4"), Phase tracker (4 circles), Live console (monospace, 500px, colored logs with timestamps), Drafted test preview (pytest code, syntax-highlighted, 62 lines, scroll), Cost meter (per-phase breakdown, running total), Cancel section, Scenario context card

- **Linked mockups:**
  - Inbound: 05v2-task-deliverable.html → "Generate test & run" on scenario
  - Outbound: 05v2-task-deliverable.html#S-011 (auto-redirect on complete), 05v2-task-deliverable.html?flash=S-011-cancelled (on cancel)

- **Pros:** 4-phase breakdown transparent; Live console readable; Cost meter per phase; Drafted code preview; Scenario context sidebar orients user

- **Cons:** Cancel only at phase 2 (one boundary only); Cost "est $0.00" vs "$0.05" unclear; Assumes fixtures exist (no pre-check); Console 500px (verbose tests scroll off); No cost cap guard; No fixture validation before phase 3

- **What I would want (for AI + user):** (1) Cost guard modal before phase 1. (2) Fixture pre-validation in phase 2. (3) Console auto-follow. (4) Cancel at any phase w/ context-aware confirmation. (5) Clarify phase 4 "describe" step. (6) Link drafted code to scenario.

---

## 05v2-close-task.html

- **Function:** Closure form for NOT_DONE tasks with unresolved findings. User must address (convert to follow-up task) or defer (with reason ≥30 chars) each finding, write close reason (≥100 chars, recorded forever), sign with full name. Task-type-specific close-safety notes.

- **Actions:** Per-finding: select Address now or Defer + reason textarea; Write close reason; Type full name signature; Pre-create follow-up first; Cancel; Close task

- **Data shown:** Header (rose, "3 unresolved items"), Unresolved items checklist (left): per finding (severity badge, F-id, description, source, action choice + reason input), Close reason textarea (left), Signature input (left), Summary card (right, emerald), Close impact card (right, amber), Recent closes table (right), Scrutiny section (rose: "What closing does NOT do")

- **Linked mockups:**
  - Inbound: 05v2-task-deliverable.html → "Close task" button
  - Outbound: 05v2-create-followup-task.html?source_finding=F-2 (Pre-create), POST /task/{id}/close (Close), 05v2-task-deliverable.html (success, CLOSED state)

- **Pros:** Per-finding action explicit; Close reason + signature create audit trail; "What NOT do" honest; "Recent closes" context

- **Cons:** Defer reason min not clear upfront; "Address now" doesn't show what task will be created; F-4 "Address chosen, will run S-007" special case unclear; Sign-off on F-3 cited but never verified; Deferred findings no link back to close action

- **What I would want (for AI + user):** (1) Defer reason upfront label ("≥30 chars") + live count. (2) "Address now" preview modal. (3) F-4 scenario context shown. (4) Deferred findings provenance (close action links forward to finding). (5) Cumulative debt running tally on form (project HIGH defers >30d).

---

## 05v2-create-followup-task.html

- **Function:** Pre-filled task form from challenger finding (F-2 rate-limit). LLM drafts title, instruction, AC from finding. User edits before committing. Links back to source (F-2 marked "addressed_by: DT-012" when DT-012 DONE). Inherits KB scope + skills/hooks/checks, but has independent AC + challenger run.

- **Actions:** Edit title/instruction, Trigger LLM tighten ($0.03), Add/remove AC, Detach skill, Add skill from library, Change type/priority/target objective, Create task (or Save + pick mode)

- **Data shown:** Source banner (amber blockquote of F-2 text), Task definition card (Title, Instruction, AC drafted, Linked source), Skills card (auto-attached, removable, "+ Add skill"), Type/Priority/Objective selectors, Summary card (right), Cost preview (right: $0.35 total, budget check), Inheritance vs. fresh (right), Scrutiny section (rose: "Follow-ups are NEW verifications")

- **Linked mockups:**
  - Inbound: 05v2-task-deliverable.html → "Create follow-up", 05v2-close-task.html → "Pre-create DT-012 first"
  - Outbound: 07-mode-selector.html (Save + pick mode), 07-new-task.html?task=DT-012 (Create), 05v2-task-deliverable.html (Cancel)

- **Pros:** Source banner blockquote clear; Pre-drafted AC test-verifiable; Inheritance vs. fresh clarifies autonomy; Cost preview early; "Follow-ups are NEW" scrutiny honest

- **Cons:** Instruction draft source not shown; Skill attachment reasoning missing; "Addressed by DT-012 DONE" state machine unclear; Type selector no guidance; No "combine findings into one task" detection; No follow-up task versioning

- **What I would want (for AI + user):** (1) Instruction draft source link (show Opus reasoning). (2) Skill attachment reasoning + rule link. (3) "Addressed" state machine explainer. (4) Type selector guidance. (5) Multi-finding batch detection. (6) Task versioning explainer.

---

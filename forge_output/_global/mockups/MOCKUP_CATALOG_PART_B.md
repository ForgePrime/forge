# Mockup catalog — Part B (objectives + DAG + orchestration)

## 03v2-create-objective.html

- **Function:** Form to create a new objective (will be O-008 on save) on a project. 5-section layout: Identity (title/priority/type/owner/scopes), Business context (≥100 chars, citations counted), Dependencies + live DAG preview with cycle check, KB focus inheritance from project defaults, and Key Results (numeric / descriptive / invalid example shown red). Enforces "objective without measurable KR is a wish" — Save disabled while any KR is unmeasurable. Right rail shows Summary, Cannot-save errors, "What Forge has NOT validated", and post-save behavior toggle.

- **Actions:**
  - Type Title (counter, ≤80 chars suggested)
  - Pick Priority (P0–P3), Type (analysis/planning/develop/documentation/draft), Owner (project members)
  - Add/remove scope chips, accept "suggested from KB" hints
  - Type Business context, click "🪄 LLM rewrite — make it more concrete ($0.03)"
  - Add/remove dependency chips → live DAG preview rerenders + cycle check
  - Toggle KB sources (5 checkboxes; SRC-009 recommended, SRC-001 down-weighted)
  - Add KR rows (numeric: target+unit+measurement command; descriptive: attestation source)
  - Remove KR · type-toggle per KR
  - Toggle "Auto-spawn first ANALYSIS task on O-008"
  - Cancel · Save as draft (no validation) · Create objective (disabled until KR-3 fixed)

- **Data shown:**
  - Header: "NEW OBJECTIVE", reserved ID "O-008", autonomy L2, budget $1.24/$10
  - Title input (53/80 chars), Priority/Type/Owner selects, 5 scope chips
  - Business context textarea (534/100 chars OK, "cites 2 sources")
  - Dependency chips (O-002, O-003) + live DAG: O-001 → O-002 → O-003 → O-008 (NEW, pulsing)
  - KB focus list: 5 sources with primary / down-weighted / recommended badges
  - KR-1 numeric (100% capture rate, pytest measurement command), KR-2 descriptive (auditor attestation), KR-3 invalid (rose, "Audit log feels solid")
  - Right rail: Summary card (emerald), Cannot-save panel (rose, lists KR-3), "What Forge has NOT validated" panel (amber, 5 bullets), "What happens after save" panel
  - Bottom scrutiny banner: "Objective without a MEASURABLE KR is a wish"
  - AI sidebar hint: page.id, draft.depends_on, suggestion chips

- **Linked mockups:**
  - Inbound: 03v2-objectives-dag.html ("+ Objective" button), 01-dashboard.html (new project flow)
  - Outbound: 03v2-objectives-dag.html (Cancel / after Save), 09-objective-detail.html?id=O-008 (after create), 16-ai-sidebar.html (sidebar suggestions)

- **Pros:**
  - "Wish vs measurable KR" rule enforced at the input layer, not as a post-hoc warning
  - Live DAG preview shows where the new objective fits before it exists
  - 3-row KR demo (numeric / descriptive / invalid) is self-teaching
  - Right rail co-locates summary + blocking errors + scrutiny in one column
  - Cycle check is structural and immediate
  - Save button has tooltip explaining exactly why it's disabled

- **Cons:**
  - LLM rewrite of business context costs $0.03 with no preview/diff
  - KB focus inheritance shown but no way to set per-task overrides from here
  - "Suggested from project KB" scopes are inline placeholder text — not interactive chips
  - Dependency picker is plain text input ("start typing") — no visible search results state
  - KR-3 invalid example is hard-coded for teaching; no way to dismiss after first time
  - Owner dropdown limited to 3 hard-coded members; no invite flow
  - "Auto-spawn analysis" defaults checked but cost not shown until later

- **What I would want (for AI + user):**
  - Diff view for "🪄 LLM rewrite" with accept/reject per paragraph
  - Inline KR scaffold generator: "🪄 propose 3 KRs from business context" with cost
  - Show downstream blast radius if dependencies are added (which objectives will be unblocked / blocked)
  - Persist a "stop showing example KR-3" preference per user
  - Add `data-objective-status="DRAFT"` and `data-kr-validity` attributes for AI sidebar reasoning
  - Pre-flight test for KR-1 measurement command (does the test path or alembic command resolve?)

---

## 03v2-objectives-dag.html

- **Function:** Project-level objectives view (DAG mode, with List/Kanban/Timeline alternates). Renders 4 objective nodes (O-001 ANALYSIS ACHIEVED, O-002 PLANNING BLOCKED, O-003 DEVELOP WAITING, O-004 DRAFT) connected by SVG arrows; amber dashed edge labeled "blocked: 2 ambiguities" between O-002 and O-003. Top strip aggregates ambiguity count across project with "Resolve all" deeplink. Bottom: educational strip explaining the 4 task types (ANALYSIS / PLANNING / DEVELOP / DOC) with role names, AC examples, and the shared schema.

- **Actions:**
  - Switch view: DAG · List · Kanban · Timeline
  - Click "+ Analysis task" / "+ Objective" toolbar buttons
  - Click "Resolve all →" on ambiguity strip
  - Click objective node → drills to 09-objective-detail.html
  - Click "→ Resolve" or "+ Planning task" inline on O-002 card
  - Click "Show all" on the O-001 sub-tasks panel
  - Click sub-task chip → task detail

- **Data shown:**
  - Tab nav: Knowledge Base · 7 / Objectives · 3 / Tasks · 14 / Activity / Reports
  - Ambiguity strip: "3 ambiguities block objective planning · surfaced by AT-001, AT-002"
  - DAG canvas (640px): 4 nodes, 3 arrows, legend (4 colors + solid/dashed), per-node status badges, BLOCKED reason text
  - O-001 sub-tasks expanded grid: AT-001..AT-004 with DONE badges, AT-003 raised 3 ambiguities (honest reporting)
  - Educational strip: 4 task types × {role, description, AC examples}, "All 4 share: AC, gates, scenarios, challenger, re-open, DAG, mode"

- **Linked mockups:**
  - Inbound: 02v2-project-kb.html (tab nav), 09-objective-detail.html (back-nav crumb), 16-ai-sidebar.html (entity context)
  - Outbound: 09-objective-detail.html (per node click), 03-project-post-analyze.html (Resolve all), 03v2-create-objective.html (+ Objective), 07-new-task.html (+ Analysis task), 02v2-project-kb.html (tab)

- **Pros:**
  - Color-codes the 4 task types consistently across project (blue/purple/emerald/slate)
  - Single ambiguity strip aggregates project-level blockers into one CTA
  - "Blocked: 2 ambiguities" labeled on the actual edge (not a separate panel) — the choke point is visible in the graph
  - Dashed border + opacity on DRAFT/IDEATED objectives signals "not yet active"
  - Sub-tasks panel shows AT-003 "raised 3 ambiguities" framed as a successful analysis outcome
  - Educational strip is on-canvas, not hidden in docs

- **Cons:**
  - DAG nodes are absolute-positioned (top/left pixel values) — won't reflow on smaller screens or with more objectives
  - Only 4 objectives shown; no zoom/pan/cluster for 20+ objective projects
  - View switcher tabs (List/Kanban/Timeline) are inert — only DAG is wired
  - Sub-tasks panel only renders for O-001; no per-objective expand state
  - Edge label "blocked: 2 ambiguities" is text positioned manually on the SVG (will overlap on layout change)
  - No keyboard navigation between nodes
  - No filtering by type/status/owner

- **What I would want (for AI + user):**
  - Auto-layout (dagre/elk) so the DAG scales beyond 4 nodes
  - Hover tooltip on edges showing the actual blocking decision IDs
  - Filter chips: "Show only BLOCKED" / "Show only ANALYSIS" / "Hide DRAFT"
  - Mini-map for large DAGs
  - Right-click context menu on nodes: "Add task here", "Edit dependencies", "Re-open", "Open in sidebar"
  - `data-objective-id` + `data-status` on each node so AI sidebar can reason about positions

---

## 09-objective-detail.html

- **Function:** Heart of the system — the primary work surface for a single objective (O-002 BLOCKED). Three-column layout: KB sources + DAG neighbors (left), description + ambiguities + AC + scenarios + challenger config (middle), 4 task-type-create buttons + tasks-on-objective list + activity feed (right). Header shows status, depends-on/blocks badges, 4-stat strip (progress / tasks / ambiguities / cost). Big amber "Scrutiny debt" strip warns about 4 recent answers (3 unedited), 2 open ambiguities, 1 unsourced AC, 0 captured failure modes — with "Continue anyway" requiring explicit acknowledgment.

- **Actions:**
  - Edit / Re-open objective (header buttons)
  - "Acknowledge debt (log reason)" / "Continue anyway" on scrutiny strip
  - Toggle KB source checkboxes (5) · Manage link
  - Click DAG neighbor links (depends-on O-001, blocks O-003 / O-005)
  - Edit / "🪄 Ask LLM to expand" description
  - Click "Resolve all →" on ambiguities; "Answer →" per Q (Q-007 HIGH, Q-008 MEDIUM); see 4 resolved
  - "🪄 Regenerate from sources" / "+ Add manually" on AC list
  - "+ Add scenario" on test scenarios card
  - 4 task-type buttons in "Ask Forge to..." panel (Analysis / Planning / Develop / Doc); type-pick fallback
  - Click any task in the right-side list

- **Data shown:**
  - Header: O-002 mono ID, "⏸ BLOCKED", depends-on/blocks chips, 4-stat strip ($1.24 cost so far, 2/5 KR met)
  - Scrutiny debt strip (amber) with 4 sub-cards: 4 recent answers (3 unedited), 2 ambiguities open, 1 unsourced AC, 0 failure modes captured
  - Left: 5 KB sources (SRC-005 excluded), DAG depends-on (O-001 ✓ ACHIEVED), blocks (O-003, O-005 waiting)
  - Middle: description with SRC-004 attribution pills + amber user note; 2 open Q's (Q-007 HIGH source-conflict, Q-008 MEDIUM); 4 resolved Q list; 5 AC (AC-2 "needs Q-007" amber); 4 test scenarios (EDGE CASE / EDGE CASE / FAILURE MODE / SECURITY); 4 challenger checks
  - Right: 4 task-creation buttons (color-matched), 4 tasks-on-objective (AT-005 DONE, AT-006 PENDING re-run pulsing, PT-003 BLOCKED, DOC-001 IDEATED), activity feed (3m / 12m / 25m ago)

- **Linked mockups:**
  - Inbound: 03v2-objectives-dag.html (per node), 01-dashboard.html (project entry), 09-* sub-pages (back-nav)
  - Outbound: 09-answer-ambiguity.html (per Q), 09-add-ac.html, 09-add-scenario.html, 09-edit-challenger-checks.html, 09-edit-dependencies.html, 09-reopen-objective.html, 07-new-task.html (4 task-type buttons), 02v2-project-kb.html (Manage), 04-orchestrate-live.html (when AT-006 starts)

- **Pros:**
  - 3-column information density without overwhelming — left = navigation context, middle = thinking, right = action
  - Scrutiny debt strip is impossible to miss (amber, 4 measurable counters, two-button choice)
  - Description shows source pills inline (SRC-004 quoted as attribution) and separates user notes from LLM-drafted text
  - Ambiguities section shows resolved Q's compactly so audit trail is on-page
  - Test scenarios are first-class with kind badges (EDGE CASE / FAILURE MODE / SECURITY)
  - "Ask Forge to..." panel makes 4 task types discoverable without hidden menus
  - Activity feed gives recent-changes context

- **Cons:**
  - Three columns × 6+ cards each = a lot to scan; no collapse states
  - "Acknowledge debt (log reason)" doesn't show the form — implied modal but unwired
  - Scrutiny debt cards "review / answer / verify or remove / add" links all point to "#" placeholders
  - KB sources panel is a checkbox list but unclear when changes save (no Save button)
  - DAG neighbors mini-panel doesn't show edge type (hard / soft)
  - Description "🪄 Ask LLM to expand" has no cost preview
  - "Tasks on this objective (6)" header but only 4 listed
  - Right-side activity feed is small and easily missed

- **What I would want (for AI + user):**
  - Collapse/expand per card (Description / AC / Scenarios / Challenger config) with persisted state
  - Inline cost preview on every "🪄" button (LLM expand, AC regenerate, scenario suggest)
  - Live-update dot per task row when AT-006 starts running (link directly to 04-orchestrate-live.html?task=AT-006)
  - "Filter tasks" by type/status above the right list
  - Replace 4 Forge-task buttons with `data-action` attributes so AI sidebar can pre-fill and trigger them
  - Make scrutiny debt counters clickable into pre-filtered drilldowns
  - Inline edit of business context with autosave + diff preview
  - Show count badge on "DAG neighbors" link to highlight broken upstream

---

## 09-add-ac.html

- **Function:** Form to add or refine an acceptance criterion on O-002. Enforces source attribution: every AC must cite SRC-XXX or be explicitly marked INVENTED (which triggers scrutiny debt). 4 fields drive validation: AC text (≥20 chars, verifiable), scenario type (positive/negative/edge case/regression), verification method (test/command/manual with conditional inputs), source attribution (dropdown + quoted passage). Right column shows live preview of how the AC will appear in the objective view, validation status checklist, and a teaching example of what an INVENTED AC looks like. Optional 🪄 Regenerate from source button at top.

- **Actions:**
  - Type AC text in textarea (counter 108/300, hint about measurability)
  - Click "🪄 Regenerate from source" ($0.04, ~10s) — overwrites textarea with Claude rewrite
  - Pick scenario type radio (positive / negative / edge case / regression)
  - Pick verification method radio (test / command / manual) — conditionally shows test_path or command field
  - Pick source from dropdown (SRC-001..SRC-004 listed; SRC-005 disabled "excluded for this objective"; USER NOTE option; INVENTED option)
  - Paste supporting passage (optional but recommended) into mono italic textarea
  - Cancel · Save as draft · Save AC

- **Data shown:**
  - Header: O-002 ID, "5 ACs currently"
  - LLM assist callout (indigo): "Regenerate this AC from source · cost $0.04 · ~10s"
  - AC text textarea (108/300, "best ACs are measurable" hint)
  - Scenario type 4-card radio (positive selected emerald)
  - Verification method 3-card radio (test selected blue) + conditional "Test path" mono input + greyed "Command" placeholder
  - Source attribution panel (slate, bordered, label says required) with full source dropdown + quoted passage textarea
  - Right preview: "AC-6" rendered in objective-view style with verified-by mono path
  - Validation status: 5 emerald checkmarks
  - Hidden INVENTED warning panel (rose) for conditional render
  - Teaching panel (amber): "How unsourced ACs look" with example AC-5 INVENTED pill
  - Footer: "Will attach as: AC-6 on O-002 · verification: pytest"
  - AI sidebar hint: page.id, entity, suggestion chips

- **Linked mockups:**
  - Inbound: 09-objective-detail.html ("+ Add manually" / "🪄 Regenerate from sources"), 05v2-task-deliverable.html ("+ Add AC / scenario"), 16-ai-sidebar.html ("Add AC for X" suggestion)
  - Outbound: 09-objective-detail.html#ac-6 (Save), 09-objective-detail.html (Save as draft / Cancel)

- **Pros:**
  - Source attribution is the biggest, most visually weighted block — encodes the "no unsourced AC" rule into UI not just policy
  - Conditional verification fields (test path appears only when test selected) reduce cognitive load
  - Live preview matches the objective-view rendering exactly, so user sees future state
  - Validation status sidebar is always visible — user knows what's blocking save
  - Teaching panel showing INVENTED rendering primes user before they pick that option
  - Quoted passage is explicitly stored for drift detection on re-ingestion

- **Cons:**
  - "🪄 Regenerate from source" overwrites textarea with no diff or undo
  - SRC-005 disabled with no explanation link (just "excluded for this objective")
  - Source dropdown is single-select; can't cite multiple sources for one AC
  - Quoted passage textarea has no helper for fuzzy match or "find this in source" jump
  - INVENTED warning is in HTML but `hidden` — won't show until JS wires it
  - Scenario type and verification method radios both have 3-4 options with similar styling — easy to mis-click
  - No live duplicate-detection against existing AC-1..AC-5

- **What I would want (for AI + user):**
  - Multi-source attribution (chips, not single dropdown)
  - "Find passage" button: opens source preview with search pre-filled to AC text keywords
  - Diff view on 🪄 Regenerate (show before/after, accept per-line)
  - Live duplicate warning: "Looks similar to AC-2 (74% match) — refine instead?"
  - Test-path autocomplete from existing pytest collection
  - `data-source-status` and `data-validation-state` for AI sidebar context
  - Save shortcut Ctrl+Enter when validation green

---

## 09-add-scenario.html

- **Function:** Form to add a non-happy-path test scenario to O-002. 4-kind picker (EDGE CASE / FAILURE MODE / SECURITY / REGRESSION), description (≥20 chars, becomes challenger claim), expected behavior (verifiable), optional link to existing AC (multi-select), and "why this matters" rationale note. Right column shows coverage preview (4 horizontal bars per kind, with current count + "new" indicator) and a rose "What I did NOT add" gap callout flagging missing kinds (e.g., REGRESSION at 0, no compliance security despite HIPAA). Top callout offers "🪄 Suggest 3 scenarios" ($0.08, ~25s).

- **Actions:**
  - Click "🪄 Suggest 3 scenarios" — Claude reads O-002 + 4 sources + resolved ambiguities
  - Pick kind radio (EDGE CASE / FAILURE MODE / SECURITY / REGRESSION) — 4-card layout
  - Type description (counter 24/300)
  - Type expected behavior (becomes challenger verification claim)
  - Toggle linked AC checkboxes (AC-2 pre-checked, AC-4, AC-5)
  - Type "why this matters" note (optional)
  - Cancel · Save as draft · Add scenario

- **Data shown:**
  - Header: O-002, BLOCKED status
  - LLM assist callout: $0.08 / ~25s
  - 4-card kind picker (EDGE CASE selected, rose; others slate)
  - Description textarea with placeholder example
  - Expected behavior textarea ("becomes part of challenger's verification claims")
  - Linked AC list: AC-2 (with "needs Q-007" amber pill), AC-4, AC-5
  - "Why this matters" note textarea
  - Coverage preview right card: 4 bars (EDGE CASE 60% "2 + new", FAILURE 33% "1", SECURITY 33% "1", REGRESSION 0% "0")
  - Gap callout (rose): "no REGRESSION scenarios, no load-related failure, no compliance-specific security (despite HIPAA scope)"
  - Footer: "Will attach to: O-002 · linked AC: AC-2"
  - AI sidebar hint: page.id, suggestion chips

- **Linked mockups:**
  - Inbound: 09-objective-detail.html ("+ Add scenario"), 05v2-task-deliverable.html ("+ Add scenario I realized is missing"), 16-ai-sidebar.html (/generate-scenarios)
  - Outbound: 09-objective-detail.html#scenarios (Add — new scenario highlighted 3s), 09-objective-detail.html (Save as draft / Cancel)

- **Pros:**
  - Kind picker has 4 distinct visual treatments and short examples per kind
  - Coverage preview gives immediate visual feedback of where the new scenario fits
  - Gap callout is rule-based (HIPAA scope → security recommended) and project-aware
  - Expected behavior field is explicitly framed as "becomes challenger claim" — wires intent to downstream effect
  - Linked AC multi-select connects scenarios to AC verification coverage
  - 🪄 Suggest 3 button respects existing scenarios (won't duplicate)

- **Cons:**
  - No way to clone an existing scenario as a starting template
  - Coverage preview hard-codes 4 kinds; no per-objective custom kinds
  - Char counter shows "24/300" but description visibly has ~110 chars (counter is wrong)
  - Linked AC list shows only 3 ACs; needs scrolling/search if 10+ ACs
  - "Why this matters" is optional and unlabeled as required for high-severity scenarios
  - Gap callout is static text; doesn't update based on draft kind selection
  - Save as draft semantics ("not promoted to challenger until promoted") not visually distinguished from Add

- **What I would want (for AI + user):**
  - Cost preview per "🪄 Suggest 3 scenarios" with token estimate based on objective+source size
  - "Clone from S-007" button to seed form from an existing scenario
  - Live coverage preview that updates with current draft kind selected
  - Required-tag warning if SECURITY kind without compliance scope link
  - Inline AC search instead of fixed 3-row list
  - Promote-from-draft action shown next to Save as draft
  - `data-scenario-kind` + `data-coverage-gap` for AI sidebar reasoning

---

## 09-answer-ambiguity.html

- **Function:** Resolve a HIGH-severity ambiguity (Q-007: share legacy DB or migrate separately) flagged by analysis task AT-005. Three-column layout: source conflict excerpts on the left (SRC-001 §4.2 vs SRC-002 /migration-plan#db with quoted passages, "DIRECT CONTRADICTION" banner, related resolved Q's), four answer options in the middle (Claude-recommended A with full reasoning + confidence, alternatives B/C extracted from sources, custom free-text, defer with reason ≥50 chars), and impact preview on the right (per-option downstream graph: which AC unblock, which tasks spawn, cost, time). Bottom: rose "What I did NOT check" scope-limit list (6 specific gaps). Footer offers Save-only or Save+re-analyze ($0.12).

- **Actions:**
  - Read SRC-001 + SRC-002 conflicting excerpts; click "Open side-by-side ↗"
  - Read related resolved Q-006, Q-003 for context
  - Pick answer radio (option A pre-selected as Claude rec; B from SRC-001, C hybrid synth, custom free-text)
  - Or check defer toggle and type ≥50-char reason
  - Type custom answer in free-text option (re-analyzed against SRC-004 hard constraints before commit)
  - Cancel · Save answer only (no re-analyze) · Save + trigger re-analysis ($0.12)
  - AI sidebar slash commands: /cross-check Q-007, etc.

- **Data shown:**
  - Header: Q-007 mono, HIGH badge, "blocks AC-2, AC-3 · spawned from AT-005", "SOURCE CONFLICT · SRC-001 vs SRC-002" badge
  - "Why this matters" amber callout — concrete impact (≈3 vs ≈6 develop tasks, blocks PT-003)
  - Left column: SRC-001 §4.2 excerpt (blue, italic blockquote with yellow-highlighted contradiction phrase, chunk metadata + last updated 2025-09); rose "DIRECT CONTRADICTION" divider; SRC-002 excerpt (purple, last updated 2026-02 by client architect); "Other sources Claude consulted" with SRC-003/004/005 notes; "Related resolved decisions" Q-006 → PostgreSQL 16, Q-003 → on-prem
  - Center column: 4 answer options, A = amber/recommended with full reasoning paragraph + medium-high confidence + scope caveat; B alternative with task-count tradeoff; C hybrid synth from SRC-003; D custom free-text textarea; defer panel with reason textarea
  - Right column: 4 impact cards (A/B/C/Defer) each with bullet list of unblocks/spawns/cost; "Who downstream reads this answer" links O-002 / PT-003 / O-003 / DOC-001
  - Scrutiny counterweight (rose, full-width): 6 specific things Claude did not check before recommending A
  - Footer: "Selected: option A (Claude's recommendation)" + 3 buttons
  - AI sidebar hint: entity=Q-007, suggestion chips

- **Linked mockups:**
  - Inbound: 09-objective-detail.html ("Answer →" per Q), 16-ai-sidebar.html ("Answer Q-007" suggestion), 02v2-project-kb.html (ambiguity badge on SRC), 03v2-objectives-dag.html (Resolve all)
  - Outbound: 09-objective-detail.html#ac-2 (Save + re-analyze with AT-006 pending pill), 09-objective-detail.html (Save only / Cancel), 02v2-source-preview.html (Open side-by-side)

- **Pros:**
  - Source conflict visualized literally (two coloured blockquotes + DIRECT CONTRADICTION banner) — user sees what Forge saw
  - Highlighted phrases inside quotes show the exact contradiction substring
  - Recommended answer comes with full reasoning + explicit confidence ("medium-high. Reasoned, not proven")
  - Alternatives B/C are explicitly tagged as source-extracted (B from SRC-001, C from SRC-003) — no invented options
  - Impact preview is deterministic (graph walk), not LLM-guessed
  - Scrutiny counterweight is concrete (6 specific gaps) and links to AI sidebar /cross-check command
  - Defer is a first-class option with reason requirement (audit trail)
  - Cost is shown on the action button ($0.12 for re-analysis)

- **Cons:**
  - Long page (3 dense columns + bottom scrutiny + footer); on smaller monitors requires scroll-then-decide
  - Custom free-text option has no live "checking against SRC-004" indicator until commit
  - "Open side-by-side ↗" is a forward-reference link with unclear destination
  - Defer reason 50-char minimum is in helper text but no live counter
  - Impact preview shows task counts (~6) but not human-readable cost / time
  - Scope-limit bullets are clickable in spirit only (not wired)
  - No way to flag "this Q is wrongly framed — re-ask analysis to reformulate"

- **What I would want (for AI + user):**
  - Live SRC-004 hard-constraint check on free-text answer before Save (preview conflicts inline)
  - Side-by-side source viewer modal launched from "Open side-by-side ↗"
  - Per-bullet "run check" button on scope-limit list — runs the AI sidebar /cross-check inline
  - Defer reason live counter + autosave draft
  - Impact preview adds human-time estimate per option (e.g. "+2 days") when planning data exists
  - "Reframe question" action that creates AT-007 to re-ask
  - `data-decision-id`, `data-recommended-option`, `data-confidence` for AI sidebar
  - "Compare options" toggle showing all 4 impact bullets in one diff table

---

## 09-edit-challenger-checks.html

- **Function:** Per-objective challenger checks editor for O-002 — manages the rules injected into the challenger's Phase C prompt on every DEVELOP task under this objective. Lists 4 active checks (2 MANDATORY, 1 RECOMMENDED, 1 ADVISORY) with firing stats (e.g., "fired 6 times · 0 issues — low signal"). Add-new-check form with severity + applies-to-task-types matrix. "Suggest from scenarios" panel promotes existing scenarios into checks. Right column: live Phase C prompt-injection preview (terminal style), cost meter (+$0.06/task at 4 checks), summary card. Bottom scrutiny strip: 6 challenger-check tradeoffs (more checks ≠ more safety, mandatory blocks DONE, scenarios vs checks vs AC distinction).

- **Actions:**
  - Reorder checks · Import from O-003
  - Edit / Remove per check row (inline)
  - Type new check text (counter 145/300, "keep under 300 chars for prompt efficiency")
  - Pick severity (mandatory blocks DONE / recommended / advisory)
  - Toggle applies-to task-type checkboxes (develop default, bug, analysis, planning)
  - Click "🪄 Suggest check from scenarios" — opens indigo panel
  - Check scenarios (S-007 load test, S-009 rollback) to promote → batch PATCH
  - Add check button (commits inline)
  - "Done — back to objective" / "Reset to org defaults" (destructive modal)

- **Data shown:**
  - Header: O-002, "4 checks currently"
  - 4 check rows ordered by severity: MANDATORY (rose) #1 CDC writes gated, MANDATORY #2 HIPAA audit log entry, RECOMMENDED (amber) #3 SessionLocal pattern with low-signal warning, ADVISORY (slate) #4 Prometheus metric naming
  - Per row: severity badge, applies-to chip, firing stats ("fired 6 times · caught 2 issues"), check text, edit/remove buttons
  - Add new check form: textarea (145 chars), severity select, task types checkboxes, Add button
  - Suggest-from-scenarios panel (indigo): 2 promotable scenarios (S-007, S-009)
  - Phase C prompt injection preview: terminal-style render with color-coded severity tags, instruction footer ("For each check above, you MUST: state whether it applies, cite evidence or flag missing")
  - Cost panel (amber): 4 checks +380 tokens +$0.06/task; tradeoff explanation
  - Summary (emerald): 4 active, 50% hit rate, 1 low-signal flagged for downgrade
  - Scrutiny strip: 6 tradeoffs (attention finite, mandatory blocks, advisory ignored, checks ≠ tests, scenarios vs checks vs AC, removal preserves history)
  - Footer: "4 checks · +$0.06/challenge · applies to next DEVELOP task"
  - AI sidebar suggestions

- **Linked mockups:**
  - Inbound: 09-objective-detail.html (challenger config card)
  - Outbound: 09-objective-detail.html (Done back-nav), 12-hooks-tab.html (companion gates link in scrutiny), 16-preview-apply-modal.html (Reset to org defaults destructive)

- **Pros:**
  - Firing stats per check enable evidence-based pruning ("low signal: 0 catches in 6 firings")
  - Live prompt-injection preview de-mystifies what Opus sees
  - Cost panel quantifies the bloat tradeoff with concrete tokens + dollars
  - Suggest-from-scenarios closes the loop (scenario → standing check) without re-typing
  - Severity legend enforces 3 distinct tiers (mandatory blocks DONE, recommended surfaces, advisory nits)
  - Scrutiny strip teaches the "scenarios vs checks vs AC" distinction explicitly
  - "Removing a check does NOT delete past challenger reports" preserves audit trail

- **Cons:**
  - Inline PATCH on edits/removes is silent — no save confirmation or undo
  - "Reorder" and "Import from O-003" buttons are inert (no handler shown)
  - Suggest-from-scenarios panel is always visible (not behind the wand button), confusing the entry point
  - 145/300 char counter is correct but no visual warning at 250+
  - Task-type matrix is 4 unconnected checkboxes; no "apply to all" / "develop only" preset
  - "Reset to org defaults" is destructive but only flagged via title attribute
  - Prompt preview is read-only; can't test against a real task
  - Hit rate "50%" computation not explained (3 caught / 6 fired ?)

- **What I would want (for AI + user):**
  - Undo toast for inline edit/remove with 5s window
  - "Test this check against DT-005" button — runs prompt against a recent task and shows what challenger would say
  - Smart presets for applies-to (e.g., "all develop tasks", "code-changing only")
  - Per-check evidence detail: click "fired 6 times · caught 2 issues" → list the 6 task IDs
  - Wand button properly gates Suggest panel (collapse by default, click to expand)
  - Auto-flag "consider downgrading" if hit rate < 20% over last 10 firings
  - `data-check-id` + `data-severity` + `data-hit-rate` for AI sidebar reasoning
  - "Promote to org default" action to escalate a project-specific check

---

## 09-edit-dependencies.html

- **Function:** Dependency editor for O-002 (PLANNING). Shows centered DAG visualization (3 columns: depends-on / O-002 highlighted / blocks read-only). Below: editable depends-on list with hard/soft toggle per row, an "Add dependency" form with cycle-prevention dropdown (cycles disabled with explanation), and read-only blocks list with "edit X deps →" links to push edits at the source. Right column: impact preview (hypotheticals "if you removed O-001" / "if you converted O-006 to soft-dep"). Bottom scrutiny: 6 dependency tradeoffs (dep doesn't add work, hides assumptions, soft-deps not enforced, structural vs semantic cycles, no notification, blocks-list is computed).

- **Actions:**
  - Click "View full DAG" → 03v2-objectives-dag.html
  - Per depends-on row: toggle hard/soft, click Remove (PATCH)
  - Pick upstream from "Add dependency" select (some options disabled w/ cycle reason); pick hard/soft radio; Add button
  - Click "edit X deps →" on each downstream block to navigate to that objective's edit-deps page
  - Done back-nav
  - AI sidebar suggestions

- **Data shown:**
  - Header: O-002, "2 deps · blocks 3 objectives"
  - DAG visualization: 5-column grid (upstream O-001, O-006 emerald | arrows | O-002 amber highlighted | arrows | downstream O-003 ACTIVE blue, O-005 BLOCKED, O-007 BLOCKED soft); status legend
  - Depends-on rows (editable): O-001 ACHIEVED (hard toggle red), O-006 ACHIEVED (hard); per row: rationale ("hard-dep: O-002 cannot start tasks until O-001 is ACHIEVED")
  - Add dependency: select with O-003/O-004/O-005 (disabled cycle)/O-007 options; cycle warning panel ("⚠ Cycle would form: O-002 → O-005 → O-002"); hard/soft radios
  - Blocks list (read-only): O-003 hard / O-005 hard / O-007 soft, each with "edit X deps →" link
  - Impact preview (amber): hypothetical "If you removed O-001" / "If you converted O-006 to soft-dep" with bulleted consequences
  - Scrutiny strip: 6 dependency-edit tradeoffs
  - Footer: "Edits save inline · cycle check runs server-side on every add"
  - AI sidebar suggestions

- **Linked mockups:**
  - Inbound: 09-objective-detail.html (DAG neighbors panel "edit deps")
  - Outbound: 09-objective-detail.html (Done), 03v2-objectives-dag.html (View full DAG), 09-edit-dependencies.html (other objective focus per "edit X deps")

- **Pros:**
  - Centered DAG visualization shows the focus objective with both directions visible
  - Hard/soft toggle is visually distinct (rose/grey pill set) and explained per row
  - Cycle prevention is structural — disabled options in dropdown with explanatory panel
  - Read-only blocks list with deep links forces single-source-of-truth (edit downstream's deps directly)
  - Impact preview is hypothetical (deterministic graph walk), not require-commit-to-see
  - Scrutiny strip distinguishes structural cycles from semantic ("circular reasoning is not caught")
  - Inline PATCH semantics ("no Save all") makes intent and persistence explicit

- **Cons:**
  - DAG visualization uses CSS grid with manual arrow chars — not visually compelling for >3 objectives per column
  - Hard/soft toggle has no documentation link explaining the difference
  - Add-dependency dropdown shows all eligible objectives (4) but no search/filter
  - Cycle warning panel is hard-coded for the O-005 cycle example; behavior with 0 cycles unclear
  - Impact preview is purely hypothetical; doesn't preview the actual change being staged
  - "edit X deps →" links create navigation chains but no breadcrumb of "where I came from"
  - No notification setting when adding a dep that affects another owner

- **What I would want (for AI + user):**
  - Real DAG render using a graph library (interactive zoom/pan)
  - Tooltip + docs link on hard/soft pills explaining "hard = blocking, soft = ordering hint"
  - Filterable add-dependency picker with search + status filter
  - "Preview this change" action: show before/after DAG diff before commit
  - Optional notification toggle: "Email O-001's owner about this change"
  - Breadcrumb chain across multi-objective edits
  - `data-dep-kind` + `data-cycle-detected` for AI sidebar reasoning
  - "Convert all hard-deps to soft-deps where safe" suggestion based on schedule slack

---

## 09-reopen-objective.html

- **Function:** Re-open form for an ACHIEVED objective (O-002, achieved 3 days ago) when later evidence shows a gap. Big gap-note textarea (≥50 chars, audit requirement) where user explains what didn't work + what to improve. History preservation panel shows what stays (15 tasks DONE, 3 ADRs, 8 closed decisions, 2 scenarios, 42 commits, KR snapshot). Auto-spawn analysis task toggle with full AT-011 instruction preview (gap note quoted, already-built artifacts listed to skip, focus output bullets). Right column: Summary, Blast radius (rose: O-005 re-blocked, amber: KR-1 flips IN_PROGRESS, emerald: nothing waiting), Recent re-opens. Bottom scrutiny: 6 things re-opening does NOT do (revert code, delete docs, notify stakeholders, refund LLM cost, invalidate share link, re-evaluate ADR validity).

- **Actions:**
  - Type gap note (≥50 chars, "🪄 LLM structure this as gap-analysis $0.04")
  - Toggle "Start re-analysis task after re-open" checkbox (default checked)
  - Read AT-011 instruction preview
  - Cancel · "Re-open without analysis task" · "Re-open with notes" (amber primary)
  - AI sidebar slash commands

- **Data shown:**
  - Header: O-002, "currently ACHIEVED · 3 days ago · 2026-04-15 11:08 UTC"
  - Gap note textarea pre-filled with rich example (826/50 chars OK) — describes UAT discovery of CDC lag, 3 numbered fix priorities, history-to-preserve note
  - LLM structure button ($0.04)
  - History preservation 2-col grid: ✓ Preserved (15 tasks, 3 ADRs, 8 decisions, 2 scenarios, 42 commits, KR snapshot) | ⟳ Re-evaluated (KR-1 → IN_PROGRESS, status flip, challenger re-eval AC-2, gap note as analysis input, O-005 blocked again)
  - Auto-spawn checked card with cost ($0.18 / ~3 min)
  - AT-011 instruction preview in mono (task type, origin, full instruction template with gap-note quoted, artifact skip list, focus bullets)
  - Right Summary (emerald): action, status flip, gap note length, est cost, "Reversible: yes within 24h"
  - Blast radius (3 cards): O-005 re-blocked rose / KR-1 flips amber / nothing waiting emerald
  - Recent re-opens: O-004 2026-03-22 (auth model missed SSO), O-001 2026-02-11 (client added integrations), "Re-opens are normal"
  - Scrutiny strip: 6 things re-open does NOT do
  - Footer: "Re-opening O-002 with 826-char gap note + auto-spawning AT-011"
  - AI sidebar hints

- **Linked mockups:**
  - Inbound: 09-objective-detail.html (header "↶ Re-open" button)
  - Outbound: 09-objective-detail.html (Cancel / after Re-open with ACTIVE + AT-011 highlighted), 16-ai-sidebar.html (Draft AT-011 from gap note)

- **Pros:**
  - Gap note is required and ≥50 chars — forces real audit trail
  - Pre-filled example shows the level of detail expected (incident description + 3 fix priorities + preservation note)
  - History preservation is concrete and counts everything that stays
  - AT-011 instruction preview is full prompt — user sees exactly what Claude will read
  - Blast radius is specific (which objective re-blocks, which KR flips, what doesn't wait)
  - Recent re-opens normalizes the action ("Re-opens are normal")
  - Reversible-within-24h note reduces commitment anxiety
  - Scrutiny strip explicitly addresses misconceptions (no code revert, no notifications, no refund)

- **Cons:**
  - Pre-filled gap note hides the "blank state" experience; user might not realize they can edit
  - "🪄 LLM structure" rewrites textarea with no diff
  - "Re-open without analysis task" button has subtle styling and could be missed
  - Recent re-opens shows only 2 entries; no "view all"
  - 24h undo window is in helper text only — no countdown or undo entry point shown
  - Blast radius hard-codes 3 cards; no scrolling for 5+ downstream objectives
  - "Does not notify stakeholders" — no opt-in to notify
  - AT-011 instruction template is fixed — can't be customized before commit

- **What I would want (for AI + user):**
  - Diff view on "🪄 LLM structure" with accept/reject per paragraph
  - Optional notify checkbox per stakeholder (J. Patel, M. Chen) with template message
  - "Edit AT-011 instruction" button before re-open commits (would route through 07-new-task.html?task=AT-011)
  - Visible undo banner in 09-objective-detail.html for 24h post-reopen
  - Blast radius scrollable / collapsible
  - "Re-open similar to O-001" template loader from past re-opens
  - `data-reopen-count` + `data-blast-radius` for AI sidebar
  - Gap note categorization (incident type) for analytics across re-opens

---

## 04-orchestrate-live.html

- **Function:** Live execution view for a multi-task run (Run #4, 8 of 15 tasks done). Header has dual progress + budget bars with ETA. Two-column body: left "Currently executing" card showing 3-phase breakdown (Phase A done 84s, Phase B running, Phase C pending) with Phase A outcome (8/8 tests pass, +124 lines), AC progress checklist; right side has streaming console (slate-900, monospace, SSE-fed claude-sonnet-4-6 output with timestamps and color-coded log lines: read files, write files, pytest output, Phase B finding extraction). Bottom: task history table for this run (T-008 DONE, T-007 FAILED with inline Retry, T-006 DONE) with cost per task. Pause + Cancel buttons in header.

- **Actions:**
  - Pause / Cancel run (header)
  - Toggle Auto-scroll on console
  - Copy / Download log
  - Click inline "↻ Retry" on T-007 FAILED row
  - "View all 15 tasks →"
  - Click LIVE indicator / SSE endpoint (implied)

- **Data shown:**
  - Crumbs: warehouseflow / Run #4 RUNNING + LIVE pulse indicator
  - Header: "Run #4 — 8 of 15 tasks", started 4 min ago, objective O-001 User authentication
  - Progress bar: 3-segment (emerald 53% done, rose 7% failed, blue 7% pulse running) + "ETA ~8 min · 8 done · 1 failed · 6 pending"
  - Budget bar: $4.20 / $10.00 (42% used) + "est $3.80 remaining"
  - Current task card: T-009 "Add user profile edit endpoint", 3 phases (✓ A 84s, ⟳ B running, 3 pending C); Phase A outcome: 8/8 tests, Python/pytest 1.34s, +124 lines / 3 files; AC progress: 3 emerald checkmarks
  - Live console (380px, monospace): timestamped streaming log of Phase A start, Claude CLI invocation (model + temp), file reads/writes, pytest progress per test, all-pass summary, Phase B finding extraction (medium severity rate-limit), Phase B "scanning hidden assumptions" with cursor blink
  - Console footer: "lines: 342 · wps: 14 · stream: SSE · /runs/4/events"
  - Task history: T-008 DONE 1m 42s $0.45, T-007 FAILED 2/5 tests + Retry button $0.12, T-006 DONE 54s $0.28

- **Linked mockups:**
  - Inbound: 07-mode-selector.html (Start), 07-crafter-preview.html (Run with this prompt), 03v2-objectives-dag.html (per-task drill), 04-orchestrate-live.html (Retry from inline T-007), 09-objective-detail.html (when AT-006 starts)
  - Outbound: 05-task-deliverable.html / 05v2-task-deliverable.html (when current task completes), task detail (View all), 04-orchestrate-live.html?task=T-007 (Retry)

- **Pros:**
  - Phase A/B/C breakdown removes "what is it doing" mystery — verification is visible work
  - SSE-fed live console replaces polling silence; user sees Claude's actions in real time
  - Dual bars (progress + budget) co-locate the two questions users ask most
  - Inline Retry on FAILED rows means no navigation away from the run
  - Color-coded console lines (slate for system, slate-300 for actions, emerald for tests passed, amber for findings) speed scanning
  - Pause + Cancel are visible and explicit — user feels in control
  - Cost per task visible in history; ETA computed from running average

- **Cons:**
  - Console is 380px tall fixed — verbose tasks scroll off rapidly
  - Phase B "Scanning for hidden assumptions" cursor blink is visual but not informative (no actual progress)
  - Task history shows only 3 rows; no filter/sort/search for 15-task runs
  - No way to jump to FAILED tasks across the run
  - Pause semantics unclear (between tasks? mid-phase?)
  - Cancel is destructive but only flagged with rose styling (no confirmation modal shown)
  - Retry button on T-007 has no cost preview
  - LIVE indicator in nav is decorative; no link to SSE health/diagnostics

- **What I would want (for AI + user):**
  - Resizable console pane with persisted height
  - Phase B "thinking" pseudo-progress: list what specifically is being scanned (with timeout)
  - Confirmation modal on Cancel + on Retry with cost estimate
  - Task history filter chips (FAILED / DONE / running) + jump-to-failed shortcut
  - "Pause between tasks" vs "Pause immediately" toggle
  - `data-task-id` + `data-phase` + `data-stream-state` attrs so AI sidebar can summarize the run
  - Cost-cap soft warning when budget bar crosses 70% / 90% with auto-pause option
  - Per-task cost + ETA tooltip on history rows

---

## 16-ai-sidebar.html

- **Function:** The AI collaboration layer — a 440px-wide right-side panel pinned across pages (here on 09-objective-detail). Header injects context (page.id, entity, token count, active skills, recent actions). Capability contract collapsible lists what AI can/cannot do on this page (4 ✓ + 2 ✗). Contextual suggestion chips pulled from page state (e.g., "Why is Q-007 HIGH?", "Verify AC-5 source likely hallucinated"). Conversation area shows user @mention + /run-skill invocation, AI response with 3 collapsible tool-call traces (read_entity, grep_sources, run_skill), drafted AC-6/7/8 with source pills, and mandatory "What I did NOT check" scope-limit box. Action buttons under the AI suggestion (Remove AC-5 / Accept AC-6,7,8 / Refine / reject all). Autonomy-L2 note explains what would change at L3/L5. Input area with @mention + slash commands + cost preview.

- **Actions:**
  - Hide AI (button in nav)
  - Click history / settings (sidebar header)
  - Expand capability contract details
  - Click contextual suggestion chips ("Why is Q-007 HIGH?", "Verify AC-5 source", "Generate 3 failure modes", "Compare with O-001", "Reverse-trace AC-2 dep")
  - Type message in textarea, use @entity mention or /command slash
  - Click 📎 attach KB / 🧩 add skill / 🪄 plan-first toggles
  - Send (Ctrl+Enter), see "est cost: $0.04"
  - Action buttons under AI message: "Remove AC-5 + log skill-leak" / "Accept AC-6, 7, 8 (preview first)" / "Refine with HIPAA scope narrowing" / "reject all"
  - Expand/collapse tool-call traces (read_entity, grep_sources, run_skill)
  - Slash command palette (visible)

- **Data shown:**
  - Page nav: O-002 crumbs, autonomy L2, budget $1.24/$10
  - Left: condensed objective view (header, ambiguities Q-007/Q-008, AC-1..AC-5 with source pills + AC-5 INVENTED rose)
  - Right sidebar header (indigo): pulse dot, "AI sidebar", history/settings; "page: objective-detail · entity: O-002", "context injected: 1840/8000 tokens · op contract · 7 active skills · 12 recent actions"
  - Capability contract: 4 ✓ (answer ambiguities dry-run, generate scenarios, propose AC, start tasks with cost preview), 2 ✗ (close ACHIEVED, modify operational contract)
  - 5 suggestion chips
  - User message: "Check @AC-5 — seems unrelated. /run-skill OP-hipaa-auditor"
  - AI message header: "🤖 sonnet-4.6 · 14s · $0.06 · 3 tool calls"
  - 3 tool traces (collapsible, mono): read_entity AC-5 (text + source_attribution null), grep_sources "Excel" (only SRC-005 match), run_skill OP-hipaa-auditor
  - AI verdict + 3 drafted AC (AC-6/7/8) with source pills (SRC-003, SRC-003 + OP-hipaa, OP-hipaa scope knowledge)
  - Mandatory rose scope-limit box (3 things did NOT check)
  - 4 action buttons (Remove AC-5, Accept AC-6-8, Refine, reject all)
  - Autonomy-L2 note (amber, centered): "drafted but did NOT apply — at L3 could apply with rollback, at L5 also auto-run analysis re-pass"
  - Input area: textarea with @entity / /command hints, attach KB / add skill / plan-first toggles, "Ctrl+Enter send · est cost $0.04"
  - Slash dropdown preview: 6 slash commands (/find-ambiguity, /generate-scenarios, /reverse-trace, /replay, /run-skill, /cost-drill)

- **Linked mockups:**
  - Inbound: every page (sidebar is global). Specifically referenced from 09-* pages, 02v2-* pages, 04-orchestrate-live.html, 03v2-* pages
  - Outbound: deep-links to entity pages from suggestion clicks (e.g., 09-answer-ambiguity.html?q=Q-007), 11-skill-edit.html (run_skill trace), 02v2-source-preview.html (grep_sources), 16-preview-apply-modal.html (Accept AC-6,7,8 preview first)

- **Pros:**
  - Token-injection counter is exposed ("1840/8000 tokens") so user knows context cost
  - Capability contract is collapsible per page — explicit can/cannot list, no silent refusals
  - Contextual suggestions are pulled from page state, not generic chatbot openers
  - Every tool call is collapsible with raw input/output (no black box)
  - Mandatory scope-limit box at end of every AI response — skeptical frame enforced in prompt + UI
  - LLM-drafted ACs have source pills (SRC-003, OP-hipaa) traceable to their origin
  - Action buttons under the AI message ("Remove AC-5 + log skill-leak") encode autonomy-aware UX
  - Autonomy-L2 explanatory note teaches what L3/L5 would unlock — progressive onboarding
  - @mention + /command + plan-first toggles make power-user flows discoverable
  - Cost preview on send button before any LLM call

- **Cons:**
  - Sidebar is fixed 440px; on small monitors may crowd page content
  - Capability contract is per-page but no link to "see all my capabilities project-wide"
  - Suggestion chips limited to 5; no "more suggestions" expansion
  - Tool-call traces use `<details>` which doesn't support nested call hierarchies
  - Action buttons after AI suggestions are AI-prescribed; no user customization
  - Slash command preview list is static; no fuzzy search
  - "history" + "settings" buttons in header are inert
  - Input textarea has no syntax highlighting for @ / /
  - Conversation has no thread/branch concept — one linear log
  - No way to "pin" a key AI message for later reference

- **What I would want (for AI + user):**
  - Resizable sidebar with collapse to icon-only mode
  - Conversation branching ("explore alternative reasoning") with per-branch token cost
  - Full-text search across past sidebar history
  - Editable suggestion chips (user can save custom suggestions per page type)
  - Pin / star messages for later reference
  - Inline "explain this tool call" expansion linking to skill docs
  - Per-message "promote to decision" / "promote to knowledge note" actions
  - `data-page-id`, `data-entity-id`, `data-token-count`, `data-skill-list` on sidebar root for cross-page state
  - Cost-cap warning if estimated send pushes user over budget
  - Voice input + read-aloud for hands-free review

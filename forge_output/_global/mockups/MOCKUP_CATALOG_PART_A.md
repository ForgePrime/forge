# Mockup catalog — Part A (entry + KB)

## index.html

- **Function:** Landing page / design canvas hub for all mockups in the Forge UX system. Introduces the 27 mockups across 3 passes (9 Pass 1 + 13 Pass 2 + 5 Pass 3) and establishes the design contract: Forge is skeptical, not reassuring. Shows paradigm shifts from v1 (SOW-driven) to v2 (Initiative + KB-driven) in a comparison table.

- **Actions:**
  - Click on mockup tiles (15+ items) → opens each mockup in new tab
  - Click flow.html link → navigate to user flow diagram
  - Click walkthrough.md link → read 10 detailed scenarios
  - Click FORGE_30_IMPROVEMENTS.md → strategic improvements doc
  - Read paradigm shift table (compare v1 vs v2)

- **Data shown:**
  - Paradigm shift table: 11 rows (Project origin, Knowledge input, Analysis/Planning, Objectives relation, Tasks relation, Execution model, Ambiguity, Objective DONE, Acceptance criteria, Challenger, Test scenarios)
  - Pass 1/2/3 status: "9 of ~52 mockups", "22 of ~52 mockups", "27 of ~52 mockups"
  - Design contract banner (red, bold): "Forge is skeptical, not reassuring"
  - 10-scenario walkthrough summary
  - 27+ mockup tiles with embedded iframes, titles, descriptions, step badges

- **Linked mockups:**
  - Inbound: none (entry point)
  - Outbound: flow.html, walkthrough.md, all 27 Pass 1/2/3 mockups via tile links and iframes

- **Pros:**
  - Taxonomy is crystal-clear: grouped by Pass + function (entry, KB, objectives, tasks, auditor)
  - Paradigm-shift table immediately corrects v1 assumptions
  - Embedded iframes show live thumbnails without context-switching
  - Design contract banner enforces skepticism from first view
  - Status badges (P1·1, P2·A1) create instant scannability

- **Cons:**
  - No search/filter for 27 mockups; scrolling alone is tedious
  - Walkthrough scenarios compressed; full narrative is in separate .md
  - Iframes always show default view, not the specific scenario described
  - No version history visible
  - No breadcrumb showing "you are viewing the index"

- **What I would want (for AI + user):**
  - Add `data-mockup-id` and `data-pass` attributes on tiles so AI sidebar can recommend "next logical mockup"
  - Support `?q=...&pass=...` query params for filtering
  - Expand walkthrough scenarios inline (expandable cards)
  - Store mockup version fingerprints in HTML comments so AI can detect stale views
  - Collapsed "Inbound/Outbound links" box per mockup for AI flow drilldowns

---

## flow.html

- **Function:** Visual swimlane diagram showing per-objective iterative lifecycle. Main spine: Project → KB → Objective → Analysis → Planning → Develop → Docs → Achieved. Three layers: ambiguity loop (above), happy path (center), failure/re-open (below). Persistent context layers banner explains what's injected into every screen.

- **Actions:**
  - Hover over nodes → border/shadow changes
  - Click on nodes → links to corresponding mockup
  - Read arrow legend + node legend

- **Data shown:**
  - 20+ labeled nodes (Project, KB, Objective, ANALYSIS, PLANNING, DEVELOP, Docs, Achieved, Ambiguity, etc.)
  - 3 swimlanes: ambiguity loop, main path (happy), failure / re-open loops
  - SVG arrows: green solid (forward), amber solid (user action), rose dashed (loops)
  - Legend tables: arrow meanings, node types
  - 7 invariants enforced by flow
  - Context layer cards: Project context, Page context, AI sidebar

- **Linked mockups:**
  - Inbound: index.html
  - Outbound: 01-dashboard.html, 02v2-project-kb.html, 09-objective-detail.html, 07-mode-selector.html, 03-project-post-analyze.html, 04-orchestrate-live.html, 10-post-exec-docs.html

- **Pros:**
  - Swimlane layout shows happy path + ambiguity handling + failure modes in parallel
  - Color-coded arrows + legend are self-documenting
  - Re-open loop shows reversibility
  - Invariants list summarizes key flow principles

- **Cons:**
  - SVG arrows are hard-coded positions; not responsive
  - Node clickability not visually hinted (no underline, no cursor change on hover)
  - "[manual] Continue bar" label ambiguous: button or automatic?
  - Failure loop path complex; unclear what triggers each branch
  - No timing estimates for each stage

- **What I would want (for AI + user):**
  - Add `<title>` attributes on SVG nodes for hover tooltips
  - Embed timeline estimates: "Analysis: 30-60s", "Planning: 5 min", "Develop: 10-60 min"
  - Add "Current location" indicator showing where user is on flow
  - Label failure/re-open loops with severity
  - Add `data-mockup-id` on nodes so AI can show "you are here" + suggest next steps
  - Collapse/expand sections (e.g., hide failure loop until needed)

---

## 01-dashboard.html

- **Function:** Org-level projects landing page. Shows 4 projects (RUNNING, NEEDS YOU, DONE, EMPTY) with progress bars, cost tracking, and audit queue (scrutiny debt: unaudited approvals, manual scenarios unrun, findings dismissed, stale analyses). Cross-project activity feed at bottom.

- **Actions:**
  - Click project card → navigate to project detail
  - Click audit-queue cards → filter to category (implied)
  - Global search ⌘K → fuzzy search projects/tasks/findings
  - "+ New project" button → create wizard
  - View report / Share link → 10-post-exec-docs.html

- **Data shown:**
  - Project grid (3 columns): name, description, status badge, progress bars (Tasks, KR), cost ($X/$Y), failed count, timestamp
  - Audit queue (4 cards): Unaudited approvals (3), Manual scenarios unrun (8), Findings dismissed (5), Stale analyses (2)
  - Activity feed (6 rows): cross-project events with severity dots
  - Budget bar (top-right): $8.45 / $20

- **Linked mockups:**
  - Inbound: none (root)
  - Outbound: 03-project-post-analyze.html, 02-project-empty.html, 10-post-exec-docs.html

- **Pros:**
  - 3 visual channels (border color, badge, content) make status instantly scannable
  - KR progress bar shows business progress, not just task count
  - Audit queue front-and-center
  - Cross-project activity feed prevents "stuck on one project" feeling
  - Cost tracking visible org-wide

- **Cons:**
  - Audit queue counts clickable but no destination mockup for filtered view
  - Status badges not explained (what triggers RUNNING vs DONE?)
  - No bulk actions
  - Budget bar small and easy to miss; no threshold color changes
  - Clicking NEEDS YOU bypasses KB, lands on decisions modal — ordering not explained

- **What I would want (for AI + user):**
  - Add `data-project-id` and `data-project-status` on cards for AI recommendations
  - Add velocity sparklines on progress bars
  - Make audit-queue cards clickable with pre-filter
  - Change budget bar color at 70% (amber), 90% (rose)
  - Show "Last action" timestamp per project
  - Inline tooltip on BLOCKED projects explaining blocker before navigation

---

## 02-project-empty.html

- **Function:** Onboarding for newly created project. Shows big welcome banner explaining upload-analyze-plan-execute pipeline with drop-zone for SOW. Pipeline preview shows 4 steps (1 active, 2–4 locked). "What happens next" strip sets time expectations.

- **Actions:**
  - Drag/drop or click to upload SOW file
  - "Use a sample project" link → pre-populate with example
  - "Start without SOW" link → skip analysis, create objectives manually
  - Auto-trigger analysis after upload (implied)

- **Data shown:**
  - Pipeline preview: 4-step swimlane
  - Welcome hero: title, 4-stage explanation, drop-zone
  - "What happens next" grid: STEP 1–4 with time estimates (10s, 30-60s, minutes, ongoing)
  - Escape hatches: sample project link, start-without-SOW link

- **Linked mockups:**
  - Inbound: 01-dashboard.html
  - Outbound: 02v2-project-kb.html (after upload), 03-project-post-analyze.html (after analysis)

- **Pros:**
  - Zero ambiguity on next step
  - Pipeline preview removes "is this the right tool?" anxiety
  - Time estimates prevent "is it broken?" panic
  - Escape hatches avoid gatekeeping
  - Locked steps clearly signal "not yet available"

- **Cons:**
  - v1 mental model persists: "upload SOW then analyze" implies one-shot, not ongoing KB
  - No explanation of SOW acronym
  - "What happens next" passive; doesn't explain user actions AFTER each step
  - No error handling shown (upload fails, parse fails)
  - "Start without SOW" link small and grey

- **What I would want (for AI + user):**
  - Add "What is a SOW?" tooltip
  - Change "What happens next" to actionable: "After step 2, you will review 3 objectives extracted"
  - Show accepted file types with icons
  - Display progress on pipeline after upload (step 1 green, step 2 animating)
  - Add keyboard shortcut hint
  - For "Start without SOW", show warning: "You'll create objectives manually — ~5 min per objective"

---

## 02v2-project-kb.html

- **Function:** Project KB management hub. Shows 4 source-type buttons (File, URL, Folder, Note) and list of 5 sources (SRC-001–005) with descriptions, metadata, and actions. SRC-005 flagged with ambiguity badge (conflicts with SRC-002). "Ready to start analysis?" CTA at bottom.

- **Actions:**
  - Click "+Add [type]" buttons → navigate to add-source forms
  - Click "Preview" on source → 02v2-source-preview.html
  - Click "Edit desc" → inline edit
  - Click "Remove" → destructive modal
  - Click "Re-crawl" on URL sources → POST /source/{id}/crawl
  - Click "Browse" on folder sources → file browser
  - Click "+ New Analysis task" → analysis wizard

- **Data shown:**
  - 5 source cards with: icon, SRC-ID, type badge, size/pages/tokens/status, title, description, metadata, action buttons
  - SRC-005 card: amber border, red "CONFLICTS" badge, red "→ Resolve ambiguity" link
  - Intro banner: explains KB purpose

- **Linked mockups:**
  - Inbound: 01-dashboard.html, 02-project-empty.html
  - Outbound: 02v2-add-source-{file,url,folder,note}.html, 02v2-source-preview.html, 09-objective-detail.html

- **Pros:**
  - 4 source types visible at a glance
  - Per-source descriptions visible and required
  - Last-read timestamps show KB is actually used
  - Ambiguity flagged at source level
  - Inline action buttons
  - Intro banner sets mental model

- **Cons:**
  - Descriptions long but not editable inline (clicking "Edit desc" behavior unclear)
  - "Referenced in 3 objectives" read-only; can't see which objectives
  - Re-crawl cost not visible upfront
  - No search/filter on 5+ sources
  - SRC-005 conflict badge doesn't link to conflict detail
  - No version history per source

- **What I would want (for AI + user):**
  - Add `data-source-id` and `data-source-type` on cards
  - Make descriptions clickable for inline expand/collapse
  - Show "Conflicts" count per source
  - "Referenced by" as clickable chips linking to objectives
  - Show re-crawl cost on hover
  - Add "Bulk actions" menu
  - Timeline slider showing KB growth as confidence metric

---

## 02v2-add-source-file.html

- **Function:** File upload form. User uploads PDF/DOCX/MD/TXT, provides description (≥30 chars), focus hint, scopes. Shows parse preview (400 chars), overlap detection against existing sources, and scrutiny section (what Forge did NOT check).

- **Actions:**
  - Drag file or click "browse" → multipart upload → auto-parse
  - Type description (required, ≥30 chars)
  - Click "🪄 Suggest from file content" → LLM call (~$0.01)
  - Add/remove scopes via chips
  - Read overlap detection and click "Preview ambiguity (Q-007)" → 09-answer-ambiguity.html
  - Toggle "Queue for analysis reuse"
  - Click "Add source only" OR "Add source + queue" → POST /source

- **Data shown:**
  - File upload status: name, size, MIME, timestamp
  - Parse result: extracted chars, tokens, embed cost
  - Description textarea with counter
  - Focus hint text input
  - Scopes (tag chips)
  - Extraction preview (400 chars, mono)
  - Overlap detection (amber panel)
  - Summary panel (right): type, size, tokens, chunks, scopes, conflicts, next ID
  - Scrutiny section (amber, 6 items): content quality, language, author authority, freshness, PII, copyright

- **Linked mockups:**
  - Inbound: 02v2-project-kb.html
  - Outbound: 02v2-project-kb.html, 09-answer-ambiguity.html (overlap preview)

- **Pros:**
  - Multi-step form mirrors natural workflow
  - Parse preview shows actual extraction quality
  - Overlap detection warns BEFORE commit
  - Scrutiny section enforces skepticism
  - Token cost visible at every step

- **Cons:**
  - "Suggest description" costs $0.01 and requires extra click (why not automatic?)
  - Overlap confidence score (0.82) unexplained
  - Conflict preview link is forward-reference to Q-007 (may not exist yet)
  - "Queue for analysis reuse" checkbox checked by default but hidden in sidebar
  - No progress indicator
  - If overlap found, no "merge" or "de-duplicate" option

- **What I would want (for AI + user):**
  - Auto-generate description on parse, show pre-filled but editable
  - Show confidence % on overlap with explanation
  - "Comparison view" button: side-by-side of conflicting chunks
  - Add `data-upload-token` so AI can track newly uploaded source
  - Suggest scopes based on file content
  - Progress indicator: "Step 1/5: File · Step 2/5: Description"

---

## 02v2-add-source-url.html

- **Function:** URL source creation with SharePoint OAuth auto-detection, crawl scope control (single/recursive/same-domain), include/exclude globs, re-crawl schedule (manual/daily/weekly), and dry-run preview. Auth scope narrowing info (read-only) and stale-content warning.

- **Actions:**
  - Enter URL → click "Test connect" → POST /source/url/test
  - Select auth type (None, Basic, Token, SharePoint OAuth auto-detected)
  - For SharePoint: click "Start OAuth →" → MS login → OAuth flow
  - Or paste existing token
  - Select crawl scope (single page, recursive depth, same-domain)
  - Edit include/exclude glob patterns
  - Select schedule (manual, daily, weekly)
  - Click "Dry-run all" → POST /source/url/dry-run
  - Click "Add source + run first crawl now"

- **Data shown:**
  - URL input + test-connect result (HTTP status, content-type, last-modified)
  - Auth type selector (4 options)
  - SharePoint OAuth panel: scopes, redirect URI, button + paste field
  - Crawl scope options: 3 radios, depth input
  - Include/exclude textareas
  - Crawl preview: first 3 URLs with word/token counts
  - robots.txt check
  - Cost projections: one-time embed, daily re-crawl, monthly
  - Auth scope narrowing panel: requested + NOT requested
  - Stale-content warning (rose)

- **Linked mockups:**
  - Inbound: 02v2-project-kb.html
  - Outbound: 02v2-project-kb.html

- **Pros:**
  - SharePoint OAuth auto-detection removes friction
  - Crawl scope options give fine control
  - Glob patterns with examples
  - robots.txt enforcement
  - Dry-run preview shows exactly which URLs would index
  - Auth scope narrowing builds trust

- **Cons:**
  - robots.txt check only warns; user can override with no consequence shown
  - Glob syntax not documented (assumes gitignore knowledge)
  - Schedule only presets (no custom cron)
  - "Test connect" and "Dry-run" are two separate buttons (unclear order)
  - If crawl preview shows 0 URLs, no error message
  - Stale-content warning scary but offers no mitigation

- **What I would want (for AI + user):**
  - Link on glob patterns: "Learn glob syntax"
  - "Test connect" should also check robots.txt (combine checks)
  - If 0 URLs match: red error banner with fix suggestions
  - Stale-content warning: add mitigation CTA ("webhook in Pass 4" or "daily crawl")
  - Add `data-auth-type` and `data-crawl-scope` for AI tracking
  - Show crawl history if re-adding

---

## 02v2-add-source-folder.html

- **Function:** Local/mounted folder registration. User specifies path, toggles recursive/symlinks/gitignore, provides include/exclude globs, sees sample preview (10 of 342 files), and metadata. Sensitive-file warnings (red section) alert if globs miss .env, .git, etc.

- **Actions:**
  - Enter path → click "Test access" → POST /source/folder/test
  - Toggle Recursive, Follow symlinks, Respect .gitignore
  - Edit include/exclude globs → sample preview updates
  - Select re-scan schedule
  - Type description, focus hint, scopes
  - Click "Add source + run first scan" OR "Add without scan"

- **Data shown:**
  - Path input + test-access result (accessible, file count, size, filesystem, mtime)
  - Scan toggles
  - Include/exclude textareas (pre-populated defaults)
  - Sample preview: 10 of 342 files with checkmarks, filenames, size, tokens
  - Summary: 342 matched, 2,076 excluded, ~118k tokens, ~$0.024 embed cost
  - Sensitive-file warning (red): "We will read every file matching your globs"
  - Examples: ".env files?", "AWS credentials?", "Customer dumps?"
  - Bottom note: "Add excludes now. Post-ingest removal requires re-embedding."
  - Scrutiny section: PII, licenses, binary detection, symlink loops, permissions

- **Linked mockups:**
  - Inbound: 02v2-project-kb.html
  - Outbound: 02v2-project-kb.html

- **Pros:**
  - Test access catches permission errors upfront
  - Sample preview shows exactly what's indexed
  - Gitignore respect by default
  - Pre-populated sensible defaults (/node_modules/, /.git/)
  - Sensitive-file warning proactive; names .env, .aws
  - "Post-ingest removal requires re-embedding" explains cost

- **Cons:**
  - No glob syntax documentation
  - Sample preview shows 10 of 342 but not paginated (can't audit all)
  - No "test for secrets" button (requires manual .env* additions)
  - "Respect .gitignore" assumes git repo
  - Symlink warning good, but no preview of symlink-reachable files
  - Daily re-scan cost shown but assumptions unclear

- **What I would want (for AI + user):**
  - Add "🔍 Scan for secrets" button (red) checking for .env, *.key, *.pem, .aws before confirm
  - Make sample preview paginated/scrollable
  - Tooltip on "Respect .gitignore"
  - Show ASCII folder tree preview (~5 levels)
  - Add `data-matched-file-count` so AI warns if too many files
  - Break down daily re-scan cost
  - Warn if .gitignore stale

---

## 02v2-add-source-note.html

- **Function:** Manual note creation (markdown editor). User writes note with title, category, content (markdown + side-by-side preview), "Describes" summary, and optional links to decisions/objectives. No external file — user content, zero LLM cost. Async embedding post-save. Scrutiny section emphasizes memory-as-source limitations.

- **Actions:**
  - Type title (required)
  - Select category (business-context, technical-context, domain-rules, meeting-notes, workaround, known-issue, policy)
  - Type markdown content; preview on right
  - Click formatting buttons (B, I, code, link, list)
  - Type "Describes" (required, ≥30 chars)
  - Search + add linked decisions and objectives (chips)
  - Add scopes (tags)
  - Click "Save note" OR "Save as draft"

- **Data shown:**
  - Title input (required)
  - Category dropdown (enum: 7 options)
  - Split editor: left textarea (markdown), right preview
  - "Describes" field with counter
  - Linked decisions and objectives: chip picker with search
  - Scopes (tag chips)
  - Summary panel (right): type, category, length, links, LLM cost ($0)
  - Scrutiny section (amber): "This note has no external source. Your memory is the source."

- **Linked mockups:**
  - Inbound: 02v2-project-kb.html
  - Outbound: 02v2-project-kb.html

- **Pros:**
  - Editor + preview side-by-side
  - "Describes" field explicit (≥30 chars) forces one-sentence summary
  - Category dropdown helps classification
  - Linked decisions/objectives create bidirectional context
  - Zero LLM cost (prominent)
  - Scrutiny section skeptical; encourages anchors, attendees, date

- **Cons:**
  - Markdown editor barebones (no tables, footnotes, embeds)
  - "Describes" same style as file/URL but notes often narrative
  - Linked decisions/objectives autocomplete not shown
  - No category defaults or smart suggestions from title
  - No duplicate-note detection (unlike file/URL sources)
  - Scopes generic; no note-specific defaults

- **What I would want (for AI + user):**
  - Add "🪄 Suggest category" button ($0) inferring from title
  - Support tables and footnotes in editor
  - Auto-suggest linked decisions: if user types "Q-007", show chip picker
  - Template dropdown: "Meeting notes", "Architecture rationale", "Constraint"
  - Warn in Scrutiny if "Describes" missing date/source anchor
  - Inline confirmation post-save with all linked entities

---

## 02v2-source-preview.html

- **Function:** Read post-extraction chunks of a source. User navigates via left panel (search within source, chunk navigator 1–38), reads current chunk in center (with metadata: anchor, boundary, embedding model, freshness), and sees citations on right (entities quoting this chunk with exact passage). Scrutiny section warns what preview does NOT show.

- **Actions:**
  - Search in left panel: enter query → BM25 + vector hybrid search
  - Click chunk in search results OR click chunk number to jump
  - Click prev/next to paginate
  - Click "View original ↗" → opens source URL/file in new tab
  - Click citation link (e.g., "O-002") → jump to objective detail
  - Click "Re-crawl now (~$0.005)" → POST /source/{id}/crawl
  - Click "Edit metadata + scopes" → 02v2-edit-source.html (Pass 4)
  - Click "View conflict with SRC-001" → 02v2-source-conflict-resolver.html (Pass 4)
  - Click "Archive source" → 16-preview-apply-modal

- **Data shown:**
  - Source metadata bar with 6-column summary
  - Left panel: search box, results, chunk navigator grid (1–38 buttons)
  - Center panel: chunk header, freshness ribbon, chunk body, chunk metadata (anchor, embedding model, boundary type, overlap)
  - Right panel: "Referenced by (chunk 4)" with citations (Q-007, O-002, DT-009, DOC-001) — entity type, status, quoted passage, timestamp
  - Source actions: Re-crawl, Edit metadata, Update focus hint, View conflict, Archive
  - Scrutiny strip (rose): "What this preview does NOT show you"

- **Linked mockups:**
  - Inbound: 02v2-project-kb.html
  - Outbound: 02v2-edit-source.html (Pass 4), 02v2-source-conflict-resolver.html (Pass 4), 16-preview-apply-modal, entity pages (citations)

- **Pros:**
  - Search within source is powerful for "show me all mentions of X"
  - Chunk navigator quick jumps
  - Freshness ribbon shows KB is current and used
  - Citations exact (quoted passages)
  - Post-extraction warning honest
  - "View original" lets user verify extraction quality

- **Cons:**
  - Search shows 3 matches but doesn't indicate total match count
  - Chunk navigator doesn't show which chunks match the search
  - Citation list limited to this chunk; can't see all citations to source
  - "View conflict" link goes to unbuilt mockup
  - Re-crawl action costs $0.005 but no confirmation before starting

- **What I would want (for AI + user):**
  - Search results: show "3 of 8 matches" + pagination
  - Highlight matching phrase in chunk body when search results clicked
  - Chunk navigator visual markers: checkmarks on recently-read, asterisks on cited chunks
  - Freshness ribbon warn if stale
  - Add `data-chunk-id` and `data-citation-count` for AI sidebar
  - Re-crawl confirmation toast
  - Add "Export as markdown" button

---

## 03-project-post-analyze.html

- **Function:** Modal overlay showing 2 blocking decisions (D-001: Authentication strategy, D-002: Payment gateway) flagged during analysis. Each shows SOW snippet Claude found, 2–3 options with reasoning, and optional custom answer. User selects per decision, then "Resolve & start planning" to unlock planning tasks. Modal is forced-attention (base page dimmed).

- **Actions:**
  - Read decision with SOW snippet, ambiguity explanation, 3+ options
  - Click radio button to select option (1st pre-checked with "Recommended by Claude")
  - Or click "Custom" and type answer in textarea
  - Repeat for D-002
  - Click "Defer (block planning)" → defers, planning blocked but flag remains
  - Click "Resolve & start planning →" → POST resolve decisions → redirect

- **Data shown:**
  - Modal header (amber): "2 decisions need your input"
  - Per decision: ID, impact badge (HIGH/MEDIUM/LOW), affected objectives, title, SOW snippet box, ambiguity explanation, 3 radio options, custom textarea
  - Footer: explanation + buttons

- **Linked mockups:**
  - Inbound: 01-dashboard.html (NEEDS YOU card), post-analysis
  - Outbound: 03v2-objectives-dag.html or 09-objective-detail.html

- **Pros:**
  - Modal forces attention
  - SOW snippet exact and cited
  - Impact badge + scope shows consequence
  - Pre-selected recommendation removes decision paralysis
  - Custom option allows override
  - "Defer (block planning)" explicit

- **Cons:**
  - Modal is MODAL (no minimize); if user wants to reference SOW while deciding, blocked
  - Impact badges no legend
  - SOW snippets sometimes truncated
  - Custom option no validation
  - Radio options don't show cost/effort
  - No "Provide more context" link
  - Footer says "edit later in Decisions tab" but tab doesn't exist

- **What I would want (for AI + user):**
  - Add cost/effort labels on options
  - Add "(i)" icon expanding reasoning
  - Allow scrolling base page (dimmed) so user can reference SOW
  - "More context from SOW" link expanding excerpt
  - Custom textarea validation (min 50 chars, max 500)
  - "Skip and create task instead" button
  - Confirmation toast post-resolve

---

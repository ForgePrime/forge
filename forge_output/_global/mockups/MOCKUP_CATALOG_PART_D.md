# Mockup catalog — Part D (auditor + skills + hooks + config + modals)

## 05v2-assign-auditor.html

- **Function:** Form to assign manual AC verification (AC-6 on DT-009, "cannot be automated") to an internal user with `can_audit` role or to an external auditor by email. Top banner shows the AC verbatim with source attribution. Form: 4 sections — pick assignee (internal vs external 2-card radio + 2 internal users J. Patel / M. Chen each with avatar, last-audited date, role pill), what exactly to verify (verbatim notes textarea ≥30 chars, passed to auditor), due-by + reminder cadence, notification preview (full email mockup with Claude's close-safety quote). Right column: Summary, Impact (rose: O-002 cannot ACHIEVE until PASSED, downstream UAT delay, FAILED→re-open path, NEEDS-CLARIFICATION→Q spawn), past auditor history with avg turnaround. Bottom scrutiny: 6 external-dependency tradeoffs.

- **Actions:**
  - Pick assignee type (Internal user / External auditor cards)
  - Pick internal user radio (J. Patel / M. Chen) — pre-selected J. Patel
  - For external: enter email + due date (greyed out unless External chosen)
  - Type verbatim verification notes (counter, must reference sources)
  - Pick due-by date + auto-remind cadence (none / 1 day / 2 days / daily until done)
  - Read notification preview email
  - Cancel · Save as draft (no notification) · Send assignment

- **Data shown:**
  - Header: AC-6, "manual verification", "cannot be automated" amber pill
  - AC banner (amber): full AC quote, verification=manual, source SRC-004 §3.1, can_audit_role required ✓
  - Assignee 2-card radio (Internal vs External) with role count and SLA hint
  - Internal user list (2 cards): JP avatar emerald, MC avatar blue, with email/role/last-audited
  - External auditor disabled inputs (email + due date)
  - Notes textarea pre-filled (810 chars, references 3 sources, OK)
  - Due-by 2026-04-22 + remind "1 day before"
  - Notification preview: From/To/Subject + email body with verification details, Claude close-safety quote in italic amber blockquote, "you can mark PASSED/FAILED/NEEDS-CLARIFICATION" footer
  - Right Summary (emerald): action, assignee, due, reminder, notes length
  - Right Impact (amber): 5 bullets (cannot ACHIEVE, last blocker, downstream UAT delay, FAILED→re-open with F-5, NEEDS-CLARIFICATION→Q spawn)
  - Right past audits: AC-3 PASSED 2-day turnaround, AC-1 NEEDS-CLARIFICATION 5-day, "avg 3.5 days · below 4-day due-by"
  - Scrutiny strip: 6 external-dependency tradeoffs (waiting blocks objective, can't enforce quality, responses stored as F-N, re-assigning confuses, plaintext email security, role snapshot at assign-time)
  - AI sidebar hints

- **Linked mockups:**
  - Inbound: 05v2-task-deliverable.html ("Assign to auditor"), 03v2-create-objective.html (KR-2 descriptive flows here on completion)
  - Outbound: 05v2-task-deliverable.html?flash=AC-6-assigned (Send), 05v2-task-deliverable.html (Cancel / Save draft), 05v2-auditor-inbox.html (notification deep-link), 09-add-ac.html (view full AC ↗)

- **Pros:**
  - Internal vs External choice is upfront with concrete SLA tradeoff (faster vs 2-5 day SLA)
  - Internal user list shows can_audit role and last-audited date so user can pick fairly
  - Notification preview is full email body — user sees exactly what auditor reads
  - Claude's close-safety quote travels with the notification — auditor knows what was NOT verified
  - Past audits with turnaround stats give realistic timing expectations
  - Impact section calls out the blast radius (which downstream objectives delay)
  - Scrutiny names the failure modes (vacation blocks, plaintext email, role snapshot)

- **Cons:**
  - External auditor inputs are disabled rather than tab-toggled — wastes screen space
  - "Verbatim to auditor" notes have no template / no past-notes loader
  - Reminder cadence is preset only (no custom intervals)
  - Notification preview is HTML mock — no preview-mode for what the in-app inbox version looks like
  - "Save as draft" doesn't show how to find the draft later
  - No conflict-of-interest check (e.g., if J. Patel authored DT-009 he shouldn't audit it)
  - Re-assignment flow not addressed (the scrutiny mentions issues but no UX)
  - Past audits limited to last 2 entries

- **What I would want (for AI + user):**
  - Tab toggle Internal/External instead of disabled fields
  - Templates dropdown for verbatim notes ("HIPAA log audit", "TLS verify", "GDPR consent")
  - Conflict-of-interest auto-check + warning if assignee touched the code
  - Custom reminder intervals + Slack DM toggle
  - Preview the in-app auditor inbox card alongside email
  - "Re-assign" affordance with auto-unassign suggestion
  - `data-assignee-id` + `data-due-days` for AI sidebar reasoning
  - Bulk-assign: tick multiple ACs and assign in one form

---

## 05v2-auditor-inbox.html

- **Function:** Inbox view for an external auditor (J. Patel · jpatel@acme.com, role external_auditor, read-only project access). Header shows last-digest time and avg turnaround. Left main column: filter bar (project / priority / status / sort), 3 active assignment cards (HIGH AC-6 due 3 days, MEDIUM AC-3 due 5 days, LOW AC-9 due 14 days) each with priority/AC/objective pills + verbatim notes excerpt + Review button, plus collapsed completed strip ("5 audits · 4 PASSED_WITH_EVIDENCE · 1 REJECTED"). Right column: notification preferences (digest cadence, reminders, Slack DM, reject email), OOO panel, audit stats (17 this quarter, 3.5 day avg). Bottom: 3-step "How auditing works" (verify / Forge records / evidence required) + 4-card verdict glossary (PASSED_WITH_EVIDENCE / PASSED_ATTESTATION / REJECTED / NEEDS_CLARIFICATION) + counterweight "What you CANNOT do here" (6 hard limits).

- **Actions:**
  - Filter: project / priority / status / sort
  - Click "Review →" on assignment cards
  - Show history (expand completed strip)
  - Save notification preferences (digest cadence, reminders, Slack DM toggle, reject email checkbox)
  - "Set OOO dates" amber button
  - AI sidebar slash commands

- **Data shown:**
  - Crumb: Auditor inbox / acme-erp-migration
  - User context: J. Patel · External Auditor pill · jpatel@acme.com mono · 3 active assignments
  - Header right: "Last digest: this morning, 08:00 UTC · Avg turnaround 3.5 days"
  - Filter bar: 4 selects (project, priority, status, sort) + "Showing 3 of 3 active"
  - Card 1 HIGH (rose border): AC-6 on DT-009, O-002, due in 3 days, PENDING, assigned by hergati, 90 min est, SRC-004 §3.1, italic notes excerpt about hash chain
  - Card 2 MEDIUM (amber): AC-3 on DT-010, due 5 days, TLS 1.3 verification with nmap
  - Card 3 LOW (slate): AC-9 on DT-004, GDPR consent flow, due 14 days, 45 min, SRC-003 §5
  - Completed strip (collapsed): 5 audits / 4 PASSED_WITH_EVIDENCE / 1 REJECTED / 0 PASSED_ATTESTATION
  - Right notification prefs: digest dropdown, reminders dropdown, 2 checkboxes (Slack, reject email)
  - Right OOO panel (amber): explanation + "Set OOO dates" button
  - Right stats card: 17 this quarter, 3.5 day avg, 14/1/2 verdict breakdown
  - "How auditing works" 3-card grid (You verify / Forge records / Evidence required) + 4-card verdict legend
  - Counterweight (rose): 6 things auditor cannot do (edit AC, close task, reassign, comment elsewhere, see prod data, override past verdict)
  - AI sidebar hints

- **Linked mockups:**
  - Inbound: notification email magic-link, 05v2-assign-auditor.html (assign flow)
  - Outbound: 05v2-auditor-review.html (Review per card, with `?ac=AC-X`)

- **Pros:**
  - Auditor identity + read-only badge make role boundary explicit
  - 3 priority levels color-coded with concrete due-day pills
  - Verbatim notes excerpt visible on the inbox card (no extra click to know what's expected)
  - Notification preferences are first-class with Slack option
  - OOO panel makes vacation handling proactive (assigner sees banner)
  - Stats reinforce performance expectations (17/quarter, 3.5 days, 82% PASSED_WITH_EVIDENCE)
  - "How auditing works" educates one-time auditors without hiding it in docs
  - Counterweight enforces scope boundary (can't edit AC, can't see prod data)

- **Cons:**
  - Filter bar lacks search by AC text or task ID
  - Completed strip is one-line collapsed; no preview of recent verdicts inline
  - Notification preferences "Save preferences" button needs explicit click — easy to forget
  - OOO is a single button without inline date picker
  - No "request reassignment" inbox action — the counterweight says use NEEDS_CLARIFICATION but flow not surfaced
  - No bulk action (e.g., bulk reject all expired)
  - Stats don't show trend (improving / declining)
  - "Why am I assigned this?" is suggested in AI sidebar but no inline explainer

- **What I would want (for AI + user):**
  - Search box for AC text + task ID across active + completed
  - Expandable completed strip with sortable history
  - Auto-save notification prefs on change with toast
  - Inline OOO date picker + impact preview ("3 incoming assignments would reroute")
  - "Request reassignment" button on each card
  - Stats sparkline (last 12 weeks)
  - "Why me?" tooltip on each card showing role match + history with assigner
  - `data-assignment-id` + `data-priority` + `data-due-days` for AI sidebar prioritization

---

## 05v2-auditor-review.html

- **Function:** Auditor's review page for one assignment (AC-6 on DT-009). Three-column body: left context (Task DT-009 summary, AC-6 verbatim "cannot edit", assigner's 4-step instructions, Challenger close-safety note + what challenger did NOT verify, 4 read-only code files), center verdict picker (4 radio cards: PASSED_WITH_EVIDENCE / PASSED_ATTESTATION / REJECTED / NEEDS_CLARIFICATION) + active evidence form for PASSED_WITH_EVIDENCE (method dropdown, when datetime, environment, file uploader with 2 files attached, evidence text ≥200 chars), 3 collapsed alternate forms for the other verdicts, right column (evidence preview with sha256 hashes, forensic capture metadata, live submission requirements checklist with 5 emerald checks). Bottom: amber close-safety note (4 bullets: PASSED is final, REJECTED bounces, name+IP+timestamp logged forever, verdict feeds AC but doesn't close task), submit footer with confirmation modal preview (sign with name).

- **Actions:**
  - Click prev/next assignment in inbox (implied)
  - Pick verdict radio (4 options)
  - Pick verification method dropdown
  - Set when executed datetime, environment select
  - Drag/drop or click to upload artifacts (.png/.jpg/.log/.txt/.xml/.json/.pdf, max 25 MB each)
  - Remove uploaded file inline
  - Type evidence text (≥200 chars enforced)
  - For PASSED_ATTESTATION: type ≥100 char "why no evidence"
  - For REJECTED: type ≥100 char rejection reason + optional suggested fix
  - For NEEDS_CLARIFICATION: type question for assigner (spawns Q-NNN)
  - Cancel · Save as draft · Submit review (opens confirm modal)
  - Sign + submit (type name in modal)

- **Data shown:**
  - Header: HIGH PRIORITY rose pill, AC-6 / DT-009 / O-002 mono, due 3 days, PENDING blue, assigned by hergati 2026-04-15, 90 min est, SRC-004 §3.1
  - Left: Task DT-009 summary box with instruction quote + "view deliverable read-only"; AC-6 verbatim amber block (cannot edit) + verification method + sources + can_audit ✓; assigner's 4-step instructions (numbered, mono script paths); Challenger close-safety quote (rose, italic) + "what challenger did NOT verify" 3-item list; 4 code files (read-only)
  - Center: 4-card verdict radio (emerald PASSED_WITH_EVIDENCE selected default) with description per option
  - Center evidence form: method dropdown (5 options including "Other"), when (2026-04-18 14:30), environment (production-mirror), drag-drop upload zone, 2 uploaded files (verify-chain-output...log 8.4 KB + grafana-audit-capture-rate.png 412 KB), evidence text 812 chars (≥200 met)
  - Center collapsed alternates: PASSED_ATTESTATION (skeptical-UX warning panel + reason ≥100 chars), REJECTED (reason + optional fix), NEEDS_CLARIFICATION (question textarea)
  - Right: Evidence preview with terminal-style log snippet preview + sha256, image placeholder + sha256
  - Right Forensic capture (slate): auditor name/email/timestamp/IP/UA/sha256s/signed by Forge service key
  - Right Submission requirements (emerald): 5 emerald checks "All requirements met. Ready to submit"
  - Close-safety amber strip: 4 bullets (PASSED final, REJECTED loops, permanent log, verdict ≠ close)
  - Submit footer: Cancel / Save as draft / Submit review buttons
  - Confirmation modal preview: full audit metadata + "Type 'J. Patel' to sign" input + Sign+submit
  - Counterweight (rose): 6 things review does NOT do (prove correctness, validate evidence authenticity, bind assigner, re-verify on code change, replace formal compliance audit, capture reasoning chain)

- **Linked mockups:**
  - Inbound: 05v2-auditor-inbox.html (Review per assignment)
  - Outbound: 05v2-auditor-inbox.html?flash=AC-6-submitted (after submit), task re-open + F-NN finding (REJECTED), Q-NNN spawn (NEEDS_CLARIFICATION)

- **Pros:**
  - 4-verdict picker with concrete behavior per option (auto-reopen, auto-Q-spawn) — no surprises
  - Evidence is required (≥1 file OR ≥200 chars) for PASSED_WITH_EVIDENCE; PASSED_ATTESTATION is visually distinguished and labeled "auditor sign-off, no artifact" forever
  - Live submission requirements checklist tells auditor what's missing
  - Forensic capture panel transparently shows what will be logged (name, IP, sha256s, signed)
  - Challenger close-safety note flows from task into review — auditor sees what was NOT verified before forming verdict
  - Confirmation modal requires typing name as signature — non-trivial commit
  - Counterweight is unusually strong: prove correctness, evidence authenticity, formal audit substitution all explicitly NOT done
  - Re-open + finding generation on REJECTED is automatic and named (F-NN)

- **Cons:**
  - 3 alternate verdict forms are collapsed details; switching verdict mid-form may lose work
  - File uploader doesn't show progress for large files
  - Evidence text "812 chars · ≥200 met" — no max limit shown
  - Read-only code file links don't preview inline (requires nav)
  - Confirmation modal "Type 'J. Patel'" is preview only — needs JS wiring for case-sensitivity
  - No way to compare against prior audit on the same task (e.g., if re-audit after rejection)
  - "REJECTED" bounces with reason as F-NN text — but no preview of how F-NN will look
  - Method dropdown is preset list; "Other" doesn't link to a sub-form
  - PASSED_ATTESTATION reason min 100 chars but no live counter

- **What I would want (for AI + user):**
  - Auto-save evidence text + uploads when switching verdict tabs
  - Inline file preview (image / log first 50 lines / pdf first page)
  - Live char counters on PASSED_ATTESTATION reason and REJECTED reason
  - "Diff vs my prior audit" panel when re-auditing after a rejection
  - Preview F-NN finding text before Submit (so auditor sees the artifact they're creating)
  - "Other" method → free-text input
  - `data-verdict` + `data-evidence-completeness` for AI sidebar reasoning
  - Auto-detect log type from filename extension for syntax-highlighted preview
  - Optional "ask Forge to summarize my evidence" pre-submit gut-check ($0.02)

---

## 10-post-exec-docs.html

- **Function:** Project documentation hub showing the two-layer architecture: auto-generated sections (README, API reference, changelog, schema, test coverage, findings triage, decisions log, cost breakdown — extracted deterministically from code/deliverables, $0 LLM cost, live) and DOC-task sections (Architecture overview, ADRs, Deployment, Runbook — LLM-polished, originated from a DOC-type task on an objective). Left TOC with auto/DOC-task badges per entry. Main column renders example sections: README (stack auto from decisions), Architecture overview (DOC-001, $0.42, includes "✱ Sources consulted" panel), API reference (12 endpoints listed with file:line + test references), 3 ADRs, changelog (git+task derived), per-objective rollup for O-002 (inputs consumed / outputs produced / cost & time). Top: Export and Share-link buttons.

- **Actions:**
  - Click TOC anchors (#readme, #overview, #adr, #changelog, etc.)
  - "📥 Export as" (markdown / PDF implied)
  - "🔗 Share link for client" (capability URL)
  - Edit / ↻ Regenerate / View task per DOC-task section
  - "+ Write new ADR"
  - "+ Add DOCUMENTATION task" in TOC footer
  - Show all (12 endpoints API ref)
  - Tab nav (Knowledge Base / Objectives / Tasks / Activity / Documentation active)

- **Data shown:**
  - Tab nav with Documentation active
  - Top intro strip (gradient): two-layer documentation explanation
  - Left TOC (sticky): 4 sections (Overview / Technical / Per-objective rollups / Audit-compliance), each entry with auto or DOC-task badge
  - README block (auto, 5m ago "from last develop task DONE"): description + mono stack box (Django 5+DRF, Python 3.13, PostgreSQL 16, on-prem container, session+HIPAA audit) + "rebuilds automatically" italic
  - Architecture overview block (DOC-001, 2h ago, $0.42): 3 paragraphs about strangler-fig, on-prem, auth + ✱ Sources consulted blue callout (Code app/api/, Objectives O-001+O-002, Decisions D-001+D-003, KB SRC-001..004) + Edit/Regenerate/View task buttons
  - API reference block (auto, 12 endpoints): per-endpoint card with HTTP verb pill, mono path, description, source file:line + test reference. 3 endpoints shown + "9 more endpoints"
  - ADR block (3 entries): ADR-001 strangler-fig, ADR-002 on-prem, ADR-003 Django over FastAPI, each with status + date + context paragraph
  - Changelog (auto from git + tasks): per-day entries with task ID pill + diff size + "challenger CONSISTENT · 2 findings"
  - Per-objective rollup O-002 (purple border): ACHIEVED, 3-card grid (Inputs consumed / Outputs produced / Cost & time)

- **Linked mockups:**
  - Inbound: 01-dashboard.html (View report / Share link), 04-orchestrate-live.html (after run completes), 05v2-documentation-deliverable.html (Spawn from DOC task)
  - Outbound: 02v2-project-kb.html, 03v2-objectives-dag.html (tab nav), 09-objective-detail.html (per-objective rollup), 07-new-task.html?type=doc (Add DOC task), regenerate flow

- **Pros:**
  - Two-layer split is a key concept made visible (auto vs DOC-task) with badges
  - Auto sections clearly labeled "$0 LLM cost · live" — user knows they don't pay to view
  - DOC sections show origin task ID + cost + age — audit trail
  - "✱ Sources consulted" panel inside Architecture overview discloses what KB/objectives/decisions fed the prose
  - API reference cross-references file:line + test names — auditable
  - Changelog ties commits to tasks + challenger verdict + finding count
  - Per-objective rollup compresses inputs/outputs/cost into a 3-card scannable summary
  - Share link is first-class (consultancy deliverable)

- **Cons:**
  - TOC is sticky but doesn't show current section / scroll position
  - "Show all 12 endpoints" link unreached in mockup
  - Edit / Regenerate buttons on DOC-task sections have no cost preview
  - Share link generation flow not shown — security model unclear (capability URL? expiry? revocation?)
  - Export as has no format picker visible
  - Changelog only shows 3 entries with no pagination
  - Per-objective rollup shows only O-002; no list of all objectives
  - Auto-rebuild "5m ago" cadence not configurable
  - No version history of a regenerated section

- **What I would want (for AI + user):**
  - TOC scrollspy + "you are here" indicator
  - Inline cost preview on Regenerate ("$0.42 again?") with diff option
  - Share-link modal with expiry + revoke + view-as-client preview
  - Export format dropdown (Markdown bundle / PDF / Confluence) with preview
  - Pagination or filter on changelog (by task type, by author)
  - All-objectives rollup grid (small cards)
  - Section freshness ribbon if auto sections fail to refresh
  - `data-section-id` + `data-source` (auto/DOC) for AI sidebar
  - "Lock this section as client deliverable" action that freezes auto-rebuild

---

## 11-skill-edit.html

- **Function:** Skill editor (SK-security-owasp v4) — full edit form for an installed skill. Left column: Basic (name, external ID, 3-card category radio SKILL/MICRO/OPINION, description), Prompt text (terminal-style textarea with `{{diff}}`/`{{task.instruction}}`/`{{op_contract}}` variable hints + "🪄 LLM suggest improvements $0.04" + "Show diff vs v3"), Applies-to-phases 5-card matrix (ANALYSIS/PLANNING/DEVELOP/DOC/CHALLENGER), Tags chip picker, Auto-attach rule (visual rule builder: IF diff_touches AND task_type AND objective_has_tag, with switch to JSON editor), Cost impact (USD/call + context tokens with observed avg/p95). Right column: Conflict check (amber: simulates new rule across 3 projects — "+2 more in acme", "−1 in retail-analytics with consider note", "= no change"), Version history (v4 current / v3 / v2 / v1), Scrutiny "What this edit does NOT do" (4 bullets: doesn't re-run past tasks, doesn't update conflicting hooks, doesn't notify other users, doesn't validate prompt actually improves findings).

- **Actions:**
  - Edit Name / External ID inputs
  - Pick category radio (SKILL/MICRO/OPINION)
  - Edit description textarea
  - Edit prompt textarea with variable substitution
  - Click "🪄 LLM suggest improvements ($0.04)"
  - Click "Show diff vs v3"
  - Toggle Applies-to-phases checkboxes (5)
  - Add/remove tags chips
  - Toggle Visual builder vs JSON editor for auto-attach rule
  - Add condition / OR / remove condition rows
  - Edit cost USD/call + context token size
  - Cancel · Save as draft (v5-draft) · Save + publish (v5)
  - AI sidebar /replay etc.

- **Data shown:**
  - Header: SKILL pill, INSTALLED · auto-attach pill, SK-security-owasp v4 mono, last edited 6d ago
  - Basic: Name input "Security OWASP sweep", External ID input mono "SK-security-owasp" (warning: changing breaks links), 3-card category radio (SKILL selected blue), description textarea
  - Prompt textarea (16 rows, slate-900 monospace, OWASP top 10 prompt with severity/category/file/evidence/fix sections + scope-limit declarations + "If diff is empty or only test files, output NO_DIFF"), char counter 842
  - Variable hints below prompt: `{{diff}}`, `{{task.instruction}}`, `{{op_contract}}`
  - Applies-to-phases: 5-card matrix with ANALYSIS+DEVELOP+CHALLENGER checked
  - Tags: 4 chips (security, owasp, challenger, web-api) + "+ add tag" input
  - Auto-attach rule: tab toggle Visual/JSON, visual builder with 2 conditions joined by OR, JSON preview at bottom showing the same rule
  - Cost impact: USD/call input "0.08" with "Last 30d observed: $0.076 avg · $0.11 p95", context tokens "840"
  - Right Conflict check (amber): 3 projects shown — "+2 more in acme-erp-migration: DT-004 + PT-002", "−1 in retail-analytics: DT-012 (no longer matched) ⚠ Consider...", "= no change in internal-tools"
  - Right Version history: v4 current 6d ago "Added A10 SSRF + scope-limit requirement", v3 / v2 / v1 with author + dates + "View full history · compare versions"
  - Right Scrutiny (rose): 4 bullets
  - Footer: "Saving creates v5 · projects auto-pick on next matching task · org stays v4 until Publish to org"
  - AI sidebar: "Show me v3 → v4 prompt diff", "/replay on last 3 tasks with new prompt"

- **Linked mockups:**
  - Inbound: 11-skills-library.html ("View source" / "Edit"), 12-skills-tab.html ("Edit" per row)
  - Outbound: 11-skills-library.html#SK-security-owasp (Save+publish or Cancel), AI sidebar /replay

- **Pros:**
  - Prompt text in monospace dark editor with variable substitution — feels like real skill authoring
  - Mandatory scope-limit declaration baked into the prompt template (encoded in skill, not just policy)
  - Conflict check is unusually strong: simulates rule against last 30d tasks across all installed projects — shows + / − / = per project with consider notes
  - Versioning is first-class (v4 / v3 / v2 / v1 with diffs), past tasks preserve their version
  - Visual rule builder + JSON editor toggle covers both audiences (PMs vs power users)
  - Cost impact has user estimate AND observed (avg/p95) for calibration
  - Apply-to-phases matrix + tags + auto-attach rule = 3 distinct dimensions, not collapsed
  - "Save + publish (v5)" vs "Save as draft (v5-draft)" semantics explicit
  - Scrutiny enumerates 4 specific things the edit does not do (notably "doesn't validate the prompt improves findings" — points to /replay)

- **Cons:**
  - Prompt textarea is fixed 16 rows — long prompts scroll
  - "Show diff vs v3" button has no implementation visible (modal? inline?)
  - Visual rule builder doesn't show match count preview (how many tasks would match this rule today)
  - Tags input is placeholder only — no autocomplete from existing tag pool
  - Cost impact USD is user-entered free-text — no validation against observed
  - Conflict-check rationale is opinion-style ("⚠ Consider: should app/billing/ also trigger?") — useful but no path to act on
  - Org-publish flow (publishing v5 to org) is mentioned in footer but not interactive
  - No "test prompt against this task" sandbox

- **What I would want (for AI + user):**
  - Resizable prompt textarea + syntax highlighting for variable substitution
  - Inline diff modal for Show diff vs v3 with side-by-side
  - Live match-count preview on rule builder ("matches 14 of 28 recent tasks")
  - Tag autocomplete from existing org/project tags
  - Cost USD field with "auto-fill from observed" button
  - "Test prompt" sandbox: pick a recent task, run skill against it, see output before publishing
  - Promote-to-org button with diff against current org version
  - `data-skill-version` + `data-applies-to-phases` for AI sidebar reasoning
  - Inline replay link: "/replay on last 3 tasks with v5" with cost preview

---

## 11-skills-library.html

- **Function:** Org-level catalog of reusable LLM capabilities. Header explains the 3-tier taxonomy (SKILLS / MICRO-SKILLS / OPINIONS) with counts (24 / 41 / 18). Top rose strip warns "Skills are not decoration — they change cost". Filter bar: search, phase select, category select, sort (most used / newest / cost / success lift). Filter chips: All · Installed for this project · Auto-attached · Marketplace · My custom. 8 skill cards in 2-col grid (SK-security-owasp installed auto-attach with success-lift +31% findings caught / OP-best-dev-django installed manual / MS-pytest-parametrize installed auto / SK-scenario-gen-nonhappy default for analysis / OP-hipaa-auditor marketplace / SK-risk-weighted-verify default for risk / MS-adr-sections auto for DOC / OP-cloud-architect marketplace WITH conflict warning). Bottom: "Default skills per phase" 4-column summary (ANALYSIS / PLANNING / DEVELOP / DEEP-VERIFY).

- **Actions:**
  - Search by name / tag
  - Filter by phase / category / sort
  - Click filter chips (All 83 / Installed 12 / Auto-attached 5 / Marketplace 41 / My custom 9)
  - Per card: View source / Edit auto-attach rule / Detach from project / View prompt / Clone & customize / + Install for this project / + Install anyway (with warning) for conflicting
  - "+ Create new skill" header button
  - "⚙ Project config" header button
  - "edit for this project" links per phase default

- **Data shown:**
  - Header: "Skills library", taxonomy explanation
  - Rose contract banner: "Skills are not decoration — change output AND cost"
  - 3 category count cards (24 SKILLS / 41 MICRO / 18 OPINIONS) with explanations
  - Filter bar (search + 3 dropdowns) + 5 filter chips
  - 8 cards each with: category pill (SKILL/MICRO/OPINION), install status pill (INSTALLED · auto-attach / INSTALLED · manual / INSTALLED · default for X / marketplace), mono ID, name, description, phase tags, 3-stat row (success lift / cost impact / auto-attach rule), action buttons
  - SK-security-owasp: +31% findings caught, +$0.08/call, "if diff touches auth/API"
  - OP-best-dev-django: +18% CONSISTENT rate, +$0.12/call, manual only
  - MS-pytest-parametrize: 3.2 → 7.1 ACs/test, +$0.02/call, auto if Python+pytest
  - SK-scenario-gen-nonhappy: −67% missed edge cases vs happy-only, +$0.15/task, default analysis
  - OP-hipaa-auditor: +4.2 compliance findings/task, +$0.18/call, healthcare/fintech
  - SK-risk-weighted-verify: +52% critical bugs caught in high-risk, +0-40%/task scales, default risk
  - MS-adr-sections: documentation phase only
  - OP-cloud-architect (faded): "may conflict with SRC-004" rose pill, "Install anyway with warning" amber button
  - Bottom phase-defaults summary: 4 colored cards (ANALYSIS / PLANNING / DEVELOP / DEEP-VERIFY) each with 3 default skills + "edit for this project" link

- **Linked mockups:**
  - Inbound: 12-project-config.html (Browse library), 12-skills-tab.html (+ Add from library), 12-add-hook.html (Browse library), 16-ai-sidebar.html (run_skill trace)
  - Outbound: 11-skill-edit.html (Edit / View source), 12-project-config.html, install flow (POST), 12-phase-defaults-tab.html (edit for this project)

- **Pros:**
  - 3-tier taxonomy (SKILLS / MICRO / OPINIONS) is enforced visually — distinct colors and counts
  - Cost-impact column is upfront on every card — prevents "more is better" instinct
  - Success-lift metric (concrete numbers like "+31% findings caught", "−67% missed edge cases") gives evidence-based selection
  - Conflict warning on OP-cloud-architect vs SRC-004 on-prem constraint is project-aware
  - Filter chips clearly count installed/marketplace/custom
  - Phase defaults summary at bottom shows the "if you do nothing" baseline
  - Auto-attach rules visible on cards (not buried in edit page)

- **Cons:**
  - "Most used" sort is default but no explanation of "used by whom" (org vs project)
  - 8 cards shown but no pagination or load-more for full 83
  - Cost impact mixes formats (+$0.08/call, +$0.15/task, +0–40%/task scales) — hard to compare
  - Success-lift metrics use different units (% rate, absolute number, ratio) — also hard to compare
  - "+ Install for this project" doesn't show cost projection before commit
  - Conflict warning explains the conflict but no inline link to SRC-004
  - "Clone & customize" flow not shown
  - No skill-search by description or tag (only by name)

- **What I would want (for AI + user):**
  - Normalize cost/lift to comparable scale + tooltip explaining each metric
  - Pagination + total count
  - Install-cost projection modal: "Adding this skill will add ~$X/month at current rate"
  - Conflict warning links to the source/decision causing the conflict (SRC-004 §X)
  - Search across name + description + tags + ID
  - "Compare skills" multi-select: pick 2-3 and see diff
  - `data-skill-id` + `data-installed` + `data-cost-impact` for AI sidebar
  - "Try this skill" sandbox before installing
  - Sort by "highest cost / lowest signal" to find candidates for detach

---

## 12-project-config.html

- **Function:** Project configuration entry page (Operational Contract tab active). 6 tabs: Operational contract / Skills · 12 / Post-stage hooks · 4 / Phase defaults / Budget+limits / Integrations. Header explains "Changes apply to all future tasks; past tasks keep original config — audit trail preserved." Main 2-col body: left = Operational contract editor (`.claude/forge.md` style markdown with sections Hard constraints from SRC-004 / Preferred stack / Patterns to follow / Patterns to avoid / Tone-style / Review obligations) with revert / 🪄 LLM suggest / Save buttons + footer stats (12 directives · 3 MUST · 2 MUST NOT · 7 prefs · ~420 tokens injected); right = Active skills sidebar (7 visible skills color-coded by category, attachment mode badges, "+ 5 more" footer, est skill overhead "+38% context · +$0.14/task avg" with Rebalance link) + Contract history (v12/v11/v10). Below main: Post-stage hooks list (4 hooks: AFTER ANALYSIS cross-objective ambiguity scan / AFTER PLANNING DAG lint / AFTER DEVELOP HIPAA audit log verification / AFTER DOC stale-link disabled). Bottom: "🤖 Autonomy level — gradual hand-off" 5-tier roadmap (L1 enabled / L2 enabled active / L3 enable→ / L4 requires L3+2 weeks / L5 locked) with concrete blocker note ("L3 requires audit pass — 3 pre-selected-and-ignored ambiguities").

- **Actions:**
  - Tab nav between 6 config tabs
  - Edit operational contract markdown
  - Click ↺ revert / 🪄 LLM suggest improvements / Save & apply to future tasks
  - Browse library / Rebalance from skills sidebar
  - Per hook: Edit/Remove + Enabled toggle
  - "+ Add hook" button
  - Click "enable →" on L3 autonomy card
  - View all contract revisions

- **Data shown:**
  - 6 tab nav with active "Operational contract"
  - Header: project config explainer
  - Contract editor box: filename `.claude/forge.md`, edited 4h ago by hergati, revert / 🪄 LLM suggest / Save buttons
  - Contract content (mono pre): Hard constraints (4 MUST/MUST NOT items from SRC-004), Preferred stack, Patterns to follow (3), Patterns to avoid (4), Tone/style (3), Review obligations (3) — 12 directives total
  - Editor footer: "12 directives · 3 MUST · 2 MUST NOT · 7 preferences · injected into every prompt (~420 tokens) · audit: every version preserved"
  - Active skills sidebar: 7 cards (Security OWASP / Scenario gen / Risk-weighted / pytest parametrize / ADR / Best dev / HIPAA auditor) with category colors and attachment badges
  - Skills footer: "+38% context · +$0.14/task avg · Rebalance link"
  - Contract history: v12 4h ago / v11 2d ago / v10 3d ago / View all 12 revisions
  - Hooks list: 4 hooks each with stage pill, name, skill ref, description, enabled checkbox, edit/remove buttons; AFTER DOC disabled (faded)
  - Autonomy roadmap: 5-card grid L1 enabled, L2 enabled active, L3 enable→ (60% opacity), L4 locked "requires L3+2 weeks clean runs", L5 locked
  - Blocker note: "Current block to L3: 3 ambiguity resolutions were pre-selected-and-ignored (see O-002 audit). L3 requires audit pass."

- **Linked mockups:**
  - Inbound: 11-skills-library.html (Project config), 03v2-objectives-dag.html (Settings), 12-* sub-tabs
  - Outbound: 12-skills-tab.html / 12-hooks-tab.html / 12-phase-defaults-tab.html, 11-skills-library.html (Browse library), 11-skill-edit.html (per skill in sidebar), 16-ai-sidebar.html (Rebalance), 09-objective-detail.html (audit pre-selected ambiguities)

- **Pros:**
  - "Future tasks only" rule explicit at the top — past tasks preserve their config (audit trail intact)
  - Operational contract is markdown text + injected as prompt context (~420 tokens) — concrete and auditable
  - Hard constraints traced to SRC-004 source — no policy without provenance
  - Active skills sidebar gives at-a-glance view of what's in every prompt (no need to navigate to skills tab)
  - Contract history is versioned with summary per revision
  - 5-tier autonomy roadmap is progressive with concrete unlock criteria
  - Block-to-L3 message names the specific evidence ("3 pre-selected-and-ignored") and links to where it happened
  - Each hook row shows skill ID + description + enabled state + edit/remove buttons inline

- **Cons:**
  - Operational contract editor is a `<pre>` block — no markdown preview / no syntax highlighting
  - "🪄 LLM suggest improvements" has no preview / no cost shown
  - Skills sidebar shows "+5 more" but no expand action visible
  - Hooks list is on the contract tab; tab nav suggests separate hooks tab — duplicates UX
  - Autonomy L3 "enable →" button doesn't show the actual gate criteria UI
  - Contract history limited to 3 entries
  - No "test contract against a recent task" sandbox
  - Skills sidebar doesn't show which skills are auto-attached vs manual at a glance

- **What I would want (for AI + user):**
  - Markdown editor with split preview for the contract
  - 🪄 LLM suggest with diff modal + cost
  - Expandable skills sidebar (collapse/expand per skill, +5 more inline)
  - Single source-of-truth for hooks (only on hooks tab; remove from contract tab)
  - Autonomy L3 enable wizard: shows 3 unmet criteria + path to satisfy
  - Inline contract-against-task sandbox
  - `data-autonomy-level` + `data-config-version` for AI sidebar
  - Diff between current contract and proposed changes highlighted live
  - "Promote contract to org template" action

---

## 12-skills-tab.html

- **Function:** Project config Skills tab — table of skills attached to this project (12 rows). Top: cost impact summary card (4 metrics: context overhead +38% ≈3,400 tokens / avg cost +$0.14/task / monthly projection $42 / status within budget of $100 cap) with "🎚 Rebalance (suggest trims)" + "Browse library →" buttons. Scrutiny strip: 4 things this tab does NOT control (auto-attach rules / hooks / phase defaults / challenger pool — each links to the right place). Filter bar: category dropdown / attachment mode dropdown / "+ Add from library" link. Table: 12 skills with columns Skill (name + mono ID) / Category (SKILL/MICRO/OPINION pill) / Attachment (auto with reason / default · phase / manual / hook · stage / hook · disabled) / Cost impact / Actions (Edit / Detach / View hook / Enable). Footer note: detaching only affects future tasks.

- **Actions:**
  - Click "🎚 Rebalance (suggest trims)" — opens AI sidebar with rebalance suggestions
  - Browse library → 11-skills-library.html
  - Filter by category / attachment mode dropdowns
  - "+ Add from library"
  - Per row: Edit (→ skill edit page), Detach (with confirmation), View hook (for hook-attached skills), Enable (for disabled hook skills)
  - Tab nav

- **Data shown:**
  - Top tab nav, page header
  - Cost impact 4-card grid: +38% context overhead, +$0.14/task, $42/mo projection, within $100 budget
  - Scrutiny rose strip: 4 things this tab does NOT control (links to 11-skill-edit / hooks tab / phase-defaults tab / op contract tab)
  - Filter bar with 3 dropdowns + 1 link
  - Column headers: Skill / Category / Attachment / Cost impact / Actions
  - 12 skill rows: SK-security-owasp auto, SK-scenario-gen-nonhappy default·analysis, SK-risk-weighted-verify default·risk, MS-pytest-parametrize auto, MS-adr-sections auto·DOC, OP-best-dev-django manual, OP-hipaa-auditor manual·critical, SK-cross-obj-ambiguity hook·after analysis, SK-dag-lint hook·after planning, MS-broken-link-check hook·disabled, MS-source-attribution default·analysis, MS-ac-coverage-gate default·planning
  - Per-row attachment shows mode badge + condition reason ("if diff touches auth/API")
  - Cost-impact column color-coded: amber for higher, slate for lower
  - Footer note: "Detaching a skill only affects future tasks. Past tasks keep the skill set they ran with — audit trail preserved."
  - AI sidebar suggestions

- **Linked mockups:**
  - Inbound: 12-project-config.html (tab nav)
  - Outbound: 11-skill-edit.html (Edit per row), 12-hooks-tab.html (View hook / Enable), 11-skills-library.html (Browse / Add from library), 16-ai-sidebar.html (Rebalance)

- **Pros:**
  - Cost impact summary is upfront with 4 distinct metrics (overhead, per-task, monthly, budget status)
  - Status "within budget" with /$100 cap is reassuring
  - Scrutiny correctly disambiguates this tab's scope from auto-attach rules / hooks / phase defaults / challenger pool — each linked
  - Attachment column distinguishes 5 modes (auto / default·phase / manual / hook·stage / hook·disabled) with consistent badging
  - Per-row condition reason ("if diff touches auth/API") removes need to drill into edit page
  - Hook-attached skills route to "View hook" instead of "Edit" — preserves single-source-of-truth
  - 12 rows fit in one page with no pagination

- **Cons:**
  - Cost-impact column mixes per-call, per-task, per-hook units — hard to sum
  - "Rebalance" button opens AI sidebar; no inline preview of what it would suggest
  - Filter dropdowns have only 3 dimensions; no search
  - Detach has no inline confirmation modal preview
  - 12 rows is the count but not all costs roll up in the table footer
  - No bulk select for detach
  - "Hook · disabled" mode shown but no quick toggle to enable from this tab (must navigate)

- **What I would want (for AI + user):**
  - Sortable columns + sticky header for longer lists
  - Search across name + ID + tags
  - Inline cost-impact normalizer (toggle per-call vs per-task view)
  - Bulk select + bulk detach with confirmation modal
  - Inline enable toggle for hook·disabled skills
  - Per-row "explain why this is auto / default" tooltip
  - `data-skill-id` + `data-attachment-mode` + `data-cost` for AI sidebar
  - Footer with column total cost (when sortable)
  - Rebalance preview inline before opening sidebar

---

## 12-hooks-tab.html

- **Function:** Project config Hooks tab listing 4 post-stage hooks. Header summary: "4 hooks configured · 3 enabled · projected cost +$0.14 per stage cycle". Scrutiny "What hooks do NOT do" (4 bullets: not pre-stage gates, don't block by default, don't share state, don't run on replays by default). 4 hook cards: AFTER ANALYSIS cross-obj ambiguity scan (always condition, $0.05/firing, 6 firings 30d, 3 toggles), AFTER PLANNING DAG lint+critical-path (condition `tasks_added >= 3`, $0.04, block-stage-on-failure ON), AFTER DEVELOP HIPAA audit log (condition diff_touches API/models, $0.18, critical pill, all 3 toggles ON), AFTER DOC stale-link scanner (DISABLED faded, $0.01). Each card has 3 toggles (Enabled / Block stage on failure / Run on replays) + History / Edit / Remove side actions. Bottom CTA: "+ Add hook →" linking to 12-add-hook.html.

- **Actions:**
  - Tab nav
  - "+ Add hook" header / footer buttons
  - Per card: toggle Enabled / Block stage on failure / Run on replays
  - Per card: Edit / History / Remove buttons
  - AI sidebar suggestions

- **Data shown:**
  - Tab nav (Hooks active)
  - Summary strip (indigo): "4 hooks · 3 enabled · +$0.14 per stage cycle" + + Add hook button + explainer about no per-task skip
  - Scrutiny rose: 4 things hooks do NOT do (no pre-stage, don't block default, no shared state, no replay default)
  - Hook 1 (AFTER ANALYSIS, blue): cross-obj ambiguity scan, ENABLED, SK-cross-obj-ambiguity, "always" condition, $0.05/firing, 6 firings·avg $0.05·$0.30 total in 30d, 3 toggles (Enabled on, Block off, Replay off)
  - Hook 2 (AFTER PLANNING, purple): DAG lint, ENABLED, SK-dag-lint, condition `tasks_added >= 3`, $0.04, 3 firings·$0.12 total, Block-on-failure ON
  - Hook 3 (AFTER DEVELOP, emerald + critical amber pill): HIPAA audit log, ENABLED, OP-hipaa-auditor, condition `diff_touches(['app/api/**', 'app/models/**'])`, $0.18, 5 firings·$0.90 total, all 3 toggles ON
  - Hook 4 (AFTER DOC, faded): Stale-link scanner DISABLED, MS-broken-link-check, "always", $0.01, 0 firings (disabled)
  - Footer "+ Add hook →" CTA with 2-step explainer
  - AI sidebar hints

- **Linked mockups:**
  - Inbound: 12-project-config.html (tab nav), 12-skills-tab.html ("View hook"/"Enable"), 09-edit-challenger-checks.html (companion gates link)
  - Outbound: 12-add-hook.html (+ Add / Edit), hook firing history endpoint (History), 16-preview-apply-modal.html (Remove confirmation), 12-skills-tab.html (tab nav)

- **Pros:**
  - Each hook card co-locates stage / skill / condition / cost / firing-history / 3 toggles in one block
  - Conditions shown in mono format with concrete syntax (`tasks_added >= 3`, `diff_touches([...])`)
  - 30-day firing stats per hook (count, avg cost, total) calibrate cost expectations
  - "Critical" pill on HIPAA hook signals HIGH severity visually
  - Disabled hook (Stale-link) is faded with 0 firings — clearly opt-out state
  - Scrutiny correctly distinguishes hooks from pre-stage gates, AC, etc.
  - Block-stage-on-failure / Run-on-replays as separate toggles offers fine control

- **Cons:**
  - Toggles save inline but no visible save confirmation
  - Condition expressions visible but not validated inline (no "test condition" affordance)
  - No way to filter hooks by stage / enabled / cost
  - "History" button leads to a separate page (no inline expansion)
  - Critical pill is manual flag with no documentation of when to use
  - "Always" condition shown for hooks with no condition — unclear if user can scope it later
  - Cost projection in summary doesn't break down which hook contributes most
  - No drag-to-reorder for hook precedence (assumes order doesn't matter)

- **What I would want (for AI + user):**
  - Inline save confirmation toast for toggle changes
  - "Test condition against last 5 tasks" affordance per hook
  - Filter chips: by stage / enabled / has-condition / cost-tier
  - Inline expandable history per hook (last 10 firings with PASS/FAIL)
  - "Critical" pill tooltip + one-line guidance
  - Cost contribution sparkline in summary
  - `data-hook-id` + `data-stage` + `data-enabled` for AI sidebar reasoning
  - "Detect redundant hooks" suggestion (e.g., if 2 hooks fire on same condition)
  - Drag handle for reordering when execution order matters

---

## 12-add-hook.html

- **Function:** Form to create a new post-stage hook. Single column. Sections: Stage 4-card radio (AFTER ANALYSIS / PLANNING / DEVELOP selected emerald / DOC); Skill picker dropdown grouped by SKILLS / MICRO / OPINIONS with cost annotation per option (selected SK-load-probe), preview card below showing description + applies_to_phases + tags; Condition optional textarea with mono syntax (default-filled `diff_touches(['app/api/**', 'app/cdc/**']) AND objective.scope in ['performance', 'migration']`) + helper showing available functions and "Full reference"; On-failure 3-radio (Raise finding continue selected / Block stage / Warn only); Run-on-replays checkbox (default off); Cost estimate amber 4-metric box (per firing $0.20 / expected 8/mo / projected $1.60/mo / budget headroom OK $44.20/$100); Scrutiny rose box (5 things this hook will NOT do, last bullet specifically analyzes the user's condition for gotchas: "will not match tasks that only touch tests or migrations"). Footer: Cancel / Save as disabled / Create hook (enabled).

- **Actions:**
  - Pick stage radio (4 options)
  - Pick skill from grouped dropdown (3 categories)
  - Read selected skill preview card
  - Type condition expression in mono textarea
  - Click "Full reference →" for condition function docs
  - Pick on-failure radio (3 options)
  - Toggle "Also run on replays"
  - Cancel · Save as disabled · Create hook (enabled)
  - AI sidebar slash commands

- **Data shown:**
  - Header: page title + 1-line explainer
  - Stage 4-card radio (AFTER DEVELOP selected emerald)
  - Skill picker dropdown grouped by SKILLS / MICRO / OPINIONS, selected SK-load-probe with +$0.20/call
  - Selected skill preview: SKILL pill + name + mono ID + description + applies_to_phases + tags
  - Condition textarea (3 rows, mono): `diff_touches(['app/api/**', 'app/cdc/**']) AND objective.scope in ['performance', 'migration']`
  - Helper: 5 available functions + Full reference link
  - On-failure 3 radios: Raise finding continue (selected), Block stage completion, Warn only
  - Run-on-replays checkbox in slate panel with explainer
  - Cost estimate 4-metric amber box: $0.20/firing, 8/mo expected, $1.60 projected, OK $44.20/$100 mo used
  - Scrutiny rose box: 5 bullets, last one is condition-specific analysis
  - Footer summary: "after-develop hook runs SK-load-probe on API/CDC changes · +$0.20/firing · raises finding on failure"
  - Cancel / Save as disabled / Create hook buttons
  - AI sidebar hints

- **Linked mockups:**
  - Inbound: 12-hooks-tab.html (+ Add hook button)
  - Outbound: 12-hooks-tab.html (after Create or Save-disabled), 11-skills-library.html (Browse the library →), condition function reference docs

- **Pros:**
  - Stage picker is 4 visual cards with phase-level color cues
  - Skill dropdown groups by category (SKILLS / MICRO / OPINIONS) and shows cost per option in the dropdown text
  - Selected-skill preview confirms what user picked before commit
  - Condition syntax has 5 named functions documented inline + reference link
  - On-failure 3-radio matches the 3 hook escalation modes from hooks tab
  - Cost estimate is concrete (per-firing, monthly projection, budget headroom)
  - Scrutiny last bullet does condition-aware analysis ("will not match tasks that only touch tests or migrations") — not generic
  - "Save as disabled" creates an inactive hook for staging

- **Cons:**
  - Condition textarea has no autocomplete / no syntax highlighting / no validation preview
  - Skill dropdown shows ~7 options; no search for orgs with 50+ skills
  - "Expected firings/month" is estimated from "condition match probability default 0.7" — opaque
  - On-failure 3 modes have no examples of when to use each
  - "Run on replays" checkbox tucked at bottom — easy to miss
  - Cost estimate doesn't show how this hook adds to the existing 4 hooks total
  - Stage picker shows only 4 stages; assumes no custom stage extension
  - No "test this hook against a recent task" affordance

- **What I would want (for AI + user):**
  - Live condition validation: parse expression, highlight unknown functions, preview "would have fired N times in last 30d"
  - Skill dropdown search + autocomplete
  - Expected firings calculation breakdown (clickable to see how 0.7 probability was derived)
  - On-failure mode examples (e.g., "use Block stage for HIPAA, Warn only for nits")
  - "Test against last task" sandbox with cost preview
  - Cost diff: "after this hook, total project hooks cost will be $X (was $Y)"
  - `data-stage` + `data-skill-id` + `data-condition` for AI sidebar to suggest improvements
  - Auto-suggest condition based on stage+skill combo
  - Move "Run on replays" up to be more visible

---

## 12-phase-defaults-tab.html

- **Function:** Project config Phase defaults tab — 4-column layout (ANALYSIS / PLANNING / DEVELOP customized / DOCUMENTATION) showing default skills per phase if no task-level overrides exist. Top scrutiny strip: 4 things phase defaults do NOT override (auto-attach rules / task-level / post-stage hooks / challenger pool) + precedence order ("task-level > auto-attach rule > phase defaults > org defaults"). Each column header has phase emoji + name + count (e.g., "ANALYSIS · 3 default skills"). Per skill card: category pill, name, mono ID, × remove button, cost line. Each column footer: "+ Add skill to X defaults" button + cost overhead total ("+$0.20/analysis task"). DEVELOP column has emerald border + "customized" badge + one skill (HIPAA auditor) marked "added for this project". Other columns show "org default — not customized" italic note. Footer: "Past tasks keep their original skill set" + Reset to org defaults / Save defaults.

- **Actions:**
  - Tab nav
  - Per skill card: × to remove from phase defaults
  - Per column: "+ Add skill to X defaults" button
  - "↺ Reset to org defaults"
  - "Save defaults"
  - AI sidebar slash commands

- **Data shown:**
  - Tab nav (Phase defaults active)
  - Page header
  - Scrutiny rose: 4 bullets + precedence chain
  - Column 1 ANALYSIS (blue): SKILL Non-happy-path scenarios SK-scenario-gen-nonhappy +$0.15/task, MICRO Ambiguity detection MS-ambiguity-detect +$0.03/task, MICRO Source attribution enforcer MS-source-attribution +$0.02/task; "org default — not customized"; "+$0.20/analysis task" overhead
  - Column 2 PLANNING (purple): MICRO DAG acyclic check MS-dag-acyclic +$0.01, MICRO AC coverage gate MS-ac-coverage-gate +$0.02, MICRO Task-size cap MS-task-size-cap +$0.01; "org default"; "+$0.04/planning task"
  - Column 3 DEVELOP (emerald, customized badge, border-2): SKILL Security OWASP sweep SK-security-owasp +$0.08/call, MICRO pytest parametrize MS-pytest-parametrize +$0.02, OPINION HIPAA auditor (project-specific) OP-hipaa-auditor +$0.18 with "added for this project" emerald pill; "+$0.28/develop task"
  - Column 4 DOCUMENTATION (slate): MICRO ADR section extractor MS-adr-sections +$0.03, MICRO Citation completeness MS-citation-check +$0.02; "org default"; "+$0.05/doc task"
  - Footer: "Past tasks keep original skill set · changes logged in config history"
  - Reset to org defaults + Save defaults buttons
  - AI sidebar hints

- **Linked mockups:**
  - Inbound: 12-project-config.html (tab nav), 12-skills-tab.html (tab nav), 11-skills-library.html ("edit for this project" per phase-defaults preview)
  - Outbound: 11-skill-edit.html (per skill mono ID click — implied), modal picker for "+ Add skill", 16-preview-apply-modal.html (Reset destructive)

- **Pros:**
  - 4 columns map directly to the 4 task types (consistent color across the app)
  - Customized vs org-default distinction is visually clear (emerald border + badge + "added for this project" pill on the project-specific entry)
  - Precedence chain ("task-level > auto-attach > phase defaults > org defaults") in the scrutiny strip clarifies the merge rules
  - Per-column cost overhead totals make the budget consequence of defaults transparent
  - Each skill card shows category pill, name, ID, cost, remove button — compact but complete
  - "+ Add skill to X defaults" button is per-phase (no global list)
  - Footer "Past tasks keep original skill set" reinforces audit safety

- **Cons:**
  - "× remove" on org-default skills isn't differentiated — unclear if removing creates a project override or is blocked
  - "Add skill to X defaults" doesn't show modal/picker preview
  - Reset to org defaults is destructive but only flagged via styling (no confirmation modal preview)
  - DEVELOP column "customized" badge but other columns have no "default" badge for symmetry
  - No cost breakdown vs org defaults (e.g., "+$0.18 above org baseline")
  - Phase defaults assume 4 phases; no extensibility for custom phases
  - Cost overhead totals don't show how they propagate to skills tab summary
  - Footer "changes logged in config history" — but no link to that history

- **What I would want (for AI + user):**
  - Distinguish between "remove from project default (revert to org)" and "remove from org default (overrides org)" with different actions
  - Modal picker for + Add skill with search and category filter
  - Confirmation modal for Reset to org defaults showing the diff
  - "Customized" badge on every column with project-level changes (not just DEVELOP)
  - Cost diff vs org default per column (e.g., "+$0.18 above org baseline")
  - `data-phase` + `data-skill-id` + `data-source` (org/project) for AI sidebar
  - Link to config history from footer
  - "Compare to other projects" view to see common patterns
  - Inline simulation: "If you remove HIPAA auditor, next 5 develop tasks would have lost +4.2 compliance findings"

---

## 16-preview-apply-modal.html

- **Function:** Generic destructive-action wrapper modal — example: "Remove AC-5 and log skill-leak incident", initiated from the AI sidebar. Background dim shows underlying O-002 page. Modal has rose header ("destructive action · preview required"), source-of-action callout (which AI conversation proposed this, cost already incurred, link to conversation), 2-column diff (Current state · O-002 ACs vs Proposed · after apply with AC-5 line-through and incident I-001 added), Scope-of-change section (4 + / − / · bullets enumerating affected entities), Scrutiny "What this action does NOT do" (6 bullets: doesn't re-run analysis, doesn't update other objectives, doesn't notify reviewers, doesn't retroactively flag past tasks, doesn't delete decision history, doesn't deny-list AC-5). Footer: actor + timestamp + "reversible via undo within 24h" + 3 buttons (Cancel / Save as draft / Apply rose).

- **Actions:**
  - Click × close (Cancel)
  - Click Cancel
  - Click "↗ open the conversation that proposed this"
  - Click "Save as draft (don't apply now)" — stores proposed change as draft for peer review
  - Click "Apply" rose primary
  - AI sidebar /cross-check or "What does undo do exactly?"

- **Data shown:**
  - Background: greyed-out (30% opacity) underlying page with O-002 + ACs visible (AC-5 with INVENTED pill)
  - Modal header (rose): destructive action label, action title "Remove AC-5 and log skill-leak incident"
  - Source-of-action callout (indigo): "🤖 source: AI sidebar suggestion · sonnet-4.6 · 14s ago · cost $0.06 (already incurred)"; user prompt quoted; link to sidebar conversation
  - Diff 2-col: LEFT current state (5 ACs with AC-5 strikethrough + INVENTED pill on rose row, footer "5 ACs · 1 unsourced (scrutiny debt)"); RIGHT proposed (4 ACs + AC-5 removed italic + new amber row "+ NEW incident:I-001", footer "4 ACs · 0 unsourced · 1 lessons-learned entry created")
  - Scope of change: 5 bullets with + / − / · markers (AC-5 removed FK cascade, scrutiny_debt -1, lessons_learned I-001 created with description, audit log entry, AC count 5→4 doesn't trigger re-analysis)
  - Scrutiny rose: 6 bullets (no re-analysis, no cross-objective scan, no reviewer notification, no retroactive flag on AT-005, decision history preserved, no deny-list)
  - Footer: actor "hergati" + timestamp "2026-04-18 14:32 UTC" + reversible note + 3 buttons (Cancel / Save as draft / Apply)
  - Annotations panel below modal: AI sidebar context + 7-step data-source list + generic-pattern note ("standard wrapper for any AI sidebar suggestion that mutates state")

- **Linked mockups:**
  - Inbound: 16-ai-sidebar.html (action button "Remove AC-5 + log skill-leak"), 12-skills-tab.html (Detach destructive), 12-phase-defaults-tab.html (Reset destructive), 09-edit-challenger-checks.html (Reset to org defaults), 02v2-source-preview.html (Archive source)
  - Outbound: 09-objective-detail.html (after Apply with flash + audit log), 16-ai-sidebar.html (open conversation), draft listing on user home (Save as draft)

- **Pros:**
  - Background dimming with underlying page visible preserves context (user can still see what's being changed)
  - Source-of-action callout names the AI conversation, cost already incurred, with link back — full traceability
  - Diff is concrete: actual line-through for removed entries, actual + NEW for created entities
  - Scope-of-change uses + / − / · markers consistently
  - Scrutiny is action-specific: 6 bullets directly tied to "remove AC-5" semantics
  - Reversibility window (24h undo) makes the action less terminal
  - 3-button footer (Cancel / Save as draft / Apply) covers all paths
  - Annotation panel marks this as a generic pattern for any AI-sidebar-initiated destructive action

- **Cons:**
  - Modal cannot be minimized — if user wants to reference the underlying page actively, blocked
  - "Save as draft" stores the change but no visible indication of where to find drafts later
  - "Apply" button has no signature requirement (auditor-review-style sign step) for destructive actions
  - Cost-already-incurred phrasing ("$0.06 already incurred") might confuse users into thinking Apply costs more
  - Background dimming hides interactive references the user might want
  - Diff doesn't show full O-002 state, only the AC list — other affected entities (lessons_learned) are inferred from scope-of-change
  - 24h undo not mentioned in scrutiny (separate footer note) — easy to miss
  - Reversibility note doesn't explain what undo restores (does it un-create incident I-001?)

- **What I would want (for AI + user):**
  - Minimize / re-open modal toggle so user can browse context while pondering
  - Optional name-signature requirement for HIGH-impact destructive actions
  - Diff that includes all affected entities, not just primary (preview lessons_learned + audit log row)
  - Inline "what does undo do?" expander explaining exact reversal semantics
  - "Save as draft" with explicit destination ("visible on your home + on O-002")
  - Cost-already-incurred wording rephrased ("Conversation cost: $0.06 — applying is free")
  - `data-action-type` + `data-is-reversible` + `data-affected-entities` for AI sidebar
  - "Schedule apply for later" option with reminder
  - Diff-export action ("copy proposed change as JSON-patch for code review")

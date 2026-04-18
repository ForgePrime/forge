# Forge UX — comprehensive walkthrough (all scenarios)

> **Design contract (must-hold invariant):** Forge UX is NOT designed for build-confidence, click-approve. It is designed for **skeptical verification**. Every screen answers three questions first: **What wasn't done? What wasn't checked? What assumption was made silently?** "Approve" is a last-resort outcome, never a default.

---

## Part 0 — foundational concepts used throughout

Before the scenarios, three concepts every screen relies on:

### 0.1 Project context — persistent across all pages

Every screen has access to:
- **Active initiative:** project slug, current objective in focus, status flags.
- **Operational contract** (`.claude/forge.md`) — the project's hard constraints, preferred stack, patterns to avoid, review obligations. Injected into every LLM call (~420 tokens).
- **Active skills list** — what Forge attaches to every LLM call on this project (SKILLs, MICROs, OPINIONs).
- **Recent user actions** (last 20) — what user did, what Forge did autonomously, in chronological order. LLM sees these as implicit context.
- **Autonomy level** (L1–L5) — how much Forge does without asking.
- **Budget trajectory** — spent, projected, cap.

### 0.2 Page context — what the current screen tells the LLM

Every mockup registers itself to the LLM layer (pattern: `useAIPage` / `useAIElement` from forge-web). The LLM always knows:
- Which page user is on (`page.id = "objective-detail", page.entity = "O-002"`).
- What data is visible (task list items, current scenario count, recent ambiguity answers).
- What actions are available (buttons, slash commands, attachable skills).

When the user chats, the LLM starts with this context — zero coldstart.

### 0.3 AI sidebar — collaboration surface

Persistent right-side panel on every page. Contains:
- **Chat** with page-aware LLM — user types `@T-005` mentions, slash commands (`/find-ambiguity`, `/generate-scenarios`, `/replay`), free-form requests.
- **Suggestion chips** contextual to the page: e.g., on objective detail, suggests "generate non-happy-path scenarios", "find missing KR", "compare with O-001".
- **Token counter** showing how much context is injected right now.
- **Capability contract** — what LLM can / cannot do on this page. Explicit. No silent refusals.
- **Tool-call stream** — every time LLM uses a tool (read file, edit task, resolve ambiguity), the call + result is rendered in the sidebar as a collapsible card.
- **Skill picker** — inline "attach this skill for this one request" without going to project config.
- **Impact alert** — before LLM does anything destructive (close task, rewrite AC, delete KB source), a preview + consent prompt.

---

## Part 1 — 10 scenarios of increasing complexity

### Scenario 1 · Greenfield: new initiative to first ACHIEVED objective

**Persona:** Jakub, tech lead. Client Acme. No code yet.

1. Opens Dashboard. Sees empty state + trust-debt counters (all zero, healthy). Clicks "+ New project".
2. Creates `acme-erp-migration` as an **initiative** (no SOW required). Navigates to project page.
3. Project page shows: KB tab (empty), Objectives tab (empty), Operational Contract (default — inherited from org template).
4. **AI sidebar already open**, knows: "you're on an empty project, next expected action is adding knowledge sources".
5. Jakub uploads `legacy-docs.pdf`. In the AI sidebar, a suggestion chip appears: "Describe what this source contains so Claude can use it effectively". Jakub clicks.
6. Sidebar-guided description: free text "describes current business rules v3.2". Posted. KB source `SRC-001` created.
7. Jakub adds SharePoint URL `/migration/requirements/`. Forge asks to auth. He pastes token. Crawler indexes 12 pages. `SRC-002` created.
8. Jakub types a **manual note** directly in KB: "Client verbally confirmed on-prem-only, Python stack preferred, no Oracle". Saved as `SRC-003`.
9. Triage dashboard (top of project) shows: 3 sources · 0 objectives · 0 conflicts (yet).
10. Jakub creates **Objective O-001 "Understand current system"** — manually (title + short goal). Type marked **ANALYSIS** (task will be analysis-oriented).
11. On objective page, sidebar suggests: "Create an analysis task for this objective? Expected: reads SRC-001, SRC-002, SRC-003 · duration ~60s · cost ~$0.12". Jakub clicks.
12. **Mode selector opens.** Direct vs Crafted. For analysis across 3 sources, Forge recommends Direct (not complex enough for crafted). Jakub accepts. Runs.
13. Live panel. Jakub sees SSE stream: "reading SRC-001 chapter 2 · reading SRC-002 /page-3 · found term 'audit_log' mentioned in both". Phase A completes in 42s.
14. Deliverable card appears on objective detail. Reading: ⚠ "This task produced 5 AC and 4 test scenarios. **3 ambiguities surfaced.** **1 AC has no source attribution — LLM-invented.** Before continuing, resolve ambiguities."
15. Jakub clicks the unsourced AC. It says "System must support reports export to Excel". Jakub checks SRCs — no mention. Removes it as hallucinated. Flags skill `OP-best-dev` for review (was it too eager?).
16. Jakub opens ambiguity modal. 3 Q's. Q-001 conflicts SRC-001 ("SQL Server") vs SRC-003 ("no Oracle, prefer Python"). Jakub writes: "use PostgreSQL, confirmed with client via email 2026-04-15". Saved as new `SRC-004` manual note, auto-linked.
17. Resolves Q-002 via recommendation; explicitly edits the pre-selected option for Q-003 (doesn't want the default).
18. Scrutiny debt strip: "4 recent answers; 1 pre-selected + unedited · 1 unsourced AC removed by you".
19. Clicks **"Continue with my answers"**. Re-analysis fires. Forge sees history, knows 4 answers, does not re-ask resolved Q's.
20. O-001 becomes ACHIEVED. Auto-docs draft README; DOC task not needed yet.

**What this scenario proves:**
- Knowledge base is incremental, mixed-source.
- Analysis is a task, not a monolithic button.
- Source attribution catches a hallucination early.
- Ambiguity resolution is manual, traceable, audited.
- Re-analysis is opt-in (user clicks), not automatic.

---

### Scenario 2 · Multi-objective DAG with cross-objective conflict

**Continues from Scenario 1.**

1. Jakub creates **O-002 "Plan migration architecture"** (type PLANNING) and **O-003 "Build migration tooling"** (type DEVELOP). Both draft.
2. In O-003, sidebar proposes: "This objective depends on O-002 being planned — add edge?". Jakub confirms. DAG: O-001 → O-002 → O-003.
3. Jakub creates **O-004 "Parallel data validation during cutover"** — standalone, marked DEVELOP.
4. Runs analysis on O-002. Takes 3 min (crafted mode, 5 sources). Produces: 5 AC, 6 test scenarios, **4 ambiguities**, and flags "this objective assumes strangler-fig migration, which contradicts O-004's assumption of parallel validation during cutover — strangler-fig implies sequential, not parallel".
5. **Cross-objective conflict alert** pops on dashboard. Links both O-002 and O-004 side-by-side. Sidebar shows: "Q-A: is migration parallel (O-004) or sequential (O-002)? Both can't coexist."
6. Jakub realizes O-004's objective description implies parallelism but the KB doesn't actually require it. He **re-opens O-004 with gap note**: "Remove parallel assumption; align with strangler-fig from O-002."
7. History preserved — the DONE state of O-004 draft is kept as v1, new work overlays as v2.
8. Sidebar: "Should I re-run analysis on O-004 with the new constraint?". Jakub: yes.
9. Analysis reruns. Produces new AC, acknowledges strangler-fig, notes "parallel validation now means 'reconciliation script' not 'concurrent dual-write'". Resolves the cross-objective conflict.
10. DAG lint (post-stage hook) fires after planning. Detects O-004 critical path is 3 tasks. Annotates.

**What this scenario proves:**
- Objectives can conflict across boundaries; conflict detection is a feature.
- Re-open is not just for failed tasks — objectives evolve.
- History is preserved in versions; nothing overwritten silently.
- Cross-objective insight is a skill running post-analysis.

---

### Scenario 3 · Autonomy level L2 → L3 promotion

**2 weeks later. Jakub has run 34 tasks. Forge is at L2.**

1. Dashboard shows **autonomy bar** at L2 with promotion criteria: "4 clean runs needed · 2 cleared · 2 to go".
2. Jakub runs another objective's analysis + planning chain. No user override, no budget exceedance. Score: clean.
3. Next day, banner appears: "L3 unlockable. Forge would auto-run analysis→planning within phase unattended; user reviews result. **What this changes:** 5min wait reduced to ~1min; cost control unchanged ($5 per run cap enforced); user review required before develop."
4. Jakub reads the change-set. Sidebar offers: "Preview what a typical L3 run looks like — replay of last objective as if at L3".
5. Sidebar runs replay: shows timeline with proposed auto-steps. Jakub sees: at Q-008 (pre-selected recommendation), L3 would have auto-accepted. But user had overridden.
6. Jakub: "I want L3 only for objectives I haven't flagged as watchlist". Adds flag "critical-review" to O-002 (has HIPAA scope) and O-005 (billing).
7. Accepts L3 promotion. Flagged objectives stay manual; others become L3-eligible.
8. 3 days later, an L3-auto-run on O-007 passes cleanly without user input. Digest notification: "1 task ran autonomously at L3. No overrides needed. View session →".

**What this scenario proves:**
- Autonomy is earned via mechanical criteria, not flipped.
- Promotion comes with a replay of what would have been auto-done — evidence.
- Partial autonomy per-objective via watchlist.
- Digest mode prevents notification fatigue.

---

### Scenario 4 · Deliverable review uncovers a hallucination — skeptical mode

**Task DT-019 "Implement patient record API" DONE.**

1. Jakub opens task deliverable. Top card: "⚠ This task is closable — but is it closable *safely*? 5 scenarios executed, 2 deferred, 1 challenger concern unresolved, 1 AC unsourced."
2. Metrics row under "What to scrutinize". Clicks "5 verified — + 3 refused to verify" on challenger tile.
3. Expands. Challenger says: refused to verify (a) OWASP top 10, (b) compliance with SRC-001 §3.2, (c) integration with existing `legacy_users` table.
4. Jakub realizes (c) — the legacy users table mentioned in SRC-001 — was never referenced in the task. He grep-scan the code: new endpoint uses `users` table, not `legacy_users`. **This is a silent integration bug.**
5. Sidebar: "Want me to reverse-trace this?". Clicks yes.
6. Reverse-trace UI opens: bug symptom "integration missing" → task prompt DT-019 → planning task PT-004 → objective O-003 → ambiguity resolution Q-014 ("should we write to legacy_users or new users?" → user answered "new users").
7. Jakub's own answer was actually WRONG — client meant write to both during migration. User misread SRC-001 §4 about dual-write.
8. Jakub re-opens O-003 with gap note: "dual-write was required per SRC-001 §4.1, not addressed in Q-014 resolution".
9. Lessons log extractor fires: captures "ambiguity answered by user based on incomplete KB read · add 'cite SRC' requirement to future ambiguity UI".
10. Anti-pattern registry: "single-write migration where dual-write required" → linked to this episode for future projects.
11. Jakub triggers re-plan on O-003 tasks affected. DT-019 reopens as TODO with constraint "must support dual-write per SRC-001 §4.1".

**What this scenario proves:**
- Scope limits (what challenger refused) caught a silent bug.
- Reverse-trace UI is not theoretical — it's a diagnostic tool.
- Lessons + anti-patterns turn one incident into project/org learning.
- Re-open preserves history while adding new constraint.

---

### Scenario 5 · Cost overrun mid-run: pause and rebalance

**Orchestrate run of O-006 "Build reporting dashboard" — 8 tasks planned.**

1. Run starts. Budget $10, estimated total $4.50.
2. Task 3 of 8 finishes. Trajectory forecast updates: "at current pace, projected $15.30 / $10 cap · **budget likely to exceed**". Red pulse on the bar.
3. Sidebar: "Why the drift? T-006-003 retried 4 times due to failing mypy gate. Each retry grew context by ~1200 tokens. Consider pausing."
4. Jakub pauses. Opens **cost forensic drill-down** for T-006-003: Phase A $0.12, but 4 retries at $0.18 each for a total $0.84. Root cause: the type hints the LLM wrote use `list[str]` which conflicts with the project's `typing.List` imports (a contract directive).
5. Sidebar: "Operational contract says 'prefer modern typing (list[str])'. Type stubs in code use old style. Conflict. Options: (a) update code to new style, (b) relax contract for this task."
6. Jakub fixes code (2 min). Resumes run.
7. Remaining 5 tasks finish without retries. Total cost $4.80 — within budget.
8. Forge records: "contract-vs-code mismatch detected · auto-suggest contract-sync skill for all Python projects next time".

**What this scenario proves:**
- Mid-run trajectory forecast is actionable, not cosmetic.
- Cost forensic drill-down reveals root cause (retries growing context), not just total.
- Contract and code can drift — Forge surfaces the delta.
- Lesson captured → future projects benefit.

---

### Scenario 6 · Interrupt mid-LLM-work and redirect

**Jakub runs crafted-mode analysis on O-008. Budget permit: $2.**

1. Sidebar streams: "crafter reading SRC-001 chapter 2 · crafter reading SRC-005 board deck Q1.pptx...".
2. **Jakub stops typing — SRC-005 is the board deck he de-prioritized earlier** (conflicts with SRC-003 manual note). The crafter shouldn't read it.
3. Clicks "interrupt". LLM stops mid-read.
4. Sidebar shows confirmation dialog: "interrupt at phase 'crafting prompt', 12% complete, $0.08 spent. Redirect to new focus or abort?".
5. Jakub: "redirect — exclude SRC-005 from KB scope for this task, continue with SRC-001–004 only".
6. Crafter resumes with updated scope. Uses the already-loaded SRC-001 context (cached). Redoes KB selection.
7. Analysis completes. Total cost $0.71 vs expected $1.20 (saved by interrupt + cache).
8. Audit log: "user interrupted crafter · reason 'excluded SRC-005 deck due to on-prem conflict'. Forge updated default KB scoping rule: 'board decks excluded unless explicitly opted in'".

**What this scenario proves:**
- Interrupt + redirect are first-class, not emergency.
- LLM work caches where possible; redirect reuses partial context.
- Per-interrupt audit log for accountability.
- Interrupts can yield new default rules.

---

### Scenario 7 · Anti-pattern surfaces in new project via org marketplace

**2 months later. New project `acme-billing-redesign` started.**

1. Jakub creates initiative. Adds KB (similar structure to ERP project).
2. Creates O-001 analysis. About to run.
3. Sidebar suggestion chip: "⚠ In your previous ERP project, an ambiguity (Q-014) was answered wrong because user didn't cite SRC. Org-level skill `SK-cite-src-enforcer` is available in marketplace, used by 7 other projects with 85% success. Install for this project?".
4. Jakub installs. It gets added to project skill library.
5. O-001 analysis runs. When generating ambiguities, skill enforces: each Q must reference specific SRC snippet + user answer must cite SRC too.
6. User answers Q-003 without citation. UI blocks with modal: "You said 'use daily batch'. Which SRC does this come from? If your own decision, type 'manual' and briefly justify."
7. Jakub: types "manual — client verbal confirmation 2026-07-02". Auto-created SRC-005 for this.
8. Anti-pattern from ERP project not repeated.

**What this scenario proves:**
- Cross-project learning via marketplace scales.
- Previously-identified anti-patterns pre-empt future cases.
- Skills enforce via UI, not just in-prompt (hard gate).

---

### Scenario 8 · Replay harness catches platform regression

**Forge platform releases a new version of the planning skill.**

1. Admin runs a replay batch: take 10 archived ACHIEVED planning tasks from 3 projects. Replay them with today's skills + contract.
2. Results dashboard: 7 of 10 achieve "equal or better quality"; 3 show regression (fewer ACs, lower challenger agreement).
3. Drill into 1 regression: plan output is shorter, missing 2 AC from original. Comparison side-by-side.
4. Admin: "regression real — new planning skill drops AC when KB has >5 sources. Rollback or patch".
5. Rollback the skill version. Replay again. Back to parity.

**What this scenario proves:**
- Replay harness detects platform regression that users would've silently absorbed.
- Skills are versioned; rollback is a first-class operation.

---

### Scenario 9 · Full autonomy run delivers with digest-only interaction

**L5 autonomy enabled for O-012 "Add reporting API endpoints". Watchlist off.**

1. Jakub sleeps. Forge runs analysis (no ambiguities — skill auto-resolved 2 using contract rules), planning (6 tasks generated), develop (all 6 tasks run).
2. DOC task auto-runs. README updates, API reference extended.
3. Digest at 08:00: "O-012 ACHIEVED overnight. 6 tasks DONE. 2 findings auto-triaged and 1 converted to follow-up (FD-045). $6.40 spent of $10 cap. 3 new lessons captured. View replay →".
4. Jakub reviews digest over coffee. Clicks FD-045 — a medium finding about N+1 queries. Accepts it as follow-up for next sprint.
5. Opens replay of one random task. Checks that challenger scope limits were honored (they were). Spot-check passes.
6. Jakub moves to next task. Forge runs O-013 next day at L5.

**What this scenario proves:**
- L5 autonomy is trustworthy because: hard cap, watchlist, digest, auditable trace, replay.
- User's role at L5 is auditor, not operator.

---

### Scenario 10 · Client audit — documentation is the deliverable

**End of engagement. Client wants handoff.**

1. Jakub opens Documentation tab. Two layers visible:
   - Auto-drafted (live): README, API reference, DB schema, changelog.
   - DOC-task-polished: Architecture overview, 3 ADRs, deployment guide, runbook.
2. Plus per-objective rollups: inputs consumed, outputs produced, cost+time, 3-5 lessons each.
3. Share link generated: capability URL, expires 90 days, view-only.
4. Client opens link. Sees clean docs. In "Sources excluded from documentation" banner: SRC-005 (board deck) — user excluded due to conflict with on-prem constraint. Client confirms this was correct.
5. Client inspects one ADR: Architecture → Django over FastAPI. Rationale cites SRC-003 team experience + O-002 analysis task. Client accepts.
6. Reverse-trace available: client clicks on any code file, sees the objective + task + ambiguity chain. Full transparency.
7. Jakub adds DOC task "Write handoff runbook for Acme ops team". Runs. Polished 5-page .md.
8. Client receives final bundle: code repo + Forge-generated docs + full audit trail export.

**What this scenario proves:**
- Deliverable is code + docs + audit trail, not just code.
- Client-facing views hide internals but expose enough for trust.
- DOC task is a legit task type with its own AC and gates.

---

## Part 2 — scenario-spanning mechanisms

These patterns recurred across the 10 scenarios — they're the platform's spine.

### AI sidebar recurring roles
- **Orient:** "you're on X page, here's what's visible and what you can do".
- **Suggest:** 3-5 contextual chips per screen. Never more (noise).
- **Execute:** user can say "run this skill" / "redirect this crafter" / "find ambiguity in O-002" and sidebar orchestrates.
- **Witness:** every tool call rendered inline, expandable, auditable.
- **Guard:** before destructive ops (close task, delete KB, modify contract), impact alert with diff preview.

### Source attribution — mechanically enforced
Every artifact that an LLM produces must cite a SRC, objective, decision, or answer. Unsourced content gets a badge; user must accept or reject. Skill `SK-cite-src-enforcer` hard-gates answers in the UI.

### Cost transparency — 3 layers
1. **Pre-flight** — before any LLM call, itemized estimate (base prompt / skills / KB / output).
2. **Live** — mid-run trajectory forecast on every orchestrate run.
3. **Post-hoc** — cost forensic drill-down per task, per phase, per retry.

### Autonomy — earned, not granted
- L1 → L5, mechanical criteria: N clean runs, zero overrides, clean audit.
- Watchlist for critical objectives.
- Hard budget cap per level.
- Veto clauses override autonomy (hard constraints, budget, flagged files).
- Digest mode for autonomous runs.

### Re-open everywhere
- Task DONE → can be pushed back to TODO with gap note. History preserved.
- Objective ACHIEVED → can be re-opened. New analysis + new planning run only on delta.
- Ambiguity answer → user can re-answer. LLM sees the old+new, explains what changes.

### Memory and learning
- Lessons captured per objective on ACHIEVED.
- Anti-patterns captured on re-open.
- Skill ROI tracked: cost, hits, misses, user overrides.
- Cross-project promotion to org marketplace when pattern repeats.

### Reverse-trace always available
- From any code symbol / bug / deliverable → task → planning → objective → ambiguity → SRC.
- Enables post-mortem without archaeology.

---

## Part 3 — what Forge refuses to do

Anti-patterns that would break the skeptical contract:

- Refuses to show only green metrics. Every green is paired with "what was NOT checked".
- Refuses to make close-task easy. Closing requires either all scenarios run or explicit deferral reason.
- Refuses to hide challenger scope limits. Always visible on deliverable.
- Refuses to auto-dismiss findings silently. Each dismissal needs ≥50-char reason.
- Refuses silent skips. "Not executed" AC stays prominent until converted or deferred-with-reason.
- Refuses irreversible ACHIEVED. Always re-openable.
- Refuses to offer "Approve" as primary button. Tertiary, grey, friction-tooltip.
- Refuses to pre-select answers without flagging them "user-did-not-edit".
- Refuses to auto-resolve ambiguities at L1-L2 autonomy. Only from L4 up, and with audit.
- Refuses to truncate KB context silently to fit budget. Warns explicitly.

---

## Part 4 — sophistication markers

The 10 scenarios above demonstrate that Forge is NOT:
- A wrapper around "one /analyze button".
- A scaffold that hands off to Cursor.
- A prompt template library.
- A TODO list with AI backing.

Forge IS:
- An orchestrator of an iterative, per-objective lifecycle.
- A skeptical auditor that refuses to let LLM claims go unchecked.
- A memory system that learns from objectives and across projects.
- An autonomy ramp that grants trust gradually, mechanically.
- A deliverable factory that outputs code + docs + audit trail.

---

## Meta — what sophistication looks like in the UI

- Every button has a "plan first" mode.
- Every LLM artifact has a "why did you write this?" inline.
- Every stream of work is interruptible.
- Every objective carries its lessons and anti-patterns.
- Every close is skeptical by default; approve is last-resort.
- Every autonomous run is audited in digest form.
- Every conflict between KB sources is flagged before use.
- Every skill has ROI visible.
- Every cost has breakdown + root cause.
- Every deliverable has scope-limits disclosed.

If you find a screen that doesn't expose at least one of these, flag it as contract-drift.

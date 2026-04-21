# Process completeness after Pass 2

Honest accounting of what's covered after Pass 2 lands and what's still missing. The full target is ~52 mockups for a complete Forge process; Pass 1 delivered 9 foundation mockups, Pass 2 adds 13 creation/mutation mockups. Total: 22 of ~52.

---

## Pass 2 — what's now covered

### Group A — KB source intake (5 mockups)

| # | File | Capability unlocked |
|---|------|---------------------|
| 1 | `02v2-add-source-file.html` | User can upload a file (PDF/DOCX/MD/TXT/HTML) with description (≥30 chars), focus hint, scopes, and see overlap detection vs existing SRC-NNN before queuing for analysis reuse. |
| 2 | `02v2-add-source-url.html` | User can register a URL source with auth (none/basic/token/SharePoint OAuth), crawl scope (single/recursive/same-domain) + path globs, schedule, with test-connect + dry-run preview + robots.txt indicator. |
| 3 | `02v2-add-source-folder.html` | User can register a local/mounted folder with include/exclude globs, gitignore respect, sample scan preview, and sensitive-file warning that surfaces missed exclude patterns. |
| 4 | `02v2-add-source-note.html` | User can write a manual markdown note tied to category + linked decisions/objectives — pure user content, no LLM cost at save. |
| 5 | `02v2-source-preview.html` | User can browse post-extraction chunks of a source with search-within-source, per-chunk freshness, citation list (which entities cited what), and source-level actions. |

### Group B — Objective creation + mutation (4 mockups)

| # | File | Capability unlocked |
|---|------|---------------------|
| 6 | `03v2-create-objective.html` | User can create a new objective with title, business_context (≥100 chars), priority, scopes, dependencies (live DAG preview), KB focus, and ≥1 measurable KR. **Save is BLOCKED while any KR is unmeasurable.** |
| 7 | `09-reopen-objective.html` | User can re-open an ACHIEVED objective with mandatory gap note (≥50 chars) + auto-spawn analysis toggle. History preserved, downstream re-blocks. |
| 8 | `09-edit-challenger-checks.html` | CRUD for per-objective challenger rules with severity/scope, "suggest from scenarios", live Phase C prompt-injection preview, and per-task cost projection. |
| 9 | `09-edit-dependencies.html` | DAG edit centered on focused objective with hard/soft toggle, inline cycle prevention with forming-path tooltip, and impact preview for hypothetical changes. |

### Group C — Task-level actions (4 mockups)

| # | File | Capability unlocked |
|---|------|---------------------|
| 10 | `05v2-close-task.html` | Close a NOT_DONE task with each unresolved finding addressed-or-deferred, a ≥100-char close reason, and typed full-name signature. Audit-logged with signature. |
| 11 | `05v2-create-followup-task.html` | Spawn a follow-up task pre-filled from a finding's text, with auto-attached skills, draft AC, and cost preview. |
| 12 | `05v2-scenario-generate.html` | Live progress for "generate test & run now" — phase tracker, streaming console, drafted code preview, cost meter, cancellable at boundaries. |
| 13 | `05v2-assign-auditor.html` | Assign manual AC verification to internal `can_audit` user OR external auditor by email, with verification notes, due-by, reminder cadence, and notification preview. |

After Pass 2, **every read-only navigation surface from Pass 1 has a corresponding mutation surface.** A user can not only view a project, but also: add KB sources of all 4 types, create objectives, re-open objectives, edit challenger rules + dependencies, close tasks with audit, spawn follow-ups, generate test scenarios live, and assign manual auditors.

---

## Pass 1 + Pass 2 combined coverage

| Surface area | Pass 1 | Pass 2 | Status |
|---|---|---|---|
| Answer ambiguity | ✓ | — | covered |
| Add AC / scenario | ✓ | — | covered |
| New task wizard | ✓ | — | step 1 only; steps 2/3 still TBD |
| Crafter preview | ✓ | — | covered |
| Project config tabs (skills/hooks/defaults) | ✓ | — | covered |
| Skill edit + hook add | ✓ | — | covered |
| Generic destructive preview modal | ✓ | — | covered (reused by Pass 2 archives) |
| KB source intake — 4 types | — | ✓ | covered |
| Source detail view (read chunks) | — | ✓ | covered |
| Objective creation | — | ✓ | covered |
| Objective re-open | — | ✓ | covered |
| Objective dependency edit | — | ✓ | covered |
| Per-objective challenger checks | — | ✓ | covered |
| Task close with reason | — | ✓ | covered |
| Follow-up task creation | — | ✓ | covered |
| Live scenario generation | — | ✓ | covered |
| Manual auditor assignment | — | ✓ | covered |

---

## Pass 3 — what's still missing (target: ~10 mockups)

### Task-report variants for non-develop types (5 mockups, deferred from earlier Pass 2 plan)
- `05v2-analysis-deliverable.html` — outputs ambiguities, draft AC, scenarios, source-coverage map. No git diff.
- `05v2-planning-deliverable.html` — outputs DAG of develop tasks, AC distribution per task, KB-scope decisions. DAG lint, no orphan AC.
- `05v2-doc-deliverable.html` — ADR docs, API ref, changelog. Citation completeness gate.
- `05v2-task-failed.html` — FAILED state w/ stack trace, retry options, "convert to investigation".
- `05v2-task-replay.html` — historical task replayed against new skill version (side-by-side diff).

### Source / KB lifecycle (3 mockups)
- `02v2-edit-source.html` — re-ingest, update description/focus, archive.
- `02v2-source-conflict-resolver.html` — pick one source over another (or exclude one) when overlap-check escalates.
- `02v2-archive-source.html` — destructive confirm using `16-preview-apply-modal` shell.

### Auditor's other side (2 mockups)
- `05v2-auditor-inbox.html` — what J. Patel sees in his inbox: list of pending audits.
- `05v2-auditor-review.html` — single audit review surface where J. Patel marks PASSED/FAILED/NEEDS-CLARIFICATION.

---

## Pass 4 — admin / cross-project / client-facing (target: ~10 mockups)

These exist outside a single project's bubble. Forge currently has zero coverage here.

- `00-org-dashboard.html` — multi-project digest, cost rollup, autonomy-level dashboard, org-wide skill-usage.
- `00-org-skills-marketplace.html` — org-shared skill library distinct from project-installed.
- `00-org-budget.html` — per-project caps, monthly spend, alerts.
- `00-org-team.html` — users + roles (incl. `can_audit`) + project memberships.
- `00-audit-log-search.html` — full audit log with filter + drilldown.
- `00-incidents.html` — lessons_learned table cross-referenced to projects.
- `00-replay-cohort.html` — admin UI to replay a cohort against a new skill version.
- `client-share-dashboard.html` — read-only project view shared with client.
- `client-share-objective.html` — shareable objective detail (filtered for external eyes).
- `client-share-deliverable.html` — shareable task deliverable.

---

## Pass 5 — failure / interrupt / cost / autonomy / advanced flows (target: ~10 mockups)

The walkthrough scenarios 03–10 in `walkthrough.md` describe these.

- `04-cost-overrun-pause.html` — mid-run cost overrun, pause + forensic.
- `04-budget-cap-hit.html` — budget cap hit.
- `04-interrupt-mid-crafter.html` — user stops a crafter mid-execution.
- `04-orchestrate-failed.html` — task crashed, recovery options.
- `04-rollback.html` — rollback a completed task's git changes.
- `12-autonomy-promote.html` — L2 → L3 promotion ceremony.
- `12-autonomy-watchlist.html` — running watchlist items.
- `12-autonomy-overnight-run.html` — L5 overnight run digest.
- `13-replay-suite.html` — replay a cohort.
- `14-anti-pattern-warn.html` — marketplace skill warns project from prior lesson.
- `15-hallucination-trace.html` — reverse-trace a hallucinated AC.
- `change-request-impact.html` — `/change-request` blast radius.
- `compound-extract.html` — extract lessons learned.
- `discover-explore.html` — `/discover` topic exploration.

---

## Honest gap list — what Pass 2 explicitly did NOT do

1. **No editor surface for objects.** `09-edit-challenger-checks.html` and `09-edit-dependencies.html` cover specific aspects of objective mutation, but a generic `03v2-edit-objective.html` (full edit of title, context, KRs) is still missing — it would mostly mirror `03v2-create-objective.html` in edit mode.

2. **No source-level edit/re-ingest surfaces.** Once a source is added (Pass 2 forms), changing its metadata, re-ingesting it on demand, or archiving it requires `02v2-edit-source.html` (Pass 3).

3. **Auditor's other side is not built.** Pass 2 builds `05v2-assign-auditor.html` (the assigner's view) but not `05v2-auditor-inbox.html` or the review surface where the auditor actually does the work and sends a verdict back.

4. **Live progress UX is shown for one flow only.** `05v2-scenario-generate.html` has a great phase tracker + console pattern. The same shell should reappear for: source crawl-in-progress, ingest analyze-in-progress, replay-in-progress — but only the scenario-generation case is mocked.

5. **No source-conflict resolver.** When `02v2-add-source-file.html` detects overlap with SRC-001, it surfaces an amber warning + link to a future page. That destination (`02v2-source-conflict-resolver.html`) is not yet built — clicking the link in Pass 2 dead-ends to the existing ambiguity page.

6. **No bulk operations.** Bulk close findings, bulk re-assign auditor, bulk re-crawl sources — none in Pass 2. Each action is per-entity.

7. **No empty / loading / error states for the 13 new mockups.** Every form is shown in the "happy filled-in" variant.

8. **DB schema implications listed in annotations but not validated.** Pass 2 introduces several implied new columns (`task.close_reason`, `task.close_signature`, `finding.defer_reason`, `manual_verification_task` table, `scenario_generation_run` table, `objective.reopen_history[]`, `objective.challenger_checks[]` JSONB shape, etc.). These are flagged in each annotation panel under "NEW DB columns implied" but a unified schema-impact doc is not produced.

9. **No mobile/responsive variant.** All 1280px desktop.

10. **Generic preview-apply modal not invoked.** Several Pass 2 destructive actions (re-open without analysis, remove a check, remove a dep, archive source) WOULD use `16-preview-apply-modal.html` but the Pass 2 mockups inline-confirm rather than show the modal trip. This is a UX-density choice — the modal should be reserved for actions with non-trivial blast radius (the Pass 1 example: removing an AC + logging incident).

11. **No translation between Pass 2 forms and the wizard pages.** `05v2-create-followup-task.html` Continue button points at `07-new-task.html` — but Pass 2 doesn't build the variant of `07-new-task.html` that's pre-filled from a follow-up. The user lands on a new-task form that ignores the pre-fill.

12. **AI sidebar is one-liner annotations only.** Same gap as Pass 1 — the actual sidebar component is referenced but not rendered.

---

## Judgment calls flagged for review (DB / schema impact)

These were implied by the mockups but warrant explicit confirmation against the actual schema:

- **`objective.reopen_history[]` JSONB array** — needed if re-open can happen N times (Pass 2 assumes yes). If schema only has scalar `objective.reopened_at`, the history-of-reopens model needs a migration.
- **`objective.depends_on[]` element shape** — Pass 2 shows hard/soft toggle per edge. If schema stores `depends_on[]` as plain string[], adding kind requires either a wrapper object `{objective_id, kind}` or a parallel `depends_on_kinds[]` array.
- **`objective.challenger_checks[]` schema** — referenced as JSONB in CLAUDE.md. Pass 2 assumes per-check `{id, text, severity, applies_to_task_types[], source}` shape. If the actual schema is just `text[]`, severity + scope need to move into the JSONB.
- **`finding` lifecycle** — Pass 2 introduces statuses OPEN / ADDRESSED / DEFERRED / INVALID with `defer_reason`, `deferred_by_task_id`, `addressed_by_task_id`. If `finding` table is currently flat, this is a real migration.
- **`manual_verification_task` table** — entirely new in Pass 2. Captures human-audit assignments distinct from regular tasks.
- **`scenario_generation_run` table** — new in Pass 2. Captures the multi-phase run with cancellation/replay support.
- **`source.weight_overrides[]`** — referenced in `03v2-create-objective.html` KB-focus list ("down-weighted per SRC-009 note"). Implies a per-source weight-modifier table that listens to "supersedes" links in notes.
- **`user.roles[]`** — Pass 2 introduces `can_audit` role. If user-role model is single-string, this needs to become an array or junction table.
- **`citation` table** — referenced in `02v2-source-preview.html`. If citations are inferred (string-search at render time) instead of materialized, the per-chunk "Referenced by" panel won't perform at scale.
- **`audit_log.signature`** — `05v2-close-task.html` requires storing the typed signature alongside close action. If `audit_log` is just `{action, actor, ts, payload}`, signature should be a payload field — but explicit storage helps audit queries.

None of these are blockers for the mockups themselves (mockups are static), but each is a flag for backend planning.

---

## Explicit scope limits — what Pass 2 did NOT do

1. **Did NOT update the existing `09-objective-detail.html`** to add buttons that link to the new Pass 2 surfaces. The breadcrumbs + AI sidebar suggestions on Pass 2 mockups assume those entry points exist — they currently rely on user navigating via URL or via the new mockups linking back. Updating `09-objective-detail.html` to surface "Re-open" / "Edit deps" / "Edit challenger checks" buttons is a Pass 3 polish item.

2. **Did NOT update `02v2-project-kb.html`** to add the 4 distinct "+ Add file/URL/folder/note" buttons. Currently `02v2-project-kb.html` has a single "+ Add source" button (per Pass 1 Revised). The 4 Pass 2 forms exist; the entry-point UI tile to pick the 4 types is implicit.

3. **Did NOT update `05v2-task-deliverable.html`** to add Close / Create-followup / Generate-scenario / Assign-auditor inline action affordances. The new mockups assume these affordances exist.

4. **Did NOT build the 9c "Confirmation modal for objective re-open"** — `09-reopen-objective.html` is a full-page form, not a modal. A future variant could be the modal version invoked from list views. Pass 2 deliberately chose full-page for the destructive-but-rich workflow.

5. **Did NOT verify all annotations cite real DB tables.** Annotations reference table/column names that follow the patterns from Pass 1. A schema audit comparing annotation references to actual schema is recommended before any backend implementation begins.

6. **Did NOT add new walkthrough scenarios.** The 10 scenarios in `walkthrough.md` still describe the original flows. Pass 2 adds capability surfaces but doesn't extend the narrative.

7. **Did NOT alter `walkthrough.md` or `flow.html`.** Those are reference docs; updating them is a separate task that should follow Pass 3 to capture the mature flow set.
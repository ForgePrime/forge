# Process completeness after Pass 1

Honest accounting of what's covered after Pass 1 lands and what's still missing across Passes 2–5. The full target is ~52 mockups for a complete Forge process; Pass 1 delivers 9. This is the foundation pass — its purpose is to make every later page have something real to link back to.

---

## Pass 1 — what's now covered

| # | File | Capability unlocked |
|---|------|---------------------|
| 1 | `09-answer-ambiguity.html` | User can resolve a HIGH/MEDIUM ambiguity with source-grounded reasoning, alternatives extracted from sources, defer with reason, per-option impact preview. **The single biggest UX gap** — Forge's whole skeptical-UX value contract hinges on this page. |
| 2 | `09-add-scenario.html` | User can add non-happy-path scenarios (edge / failure / security / regression) post-hoc to an objective. |
| 3 | `09-add-ac.html` | User can add or refine an acceptance criterion with required source attribution; INVENTED ACs are explicitly flagged. |
| 4 | `07-new-task.html` | Wizard step 1 — task details (title, instruction, AC, deps, KB scope) for any of the 4 task types. Lands the user into the existing `07-mode-selector.html` for step 2. |
| 5 | `07-crafter-preview.html` | Before paying executor cost (~$0.42), user inspects the crafter's output, what KB was read, what code was inspected, what the crafter explicitly did NOT do. |
| 6 | `12-skills-tab.html` | Project config — full list of attached skills with cost-impact summary, attachment-mode column, detach action. |
| 7 | `12-hooks-tab.html` | Project config — 4 hooks rendered as editable rows with firing history, condition expression, on-failure behavior. |
| 8 | `12-phase-defaults-tab.html` | Project config — 4-column matrix of which skills run as default per phase, with org-vs-project layer indicator. |
| 9a | `12-add-hook.html` | Form for creating a new post-stage hook with stage/skill/condition/cost-projection. |
| 9b | `11-skill-edit.html` | Skill creation/edit form with prompt template, applies-to-phases, auto-attach rule (visual + JSON), cost impact, version history, conflict-check. |
| 9c | `16-preview-apply-modal.html` | Generic destructive-action preview that the AI sidebar uses for any state mutation. Reused by many future Pass 2+ flows. |

After Pass 1, every navigation/viewing-layer mockup has a destination form to land on for its primary actions. The "+ task", "+ AC", "+ scenario", "Answer →", "Edit", "+ Add hook" buttons all point at real pages now.

---

## Pass 2 — task-report variants for non-develop types (target: 6 mockups)

`05v2-task-deliverable.html` shows a develop task. The other 3 task types need parallel deliverable pages because the artifacts are different:

- `05v2-analysis-deliverable.html` — outputs ambiguities (linked to `09-answer-ambiguity`), draft AC, scenarios, source-coverage map. No git diff. Verification = challenger checked alignment.
- `05v2-planning-deliverable.html` — outputs DAG of develop tasks, AC distribution per task, KB-scope decisions per task. Verification = DAG lint passed, no orphan AC, task-size cap respected.
- `05v2-doc-deliverable.html` — outputs ADR documents, API ref, changelog rollups. Verification = citation completeness, stale-link scan passed.
- `05v2-task-failed.html` — task FAILED state (test failures, LLM errored, gate blocked). Stack trace, retry options, "convert to investigation task" path.
- `05v2-task-replay.html` — historical task being replayed (skill version drift visible, side-by-side original vs replay diff).
- `05v2-task-archived.html` — archived task in read-only mode (preserved for audit; no buttons that mutate).

---

## Pass 3 — admin / cross-project / client-facing surfaces (target: 12 mockups)

These exist outside a single project's bubble. Forge currently has zero coverage here.

- `00-org-dashboard.html` — multi-project digest, cost rollup, autonomy-level dashboard, org-wide skill-usage stats.
- `00-org-skills-marketplace.html` — org-shared skill library distinct from project-installed.
- `00-org-budget.html` — per-project budget caps, monthly spend, alerts.
- `00-org-team.html` — users + roles + project memberships.
- `00-audit-log-search.html` — full audit log with filter + drilldown.
- `00-incidents.html` — lessons_learned table (skill-leak incidents, regression catches) cross-referenced to projects.
- `00-replay-cohort.html` — admin UI to replay a cohort of past tasks against a new skill version.
- `client-share-dashboard.html` — read-only project view shared with client (no buttons, no costs, only deliverables + ADRs + open ambiguities).
- `client-share-objective.html` — shareable objective detail (filtered for external eyes).
- `client-share-deliverable.html` — shareable task deliverable (no internal LLM costs/skill traces).
- `client-handoff-summary.html` — end-of-engagement summary doc generator.
- `client-share-link-config.html` — user configures what's visible in the shareable URL.

---

## Pass 4 — onboarding + management of objects we haven't seen creation forms for (target: 10 mockups)

- `02v2-add-source.html` — add a new KB source (file upload / URL paste / SharePoint folder picker / manual note). 4 source types, each with its own field set.
- `02v2-edit-source.html` — re-ingest, update description/focus, archive, delete.
- `02v2-source-conflict-resolver.html` — when 2 sources contradict, this is the page where user picks (or excludes one).
- `03v2-add-objective.html` — create a new objective (title, description, depends_on, blocks, KB-scope inheritance).
- `03v2-edit-objective.html` — same form, edit mode + status transitions.
- `03v2-archive-objective.html` — confirmation page for archiving (destructive, uses `16-preview-apply-modal`).
- `12-edit-contract.html` — the operational-contract editor as its own focused page (currently embedded in `12-project-config`).
- `12-edit-contract-history.html` — diff between contract revisions.
- `01-create-project.html` — empty-project creation form (fills the gap that `02-project-empty.html` v1 awkwardly tried to handle).
- `01-archive-project.html` — destructive archive confirmation.

---

## Pass 5 — failure / interrupt / cost / autonomy + advanced flows (target: 15 mockups)

The walkthrough scenarios 03–10 in `walkthrough.md` describe these flows. Pass 1 doesn't deliver any of them.

- `04-cost-overrun-pause.html` — mid-run cost overrun, pause + forensic.
- `04-budget-cap-hit.html` — budget cap hit, what user can do.
- `04-interrupt-mid-crafter.html` — user stops a crafter mid-execution.
- `04-orchestrate-failed.html` — task crashed, recovery options.
- `04-rollback.html` — rollback a completed task's git changes.
- `12-autonomy-promote.html` — L2 → L3 promotion ceremony with watchlist, blockers.
- `12-autonomy-watchlist.html` — running watchlist items that block promotion.
- `12-autonomy-overnight-run.html` — L5 overnight run digest.
- `13-replay-suite.html` — replay a cohort to validate skill change.
- `14-anti-pattern-warn.html` — marketplace skill warns project from prior lesson.
- `15-hallucination-trace.html` — reverse-trace a hallucinated AC back to wrong user answer.
- `15-decision-redo.html` — redo a closed decision (with cascade impact preview).
- `change-request-impact.html` — `/change-request` shows blast radius.
- `compound-extract.html` — extract lessons learned from a completed objective.
- `discover-explore.html` — `/discover` topic exploration before planning.

---

## Honest gap list — what Pass 1 explicitly did NOT do

1. **No real forms for the 3 non-develop task types' deliverables.** A user clicking on a completed analysis task today still lands on the develop-shaped `05v2-task-deliverable`. Pass 2 fixes this.
2. **No empty / loading / error states for the 9 Pass-1 mockups themselves.** Every form is shown in the "happy filled-in" variant. Server errors, network failures, cost-cap-hit modals from within these forms are not mocked.
3. **No multi-step wizard for steps 2 and 3** of new-task — `07-mode-selector` exists from before, but `07-new-task-confirm.html` (step 3) is not built. User flow currently jumps from step 2 (mode) to live execution `04-orchestrate-live` without an explicit confirm step.
4. **No "+ Add task-specific AC" inline form invoked from `07-new-task`** — the button is shown but lands users back on `09-add-ac` (which assumes it attaches to objective). Pass 2 needs a per-task variant or modal version.
5. **No mobile / responsive variant.** All mockups target a 1280px desktop viewport.
6. **No dark mode.** Single light theme.
7. **No keyboard navigation flow** beyond the ⌘K palette indicator. No actual modal trap, no focus management, no aria-* attributes.
8. **AI sidebar integration is one-liner annotations only** — the actual sidebar component isn't rendered on these 9 pages. Reader infers from `16-ai-sidebar.html`.
9. **No animations / transitions documented** between states (e.g., what happens when "Save + re-analyze" is clicked but the re-analysis takes 90s — is there a progress page?).
10. **No localization variants.** All copy is English (despite `lang="pl"` in the HTML — kept for consistency with existing files).
11. **No accessibility audit.** Color contrast and heading hierarchy not verified against WCAG.
12. **Generic preview-apply modal** (`16-preview-apply-modal`) is shown with one example (Remove AC-5). The other ~10 destructive actions that should reuse it are listed in the annotation but not individually mocked.

---

## What's reasonable to expect from Passes 2–5

If Pass 1 took 9 mockups in 1 invocation, the remaining 43 mockups split across 4 passes of roughly 10–12 each is realistic. Recommended ordering:

- **Pass 2** (task-report variants) — depends on no other passes; can ship next.
- **Pass 3** (admin / client) — depends on Pass 2 because client-share pages reuse the deliverable shells.
- **Pass 4** (creation forms for sources / objectives / contract) — independent; could ship in parallel with Pass 2.
- **Pass 5** (failure / interrupt / cost / autonomy / advanced flows) — depends on Passes 2 and 4 because these flows often start from a completed task or a configured project.

Total expected to reach the "complete process" goal: ~52 mockups, of which 19 already exist (10 Revised + 9 Pass-1).

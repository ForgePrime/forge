# Process completeness after Pass 3

Honest accounting of what's covered after Pass 3 lands and what's still missing. The full target is ~52 mockups for a complete Forge process; Pass 1 delivered 9 foundation, Pass 2 added 13 creation/mutation, Pass 3 adds 5 task-deliverable variants + auditor surfaces. **Total: 27 of ~52.**

---

## Pass 3 — what's now covered

### Group A — Non-develop task-deliverable variants (3 mockups)

| # | File | Capability unlocked |
|---|------|---------------------|
| 1 | `05v2-analysis-deliverable.html` | Full ANALYSIS task report — 6 ambiguities (4 inline-resolved, 2 escalated to Q-007/Q-008), 5 AC drafted (1 INVENTED from excluded source), 4 scenarios generated, per-source chunks-read + citations extracted, SRC-005 explicit exclusion, challenger verification of extraction fidelity, analysis-specific close-safety (Q persistence on objective, not on task). |
| 2 | `05v2-planning-deliverable.html` | Full PLANNING task report — 12-task DAG (+1 doc) with critical-path SVG, fanout warning (DT-001 blocks 7), AC coverage matrix (5 O-002 AC × 12 tasks), challenger acyclic-check + size-distribution + velocity concerns, planning-specific close-safety (DRAFT discard if not approved). |
| 3 | `05v2-documentation-deliverable.html` | Full DOC task report — 3 artifacts produced (architecture.md, ADR-001, README update), 29 citations resolved, 2 unsourced-claim paragraphs flagged via citation-density heatmap, ADR section completeness check, DOC-specific close-safety (artifacts stay regeneratable; freeze paths explained). |

### Group B — Auditor's side of the loop (2 mockups)

| # | File | Capability unlocked |
|---|------|---------------------|
| 4 | `05v2-auditor-inbox.html` | External auditor (J. Patel) sees their pending audit assignments across projects with priority + due-date sort, manages notification preferences (digest cadence, Slack, OOO), reads "how auditing works" + counterweight ("what you CANNOT do"). |
| 5 | `05v2-auditor-review.html` | **Mitigates HIGH-risk #4 (evidence-chain).** Auditor submits one of 4 verdicts (PASSED_WITH_EVIDENCE / PASSED_ATTESTATION / REJECTED / NEEDS_CLARIFICATION) with evidence requirements enforced (≥1 file OR ≥200 chars text); attestation-only path requires ≥100-char reason and shows skeptical-UX warning + visually distinct audit-trail tag. Forensic capture: name + timestamp + IP + sha256 hashes + typed signature. |

After Pass 3, **all 4 task types have first-class deliverable surfaces** (DEVELOP from Pass-1-revised, ANALYSIS / PLANNING / DOCUMENTATION new in Pass 3) and **the assign-auditor loop is complete end-to-end** (W-13 → W-27 → W-28 → back to deliverable with verdict).

---

## Pass 1 + Pass 2 + Pass 3 combined coverage (27 of ~52)

| Surface area | Pass 1 | Pass 2 | Pass 3 | Status |
|---|---|---|---|---|
| Answer ambiguity | ✓ | — | — | covered |
| Add AC / scenario | ✓ | — | — | covered |
| New task wizard step 1 | ✓ | — | — | covered (steps 2/3 still TBD) |
| Crafter preview | ✓ | — | — | covered |
| Project config tabs | ✓ | — | — | covered |
| Skill edit + hook add | ✓ | — | — | covered |
| Generic destructive preview modal | ✓ | — | — | covered |
| KB source intake — 4 types | — | ✓ | — | covered |
| Source detail view (read chunks) | — | ✓ | — | covered |
| Objective creation / re-open / edit | — | ✓ | — | covered |
| Per-objective challenger checks | — | ✓ | — | covered |
| Task close with reason + signature | — | ✓ | — | covered |
| Follow-up task creation | — | ✓ | — | covered |
| Live scenario generation | — | ✓ | — | covered |
| Manual auditor assignment (assigner side) | — | ✓ | — | covered |
| **DEVELOP task deliverable** | — | (revised) | — | covered (`05v2-task-deliverable.html`) |
| **ANALYSIS task deliverable** | — | — | ✓ | covered |
| **PLANNING task deliverable** | — | — | ✓ | covered |
| **DOCUMENTATION task deliverable** | — | — | ✓ | covered |
| **Auditor's inbox** | — | — | ✓ | covered |
| **Auditor's review-with-evidence** | — | — | ✓ | covered (HIGH-risk #4 closed) |

---

## HIGH-risk mitigations status

From `PASS_2_RISK_REPORT.md` — 4 HIGH risks identified.

| # | Risk | Mitigation status |
|---|------|-------------------|
| **HIGH #1** | KB folder PII — `02v2-add-source-folder.html` indexes >2000 files w/o file-list review modal | **Pass 3 did NOT fix.** Still needs: required preview modal showing first 20 matched files + post-ingest async PII/SECRET regex scan + monthly digest. |
| **HIGH #2** | Scenario generation no gas gauge — `05v2-scenario-generate.html` phase 3/4 can hang with hidden cost | **Pass 3 did NOT fix.** Still needs: hard timeout per phase (≤5min phase 3, ≤2min phase 4), per-run hard cap ($0.50), surface time overrun immediately. |
| **HIGH #3** | Close-task allows deferring all findings without circuit breaker | **Pass 3 did NOT fix.** Still needs: running tally on close form ("deferring 2; project has 5 open >30d"), auto-spawn-followup-task checkbox, project-level "findings by age × severity" red-bar alert on dashboard. |
| **HIGH #4** | Manual AC stores verdict without evidence — `05v2-assign-auditor.html` | **✓ FIXED in Pass 3** via `05v2-auditor-review.html`. Verdicts split into PASSED_WITH_EVIDENCE (requires ≥1 file OR ≥200 chars text) vs PASSED_ATTESTATION (requires ≥100-char reason + visually distinct in audit trail). Forensic capture (sha256 hashes, IP, timestamp, typed signature) added. New schema fields documented in mockup annotations. |

---

## Pass 4 — what's still missing (target: ~10 mockups)

### Failure / interrupt / degraded-state surfaces (5 mockups)
- `05v2-task-failed.html` — task FAILED state w/ stack trace, retry options, "convert to investigation"
- `05v2-task-replay.html` — historical task replayed against new skill version (side-by-side diff)
- `04-cost-overrun-pause.html` — mid-run cost overrun, pause + forensic
- `04-budget-cap-hit.html` — budget cap hit
- `04-interrupt-mid-crafter.html` — user stops a crafter mid-execution

### Source / KB lifecycle (3 mockups, deferred from Pass 3)
- `02v2-edit-source.html` — re-ingest, update description/focus, archive
- `02v2-source-conflict-resolver.html` — pick SRC-001 vs SRC-002 when overlap-check escalates
- `02v2-archive-source.html` — destructive confirm using `16-preview-apply-modal` shell

### Auth / role surfaces (2 mockups)
- `00-org-team.html` — users + roles (incl. `can_audit`) + project memberships
- `00-login.html` + `00-magic-link.html` — auth landing for external auditors

---

## Pass 5 — admin / cross-project / client-facing (target: ~10 mockups)

These exist outside a single project's bubble. Forge currently has zero coverage.

- `00-org-dashboard.html` — multi-project digest, cost rollup, autonomy-level dashboard
- `00-org-skills-marketplace.html` — org-shared skill library distinct from project-installed
- `00-org-budget.html` — per-project caps, monthly spend, alerts
- `00-audit-log-search.html` — full audit log with filter + drilldown (wired to evidence hashes from W-28)
- `00-incidents.html` — lessons_learned table cross-referenced to projects
- `00-replay-cohort.html` — admin UI to replay a cohort against a new skill version
- `client-share-dashboard.html` — read-only project view shared with client
- `client-share-objective.html` — shareable objective detail (filtered for external eyes)
- `client-share-deliverable.html` — shareable task deliverable
- `12-autonomy-promote.html`, `12-autonomy-watchlist.html`, `12-autonomy-overnight-run.html` — L-promotion ceremonies

---

## Honest gap list — what Pass 3 explicitly did NOT do

1. **Did not address HIGH risks #1, #2, #3.** Only #4 (evidence-chain) was in scope. The other 3 still need Pass 4 work.

2. **No re-render of `05v2-task-deliverable.html`** to show the post-audit state (verdict + evidence link surfaced inline). The auditor's submitted verdict feeds back to the deliverable, but the visual update isn't mocked. Pass 3 inferred this state from data flow, didn't render the variant.

3. **No editor surface for produced artifacts.** `05v2-documentation-deliverable.html` shows preview + offers "Edit" button, but the actual editor (markdown WYSIWYG or code-style) is not built. Real implementation would either hand off to in-IDE or build a web editor.

4. **No diagram rendering for ADR / architecture.md.** DOC deliverable shows text-only preview. Real architecture docs need diagram support (Mermaid / PlantUML / image embed) — out of scope for Pass 3.

5. **DAG SVG in planning deliverable is illustrative only.** Real implementation would need a graph layout library (dagre, d3-graphviz) — the mockup hand-positions 13 nodes.

6. **Auditor review form shows all 4 variants on one page.** Real UI would render only the selected verdict's form. The `<details>` elements expose the alternate variants for design-review purposes.

7. **No mobile / responsive variant.** All 1280px+ desktop. Auditor inbox + review especially likely to be used on tablet by external reviewers — Pass 4 should consider a mobile pass.

8. **No empty / loading / error states for the 5 new mockups.** Every form shown in the "happy filled-in" variant.

9. **No per-artifact freeze workflow shown.** DOC deliverable mentions `artifact.is_frozen` + freeze kinds (adr_accepted, pdf_export, folder_rule), but a "Freeze artifact" modal is not built.

10. **AC coverage matrix in planning deliverable is hard-coded markup.** Real implementation needs a sticky-header + sticky-first-column scrollable table for objectives with >5 AC × >12 tasks.

11. **No visualization of evidence in audit-log search.** Pass 3 captures evidence hashes + URLs, but the cross-project audit-log search surface that uses them is Pass 5.

12. **AI sidebar is one-liner annotations only.** Same gap as Passes 1+2 — the actual sidebar component is referenced but not rendered.

---

## Judgment calls flagged for review (DB / schema impact)

These were implied by Pass 3 mockups but warrant explicit confirmation against the actual schema:

### From task-deliverable variants (W-24, W-25, W-26):
- **`task.source_reads[]` JSONB** — per-source {src_id, chunks_read_ids[], citations_extracted[]}. Without this, "4 of 5 scoped sources" + per-source chunk count cannot be displayed.
- **`task.scenarios_generated[]`** + **`scenario.generated_by_task_id`** — needed for analysis deliverable's scenario panel.
- **`decision.resolution_path`** ENUM (inline_cross_read | user_answer | deferred) — separates the 4 inline-resolved Q's from the 2 escalated.
- **`ac.draft_by_task_id`** — links AC back to the analysis task that proposed it.
- **`source.status='EXCLUDED'`** + **`source.excluded_by_decision_id`** — needed for SRC-005 exclusion display.
- **`task.generated_by_task_id`** — for planning, links each draft develop task to PT-003.
- **`task.covers_ac_ids[]`** — drives the AC coverage matrix.
- **`task.estimated_llm_cost`** — crafter's pre-run estimate, displayed in planning task list.
- **`task.status='DRAFT'`** sub-state — needed before approve-all spawns.
- **`plan.critical_path_task_ids[]`** — derived field for highlighting in DAG.
- **`artifact` table** entirely new — captures DOC outputs with paragraphs[], adr_sections[], unsourced_paras[], diff_patch (for modify-kind), is_frozen + freeze_kind.

### From auditor surfaces (W-27, W-28) — these are Pass 2 schema gaps that Pass 3 surfaces:
- **`manual_verification_task.verdict`** ENUM extended: PASSED_WITH_EVIDENCE, PASSED_ATTESTATION, REJECTED, NEEDS_CLARIFICATION (Pass 2 had a single ambiguous "PASSED").
- **`manual_verification_task.evidence_artifacts[]`** JSONB — {url, sha256, mime, size, uploaded_at}. **This is the HIGH-risk #4 fix.** Without this column, evidence cannot be captured.
- **`manual_verification_task.evidence_text`** + **`evidence_text_hash`** — for pasted text evidence.
- **`manual_verification_task.method`** ENUM, **`executed_at`** timestamp, **`environment`** ENUM (staging | production-mirror | local-dev | production-readonly).
- **`manual_verification_task.signature_text`**, **`signature_ip`**, **`signature_user_agent`**, **`signed_at`** — forensic capture.
- **`manual_verification_task.attestation_reason`** TEXT (≥100 chars, only for PASSED_ATTESTATION).
- **`user.notification_prefs`** JSONB — {digest_cadence, reminders_before_due, slack_dm, reject_reopen_email}.
- **`user.ooo_dates[]`** JSONB.
- **`finding.created_by_auditor_id`** — for findings spawned by REJECTED verdicts.
- **`decision.originating_auditor_id`** + **`decision.kind='clarification'`** — for NEEDS_CLARIFICATION verdicts.

None of these are blockers for the mockups themselves (mockups are static), but each is a flag for backend planning.

---

## Explicit scope limits — what Pass 3 did NOT do

1. **Did NOT update `05v2-task-deliverable.html`** to surface post-audit verdict + evidence inline. The auditor's verdict flows back through `manual_verification_task` → `ac.status` → deliverable, but the visual integration is a Pass 4 polish item.

2. **Did NOT build the editor surfaces** that DOC deliverable's "Edit architecture.md" / "Open in editor" buttons reference. Real implementation likely federates to an in-IDE plugin or web editor — Pass 4 + 5 will decide architecture.

3. **Did NOT mock the share-link generation flow.** DOC deliverable links to `10-post-exec-docs.html` for sharing, which exists from Pass 1 but doesn't model the share-with-evidence-redaction feature.

4. **Did NOT update `09-objective-detail.html`** to add deep-links to the 3 new task-type deliverables. Currently the breadcrumbs assume entry via DAG or task-row click — `09-objective-detail.html` doesn't have explicit "View AT-005 deliverable" affordances on each task row. Pass 4 polish.

5. **Did NOT verify all annotations cite real DB tables.** Annotations reference table/column names following Pass 1+2 patterns. Schema audit recommended before backend work.

6. **Did NOT add new walkthrough scenarios** for analysis / planning / DOC task lifecycles. Existing walkthrough scenarios cover develop-task flow well; non-develop task narratives are still implicit.

7. **Did NOT update `walkthrough.md` or `flow.html`.** Reference docs unchanged.

8. **Did NOT build failed-state variants** — `05v2-task-failed.html` is referenced as Pass 4 work. The 3 new deliverables only show DONE-with-concerns, not FAILED-mid-execution.

9. **Did NOT model multi-auditor scenarios.** AC-6 has one assignee. If two auditors disagree (assigner re-routes mid-cycle), the schema/UI for that is Pass 5 (admin / cross-cutting concerns).

10. **Did NOT integrate evidence into compliance-export.** Auditor-captured evidence (sha256 + signed_at) sits in `manual_verification_task.evidence_*` but no PDF/CSV/SOC2-template export from Forge is built. Audit-log search (Pass 5) is the natural home.

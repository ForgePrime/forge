# Pass 2 deep-risk report

**Date:** 2026-04-19 · **Auditor:** deep-risk (Explore agent)
**Scope:** 13 Pass 2 mockups against Forge skeptical-UX contract

## Summary

- **High risks: 4** (must address before production)
- **Medium risks: 6** (should address in Pass 3)
- **Low risks: 3** (note for future)

**Categorical hotspots:**
1. **State Consistency** — KB sources added immediately appear in scope without confirming parse succeeded; ambiguities auto-surface but no lock prevents simultaneous edits.
2. **Cost / Runaway** — folder source can ingest >2000 files without per-file cost preview; scenario-gen cancellation only at "phase boundaries" (can be 30s gaps); no per-source spend cap.
3. **Skeptical-UX Drift** — close-task frames findings as "deferrable" without surfacing cumulative debt metric.
4. **Hidden State** — manual AC stores auditor "PASSED" without evidence link.
5. **Concurrency** — DAG edit shows no lock indication; cycle detection runs on stale graph.

**Single most dangerous risk + mitigation:**

**Risk:** KB folder source (`02v2-add-source-folder.html`) indexes 2,418 files with a checkbox confirmation but DOES NOT prompt user to review which files matched globs BEFORE embedding. If user misconfigures includes/excludes (forgets `**/.env*`), AWS credentials silently embedded — cannot be unembedded.

**Mitigation:** Required review modal showing first 20 matched files + confirmation checkbox; post-ingest async PII/SECRET regex scan with quarantine action; audit log of all ingests with monthly digest.

---

## High risks (must address)

### 1. KB Source Overlap Detection Not Actionable
**Mockup:** `02v2-add-source-file.html` lines 136-149
**Dimensions:** Confusion, skeptical-UX violation, hidden state

User sees amber "ambiguity will be raised" warning but cannot preview the actual conflict. Link to `09-answer-ambiguity.html` is forward-ref. User commits without seeing what they're committing to.

**Mitigation:** Inline side-by-side of conflicting chunks (200 chars each) before commit. Force explicit "keep both / cancel" choice + log in audit trail.

### 2. Scenario Generation Has No Gas Gauge
**Mockup:** `05v2-scenario-generate.html` lines 190-227
**Dimensions:** Cost runaway, user surprise

Phase 3 (test runner) can hang 5+ min while UI shows "~30s". Cost meter only counts LLM calls; CPU compute is hidden. Phase 4 may spawn unbudgeted LLM calls.

**Mitigation:** Hard timeout per phase (≤5min phase 3, ≤2min phase 4); per-run hard cap ($0.50 max); show "running 7 min (est 2 min)" surface time overrun immediately.

### 3. Close-Task Allows Deferring All Findings Without Circuit Breaker
**Mockups:** `05v2-close-task.html` lines 62-142
**Dimensions:** Skeptical-UX violation, silent debt accumulation

User can defer 2 HIGH + 1 MEDIUM finding per close. No alert when N tasks accumulate K deferred HIGHs. Findings become orphaned (not tied to tasks). Project dashboard doesn't surface "20% of closed tasks deferred HIGH in last sprint."

**Mitigation:** Running tally on close form: "deferring 2; project has 5 open >30d"; auto-spawn-followup-task checkbox; project-level "findings by age × severity" red-bar alert.

### 4. Manual AC Assignment Stores Verdict Without Evidence
**Mockup:** `05v2-assign-auditor.html` lines 138-199
**Dimensions:** Hidden state, evidence loss, audit failure

Auditor can mark PASSED without running the verify script; no `evidence_artifact_url` stored. AC-6 (HIPAA tamper-evidence) recordable as verified without proof. Auditor explicitly noted in scrutiny ("Forge cannot enforce audit quality") but the gap goes uncaptured.

**Mitigation:** Require evidence upload/paste in auditor UI; distinguish `PASSED_WITH_EVIDENCE` vs `PASSED_ATTESTATION`; specify evidence format on assign form (e.g., "paste output of verify-chain.sh"); link evidence on task deliverable.

---

## Medium risks (should address)

### 5. Objective Dependencies — No Concurrent-Edit Lock
**Mockup:** `09-edit-dependencies.html` lines 177-198 — Cycle detection runs on stale graph if two users edit simultaneously. **Fix:** optimistic locking via `depends_on_version` + 409 Conflict on stale write; real-time subscription with reload prompt.

### 6. KB Source "Queue for Analysis Reuse" Best-Effort
**Mockup:** `02v2-add-source-file.html` lines 169-176 — If queued objective gets archived, queue entry orphaned. No spec for "automatically reads it." **Fix:** validate non-archived on queue; persist `source_queue` table with status; surface "queued for X but not yet used."

### 7. Challenger Checks — No Quality Feedback Loop
**Mockup:** `09-edit-challenger-checks.html` lines 237-247 — Cost meter shows token impact but not quality dilution. Adding 5th low-signal check costs +$0.02 + drops catch rate from 50% to 40%. No automated detection. **Fix:** show live quality warning on add ("hit rate <30% will dilute focus"); sort check list by hit-rate; monthly digest "check #3 caught 0 in 8 firings."

### 8. Re-open "History Preservation" Doesn't Verify Artifacts
**Mockup:** `09-reopen-objective.html` lines 80-105 — Status preserved but artifacts (test results, benchmarks, ADRs) might be missing/stale post-restart. New analysis may reference dead files. **Fix:** add `/objective/{id}/verify-artifacts` step; surface missing files as warnings; offer regenerate or mark suspect.

### 9. Scenario Generation Phase Boundaries Race Condition
**Mockup:** `05v2-scenario-generate.html` lines 232-233 — Cancel sent at token 200/500 of phase 1: does it wait or fire? Network hiccup loses "phase 2 complete" event. UI says "still on 2" while server is on 4. User cancels phase 4 thinking it's phase 2. **Fix:** explicit server state pill; atomic `POST /cancel-with-lock` returns current phase; client polls /status until phase completes.

### 10. Concurrency / Multi-User Layer Missing
Several mockups assume single-user. Multi-user concerns: concurrent DAG edits (5), KB ingest tracking (6), auditor lifecycle (no revoke / reassign UI), findings dedup (no similarity merge).

---

## Low risks (note)

### 11. Source Preview Doesn't Show Chunk Boundaries
**Mockup:** `02v2-source-preview.html` lines 114-168 — Chunker may split mid-sentence on PDFs without headings. Retrieval picks wrong section. **Fix:** show chunk boundary markers; allow drag-adjust.

### 12. Add-source Scope Tag Autocomplete Stale
**Mockups:** `02v2-add-source-file.html`, `02v2-add-source-folder.html` — Suggestions from `project.known_scopes[]` without recency cleanup. **Fix:** show "last used 30d ago" on suggestions; warn on stale.

### 13. Close-Task Signature Soft Check Only
**Mockup:** `05v2-close-task.html` lines 154-160 — Disabled-button + name match are client-side. User can dev-tools-bypass. **Fix:** server-side validate `close_signature IS NOT NULL`; reject 400 on missing.

---

## Cross-cutting patterns

### Creation pattern (5 add-source + 1 create-objective)
All show right-panel scrutiny. **Unified fix:** reusable Counterweight template component; standardize checklist (input unverified / assumption made / what-if-wrong); always-visible on desktop, collapsible on mobile.

### Destructive pattern (close-task, reopen-objective, assign-auditor)
All conservatively named, but destructiveness varies (close has irreversible deferral; re-open triggers re-analysis cost; assign creates external dep). **Unified fix:** Destructive-Action Confirmation template — show what changes, what doesn't, require ≥50-char reason, downstream impact, type-entity-ID for HIGH-impact (>3 blocked, >$0.5 cost).

### Source overlap / conflict (add-source-file, add-source-note, source-preview)
Detection is surfaced (amber) but not actionable. **Unified fix:** Conflict Resolution panel showing conflicting passages side-by-side + "keep both / archive old / cancel" choice; on source-preview, mirror "Referenced by" with "Contradicted by" section.

---

## Skeptical-UX contract scoring

Scale 0-3 per: **(a)** counterweight visible · **(b)** primary action conservatively named · **(c)** reversibility/impact previewed.

| Mockup | (a) | (b) | (c) | Total | Status |
|---|---|---|---|---|---|
| 02v2-add-source-file | 3 | 3 | 2 | **8/9** | Pass |
| 02v2-add-source-url | 3 | 2 | 1 | **6/9** | Borderline — no impact preview for crawl cost |
| 02v2-add-source-folder | 3 | 2 | 1 | **6/9** | Borderline — sensitive-file warning lacks impact-if-slipped |
| 02v2-add-source-note | 3 | 3 | 1 | **7/9** | OK — needs impact preview |
| 02v2-source-preview | 3 | 2 | 2 | **7/9** | OK |
| 03v2-create-objective | 3 | 2 | 2 | **7/9** | OK — no conflict-with-other-objectives check |
| **09-reopen-objective** | 3 | 3 | 3 | **9/9** | **Excellent** — gold standard |
| 09-edit-challenger-checks | 3 | 2 | 2 | **7/9** | OK |
| 09-edit-dependencies | 2 | 2 | 3 | **7/9** | OK — semantic cycles missed |
| 05v2-close-task | 3 | 3 | 2 | **8/9** | Good — needs cumulative debt surface |
| 05v2-create-followup-task | 2 | 2 | 2 | **6/9** | Borderline — needs Pitfalls panel |
| **05v2-scenario-generate** | 2 | 2 | 1 | **5/9** | **Weak — redesign** |
| 05v2-assign-auditor | 2 | 2 | 2 | **6/9** | Borderline — needs evidence-chain requirement |

**Mockups <6/9 (require redesign): 1 (scenario-generate)**
**Mockups 6/9 (borderline, fix in Pass 3): 4** (add-source-url, add-source-folder, create-followup-task, assign-auditor)

---

## Concurrency / multi-user note

**Implicit assumptions:** single-user per project; objective DAG edits non-concurrent; KB ingest async-untracked; auditor won't be un-invited mid-task.

**Missing layer:**
- Concurrent edits — later write wins silently. Need optimistic locking + 409 Conflict.
- KB ingest tracking — `source_queue` not persisted; queued-but-archived = orphan.
- Auditor lifecycle — no revoke/reassign; vacation = forever-block.
- Findings dedup — duplicates accepted; no similarity matcher.

**Recommended:** version numbers on mutable entities; `/cancel-with-lock`; audit-assignment 7-day timeout + escalation; findings-similarity matcher (>80% text match → merge prompt).

---

## Recommendations by priority

**Before shipping Pass 2:**
1. Fix scenario-gen cost guardrails (H#2).
2. Fix KB folder PII risk (H#1).
3. Add close-task deferred-findings circuit-breaker (H#3).
4. Add evidence-chain for auditor assignments (H#4).

**In Pass 3:**
1. DAG concurrent-edit locking (M#5).
2. Auditor timeout + escalation (M#8).
3. Refactor all creation flows to shared counterweight template.
4. Refactor destructive actions to shared confirmation template.

**Total assessment:** Pass 2 is **safe to prototype** if 4 HIGH-risk mitigations applied. Contract mostly honored (8/13 mockups score 7+/9). Systematic gaps in cost guardrails, evidence capture, multi-user coordination — will surface during real use.

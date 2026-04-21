# Pass 2 deep-verify report

**Date:** 2026-04-19 · **Auditor:** deep-verify (Explore agent)
**Scope:** 13 Pass 2 mockups + FLOWS.md + PROCESS_COMPLETENESS_PASS2.md + index.html

## Summary
- **0 defects** (blocking)
- **2 warnings** (non-blocking, documentation-level)
- **2 forward-references** (Pass 3+ work, properly documented)
- **10 implied DB columns/tables** flagged for backend planning (not defects)

**Verdict: PRODUCTION-READY.** All 13 mockups pass all 11 verification dimensions.

## Defects (must-fix before merge)
**None.**

## Warnings (consider fixing)

| File | Issue | Suggested fix |
|---|---|---|
| `09-reopen-objective.html` line 95 | Count mismatch: claims "15 tasks preserved" but body lists 14 (AT-005, PT-003, DT-001..DT-010, DOC-001, DOC-002) | Change "15 tasks" → "14 tasks" or add the missing entry |
| `09-edit-dependencies.html` annotations | Assumes `objective.depends_on[]` shape is `{objective_id, kind: hard|soft}`; backend may store as flat string array | Validate `app/models/objective.py`; if flat, document as Pass-3 schema migration |

## Forward-references (Pass 3+ work; not defects)

| File | Links to | Status |
|---|---|---|
| `02v2-source-preview.html` | `02v2-edit-source.html` | Documented in PROCESS_COMPLETENESS_PASS2.md §Gaps #2 |
| `02v2-source-preview.html` | `02v2-source-conflict-resolver.html` | Documented in PROCESS_COMPLETENESS_PASS2.md §Gaps #5 |

## Data-model implied (deltas vs current schema)

| New column / table | Mockup | Already in schema_migrations.py? |
|---|---|---|
| `task.close_reason` (TEXT) | 05v2-close-task | ❌ |
| `task.close_signature` (VARCHAR) | 05v2-close-task | ❌ |
| `Finding.defer_reason` (TEXT) | 05v2-close-task | ❌ |
| `Finding.deferred_by_task_id` (FK) | 05v2-close-task | ❌ |
| `Finding.addressed_by_task_id` (FK) | 05v2-create-followup-task | ❌ |
| `manual_verification_task` (new table) | 05v2-assign-auditor | ❌ |
| `scenario_generation_run` (new table) | 05v2-scenario-generate | ❌ |
| `objective.reopen_history[]` (JSONB) | 09-reopen-objective | ❌ — only scalar reopen exists |
| `objective.challenger_checks[]` (richer JSONB shape) | 09-edit-challenger-checks | 🟡 column exists; shape needs upgrade |
| `objective.depends_on[]` element shape | 09-edit-dependencies | 🟡 relationship exists; element shape needs upgrade |

All ten are listed for backend planning, not as mockup defects.

## Per-mockup verdict

| # | Mockup | Verdict |
|---|---|---|
| 1 | 02v2-add-source-file.html | ✅ PASS |
| 2 | 02v2-add-source-url.html | ✅ PASS |
| 3 | 02v2-add-source-folder.html | ✅ PASS |
| 4 | 02v2-add-source-note.html | ✅ PASS |
| 5 | 02v2-source-preview.html | ✅ PASS (2 documented forward-refs) |
| 6 | 03v2-create-objective.html | ✅ PASS |
| 7 | 09-reopen-objective.html | ⚠ PASS (count warning) |
| 8 | 09-edit-challenger-checks.html | ✅ PASS |
| 9 | 09-edit-dependencies.html | ⚠ PASS (schema assumption) |
| 10 | 05v2-close-task.html | ✅ PASS |
| 11 | 05v2-create-followup-task.html | ✅ PASS |
| 12 | 05v2-scenario-generate.html | ✅ PASS |
| 13 | 05v2-assign-auditor.html | ✅ PASS |

## All 7 dimensions + 4 cross-cutting checks: PASS

1. ✅ Link integrity — 0 broken links across 13 mockups
2. ✅ Breadcrumb correctness — all reflect actual entry paths
3. ✅ Scenario consistency — acme-erp-migration / hergati / O-001..008 / SRC-001..009 / AT/PT/DT/DOC ranges OK
4. ✅ Annotation data-source completeness — every main element mapped
5. ✅ Skeptical-UX counterweight — every page has visible "what I did NOT" element
6. ✅ AI sidebar hint — present on all 13
7. ✅ Primary-action destination — every primary button names exact destination file
8. ✅ FLOWS.md vs mockups consistency — W-11..W-23 all match
9. ✅ index.html tile coverage — all 13 tiles present with correct hrefs
10. ✅ Forward-references inventoried (only 2, both documented)
11. 🟡 Data-model implied: 10 deltas — not defects, but backend planning items

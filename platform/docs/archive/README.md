# Archive — v1 governance documents

> **Status:** SUPERSEDED. These documents are retained for audit / git-archaeology only. Do not use for current decisions.

## What's here

- [`FORMAL_PROPERTIES.md`](FORMAL_PROPERTIES.md) — v1 spec (10 dynamical/structural properties, 3 completeness statements, 2 gate-level). Superseded by [`../FORMAL_PROPERTIES_v2.md`](../FORMAL_PROPERTIES_v2.md) which consolidated 4 sources into 25 atomic properties (v2.1 patch).
- [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) — v1 gap audit 2026-04-22 morning. Contains 3 factual errors documented in v2 §0: hallucinated `Decision.blocked_by_decisions`, hallucinated `Finding.source_execution_id`, undercount "30+" vs actual 75 `.status = "..."` sites. Superseded by [`../GAP_ANALYSIS_v2.md`](../GAP_ANALYSIS_v2.md).
- [`CHANGE_PLAN.md`](CHANGE_PLAN.md) — v1 five-phase plan (A→E). Superseded by [`../CHANGE_PLAN_v2.md`](../CHANGE_PLAN_v2.md) (seven-phase A→G) which added Phase F (decision discipline) and Phase G (CGAID compliance).

## Why retained (not deleted)

1. **Audit trail.** v2 §0 corrections reference specific errors in v1. Deleting v1 would orphan those references.
2. **git-archaeology.** Future readers may need to trace how the spec evolved; deletion breaks `git log --follow`.
3. **Validation of superseding.** If v2 itself gets superseded, v1 remains the anchor for what both "point" attempted.

## Why not binding

- v1 is solo-authored by a single Claude session (2026-04-22 morning) — same R-GOV-01 (composite 19 CRITICAL) violation as v2, unresolved.
- v1 missed five atomic properties that v2 added from theorems already in the workspace at the time (Root Cause Uniqueness, Invariant Preservation, Evidence Source Constraint, Evidence Verifiability, Assumption Elimination).
- v1 had hallucinated references.
- If you find a claim here that contradicts v2 — **trust v2**; flag the contradiction as a Finding for audit.

## When to read

- Auditing how the spec evolved (changelog context).
- Trying to understand what a v2 correction reference means.
- External reviewer comparing v1-vs-v2 for methodological review.

**Never** for implementation guidance. Use [`../ROADMAP.md`](../ROADMAP.md) or [`../FORMAL_PROPERTIES_v2.md`](../FORMAL_PROPERTIES_v2.md) instead.

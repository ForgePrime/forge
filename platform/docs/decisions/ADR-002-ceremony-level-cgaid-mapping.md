# ADR-002 — Map Forge `ceremony_level` to CGAID Adaptive Rigor tiers (1:1)

**Status:** CLOSED · ACCEPTED (with premise correction)
**Date:** 2026-04-22
**Decided by:** user (`hergati@gmail.com`), response "tak" to calibration prompt — **on a corrected premise, see §Premise Correction**
**Related:** [FRAMEWORK_MAPPING.md §9](../FRAMEWORK_MAPPING.md), [CHANGE_PLAN_v2.md §13.3 G7](../CHANGE_PLAN_v2.md), [FORMAL_PROPERTIES_v2.md §11.3](../FORMAL_PROPERTIES_v2.md)

## Premise Correction *(must be read first)*

The calibration prompt user approved stated:

> Forge `ceremony_level ∈ {MINIMAL, LIGHT, STANDARD, FULL}` (4 levels); CGAID has `Fast Track / Standard / Critical` (3 tiers). Proposed: `{MINIMAL+LIGHT → Fast, STANDARD → Standard, FULL → Critical}`.

Deep-verify of `platform/app/api/execute.py:53-60` (`_determine_ceremony`) and `platform/seed/seed_data.py:21,29,57,85` (output_contracts seed) shows:

- `_determine_ceremony()` returns only three values: `"LIGHT"`, `"STANDARD"`, `"FULL"`.
- `output_contracts` seeded rows: `(*, *)`, `(feature, STANDARD)`, `(feature, FULL)`, `(bug, LIGHT)`.
- **No `MINIMAL` anywhere in platform code.** [CONFIRMED via grep `MINIMAL|ceremony_level` across `platform/app/` — zero matches for `MINIMAL` in platform.]

**Root cause of the error in the calibration prompt:** the outer `forge/.claude/CLAUDE.md:86` documents ceremony as `MINIMAL/LIGHT/STANDARD/FULL` — but that outer CLAUDE.md describes the legacy `core/` JSON-based pipeline, not the `platform/` SQLAlchemy pipeline. The author (Claude, in prior turn) mixed sources. This violates P19 Assumption Control in platform's own governance docs — it is itself a Finding.

**Corrected premise:**
- Forge `ceremony_level ∈ {LIGHT, STANDARD, FULL}` (3 values).
- CGAID `{Fast Track, Standard, Critical}` (3 tiers).

Given 3:3, the mapping becomes trivially **1:1**, simpler than the collapsed 4→3 form the user approved. User's intent (align Forge with CGAID Adaptive Rigor) is strictly satisfied.

User signalled acceptance of the corrected decision by not objecting after the premise correction was stated in conversation 2026-04-22 evening.

## Context

### CGAID source (OPERATING_MODEL §7)

- `Fast Track` — minimal overhead for low-risk changes. 4 preconditions (OM §7.2). AC tagging always; PR review always; tests-in-PR.
- `Standard` — full delivery loop. Evidence Pack, Execution Plan, Handoff, ADRs for non-trivial, Edge-Case Test Plan, Business-Level DoD required.
- `Critical` — full traceability and formal validation. Standard + explicit failure-mode enumeration + second reviewer with domain expertise + business-outcome evidence artifact.

### Forge source (CONFIRMED from code)

- `Task.ceremony_level` — column populated by `_determine_ceremony(task_type, ac_count)`:
  - `chore`, `investigation` → `LIGHT`
  - `bug` with `ac_count ≤ 3` → `LIGHT`
  - `feature` with `ac_count ≤ 3` → `STANDARD`
  - all others → `FULL`
- `output_contracts(task_type, ceremony_level, version, active, definition)` seeded with 4 rows. Fallback chain in `execute.py:42`: `(exact, exact)` → `(*, exact)` → `(exact, *)` → `(*, *)`.

## Decision

**Map Forge ceremony_level to CGAID Adaptive Rigor tier 1:1:**

| Forge `ceremony_level` | CGAID tier |
|---|---|
| `LIGHT` | `Fast Track` |
| `STANDARD` | `Standard` |
| `FULL` | `Critical` |

The mapping is encoded in `platform/app/services/adaptive_rigor.py` (new file, Phase G7) as a dict; consumed by metrics (G3), Steward audit report (G5), and CONTRACT.md artifact-requirement validators (G6).

## Rationale

1. **Cardinality matches.** 3 → 3, no collapse needed. Simpler by construction.
2. **Semantic alignment.** `LIGHT` in Forge is produced for chore/investigation/small-bug — exactly the class CGAID defines as Fast Track (low-risk). `STANDARD` in Forge is produced for feature with ≤ 3 AC — aligns with CGAID Standard (full loop, moderate complexity). `FULL` in Forge is produced for large features — aligns with CGAID Critical (full traceability).
3. **Fast Track preconditions (OM §7.2)** map naturally to existing Forge gates: (a) scope size → AC count ≤ 3 + diff size check; (b) no new external integration → `@side_effect` registry check (Phase C); (c) no prod data mutation → `budget_guard.veto_paths`; (d) existing test coverage ≥ 80% → coverage report (Phase D).
4. **Zero schema change.** The mapping is config (a dict), not a database migration. Forge's `ceremony_level` column values remain `LIGHT/STANDARD/FULL`; the CGAID label is added as a derived view.

## Alternatives considered

- **Keep both vocabularies separately.** Rejected: forces every reader of a per-task artifact to know both enumerations. Contradicts MANIFEST Principle 8 (traceable end-to-end).
- **Rename Forge enum values to CGAID tier names.** Rejected: breaks backward compatibility with existing rows; no semantic gain over a mapping view.
- **Add a `MINIMAL` level below LIGHT.** Rejected: no evidence of a category below LIGHT in Forge's current operational experience; introduces ceremony without reducing risk (Operational Rule Anti-bureaucracy).

## Consequences

### Affected code (Phase G7 scope)

- **New** `platform/app/services/adaptive_rigor.py` with:
  ```python
  CEREMONY_TO_CGAID_TIER = {
      "LIGHT": "fast_track",
      "STANDARD": "standard",
      "FULL": "critical",
  }
  ```
- **New** `platform/app/services/adaptive_rigor.py:required_artifacts(tier, task_type)` returning the per-tier artifact set per OM §7.1 table.
- **Extended** `seed_data.py` — output_contracts definitions updated to reflect per-tier artifact requirements (not new rows; updated `definition` JSONB).
- **Extended** `contract_validator` — Fast Track preconditions validator rule (OM §7.2, 4 conditions).
- **Extended** `tier1.py` UI — expose CGAID tier label alongside ceremony_level in task views.

### Data migration

No data migration. `ceremony_level` column values unchanged.

### Downstream

- Phase G3 Metric collection labels everything by CGAID tier as well as ceremony_level.
- Phase G5 Steward sign-off requirement triggers on `ceremony_level == "FULL"` (= CGAID Critical).
- Phase G6 artifact-mapping table uses CGAID tier labels.

### Risks

- **Ceremony inflation** if `_determine_ceremony` heuristic overclassifies. Existing mitigation: `ceremony_level` is determined automatically per task_type + ac_count; no user-facing "pick a tier" decision. If production data shows over-classification, tune `_determine_ceremony` thresholds.
- **Fast Track preconditions strictness.** OM §7.2 requires 4 conditions ALL hold; encoding "test coverage ≥ 80%" as a validator requires coverage infrastructure (Phase D dependency). Until Phase D ships, Fast Track validator runs in log-only mode.

### Reversibility

REVERSIBLE via config change. `CEREMONY_TO_CGAID_TIER` is a dict in Python config file; emptying the dict effectively opt-outs from the mapping. No DB schema change to revert.

## Evidence captured

- **CONFIRMED** `_determine_ceremony` signature and return values from `execute.py:53-60` (read in ADR preparation 2026-04-22).
- **CONFIRMED** seeded `output_contracts` set from `seed_data.py:21,29,57,85`.
- **CONFIRMED** OM §7.1 tier definitions + §7.2 preconditions from `.ai/framework/OPERATING_MODEL.md` first-200-line read 2026-04-22.
- **CONFIRMED** no `MINIMAL` in platform via grep with zero matches.
- **ASSUMED** none. Premise correction eliminated the single assumption that was in the calibration prompt.

## Supersedes

None. Supersedes the incorrect "4 levels, collapse" wording in:
- `FORMAL_PROPERTIES_v2.md §11.3` (first paragraph of §11 Patch mapping)
- `FRAMEWORK_MAPPING.md §9`
- `CHANGE_PLAN_v2.md §13.3 G7` and `§13.6` calibration table.

Those documents must be updated to reflect the 3-level reality + 1:1 mapping. See "Document corrections" below.

## Document corrections required

1. `FORMAL_PROPERTIES_v2.md §11.3` — no direct mention of ceremony levels; no change.
2. `FRAMEWORK_MAPPING.md §9` — update header + mapping table.
3. `CHANGE_PLAN_v2.md §13.3 G7` — update proposed mapping text.
4. `CHANGE_PLAN_v2.md §13.6` — update calibration row from "MINIMAL+LIGHT→Fast..." to "CLOSED: see ADR-002".

(Applied in same ADR-002 PR.)

## Implementation tracking

Part of **CHANGE_PLAN_v2.md §13.3 G7** (Adaptive Rigor alignment). No standalone PR; bundled with Phase G rollout.

## Versioning

- v1 (2026-04-22) — initial acceptance with premise correction. Supersedes nothing.

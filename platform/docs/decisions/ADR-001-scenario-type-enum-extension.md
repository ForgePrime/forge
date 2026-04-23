# ADR-001 — Extend `AcceptanceCriterion.scenario_type` enum to 9 values

**Status:** CLOSED · ACCEPTED
**Date:** 2026-04-22
**Decided by:** user (`hergati@gmail.com`), response "tak" to calibration prompt
**Related:** [FORMAL_PROPERTIES_v2.md §11.1](../FORMAL_PROPERTIES_v2.md), [GAP_ANALYSIS_v2.md §8.1](../GAP_ANALYSIS_v2.md), [CHANGE_PLAN_v2.md §13.6](../CHANGE_PLAN_v2.md)

## Context

### Current state (CONFIRMED from code)

- `platform/app/models/task.py:86-88` — `CheckConstraint("scenario_type IN ('positive', 'negative', 'edge_case', 'regression')")`. **4 values.**
- `platform/app/api/projects.py:24, 130`, `tier1.py:650`, `ui.py:1333, 1360` — Pydantic `pattern="^(positive|negative|edge_case|regression)$"`. Consistent with task.py.
- `platform/app/services/scenario_generator.py:30-35` — `NEGATIVE_EXPECTATIONS` dict keyed on 4 values. Line 33: `"edge_case": "Boundary condition handled correctly without crash"` — conflates `boundary` into `edge_case`.
- `platform/app/services/contract_validator.py:188-194` — FAIL gate: feature/bug tasks must have ≥ 1 AC with `scenario_type in ("negative", "edge_case")` and `verdict == "PASS"`.

### Parallel taxonomy (different entity)

- `platform/app/models/objective.py:39` (comment) — `test_scenarios` JSONB kind: `edge_case | failure_mode | security | regression`.
- `platform/app/api/tier1.py:703` — `kind: str = Field("edge_case", pattern="^(edge_case|failure_mode|security|regression|performance)$")` — **5 values** on Objective scenarios.

Two disjoint vocabularies exist today: AC `scenario_type` (4 values) and Objective `scenarios.kind` (5 values). Shared: `edge_case`, `regression`. AC-only: `positive`, `negative`. Objective-only: `failure_mode`, `security`, `performance`.

### Coverage gaps (from GAP_ANALYSIS_v2.md §8.1 deep-verify)

- **boundary** — conflated with `edge_case`. No gate requiring N-1/N/N+1 triplet enumeration.
- **concurrent** — absent. CONTRACT §B.5 lists "concurrent access" in example only.
- **malformed** — conflated with `negative` (shape errors → 400/409/422 only). No fuzz/injection/binary/null-byte coverage.
- **performance, security** — exist at objective level, not at AC level.

## Decision

**Extend `AcceptanceCriterion.scenario_type` enum to 9 values:**

```
{positive, negative, edge_case, boundary, concurrent, malformed, regression, performance, security}
```

New values: `boundary`, `concurrent`, `malformed`, `performance`, `security`. Existing values unchanged.

## Rationale

1. **Evidence of coverage gap.** `scenario_generator.py:33` literally includes the word "Boundary" inside the edge_case description — proof that boundary is already a mental subcategory, just not a distinct enum value. Same for malformed (conflated with negative).
2. **User's 8-point satisfaction criterion §3** ("every uncertainty blocks execution") requires distinct failure-mode categories; conflation hides uncertainty behind a single tag.
3. **Parity with Objective vocabulary.** `performance` and `security` already exist at objective level; promoting to AC level unifies vocabularies without introducing new concepts.
4. **Binding for P10 risk-weighted coverage** (FORMAL_PROPERTIES_v2.md) requires that each category has a risk weight; categories must be distinct enum values, not overloaded.

## Alternatives considered

- **Keep 4 values, add tags on AC.** Rejected: tags are unstructured; schema enforcement is weaker; risk-weighted coverage cannot compute $\sum w_m \text{Cov}(T,m)$ over untyped tags.
- **Use only Objective.scenarios.kind.** Rejected: AC is the granularity at which the validator gate fires (`contract_validator.py:188`). Objective-level scenarios are too coarse.
- **Separate per-category sub-entities (`BoundaryAC`, `ConcurrentAC`, ...).** Rejected: unnecessary schema complexity; enum value suffices for categorization.

## Consequences

### Affected code (migration scope)

- `platform/app/models/task.py:86-88` — update `CheckConstraint` to 9 values. **Alembic migration required** (destructive — old constraint dropped, new created).
- `platform/app/api/projects.py:24, 130`, `tier1.py:650`, `ui.py:1333, 1360` — update Pydantic `pattern` regex to 9 values.
- `platform/app/services/scenario_generator.py` — extend `NEGATIVE_EXPECTATIONS` dict with 5 new entries; add per-category heuristic (boundary → N-1/N/N+1 triplet; concurrent → interleaving; malformed → fuzz set).
- `platform/app/services/contract_validator.py:188-194` — extend `has_negative_pass` check: new per-capability coverage rule accepting any of `{negative, edge_case, boundary, concurrent, malformed}` for the "failure coverage" criterion.
- `platform/app/services/handoff_exporter.py:180` — extend AC filter.
- `platform/app/templates/objective_detail.html:337, 391, 406` — extend UI select options.

### Data migration

Existing rows have `scenario_type ∈ {positive, negative, edge_case, regression}`. All 4 remain valid. **No row migration needed** — new constraint is a superset.

### Downstream

- Phase D (failure-oriented tests) now has explicit 5 new categories to seed; `build_adversarial_fixtures.py` can use actual enum values.
- Phase G3 Metric 3 (edge-cases-caught-in-planning vs production) becomes more precise because the taxonomy is richer.

### Risks

- **Generator heuristic quality.** `scenario_generator.py` today is regex-over-AC-text; extending to 5 new categories risks false positives in category assignment. Mitigation: initial rollout is conservative (generator emits stub only when keyword strongly matches); manual override always allowed.
- **Validator backward compatibility.** Old AC rows with `scenario_type='negative'` used to cover malformed scenarios implicitly. After extension, the same check still passes (negative + malformed are both in failure-coverage set). No regression.

### Reversibility

REVERSIBLE via alembic down-migration: drop new constraint, restore 4-value constraint. Would require removing any rows with new values (or coercing to nearest legacy value).

## Evidence captured

- `execute.py:131` `candidate.ceremony_level = ceremony` — unrelated to this ADR, but shows same mutation pattern that new values will follow.
- `contract_validator.py:188` — gate expression already uses `in ("negative", "edge_case")` tuple, trivially extensible to the new set.
- Commit history: no prior attempt to extend this enum found via git log (as of 2026-04-22).

## Implementation tracking

Will be implemented as part of **CHANGE_PLAN_v2.md §13.3 Phase F** (strengthening of P10 + P19 validator) + **Phase D** (adversarial fixtures consuming new categories). Not a standalone PR.

## Versioning

- v1 (2026-04-22) — initial acceptance. Supersedes nothing.

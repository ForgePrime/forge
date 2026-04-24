# Architecture Decision Records (ADRs)

> Per [ADR-003](ADR-003-human-reviewer-normative-transition.md), ADR content is DRAFT until peer-reviewed in [`../reviews/`](../reviews/).

## Index

| # | Decision | Status | Date | Decided by |
|---|---|---|---|---|
| [ADR-001](ADR-001-scenario-type-enum-extension.md) | Extend `AcceptanceCriterion.scenario_type` enum from 4 to 9 values: `{positive, negative, edge_case, boundary, concurrent, malformed, regression, performance, security}` | decision CLOSED · content DRAFT | 2026-04-22 | user |
| [ADR-002](ADR-002-ceremony-level-cgaid-mapping.md) | Map Forge `ceremony_level` to CGAID tiers 1:1 — `{LIGHT→Fast Track, STANDARD→Standard, FULL→Critical}`. Premise correction: Forge has 3 levels, not 4 (`MINIMAL` was cross-source hallucination). | decision CLOSED · content DRAFT | 2026-04-22 | user (corrected premise) |
| [ADR-003](ADR-003-human-reviewer-normative-transition.md) | All normative `platform/docs/` require distinct-actor peer review before NORMATIVE status. Phase A blocked until core docs ratified. | **OPEN** (self-referential) | 2026-04-22 | pending user ratification |
| [ADR-004](ADR-004-calibration-constants.md) | Calibration constants (α per capability, τ, W, q_min per autonomy level, w_m risk weights) | **OPEN** (skeleton) | 2026-04-24 | pending domain expert + platform owner |
| [ADR-005](ADR-005-invariant-check-fn-format.md) | Invariant.check_fn format — Python callable / DSL / SQL | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-006](ADR-006-model-version-pinning.md) | LLM model version pinning + canary eval procedure | **OPEN** (skeleton) | 2026-04-24 | pending platform + governance |
| [ADR-007](ADR-007-steward-rotation.md) | Framework Steward role + rotation policy | **OPEN** (skeleton) | 2026-04-24 | pending organizational leadership |
| [ADR-008](ADR-008-retroactive-stage-0-strategy.md) | Retroactive Stage 0 Data Classification + SecurityIncident schema | **OPEN** (skeleton) | 2026-04-24 | pending platform + security + governance |
| [ADR-009](ADR-009-snapshot-validation-5-components.md) | Deterministic Snapshot Validation 5 components | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-010](ADR-010-non-trivial-classifier-threshold.md) | Non-trivial claim classifier threshold + mechanism | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-011](ADR-011-blocked-state-down-migration.md) | BLOCKED state down-migration handling | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-012](ADR-012-distinct-actor-edge-cases.md) | Distinct-actor edge cases for SR-3 autonomous loop | **OPEN** (skeleton) | 2026-04-24 | pending platform + governance |
| [ADR-013](ADR-013-challenger-refuted-handling.md) | Challenger REFUTED verdict handling (re-queue / reject / override) | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-014](ADR-014-c2-sufficiency-gate-placement.md) | C2 sufficiency gate placement: pre-LLM vs post-hoc validator | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-015](ADR-015-requirement-entity.md) | Requirement entity — promote from Finding.type or accept as-is | **OPEN** (skeleton) | 2026-04-24 | pending platform + architecture |
| [ADR-016](ADR-016-test-entity.md) | Test entity — promote AC.scenario_type or accept as-is | **OPEN** (skeleton) | 2026-04-24 | pending platform + architecture |
| [ADR-017](ADR-017-relation-text-to-enum-mapping.md) | Canonical `relation TEXT → relation_semantic ENUM` mapping for B.6 | **OPEN** (skeleton) | 2026-04-24 | pending platform engineering |
| [ADR-018](ADR-018-dlp-mechanism.md) | DLP mechanism for Confidential+ tier (technology vs ACKNOWLEDGED_GAP) | **OPEN** (skeleton) | 2026-04-24 | pending platform + security + governance |
| [ADR-019](ADR-019-candidate-scoring-weights.md) | Candidate Solution scoring weights (14 dimensions) + trivial-change bypass | **OPEN** (skeleton) | 2026-04-24 | pending platform + architecture lead |
| [ADR-020](ADR-020-technical-debt-categories.md) | Technical debt category enum + `accepted_by` role allowlist | **OPEN** (skeleton) | 2026-04-24 | pending platform + governance |
| [ADR-021](ADR-021-expected-diff-schema.md) | ExpectedDiff schema per Change.type + IRREVERSIBLE recovery procedure | **OPEN** (skeleton) | 2026-04-24 | pending platform + governance |

## ADR template

Every new ADR must include:

```markdown
# ADR-NNN — [Decision title]

**Status:** OPEN | PROPOSED | CLOSED | SUPERSEDED
**Date:** YYYY-MM-DD
**Decided by:** [who]
**Related:** [links to FORMAL_PROPERTIES property, phase, risk, prior ADRs]

## Context
[Why this decision is needed — with evidence / file:line / measured data.]

## Decision
[What is decided. One sentence or a small table.]

## Rationale
[1. bullet 2. bullet 3. bullet — each backed by evidence or named tradeoff.]

## Alternatives considered
- **A.** [name] — rejected because [specific reason, not "suboptimal"].
- **B.** [name] — rejected because [specific reason].
- (minimum 2 alternatives with explicit rejection reasoning per Root Cause Uniqueness, FORMAL §P21)

## Consequences
### Immediate
### Downstream
### Risks
### Reversibility
REVERSIBLE | COMPENSATABLE | RECONSTRUCTABLE | IRREVERSIBLE — [explain].

## Evidence captured
- **[CONFIRMED]** [claim] — via [file:line | command output | citation].
- **[ASSUMED]** [claim] — reason [...].
- **[UNKNOWN]** [claim] — pending [...].

## Supersedes
[prior ADR or "none"]

## Versioning
- v1 (YYYY-MM-DD) — [initial].
```

## Rules

1. **One decision per ADR.** Never two. If two coupled, write both ADRs and reference each other.
2. **Immutable once RATIFIED.** Errors produce a new ADR that Supersedes the prior; never edit-in-place.
3. **Evidence-first** per CONTRACT §B.1. `[CONFIRMED]` requires runtime evidence or direct citation; reading code without executing is `[ASSUMED]`.
4. **Non-trivial claims tagged** per CONTRACT §B.2. No untagged assertion about state/contract/cascade/external-system.
5. **Peer review required before RATIFIED** per ADR-003. Self-authored ADRs are DRAFT until distinct-actor review.
6. **Alternatives enumerate ≥ 2** per FORMAL P21 Root Cause Uniqueness.

## How to submit a new ADR

1. Copy template above into `ADR-NNN-[kebab-case-title].md` (increment NNN).
2. Fill every section. Empty sections = skip block with justification.
3. Open PR referencing the phase / property / risk the ADR unblocks.
4. Request review in `../reviews/`. Use [review template](../reviews/_template.md).
5. Update this index's table when the decision reaches CLOSED.

## How to supersede an existing ADR

1. New ADR with `Supersedes: ADR-NNN` field populated.
2. Prior ADR's `Status` updated to `SUPERSEDED by ADR-MMM`.
3. Both ADRs remain in the folder — never delete.

## Numbering

- ADR-001 through ADR-003 reserved (already issued).
- Next available: **ADR-004**.
- Common near-term candidates (per `DEEP_RISK_REGISTER.md` + `FORMAL_PROPERTIES_v2.md §7` calibration):
  - ADR-004: Calibration constants — W, q_min, τ, α, idempotency TTL, etc.
  - ADR-005: `Invariant.check_fn` format (Python callable vs DSL).
  - ADR-006: Model version pinning policy (compass R-SPEC-05).
  - ADR-007: Framework Steward rotation for Forge project (R-OP-02).
  - ADR-008: Retroactive Stage 0 classification strategy (R-IRR-03).

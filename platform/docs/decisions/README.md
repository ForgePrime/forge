# Architecture Decision Records (ADRs)

> Per [ADR-003](ADR-003-human-reviewer-normative-transition.md), ADR content is DRAFT until peer-reviewed in [`../reviews/`](../reviews/).

## Index

| # | Decision | Status | Date | Decided by |
|---|---|---|---|---|
| [ADR-001](ADR-001-scenario-type-enum-extension.md) | Extend `AcceptanceCriterion.scenario_type` enum from 4 to 9 values: `{positive, negative, edge_case, boundary, concurrent, malformed, regression, performance, security}` | decision CLOSED · content DRAFT | 2026-04-22 | user |
| [ADR-002](ADR-002-ceremony-level-cgaid-mapping.md) | Map Forge `ceremony_level` to CGAID tiers 1:1 — `{LIGHT→Fast Track, STANDARD→Standard, FULL→Critical}`. Premise correction: Forge has 3 levels, not 4 (`MINIMAL` was cross-source hallucination). | decision CLOSED · content DRAFT | 2026-04-22 | user (corrected premise) |
| [ADR-003](ADR-003-human-reviewer-normative-transition.md) | All normative `platform/docs/` require distinct-actor peer review before NORMATIVE status. Phase A blocked until core docs ratified. | **RATIFIED** | 2026-04-22 authored / 2026-04-24 ratified | user (hergati@gmail.com) — review: [record](../reviews/review-ADR-003-by-user-2026-04-24.md) |
| [ADR-004](ADR-004-calibration-constants.md) | Calibration constants: engineering defaults (α=0.8 uniform, τ=0.01, W=30d, q_min linear 0.5→0.9 L1-L5, w_m uniform 1/|M|) tagged [ASSUMED: pending-calibration-study]; mandatory supersession after 3 months production | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-005](ADR-005-invariant-check-fn-format.md) | Invariant.check_fn format: Option A (Python callable with import-path storage + ast.parse whitelist + @invariant_check purity decorator + read-only session) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-006](ADR-006-model-version-pinning.md) | Model version pinning: Option B extended (strict model-id:version-tag + 100-execution canary + ≤1% divergence + 7-day Steward SLA + emergency revert) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-007](ADR-007-steward-rotation.md) | Framework Steward: Option B modified (interim solo = project owner + backup ACKNOWLEDGED_GAP; re-evaluate at team ≥3; OOO>14d kill-criteria) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-008](ADR-008-retroactive-stage-0-strategy.md) | Retroactive Stage 0: Option C hybrid (migrate-default Internal + 30d Steward spot-audit + retroactive incident mechanism) + finalized SecurityIncident schema | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-009](ADR-009-snapshot-validation-5-components.md) | Snapshot Validation: Option A (5 components — structural, distribution, invariant, cross-entity, temporal; mutable-catalog exclusions per AD-7) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-010](ADR-010-non-trivial-classifier-threshold.md) | Non-trivial classifier: Option A (regex library per CONTRACT §A.2 triggers + [TRIVIAL: reason] author override + 3-month production calibration) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-011](ADR-011-blocked-state-down-migration.md) | BLOCKED state down-migration: Option C (migration FAIL with diagnostic + operator-tool pre-step; no silent state loss) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-012](ADR-012-distinct-actor-edge-cases.md) | Distinct-actor edge cases: Option D hybrid (distinct iff different trace_id AND (different model_id OR human_in_loop)); partial-blocks on ADR-006 stable model_id | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-013](ADR-013-challenger-refuted-handling.md) | Challenger REFUTED: Option D hybrid (N=3 retry + terminal REJECT + Steward override with signed record + M_challenger_override_rate metric) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-014](ADR-014-c2-sufficiency-gate-placement.md) | C2 sufficiency gate placement: Option C (both pre-LLM AND post-hoc validation per P11 diagonalizability) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-015](ADR-015-requirement-entity.md) | Requirement entity: Option B (Finding-as-Requirement canonical; zero migration; reversible via future supersession if test-per-Req > 1 emerges) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-016](ADR-016-test-entity.md) | Test entity: Option B (AC + scenario_type as test-link; zero migration; supersede if test-per-AC > 1 common) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-017](ADR-017-relation-text-to-enum-mapping.md) | relation TEXT → relation_semantic ENUM mapping: Option A (exhaustive YAML mapping table v1 + Finding on unmappable + relation_semantic_version column) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-018](ADR-018-dlp-mechanism.md) | DLP mechanism: Path B ACKNOWLEDGED_GAP (Forge = dev-artifact orchestration, not primary data ingestion; upstream org DLP assumed; quarterly Steward re-sign + supersession triggers to Path A Presidio) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-019](ADR-019-candidate-scoring-weights.md) | Candidate scoring: Option B prioritization tiers (P0=5×, P1=3×, P2=1×, P3=0.5×); trivial bypass LOC ≤50 AND closure ≤1; tie-breaker by complexity→cost→UUID | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-020](ADR-020-technical-debt-categories.md) | Technical debt: Option A (8-category enum + 3-role allowlist + size-based co-sign LOC>100 OR deferral>4w + Steward-only for known_regression) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-021](ADR-021-expected-diff-schema.md) | ExpectedDiff schema: Option A (per-Change.type Pydantic schemas + range-based row-count + 48h IRREVERSIBLE recovery SLA with 3 approved options + legacy-Changes exemption) | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-022](ADR-022-memory-version-pinning.md) | Memory-version pinning per Execution: capture rule/microskill/guideline/invariant version_ids at pending→IN_PROGRESS transition (B.5 extension); append-only memory tables; bounds Phase 10→1 feedback loop per USAGE_PROCESS §16 method-weakness #3 | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-023](ADR-023-critical-path-enforcement.md) | Critical Path enforcement via standard CPM: Task.duration_estimate_hours + compute_critical_path.py + CriticalPathGate in Execution scheduler chain; G.3 metrics M_critpath_slippage + M_critpath_respect_rate. Closes AIOS A8 + AI-SDLC #10. Stage D.6 in PLAN_QUALITY_ASSURANCE | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-024](ADR-024-error-propagation-mechanism.md) | Error propagation via Finding inheritance (parent_finding_id + propagates_to_task_ids) + Execution invalidation + ErrorPropagationCheck gate; max_depth=5 cascade cap; contest-propagation path. Closes AIOS A18 + AI-SDLC §19+#20 + FC §14 aspect. Stage G.11 in PLAN_GOVERNANCE | decision CLOSED · content DRAFT | 2026-04-24 | user |
| [ADR-025](ADR-025-actor-and-business-process-entities.md) | Actor + BusinessProcess entities with Finding.actor_refs/process_refs JSONB + BusinessAnalysisCompleteness validator; legacy-row exemption; LLM-based extraction with Steward review. Closes FC §9 + AI-SDLC §7 Business Analysis. Stage B.8 in PLAN_MEMORY_CONTEXT | decision CLOSED · content DRAFT | 2026-04-24 | user |

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

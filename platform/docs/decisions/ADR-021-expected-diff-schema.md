# ADR-021 — ExpectedDiff schema per Change.type + IRREVERSIBLE recovery procedure

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** PLAN_GOVERNANCE Stage G.10, Forge Complete theorem §25 + §26, ADR-009 (snapshot_validator consumer), ADR-008 (SecurityIncident schema parallel).

## Context

G.10 requires every state-mutating Change to declare `expected_diff` pre-commit. After apply, observed Diff is compared; Diff ≠ ExpectedDiff → REJECTED + auto-rollback (REVERSIBLE) or CRITICAL Incident (IRREVERSIBLE). Two decision groups:

1. **Schema of `Change.expected_diff` per Change.type** — migration vs code vs config each need different shape.
2. **IRREVERSIBLE recovery procedure** — what happens when irreversible Change produces unexpected Diff (auto-rollback impossible)?

## Decision

**Option A — Per-Change.type typed JSONB schemas + 48h IRREVERSIBLE recovery SLA.**

### Part 1: ExpectedDiff schema per Change.type

Schema per Change.type (validated at insert via Pydantic + DB CHECK constraint):

```python
# app/validation/expected_diff_schema.py
class MigrationExpectedDiff(BaseModel):
    tables_created: list[str] = []
    tables_dropped: list[str] = []
    columns_added: list[dict]  # [{"table": str, "column": str, "type": str}]
    columns_dropped: list[dict]
    indexes_added: list[str] = []
    indexes_dropped: list[str] = []
    rows_affected_estimate_min: int = 0
    rows_affected_estimate_max: int  # inclusive upper bound

class CodeExpectedDiff(BaseModel):
    files_added: list[str] = []
    files_modified: list[str] = []
    files_removed: list[str] = []
    public_api_added: list[str] = []
    public_api_removed: list[str] = []

class ConfigExpectedDiff(BaseModel):
    env_vars_added: list[str] = []
    env_vars_modified: list[str] = []
    feature_flags_changed: list[dict]  # [{"flag": str, "from": str, "to": str}]

class DataExpectedDiff(BaseModel):
    tables_touched: list[str]
    rows_inserted_estimate_min: int = 0
    rows_inserted_estimate_max: int
    rows_updated_estimate_min: int = 0
    rows_updated_estimate_max: int
    rows_deleted_estimate_min: int = 0
    rows_deleted_estimate_max: int
```

Row-count validation:
- **Range-based, not exact**: actual rows_affected must be in `[min, max]` inclusive. Outside range → DIFF_MISMATCH per G.10.
- Rationale: exact counts fragile (concurrent inserts, retry loops); range captures author intent while allowing realistic variation.

### Part 2: IRREVERSIBLE recovery procedure

When Change.reversibility_class=IRREVERSIBLE AND Diff ≠ ExpectedDiff:

1. **Immediate**: `Change.status=DIFF_MISMATCH_IRREVERSIBLE`; system-wide BLOCKED flag raised (new Executions cannot commit Changes until recovery complete).
2. **Incident record**: `SecurityIncident`-like table `change_incidents(id, change_id, detected_at, severity='CRITICAL', investigator_assigned_to NULL, recovery_option_chosen NULL, resolved_at NULL)`.
3. **Investigation window**: 48h SLA for Steward to:
   - Review ExpectedDiff vs actual Diff (diagnostic query available via `GET /incidents/{id}/diff-report`).
   - Choose recovery option.
4. **Approved recovery options** (exactly one chosen per incident):
   - **(a) Compensating Change**: author a new Change that returns state to Baseline-equivalent. Requires its own ExpectedDiff + Baseline/Post cycle. Original Change remains DIFF_MISMATCH_IRREVERSIBLE in audit.
   - **(b) Accept deviation**: Steward signs off with new Decision(type='deviation_acceptance', evidence_ref=deviation_analysis); Change.status → APPLIED_WITH_DEVIATION; AuditLog mandatory.
   - **(c) Extended BLOCKED**: if neither (a) nor (b) chosen within 48h SLA → system-wide BLOCKED persists; escalation to higher authority (per org); Steward must provide explanation of delay.
5. **SLA breach**: 48h elapsed without recovery option chosen → Finding(kind='IRREVERSIBLE_recovery_sla_breach', severity=CRITICAL) auto-emitted; G.3 metrics tracked.

Implementation:
- Schema: `Change.expected_diff JSONB NOT NULL` + CHECK constraint per Change.type; `Change.expected_diff_schema_version INT DEFAULT 1` for evolution.
- Legacy Changes (pre-G.10): migration adds column NULL; query `UPDATE changes SET expected_diff = '{}'::jsonb WHERE expected_diff IS NULL AND created_at < <G.10 deployment date>` flags legacy as "exempted" via new `expected_diff_exempted_legacy BOOL DEFAULT false` + Finding explaining exemption. Post-G.10 Changes CANNOT use exemption path.
- G.10 T10 test: synthetic IRREVERSIBLE mismatch → system-wide BLOCKED within 1 second; SLA timer starts; at 48h without resolution → Finding emitted.

Rejected alternatives:
- **B (generic schema)**: loses Change.type-specific validation; weak.
- **C (free-form JSONB)**: violates FC §27 determinism; unvalidatable.
- **D (ExpectedDiff optional for non-migration)**: violates §26 per-element runtime verification for all Impact elements.

## Alternatives considered

- **A. Per-Change.type typed schemas (above) + detailed recovery runbook** — candidate: thorough but needs maintenance.
- **B. Single generic `{added: [...], modified: [...], removed: [...]}` schema for all Change types** — rejected: loses type-specific validation semantics.
- **C. Free-form JSONB ExpectedDiff** — rejected: not validatable; violates FC §27 determinism.
- **D. ExpectedDiff mandatory only for migrations; other types optional** — rejected: §26 requires per-element check for all Impacts.

## Consequences

### Immediate
- G.10 migration adds `Change.expected_diff JSONB NOT NULL` with CHECK constraint per schema (A).
- `baseline_post_verifier.py` has per-type validation.

### Downstream
- Changes without ExpectedDiff are impossible (insert rejected) — pre-existing Changes (legacy) need backfill decision.
- IRREVERSIBLE runbook becomes operational dependency.

### Risks
- Schema mismatch with actual Change shape → valid Changes rejected at insert (friction).
- Runbook untested → real incident exposes gaps.

### Reversibility
- Schema: COMPENSATABLE via superseding ADR.
- Recovery procedure: tested via tabletop exercises post-G.10.

## Evidence captured

- **[CONFIRMED: PLAN_GOVERNANCE Stage G.10]** ADR-021 blocks G.10 start.
- **[UNKNOWN]** historical Change.diff distribution — which Change.type dominates?
- **[UNKNOWN]** existing incident-response infrastructure (integration point for IRREVERSIBLE recovery).

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option A (per-Change.type Pydantic schemas + range-based row-count validation + 48h IRREVERSIBLE recovery SLA with 3 approved options + legacy-Changes exemption path); content DRAFT.

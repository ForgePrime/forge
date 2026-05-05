# ADR-006 — LLM model version pinning + canary eval procedure

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** R-SPEC-05, PRACTICE_SURVEY model-drift incidents, FORMAL P6, CCEGAP C9, ADR-012 (distinct-actor requires stable model_id).

## Context

Forge executions invoke LLMs. Without version pinning + canary evaluation, a provider-side model update can silently change platform behavior — violates CCEGAP C9 deterministic gate (same inputs → same result) and ECITP §2.8 prior substitution (different model ≠ same priors).

## Decision

**Option B (extended) — strict model-id + version-tag pinning + 100-execution canary + divergence threshold ≤ 1% + Steward sign-off within 7-day SLA.**

### Pinning granularity
- **Strict** `model-id:version-tag` format (e.g., `claude-opus-4-7:2026-04-15`) stored in `app/config.py` + env var `FORGE_MODEL_PIN`.
- `ai_interaction` table + `llm_calls` row captures `model_pin_used` immutable per call (audit trail).
- Current pins (as of 2026-04-24):
  - `claude_model: claude-opus-4-7:2026-04-15` (primary)
  - `claude_model_challenger: claude-sonnet-4-6:2026-04-15` (challenger per F.6)
- Version tag = release-date marker; format enforced via regex at config-load.

### Canary procedure for version bumps
- **Dataset**: fixed 100 historical Executions pinned at baseline state (stored in `canary_fixtures/` directory; deterministic replay).
- **Replay**: `scripts/canary_replay.py --new-version=X` runs all 100 against new model version; produces divergence report per Execution.
- **Divergence metric**: output-shape equality (ContractSchema validator pass/fail agreement) + assumption-tag agreement (CONFIRMED/ASSUMED/UNKNOWN match). Numeric threshold: **divergence rate ≤ 1% of 100 = ≤1 Execution can disagree**.
- **Bump criteria**:
  - Canary divergence ≤ 1% → proposal advances.
  - Divergence > 1% → bump REJECTED; stays on pinned baseline; Finding filed.

### Approval flow
- **Proposed bump** creates `model_version_proposal` row (new table): `{proposed_pin, canary_result, diverged_executions, proposer_user_id, proposed_at, steward_sign_off_by NULL, steward_sign_off_at NULL}`.
- **Steward SLA**: 7 calendar days from canary PASS to sign-off.
- **If signed within SLA**: pin updated; old pin archived; AuditLog row.
- **If NOT signed within 7 days**: auto-revert proposal (fallback to baseline); Finding emitted `model_version_bump_sla_breached`.

### Emergency revert
Any Steward may issue immediate revert via `POST /config/model-pin/revert` citing incident_id; bypasses canary for revert-only (cannot bump via revert path).

Rejected alternatives:
- **A (no pinning)**: explicit R-SPEC-05 violation; blocked.
- **C (MANDATORY sign-off every bump regardless of divergence)**: adds governance load for zero-divergence bumps; excessive.

Schema:
```sql
CREATE TABLE model_version_proposal (
  id SERIAL PRIMARY KEY,
  proposed_pin TEXT NOT NULL,
  canary_divergence_count INT NOT NULL,
  canary_total INT NOT NULL DEFAULT 100,
  proposer_user_id INT FK,
  proposed_at TIMESTAMP NOT NULL,
  steward_sign_off_by INT FK NULL,
  steward_sign_off_at TIMESTAMP NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'sla_reverted'))
);
```

## Alternatives considered

- **A. No pinning, use provider-latest** — rejected: R-SPEC-05 explicit risk; violates P6 determinism.
- **B. Strict pinning to specific model-id + date tag; canary on fixed 100-execution replay; automatic bump if divergence ≤ 1%** — minimum viable.
- **C. Strict pinning + canary + MANDATORY Steward sign-off on every bump regardless of divergence** — safest but adds governance load.

## Consequences

### Immediate
- Pinning string added to `app/config.py` or env var; canary replay script needed.

### Downstream
- Provider deprecates pinned version → forced bump → canary + sign-off ceremony.

### Risks
- Canary dataset stale → false-positive "no divergence" on workloads not in canary.
- Canary dataset contains PII → leak risk.

### Reversibility
REVERSIBLE — pin string change + redeploy.

## Evidence captured

- **[CONFIRMED: ROADMAP.md §12]** ADR-006 Model version pinning listed as pending.
- **[UNKNOWN]** current model pinning state — grep `app/` for model-id strings.
- **[UNKNOWN]** canary dataset availability.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — skeleton OPEN.
- v2 (2026-04-24) — CLOSED on Option B extended (strict model-id:version-tag pin, 100-execution canary dataset, ≤1% divergence threshold, 7-day Steward SLA, emergency revert path, model_version_proposal schema); content DRAFT.

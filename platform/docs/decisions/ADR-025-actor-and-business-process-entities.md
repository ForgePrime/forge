# ADR-025 — Actor + BusinessProcess entities for business-analysis completeness

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** user (Tier 1 closure mass-accept) + AI agent (draft)
**Related:** Forge Complete §9 (Business Problem Decomposition partial), AI-SDLC §7 + #7 (Business Analysis complete partial), PLAN_MEMORY_CONTEXT new Stage B.8, THEOREM_VERIFICATION_AIOS_AISDLC.md §5.1 G-SHARED-3.

## Context

Two theorems require business-analysis stage to decompose business input into specific entities:

- **Forge Complete §9**: decomposition must include actors, processes, decisions, data entities, business rules, exceptions, success metrics, risks, constraints.
- **AI-SDLC §7 + Condition #7**: Business Analysis valid iff `BusinessProblemDefined ∧ ObjectiveDefined ∧ ActorsDefined ∧ ProcessContextDefined ∧ BusinessRulesDefined ∧ ConstraintsDefined ∧ RisksDefined ∧ SuccessMeasuresDefined`.

Current Forge state:
- `Objective` + `KeyResult` cover business goals + success measures ✅
- `Guideline` + `Invariant` cover business rules + constraints ✅
- `Finding(type='risk')` covers risks ✅
- `Knowledge` covers data entities ✅
- `Decision` covers decisions ✅
- **Actor entity MISSING** — no explicit concept of "who performs / triggers / owns this process"
- **BusinessProcess entity MISSING** — no explicit concept of "what business process this Objective serves"

Without these, Business Analysis stage cannot satisfy theorem condition structurally. Requirements authored without linkage to Actor + Process become floating requirements (common anti-pattern).

## Decision

**Two new entities** + validator linking `Finding(type='requirement')` to both.

### Schema — Actor

```sql
CREATE TABLE actors (
  id SERIAL PRIMARY KEY,
  project_id INT FK REFERENCES projects(id) NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL,  -- free-form role description
  authority_level ENUM('observer', 'participant', 'decision_maker', 'approver', 'system_automation') NOT NULL,
  description TEXT,
  external_identifier TEXT,  -- links to external identity systems (e.g. LDAP DN, email)
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  archived_at TIMESTAMP NULL,  -- soft-delete for historical actors
  UNIQUE(project_id, name)
);

CREATE INDEX ix_actors_project ON actors(project_id) WHERE archived_at IS NULL;
```

Authority levels:
- `observer` — sees outcomes, no action authority (e.g. stakeholder)
- `participant` — performs process steps (e.g. end-user)
- `decision_maker` — authors Decisions within process (e.g. product owner)
- `approver` — signs off on outcomes (e.g. Steward, legal)
- `system_automation` — non-human automated actor (e.g. cron job, webhook)

### Schema — BusinessProcess

```sql
CREATE TABLE business_processes (
  id SERIAL PRIMARY KEY,
  project_id INT FK REFERENCES projects(id) NOT NULL,
  name TEXT NOT NULL,
  input_trigger TEXT NOT NULL,  -- what starts this process
  output_outcome TEXT NOT NULL,  -- what it produces
  expected_duration_hours NUMERIC(10, 2),  -- SLA ref
  frequency_per_day NUMERIC(10, 4),  -- usage volume estimate
  description TEXT,
  parent_process_id INT FK REFERENCES business_processes(id) NULL,  -- nested processes
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  archived_at TIMESTAMP NULL,
  UNIQUE(project_id, name)
);

-- Many-to-many: process ↔ actor
CREATE TABLE business_process_actors (
  process_id INT FK REFERENCES business_processes(id) NOT NULL,
  actor_id INT FK REFERENCES actors(id) NOT NULL,
  role_in_process TEXT NOT NULL,  -- e.g. "initiates", "approves", "receives_outcome"
  PRIMARY KEY (process_id, actor_id, role_in_process)
);
```

### Schema — Finding linkage (for type='requirement')

```sql
ALTER TABLE findings ADD COLUMN actor_refs JSONB NOT NULL DEFAULT '[]'::jsonb;
  -- list of actor_ids this Finding pertains to
ALTER TABLE findings ADD COLUMN process_refs JSONB NOT NULL DEFAULT '[]'::jsonb;
  -- list of business_process_ids this Finding pertains to
```

### Validator — `BusinessAnalysisCompleteness`

Added to GateRegistry for `(Finding, *, OPEN)` insert chain (Finding insert-validation):

```python
def business_analysis_completeness_check(finding):
    if finding.type != 'requirement':
        return Verdict.PASS  # only requirements require actor+process linkage

    actor_count = len(finding.actor_refs or [])
    process_count = len(finding.process_refs or [])

    # Exception: requirements scoped entirely to system_automation actors
    # (e.g. "system must log all errors") may skip process link if all actors
    # are authority_level='system_automation'
    all_system = False
    if actor_count > 0:
        actors = db.query(Actor).filter(Actor.id.in_(finding.actor_refs)).all()
        all_system = all(a.authority_level == 'system_automation' for a in actors)

    if actor_count == 0:
        return Verdict(
            passed=False,
            rule_code='requirement_missing_actor',
            reason='Finding(type=requirement) must reference >=1 actor_id; '
                   'if applicable only to system automation, specify with '
                   'authority_level=system_automation actor'
        )

    if process_count == 0 and not all_system:
        return Verdict(
            passed=False,
            rule_code='requirement_missing_process',
            reason='Finding(type=requirement) must reference >=1 business_process_id '
                   '(exception: all actors are system_automation)'
        )

    return Verdict.PASS
```

### Business-analysis extraction flow (Phase 1 + 2 of USAGE_PROCESS)

When Agent/User is performing Phase 1 INTAKE or Phase 2 UNDERSTANDING:

1. Extract **Actor candidates** from Knowledge content — LLM prompt: "Identify all actors: humans, roles, organizational units, system automations mentioned in this document. Output structured list."
2. Extract **Process candidates** — LLM prompt: "Identify all business processes this system supports: name, trigger, outcome, actors involved."
3. User/Steward reviews extracted candidates in dashboard (`GET /projects/{slug}/business-analysis/candidates`).
4. Approve → inserts `actors` + `business_processes` rows.
5. Requirement Findings created in Phase 2-4 must reference these (enforced by validator).

### Actor/Process evidence per Finding

Each actor_refs + process_refs entry in Finding carries a citation:
```json
{
  "actor_refs": [
    {"actor_id": 42, "evidence_ref": "Knowledge#123:para-4", "quote": "the operations manager reviews weekly..."},
    {"actor_id": 45, "evidence_ref": "Knowledge#128:para-1"}
  ],
  "process_refs": [
    {"process_id": 7, "evidence_ref": "Knowledge#123:para-7"}
  ]
}
```

Enforces that actor/process links are not speculative — every link traces to source material.

## Rationale

1. **Forge Complete §9 + AI-SDLC §7 explicit requirements** — business analysis is structurally incomplete without actors + processes.
2. **Anti-pattern prevention** — "floating requirements" (requirements without clear owner/context) are a known SDLC failure mode; Actor+Process links make owner + context mandatory.
3. **Aligns with G.5 Steward accountability** — Steward authority defined in ADR-007 maps naturally to `authority_level='approver'` role.
4. **LLM-extractable** — Actor + Process extraction from prose is a well-understood NLP task; can be auto-proposed with Steward review.
5. **Optional for system-only requirements** — pragmatic exception for internal requirements that have no human stakeholder (e.g. "system must be idempotent per P6").

## Alternatives considered

- **A. No new entities — use Finding.tags** — rejected: tags are unstructured; no schema for authority level, trigger, outcome; impossible to query "what processes does this project support."
- **B. Single `StakeholderMap` entity combining both** — rejected: conflates orthogonal concepts (who vs what); violates P11 diagonalizability.
- **C. Actor only, no Process** — rejected: AI-SDLC §7 explicitly requires both `ActorsDefined AND ProcessContextDefined`.
- **D. Extract per-Finding from prose at query time (no persistent entities)** — rejected: query-time extraction is non-deterministic (same prose → different extraction by LLM); violates CCEGAP C9 deterministic gate.

## Consequences

### Immediate

1. Two new tables (`actors`, `business_processes`, `business_process_actors`).
2. `Finding` schema extension: `actor_refs JSONB`, `process_refs JSONB`.
3. `BusinessAnalysisCompleteness` gate added to `(Finding, *, OPEN)` insert chain.
4. Dashboard endpoint `GET /projects/{slug}/business-analysis/candidates`.
5. Stage B.8 ActorAndProcessEntities added to PLAN_MEMORY_CONTEXT.

### Downstream

- Every `Finding(type='requirement')` traceable to actor(s) + process(es) — closes FC §10 BR↔TR traceability gap partially.
- G.9 proof-trail audit chain extended: `Change → Execution → AC → Task → Objective → Finding(type=requirement) → {Actor, BusinessProcess}` — 12-link chain (from 10 pre-ADR-025).
- F.11 candidate-evaluation's `Necessary(c)` evidence_ref can cite Actor/Process justification — closes F.11 "requirement" citation gap.
- Forge's business-analysis vocabulary now structurally complete per AI-SDLC §7.

### Risks

1. **Actor inflation** — every minor stakeholder added as Actor → dashboard noise; mitigation: Steward quarterly audit prunes archived actors; `archived_at` soft-delete preserves history.
2. **Process granularity unclear** — where does "checkout flow" end and "payment processing" begin? Mitigation: `parent_process_id` allows hierarchical nesting; `frequency_per_day` differentiates high-level vs detail processes.
3. **Retroactive gap** — existing Findings (pre-ADR-025) have empty actor_refs/process_refs; mitigation: migration flags as `legacy_exempted_business_analysis=true`; validator skips legacy rows; Steward quarterly review to backfill.

### Reversibility

REVERSIBLE — gate disabled via feature flag `BUSINESS_ANALYSIS_ENFORCEMENT=off`; tables stay without enforcement; Finding.actor_refs/process_refs columns retained for audit.

## Evidence captured

- **[CONFIRMED: Forge Complete §9 text]** decomposition requires "actors, processes, decisions, data entities..."
- **[CONFIRMED: AI-SDLC §7 text]** Valid(S1) iff "... ActorsDefined and ProcessContextDefined..."
- **[CONFIRMED: AI-SDLC Condition #7 text]** "Business analysis is complete" requires ≥8 fields enumerated.
- **[CONFIRMED: THEOREM_VERIFICATION_AIOS_AISDLC.md §5.1 G-SHARED-3]** gap explicitly identified.
- **[ASSUMED]** LLM-based Actor/Process extraction quality sufficient for Steward-reviewed auto-proposals; requires calibration on first 20 documents.
- **[UNKNOWN]** performance impact of per-Finding JSONB actor_refs/process_refs on high-volume Projects; benchmark required.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — initial DRAFT + CLOSED via Tier 1 mass-accept; content DRAFT pending distinct-actor review.

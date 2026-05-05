# ADR-026 — Architecture components unified view

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** user (Tier 2 closure mass-accept) + AI agent (draft)
**Related:** AI-SDLC §9 + #9 (Architecture explicit components), PLAN_CONTRACT_DISCIPLINE new Stage E.9, THEOREM_VERIFICATION_AIOS_AISDLC.md §5.3 G-AISDLC-9.

## Context

AI-SDLC §9 Architecture stage is valid only if it explicitly defines:
- components
- data model
- interfaces
- dependencies
- state transitions
- invariants
- single source of truth (SSoT)
- failure handling
- scalability / resilience / security constraints
- rollback / compensation path

Current Forge state (scattered coverage):
- Invariants (E.2) ✅
- task_dependencies + causal_edges ✅ (deps)
- GateRegistry state transitions ✅
- ContractSchema (E.1) = SSoT per Task ✅
- C.4 rollback + C.4 Reversibility ✅
- F.4 BLOCKED + F.6 challenger = failure handling ✅
- **NO unified `architecture_components` entity** — components/modules/services exist implicitly via files/folders; data models via SQLAlchemy schema; interfaces via FastAPI endpoints; scalability/resilience/security constraints scattered across Guidelines
- **No queryable architecture inventory** — "what services does this project have?" answered by grep, not by query

Without this, the architecture is not a first-class artifact. Changes to architecture happen via code changes without explicit Architecture authorship + approval trace. AI-SDLC §9 `ValidArchitecture` clause cannot be satisfied mechanically.

## Decision

**Unified `architecture_components` entity + relationship table + G.9 proof-trail extension.**

### Schema

```sql
CREATE TABLE architecture_components (
  id SERIAL PRIMARY KEY,
  project_id INT FK REFERENCES projects(id) NOT NULL,
  name TEXT NOT NULL,
  kind ENUM(
    'service',      -- HTTP/gRPC service
    'module',       -- Python package or significant file group
    'data_store',   -- table / index / cache / blob storage
    'interface',    -- FastAPI endpoint / gRPC method / event topic
    'external',     -- 3rd-party system (LLM provider, DB, payment processor)
    'job',          -- scheduled / cron / worker
    'config'        -- feature flag / env var set
  ) NOT NULL,
  parent_component_id INT FK REFERENCES architecture_components(id) NULL,
  description TEXT NOT NULL,
  source_ref TEXT NOT NULL,
    -- file path / module path / external identifier; evidence of component existence
  ssot_ref TEXT,
    -- for 'data_store' kind: which component owns this data (SSoT per AI-SDLC §9)
  scalability_constraint TEXT,
    -- e.g. "read QPS < 10k/s before cache layer needed"
  resilience_constraint TEXT,
    -- e.g. "SLO 99.5% availability; failover via replica X"
  security_constraint TEXT,
    -- e.g. "requires MFA; data tier=Confidential"
  rollback_reference_id INT FK REFERENCES changes(id) NULL,
    -- links to rollback path if component was added via a Change
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  archived_at TIMESTAMP NULL,
  UNIQUE(project_id, name)
);

CREATE INDEX ix_arch_components_project ON architecture_components(project_id) WHERE archived_at IS NULL;
CREATE INDEX ix_arch_components_kind ON architecture_components(kind);

CREATE TABLE architecture_component_relationships (
  source_id INT FK REFERENCES architecture_components(id) NOT NULL,
  target_id INT FK REFERENCES architecture_components(id) NOT NULL,
  relation ENUM(
    'depends_on',     -- source requires target to function
    'implements',     -- source fulfills interface defined by target
    'exposes',        -- source publishes/provides target (e.g. service exposes endpoint)
    'consumes',       -- source uses target's output (e.g. service consumes event topic)
    'owns',           -- source is SSoT for target data_store
    'routes_to',      -- source forwards to target (load balancer, proxy pattern)
    'deprecates'      -- source supersedes target (deprecation chain)
  ) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  archived_at TIMESTAMP NULL,
  PRIMARY KEY (source_id, target_id, relation)
);

CREATE INDEX ix_arch_rel_source ON architecture_component_relationships(source_id);
CREATE INDEX ix_arch_rel_target ON architecture_component_relationships(target_id);
```

### Change linkage

```sql
ALTER TABLE changes ADD COLUMN architecture_components_affected JSONB NOT NULL DEFAULT '[]'::jsonb;
  -- list of architecture_component_ids this Change touches
```

### Validators (added to GateRegistry)

**ArchitectureChangeValidator** — at `Change insert` with architectural=true flag:
- Require `architecture_components_affected` non-empty.
- Every entry must reference existing `architecture_components.id` (FK constraint check).
- If Change creates new component → Decision(type='architectural', component_created_id=X) required.

**SSoTUniquenessValidator** — at `architecture_components` insert where `kind='data_store'`:
- Check no other active component already owns this SSoT (unique ownership per data_store).

**RollbackReferenceValidator** — at `architecture_components` insert where `rollback_reference_id IS NULL`:
- Allowed only if kind ∈ {'external', 'config'} (non-code components may not have rollback Change linkage).
- For kind ∈ {'service', 'module', 'data_store', 'interface', 'job'}: require rollback_reference_id.

### G.9 proof-trail extension

G.9 ProofTrailCompleteness audit extended: for each Change with `Change.type='architectural'` OR `architecture_components_affected ≠ []`:
- Verify Change has a Decision(type='architectural') ancestor with F.11 CandidateSolutionEvaluation-compliant structure.
- Verify each affected component exists + has all required fields (description, source_ref, and appropriate constraint fields per kind).

### Query materialization

Endpoint: `GET /projects/{slug}/architecture` returns:
- Hierarchical JSON: components tree by parent_component_id
- Relationship edges with kinds
- SVG Mermaid diagram rendered from components + relationships
- Summary stats: count per kind, constraint coverage

Steward quarterly review consumes this endpoint.

## Rationale

1. **AI-SDLC §9 explicit requirement** — ValidArchitecture iff all 10 enumerated concerns defined mechanically. Current scattered state does not satisfy.
2. **Makes architecture a first-class artifact** — change to architecture requires architectural Decision + F.11 evaluation + component linkage. Prevents architecture drift.
3. **Integrates with existing F.11** — F.11 CandidateSolutionEvaluation operates on Decision.type='architectural'; architectural Changes link to components, making F.11 scope queryable.
4. **G.9 extension is natural** — proof trail already traverses Changes; extending to architectural components adds one link type.
5. **Non-invasive** — existing Changes (non-architectural) unaffected; `architecture_components_affected` defaults to empty for non-architectural Changes.

## Alternatives considered

- **A. No unified view — rely on file-system + SQL schema** — rejected: violates AI-SDLC §9 explicit requirement; not queryable; scalability/resilience/security constraints invisible.
- **B. Separate tables per component kind** — rejected: forces schema rigidity; cross-kind relationships complex; ENUM kind is simpler.
- **C. Auto-extract from code via AST** — rejected: violates ESC-1 determinism (AST parser differs across tools); doesn't capture intent (scalability constraints not in code); keeps architecture implicit.
- **D. External architecture tool integration (e.g. C4 model, ArchiMate)** — rejected at current scope: couples Forge to external tool; our component kinds (service/module/data_store/interface/external/job/config) sufficient. If future architecture complexity justifies → supersede with Option D.

## Consequences

### Immediate

1. 2 new tables (`architecture_components`, `architecture_component_relationships`).
2. `changes.architecture_components_affected JSONB` schema extension.
3. Three new validators in GateRegistry.
4. Dashboard endpoint `GET /projects/{slug}/architecture`.
5. G.9 proof-trail audit extension for architectural Changes.
6. Stage E.9 ArchitectureComponents added to PLAN_CONTRACT_DISCIPLINE.

### Downstream

- Every architectural Change traceable to affected components.
- Steward quarterly review includes architecture-evolution summary.
- F.11 CandidateSolutionEvaluation's `necessary_components_list` can reference `architecture_components.id` directly (typed FK instead of free-form text).

### Risks

1. **Manual maintenance burden** — architecture components must be kept up-to-date manually. Mitigation: CI check at E.9 T5 — every new Python package in app/ without matching architecture_component row → Finding.
2. **Component granularity drift** — "service" vs "module" boundary varies team-to-team. Mitigation: Steward quarterly review refines kind assignments.
3. **Legacy scope** — existing Forge codebase has many implicit components. Mitigation: migration phase creates legacy_exempted_architecture rows flagged for Steward backfill over first quarter.

### Reversibility

REVERSIBLE — validators can be disabled via feature flag `ARCHITECTURE_ENFORCEMENT=off`; tables remain for audit. Rollback: 1 PR to revert validator addition.

## Evidence captured

- **[CONFIRMED: AI-SDLC §9 text]** ValidArchitecture requires 10 enumerated properties.
- **[CONFIRMED: AI-SDLC Condition #9 text]** "Architecture has explicit dependencies and invariants".
- **[CONFIRMED: THEOREM_VERIFICATION_AIOS_AISDLC.md §5.3 G-AISDLC-9]** gap identified.
- **[ASSUMED]** 7-kind enum (service/module/data_store/interface/external/job/config) sufficient for Forge scope; domain extension requires superseding ADR.
- **[UNKNOWN]** Legacy-row migration volume — depends on existing codebase component count.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — initial DRAFT + CLOSED via Tier 2 mass-accept; content DRAFT pending distinct-actor review.

-- ============================================================================
-- DRAFT — DO NOT RUN until ADR-028 is RATIFIED
-- ============================================================================
-- File: platform/docs/migrations_drafts/2026_04_26_phase1_redesign.sql
-- Status: DRAFT (PROPOSED)
-- Authored: 2026-04-25
-- Source: PLAN_PHASE1_UX_INTEGRATION.md §5.1, ADR-028
-- Blocks: G_5.1 ExitGate cannot fire until this is run + reversed cleanly
-- Why .sql in docs and not platform/alembic/versions/*.py:
--   1. Alembic versions/ is empty; production schema came from
--      Base.metadata.create_all() per SESSION_STATE §1.5. Adding a Python
--      revision file there without a baseline = broken migration chain.
--   2. SQL form is unambiguous about DRAFT status (not auto-discoverable
--      by Alembic; cannot be triggered accidentally).
--   3. On ratification, this file is renamed/ported into a proper
--      Alembic revision OR run as one-shot SQL after stamping the baseline.
-- Reversal:
--   See §99 at the bottom — every CREATE has a matching DROP / every ALTER
--   has a matching column drop. Idempotency: each block uses IF EXISTS /
--   IF NOT EXISTS where Postgres permits.
-- Pre-flight checks before running (manual gate):
--   1. ADR-028 status field reads 'RATIFIED'.
--   2. SESSION_STATE.md U.5 closed (distinct-actor reviewer named).
--   3. Backup taken: pg_dump forge_platform > backup_pre_phase1.sql.
--   4. Existing tables present: SELECT to_regclass for objectives, decisions,
--      acceptance_criteria, evidence_sets — all NOT NULL.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- §1. epistemic_tag ENUM (ADR-028 Decision 2 — REVISED: 6 closed values)
-- ----------------------------------------------------------------------------
-- 6 closed values: 4 from redesign mock + EMPIRICALLY_OBSERVED + TOOL_VERIFIED
-- needed for AI-autonomy distinguishability (CONTRACT §A.6 false-completeness
-- prevention). Mock 'DERIVED' renamed to 'SPEC_DERIVED' to disambiguate from
-- empirical/tool-derived basis.
-- Hyphens in display normalised to underscores for ENUM identifier.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'epistemic_tag') THEN
    CREATE TYPE epistemic_tag AS ENUM (
      'INVENTED',              -- claim with no upstream source (runtime ASSUMED)
      'SPEC_DERIVED',          -- claim follows from cited spec/contract/SLA
      'ADR_CITED',             -- claim appeals to specific ADR ID
      'EMPIRICALLY_OBSERVED',  -- claim from runtime observation (test pass, log query)
      'TOOL_VERIFIED',         -- claim verified by deterministic tool (grep, type-check)
      'STEWARD_AUTHORED'       -- claim held by Steward; sign-off recorded
    );
  END IF;
END $$;

-- ----------------------------------------------------------------------------
-- §2. ALTER TABLE — additive columns on existing tables
-- ----------------------------------------------------------------------------
-- Reversal: ALTER TABLE ... DROP COLUMN. NULL-default = no backfill needed.

ALTER TABLE acceptance_criteria
  ADD COLUMN IF NOT EXISTS epistemic_tag epistemic_tag NULL;

ALTER TABLE decisions
  ADD COLUMN IF NOT EXISTS epistemic_tag epistemic_tag NULL;

ALTER TABLE objectives
  ADD COLUMN IF NOT EXISTS stage VARCHAR(8) NULL,
  ADD COLUMN IF NOT EXISTS autonomy_pinned VARCHAR(8) NULL;

-- Composite check on objectives.stage (ADR-028 Decision 4 REVISED:
-- VARCHAR + CHECK rather than SMALLINT — self-documenting in raw SQL,
-- consistent with existing `objectives.status VARCHAR(20) CHECK IN (...)`
-- pattern. AI agents see one pattern, not an exception).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'valid_objective_stage'
  ) THEN
    ALTER TABLE objectives
      ADD CONSTRAINT valid_objective_stage
      CHECK (stage IS NULL OR stage IN ('KICKOFF','PLAN','EXEC','VERIFY'));
  END IF;
END $$;

-- Composite check on objectives.autonomy_pinned (ADR-028 Decision 1
-- composite: enum is 'L0'/'L1'/'L2'/'L3'; NULL = follow project default)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'valid_autonomy_pinned'
  ) THEN
    ALTER TABLE objectives
      ADD CONSTRAINT valid_autonomy_pinned
      CHECK (autonomy_pinned IS NULL
             OR autonomy_pinned IN ('L0','L1','L2','L3'));
  END IF;
END $$;

-- Note: objectives.autonomy_optout BOOLEAN is RETAINED for transition.
-- A view (objective_autonomy_v) synthesises a single effective value
-- (not part of this migration; lives in repository code).

-- ----------------------------------------------------------------------------
-- §3. CGAID alternatives table (ADR-028 §Composite, mock §3)
-- ----------------------------------------------------------------------------
-- Replaces decisions.alternatives_considered TEXT free-form blob.
-- Old TEXT column retained until next-phase deprecation revision.
CREATE TABLE IF NOT EXISTS alternatives (
  id            BIGSERIAL PRIMARY KEY,
  decision_id   INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  position      SMALLINT NOT NULL,
  text          TEXT NOT NULL,
  src           TEXT NULL,
  blocks_count  INTEGER NOT NULL DEFAULT 0,
  task_ref      INTEGER NULL REFERENCES tasks(id) ON DELETE SET NULL,
  impact_deltas JSONB NULL,
  rejected_because TEXT NULL,           -- aligns with P21 root_cause_uniqueness
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT alt_position_nonneg  CHECK (position >= 0),
  CONSTRAINT alt_text_nonempty    CHECK (length(text) >= 5),
  CONSTRAINT alt_uniq_pos_per_dec UNIQUE (decision_id, position)
);

CREATE INDEX IF NOT EXISTS ix_alternatives_decision_id
  ON alternatives (decision_id);

-- ----------------------------------------------------------------------------
-- §4. side_effect_map table (ADR-028 Decision 3)
-- ----------------------------------------------------------------------------
-- Persistence layer for C.2 SideEffectRegistry. impact_deltas is free-form
-- JSONB at DB; Pydantic validates shape at write boundary
-- (see app/schemas/side_effect_map.py — to be authored).
CREATE TABLE IF NOT EXISTS side_effect_map (
  id              BIGSERIAL PRIMARY KEY,
  decision_id     INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  kind            VARCHAR(64) NOT NULL,
  owner           VARCHAR(128) NULL,           -- NULL = K1 owner-required gate WILL fire
  evidence_set_id INTEGER NULL REFERENCES evidence_sets(id) ON DELETE SET NULL,
  blocking        BOOLEAN NOT NULL DEFAULT false,
  impact_deltas   JSONB NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT sem_kind_nonempty CHECK (length(kind) >= 1)
);

CREATE INDEX IF NOT EXISTS ix_side_effect_map_decision_id
  ON side_effect_map (decision_id);
CREATE INDEX IF NOT EXISTS ix_side_effect_map_owner_null
  ON side_effect_map (decision_id) WHERE owner IS NULL;

-- ----------------------------------------------------------------------------
-- §5. cascade_dod_item table (ADR-028 §Composite, mock §4)
-- ----------------------------------------------------------------------------
-- Per-objective Definition-of-Done checklist. Replaces
-- objectives.success_criteria TEXT (kept for transition).
CREATE TABLE IF NOT EXISTS cascade_dod_item (
  id           BIGSERIAL PRIMARY KEY,
  objective_id INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
  position     SMALLINT NOT NULL,
  text         TEXT NOT NULL,
  signed_by    VARCHAR(128) NULL,
  signed_at    TIMESTAMPTZ NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT dod_position_nonneg     CHECK (position >= 0),
  CONSTRAINT dod_text_nonempty       CHECK (length(text) >= 10),
  CONSTRAINT dod_uniq_pos_per_obj    UNIQUE (objective_id, position),
  CONSTRAINT dod_signature_complete  CHECK (
    (signed_by IS NULL AND signed_at IS NULL) OR
    (signed_by IS NOT NULL AND signed_at IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS ix_cascade_dod_item_objective_id
  ON cascade_dod_item (objective_id);

-- ----------------------------------------------------------------------------
-- §6. kill_criteria_event_log table (ADR-028 §Composite, mock §5)
-- ----------------------------------------------------------------------------
-- K1..K6 firing log. Append-only. K1 owner-required, K2 evidence-link,
-- K3 reversibility, K4 solo-verifier, K5 budget-cap, K6 contract-violation.
-- These are GATES over GateRegistry — this table is a *firing audit*, not
-- the gates themselves.
CREATE TABLE IF NOT EXISTS kill_criteria_event_log (
  id              BIGSERIAL PRIMARY KEY,
  objective_id    INTEGER NULL REFERENCES objectives(id) ON DELETE SET NULL,
  decision_id     INTEGER NULL REFERENCES decisions(id) ON DELETE SET NULL,
  task_id         INTEGER NULL REFERENCES tasks(id) ON DELETE SET NULL,
  kc_code         VARCHAR(8) NOT NULL,         -- 'K1'..'K6'
  fired_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  reason          TEXT NOT NULL,
  evidence_set_id INTEGER NULL REFERENCES evidence_sets(id) ON DELETE SET NULL,

  CONSTRAINT kc_code_valid CHECK (kc_code IN ('K1','K2','K3','K4','K5','K6')),
  CONSTRAINT kc_reason_nonempty CHECK (length(reason) >= 5),
  -- At least one entity reference (objective/decision/task) so the row is meaningful.
  CONSTRAINT kc_at_least_one_ref CHECK (
    objective_id IS NOT NULL
    OR decision_id IS NOT NULL
    OR task_id IS NOT NULL
  )
);

CREATE INDEX IF NOT EXISTS ix_kc_log_fired_at  ON kill_criteria_event_log (fired_at DESC);
CREATE INDEX IF NOT EXISTS ix_kc_log_kc_code   ON kill_criteria_event_log (kc_code);
CREATE INDEX IF NOT EXISTS ix_kc_log_objective ON kill_criteria_event_log (objective_id) WHERE objective_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- §7. trust_debt_snapshot table (ADR-028 §Composite, mock §6)
-- ----------------------------------------------------------------------------
-- Per-project trust-debt computation history. The trust-debt FORMULA is
-- INVENTED in the redesign mock and requires Steward ratification before
-- any value here is read in Steward-facing UI as authoritative. Until then,
-- the dashboard reads it as "indicative only" (rendering layer concern,
-- not schema).
CREATE TABLE IF NOT EXISTS trust_debt_snapshot (
  id            BIGSERIAL PRIMARY KEY,
  project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  value         NUMERIC(10,4) NOT NULL,
  decomposition JSONB NULL,                    -- per-component breakdown for explainability

  CONSTRAINT td_value_nonneg CHECK (value >= 0)
);

CREATE INDEX IF NOT EXISTS ix_trust_debt_snapshot_project_time
  ON trust_debt_snapshot (project_id, computed_at DESC);

COMMIT;

-- ============================================================================
-- §99. REVERSAL — `down()` equivalent
-- ============================================================================
-- Run ONLY if rolling back this migration. Each section reverses its
-- corresponding §1..§7 above. Order: drop tables FIRST (FKs), then ALTER
-- columns OFF, then DROP TYPE.
--
-- BEGIN;
-- DROP TABLE IF EXISTS trust_debt_snapshot;
-- DROP TABLE IF EXISTS kill_criteria_event_log;
-- DROP TABLE IF EXISTS cascade_dod_item;
-- DROP TABLE IF EXISTS side_effect_map;
-- DROP TABLE IF EXISTS alternatives;
--
-- ALTER TABLE objectives DROP CONSTRAINT IF EXISTS valid_autonomy_pinned;
-- ALTER TABLE objectives DROP CONSTRAINT IF EXISTS valid_objective_stage;
-- ALTER TABLE objectives DROP COLUMN IF EXISTS autonomy_pinned;
-- ALTER TABLE objectives DROP COLUMN IF EXISTS stage;
--
-- ALTER TABLE decisions DROP COLUMN IF EXISTS epistemic_tag;
-- ALTER TABLE acceptance_criteria DROP COLUMN IF EXISTS epistemic_tag;
--
-- DROP TYPE IF EXISTS epistemic_tag;
-- COMMIT;

-- ============================================================================
-- §100. Backfill (PHASE 1.b — separate revision after stage 1 success)
-- ============================================================================
-- objectives.stage backfill heuristic per ADR-028 Decision 4 REVISED:
--   UPDATE objectives SET stage = 'EXEC'
--     WHERE id IN (SELECT objective_id FROM tasks WHERE status IN ('IN_PROGRESS','DONE'))
--       AND stage IS NULL;
--   UPDATE objectives SET stage = 'KICKOFF'
--     WHERE id NOT IN (SELECT objective_id FROM tasks)
--       AND stage IS NULL;
-- (Anything ambiguous → stays NULL → renders "stage unknown".)
--
-- objectives.autonomy_pinned backfill from existing autonomy_optout:
--   UPDATE objectives SET autonomy_pinned = 'L0'  -- L0 = no autonomy / opt-out
--     WHERE autonomy_optout = true AND autonomy_pinned IS NULL;
-- (autonomy_optout=false rows stay NULL = follow project default.)
--
-- Backfill is a separate transaction so DDL stage 1 can roll back cleanly.

-- ============================================================================
-- §101. Verification queries (post-up, post-backfill)
-- ============================================================================
-- After running this migration, the following SELECT statements MUST succeed:
--
-- SELECT typname FROM pg_type WHERE typname = 'epistemic_tag';
--   -- Expect: 1 row.
--
-- SELECT to_regclass('alternatives'),
--        to_regclass('side_effect_map'),
--        to_regclass('cascade_dod_item'),
--        to_regclass('kill_criteria_event_log'),
--        to_regclass('trust_debt_snapshot');
--   -- Expect: all 5 non-NULL.
--
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name='objectives' AND column_name IN ('stage','autonomy_pinned');
--   -- Expect: 2 rows.
--
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name='decisions' AND column_name='epistemic_tag';
--   -- Expect: 1 row.
--
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name='acceptance_criteria' AND column_name='epistemic_tag';
--   -- Expect: 1 row.
--
-- These 5 verifications collectively constitute G_5.1 ExitGate evidence.

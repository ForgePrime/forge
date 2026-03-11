-- Migration 004: Objectives overhaul — descriptive KRs + guideline_ids + relations
-- Supports O-008: Objectives module overhaul
-- Idempotent: safe to run multiple times (IF NOT EXISTS / IF EXISTS checks)

-- ============================================================
-- 1. key_results: add description column, make metric nullable
-- ============================================================
ALTER TABLE key_results ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE key_results ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'NOT_STARTED';

-- Make metric nullable (was NOT NULL) — descriptive KRs have no metric
ALTER TABLE key_results ALTER COLUMN metric DROP NOT NULL;

-- Make target nullable — descriptive KRs have no target
ALTER TABLE key_results ALTER COLUMN target DROP NOT NULL;

-- CHECK: each KR must have either metric or description (or both)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_kr_metric_or_description'
    ) THEN
        ALTER TABLE key_results ADD CONSTRAINT chk_kr_metric_or_description
            CHECK ((metric IS NOT NULL) OR (description IS NOT NULL));
    END IF;
END $$;

-- ============================================================
-- 2. objectives: add guideline_ids and relations columns
-- ============================================================
ALTER TABLE objectives ADD COLUMN IF NOT EXISTS guideline_ids TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE objectives ADD COLUMN IF NOT EXISTS relations JSONB NOT NULL DEFAULT '[]'::jsonb;

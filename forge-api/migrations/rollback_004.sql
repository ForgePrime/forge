-- Rollback migration 004: Objectives overhaul
-- WARNING: This will drop columns and data. Only run if you need to revert.

-- Remove CHECK constraint
ALTER TABLE key_results DROP CONSTRAINT IF EXISTS chk_kr_metric_or_description;

-- Remove new columns from key_results
ALTER TABLE key_results DROP COLUMN IF EXISTS description;
ALTER TABLE key_results DROP COLUMN IF EXISTS status;

-- Restore NOT NULL on metric and target (will fail if any rows have NULL values)
-- Manually fix data first: UPDATE key_results SET metric = 'unknown' WHERE metric IS NULL;
-- ALTER TABLE key_results ALTER COLUMN metric SET NOT NULL;
-- ALTER TABLE key_results ALTER COLUMN target SET NOT NULL;

-- Remove new columns from objectives
ALTER TABLE objectives DROP COLUMN IF EXISTS guideline_ids;
ALTER TABLE objectives DROP COLUMN IF EXISTS relations;

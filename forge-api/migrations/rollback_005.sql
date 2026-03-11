-- Rollback migration 005: Skills
-- WARNING: This will drop the skills table and ALL data. Only run if you need to revert.

BEGIN;

-- Drop indexes first (they'll be dropped with the table, but explicit for clarity)
DROP INDEX IF EXISTS idx_skills_tags;
DROP INDEX IF EXISTS idx_skills_scopes;
DROP INDEX IF EXISTS idx_skills_status;
DROP INDEX IF EXISTS idx_skills_category;
DROP INDEX IF EXISTS idx_skills_fts;
DROP INDEX IF EXISTS idx_skills_created_at;
DROP INDEX IF EXISTS idx_skills_updated_at;

-- Drop table
DROP TABLE IF EXISTS skills;

COMMIT;

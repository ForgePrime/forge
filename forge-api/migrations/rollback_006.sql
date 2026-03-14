-- Rollback migration 006: Workflow Execution Engine
-- WARNING: This will drop workflow tables and ALL execution data.

BEGIN;

-- Drop indexes first (explicit for clarity)
DROP INDEX IF EXISTS idx_workflow_exec_project_status;
DROP INDEX IF EXISTS idx_workflow_exec_ext_id;
DROP INDEX IF EXISTS idx_workflow_exec_status;
DROP INDEX IF EXISTS idx_workflow_steps_execution;
DROP INDEX IF EXISTS idx_workflow_exec_created_at;

-- Drop tables (step_results first due to FK)
DROP TABLE IF EXISTS workflow_step_results;
DROP TABLE IF EXISTS workflow_executions;

-- Remove migration tracking entry so migrate.py can re-apply
DELETE FROM schema_migrations WHERE version = '006';

COMMIT;

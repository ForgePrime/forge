-- Migration 006: Workflow Execution Engine
-- Supports O-001: Workflow Execution Engine (forge-web transformation)
-- D-002: Postgres persistence (user override from JSON)
-- D-001: Custom state machine architecture
-- Idempotent: safe to run multiple times (IF NOT EXISTS checks)

BEGIN;

-- ============================================================
-- Workflow Executions — runtime state of a workflow instance
-- ============================================================
CREATE TABLE IF NOT EXISTS workflow_executions (
    id              SERIAL PRIMARY KEY,
    ext_id          TEXT NOT NULL,                      -- WE-001, WE-002, ...
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    workflow_def_id TEXT NOT NULL,                      -- e.g. 'full-lifecycle', 'simplified-next'
    objective_id    TEXT,                               -- O-NNN reference (optional)
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending', 'running', 'paused',
                        'completed', 'failed', 'cancelled'
                    )),
    current_step    TEXT,                               -- step_id currently executing
    variables       JSONB NOT NULL DEFAULT '{}',        -- workflow-scoped variables (user responses, step outputs)
    pause_reason    TEXT,                               -- why paused (decision_id or 'awaiting_user_decision')
    error           TEXT,                               -- error message on failure
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Workflow Step Results — per-step execution outcome
-- ============================================================
CREATE TABLE IF NOT EXISTS workflow_step_results (
    id              SERIAL PRIMARY KEY,
    execution_id    INT NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    step_id         TEXT NOT NULL,                      -- matches StepDefinition.id
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending', 'running', 'completed',
                        'failed', 'skipped'
                    )),
    output          JSONB,                             -- step output (summary, artifacts, etc.)
    session_id      TEXT,                              -- LLM ChatSession ID (for llm_agent steps)
    error           TEXT,                              -- error message on failure
    decision_ids    TEXT[] NOT NULL DEFAULT '{}',      -- D-NNN decisions made during step
    retries         INT NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    UNIQUE (execution_id, step_id)
);

-- ============================================================
-- Indexes
-- ============================================================

-- Main query pattern: list executions by project + status
CREATE INDEX IF NOT EXISTS idx_workflow_exec_project_status
    ON workflow_executions (project_id, status);

-- Lookup by ext_id (used by router)
CREATE INDEX IF NOT EXISTS idx_workflow_exec_ext_id
    ON workflow_executions (ext_id);

-- Recovery: find running/paused executions across all projects
CREATE INDEX IF NOT EXISTS idx_workflow_exec_status
    ON workflow_executions (status)
    WHERE status IN ('running', 'paused');

-- Step results by execution (already covered by FK index, but explicit for clarity)
CREATE INDEX IF NOT EXISTS idx_workflow_steps_execution
    ON workflow_step_results (execution_id);

-- Timestamps for sorting
CREATE INDEX IF NOT EXISTS idx_workflow_exec_created_at
    ON workflow_executions (created_at);

COMMIT;

-- Migration 005: Skills — global platform-level entity (no project_id)
-- Supports O-009: Skills Management
-- ADR-1 (D-023): Full DB storage — SKILL.md as TEXT, evals as JSONB
-- ADR-2 (D-023): Global routing — no project_id FK
-- Idempotent: safe to run multiple times (IF NOT EXISTS checks)

BEGIN;

-- ============================================================
-- Skills table — global entity (no project_id FK)
-- ============================================================
CREATE TABLE IF NOT EXISTS skills (
    id                      SERIAL PRIMARY KEY,
    ext_id                  TEXT NOT NULL UNIQUE,              -- S-001, S-002, ...
    name                    TEXT NOT NULL,
    description             TEXT NOT NULL DEFAULT '',
    category                TEXT NOT NULL DEFAULT 'custom'
                            CHECK (category IN (
                                'workflow', 'analysis', 'generation', 'validation',
                                'integration', 'refactoring', 'testing', 'deployment',
                                'documentation', 'custom'
                            )),
    status                  TEXT NOT NULL DEFAULT 'DRAFT'
                            CHECK (status IN ('DRAFT', 'ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    skill_md_content        TEXT,                              -- Full SKILL.md content (ADR-1)
    evals_json              JSONB NOT NULL DEFAULT '[]',       -- evals/evals.json content
    resources               JSONB NOT NULL DEFAULT '{}',       -- Bundled resource metadata
    teslint_config          JSONB,                             -- Optional TESLint overrides
    tags                    TEXT[] NOT NULL DEFAULT '{}',       -- Free-form labels
    scopes                  TEXT[] NOT NULL DEFAULT '{}',       -- Guideline scope alignment
    promoted_with_warnings  BOOLEAN NOT NULL DEFAULT FALSE,    -- Force-promoted past TESLint errors
    promotion_history       JSONB NOT NULL DEFAULT '[]',       -- [{promoted_at, promoted_by, errors, warnings, forced}]
    usage_count             INTEGER NOT NULL DEFAULT 0,        -- Tasks referencing this skill
    created_by              TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Indexes
-- ============================================================

-- GIN indexes on array columns
CREATE INDEX IF NOT EXISTS idx_skills_tags ON skills USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_skills_scopes ON skills USING GIN (scopes);

-- B-tree indexes for filtering
CREATE INDEX IF NOT EXISTS idx_skills_status ON skills (status);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills (category);

-- Full-text search on name + description
CREATE INDEX IF NOT EXISTS idx_skills_fts ON skills
    USING GIN (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, '')));

-- Timestamp index for sorting
CREATE INDEX IF NOT EXISTS idx_skills_created_at ON skills (created_at);
CREATE INDEX IF NOT EXISTS idx_skills_updated_at ON skills (updated_at);

COMMIT;

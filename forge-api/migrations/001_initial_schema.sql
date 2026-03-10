-- Forge Platform v2 — Initial Schema
-- Reference: docs/FORGE-PLATFORM-V2.md Section 7.4
-- All entity tables with fields matching core/*.py module structures.

BEGIN;

-- ============================================================
-- Projects
-- ============================================================
CREATE TABLE projects (
    id          SERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    goal        TEXT NOT NULL DEFAULT '',
    config      JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Objectives (core/objectives.py)
-- ============================================================
CREATE TABLE objectives (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ext_id          TEXT NOT NULL,                  -- O-001, O-002, ...
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    appetite        TEXT NOT NULL DEFAULT 'medium', -- small, medium, large
    scope           TEXT NOT NULL DEFAULT 'project',-- project, cross-project
    status          TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, ACHIEVED, ABANDONED, PAUSED
    assumptions     JSONB NOT NULL DEFAULT '[]',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    derived_guidelines TEXT[] NOT NULL DEFAULT '{}',-- G-NNN references
    knowledge_ids   TEXT[] NOT NULL DEFAULT '{}',   -- K-NNN references
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Key Results (nested in objectives in JSON, separate table in DB)
-- ============================================================
CREATE TABLE key_results (
    id              SERIAL PRIMARY KEY,
    objective_id    INT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    ext_id          TEXT NOT NULL,                  -- KR-001, KR-002, ...
    metric          TEXT NOT NULL,
    baseline        NUMERIC NOT NULL DEFAULT 0,
    target          NUMERIC NOT NULL,
    current         NUMERIC NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (objective_id, ext_id)
);

-- ============================================================
-- Ideas (core/ideas.py)
-- ============================================================
CREATE TABLE ideas (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id       INT REFERENCES ideas(id) ON DELETE SET NULL,
    ext_id          TEXT NOT NULL,                  -- I-001, I-002, ...
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'feature',-- feature, improvement, experiment, migration, refactor, business-opportunity, research, infrastructure
    status          TEXT NOT NULL DEFAULT 'DRAFT',  -- DRAFT, EXPLORING, APPROVED, COMMITTED, REJECTED
    appetite        TEXT NOT NULL DEFAULT 'medium',
    priority        TEXT NOT NULL DEFAULT 'MEDIUM', -- HIGH, MEDIUM, LOW
    tags            TEXT[] NOT NULL DEFAULT '{}',
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    knowledge_ids   TEXT[] NOT NULL DEFAULT '{}',
    guidelines      TEXT[] NOT NULL DEFAULT '{}',   -- G-NNN references
    advances_key_results TEXT[] NOT NULL DEFAULT '{}',-- O-001/KR-001 references
    rejection_reason TEXT,
    merged_into     TEXT,                           -- I-NNN reference
    exploration_notes TEXT NOT NULL DEFAULT '',
    committed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Tasks (core/pipeline.py)
-- ============================================================
CREATE TABLE tasks (
    id                  SERIAL PRIMARY KEY,
    project_id          INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ext_id              TEXT NOT NULL,                  -- T-001, T-002, ...
    name                TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    instruction         TEXT NOT NULL DEFAULT '',
    type                TEXT NOT NULL DEFAULT 'feature',-- feature, bug, chore, investigation
    status              TEXT NOT NULL DEFAULT 'TODO',   -- TODO, CLAIMING, IN_PROGRESS, DONE, FAILED, SKIPPED
    origin              TEXT NOT NULL DEFAULT '',       -- I-NNN or free text
    origin_idea_id      INT REFERENCES ideas(id) ON DELETE SET NULL,
    skill               TEXT,
    parallel            BOOLEAN NOT NULL DEFAULT FALSE,
    acceptance_criteria JSONB NOT NULL DEFAULT '[]',
    test_requirements   JSONB,
    depends_on          TEXT[] NOT NULL DEFAULT '{}',   -- T-NNN references (denormalized)
    conflicts_with      TEXT[] NOT NULL DEFAULT '{}',   -- T-NNN references (denormalized)
    knowledge_ids       TEXT[] NOT NULL DEFAULT '{}',
    scopes              TEXT[] NOT NULL DEFAULT '{}',
    blocked_by_decisions TEXT[] NOT NULL DEFAULT '{}',  -- D-NNN references
    agent               TEXT,                          -- agent name for multi-agent
    failed_reason       TEXT,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Decisions (core/decisions.py)
-- ============================================================
CREATE TABLE decisions (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ext_id          TEXT NOT NULL,                  -- D-001, D-002, ...
    task_id         TEXT NOT NULL DEFAULT '',       -- T-NNN reference
    type            TEXT NOT NULL DEFAULT 'implementation', -- implementation, convention, architecture, dependency, security, performance, testing, naming, constraint, business, strategy, exploration, risk, other
    status          TEXT NOT NULL DEFAULT 'OPEN',   -- OPEN, CLOSED, DEFERRED, ANALYZING, ACCEPTED, MITIGATED
    issue           TEXT NOT NULL DEFAULT '',
    recommendation  TEXT NOT NULL DEFAULT '',
    reasoning       TEXT NOT NULL DEFAULT '',
    alternatives    JSONB NOT NULL DEFAULT '[]',
    confidence      TEXT NOT NULL DEFAULT 'MEDIUM', -- HIGH, MEDIUM, LOW
    decided_by      TEXT NOT NULL DEFAULT '',
    file            TEXT,
    scope           TEXT,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    -- Exploration-specific fields
    exploration_type TEXT,
    findings        JSONB,
    options         JSONB,
    open_questions  JSONB,
    -- Risk-specific fields
    severity        TEXT,                           -- critical, high, medium, low
    likelihood      TEXT,                           -- high, medium, low
    linked_entity_type TEXT,
    linked_entity_id   TEXT,
    mitigation_plan TEXT,
    resolution_notes TEXT,
    -- Exploration-specific extra fields
    blockers        JSONB,                            -- list of blockers
    ready_for_tracker BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_refs   JSONB,                            -- list of evidence references
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Changes (core/changes.py)
-- ============================================================
CREATE TABLE changes (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ext_id          TEXT NOT NULL,                  -- C-001, C-002, ...
    task_id         TEXT NOT NULL DEFAULT '',       -- T-NNN reference
    file            TEXT NOT NULL DEFAULT '',
    action          TEXT NOT NULL DEFAULT 'edit',   -- create, edit, delete
    summary         TEXT NOT NULL DEFAULT '',
    reasoning_trace JSONB NOT NULL DEFAULT '[]',
    decision_ids    TEXT[] NOT NULL DEFAULT '{}',
    guidelines_checked TEXT[] NOT NULL DEFAULT '{}',
    group_id        TEXT NOT NULL DEFAULT '',        -- groups related changes
    lines_added     INT NOT NULL DEFAULT 0,
    lines_removed   INT NOT NULL DEFAULT 0,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Lessons (core/lessons.py)
-- ============================================================
CREATE TABLE lessons (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ext_id          TEXT NOT NULL,                  -- L-001, L-002, ...
    category        TEXT NOT NULL DEFAULT 'pattern-discovered',
    title           TEXT NOT NULL,
    detail          TEXT NOT NULL DEFAULT '',
    task_id         TEXT,                           -- T-NNN reference
    decision_ids    TEXT[] NOT NULL DEFAULT '{}',
    severity        TEXT NOT NULL DEFAULT 'minor',  -- critical, important, minor
    applies_to      TEXT,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    promoted_to_guideline TEXT,                      -- G-NNN ID or NULL
    promoted_to_knowledge TEXT,                      -- K-NNN ID or NULL
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, ext_id)
);

-- ============================================================
-- Guidelines (core/guidelines.py)
-- ============================================================
CREATE TABLE guidelines (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id) ON DELETE CASCADE, -- NULL = global
    ext_id          TEXT NOT NULL,                  -- G-001, G-002, ...
    title           TEXT NOT NULL,
    scope           TEXT NOT NULL,                  -- backend, frontend, database, general, etc.
    content         TEXT NOT NULL,
    rationale       TEXT NOT NULL DEFAULT '',
    examples        JSONB NOT NULL DEFAULT '[]',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    weight          TEXT NOT NULL DEFAULT 'should', -- must, should, may
    status          TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, DEPRECATED, SUPERSEDED
    derived_from    TEXT,                           -- O-NNN reference
    imported_from   TEXT,                           -- source/G-NNN for imports
    promoted_from   TEXT,                           -- L-NNN for promoted lessons
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE NULLS NOT DISTINCT (project_id, ext_id) -- PG15+: NULL-safe unique
);

-- ============================================================
-- Knowledge (core/knowledge.py)
-- ============================================================
CREATE TABLE knowledge (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id) ON DELETE CASCADE, -- NULL = global
    ext_id          TEXT NOT NULL,                  -- K-001, K-002, ...
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,                  -- domain, technical, process, convention, reference
    content         TEXT NOT NULL DEFAULT '',
    current_version INT NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'DRAFT',  -- DRAFT, ACTIVE, REVIEW_NEEDED, DEPRECATED, ARCHIVED
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    dependencies    TEXT[] NOT NULL DEFAULT '{}',   -- K-NNN references (knowledge deps)
    source          TEXT,
    source_type     TEXT,                           -- documentation, lesson, research, user, codebase, ai-extraction
    created_by      TEXT NOT NULL DEFAULT '',
    linked_entities JSONB NOT NULL DEFAULT '[]',   -- [{entity_type, entity_id, relation}]
    review          JSONB,                          -- {last_reviewed_at, review_interval_days, next_review_at}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE NULLS NOT DISTINCT (project_id, ext_id) -- PG15+: NULL-safe unique
);

-- ============================================================
-- Knowledge Versions (PostgreSQL-only, Section 7.2)
-- ============================================================
CREATE TABLE knowledge_versions (
    id              SERIAL PRIMARY KEY,
    knowledge_id    INT NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    content         TEXT NOT NULL,
    changed_by      TEXT NOT NULL DEFAULT '',
    change_reason   TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (knowledge_id, version)
);

-- ============================================================
-- AC Templates (core/ac_templates.py)
-- ============================================================
CREATE TABLE ac_templates (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id) ON DELETE CASCADE, -- NULL = global
    ext_id          TEXT NOT NULL,                  -- AC-001, AC-002, ...
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    template        TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'general',-- api, frontend, backend, testing, security, general
    verification_method TEXT NOT NULL DEFAULT '',
    parameters      JSONB NOT NULL DEFAULT '{}',
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'ACTIVE',
    usage_count     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE NULLS NOT DISTINCT (project_id, ext_id) -- PG15+: NULL-safe unique
);

-- ============================================================
-- Gates (stored in tracker config in JSON, separate table in DB)
-- ============================================================
CREATE TABLE gates (
    id              SERIAL PRIMARY KEY,
    project_id      INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    command         TEXT NOT NULL,
    required        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, name)
);

COMMIT;

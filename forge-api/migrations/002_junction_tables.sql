-- Forge Platform v2 — Junction Tables
-- Reference: docs/FORGE-PLATFORM-V2.md Section 7.4
-- Many-to-many relationships and cross-entity links.

BEGIN;

-- ============================================================
-- Knowledge Links (polymorphic association)
-- Links knowledge entries to any entity type
-- ============================================================
CREATE TABLE knowledge_links (
    id              SERIAL PRIMARY KEY,
    knowledge_id    INT NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    entity_type     TEXT NOT NULL,      -- 'objective', 'idea', 'task', 'decision', 'guideline'
    entity_id       INT NOT NULL,       -- ID of the linked entity
    relation        TEXT NOT NULL DEFAULT 'references', -- references, derived-from, supports, contradicts
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (knowledge_id, entity_type, entity_id)
);

-- ============================================================
-- Task Dependencies (task DAG edges)
-- ============================================================
CREATE TABLE task_dependencies (
    task_id         INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_id   INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, depends_on_id),
    CHECK (task_id <> depends_on_id)
);

-- ============================================================
-- Task Conflicts (mutual exclusion for parallel execution)
-- ============================================================
CREATE TABLE task_conflicts (
    task_id         INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    conflicts_with_id INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, conflicts_with_id),
    CHECK (task_id <> conflicts_with_id)
);

-- ============================================================
-- Task AC (instantiated acceptance criteria from templates)
-- ============================================================
CREATE TABLE task_ac (
    id              SERIAL PRIMARY KEY,
    task_id         INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    ac_template_id  INT NOT NULL REFERENCES ac_templates(id) ON DELETE CASCADE,
    params          JSONB NOT NULL DEFAULT '{}',
    instantiated_text TEXT NOT NULL DEFAULT '',
    passed          BOOLEAN,
    checked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (task_id, ac_template_id)
);

-- ============================================================
-- Task Knowledge (knowledge entries relevant to a task)
-- ============================================================
CREATE TABLE task_knowledge (
    task_id         INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    knowledge_id    INT NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, knowledge_id)
);

-- ============================================================
-- Idea Relations (parent/child, related, alternative, merged)
-- ============================================================
CREATE TABLE idea_relations (
    id              SERIAL PRIMARY KEY,
    idea_id         INT NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    target_id       INT NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    relation_type   TEXT NOT NULL DEFAULT 'related', -- parent, child, related, alternative, merged-into
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (idea_id, target_id, relation_type),
    CHECK (idea_id <> target_id)
);

-- ============================================================
-- Decision Alternatives (normalized from JSONB for querying)
-- ============================================================
CREATE TABLE decision_alternatives (
    id              SERIAL PRIMARY KEY,
    decision_id     INT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    pros            JSONB NOT NULL DEFAULT '[]',
    cons            JSONB NOT NULL DEFAULT '[]',
    chosen          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Task Decision Links (which decisions affect which tasks)
-- ============================================================
CREATE TABLE task_decisions (
    task_id         INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    decision_id     INT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    relation        TEXT NOT NULL DEFAULT 'blocked-by', -- blocked-by, informed-by, created-by
    PRIMARY KEY (task_id, decision_id)
);

-- ============================================================
-- Change Decision Links (which decisions led to which changes)
-- ============================================================
CREATE TABLE change_decisions (
    change_id       INT NOT NULL REFERENCES changes(id) ON DELETE CASCADE,
    decision_id     INT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    PRIMARY KEY (change_id, decision_id)
);

-- ============================================================
-- Change Guidelines Checked (audit trail)
-- ============================================================
CREATE TABLE change_guidelines (
    change_id       INT NOT NULL REFERENCES changes(id) ON DELETE CASCADE,
    guideline_id    INT NOT NULL REFERENCES guidelines(id) ON DELETE CASCADE,
    PRIMARY KEY (change_id, guideline_id)
);

-- ============================================================
-- Lesson Links (lessons linked to tasks and decisions)
-- ============================================================
CREATE TABLE lesson_decisions (
    lesson_id       INT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    decision_id     INT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    PRIMARY KEY (lesson_id, decision_id)
);

COMMIT;

-- Forge Platform v2 — Indexes
-- Reference: docs/FORGE-PLATFORM-V2.md Section 7.4
-- GIN indexes for arrays, FTS for knowledge, standard indexes for queries.

BEGIN;

-- ============================================================
-- GIN indexes on array columns (scopes, tags)
-- ============================================================
CREATE INDEX idx_objectives_tags ON objectives USING GIN (tags);
CREATE INDEX idx_objectives_scopes ON objectives USING GIN (scopes);

CREATE INDEX idx_ideas_tags ON ideas USING GIN (tags);
CREATE INDEX idx_ideas_scopes ON ideas USING GIN (scopes);

CREATE INDEX idx_tasks_scopes ON tasks USING GIN (scopes);
CREATE INDEX idx_tasks_knowledge_ids ON tasks USING GIN (knowledge_ids);
CREATE INDEX idx_tasks_depends_on ON tasks USING GIN (depends_on);
CREATE INDEX idx_tasks_conflicts_with ON tasks USING GIN (conflicts_with);
CREATE INDEX idx_tasks_blocked_by_decisions ON tasks USING GIN (blocked_by_decisions);

CREATE INDEX idx_decisions_tags ON decisions USING GIN (tags);

CREATE INDEX idx_guidelines_tags ON guidelines USING GIN (tags);

CREATE INDEX idx_knowledge_scopes ON knowledge USING GIN (scopes);
CREATE INDEX idx_knowledge_tags ON knowledge USING GIN (tags);
CREATE INDEX idx_knowledge_dependencies ON knowledge USING GIN (dependencies);

CREATE INDEX idx_objectives_knowledge_ids ON objectives USING GIN (knowledge_ids);
CREATE INDEX idx_ideas_knowledge_ids ON ideas USING GIN (knowledge_ids);
CREATE INDEX idx_ideas_guidelines ON ideas USING GIN (guidelines);

CREATE INDEX idx_ac_templates_scopes ON ac_templates USING GIN (scopes);
CREATE INDEX idx_ac_templates_tags ON ac_templates USING GIN (tags);

CREATE INDEX idx_lessons_tags ON lessons USING GIN (tags);
CREATE INDEX idx_lessons_decision_ids ON lessons USING GIN (decision_ids);

CREATE INDEX idx_changes_decision_ids ON changes USING GIN (decision_ids);
CREATE INDEX idx_changes_guidelines_checked ON changes USING GIN (guidelines_checked);

-- ============================================================
-- Full-text search on knowledge (title + content)
-- ============================================================
CREATE INDEX idx_knowledge_fts ON knowledge
    USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')));

-- ============================================================
-- Standard B-tree indexes for filtering & joins
-- ============================================================

-- Status indexes (most common filter)
CREATE INDEX idx_objectives_status ON objectives (status);
CREATE INDEX idx_ideas_status ON ideas (status);
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_decisions_status ON decisions (status);
CREATE INDEX idx_guidelines_status ON guidelines (status);
CREATE INDEX idx_knowledge_status ON knowledge (status);
CREATE INDEX idx_ac_templates_status ON ac_templates (status);

-- Category / type indexes
CREATE INDEX idx_ideas_category ON ideas (category);
CREATE INDEX idx_tasks_type ON tasks (type);
CREATE INDEX idx_decisions_type ON decisions (type);
CREATE INDEX idx_knowledge_category ON knowledge (category);
CREATE INDEX idx_ac_templates_category ON ac_templates (category);
CREATE INDEX idx_lessons_category ON lessons (category);
CREATE INDEX idx_lessons_severity ON lessons (severity);

-- Scope index on guidelines (frequently queried by scope)
CREATE INDEX idx_guidelines_scope ON guidelines (scope);

-- Foreign key indexes (not auto-created by PostgreSQL)
CREATE INDEX idx_objectives_project_id ON objectives (project_id);
CREATE INDEX idx_ideas_project_id ON ideas (project_id);
CREATE INDEX idx_ideas_parent_id ON ideas (parent_id);
CREATE INDEX idx_tasks_project_id ON tasks (project_id);
CREATE INDEX idx_tasks_origin_idea_id ON tasks (origin_idea_id);
CREATE INDEX idx_decisions_project_id ON decisions (project_id);
CREATE INDEX idx_changes_project_id ON changes (project_id);
CREATE INDEX idx_lessons_project_id ON lessons (project_id);
CREATE INDEX idx_guidelines_project_id ON guidelines (project_id);
CREATE INDEX idx_knowledge_project_id ON knowledge (project_id);
CREATE INDEX idx_ac_templates_project_id ON ac_templates (project_id);
CREATE INDEX idx_gates_project_id ON gates (project_id);

CREATE INDEX idx_key_results_objective_id ON key_results (objective_id);
CREATE INDEX idx_knowledge_versions_knowledge_id ON knowledge_versions (knowledge_id);

-- Junction table indexes (beyond PKs)
CREATE INDEX idx_knowledge_links_entity ON knowledge_links (entity_type, entity_id);
CREATE INDEX idx_knowledge_links_knowledge_id ON knowledge_links (knowledge_id);
CREATE INDEX idx_task_ac_task_id ON task_ac (task_id);
CREATE INDEX idx_task_ac_template_id ON task_ac (ac_template_id);
CREATE INDEX idx_idea_relations_target ON idea_relations (target_id);
CREATE INDEX idx_decision_alternatives_decision ON decision_alternatives (decision_id);

-- Timestamp indexes for sorting / range queries
CREATE INDEX idx_tasks_started_at ON tasks (started_at) WHERE started_at IS NOT NULL;
CREATE INDEX idx_tasks_completed_at ON tasks (completed_at) WHERE completed_at IS NOT NULL;
CREATE INDEX idx_changes_recorded_at ON changes (recorded_at);

-- Agent index for multi-agent queries
CREATE INDEX idx_tasks_agent ON tasks (agent) WHERE agent IS NOT NULL;

-- Confidence & severity for decision/risk filtering
CREATE INDEX idx_decisions_confidence ON decisions (confidence);
CREATE INDEX idx_decisions_severity ON decisions (severity) WHERE severity IS NOT NULL;

-- Text FK columns used as filters (T-NNN, C-NNN references)
CREATE INDEX idx_changes_task_id ON changes (task_id);
CREATE INDEX idx_decisions_task_id ON decisions (task_id);
CREATE INDEX idx_lessons_task_id ON lessons (task_id) WHERE task_id IS NOT NULL;

-- Ideas priority for sorting
CREATE INDEX idx_ideas_priority ON ideas (priority);

COMMIT;

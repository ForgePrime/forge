# Domain Module: Data

## Triggers

Activated when entity scopes include: `database`, `data`, `schema`, `migration`, `storage`, `etl`

## Prerequisites

Before running any phase, **read the codebase** and list what you found:
- Database type, ORM/data access, migration tool
- Existing schema: tables, relationships, indexes, constraints
- Naming conventions: snake_case/camelCase, singular/plural tables
- Seed/fixture data patterns

**You MUST list files read and patterns found before proceeding.**
If you cannot list them, you have not read the codebase.

---

## Phase 1: Vision Extraction

**Used during**: objective definition, idea capture, initial alignment

### Input

- `user_goal` — what the user said they want
- `existing_tables` — tables found in codebase (from prerequisites)

### Questions to Ask

Pick 2-4 from below based on what you cannot answer from code:

**Entity Shape** (when goal involves new data):
- "What data does [entity] hold? List the fields — I'll figure out types from context."
- "I see [related entity] has fields [X, Y, Z]. Does new entity relate? How — one-to-many? Many-to-many?"

**Lifecycle & Mutability**:
- "Once created, which fields can change? Which are immutable?"
- "Ever deleted? Soft-deleted? Kept forever? Need audit trail?"

**Volume & Access Patterns** (when it affects design):
- "How many — tens, thousands, millions? Affects indexing."
- "Main query pattern — list by user? Lookup by ID? Search? Filter by status?"

**Relationships** (ask proactively):
- "When [parent] deleted — cascade? Orphan? Block deletion?"

**Never ask**: "Should we normalize?", "What about indexes?", "UUID or integer IDs?"

### Output

Produce and store in **Research (R-NNN)**:

- **entity_schema** — each entity with fields, types, constraints
  Example: `WorkflowExecution: id (uuid PK), workflow_id (uuid FK), status (enum), steps_snapshot (jsonb NOT NULL), created_at`

- **relationships** — how entities relate, with on_delete behavior
  Example: `workflow_executions → workflows: many-to-one, FK workflow_id, CASCADE`

- **access_patterns** — how data will be queried, frequency, indexes needed
  Example: "List executions for workflow: WHERE workflow_id = ? ORDER BY created_at DESC → index on workflow_id"

- **data_rules** — business rules about integrity
  Example: "Only one RUNNING execution per workflow → partial unique index"

- **open_questions** — unresolved, passed to Phase 2

---

## Phase 2: Research

**Used during**: discovery, exploration, feasibility assessment

### Input

- `entity_schema`, `relationships` — from Phase 1
- If missing: warn and ask user. Do NOT invent schemas.

### What to Research

1. **Existing schema patterns**: How tables defined (ORM, raw SQL, migrations)? Naming?
   "Models in `models/workflow.py` using SQLAlchemy, migrations via Alembic."

2. **Migration strategy**: Tool, numbering, existing data considerations.
   "Next migration: 003. Convention: `003_add_workflow_executions.py`."

3. **Constraint analysis**: For each data_rule, DB constraint vs app check vs both.
   "Partial unique index: `CREATE UNIQUE INDEX ... WHERE status = 'RUNNING'`"

4. **Impact on existing queries**: Will changes affect performance? Need modifications?

### Output

Store in **Research (R-NNN updated) + Knowledge (K-NNN)**:

- **migration_plan** — ordered schema changes with files, operations, reversibility
- **model_mapping** — ORM files to create/modify with pattern sources
- **constraint_implementation** — how each data rule is enforced (DB, app, both)
- **affected_queries** — existing queries needing updates
- **resolved_questions**

---

## Phase 3: Planning

**Used during**: task decomposition, plan creation

### Input

- `entity_schema`, `migration_plan`, `model_mapping` — from previous phases

### Decomposition Strategy

Use **layer-centric decomposition** (schema → model → repository):

Good: `Create execution migration` / `Create WorkflowExecution model` / `Create ExecutionRepository` / `Add relationship to Workflow model`
Bad: `Add execution tables and models` / `Add data access`

### Task Rules

**instruction** must reference: exact migration file, exact columns/types/constraints, pattern source.

**acceptance_criteria** — use `Given {initial state} When {operation} Then {data invariant holds}` format:
- "Given empty DB, When migration runs, Then `workflow_executions` exists with columns: id (uuid PK), workflow_id (uuid FK NOT NULL), status (enum)"
- "Given execution RUNNING, When second execution created for same workflow, Then unique index violation"
- "Given migration applied, When downgrade runs, Then table dropped cleanly"

**exclusions**:
- "Do NOT modify workflows table — relationship added in T-004"
- "Do NOT create repository — that's T-003"
- "Do NOT add seed data"

### Output

Store in **Task fields**: instruction, acceptance_criteria, exclusions, alignment.

---

## Phase 4: Execution

**Used during**: task implementation, verification

### Checklist

Before: Read existing migrations (pattern, revision chain), read existing models.
During: Column types EXACTLY per schema, every constraint in migration, every index created, reversible.
After: Does migration run on empty DB? On current DB? Does downgrade work?

### Micro-review (max 5 lines)

```
T-001 done: Created migration 003_add_workflow_executions.
- Tables: workflow_executions (8 cols), execution_steps (6 cols)
- Constraints: FK to workflows, FK to users, partial unique for RUNNING
- Reversible: yes
- Excluded: ORM models, repository, seed data
Is this what you wanted?
```

---

## Cross-module Interface

### Provides to other modules

| To | Data | Purpose |
|----|------|---------|
| Backend | `entity_schema` → table structure | Backend knows data layer shape |
| Backend | `migration_plan` → availability order | Backend knows when tables exist |
| Process | `entity_schema` → state storage | Process knows how states are persisted |
| UX | `entity_schema` → field names/types | UX knows what to show in forms/tables |

### Needs from other modules

| From | Data | Purpose |
|------|------|---------|
| Backend | `api_contracts` → data needs | Data knows what schema must support |
| Process | `state_diagram` → state values | Data knows enum values to define |
| UX | `user_flows` → query patterns | Data knows what indexes are needed |

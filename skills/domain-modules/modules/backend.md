# Domain Module: Backend

## Triggers

Activated when entity scopes include: `backend`, `api`, `server`, `services`

## Prerequisites

Before running any phase, **read the codebase** and list what you found:
- API structure: routing pattern, controller/service/repository layers
- Existing endpoints: naming convention, response format, error handling
- Auth/middleware stack, data access patterns (ORM, raw SQL)
- Config: secrets, DB connections, feature flags

**You MUST list files read and patterns found before proceeding.**
If you cannot list them, you have not read the codebase.

---

## Phase 1: Vision Extraction

**Used during**: objective definition, idea capture, initial alignment

### Input

- `user_goal` — what the user said they want
- `existing_endpoints` — endpoints found in codebase (from prerequisites)

### Questions to Ask

Pick 2-4 from below based on what you cannot answer from code:

**API Shape** (when goal involves new/modified endpoints):
- "I see endpoints follow `[METHOD] /api/v1/{resource}`. New endpoint — what data in, what data out? Give me input/output example."
- "New resource (`/executions`) or action on existing (`POST /workflows/{id}/execute`)?"

**Behavior & Rules** (always ask for business logic):
- "What are the rules? When should [action] be allowed and when rejected?"
- "Concurrent/duplicate requests — fail, queue, or idempotent?"

**Error Scenarios** (ask proactively):
- "If [dependency] unavailable — fail fast, retry, or degrade?"
- "Error response format? I see existing errors return `{error: string, code: string}`. Same?"

**Integration** (when touching other systems):
- "Triggers downstream — notifications, webhooks, queue messages, cache invalidation?"
- "Transactional with [other operation]? Or eventual consistency?"

**Never ask**: "What about security?", "Should we add logging?", "What about performance?"

### Output

Produce and store in **Research (R-NNN)**:

- **api_contracts** — each endpoint with method, path, input, output, errors
  Example: `POST /api/v1/workflows/{id}/execute → 201 {execution_id, status} | 404 | 409 | 422`

- **business_rules** — when operations allowed/rejected, with violation response
  Example: "Cannot execute RUNNING workflow → 409"

- **error_scenarios** — how each error is handled (fail, retry, degrade)

- **integration_points** — downstream effects

- **open_questions** — unresolved, passed to Phase 2

---

## Phase 2: Research

**Used during**: discovery, exploration, feasibility assessment

### Input

- `api_contracts`, `business_rules` — from Phase 1
- If missing: warn and ask user. Do NOT invent API contracts.

### What to Research

1. **Existing code patterns**: Find similar endpoints, document router → service → repository chain.
   "Found `POST /publish` in `routers/workflows.py` → `services/workflow_service.py:publish()`. New endpoint follows same pattern."

2. **Data model analysis**: Tables involved, what needs to change, FKs/indexes/constraints.

3. **Concurrency**: For each business rule, how to enforce safely (locking, optimistic concurrency).
   "Rule 'cannot execute if RUNNING' needs SELECT FOR UPDATE to prevent race condition."

4. **Dependency analysis**: What existing code is affected, what tests cover it.

### Output

Store in **Research (R-NNN updated) + Knowledge (K-NNN)** for durable artifacts:

- **implementation_mapping** — exact files per layer with pattern sources
- **concurrency_strategy** — per operation
- **affected_code** — existing files that will be impacted
- **resolved_questions** — answers to Phase 1 open questions

---

## Phase 3: Planning

**Used during**: task decomposition, plan creation

### Input

- `implementation_mapping`, `api_contracts`, `business_rules` — from previous phases

### Decomposition Strategy

Use **layer-centric decomposition**:

Good: `Create execution migration` / `Create ExecutionRepository` / `Create ExecutionService` / `Add POST /execute endpoint`
Bad: `Implement workflow execution backend` / `Add error handling`

### Task Rules

**instruction** must reference: exact file, exact layer, exact pattern source, data contract (in/out).

**acceptance_criteria** — use `Given {auth + state} When {HTTP method + endpoint} Then {status code + response}` format:
- "Given valid workflow, When POST /execute, Then 201 {execution_id, status: PENDING}"
- "Given workflow with 0 steps, When POST /execute, Then 422 {error: 'no steps'}"
- "Given RUNNING workflow, When POST /execute, Then 409 {error: 'already running'}"

**exclusions** — layer boundaries, feature boundaries:
- "This task creates service layer ONLY — do NOT modify router"
- "Do NOT implement step execution — only create execution record"

### Output

Store in **Task fields**: instruction, acceptance_criteria, exclusions, alignment.

---

## Phase 4: Execution

**Used during**: task implementation, verification

### Checklist

Before: Read pattern source, read related layers, check existing tests.
During: Follow layer separation, implement EVERY business rule from AC, return EXACT error codes.
After: Trace request → router → service → repo → response. Does it match AC?

### Micro-review (max 5 lines)

```
T-004 done: Added POST /api/v1/workflows/{id}/execute.
- Validates: exists (404), has steps (422), not running (409)
- Creates: execution record with step snapshot, status PENDING
- Returns: 201 {execution_id, status}
- Excluded: step execution logic, WebSocket events
Is this what you wanted?
```

---

## Cross-module Interface

### Provides to other modules

| To | Data | Purpose |
|----|------|---------|
| UX | `api_contracts` → response shapes | UX knows what data to display |
| UX | `error_scenarios` → distinct error codes | UX knows error messages per code |
| Process | `business_rules` → rule enforcement | Process knows which transitions backend rejects |
| Data | `api_contracts` → data needs | Data knows what schema must support |

### Needs from other modules

| From | Data | Purpose |
|------|------|---------|
| UX | `user_flows` → required API calls | Backend knows what endpoints to build |
| Process | `state_transitions` → valid transitions | Backend knows business rules to enforce |
| Data | `entity_schema` → table structure | Backend knows data layer shape |
| Data | `migration_sequence` → availability order | Backend knows when tables exist |

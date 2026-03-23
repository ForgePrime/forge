---
name: plan
id: SKILL-PLAN
version: "1.0"
description: "Decompose a high-level goal into a tracked, dependency-aware task graph."
---

# Plan

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-PLAN |
| Version | 1.0 |
| Description | Assess complexity, decompose goal into tasks, create pipeline with dependencies. |

## Read Commands

| ID | Command | Returns | When |
|----|---------|---------|------|
| R1 | `python -m core.pipeline status {project}` | Current pipeline state (if project exists) | Step 1 — check existing state |
| R2 | `python -m core.lessons read-all` | Lessons from past projects | Step 2 — learn from history |
| R3 | `python -m core.guidelines read {project} --weight must` | Must-follow project guidelines | Step 2 — inform decomposition |
| R5 | `python -m core.changes contract` | Contract for recording changes | Reference only |
| R6 | `skills/deep-align/SKILL.md` | Alignment procedure | Step 3 — before decomposition |
| R7 | `python -m core.research context {project} --entity {id}` | Research linked to entity | Step 2 — load research context |
| R8 | `python -m core.objectives show {project} {objective_id}` | Objective details + KRs | Step 2 — if planning from objective |
| R9 | `python -m core.knowledge read {project}` | Available knowledge objects | Step 2 — for task knowledge assignment |
| R10 | `python -m core.guidelines scopes {project}` | Available guideline scopes | Step 2 — for task scope assignment |
| R11 | `python -m core.knowledge read {project} --category requirement` | Extracted requirements from source docs | Step 1.5 — requirements baseline |
| R11 | `python -m core.decisions read {project} --type risk` | Active risk decisions | Step 6 — inform task structure and AC |
| R12 | `python -m core.domain_modules for-scopes --scopes "{s}" --phase planning` | Domain decomposition rules | Step 4.5 — if Standard/Complex |

## Write Commands

| ID | Command | Effect | When | Contract |
|----|---------|--------|------|----------|
| W1 | `python -m core.pipeline init {project} --goal "..."` | Creates tracker.json | Step 3 — create project |
| W2 | `python -m core.pipeline draft-plan {project} --data '{json}' [--idea I-NNN] [--objective O-NNN]` | Stores draft plan for review | Step 5 — after decomposition |
| W2b | `python -m core.pipeline approve-plan {project}` | Materializes draft into pipeline | Step 7 — after user approval |
| W2c | `python -m core.pipeline add-tasks {project} --data '{json}'` | Direct task addition (alternative to draft) | Step 5 — when bypassing draft review |
| W3 | `python -m core.decisions add {project} --data '{json}'` | Records planning decisions | Step 4 — for architectural choices | `python -m core.decisions contract add` |
| W4 | `python -m core.knowledge add {project} --data '[...]'` | Stores Impact Map as knowledge object | Step 6.5 — after decomposition, before draft |

## Output

| File | Contains |
|------|----------|
| `forge_output/{project}/tracker.json` | Pipeline with task graph |
| `forge_output/{project}/decisions.json` | Planning decisions (if any) |

## Success Criteria

- Project created with clear goal statement
- Tasks are concrete, focused units of work (not vague)
- Every task has a meaningful description and instruction
- Dependencies form a valid DAG (no cycles, validated by pipeline)
- No task has more than 3 dependencies (symptom of poor decomposition)
- User has reviewed and approved the plan before execution
- Must-guidelines respected in task design (no task violates a must-guideline without a recorded decision)

## References

- `docs/DESIGN.md` — Architecture overview
- `docs/STANDARDS.md` — Skill standards

---

## Overview

Decompose a user's high-level goal into a tracked task graph.

**The only test**: take task `_1`. Paste its `instruction` into a blank context
with no other information. Does the agent know which file to open first?
If not — the plan is not done.

Every step below serves this test. If an instruction can't pass cold start,
no amount of dependency graphs or acceptance criteria will save the plan.

## Prerequisites

- User has stated a goal
- Working directory is a codebase (or will become one)
- **If source documents were ingested** (K-NNN with category=source-document exist):
  - Objectives MUST exist (run `/analyze` first if they don't)
  - `draft-plan` will BLOCK without `--objective O-NNN` when objectives exist
  - Pipeline: `/ingest` → `/analyze` (creates objectives) → `/plan` (links to objective)
- **If no source documents**: standalone plan is allowed without objectives (warning only)

---

### Step 0 — Read and tag the input

**Do this before any decomposition. Do not skip.**

Read every piece of input (goal description, requirements, codebase context,
constraints). Tag every statement:

| Tag | Meaning | Goes to |
|-----|---------|---------|
| `[REQ]` | Something the system must do | task instruction + AC |
| `[CONSTRAINT]` | Hard limit — tech, compliance, must-guideline | task instruction |
| `[DECISION]` | Architecture/tech choice already made | task instruction (follow, don't revisit) |
| `[SCOPE-OUT]` | Explicitly excluded | Out of scope only — never into tasks |
| `[IMPLICIT]` | Assumed but not stated | write explicitly before planning |
| `[CONFLICT]` | Two statements contradict each other | **hard stop** — ask before planning |
| `[VAGUE]` | Too ambiguous to act on as written | **hard stop** — clarify or make explicit assumption |

**Output of Step 0** (write this before proceeding):

```
Tagged input:
[REQ] user can create an order with products and delivery address
[REQ] confirmation email sent after order saved
[CONSTRAINT] follow existing Express + TypeScript patterns in src/api/
[DECISION] use BullMQ for async jobs (established in codebase)
[IMPLICIT] order status = 'pending' on creation — if wrong: model changes
[VAGUE] "products" → resolved: [{product_id: UUID, quantity: int}], no price in scope
```

**Rules:**
- Every `[VAGUE]` must become an explicit assumption before continuing. Write:
  "I assume X because Y. If wrong, Z changes."
- Every `[CONFLICT]` is a hard stop. Do not plan until resolved.
- Every `[IMPLICIT]` must be written down with consequence if wrong.
- Items tagged `[SCOPE-OUT]` go ONLY into the Out of Scope block. If any task
  implements a `[SCOPE-OUT]` item, the plan has a scope leak — fix it.
- Every `[IMPLICIT]` assumption must be reconciled with must-guidelines from Step 2.
  If an assumption contradicts a must-guideline, re-tag as `[CONFLICT]` and resolve.

---

### Step 1 — Assess Current State

Check if a project already exists:
```bash
ls forge_output/ 2>/dev/null
```

If a project exists for the same goal, resume instead of creating new.

Read the existing codebase to understand what exists:
- Directory structure
- Key configuration files (package.json, requirements.txt, etc.)
- Existing architecture patterns

---

### Step 1.5 — Load Source Requirements

If source documents have been ingested, load extracted requirements:

```bash
python -m core.knowledge read {project} --category requirement
python -m core.knowledge read {project} --category domain-rules
python -m core.knowledge read {project} --category source-document
```

If `source-document` objects exist but few `requirement` objects:
- WARNING: Documents registered but not fully ingested. Run the ingest skill first (`skills/ingest/SKILL.md`).

These requirements are the baseline for coverage checking. Every requirement K-NNN must be:
- **Referenced** by at least one task's `source_requirements`
- **Or explicitly** marked DEFERRED/OUT_OF_SCOPE in the coverage check

When decomposing tasks (Step 4+), add `source_requirements` to each task:
```json
{
  "source_requirements": [
    {"knowledge_id": "K-003", "text": "System must support 500 users", "source_ref": "spec.md:section-3"}
  ]
}
```

---

### Step 2 — Learn from History & Check Guidelines

Check lessons from past projects for relevant patterns:
```bash
python -m core.lessons read-all --severity critical --limit 15
```

Check project guidelines (if project exists or will be created from existing one):
```bash
python -m core.guidelines read {project} --weight must
```

Note any lessons and `must` guidelines that apply to the current goal. Guidelines inform decomposition — e.g., if a guideline says "every endpoint needs rate limiting", that affects task structure.

When decomposing (Step 6), assign `scopes` to each task based on which guidelines apply.

Load available scopes and knowledge so you can assign them to tasks (R9, R10):
```bash
python -m core.guidelines scopes {project}
python -m core.knowledge read {project}
```
This gives you the full list of available scopes (e.g., `backend`, `frontend`, `database`) and knowledge objects (K-NNN). Use these when assigning `scopes` and `knowledge_ids` to tasks in Step 6. **Do not assign scopes that don't exist in guidelines** — backend tasks get backend scopes, frontend tasks get frontend scopes.

If planning from an idea (`/plan I-001`), load the idea's scopes, knowledge, and research:
```bash
python -m core.ideas show {project} {idea_id}
python -m core.guidelines context {project} --scopes "{idea_scopes}"
python -m core.research context {project} --entity {idea_id}
```
The idea's `scopes` and `knowledge_ids` are the baseline — propagate them to tasks that implement this idea. Tasks may have narrower scopes (e.g., idea has `["backend", "frontend"]` but a task only touches backend).

If planning from an objective (`/plan O-001`), load the objective context, knowledge, and research:
```bash
python -m core.objectives show {project} {objective_id}
python -m core.research context {project} --entity {objective_id}
```
The objective's `scopes` and `knowledge_ids` are the baseline for all tasks. Propagate relevant knowledge to tasks — if K-001 is about API patterns and K-002 about database schema, backend tasks get K-001, database tasks get K-002.

**Scope resolution for objectives**: Build the full scope set by combining:
1. `objective.scopes` — the objective's own scopes
2. Scopes from `derived_guidelines` — load each guideline ID from `objective.derived_guidelines`, extract its `scope`, add to the set

```bash
python -m core.guidelines read {project}
```
Find guidelines whose IDs are in `objective.derived_guidelines`. Collect their scopes. Merge with `objective.scopes`. Then load:
```bash
python -m core.guidelines context {project} --scopes "{merged_scopes}"
```

**IMPORTANT**: If a derived guideline has a scope NOT in the objective's scopes, warn the user:
```
WARNING: Derived guideline G-015 (scope: "latency") has scope not in objective O-001 scopes.
Consider adding "latency" to objective scopes: python -m core.objectives update {project} --data '[{"id": "O-001", "scopes": ["backend", "performance", "latency"]}]'
```

Also check for approved ideas advancing this objective:
```bash
python -m core.ideas read {project} --status APPROVED
```
Filter to ideas with `advances_key_results` referencing this objective's KRs. If found, their research and exploration notes provide additional context for decomposition. Inherit their `knowledge_ids` where relevant.

**Must-guidelines are non-negotiable during decomposition:**
- If a must-guideline says "all endpoints need rate limiting" → include a rate limiting task or subtask
- If a must-guideline says "use PostgreSQL" → do NOT plan tasks with MongoDB
- Record a decision if a must-guideline conflicts with the goal (don't silently ignore)

---

### Step 2.5 — Research Readiness Gate

Before planning, verify that all related research/explorations are ready:

```bash
python -m core.decisions read {project} --type exploration
```

**Gate rule**: If ANY exploration decision linked to this entity (via `task_id` matching the idea/objective ID) has `ready_for_tracker: false` and status is OPEN, **BLOCK** planning:

```
BLOCKED: Cannot plan — {N} exploration(s) not ready for tracker.
  - D-{NNN}: {issue} (ready_for_tracker: false)

Resolve before planning:
  - Complete exploration: `/discover {entity_id}`
  - Or mark ready: `python -m core.decisions update {project} --data '[{"id": "D-NNN", "ready_for_tracker": true}]'`
```

Also warn (but don't block) on HIGH-severity OPEN risks without mitigation:

```
WARNING: {N} HIGH-severity risk(s) without mitigation plan.
  - D-{NNN}: {issue}

Consider addressing these before planning, or acknowledge them as accepted risks.
```

The gate BLOCKS on unready explorations but only WARNS on unmitigated HIGH risks.

---

### Step 3 — Align on Goal

**If planning from idea/objective** (`/plan I-001` or `/plan O-001`): alignment already exists
from /objective or /discover. Read it — don't re-do it:
```bash
python -m core.ideas show {project} {idea_id}       # has description, scopes, discovery context
python -m core.objectives show {project} {obj_id}   # has KRs, description, scopes
```
Ask only about implementation gaps (quality level, priorities between KRs, verification approach).

**If planning directly** (`/plan {goal text}`): this IS the entry point — do full alignment:
- **Restate** the goal: "You want X so that Y." Get confirmation.
- **Ask 2-4 scoping questions**: scope, constraints, quality, boundaries, verification.

**If user says "just plan it"** — proceed but flag top 2 assumptions.

**Capture alignment contract** for all tasks:
```json
{
  "goal": "single sentence goal",
  "boundaries": {"must": [...], "must_not": [...], "not_in_scope": [...]},
  "success": "how user judges if done — what to test/observe"
}
```
Stored on each task as `alignment` field. Narrowing `success` per task is encouraged.

**Persist as Vision** — so context survives to task 5 of 8:
```bash
python -m core.knowledge add {project} --data - <<'EOF'
[{"title": "Vision: {goal}", "category": "business-context", "scopes": ["{scopes}"], "content": "{goal, boundaries, success criteria}"}]
EOF
```

---

### Step 4 — Assess Complexity

Before decomposing, classify the goal into one of three tracks:

| Track | Criteria | Task count | Example |
|-------|----------|------------|---------|
| **Quick** | Single concern, < 3 files, no architectural decisions | 1-3 tasks | "Fix login bug", "Add field to form" |
| **Standard** | Multiple concerns, clear scope, known patterns | 3-7 tasks | "Add JWT auth", "Create CRUD endpoint" |
| **Complex** | Cross-cutting concerns, architectural decisions needed, unknown territory | 5-12 tasks | "Migrate database", "Add real-time features" |

Present the assessment to the user:
```
Complexity assessment: [Quick/Standard/Complex]
Reasoning: ...
Estimated tasks: N
```

Ask user to confirm before proceeding.

---

### Step 4.5 — Load Domain Guidance (Standard/Complex only)

If the plan involves specific technical domains (not Quick track), load domain-specific
decomposition rules before generating tasks:

```bash
python -m core.domain_modules for-scopes --scopes "{scopes}" --phase planning
```

Apply the domain module's decomposition strategy, AC format, and exclusion patterns
when generating tasks in Step 6. If no scopes are known yet, determine them from the
goal description (see scope discovery in `skills/domain-modules/SKILL.md`).

Skip for Quick track or when no scopes match any domain module.

---

### Step 5 — Create Project

Generate a project slug from the goal (lowercase, hyphens, max 40 chars):
```bash
python -m core.pipeline init {slug} --goal "{full goal text}" --project-dir "{absolute_path_to_workspace}"
```

`--project-dir` is REQUIRED — it tells Forge where the code lives. All commands (gates, AC tests, KR measurements) run in this directory.

If you make any architectural decisions during planning (e.g., choosing a framework,
deciding on a pattern), record them:

```bash
python -m core.decisions add {project} --data '[...]'
```

Use `task_id: "PLANNING"` for decisions made before tasks exist.

---

### Step 6 — Decompose

If decomposition approach isn't obvious, consult `references/splitting-patterns.md` for 9 named strategies (workflow steps, CRUD, business rules, etc.). Choose the strategy that matches the goal's shape. **Never split by technical layer** (frontend/backend/tests) — always by vertical slices delivering end-to-end value.

Apply these decomposition rules:

1. **Each task = one focused change**: A task should modify one logical component
2. **Setup before implementation**: Infrastructure/config tasks first
3. **Implementation before testing**: Create code before tests
4. **Independent where possible**: Minimize dependencies to allow parallel work
5. **Testable**: After each task, something verifiable should exist

For Standard/Complex tracks, use this template:
```
Phase 1 — Foundation:  Setup, config, infrastructure
Phase 2 — Core:        Main implementation tasks
Phase 3 — Integration: Connect components, add middleware
Phase 4 — Quality:     Tests, validation, documentation
```

For each task, specify:
- `id`: Use temporary IDs: `_1`, `_2`, `_3`, etc. These are auto-remapped to real `T-NNN` IDs when the plan is approved (`approve-plan`) or tasks are added (`add-tasks`). This prevents ID collisions between concurrent planning processes. Use temp IDs in `depends_on` and `conflicts_with` too — they will be remapped together.
- `name`: kebab-case, descriptive (e.g., "setup-database-schema")
- `description`: WHAT needs to be done (concrete, not vague). Include boundary when scope edge is ambiguous: "This task IS {X}. This task is NOT {Y}."
- `instruction`: HOW to do it. Must pass the cold start test (paste into blank context — agent knows which file to open first). Every instruction must contain all five:
  1. **Exact files to create** — full paths (e.g., "Create `src/api/routes/orders.ts`")
  2. **Exact files to modify** — full paths (e.g., "Register route in `src/api/routes/index.ts`")
  3. **Exact files NOT to touch** — name what a sibling task owns (e.g., "Do NOT modify `src/api/routes/auth.ts` — owned by _3")
  4. **Pattern to follow** — name the existing file to use as a model, or write "no existing pattern — create from scratch" (e.g., "Follow pattern in `src/api/routes/invoices.ts`")
  5. **Reference to dependency output** — if `depends_on` is non-empty, name what you're using from the dependency (e.g., "using OrderModel from `src/models/Order.ts` (_1)")

  | Bad | Good |
  |-----|------|
  | "Implement order creation" | "1. Create `src/api/routes/orders.ts` following `src/api/routes/invoices.ts`. 2. Add POST handler: validate with `OrderCreateSchema`, call `OrderModel.create()` from _1, return 201. 3. Register in `src/api/routes/index.ts`. Do NOT modify `src/api/routes/auth.ts`." |
  | "Add email job" | "1. Create `src/jobs/order-confirmation.ts` using BullMQ pattern from `src/jobs/invoice-reminder.ts`. 2. Job receives `{order_id, email}`. 3. In `src/api/routes/orders.ts` (_2): after create, enqueue job." |
- `depends_on`: list of prerequisite task IDs (use temp IDs `_1`, `_2` for tasks in the same batch, or real `T-NNN` IDs for existing tasks)
- `uses_from_dependencies`: dict mapping each dependency ID to exactly what this task takes from it. **Mandatory when `depends_on` is non-empty.** Format:
  ```json
  "uses_from_dependencies": {
    "_1": "OrderModel from src/models/Order.ts — call OrderModel.create(data) returning Promise<Order>",
    "_3": "confirmationQueue from src/jobs/order-confirmation.ts — call .add({order_id, email})"
  }
  ```
  **Rule**: `depends_on` non-empty + `uses_from_dependencies` empty = the dependency is decorative. Either fill it (name what this task consumes from the dependency's `produces`) or remove the dependency. The referenced artifact must also appear by name in `instruction`.
- `parallel`: true if this task can run alongside siblings
- `conflicts_with`: list of task IDs modifying same files (supports temp IDs within the same batch)
- `scopes`: list of guideline scopes this task relates to (e.g., `["backend", "database"]`). **Only use scopes that exist in the project** (loaded via R10 in Step 2). Inherit from idea/objective scopes but narrow per task — a backend-only task should NOT get frontend scopes. `general` is always included automatically during execution.
- `source_requirements`: list of `{knowledge_id: "K-NNN", text: "requirement text", source_ref: "file:section"}`. **REQUIRED for feature/bug tasks when requirements exist.** Links this task to specific extracted requirements. Every requirement K-NNN must be referenced by at least one task. Auto-coverage gate checks this.
- `knowledge_ids`: list of Knowledge IDs (K-001, etc.) that provide context for this task. **Only assign knowledge relevant to the task** — if K-001 is about API patterns and the task is pure CSS, don't assign K-001. Inherit from source idea/objective but distribute selectively. Loaded by `pipeline context` for LLM assembly.
- `test_requirements`: dict with boolean keys `unit`, `integration`, `e2e` indicating which test types this task needs.
- `alignment`: the alignment contract from Step 3 (dict with `goal`, `boundaries`, `success`). All tasks share the same plan-level alignment. Required for feature/bug tasks planned via `/plan`. Narrowing `success` per task is encouraged when tasks cover different aspects of the goal.
- `produces`: dict describing what this task creates for downstream consumers. Use when other tasks depend on this task's output. Keys are semantic labels, values describe the contract:
  - `endpoint`: "POST /api/users → 201 {id, email}" (API shape for consuming tasks)
  - `model`: "User(id, email, hashed_password)" (data model for dependent tasks)
  - `migration`: "users table with columns: id, email, hashed_password, created_at" (schema for model tasks)
  - `component`: "UserForm component accepting onSubmit(data) prop" (interface for integration tasks)
  - `errors`: "409 duplicate email, 422 validation, 401 unauthorized" (error contract)
  Downstream tasks see this contract in `pipeline context` and should verify their implementation matches it.
- `exclusions`: list of task-specific DO NOT rules. Generate from:
  1. **Cross-task boundaries**: If T-005 does backend and T-008 does frontend, T-005 gets `"DO NOT modify frontend components or pages"`, T-008 gets `"DO NOT modify API routes or backend logic"`
  2. **File-level exclusions**: Name specific files this task must NOT touch that a sibling task owns (e.g., `"DO NOT modify WorkflowList.tsx — that is T-012"`)
  3. **Scope creep prevention**: Exclude work that belongs to a later task (e.g., `"DO NOT add error handling — that is T-015"`, `"DO NOT implement pagination — out of scope"`)
  4. **Pattern violations**: Exclude anti-patterns for this codebase (e.g., `"DO NOT use inline styles — project uses CSS modules"`)

  For chore/investigation tasks, exclusions are optional but recommended.
- `acceptance_criteria`: **STRUCTURED format required for feature/bug tasks.** Each AC must be a dict:
  ```json
  {"text": "endpoint returns 200 with user object", "verification": "test", "test_path": "tests/test_users.py"}
  {"text": "response time < 200ms", "verification": "command", "command": "python scripts/measure_latency.py"}
  {"text": "UI matches wireframe", "verification": "manual", "check": "Compare against docs/wireframes/login.png"}
  ```

  `verification` field is REQUIRED: `"test"` (pytest path), `"command"` (shell command), or `"manual"` (with `check` description).
  `kr_link` optional: `"O-001/KR-1"` — links AC result to KR for automatic measurement.

  Generate AC from these sources (2-5 per task):
  1. **Source requirements** — from `source_requirements` on the task. Each requirement should have at least one AC.
  2. **Alignment success criteria** — from Step 3. The `success` field defines what the user will test/observe.
  3. **Task output** — what artifact exists after? (file created, endpoint responding, test passing)
  4. **Integration point** — how does this connect to the next task? (data format, API contract)

  **Anti-patterns** (these are REJECTED by `approve-plan`):
  | Rejected | Accepted |
  |----------|----------|
  | `"Error handling works"` (plain string) | `{"text": "Returns 400 with {error} for invalid input", "verification": "test", "test_path": "tests/test_errors.py"}` |
  | `{"text": "API secured"}` (no verification) | `{"text": "401 for missing auth header", "verification": "test", "test_path": "tests/test_auth.py"}` |
  | `{"text": "Tests pass", "verification": "manual"}` | `{"text": "All auth tests pass", "verification": "test", "test_path": "tests/test_auth.py"}` |

  Skip AC for `investigation` and `chore` tasks — use `--force` on completion.

  **AC should be functional, not metric-based:**
  - Describe what the feature DOES from the user's perspective, not implementation metrics
  - Good: "Jest przycisk 'Uruchom' na górze strony obok 'Edytuj'" / "Kliknięcie otwiera modal z listą kroków"
  - Bad: "Component renders in under 100ms" / "Function has O(n) complexity"
  - Exception: performance/infrastructure tasks where metrics ARE the deliverable

**Cross-task exclusion derivation:**

After defining all tasks, do a second pass to derive cross-task exclusions:
1. Group tasks by the files/directories they modify
2. For each group of tasks touching related areas, add exclusions that prevent overlap:
   - If tasks are in the same domain (e.g., both backend), exclude specific files
   - If tasks are in different domains (e.g., backend vs frontend), exclude the other domain entirely
3. For sequential tasks (A depends on B), ensure B does not redo or undo A's work:
   - B gets `"DO NOT revert changes from {A.id}"`
   - If A creates an interface, B gets `"DO NOT modify the interface created by {A.id} — extend it instead"`

**Risk-informed decomposition:**

Load active risk decisions that may affect task design (R11):
```bash
python -m core.decisions read {project} --type risk
```

For each OPEN or MITIGATED risk:
- If the risk has a `mitigation_plan`, consider whether a task should implement that mitigation
- If the risk affects specific components, ensure tasks touching those components have appropriate acceptance criteria that address the risk
- HIGH-severity risks should result in explicit AC on relevant tasks (e.g., "Rate limiting handles 1000 req/s without degradation")

If planning from an idea or objective, also check risks linked to that entity:
```bash
python -m core.decisions read {project} --entity {idea_or_objective_id}
```

Store as draft plan for review (W2):
```bash
# If planning from an idea:
python -m core.pipeline draft-plan {project} --data '[...]' --idea {idea_id}

# If planning from an objective:
python -m core.pipeline draft-plan {project} --data '[...]' --objective {objective_id}
```

When planning from an objective, each task's `origin` is set to the objective ID (e.g., `O-001`).
If there are APPROVED ideas advancing this objective, consider using them as intermediate origins for specific tasks.

---

### Step 6a — Readiness Check (mandatory)

Before committing to this plan, honestly assess what you KNOW vs what you ASSUME.

**Produce this table:**

```
## Readiness Check

| # | I ASSUME that... | BECAUSE... | If wrong, impact is... |
|---|------------------|------------|------------------------|
| 1 | [assumption about code/system/behavior] | [evidence: file read, grep result, or just "seems likely"] | HIGH/MED/LOW |
```

**Severity:**
- **HIGH**: wrong assumption would change the architecture, data model, or task structure
- **MED**: wrong assumption would change one component's implementation
- **LOW**: wrong assumption would change an implementation detail only

**Rules:**
- 0-2 HIGH: proceed to Impact Map
- 3-4 HIGH: proceed but add to draft header: `⚠️ High assumption risk — verify before Phase 1`
- **5+ HIGH: STOP. Do NOT draft the plan.** Instead, ask the user to clarify. List your HIGH assumptions as questions. A plan built on 5+ guesses is not a plan — it's a gamble.

**What counts as ASSUMED (not KNOWN):**
- You didn't read the file, you inferred from the directory name
- You read the file but didn't verify how it's used by other files
- The behavior is undocumented and you're guessing from naming conventions
- You're assuming a library/framework works a certain way without checking docs

**What counts as KNOWN:**
- You read the actual code and it explicitly does X
- The test suite verifies this behavior
- Configuration file explicitly sets this value

This gate exists because the most common failure mode is: agent reads 5 files, understands 3, plans as if it understood 5. The plan looks good. Execution reveals the 2 misunderstood files break everything.

**Mechanical enforcement**: Pass assumptions to `draft-plan` with `--assumptions`:
```bash
python -m core.pipeline draft-plan {project} --data '[...]' --assumptions '[{"assumption": "DB supports JSON columns", "basis": "PostgreSQL docs", "severity": "LOW"}, {"assumption": "middleware runs in order", "basis": "read app.ts:15", "severity": "HIGH"}]'
```
- 5+ HIGH → `draft-plan` exits with error (`sys.exit(1)`), draft NOT saved
- 3-4 HIGH → warning in draft header
- Assumptions stored on `tracker.draft_plan.assumptions`

---

### Step 6.5 — Impact Map (Standard/Complex only)

**Skip for Quick track.**

Before drafting the plan, produce an **Impact Map** that proves understanding of the codebase you are about to modify. This prevents plans built on surface-level directory scans.

For each file that any task will create or modify:

1. **Read the file** (or the directory it will be created in)
2. **Search for usages**: `grep` for imports, function calls, references across the codebase
3. **Identify invariants**: ordering constraints, interface contracts, configuration dependencies

Produce this table:

```
## Impact Map

| File | Action | Depended on by | Invariants |
|------|--------|----------------|------------|
| src/api/auth.ts | modify | routes/*.ts, middleware/rate-limit.ts | Must run BEFORE rate-limit middleware |
| src/models/user.ts | create | api/auth.ts, api/users.ts | Matches DB migration schema |
| migrations/002_sessions.sql | create | — | Must run AFTER 001_users.sql |

### Integration Points
1. {file} exports {symbol} used by {N consumers} — signature change is breaking
2. {config key} is read at {location} — change requires restart

### Assumptions
- "Database migrations run before app start" — VERIFIED (read docker-compose.yml:12)
- "Rate limiter is stateless" — UNVERIFIED (must check during T-003)
```

**Rules:**
- Every file mentioned in task instructions MUST appear in the Impact Map
- Every UNVERIFIED assumption must be assigned to a task for verification
- If you discover an invariant that affects task ordering, update `depends_on` accordingly

Store the Impact Map as a knowledge object (W4):

```bash
python -m core.knowledge add {project} --data '[{"title": "Impact Map: {goal}", "category": "architecture", "scopes": ["{scopes}"], "content": "{impact map markdown}"}]'
```

Tasks will receive this knowledge via `knowledge_ids` in `pipeline context`.

---

### Step 7 — Configure Project

Set up project configuration for gates and git:

```bash
python -m core.pipeline config {project} --data '{"test_cmd": "pytest", "lint_cmd": "ruff check ."}'
```

Configure validation gates:
```bash
python -m core.gates config {project} --data '[{"name": "test", "command": "pytest", "required": true}, {"name": "lint", "command": "ruff check .", "required": true}]'
```

Adapt commands to the project's actual tech stack. If unsure about commands,
create an OPEN decision asking the user.

---

### Step 7.5 — Plan Quality Test (mandatory)

Before showing the draft to the user, run these checks. Each is an action
with a binary result — not a question to answer "yes" to. Write the output
of each check inline.

**Check 1 — Cold start, first task:**
Take `_1`'s instruction. Write: "First file to open: [path]."
If you cannot name an exact path — instruction is invalid. Fix before continuing.

Common failures: "Implement the auth system" (which files?), "Set up the database"
(which tables?), "Add error handling" (which errors? where?).

**Check 2 — Cold start, last task:**
Same for the last task. Planning fatigue makes last tasks the vaguest. Fix it.

**Check 3 — Dependency contracts:**
For every task with `depends_on`, write:
```
_N depends_on _M
  _M.produces key: [key name]
  _N.uses_from_dependencies._M: [value] — matches key? [YES/NO]
  _N.instruction references this item? [YES: quote / NO]
```
Any NO = contract broken. Fix: either add the reference to instruction, fill
`uses_from_dependencies`, or remove the dependency.

**Check 4 — Scope leak:**
List every item tagged `[SCOPE-OUT]` in Step 0. For each, write:
"Is there a task that implements this? [task id / NONE]"
Any answer other than NONE = scope leak. Fix: either remove that work from the task,
or re-tag the item in Step 0 as `[REQ]` with clear boundary (e.g., "partial: only the X part").

All 4 checks must produce written output. Unwritten = not done.
If any check fails: fix the task, then restart from Check 1.

---

### Step 7.6 — Coverage Check (mandatory)

Open the source document (page spec, requirement doc, analysis file) that defines what you're building. For every concrete requirement or UI element in the source:

| Source doc requirement | Covered by task | Status |
|------------------------|----------------|--------|
| 3 sub-tabs (Active, All, Previously Purchased) | T-008 | COVERED |
| Sales type override per customer | — | DEFERRED: needs business rule clarification |
| Country-scoped access for OpCo role | — | DEFERRED: needs auth refactor |

Every requirement must be one of:
- **COVERED** — a task implements it, and the task's instruction mentions it
- **DEFERRED** — intentionally postponed, with a reason
- **OUT_OF_SCOPE** — explicitly excluded, with a reason

**There is no MISSING.** If a requirement isn't covered and you can't justify deferring it, add it to a task.

#### Semantic Fidelity Check

After syntactic coverage, `draft-plan` also runs a **semantic check**: it extracts key terms from each requirement K-NNN and checks if the covering task's instruction contains those terms. If fewer than 30% of key terms match, a `SEMANTIC_GAP` warning is printed.

**When you see SEMANTIC_GAP warnings:**
1. Re-read the source requirement (K-NNN content)
2. Compare with the task instruction — did you rephrase in a way that changes meaning?
3. If the instruction is semantically correct but uses different vocabulary, update the instruction to include key terms from the requirement
4. If the requirement was decomposed across multiple tasks, verify each piece is covered somewhere

**Mechanical enforcement**: Pass coverage to `draft-plan` with `--coverage`:
```bash
python -m core.pipeline draft-plan {project} --data '[...]' --coverage '[
  {"requirement": "3 sub-tabs", "status": "COVERED", "covered_by": "T-008"},
  {"requirement": "sales type override", "status": "DEFERRED", "reason": "needs business rule clarification"},
  {"requirement": "country scoping", "status": "DEFERRED", "reason": "needs auth refactor"}
]'
```
- Any requirement with status `MISSING` → `draft-plan` exits with error, draft NOT saved
- `DEFERRED` and `OUT_OF_SCOPE` require a `reason` field — no reason = error
- Coverage summary printed in draft header

---

### Step 8 — Review and Approve

The draft plan is displayed automatically by `draft-plan`. Present it to the user:

```
## Draft Plan: {goal}
Complexity: {track}
Tasks: {N}

{task list from draft-plan output}

Review the tasks above. When ready, I'll approve and materialize into the pipeline.
```

Wait for user approval. Offer:
- Modify tasks (regenerate draft with `draft-plan`)
- Add/remove tasks
- Reorder dependencies
- Change task granularity

When user approves, materialize (W2b):
```bash
python -m core.pipeline approve-plan {project}
```

This will:
- Move draft tasks into the pipeline
- If source idea was specified, mark it as COMMITTED
- Validate the DAG

Then show the final status:
```bash
python -m core.pipeline status {project}
```

Offer: Start execution with `/next`

---

## Error Handling

| Error | Action |
|-------|--------|
| Goal too vague | Ask user for clarification before decomposing |
| DAG validation fails | Fix circular dependencies, re-add tasks |
| Too many tasks (>12) | Consider grouping related tasks |
| Too few tasks (<2) for Standard/Complex | Reconsider if decomposition is too coarse |

## Resumability

- If interrupted during planning, project already exists via init (W1)
- Tasks can be added incrementally via draft-plan (W2) or add-tasks (W2c)
- Planning decisions are already persisted (W3)

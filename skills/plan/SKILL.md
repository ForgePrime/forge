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
| R4 | `python -m core.decisions contract add` | Contract for recording decisions | Step 4 — before recording planning decisions |
| R5 | `python -m core.changes contract` | Contract for recording changes | Reference only |

## Write Commands

| ID | Command | Effect | When | Contract |
|----|---------|--------|------|----------|
| W1 | `python -m core.pipeline init {project} --goal "..."` | Creates tracker.json | Step 3 — create project |
| W2 | `python -m core.pipeline draft-plan {project} --data '{json}' [--idea I-NNN]` | Stores draft plan for review | Step 5 — after decomposition |
| W2b | `python -m core.pipeline approve-plan {project}` | Materializes draft into pipeline | Step 7 — after user approval |
| W2c | `python -m core.pipeline add-tasks {project} --data '{json}'` | Direct task addition (alternative to draft) | Step 5 — when bypassing draft review |
| W3 | `python -m core.decisions add {project} --data '{json}'` | Records planning decisions | Step 4 — for architectural choices | `python -m core.decisions contract add` |

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

Decompose a user's high-level goal into a tracked task graph. The plan skill
follows a complexity-first approach: assess the scope before decomposing.

## Prerequisites

- User has stated a goal
- Working directory is a codebase (or will become one)

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

When decomposing (Step 5), assign `scopes` to each task based on which guidelines apply.

If planning from an idea (`/plan I-001`), load the idea's scopes and use them to filter guidelines:
```bash
python -m core.ideas show {project} {idea_id}
python -m core.guidelines context {project} --scopes "{idea_scopes}"
```

**Must-guidelines are non-negotiable during decomposition:**
- If a must-guideline says "all endpoints need rate limiting" → include a rate limiting task or subtask
- If a must-guideline says "use PostgreSQL" → do NOT plan tasks with MongoDB
- Record a decision if a must-guideline conflicts with the goal (don't silently ignore)

---

### Step 3 — Assess Complexity

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

### Step 4 — Create Project

Generate a project slug from the goal (lowercase, hyphens, max 40 chars):
```bash
python -m core.pipeline init {slug} --goal "{full goal text}"
```

If you make any architectural decisions during planning (e.g., choosing a framework,
deciding on a pattern), record them immediately:

MANDATORY — load contract first (R4):
```bash
python -m core.decisions contract add
```

Then record:
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "PLANNING",
  "type": "architecture",
  "issue": "...",
  "recommendation": "...",
  "reasoning": "...",
  "alternatives": ["...", "..."],
  "confidence": "HIGH|MEDIUM|LOW",
  "decided_by": "claude"
}]'
```

Use `task_id: "PLANNING"` for decisions made before tasks exist.

---

### Step 5 — Decompose

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
- `id`: T-001, T-002, etc.
- `name`: kebab-case, descriptive (e.g., "setup-database-schema")
- `description`: WHAT needs to be done (concrete, not vague)
- `instruction`: HOW to do it (step-by-step, mention specific files)
- `depends_on`: list of prerequisite task IDs
- `parallel`: true if this task can run alongside siblings
- `conflicts_with`: list of task IDs modifying same files
- `scopes`: list of guideline scopes this task relates to (e.g., `["backend", "database"]`). Inherit from idea scopes where applicable. `general` is always included automatically during execution.

Store as draft plan for review (W2):
```bash
python -m core.pipeline draft-plan {project} --data '[...]' --idea {idea_id_if_applicable}
```

---

### Step 6 — Configure Project

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

### Step 7 — Review and Approve

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

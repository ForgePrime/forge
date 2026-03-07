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
| R3 | `python -m core.decisions contract add` | Contract for recording decisions | Step 4 — before recording planning decisions |
| R4 | `python -m core.changes contract` | Contract for recording changes | Reference only |

## Write Commands

| ID | Command | Effect | When | Contract |
|----|---------|--------|------|----------|
| W1 | `python -m core.pipeline init {project} --goal "..."` | Creates tracker.json | Step 3 — create project |
| W2 | `python -m core.pipeline add-tasks {project} --data '{json}'` | Adds tasks to pipeline | Step 5 — after decomposition |
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

### Step 2 — Learn from History

Check lessons from past projects for relevant patterns:
```bash
python -m core.lessons read-all
```

Note any lessons that apply to the current goal.

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

MANDATORY — load contract first (R3):
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

### Step 5 — Check Recipes and Decompose

Before decomposing from scratch, check if a recipe matches the goal:

```bash
python -m core.recipes list
```

If a recipe fits, apply it:
```bash
python -m core.recipes show {recipe-name}
python -m core.recipes apply {project} {recipe-name} --vars '{...}'
```

Then customize the generated tasks for the specific goal. Skip to Step 6.

If no recipe fits, decompose manually:

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

Add tasks to pipeline (W2):
```bash
python -m core.pipeline add-tasks {project} --data '[...]'
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

### Step 7 — Present and Confirm

Show the plan:
```bash
python -m core.pipeline status {project}
```

Present the plan to the user with a summary:
```
## Plan: {goal}
Complexity: {track}
Tasks: {N}

{task list with descriptions}

Ready to start? Use /next to begin, or modify the plan first.
```

Wait for user approval. Offer:
- Add/remove tasks
- Reorder dependencies
- Change task granularity
- Start execution with `/next`

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
- Tasks can be added incrementally via add-tasks (W2)
- Planning decisions are already persisted (W3)

# Forge — Structured Change Orchestrator

You are operating inside Forge, a change orchestration system.
Every code change you make must be **planned, tracked, reasoned about, and auditable**.

## Core Principle

You do NOT just write code. You:
1. **Plan** — decompose the goal into tasks with dependencies
2. **Track** — every task has a status in the pipeline
3. **Decide** — record architectural and implementation decisions with reasoning
4. **Execute** — make changes, recording what you changed and why
5. **Validate** — run tests/checks before marking complete

## How It Works

### Pipeline (task graph)
```
python -m core.pipeline init {project} --goal "..."     Create project
python -m core.pipeline add-tasks {project} --data '...' Add tasks
python -m core.pipeline next {project}                   Get next task
python -m core.pipeline complete {project} {task_id}     Mark done
python -m core.pipeline status {project}                 Dashboard
```

### Decisions (why things are done)
```
python -m core.decisions add {project} --data '...'    Record a decision
python -m core.decisions read {project}                 View all decisions
python -m core.decisions read {project} --status OPEN   Open decisions
python -m core.decisions update {project} --data '...'  Close/defer
python -m core.decisions contract add                   See expected format
```

### Changes (what was modified)
```
python -m core.changes diff {project} {task_id}         Auto-detect changes from git
python -m core.changes record {project} --data '...'    Record file changes
python -m core.changes read {project}                   View change log
python -m core.changes summary {project}                Statistics
python -m core.changes contract                         See expected format
```

### Lessons (compound learning)
```
python -m core.lessons add {project} --data '...'      Record lessons learned
python -m core.lessons read {project}                   View project lessons
python -m core.lessons read-all                         View lessons across all projects
python -m core.lessons contract                         See expected format
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/plan {goal}` | Decompose a goal into a tracked task graph |
| `/status` | Show current project status |
| `/next` | Get and start the next task |
| `/decide` | Review and resolve open decisions |
| `/log` | Show full audit trail (changes + decisions) |
| `/compound` | Extract lessons learned from project execution |

## Task Properties

When adding tasks, each task supports:
- `id`, `name`, `description`, `instruction` — basic info
- `depends_on` — list of task IDs that must complete first
- `parallel` — `true` if this task can run alongside others (multi-agent)
- `conflicts_with` — list of task IDs that modify same files (cannot run in parallel)
- `skill` — path to SKILL.md for structured execution

## Workflow

When user gives a goal:
1. Run `/plan {goal}` — creates project, decomposes into tasks
2. Check lessons from past projects: `python -m core.lessons read-all`
3. Run `/next` — get first task
4. For each task:
   a. Record any significant decisions via `decisions add`
   b. Make the code changes
   c. Record changes via `changes record`
   d. Run relevant tests/checks
   e. Mark task complete via `pipeline complete`
5. When all tasks done, run `/compound` to extract lessons
6. Show summary

## Rules

- **NEVER skip the pipeline**. Every change goes through plan -> execute -> record.
- **Record decisions** for any non-trivial choice (architecture, library, pattern, trade-off).
- **Record changes** for every file you create, edit, or delete.
- **reasoning_trace is mandatory** — explain WHY, not just WHAT.
- **Contracts are the source of truth** — run `contract` before producing structured output.
- **When unsure, create an OPEN decision** — let the human decide.
- **Tests before completion** — run tests/lint before marking a task DONE.

## Current Project

On startup, check for existing projects:
```bash
ls forge_output/ 2>/dev/null
```

If projects exist, show status. Otherwise, wait for `/plan`.

## Configuration

If `.claude/forge.local.md` exists, read it for user preferences.

## Output Location

All Forge state goes to `forge_output/{project}/`:
- `tracker.json` — pipeline state
- `decisions.json` — decision log
- `changes.json` — change records
- `lessons.json` — lessons learned (compound learning)

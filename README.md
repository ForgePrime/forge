# Forge

Structured change orchestrator for Claude Code. Turns high-level goals into tracked, dependency-aware tasks with full traceability and observability.

Every code change goes through: **Plan → Track → Decide → Execute → Record → Validate**

## Why Forge

Most AI coding assistants generate code without structure. Forge adds:

- **Traceability** — every change linked to a task, decision, and reasoning trace
- **Decision log** — architectural choices recorded with provenance (who, why, alternatives)
- **Validation gates** — tests, lint, and secret scanning before task completion
- **Resumability** — interrupt and resume at any point; state persists in JSON
- **Compound learning** — lessons extracted from past projects inform future ones

## Quick Start

```bash
# Inside Claude Code, use slash commands:
/plan Add JWT authentication to the API    # Decompose goal into task graph
/next                                       # Execute next task with traceability
/status                                     # Show project dashboard + DAG
/decide                                     # Review open decisions
/log                                        # Full audit trail
```

For existing codebases, start with `/onboard {path}` to import project knowledge before planning.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/plan {goal}` | Decompose a goal into a tracked task graph |
| `/next` | Get and execute the next task with full traceability |
| `/run [tasks]` | Continuous execution (`/run`, `/run 3`, `/run T-003..T-007`) |
| `/status` | Show project state, decisions, and change summary |
| `/decide` | Review and resolve open decisions (accept/override/defer) |
| `/review {task_id}` | Structured code review (5 perspectives) |
| `/log` | Full audit trail: decisions + changes + narrative |
| `/compound` | Extract lessons learned from project execution |
| `/onboard {path}` | Import brownfield project knowledge into Forge |
| `/process [skill]` | Execute external plugin skill from registry |

## Architecture

```
forge/
  core/                  # Domain-agnostic Python engine
    pipeline.py          # Task graph state machine (DAG with dependencies)
    decisions.py         # Decision log with provenance
    changes.py           # Change tracking with reasoning traces
    contracts.py         # Contract-first validation (render + validate)
    gates.py             # Validation gates (test, lint, secrets)
    lessons.py           # Compound learning across projects
    git_ops.py           # Optional git integration (branch, commit)
    recipes.py           # Task graph templates
    plugins.py           # External skill registry & discovery
  skills/                # Built-in skill definitions (SKILL.md format)
    plan/                #   Decompose goal into task graph
    next/                #   Execute task with full traceability
    onboard/             #   Import brownfield project knowledge
    review/              #   Structured 5-perspective code review
  recipes/               # Reusable task graph templates
    api-endpoint.json    #   5-task template for adding API endpoints
    bug-fix.json         #   3-task template: investigate → fix → regression test
    refactor.json        #   4-task template: audit → tests → change → verify
  docs/                  # Design documentation
    DESIGN.md            #   Architecture, concepts, Python/LLM boundary
    ASSUMPTIONS.md       #   Active assumptions and deferred decisions
    STANDARDS.md         #   Standards for skills and core modules
  .claude/               # Claude Code integration
    CLAUDE.md            #   Agent instructions and command reference
    commands/            #   Slash command definitions
    settings.json        #   PostToolUse hooks
  forge_output/          # Runtime state (per-project JSON files)
```

## Core Concepts

### Pipeline (Task Graph)

Tasks form a DAG with explicit dependencies. States: `TODO → IN_PROGRESS → DONE` (or `FAILED`/`SKIPPED`). Supports parallel execution, conflict detection, and subtask decomposition.

### Decision Log

Every non-trivial choice is recorded with: issue, recommendation, reasoning, alternatives, confidence level, and who decided (human vs AI). Statuses: `OPEN`, `CLOSED`, `DEFERRED`, `OVERRIDE`.

### Change Records

Every file modification tracked with `reasoning_trace` (mandatory) — an array of steps explaining *why* the change was made, linked to tasks and decisions.

### Validation Gates

Configurable per project: test, lint, type-check, secret scanning. Required gates block task completion until fixed. Runs automatically before marking a task DONE.

### Compound Learning

Lessons extracted from completed projects (patterns discovered, mistakes avoided, decisions validated). Stored and queried across projects to improve future work.

### Recipes

JSON templates for common task patterns. Apply with variable substitution to quickly scaffold familiar workflows.

### Plugin Skills

External skills auto-discovered from configured scan paths. Registered in `forge_plugins.json` and executed via `/process {skill-name}`.

## CLI Usage (standalone, without Claude Code)

```bash
# Pipeline
python -m core.pipeline init myproject --goal "Build a REST API"
python -m core.pipeline add-tasks myproject --data '[...]'
python -m core.pipeline next myproject
python -m core.pipeline complete myproject T-001
python -m core.pipeline status myproject

# Decisions
python -m core.decisions add myproject --data '[...]'
python -m core.decisions read myproject --status OPEN
python -m core.decisions update myproject --data '[...]'

# Changes
python -m core.changes diff myproject T-001
python -m core.changes record myproject --data '[...]'
python -m core.changes summary myproject

# Gates
python -m core.gates config myproject --data '[...]'
python -m core.gates check myproject --task T-001
python -m core.gates scan-secrets myproject

# Lessons
python -m core.lessons add myproject --data '[...]'
python -m core.lessons read-all

# Recipes
python -m core.recipes list
python -m core.recipes apply myproject api-endpoint --vars '{"component_name": "users"}'

# Git
python -m core.git_ops branch-create myproject T-001
python -m core.git_ops commit myproject T-001 -m "Add user endpoint"

# Plugins
python -m core.plugins scan
python -m core.plugins list
```

Use `contract` subcommand on any module to see the expected data format (e.g. `python -m core.pipeline contract add-tasks`).

## Multi-Agent Support

Forge supports multiple agents working on the same project in parallel:

- Each agent identifies with `--agent {name}` on `next` and `complete`
- Two-phase claiming prevents race conditions (`CLAIMING → IN_PROGRESS`)
- `conflicts_with` on tasks prevents concurrent modification of the same files

## Heritage

Core patterns evolved from Skill_v1 (BigQuery schema builder):

| Pattern | Description |
|---------|-------------|
| Contract-first | One Python dict drives both the LLM prompt and validation |
| Pipeline state machine | Resumable task execution with dependency tracking |
| Decision log | Accept/override/defer with human vs AI provenance |
| Python/LLM boundary | Python handles I/O + validation, LLM handles judgment |

See `docs/DESIGN.md` for full architecture documentation.

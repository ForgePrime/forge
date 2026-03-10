# Forge

Structured change orchestrator for Claude Code. Turns high-level goals into tracked, dependency-aware tasks with full traceability and observability.

Every code change goes through: **Plan → Track → Decide → Execute → Record → Validate**

Three tracks: **`/do`** (quick — 80% of tasks) | **`/plan`** (standard) | **full workflow** (objective → idea → discover → plan)

## Why Forge

Most AI coding assistants generate code without structure. Forge adds:

- **Traceability** — every change linked to a task, decision, and reasoning trace
- **Decision log** — architectural choices recorded with provenance (who, why, alternatives)
- **Validation gates** — tests, lint, and secret scanning before task completion
- **Resumability** — interrupt and resume at any point; state persists in JSON
- **Compound learning** — lessons extracted from past projects inform future ones

## Quick Start

```bash
# Quick path — simple tasks (bug fix, refactor, small feature):
/do Fix the login timeout bug in auth.py    # One task, start to finish

# Standard path — multi-task work:
/plan Add Redis caching to API              # Decompose → execute → done

# Full path — complex/risky work:
/objective Reduce API response time         # Define business goal
/idea Redis caching                         # Capture proposal
/discover I-001                             # Explore risks & options
/plan I-001                                 # Draft plan → approve → execute
```

```bash
# Other useful commands:
/guideline use Repository Pattern --scope backend  # Set project standards
/next                                       # Execute next task (with verification)
/run                                        # Execute all tasks continuously
/status                                     # Show project dashboard + DAG
```

For existing codebases, start with `/onboard {path}` to import project knowledge before planning.

## Slash Commands

| Command | Description |
|---------|-------------|
| **`/do {task}`** | **Quick path — single task, start to finish, minimum ceremony** |
| `/plan {goal\|idea_id}` | Decompose goal into task graph (two-phase: draft → approve) |
| `/idea {title}` | Add idea to staging area (supports hierarchy and relations) |
| `/ideas [id] [action]` | List/show/manage ideas (explore, approve, reject, commit) |
| `/discover {topic\|idea_id}` | Explore options, assess risks → creates exploration + risk decisions |
| `/risk [title\|id] [action]` | Manage risks (add, analyze, mitigate, accept, close) |
| `/guideline {text}` | Add project guideline |
| `/guidelines [scope]` | List/manage guidelines |
| `/next` | Execute next task (includes verification + guidelines check) |
| `/run [tasks]` | Continuous execution (`/run`, `/run 3`, `/run T-003..T-007`) |
| `/status` | Show project state, decisions, and change summary |
| `/decide` | Review and resolve open decisions (accept/override/defer) |
| `/review {task_id}` | Deep code review (optional — basic built into `/next`) |
| `/log` | Full audit trail: decisions + changes + narrative |
| `/compound` | Extract lessons learned from project execution |
| `/onboard {path}` | Import brownfield project knowledge into Forge |

## Architecture

```
forge/
  core/                  # Domain-agnostic Python engine
    pipeline.py          # Task graph state machine (DAG with dependencies, two-phase planning)
    decisions.py         # Unified decision log (standard + exploration + risk)
    changes.py           # Change tracking with reasoning traces
    contracts.py         # Contract-first validation (render + validate)
    gates.py             # Validation gates (test, lint, secrets)
    lessons.py           # Compound learning across projects
    guidelines.py        # Project standards and conventions registry
    ideas.py             # Hierarchical idea staging with relations
  skills/                # Built-in skill definitions (SKILL.md format)
    discover/            #   Explore, assess, design before planning
    plan/                #   Decompose goal into task graph
    next/                #   Execute task with full traceability
    onboard/             #   Import brownfield project knowledge
    review/              #   Structured 6-perspective code review
    deep-orchestration/  #   Coordinate analysis workflows
    deep-explore/        #   Structured option exploration
    deep-risk/           #   5D risk assessment
    deep-architect/      #   Architecture with adversarial testing
    deep-verify/         #   Artifact verification with scoring
    deep-aggregate/      #   Combine analysis outputs
    deep-align/          #   Goal alignment before analysis
    optional/            #   Additional skills (deep-feasibility, deep-requirements, niche-scout)
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

### Decision Log (Unified)

Every non-trivial choice is recorded with: issue, recommendation, reasoning, alternatives, confidence level, and who decided (human vs AI). Three types:
- **Standard** decisions: architecture, implementation, security, etc. Statuses: `OPEN`, `CLOSED`, `DEFERRED`, `OVERRIDE`.
- **Exploration** decisions (type=exploration): findings, options, open questions from `/discover`. Carries `exploration_type`, `findings`, `options`.
- **Risk** decisions (type=risk): severity, likelihood, mitigation plan. Lifecycle: `OPEN → ANALYZING → MITIGATED/ACCEPTED → CLOSED`.

### Change Records

Every file modification tracked with `reasoning_trace` (mandatory) — an array of steps explaining *why* the change was made, linked to tasks and decisions.

### Validation Gates

Configurable per project: test, lint, type-check, secret scanning. Required gates block task completion until fixed. Runs automatically before marking a task DONE.

### Compound Learning

Lessons extracted from completed projects (patterns discovered, mistakes avoided, decisions validated). Stored and queried across projects to improve future work.

### Guidelines

Project-wide coding standards, architectural conventions, and rules. Scoped (backend, frontend, database, general, etc.) and weighted (must/should/may) to control context injection. Automatically loaded into task context during execution — `must` guidelines always visible, `should` when count is manageable, `may` on demand.

### Ideas (Staging)

Hierarchical proposals that mature before becoming tasks. Lifecycle: `DRAFT → EXPLORING → APPROVED → COMMITTED`. Ideas support parent-child hierarchy (`parent_id`) and typed relations (`depends_on`, `related_to`, `supersedes`, `duplicates`). During EXPLORING, run `/discover` to create exploration and risk decisions. APPROVED ideas are committed to the task pipeline via `/plan` (two-phase: draft → user approval → materialize). REJECTED ideas are preserved with reasoning.

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
# Lessons
python -m core.lessons add myproject --data '[...]'
python -m core.lessons read-all --severity critical --limit 15

# Ideas (hierarchical)
python -m core.ideas add myproject --data '[{"title": "...", "parent_id": "I-001", "relations": [...]}]'
python -m core.ideas read myproject --status EXPLORING --parent root
python -m core.ideas show myproject I-001
python -m core.ideas commit myproject I-001

# Decisions (explorations + risks)
python -m core.decisions read myproject --type exploration
python -m core.decisions read myproject --type risk --status OPEN
python -m core.decisions show myproject D-001

# Guidelines
python -m core.guidelines add myproject --data '[...]'
python -m core.guidelines read myproject --scope backend
python -m core.guidelines context myproject --scopes "backend,database"

```

Use `contract` subcommand on any module to see the expected data format (e.g. `python -m core.pipeline contract add-tasks`).

## Multi-Agent Support

Forge supports multiple agents working on the same project in parallel:

- Each agent identifies with `--agent {name}` on `next` and `complete`
- Two-phase claiming prevents race conditions (`CLAIMING → IN_PROGRESS`)
- `conflicts_with` on tasks prevents concurrent modification of the same files

## Analysis Skills (Deep-Process)

Forge includes built-in analysis skills adapted from [Deep-Process](https://github.com/Deep-Process/deep-process):

| Skill | Purpose |
|-------|---------|
| deep-orchestration | Coordinate analysis workflows (conductor) |
| deep-explore | Structured option exploration with consequence tracing |
| deep-risk | 5-dimensional risk assessment with cascade analysis |
| deep-feasibility | 10-dimension feasibility with GO/NO-GO verdict |
| deep-architect | Architecture design with 8 adversarial challenges |
| deep-verify | Artifact verification with impossibility pattern matching |
| deep-requirements | Requirements extraction and contradiction checking |
| deep-aggregate | Combine multiple analysis outputs into decision brief |

These are invoked automatically via `/discover` or manually during task execution. Findings are recorded as Forge decisions with full provenance.

To check for updates from upstream: compare version in each `skills/deep-*/SKILL.md` provenance header against https://github.com/Deep-Process/deep-process.

## Heritage


| Pattern | Description |
|---------|-------------|
| Contract-first | One Python dict drives both the LLM prompt and validation |
| Pipeline state machine | Resumable task execution with dependency tracking |
| Decision log | Accept/override/defer with human vs AI provenance |
| Python/LLM boundary | Python handles I/O + validation, LLM handles judgment |

See `docs/DESIGN.md` for full architecture documentation.

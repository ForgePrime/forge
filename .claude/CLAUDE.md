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
python -m core.pipeline init {project} --goal "..."      Create project
python -m core.pipeline add-tasks {project} --data '...' Add tasks (direct, bypasses draft)
python -m core.pipeline draft-plan {project} --data '...' [--idea I-NNN]  Store draft plan for review
python -m core.pipeline show-draft {project}             Show current draft plan
python -m core.pipeline approve-plan {project}           Approve draft → materialize tasks
python -m core.pipeline update-task {project} --data '{...}' Update existing task
python -m core.pipeline remove-task {project} {task_id}  Remove TODO task
python -m core.pipeline next {project} [--agent name]    Get next task
python -m core.pipeline complete {project} {task_id} [--force]  Mark done (checks changes + gates)
python -m core.pipeline contract add-tasks               Show task contract
python -m core.pipeline contract update-task             Show update contract
python -m core.pipeline contract register-subtasks       Show subtask contract
python -m core.pipeline status {project}                 Dashboard + DAG
python -m core.pipeline context {project} {task_id}      Context from deps + risks
python -m core.pipeline config {project} --data '{...}'  Set project config
```

### Decisions (unified: decisions + explorations + risks)
```
python -m core.decisions add {project} --data '...'                     Record decisions
python -m core.decisions read {project}                                  View all decisions
python -m core.decisions read {project} --status OPEN                    Open decisions
python -m core.decisions read {project} --type exploration               Explorations only
python -m core.decisions read {project} --type risk                      Risks only
python -m core.decisions read {project} --entity I-001                   By linked entity
python -m core.decisions update {project} --data '...'                   Close/defer/mitigate
python -m core.decisions show {project} {decision_id}                    Full details
python -m core.decisions contract add                                    See expected format
```

Decision types:
- **Standard**: architecture, implementation, dependency, security, performance, testing, naming, convention, constraint, business, strategy, other
- **Exploration** (type=exploration): carries findings, options, open_questions, blockers, exploration_type (domain/architecture/business/risk/feasibility)
- **Risk** (type=risk): carries severity, likelihood, linked_entity_type/id, mitigation_plan, resolution_notes

Risk status lifecycle: OPEN → ANALYZING → MITIGATED/ACCEPTED → CLOSED (can reopen)

### Changes (what was modified)
```
python -m core.changes auto {project} {task_id} --reasoning "..." [--decision_ids "D-001,D-002"] [--guidelines "G-001"]  One-step: git diff → record
python -m core.changes diff {project} {task_id}         Auto-detect changes from git (manual enrichment)
python -m core.changes record {project} --data '...'    Record file changes (full control)
python -m core.changes read {project}                   View change log
python -m core.changes summary {project}                Statistics
python -m core.changes contract                         See expected format
```

Prefer `changes auto` for routine recording (one command). Use `changes diff` + `changes record` when per-file reasoning_trace is needed.

### Lessons (compound learning)
```
python -m core.lessons add {project} --data '...'      Record lessons learned
python -m core.lessons read {project}                   View project lessons
python -m core.lessons read-all [--severity X] [--tags "a,b"] [--category X] [--limit N]  View lessons across all projects
python -m core.lessons contract                         See expected format
```

### Ideas (staging area — hierarchical, with relations)
```
python -m core.ideas add {project} --data '[...]'                      Add ideas (supports parent_id, relations, scopes)
python -m core.ideas read {project} [--status X] [--category X] [--parent X]  Read ideas (--parent root for top-level)
python -m core.ideas show {project} {idea_id}                          Show full details (hierarchy, explorations, risks, decisions)
python -m core.ideas update {project} --data '[...]'                   Update status/fields (relations append-merged)
python -m core.ideas commit {project} {idea_id}                        Mark APPROVED → COMMITTED (validates depends_on)
python -m core.ideas contract add                                      Show idea contract
```

### Guidelines (project standards)
```
python -m core.guidelines add {project} --data '[...]'         Add guidelines
python -m core.guidelines read {project} [--scope X] [--weight X]  Read guidelines
python -m core.guidelines update {project} --data '[...]'      Update guideline status
python -m core.guidelines context {project} --scopes "a,b"     Guidelines for LLM context
python -m core.guidelines scopes {project}                     List unique scopes
python -m core.guidelines contract add                         Show guideline contract
```

### Gates (validation checks)
```
python -m core.gates config {project} --data '[...]'   Configure test/lint gates
python -m core.gates show {project}                    Show configured gates
python -m core.gates check {project} --task {task_id}  Run all gates
python -m core.gates contract config                   Show gate contract
```

Tip: Configure secret scanning as a gate: `{"name": "secrets", "command": "gitleaks detect --no-git -v", "required": true}`

## Slash Commands

| Command | Description |
|---------|-------------|
| `/idea {title}` | Add an idea to staging area (supports --parent, --relates-to) |
| `/ideas [id] [action]` | List/show/manage ideas (explore, approve, reject, commit) |
| `/discover {topic\|idea_id}` | Explore options, assess risks, design architecture → creates exploration + risk decisions |
| `/plan {goal\|idea_id}` | Decompose into task graph (two-phase: draft → approve) |
| `/risk [title\|id] [action]` | Manage risks (add type=risk decisions, analyze, mitigate, accept, close) |
| `/guideline {text}` | Add a project guideline (standard, convention, rule) |
| `/guidelines [scope]` | List/manage guidelines |
| `/status` | Show current project status |
| `/next` | Get and execute next task (includes verification + guidelines check) |
| `/run [tasks]` | Execute tasks continuously: `/run`, `/run 3`, `/run T-003..T-007` |
| `/decide` | Review and resolve open decisions |
| `/review {task_id}` | Deep code review (optional — basic verification built into `/next`) |
| `/log` | Show full audit trail (changes + decisions) |
| `/compound` | Extract lessons learned from project execution |
| `/onboard` | Import brownfield project knowledge into Forge (see `skills/onboard/SKILL.md`) |

## Task Properties

When adding tasks, each task supports:
- `id`, `name`, `description`, `instruction` — basic info
- `type` — task category: `feature` (default), `bug`, `chore`, `investigation`
- `acceptance_criteria` — list of concrete conditions that must be true when DONE
- `depends_on` — list of task IDs that must complete first
- `blocked_by_decisions` — list of decision IDs (D-001, etc.) that must be CLOSED before this task can start
- `parallel` — `true` if this task can run alongside others (multi-agent)
- `conflicts_with` — list of task IDs that modify same files (cannot run in parallel)
- `skill` — path to SKILL.md for structured execution
- `scopes` — list of guideline scopes this task relates to (e.g., `["backend", "database"]`). `general` is always included automatically. Used by `pipeline context` to load applicable guidelines.
- `origin` — where this task came from (idea ID like `I-001`, or free text)

Tasks can be modified after creation with `update-task` (only TODO/FAILED tasks).
Tasks can be removed with `remove-task` (only TODO, and only if no other tasks depend on them).

### Decision Blocking

Tasks with `blocked_by_decisions` will NOT be picked up by `next` (or `/run`) until all listed decisions are CLOSED.
This ensures architectural/design decisions are resolved before implementation begins.
Use `/decide` to review and close OPEN decisions.

### Completion Enforcement

`pipeline complete` checks before marking DONE:
- Changes must be recorded for the task (at least one entry in changes.json)
- Gates must have passed (if gates were run)
- Use `--force` to bypass these checks when appropriate (e.g., investigation tasks with no code changes)

## Workflow

For brownfield projects (existing codebase):
1. Run `/onboard` — discover project, import decisions/conventions, configure gates
2. Then continue with `/plan {goal}` for specific work

When user gives a goal:
1. Capture as idea: `/idea {title}` — add to staging area
   - Ideas support hierarchy: `/idea {title} --parent I-001` for sub-ideas
   - Ideas support relations: depends_on, related_to, supersedes, duplicates
2. Explore: `/discover {idea_id}` — creates exploration + risk decisions
   - Status flow: DRAFT → EXPLORING → APPROVED
   - Use `/risk` to track and mitigate identified risks
3. When ready: `/ideas {idea_id} approve` then `/plan {idea_id}`
4. `/plan` creates a **draft plan** — review, modify, then approve to materialize
5. Configure project: `pipeline config` (test_cmd, lint_cmd) and `gates config`
6. Define project guidelines: `/guideline {text}` — coding standards, conventions
7. Run `/next` — get first task (follows `skills/next/SKILL.md`)
8. For each task:
   a. Gather context: `pipeline context {project} {task_id}` (deps + guidelines + risks)
   b. Record any significant decisions via `decisions add`
   c. Make the code changes
   d. Record changes via `changes diff` then `changes record`
   e. Verify: deep-verify + guidelines compliance (built into `/next` Step 5)
   f. Run gates: `gates check {project} --task {task_id}`
   g. Commit changes via git
   h. Mark task complete via `pipeline complete` (enforces changes + gates)
9. Optionally run `/review {task_id}` for critical tasks
10. When all tasks done, run `/compound` to extract lessons

## Rules

- **NEVER skip the pipeline**. Every change goes through plan -> execute -> record.
- **Record decisions** for any non-trivial choice (architecture, library, pattern, trade-off).
- **Record changes** for every file you create, edit, or delete.
- **reasoning_trace is mandatory** — explain WHY, not just WHAT.
- **Contracts are the source of truth** — run `contract` before producing structured output.
- **When unsure, create an OPEN decision** — let the human decide.
- **Tests before completion** — run tests/lint before marking a task DONE.
- **Use --force on complete** only for tasks that genuinely have no code changes (e.g., investigation, planning).

## Multi-Agent Support

Forge supports multiple agents working on the same project in parallel.

### How it works
- Each agent identifies itself with `--agent {name}` on `next` and `complete`
- Single-agent mode skips the claim wait (no 1.5s delay)
- Multi-agent mode uses **two-phase claim**: CLAIMING → wait → verify → IN_PROGRESS (max 5 retries)
- `conflicts_with` is enforced: if task A conflicts with task B, they cannot be active at the same time

### Usage
```bash
# Agent Alice gets her next task
python -m core.pipeline next {project} --agent alice

# Agent Bob gets a different task (conflicts respected)
python -m core.pipeline next {project} --agent bob

# Each agent completes their own task
python -m core.pipeline complete {project} T-001 --agent alice
python -m core.pipeline complete {project} T-002 --agent bob
```

### Rules for multi-agent
- Set `conflicts_with` on tasks that modify the same files
- Tasks with unmet dependencies are never assigned
- Tasks conflicting with an active task are blocked until it completes
- Without `--agent`, single-agent mode works as before (backward compatible)

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
- `tracker.json` — pipeline state (tasks + optional draft_plan)
- `decisions.json` — unified decision log (includes explorations and risks)
- `changes.json` — change records
- `lessons.json` — lessons learned (compound learning)
- `guidelines.json` — project standards and conventions
- `ideas.json` — idea staging area (hierarchical, with relations)

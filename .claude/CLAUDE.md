# Forge — Change Orchestrator

You are operating inside Forge. Your job: plan work, execute it, and leave a trail that makes sense.

## Core Principle

1. **Understand** — read the code, list your assumptions, check for conflicts
2. **Plan** — decompose into tasks with a dependency graph
3. **Execute** — implement, validate (gates + tests), record what changed

That's it. Don't add ceremony that doesn't help you deliver correctly.

## What matters

```
Tasks (core) ──→ Dependencies + Produces contracts
  │
  ├─ validated by Gates (tests, lint — mechanically enforced)
  ├─ guided by Guidelines (project rules loaded by scope)
  └─ documented by Decisions (only when deviating or choosing between alternatives)
```

**Required when source documents are ingested** (enforced by pipeline gates):
Objectives (with measurable KRs), Knowledge, Research, Decisions.
Pipeline: `/ingest` → `/analyze` (creates objectives) → `/plan --objective O-NNN` → `/run`.
Skipping `/analyze` will BLOCK `/plan` when source documents exist.

**Available for complex projects** (use via `/discover`, `/objective`):
Ideas, AC Templates, Domain Modules, Lessons — these are opt-in.

## Fidelity Chain (mechanically enforced)

Prevents information loss from docs → objectives → tasks → code:

- **Atomic Requirements**: `knowledge add` warns on compound requirements (>100 chars + "and"/"oraz")
- **Semantic Coverage**: `draft-plan` checks that task instructions contain key terms from requirements
- **Cross-Objective Overlap**: `draft-plan` detects when new tasks duplicate DONE tasks from other objectives
- **Feature Registry**: `complete` registers routes/components; `draft-plan` checks for conflicts
- **Over-Coverage**: `approve-plan` detects when same requirement is covered by tasks from different objectives
- **Source Fidelity**: `begin` compares task instruction against linked requirements, warns on drift
- **Implementation Traceability**: `complete` checks git diff against requirement key terms

Feature Registry: `python -m core.feature_registry show {project}` — shows what features exist.

## Pipeline Contracts (mechanically enforced)

Each pipeline transition has a contract checked by CODE. See `docs/PIPELINE-CONTRACTS.md` for full spec.

- **C1 — Ingestion completeness**: `draft-plan` BLOCKS if source docs registered but facts not extracted. Check: `python -m core.pipeline validate-ingestion {project}`
- **C2 — Analysis completeness**: `draft-plan` BLOCKS if source docs exist but no objectives with measurable KRs. Check: `python -m core.objectives verify {project}`
- **C3 — Plan linkage**: `draft-plan` BLOCKS without `--objective` when active objectives exist. `approve-plan` BLOCKS if origin/knowledge_ids reference non-existent entities.
- **C5 — Begin contract**: `begin` WARNS if task targets an ACHIEVED objective.
- **C6 — Complete + KR**: `complete` validates `kr_link` references, KR measurement failures are WARNED (not silent). Task without origin that should have one → WARNING.
- **C7 — Objective completion**: When last task for O-NNN completes, auto-checks all KRs. If all met → objective ACHIEVED. If not → WARNING with unmet KRs.

## Mechanical Guardrails

- **Readiness gate**: `draft-plan --assumptions '[...]'` rejects plan at 5+ HIGH-severity assumptions
- **Gates enforcement**: `complete` blocks feature/bug tasks when required gates fail
- **Mechanical AC always runs**: structured AC with `verification: "test"|"command"` runs at completion **regardless of ceremony level or task type**. This is a gate, not ceremony.
- **AC evidence required**: manual AC needs `--ac-reasoning` with concrete proof (min 50 chars). Each criterion must be addressed with specific evidence (file paths, command output, test results). Filler words like "done" or "verified" are rejected.
- **Skip requires justification**: `skip` requires `--reason` (min 50 chars). Feature/bug tasks also require `--force`.
- **KR auto-update**: completing a task with `origin: "O-XXX"` auto-updates descriptive KR statuses (NOT_STARTED → IN_PROGRESS → ACHIEVED). Numeric KRs via measurement commands. Failures are WARNED, not silent.
- **Contract alignment**: `begin` warns when task instruction doesn't reference upstream `produces` contracts
- **Lean context**: `begin --lean` skips Knowledge, Research, Business Context, Lessons for simple tasks
- **Coverage gate**: `draft-plan --coverage '[...]'` rejects plan if any source requirement has status MISSING. DEFERRED/OUT_OF_SCOPE require reason.
- **Plan context auto-load**: `draft-plan` automatically loads must-guidelines, objectives, knowledge and shows them. It validates that tasks reference proper scopes (matching their origin objective's scopes) and that must-guideline scopes are covered by the plan. `approve-plan` blocks if context errors exist.
- **Plan staleness**: `begin` warns when files in task instruction were modified (committed) since plan approval

## CLI Reference

Full command reference: `docs/CLI-REFERENCE.md`. Key patterns:

```
python -m core.pipeline {init|add-tasks|draft-plan|approve-plan|begin|next|complete|status|context|config|update-task|remove-task|contract} {project} [args]
python -m core.decisions {add|read|update|show|contract} {project} [args]
python -m core.changes {auto|record|read|contract} {project} [args]
python -m core.{lessons|objectives|ideas|guidelines|knowledge|research|ac_templates|gates|domain_modules|decision_checker|git_ops} {subcommand} [args]
```

Use `--help` for full syntax. Use `contract` subcommand for entity JSON format.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/plan {goal}` | Decompose into task graph (draft → approve) |
| `/next` | Get and execute next task |
| `/run [tasks]` | Execute tasks continuously: `/run`, `/run 3`, `/run T-003..T-007` |
| `/task {description}` | Quick-add a single task |
| `/status` | Show current project status |
| `/decide` | Review and resolve open decisions |
| `/ingest` | Register and extract facts from source documentation |
| `/analyze` | Resolve decisions, group requirements into objectives with measurable KR |
| `/change-request` | Handle new/changed requirements during execution |
| `/discover {topic}` | Explore options, assess risks, design architecture |
| `/objective {title}` | Define business objective with measurable key results |
| `/review {task_id}` | Deep code review (critical tasks only) |
| `/compound` | Extract lessons learned |
| `/onboard` | Import brownfield project knowledge |
| `/guideline {text}` / `/guidelines` | Add/manage project guidelines |
| `/idea {title}` / `/ideas` | Add/manage ideas (staging area) |
| `/risk [title\|id] [action]` | Manage risks |
| `/log` | Show full audit trail |
| `/knowledge`, `/research`, `/ac-template` | Manage knowledge, research, AC templates |
| `/objectives` | Manage objectives |
| `/help` | Show all commands |

## Task Properties

When adding tasks, each task supports:
- `id`, `name`, `description`, `instruction` — basic info
- `type` — `feature` (default), `bug`, `chore`, `investigation`
- `acceptance_criteria` — conditions that must be true when DONE. Supports plain strings (manual verification) and structured: `{text, verification: "test"|"command"|"manual", test_path?, command?}`
- `depends_on` — task IDs that must complete first
- `produces` — semantic contract for downstream consumers (e.g., `{"endpoint": "POST /users → 201 {id, email}"}`)
- `exclusions` — task-specific DO NOT rules
- `alignment` — `{goal, boundaries: {must, must_not, not_in_scope}, success}`
- `scopes` — guideline scopes (e.g., `["backend", "database"]`). `general` always included.
- `parallel`, `conflicts_with` — multi-agent coordination
- `blocked_by_decisions` — decision IDs that must be CLOSED before start
- `skill` — path to SKILL.md for structured execution
- `origin` — objective ID (O-NNN). **Required** for feature/bug tasks when objectives exist. Enables KR auto-update.
- `knowledge_ids`, `test_requirements` — optional context

### Validation

- **Planning**: feature/bug tasks MUST have `acceptance_criteria`. Temp IDs (`_1`, `_2`) auto-remap to `T-NNN`.
- **Completion**: gates must pass (mechanical enforcement for feature/bug) + AC verified. Ceremony level auto-detected (MINIMAL/LIGHT/STANDARD/FULL) from task type and diff size. Use `--deferred '[{requirement, reason}]'` to record source doc requirements not covered — auto-creates OPEN decisions.
- **Batch format**: `{"new_tasks": [...], "update_tasks": [...]}` for atomic add + update.

## Workflow

### Default: standalone plan (no source documents)
```
/plan {goal}  ──→  /run  ──→  done
```

### From source documents (MANDATORY sequence — gates enforce this)
```
/ingest ──→ /analyze ──→ /plan --objective O-NNN ──→ /run ──→ verified
```
Skipping `/analyze` BLOCKS `/plan`. Missing `--objective` BLOCKS `draft-plan`.

### For complex work: discover first
```
/objective ──→ /discover ──→ /plan --objective O-NNN ──→ /run ──→ /compound
```

### From documentation: full pipeline
```
/ingest ──→ /analyze ──→ /plan ──→ /run ──→ verified (requirements coverage + KR achievement)
```

### Mid-flight changes
```
/change-request {description}  ──→  impact assessed  ──→  plan updated
```

### For brownfield projects
Run `/onboard` first — discover project, import decisions/conventions, configure gates.

## Rules

- **Use the pipeline.** Every change goes through plan → execute → complete.
- **Changes are auto-recorded** from git at completion. Manual recording only when linking changes to specific decisions mid-task.
- **Record decisions** when deviating from task instruction or choosing between alternatives that affect downstream tasks. Not for every obvious choice.
- **Contracts on first use** — run `contract` the first time you use an entity type in a session.
- **When you find a conflict, surface it** — create an OPEN decision with both sides stated. Do NOT silently pick one interpretation.
- **When unsure, ask** — create an OPEN decision or ask the user directly.
- **Gates are enforced** — required gates must pass before feature/bug tasks can complete. `--force` only works for chore/investigation.

## Current Project

On startup, check for existing projects:
```bash
ls forge_output/ 2>/dev/null
```

If projects exist, show status. Otherwise, wait for `/plan`.
If `.claude/forge.local.md` exists, read it for user preferences.

## Output Location

All Forge state goes to `forge_output/{project}/`:
- `tracker.json` — pipeline state (tasks + draft_plan)
- `decisions.json` — decisions + explorations + risks
- `changes.json` — change records
- `guidelines.json` — project standards
- `lessons.json`, `objectives.json`, `ideas.json`, `knowledge.json`, `research.json`, `ac_templates.json` — optional context

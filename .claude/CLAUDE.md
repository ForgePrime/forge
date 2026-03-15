# Forge — Structured Change Orchestrator

You are operating inside Forge, a change orchestration system.
Every code change you make must be **planned, tracked, reasoned about, and auditable**.

## Core Principle

You do NOT just write code. You:
1. **Align** — build shared understanding before execution (deep-align)
2. **Plan** — decompose the goal into tasks with dependencies
3. **Track** — every task has a status in the pipeline
4. **Decide** — record architectural and implementation decisions with reasoning
5. **Execute** — make changes, recording what you changed and why
6. **Validate** — run tests/checks before marking complete

## Information Flow

```
Objective O-001 "Reduce API response time"         ← NORTH STAR (why)
│  key_results: [KR-1: p95 < 200ms, KR-2: 0 timeouts]
│  scopes: [backend, performance]
│  derived_guidelines: [G-010]
│
├──derives──→ Guideline G-010 "Latency benchmarks"  ← STANDARDS (how to work)
│               derived_from: O-001                    loaded into task context via scopes
│               scope: performance, weight: must
│
├──researched by──→ Research R-001 "Caching options"  ← ANALYSIS (what was found)
│  │                 linked_entity: O-001
│  │                 file: research/deep-explore-caching.md
│  │                 decisions: [D-001, D-002]
│  │
├──advances──→ Idea I-001 "Redis caching"           ← PROPOSALS (what to build)
│  │             advances_key_results: [O-001/KR-1]
│  │             scopes: [backend, performance]  ← inherited from O-001
│  │
│  ├──explored by──→ Decision D-001 (exploration)   ← REASONING (why this way)
│  ├──risk──→ Decision D-002 (risk)                   linked via task_id: I-001
│  │
│  └──committed to──→ Task T-001 "setup-redis"      ← EXECUTION (do it)
│     │                 origin: I-001 (or O-001 if planned from objective)
│     │                 scopes: [backend]
│     │
│     ├──context loads──→ Guidelines (by scopes)
│     │                   Business Context (O-001 + KR progress)
│     │                   Research (from origin idea/objective)
│     │                   Dependency outputs
│     │                   Active risks from I-001
│     │
│     ├──produces──→ Changes (auto-recorded on complete)
│     ├──records──→ Decisions (implementation choices)
│     └──validated by──→ Gates (tests, lint, secrets)
│
└──measured by──→ KR-1 current: 320/200 (61%)       ← OUTCOMES (did it work?)
                  KR-2 current: 5/0 (89%)
                  updated manually via /objectives update

Post-project:
  /compound ──→ Lessons (cross-project learning)
```

### Data flow at task execution (`pipeline context`)

```
Task T-001
  │
  ├─ task.scopes ──→ load Guidelines matching scopes
  │                  + Knowledge matching scopes (additive to explicit IDs)
  │                  + global guidelines (always)
  │
  ├─ task.origin ──→ Idea I-001 or Objective O-001
  │   ├─ idea.advances_key_results ──→ Objective O-001
  │   │   └─ show: title, KR progress, status (Business Context)
  │   └─ Research R-NNN (linked to origin idea/objective)
  │       └─ summary, key_findings, decision_ids
  │
  ├─ task.depends_on ──→ completed tasks
  │   ├─ their Changes (files modified)
  │   └─ their Decisions (choices made)
  │
  ├─ task.origin (I-* or O-*) ──→ active Risk decisions
  │
  └─ task.blocked_by_decisions ──→ must be CLOSED before start
```

### Coverage tracking (3 levels)

```
Planning:   KRs with ≥1 linked Idea  →  "2/3 KRs covered"
Execution:  DONE tasks / total tasks  →  "5/8 tasks done (62%)"
Outcome:    KR current vs target      →  "KR-1: 61%, KR-2: 89%"
```

## How It Works

### Pipeline (task graph)
```
python -m core.pipeline init {project} --goal "..."      Create project
python -m core.pipeline add-tasks {project} --data '...' Add tasks (array or batch format with update_tasks)
python -m core.pipeline draft-plan {project} --data '...' [--idea I-NNN] [--objective O-NNN]  Store draft plan for review
python -m core.pipeline show-draft {project}             Show current draft plan
python -m core.pipeline approve-plan {project}           Approve draft → materialize tasks
python -m core.pipeline update-task {project} --data '{...}' Update existing task
python -m core.pipeline remove-task {project} {task_id}  Remove TODO task
python -m core.pipeline begin {project} [--agent name]   Claim next task + show full context (next + context combined)
python -m core.pipeline next {project} [--agent name]    Get next task (without context)
python -m core.pipeline complete {project} {task_id} [--force] [--reasoning "..."] [--ac-reasoning "..."]  Mark done (auto-records git changes + checks gates + verifies AC)
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

**Auto-recording**: `pipeline complete` now auto-records git changes (committed + uncommitted since task start). Use `--reasoning` to explain why. Manual `changes auto`/`changes record` still work for per-file reasoning or mid-task recording.

### Lessons (compound learning)
```
python -m core.lessons add {project} --data '...'      Record lessons learned
python -m core.lessons read {project}                   View project lessons
python -m core.lessons read-all [--severity X] [--tags "a,b"] [--category X] [--limit N]  View lessons across all projects
python -m core.lessons promote {lesson_id} [--scope X] [--weight X]  Promote lesson to global guideline
python -m core.lessons contract                         See expected format
```

Promoting lessons: `lessons promote L-001 --scope backend --weight must` creates a global guideline from a lesson. Severity maps to weight: critical→must, important→should, minor→may.

### Objectives (business goals with measurable key results)
```
python -m core.objectives add {project} --data '[...]'      Add objectives with key results
python -m core.objectives read {project} [--status X]        Read objectives
python -m core.objectives show {project} {objective_id}      Show details + coverage + progress
python -m core.objectives update {project} --data '[...]'    Update objective/KR progress
python -m core.objectives status {project}                   Coverage dashboard
python -m core.objectives contract add                       Show objective contract
```

Objectives sit above Ideas — they answer "what do we want to achieve?" Ideas answer "how?"
- Key Results: measurable targets (metric + baseline + target + current)
- Ideas link to KRs via `advances_key_results: ["O-001/KR-1"]`
- `scopes`: guideline scopes this objective relates to — ideas can inherit these
- `derived_guidelines`: guideline IDs created BECAUSE of this objective (outbound traceability)
- `assumptions`: explicit hypotheses that must hold (from Theory of Change)
- `appetite`: effort budget — small (days), medium (weeks), large (months) (from Shape Up)
- Status lifecycle: ACTIVE → ACHIEVED | ABANDONED | PAUSED
- On ACHIEVED/ABANDONED: warns about derived guidelines to review
- Coverage tracking: planning (KRs → Ideas), execution (Ideas → Tasks), outcome (KR progress)

### Ideas (staging area — hierarchical, with relations)
```
python -m core.ideas add {project} --data '[...]'                      Add ideas (supports parent_id, relations, scopes, advances_key_results)
python -m core.ideas read {project} [--status X] [--category X] [--parent X]  Read ideas (--parent root for top-level)
python -m core.ideas show {project} {idea_id}                          Show full details (hierarchy, explorations, risks, decisions)
python -m core.ideas update {project} --data '[...]'                   Update status/fields (relations append-merged)
python -m core.ideas commit {project} {idea_id}                        Mark APPROVED → COMMITTED (validates depends_on)
python -m core.ideas contract add                                      Show idea contract
```

- `advances_key_results`: links idea to objective KRs (e.g., `["O-001/KR-1"]`)
- `scopes`: guideline scopes — can be inherited from linked objective

### Guidelines (project standards)
```
python -m core.guidelines add {project} --data '[...]'         Add guidelines (supports derived_from for objective traceability)
python -m core.guidelines read {project} [--scope X] [--weight X]  Read guidelines
python -m core.guidelines update {project} --data '[...]'      Update guideline status
python -m core.guidelines context {project} --scopes "a,b"     Guidelines for LLM context
python -m core.guidelines scopes {project}                     List unique scopes
python -m core.guidelines import {project} --source {other} [--scope X]  Import from another project
python -m core.guidelines contract add                         Show guideline contract
```

- `derived_from`: objective ID this guideline was created because of (e.g., `"O-001"`)
- When an objective is ACHIEVED/ABANDONED, review its derived guidelines
- `guidelines import`: copy guidelines from one project to another (dedup by title, tracks source)

### Knowledge (domain context — K-NNN)
```
python -m core.knowledge add {project} --data '[...]'              Add knowledge objects
python -m core.knowledge read {project} [--status X] [--category X] [--scope X]  Read/filter
python -m core.knowledge show {project} {knowledge_id}             Show details + version history
python -m core.knowledge update {project} --data '[...]'           Update (creates version if content changed)
python -m core.knowledge link {project} --data '{...}'             Link to entity
python -m core.knowledge unlink {project} {knowledge_id} {index}   Remove link by index
python -m core.knowledge impact {project} {knowledge_id}           Impact analysis
python -m core.knowledge contract add                              Show add contract
```

- Categories: domain-rules, api-reference, architecture, business-context, technical-context, code-patterns, integration, infrastructure
- Status lifecycle: DRAFT → ACTIVE → REVIEW_NEEDED → ACTIVE / DEPRECATED → ARCHIVED
- Versioning: content updates create new version entries (change_reason required)
- Impact analysis: scans tracker, ideas, objectives for references to K-NNN
- Tasks and ideas can reference knowledge via `knowledge_ids: ["K-001"]`
- Lessons can be promoted to knowledge via `lessons promote-knowledge`

### Research (structured analysis output — R-NNN)
```
python -m core.research add {project} --data '[...]'                      Add research objects
python -m core.research read {project} [--status X] [--category X] [--entity X]  Read/filter
python -m core.research show {project} {research_id}                      Show details
python -m core.research update {project} --data '[...]'                   Update (status, findings)
python -m core.research context {project} --entity {O-001|I-001}          Research for LLM context
python -m core.research contract {name}                                   Show contract spec
```

- Categories: architecture, domain, feasibility, risk, business, technical
- Status lifecycle: DRAFT → ACTIVE → SUPERSEDED | ARCHIVED
- Links to objectives or ideas via `linked_entity_type` + `linked_entity_id`
- `linked_idea_id`: secondary idea link when primary entity is an objective
- `decision_ids`: D-NNN IDs that originated from this research (bidirectional with `evidence_refs`)
- `file_path`: path to research markdown file (relative to project dir)
- `key_findings`: bullet-point summary of findings
- Created by `/discover`, loaded by `pipeline context` and `/plan`

### AC Templates (reusable acceptance criteria — AC-NNN)
```
python -m core.ac_templates add {project} --data '[...]'                          Add templates
python -m core.ac_templates read {project} [--category X] [--scope X]             Read/filter
python -m core.ac_templates show {project} {template_id}                          Show details
python -m core.ac_templates update {project} --data '[...]'                       Update template
python -m core.ac_templates instantiate {project} {template_id} --params '{...}'  Fill in params
python -m core.ac_templates contract add                                          Show add contract
```

- Categories: performance, security, quality, functionality, accessibility, reliability, data-integrity, ux
- Status lifecycle: PROPOSED → ACTIVE → DEPRECATED
- PROPOSED: candidate from `/compound`, not yet approved — cannot be instantiated
- ACTIVE: approved for use — can be instantiated
- `occurrences`: detection count for PROPOSED templates (incremented when `/compound` finds similar pattern)
- `source_tasks`: task IDs where the pattern was observed
- Parameterized: templates use `{placeholder}` syntax, filled by `instantiate`
- Instantiation returns structured AC: `{text, from_template, params}` — used in task acceptance_criteria
- Usage tracking: `usage_count` incremented on each instantiation

### Gates (validation checks)
```
python -m core.gates config {project} --data '[...]'   Configure test/lint gates
python -m core.gates show {project}                    Show configured gates
python -m core.gates check {project} --task {task_id}  Run all gates
python -m core.gates contract config                   Show gate contract
```

Tip: Configure secret scanning as a gate: `{"name": "secrets", "command": "gitleaks detect --no-git -v", "required": true}`

### Git Workflow (branch, worktree, PR automation)
```
python -m core.git_ops status                    Show branches and worktrees
python -m core.git_ops cleanup {project}         Clean up completed task branches/worktrees
```

**Configuration** (via `pipeline config`):
```json
{
  "git_workflow": {
    "enabled": true,
    "branch_prefix": "forge/",
    "use_worktrees": false,
    "worktree_dir": "forge_worktrees",
    "auto_push": true,
    "auto_pr": true,
    "pr_target": "main",
    "pr_draft": true
  }
}
```

**How it works**:
- `pipeline next` creates a branch `{prefix}{task_id}-{slug}` and optionally a worktree
- `pipeline complete` pushes branch, creates PR (if configured), cleans up worktree
- Branch-only mode (default): checkout branch in main repo — for single-agent work
- Worktree mode (`use_worktrees: true`): creates `forge_worktrees/{task_id}-{slug}/` — for multi-agent parallel work
- Each agent works in its own worktree directory, pipeline commands run from main repo
- `auto_record_changes` is worktree-aware (uses correct cwd for git diff)

**Stored on task**: `branch`, `worktree_path`, `pr_url` — recorded automatically by pipeline

## Slash Commands

### Workflow Commands

| Command | Description |
|---------|-------------|
| `/objective {title}` | Define a business objective with measurable key results (north star) |
| `/objectives [id] [action]` | List/show/manage objectives, update KR progress, coverage dashboard |
| `/idea {title}` | Add an idea to staging area (supports --parent, --relates-to, --advances) |
| `/ideas [id] [action]` | List/show/manage ideas (explore, approve, reject, commit) |
| `/discover {topic\|idea_id}` | Explore options, assess risks, design architecture → creates exploration + risk decisions |
| `/plan {goal\|idea_id}` | Decompose into task graph (two-phase: draft → approve) |
| `/risk [title\|id] [action]` | Manage risks (add type=risk decisions, analyze, mitigate, accept, close) |
| `/guideline {text}` | Add a project guideline (standard, convention, rule) |
| `/guidelines [scope]` | List/manage guidelines |
| `/knowledge [id] [action]` | Manage knowledge objects (domain rules, patterns, technical context) |
| `/research [id] [action]` | Manage research objects (R-NNN structured analysis summaries, linked to objectives/ideas/decisions) |
| `/ac-template [id] [action]` | Manage AC templates (reusable parameterized acceptance criteria) |
| `/status` | Show current project status |
| `/next` | Get and execute next task (includes verification + guidelines check) |
| `/run [tasks]` | Execute tasks continuously: `/run`, `/run 3`, `/run T-003..T-007` |
| `/decide` | Review and resolve open decisions |
| `/review {task_id}` | Deep code review (optional — basic verification built into `/next`) |
| `/log` | Show full audit trail (changes + decisions) |
| `/compound` | Extract lessons learned from project execution |
| `/onboard` | Import brownfield project knowledge into Forge (see `skills/onboard/SKILL.md`) |
| `/task {description}` | Quick-add a task with alignment-driven acceptance criteria |
| `/help` | Show all commands with descriptions and when to use each one |

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
- `knowledge_ids` — list of Knowledge IDs (K-001, etc.) that provide context for this task. Loaded by `pipeline context`.
- `test_requirements` — dict with `unit`, `integration`, `e2e` booleans indicating required test types.
- `alignment` — dict with `{goal, boundaries: {must, must_not, not_in_scope}, success}` — persisted alignment contract from planning. Displayed in `pipeline context` and `print_task_detail`. Derive AC from `alignment.success`.
- `exclusions` — list of task-specific DO NOT rules (e.g., `["DO NOT modify auth.ts", "DO NOT add pagination — that is T-015"]`). Displayed prominently in both `print_task_detail` and `pipeline context`.

### Plan Validation

At `approve-plan`, the following gates apply:
- **AC hard gate**: feature/bug tasks MUST have `acceptance_criteria`. Chore/investigation tasks are exempt.
- **Reference warnings** (advisory): invalid `origin` (I-/O- not found), unknown `scopes`, missing `knowledge_ids` are reported.
- **AC reasoning validation** (advisory): at `complete`, `--ac-reasoning` is checked for per-criterion coverage and PASS/FAIL verdicts.
- **KR reminder**: after `complete`, if the task traces to an objective, KR progress is displayed.

### Temporary IDs (concurrent-safe planning)

Tasks use temporary IDs (`_1`, `_2`, `_3`, ...) during planning. These are auto-remapped
to real `T-NNN` IDs at materialize time (`approve-plan` or `add-tasks`), under a file lock
that prevents race conditions between concurrent planning processes.

- `depends_on` and `conflicts_with` can reference temp IDs within the same batch — they are remapped together.
- Explicit `T-NNN` IDs are still supported (backward compatible) — they are used as-is.
- The ID mapping is printed to stdout after materialization.

**Batch format** for atomic add + update (inserts new tasks AND modifies existing tasks' dependencies in one operation):
```json
{"new_tasks": [{"id": "_1", "name": "new-task", ...}], "update_tasks": [{"id": "T-003", "depends_on": ["_1"]}]}
```
`update_tasks` follows the same contract as `update-task` and can reference temp IDs from `new_tasks`.

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
- Acceptance criteria must be verified with `--ac-reasoning` (if task has AC)
- Use `--force` to bypass these checks when appropriate (e.g., investigation tasks with no code changes)

## Workflow

For brownfield projects (existing codebase):
1. Run `/onboard` — discover project, import decisions/conventions, configure gates
2. Then continue with `/plan {goal}` for specific work

When user gives a goal, **choose the right track**:

### Standard Track (multi-task work)

```
/plan {goal}  ──→  /next|/run  ──→  /compound
  (how)            (execute)        (learn)
```

Use when: 3-8 tasks, medium complexity, clear goal.
Provides: full task graph with dependencies, guidelines per scope, verification, gates.

### Full Track (complex/risky work)

```
/objective ──→ /idea ──→ /discover ──→ /plan ──→ /next|/run ──→ /compound
  (why)        (what)     (assess)     (how)    (execute)      (learn)
```

Use when: 9+ tasks, architectural decisions, high risk, needs exploration.
Provides: everything — objectives, ideas, discovery, risk assessment, full traceability.

### Architecture-first Track (design before implementation)

When the project needs upfront architecture, UI mockups, or technical design before coding:

```
/objective ──→ /discover --full ──→ /knowledge add ──→ /plan ──→ /next|/run
  (why)         (design+assess)     (persist design)   (tasks)   (build)
```

Key difference from Full Track: `/discover` with `deep-architect` IS the design phase.
Discovery findings that should persist as living docs → create Knowledge objects (category: `architecture`).
`/plan` reads Knowledge (Step 2, R9) and assigns `knowledge_ids` to tasks.
`pipeline context` loads Knowledge for each task during execution.

**How design artifacts flow to implementation:**
1. `/discover --full` → Research (R-NNN, snapshot) + Decisions (architecture type)
2. Promote durable findings to Knowledge (K-NNN, living docs) — architecture, API contracts, data models
3. `/plan` assigns `knowledge_ids: [K-001, K-002]` to relevant tasks
4. `/next` loads Knowledge via `pipeline context` (explicit IDs + origin chain)
5. When implementation reveals design issues → `knowledge update` creates new version

No special skills or entity types needed — existing primitives cover the full workflow.

### How to choose

| Signal | Track |
|--------|-------|
| "Fix this bug", "Rename X", "Add a test" | **Standard** (`/task` + `/next`) |
| "Add feature X with Y and Z" | **Standard** (`/plan`) |
| "Design the system first, then build" | **Architecture-first** (`/objective` → `/discover --full` → ...) |
| "We need to redesign the auth system" | **Full** (`/objective` → ...) |
| User explicitly asks for full analysis | **Full** |

### Full Track Details

0. (Optional) Define north star: `/objective {title}` — business goal with measurable KRs
   - Provides "why" context for all downstream work
   - Optionally create derived guidelines from KRs (`derived_from: "O-001"`)
   - Ideas link to KRs via `advances_key_results`
1. Capture as idea: `/idea {title}` — add to staging area (uses deep-align: restatement + questions)
   - Ideas support hierarchy: `/idea {title} --parent I-001` for sub-ideas
   - Ideas support relations: depends_on, related_to, supersedes, duplicates
   - Ideas can advance KRs: `advances_key_results: ["O-001/KR-1"]`
   - Scopes inherited from linked objective
2. Explore: `/discover {idea_id}` — creates exploration + risk decisions (uses deep-align for scope)
   - Status flow: DRAFT → EXPLORING → APPROVED
   - Use `/risk` to track and mitigate identified risks
3. When ready: `/ideas {idea_id} approve` then `/plan {idea_id}`
4. `/plan` creates a **draft plan** — uses deep-align for goal alignment, then review → approve
5. Configure project: `pipeline config` (test_cmd, lint_cmd) and `gates config`
6. Define project guidelines: `/guideline {text}` — coding standards, conventions
7. Run `/next` — get first task (follows `skills/next/SKILL.md`)
8. For each task:
   a. Gather context: `pipeline context` — loads deps + guidelines + risks + **business context from objective**
   b. Record any significant decisions via `decisions add`
   c. Make the code changes
   d. (Optional) Record changes mid-task via `changes auto` for per-file detail
   e. Verify: deep-verify + guidelines compliance (built into `/next` Step 5)
   f. Run gates: `gates check {project} --task {task_id}`
   g. Commit changes via git
   h. Mark task complete via `pipeline complete --reasoning "..."` (auto-records git changes + checks gates)
9. Optionally run `/review {task_id}` for critical tasks
10. Track objective progress: `/objectives O-001 update` — update KR current values
11. When all tasks done, run `/compound` to extract lessons

## Rules

- **NEVER skip the pipeline**. Every change goes through plan -> execute -> record.
- **Record decisions** for any non-trivial choice (architecture, library, pattern, trade-off).
- **Record changes** for every file you create, edit, or delete.
- **reasoning_trace is mandatory** — explain WHY, not just WHAT.
- **Contracts are the source of truth** — run `contract` before producing structured output. Note: `contract` does NOT take a project argument (e.g. `python -m core.guidelines contract add`, NOT `... contract add {project}`).
- **When unsure, create an OPEN decision** — let the human decide.
- **Tests before completion** — run tests/lint before marking a task DONE.
- **Use --force on complete** only for tasks that genuinely have no code changes (e.g., investigation, planning).
- **Use `--data -` with heredoc for complex JSON** — all `--data` parameters support stdin via `--data -`. Use with heredoc to avoid bash quoting issues:
  ```bash
  python -m core.decisions add {project} --data - <<'EOF'
  [{"issue": "it's a test with 'quotes' and $vars"}]
  EOF
  ```
  `<<'EOF'` passes content literally — no escaping needed. Fallback: `--data @file.json` reads from file. If unsure about format, run `contract` first.

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
- `objectives.json` — business objectives with key results
- `knowledge.json` — knowledge objects (domain rules, patterns, context)
- `ac_templates.json` — acceptance criteria templates (reusable, parameterized)
- `research.json` — research objects (R-NNN, structured analysis from /discover)

# Forge — Structured Development Loop for AI Agents

You open a project in VS Code, start Claude Code, and type `/plan Add user authentication`. Forge breaks that into 6 tasks with dependencies, loads project guidelines into context, tracks every decision along the way, runs tests before marking each task done, and records what changed and why — so next time the agent (or you) can pick up exactly where things left off.

> **The problem:** AI agents write code fast but without structure. They forget why a decision was made, skip tests, can't resume after a crash, and make the same mistakes across projects. Forge wraps every code change in a discipline loop: plan, decide, execute, validate, learn.

## Getting Started

```bash
git clone https://github.com/anthropics/forge.git   # or your fork
cd forge
```

Open this folder in VS Code with Claude Code extension. That's it — Forge loads automatically via `.claude/CLAUDE.md`.

Now type a command in Claude Code chat:

```
/do Fix the login timeout bug in auth.py
```

Forge creates a tracked task, executes it, records changes from git, runs validation gates, and marks it done. One command, full traceability.

## How You Actually Use It

### Simple task — just do it

```
/do Rename getUserById to findUser across the codebase
```

The `/do` command is for 80% of daily work: bug fixes, renames, small features. Forge tracks it, records changes, runs gates — but with minimum ceremony.

### Bigger feature — plan first, then execute

```
/plan Add Redis caching to API responses
```

Forge asks clarifying questions, then produces a **draft plan** — a list of tasks with dependencies:

```
Draft plan for "Add Redis caching to API responses":
  T-001 add-redis-connection-config
  T-002 implement-cache-middleware       (depends on T-001)
  T-003 cache-invalidation-on-write      (depends on T-002)
  T-004 add-cache-headers               (depends on T-002)
  T-005 integration-tests               (depends on T-003, T-004)

Approve this plan? (yes/no/edit)
```

You review, adjust if needed, approve. Then execute:

```
/next          ← picks T-001 (first with no blockers), executes it, marks done
/next          ← picks T-002, loads T-001's output as context, executes
/run           ← or just run all remaining tasks continuously
```

Each `/next` automatically:
1. Loads context from completed dependencies
2. Loads project guidelines matching the task's scopes
3. Executes the code changes
4. Runs validation gates (tests, lint)
5. Records changes with reasoning trace
6. Marks the task DONE

### Complex/risky work — the full workflow

For big architectural changes, you want more structure:

```
/objective Reduce API response time to under 200ms
```

This creates a **business objective** with measurable **Key Results** (like OKRs). It's the "why" — everything downstream traces back to it.

```
/idea Redis caching layer
```

An **idea** is a proposal — "what if we did this?" Ideas live in a staging area. You can have multiple competing ideas for the same objective. They don't become tasks until approved.

```
/discover I-001
```

**Discover** explores the idea before you commit. It creates:
- An **exploration decision** — what options exist, what are the trade-offs
- **Risk decisions** — what could go wrong, how severe, how to mitigate

Now you have a clear picture. If the idea looks good:

```
/plan I-001
```

This generates a task plan *from the idea*, with all the context from discovery built in. After approval:

```
/run                    ← execute all tasks
/compound               ← when done, extract lessons learned
```

**`/compound`** looks at the completed project — what patterns emerged, what mistakes were made, what decisions proved right — and records **lessons**. These lessons are available to future projects, so the agent doesn't repeat mistakes.

### From documentation — requirements-driven

When you have specs, PRDs, or any source documentation:

```
/ingest docs/requirements.md
```

**Ingest** reads each document and extracts every fact that matters for implementation — requirements, business rules, tech decisions, guidelines. It assigns trust levels (HIGH/MEDIUM/LOW), detects conflicts between documents, and surfaces implicit assumptions as OPEN decisions.

```
/analyze
```

**Analyze** bridges ingestion and planning. It resolves OPEN decisions, groups requirements into **objectives** with measurable key results, and links every requirement to an objective. After analysis, `/plan` has everything it needs.

```
/plan --objective O-001
```

Now planning has full traceability: every task traces back to a requirement, which traces back to a source document.

### Mid-flight changes

Requirements changed after you started? No problem:

```
/change-request Client added CSV export requirement
```

Forge assesses the impact (Minor/Moderate/Major/Breaking), updates affected tasks and objectives, and keeps the pipeline consistent.

## The Building Blocks

### Objectives — "Why are we doing this?"

```
/objective Reduce API response time
```

Business goals with measurable Key Results. Example:
- **O-001**: "Reduce API response time"
  - KR-1: p95 latency < 200ms (current: 450ms)
  - KR-2: Zero timeout errors per day (current: 12)

Ideas link to KRs (`advances_key_results`), so you always know which goal a piece of work serves. When the objective is achieved or abandoned, Forge reminds you to review derived guidelines.

### Ideas — "What could we build?"

```
/idea Redis caching layer --advances O-001/KR-1
```

Proposals that mature before becoming work. Lifecycle: `DRAFT → EXPLORING → APPROVED → COMMITTED`. Ideas support hierarchy (sub-ideas via `--parent I-001`) and relations (depends_on, related_to, supersedes).

You don't plan directly from ideas — first explore (`/discover`), then approve, then plan. This prevents jumping to implementation before understanding.

### Discover — "What are the risks and options?"

```
/discover I-001
```

Runs structured analysis on an idea:
- **Exploration**: What approaches exist? What are trade-offs? Open questions?
- **Risk assessment**: What could fail? Severity? Mitigation plan?

Results are stored as decisions — they become part of the task context when you later execute.

### Guidelines — "How do we work here?"

```
/guideline "All API endpoints must return structured error responses with error codes" --scope backend --weight must
```

Project-wide standards. Each guideline has a **scope** (backend, frontend, database...) and a **weight**:
- `must` — always loaded into task context, non-negotiable
- `should` — loaded when relevant, expected to follow
- `may` — available on request, nice-to-have

When a task with `scopes: ["backend"]` runs, all `backend` guidelines are automatically injected into the agent's context. The agent sees the rules *before* writing code, not after review.

### Knowledge — "What do we know about this domain?"

```
/knowledge add --data '[{"title": "MEXC API rate limits", "category": "api-reference", "content": "..."}]'
```

Domain context that tasks can reference: API docs, business rules, architectural patterns, integration specs. Versioned — when knowledge changes, Forge tracks what changed and why. Tasks reference knowledge via `knowledge_ids`, and it's loaded into context during execution.

### Decisions — "Why did we choose this?"

Every non-trivial choice gets recorded automatically during task execution. You can also create them explicitly:

```
/decide
```

Shows all OPEN decisions and lets you resolve them. Three types:
- **Standard**: architecture, library choice, naming convention, trade-off
- **Exploration**: options and findings from `/discover`
- **Risk**: severity + likelihood + mitigation plan

Tasks can be **blocked by decisions** — they won't start until the decision is CLOSED. This prevents coding before the architecture is agreed on.

### Compound & Lessons — "What did we learn?"

```
/compound
```

Run after a project is done. Forge analyzes completed tasks, decisions, and changes to extract **lessons**: patterns that worked, mistakes to avoid, decisions that proved right or wrong. Lessons carry severity (critical/important/minor) and can be **promoted to guidelines** for future projects:

```python
python -m core.lessons promote L-001 --scope backend --weight should
```

This is the learning loop — experience from project A improves the rules for project B.

## Contracts — The AI/Python Handshake

Every entity (task, decision, guideline...) has a **contract** — the exact JSON schema it expects. Example:

```bash
python -m core.pipeline contract add-tasks
```

This prints the schema. Contracts exist for two reasons:

1. **The agent sees the contract before generating data** — no guessing what fields exist, no hallucinated properties
2. **Python validates output against the contract** — if the LLM produces invalid JSON, the operation fails with a clear error, not corrupt state

Python handles I/O and validation. The LLM handles judgment. The contract is where they meet.

## Skills — Reusable Agent Procedures

Skills are structured SKILL.md files that guide the agent through multi-step procedures. They define steps, verification criteria, tool permissions, and scope transparency (what the skill does NOT cover).

Built-in skills power the slash commands:

| Command | Skill | What It Does |
|---------|-------|-------------|
| `/plan` | `plan` | Decompose goal into dependency DAG |
| `/next` | `next` | Execute task with context, guidelines, verification |
| `/discover` | `discover` | Explore options and assess risks |
| `/ingest` | `ingest` | Register docs, extract structured facts, detect conflicts |
| `/analyze` | `analyze` | Resolve decisions, group requirements into objectives |
| `/change-request` | `change-request` | Handle mid-flight requirement changes |
| `/review` | `review` | 6-perspective code review |
| `/onboard` | `onboard` | Import existing project knowledge |

You can create your own skills, lint them, promote DRAFT → ACTIVE, and sync them across environments via git.

## Validation Gates

```
/do Configure test gates for this project
```

Or directly:

```bash
python -m core.gates config myproject --data '[
  {"name": "test", "command": "pytest", "required": true},
  {"name": "lint", "command": "ruff check .", "required": true},
  {"name": "secrets", "command": "gitleaks detect --no-git -v", "required": true}
]'
```

Gates run automatically before a task is marked DONE. Required gates block completion until they pass. This prevents "it compiles, ship it" — the agent must fix test failures before moving on.

## For Existing Projects

```
/onboard ./my-existing-project
```

Forge scans the codebase, discovers conventions, imports architectural decisions, and sets up guidelines. Then you can plan work on top of it:

```
/plan Add payment processing to the checkout flow
```

## Multi-Agent

Multiple agents can work on the same project simultaneously:

```bash
python -m core.pipeline next myproject --agent alice
python -m core.pipeline next myproject --agent bob
```

Two-phase claiming prevents race conditions. `conflicts_with` on tasks prevents two agents from editing the same files at once.

## All Commands

| Command | Purpose |
|---------|---------|
| `/do {task}` | Quick — one task, full traceability, minimum ceremony |
| `/plan {goal}` | Decompose into tasks with dependencies |
| `/objective {title}` | Define business goal with measurable KRs |
| `/idea {title}` | Capture a proposal |
| `/discover {topic}` | Explore options and risks |
| `/guideline {text}` | Set a project standard |
| `/knowledge` | Manage domain context |
| `/task {desc}` | Quick-add a single task |
| `/next` | Execute next ready task |
| `/run` | Execute all tasks continuously |
| `/ingest [path]` | Register and extract facts from documentation |
| `/analyze` | Resolve decisions, create objectives with KR |
| `/change-request {desc}` | Handle new/changed requirements mid-execution |
| `/decide` | Resolve open decisions |
| `/review {id}` | Deep code review |
| `/status` | Dashboard + progress |
| `/log` | Full audit trail |
| `/compound` | Extract lessons from completed work |
| `/onboard {path}` | Import existing project |
| `/help` | Show all commands |

## State

All state lives in `forge_output/{project}/` as JSON files. No database. No migrations. Version-controllable with git.

| File | What's In It |
|------|-------------|
| `tracker.json` | Task graph — DAG with dependencies and statuses |
| `decisions.json` | Every decision with reasoning, alternatives, provenance |
| `changes.json` | File changes with reasoning traces |
| `guidelines.json` | Project standards by scope and weight |
| `objectives.json` | Business goals and Key Result progress |
| `ideas.json` | Proposals in various lifecycle stages |
| `knowledge.json` | Domain context (versioned) |
| `lessons.json` | Cross-project learning |

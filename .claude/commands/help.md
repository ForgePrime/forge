# /help

Show all Forge commands with descriptions and when to use each one.

## Output

Print the following guide:

---

## Forge Commands

### Business Goals & Planning

| Command | When to use |
|---------|-------------|
| `/objective {title}` | Define a business goal with measurable key results — the "north star" for work. |
| `/objectives [id] [action]` | See objectives, update KR progress, coverage dashboard. |
| `/idea {title}` | You have a new idea — capture it before it's lost. Link to KRs with `advances_key_results`. |
| `/ideas [id] [action]` | You want to **see or manage** existing ideas. Plural = **list/show/act**. |
| `/discover {topic\|idea_id}` | Before planning — explore options, risks, feasibility. Creates decisions. |
| `/plan {goal\|idea_id}` | Ready to implement — decompose into tasks. Creates draft → review → approve. |

### Executing

| Command | When to use |
|---------|-------------|
| `/task {description}` | Quick-add a single task to the pipeline. Asks alignment questions to generate proper acceptance criteria. Use `--quick` to skip alignment. |
| `/next` | Get and execute the next available task (one at a time, with full verification). |
| `/run [tasks]` | Execute tasks continuously without stopping between them. `/run` = all, `/run 3` = three, `/run T-003..T-007` = range. |
| `/status` | See where you are — project progress, current task, what's done/remaining. **Start here when resuming work.** |

### Decision & Risk Management

| Command | When to use |
|---------|-------------|
| `/decide` | There are open decisions that need human input. Review and resolve them. |
| `/risk [title\|id] [action]` | Track, analyze, mitigate, or accept project risks. |

### Standards & Quality

| Command | When to use |
|---------|-------------|
| `/guideline {text}` | Add a new coding standard or convention. Singular = **add one**. |
| `/guidelines [scope]` | See or manage existing guidelines. Plural = **list/manage**. |
| `/review {task_id}` | Deep code review for critical tasks. Optional — basic verification is built into `/next`. |

### Audit & Learning

| Command | When to use |
|---------|-------------|
| `/log` | See full audit trail: changes, decisions, timeline. |
| `/compound` | After project completion — extract lessons learned for future use. |

### Documentation Pipeline

| Command | When to use |
|---------|-------------|
| `/ingest [path]` | Register source documents, extract structured facts, detect conflicts and assumptions. |
| `/analyze` | After ingestion — resolve decisions, group requirements into objectives with measurable KR. |
| `/change-request {desc}` | During execution — new/changed requirements arrived, assess impact and update plan. |

### Special

| Command | When to use |
|---------|-------------|
| `/onboard` | Importing an existing (brownfield) project into Forge for the first time. |

### Common Confusions

- **`/objective` vs `/objectives`** — singular **defines** a new objective, plural **lists/manages** existing ones
- **`/idea` vs `/ideas`** — singular **adds** one idea, plural **lists/manages** existing ideas
- **`/guideline` vs `/guidelines`** — same pattern: singular adds, plural manages
- **`/objective` vs `/idea`** — objective = "what to achieve" (measurable), idea = "how to achieve it" (proposal)
- **`/next` vs `/run`** — `/next` does one task with full control, `/run` does many continuously
- **`/status` vs `/log`** — `/status` is a quick dashboard, `/log` is the full audit trail
- **`/review` vs `/next`** — `/next` includes basic verification; `/review` is a deep optional audit

### Choose Your Track

**Standard** (single or multi-task work):
```
/plan {goal} → /run → /compound
```

**From documentation** (requirements-driven):
```
/ingest → /analyze → /plan → /run → /compound
```

**Full** (complex/risky work):
```
/objective → /idea → /discover → /decide → /plan → /run → /compound
```

**Mid-flight changes**:
```
/change-request {description} → impact assessed → plan updated
```

When in doubt, start with `/task`. Escalate to `/plan` if it gets complex.

# /run $ARGUMENTS

Execute tasks from the pipeline continuously, without stopping between tasks.

## Arguments

$ARGUMENTS can be combined:

| Form | Meaning | Example |
|------|---------|---------|
| (empty) | Run all TODO tasks in dependency order | `/run` |
| `N` | Run at most N tasks, then stop | `/run 3` |
| `T-003` | Run task T-003 (and any unfinished dependencies first) | `/run T-003` |
| `T-003..T-007` | Run tasks T-003 through T-007 (and any unfinished dependencies) | `/run T-003..T-007` |
| `T-003,T-005,T-008` | Run exactly these tasks (and any unfinished dependencies) | `/run T-003,T-005,T-008` |
| `--agent {name}` | Identify as named agent (multi-agent mode) | `/run --agent alice` |

Arguments combine: `/run T-003..T-007 --agent alice`

## Task Selection Logic

1. **No task IDs given** — run all TODO tasks in dependency order (same as calling `/next` in a loop)
2. **Single task ID** (`T-003`) — check its dependencies. If any dependency is not DONE, execute those first (in order), then execute T-003.
3. **Range** (`T-003..T-007`) — collect T-003, T-004, T-005, T-006, T-007. For each, resolve unfinished dependencies. Build execution order respecting the DAG.
4. **List** (`T-003,T-005,T-008`) — collect exactly those tasks. Resolve unfinished dependencies for each. Build execution order.
5. **Count limit** (`3`) — run at most 3 tasks from the available set, then stop.

**Dependency resolution:** If you request T-005 but T-003 (its dependency) is still TODO, execute T-003 first automatically. Do NOT ask — just do it and note: `Resolving dependency: T-003 required by T-005.`

**Already DONE tasks:** If a requested task is already DONE, skip it silently. If ALL requested tasks are DONE, report that and stop.

## Instructions

You are in CONTINUOUS EXECUTION MODE. This means:

1. **Do NOT stop between tasks.** After completing one task, immediately get the next.
2. **Do NOT ask "what should I do next?" or "shall I continue?"** — just continue.
3. **Do NOT summarize after each task.** Brief status line only: `Completed T-001. Moving to T-002.`
4. **DO stop if:**
   - A task FAILS and you cannot fix it
   - A required gate fails and you cannot fix it after one retry
   - You create an OPEN decision that genuinely needs human input (not routine choices)
   - All requested tasks are DONE
   - You've reached the count limit (if specified)

## Execution Loop

```
1. Determine target tasks from $ARGUMENTS
2. Resolve all dependencies → build ordered execution list
3. Filter out already DONE tasks
4. Print: "Starting run. Tasks to execute: T-001, T-003, T-005 (N total)"

WHILE execution list not empty:
  5. Take next task from list
  6. Execute per skills/next/SKILL.md (Steps 1-6)
  7. On completion → print one-line status
  8. GOTO 5

9. Print summary
```

## What to print

- Start: `Starting run. Project: {project}. Tasks: T-001, T-003, T-005 (3 total)`
- Dependency: `Resolving dependency: T-001 required by T-003.`
- Per task: `[T-001] setup-database — DONE (2 decisions, 3 files changed)`
- Skip: `[T-002] already DONE, skipping.`
- On failure: `[T-003] implement-auth — FAILED: {reason}. Stopping.`
- End: `Run complete. {done}/{total} tasks finished. Use /status for details.`

## Rules

- All Forge traceability rules still apply (decisions, changes, gates, commits)
- Do NOT skip gates or validation to go faster
- Do NOT reduce quality of reasoning traces to save time
- If a task has a `skill` field pointing to a SKILL.md, follow THAT skill instead of generic next

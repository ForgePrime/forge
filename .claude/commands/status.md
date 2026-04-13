# /status $ARGUMENTS

Show the current state of all Forge projects.

## Arguments

| Form | Meaning |
|------|---------|
| (no args) | Compact status — quick dashboard |
| `--full` | Full status with open decisions, changes, details |

## Procedure

1. List all projects:
```bash
ls forge_output/ 2>/dev/null
```

If no projects exist, inform the user and suggest using `/do {task}` or `/plan {goal}` to start.

### Compact mode (default)

2. For each project, show a concise summary (max 15 lines total):

```bash
python -m core.pipeline status {project}
```

Present as:
```
## {project}: {goal}
Tasks: {done}/{total} ({pct}%) | Open decisions: {N} | Risks: {N}
Next: {task_id} — {task_name}
```

### Full mode (`--full`)

2. For each project directory found, show its full status:
```bash
python -m core.pipeline status {project}
```

3. Show open decisions:
```bash
python -m core.decisions read {project} --status OPEN
```

4. Show change summary:
```bash
python -m core.changes summary {project}
```

5. Show active risks:
```bash
python -m core.decisions read {project} --type risk --status OPEN
```

# /objectives $ARGUMENTS

View and manage business objectives.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| _(empty)_ | List all objectives with KR progress | `/objectives` |
| `{id}` | Show objective details + coverage analysis | `/objectives O-001` |
| `{id} update` | Update KR current values (progress tracking) | `/objectives O-001 update` |
| `dashboard` | Coverage dashboard across all objectives | `/objectives dashboard` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

2. Parse arguments and route:

### List all (no arguments)
```bash
python -m core.objectives read {project}
```

### Show details (`/objectives O-001`)
```bash
python -m core.objectives show {project} {objective_id}
```
This shows: KR progress bars, linked Ideas, planning coverage, execution progress, outcome progress.

### Update KR progress (`/objectives O-001 update`)

Ask the user for current values of key results:
```
O-001 "Reduce API response time" — update Key Results:

KR-1: p95 response time (ms) — baseline: 850, target: 200, current: 850
  → What's the current value?

KR-2: timeout errors per day — baseline: 47, target: 0, current: 47
  → What's the current value?
```

Then update:
```bash
python -m core.objectives update {project} --data '[{
  "id": "{objective_id}",
  "key_results": [
    {"id": "KR-1", "current": {new_value}},
    {"id": "KR-2", "current": {new_value}}
  ]
}]'
```

### Dashboard (`/objectives dashboard`)
```bash
python -m core.objectives status {project}
```

Shows all objectives with:
- [+] / [-] per KR indicating if Ideas address it
- Progress bars and percentages
- Task completion stats
- Planning coverage (KRs with linked Ideas)
- Outcome progress (average KR achievement)

3. After showing, suggest relevant actions:
   - Uncovered KRs? → `/idea {title}` to propose solutions
   - All KRs at 100%? → Suggest marking ACHIEVED: `/objectives O-001 update` with status
   - Stale objectives? → Suggest reviewing assumptions

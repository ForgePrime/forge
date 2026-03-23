# /change-request $ARGUMENTS

Handle new or changed requirements during execution — ingest changes, assess impact, update objectives and plan.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| `{description}` | Describe what changed | `/change-request client added export to CSV requirement` |
| `{path}` | New/updated document to ingest | `/change-request docs/updated-spec.md` |
| `drop {K-NNN}` | Drop a requirement from scope | `/change-request drop K-005` |

## When to Use

- New document added during execution
- Existing requirement changed (updated spec, client feedback)
- Scope change (feature added or dropped)
- Discovered requirement during implementation

## Instructions

Read and follow the procedure in `skills/change-request/SKILL.md`.

Key points:
- Assess impact level: Minor (update AC), Moderate (add tasks), Major (new objective), Breaking (reset + re-plan)
- Record change decision as D-NNN
- Update affected tasks, objectives, and coverage
- Verify pipeline integrity after changes

The change is: $ARGUMENTS

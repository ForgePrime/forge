# /idea $ARGUMENTS

Add an idea to the staging area for exploration before planning.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| `{title}` | Quick add with title | `/idea Add Redis caching to API` |
| `{title} --priority HIGH` | Add with priority | `/idea Fix auth module --priority HIGH` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

If no project exists, create one:
```bash
python -m core.pipeline init {slug} --goal "Project workspace"
```

2. Check the contract:
```bash
python -m core.ideas contract add
```

3. Create the idea from the user's input. Ask for description if only title given.

```bash
python -m core.ideas add {project} --data '[{
  "title": "{from arguments}",
  "description": "{what and why}",
  "category": "{feature|improvement|experiment|migration|refactor|infrastructure}",
  "priority": "{HIGH|MEDIUM|LOW}",
  "tags": ["{relevant tags}"]
}]'
```

4. Present the created idea and suggest next steps:
   - `/discover {idea_id}` — explore feasibility, risks, architecture
   - `/ideas` — see all ideas
   - If user is confident: update to ACCEPTED and `/plan {idea_id}`

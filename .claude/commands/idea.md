# /idea $ARGUMENTS

Add an idea to the staging area for exploration before planning.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| `{title}` | Quick add with title | `/idea Add Redis caching to API` |
| `{title} --priority HIGH` | Add with priority | `/idea Fix auth module --priority HIGH` |
| `{title} --parent I-001` | Add as sub-idea | `/idea Signal Generator --parent I-001` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

If no project exists, create one:
```bash
python -m core.pipeline init {slug} --goal "Project workspace"
```

2. **Align** (light alignment per `skills/deep-align/SKILL.md`):

   a. **Restate** the user's idea in one sentence: "You want X so that Y."
      Get confirmation. If the restatement is wrong, the idea will be wrong.

   b. **Ask 1-2 targeted questions** — only where you'd have to guess:
      - Scope unclear? → "Does this include X or just Y?"
      - Priority ambiguous? → "Is this blocking something or nice-to-have?"
      - Category unclear? → "Is this a new feature or improvement to existing?"
      - If the title is self-explanatory and user gave context, skip questions.

   c. **Check if objectives exist** — if so, ask which KR(s) this idea advances:
      ```bash
      python -m core.objectives read {project}
      ```
      If objectives exist, ask: "Does this idea advance any of these Key Results?"
      If yes, set `advances_key_results: ["O-001/KR-1"]` and **inherit the objective's
      scopes** as a starting point for the idea's `scopes` field (user can adjust).

   d. If user says "just add it" or `--quick` — skip questions, but flag your
      top assumption in the description (e.g., "Assumed scope: backend only").

3. Check the contract:
```bash
python -m core.ideas contract add
```

4. Create the idea using confirmed understanding from alignment:

```bash
python -m core.ideas add {project} --data '[{
  "title": "{from arguments}",
  "description": "{what and why — informed by alignment}",
  "category": "{feature|improvement|experiment|migration|refactor|infrastructure}",
  "priority": "{HIGH|MEDIUM|LOW}",
  "tags": ["{relevant tags}"],
  "parent_id": "{parent idea ID or omit for root}",
  "relations": [{"type": "depends_on|related_to|supersedes|duplicates", "target_id": "I-NNN"}],
  "advances_key_results": ["{O-NNN/KR-N if linked to objective}"],
  "scopes": ["{inherited from objective + user additions}"]
}]'
```

5. Present the created idea and suggest next steps:
   - `/discover {idea_id}` — explore feasibility, risks, architecture
   - `/ideas` — see all ideas
   - `/ideas {idea_id} children` — if this is a parent, see sub-ideas
   - If user is confident: `/ideas {idea_id} approve` then `/plan {idea_id}`

## Alignment Reference

This command uses **light alignment** from `skills/deep-align/SKILL.md`:
- Always restate before creating
- Ask only where guessing wrong would produce a bad idea
- Skip questions for self-explanatory requests or `--quick`

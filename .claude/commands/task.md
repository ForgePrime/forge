# /task $ARGUMENTS

Quickly add a task to the current project's pipeline, using alignment to generate proper acceptance criteria.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| `{description}` | Add task with alignment | `/task add rate limiting to API endpoints` |
| `{description} --quick` | Add without alignment (trust the description) | `/task fix typo in README --quick` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

If no project exists, tell the user to run `/plan` first.

2. **If `--quick` is NOT set** — run a mini deep-align:

   a. **Restate**: "You want to add a task: {one sentence summary}. Correct?"

   b. **Ask only what's unclear** (group in one message):
      - What files/areas will this touch? (→ informs `scopes`)
      - What does "done" look like concretely? (→ informs `acceptance_criteria`)
      - How will you verify it works? (→ informs testable AC)
      - What is NOT in scope? (→ informs boundary in description)
      - Does this depend on any existing task? (→ informs `depends_on`)

   c. From the answers, generate acceptance criteria using the 4-source method:
      1. **User's answer** — what they said "done" looks like
      2. **Task output** — what artifact exists after? (file, endpoint, test)
      3. **Integration** — how does this connect to existing code? (contract, import, data shape)
      4. **Boundary** — "Does NOT {X}" for ambiguous scope edges

3. **If `--quick` IS set** — infer acceptance criteria from the description. Flag your top 2 assumptions.

4. Check the contract:
```bash
python -m core.pipeline contract add-tasks
```

5. Add the task:
```bash
python -m core.pipeline add-tasks {project} --data '[{
  "name": "{slug-from-title}",
  "description": "{full description}",
  "type": "{feature|bug|chore|investigation}",
  "acceptance_criteria": ["{criterion 1}", "{criterion 2}", ...],
  "depends_on": ["{T-NNN if any}"],
  "scopes": ["{relevant scopes}"]
}]'
```

6. Confirm what was added:
```bash
python -m core.pipeline status {project}
```

## Rules

- Acceptance criteria must be **concrete and testable** — avoid vague words: "handles", "ensures", "properly", "robust", "correctly", "works"
- Each criterion must be verifiable by reading code, running a command, or observing output — if you cannot describe HOW to check it, rewrite it
- If the task is trivial (typo fix, one-liner), 1-2 criteria is enough
- If the task is complex, ask before assuming scope — per global guideline G-002
- Always check if the task duplicates or overlaps with existing tasks first

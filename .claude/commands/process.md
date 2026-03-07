# /process $ARGUMENTS

Execute an external plugin skill from the Forge plugin registry.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| (empty) | List all available plugin skills | `/process` |
| `{skill-name}` | Execute that skill | `/process deep-verify` |
| `{skill-name} {context}` | Execute skill with context | `/process deep-risk the authentication module` |

## Procedure

### If no arguments (list mode):

```bash
python -m core.plugins list
```

If no plugins found, tell the user how to configure:
```bash
python -m core.plugins add-path /path/to/skill-pack
python -m core.plugins scan
```

### If skill name given (execute mode):

1. **Resolve the skill**:
```bash
python -m core.plugins show {skill-name}
```
This returns the full path to SKILL.md and references directory.

2. **Read the SKILL.md** at the returned path.

3. **If the skill has a references/ directory**, note the path — you may need to read
   reference files during execution (e.g., `references/patterns.md`, `references/scoring.md`).

4. **Follow the SKILL.md procedure** exactly as written.
   - The skill is external — it does NOT know about Forge pipeline, decisions, or changes.
   - You are the bridge: use Forge to record any decisions or findings that result from
     the skill execution.

5. **After execution**, if inside an active Forge project:
   - Record significant findings as decisions: `decisions add {project} --data '...'`
   - If the skill produced a verdict or assessment, record it as a lesson:
     `lessons add {project} --data '...'`

## Integration with Forge Pipeline

When `/process` is invoked during an active task (task is IN_PROGRESS):
- The plugin skill execution is **part of that task's work**
- Findings become decisions linked to the current task_id
- The plugin skill's output is context for the task, not a separate activity

When `/process` is invoked outside a task:
- Use task_id `"REVIEW"` for findings recorded as decisions
- Results are standalone — no pipeline linkage needed

## Rules

- Plugin skills are READ-ONLY from Forge's perspective — they don't modify Forge state directly
- Forge records the outcomes (decisions, lessons) — the bridge is always Forge
- If a plugin skill requires tools not available (e.g., WebSearch), note the limitation
- Never modify plugin skill files — they are external and may be updated independently

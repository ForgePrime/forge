---
name: task-executor
description: "Guides task execution with AC verification, decision recording, and change tracking"
version: "1.0.0"
entity-types: [task]
contract-refs: [pipeline/add-tasks, pipeline/update-task]
---

# Task Executor

Guide the LLM through structured task execution within Forge's pipeline.

## When to Use

- User is working on a specific task
- User needs help understanding task requirements
- User wants to verify acceptance criteria before completion

## Procedure

1. **Load context**: Review the task's description, instruction, and acceptance criteria.
2. **Check dependencies**: Ensure all `depends_on` tasks are DONE.
3. **Check decision blocks**: Ensure all `blocked_by_decisions` are CLOSED.
4. **Execute**: Follow the task instruction. If a `skill` field exists, follow that skill instead.
5. **Record decisions**: For any non-trivial choice, create a decision record.
6. **Verify AC**: Check each acceptance criterion is met. Document evidence.
7. **Record changes**: Use `changes auto` or let `pipeline complete` auto-record.
8. **Complete**: Mark task DONE with reasoning and AC verification.

## Output Format

Use the `pipeline/add-tasks` contract for task creation and `pipeline/update-task` for updates. Fetch contracts via:
```
GET /api/v1/contracts/pipeline/add-tasks
GET /api/v1/contracts/pipeline/update-task
```

## AC Verification Pattern

For each acceptance criterion, provide structured evidence:
```
AC N: [criterion text] -- PASS|FAIL: [concrete evidence]
```

Pass `--ac-reasoning` with this evidence when completing:
```bash
python -m core.pipeline complete {project} {task_id} --reasoning "..." --ac-reasoning "AC1: ... -- PASS: ..."
```

## Quality Checklist

- All acceptance criteria addressed with evidence
- Decisions recorded for non-trivial choices
- Changes committed to git before completion
- Gates pass (tests, lint) if configured
- Task scoped guidelines were followed

## Tips

- Use `--force` on `pipeline complete` only for tasks with no code changes
- If a task FAILS, set `failed_reason` explaining why
- For investigation tasks, record findings as decisions
- Check `pipeline context {project} {task_id}` for full dependency and guideline context

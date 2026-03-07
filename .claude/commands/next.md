# /next

Get the next task from the pipeline and start working on it.

## Procedure

1. Find the active project:
```bash
ls forge_output/ 2>/dev/null
```
If multiple projects, use the most recently updated one. If none, tell the user to run `/plan` first.

2. Get the next task:
```bash
python -m core.pipeline next {project}
```

3. If a task is returned:
   a. Read and understand the task description and instruction
   b. If the task has a `skill` path, read that SKILL.md file
   c. Check for relevant open decisions:
      ```bash
      python -m core.decisions read {project} --task {task_id}
      ```
   d. Begin execution following the task instruction
   e. For any significant design/implementation choice, record a decision:
      ```bash
      python -m core.decisions add {project} --data '[{...}]'
      ```
   f. After making code changes, use `changes diff` to auto-detect what changed:
      ```bash
      python -m core.changes diff {project} {task_id}
      ```
      Review the suggested change records, enrich with `reasoning_trace` and `decision_ids`,
      then record:
      ```bash
      python -m core.changes record {project} --data '[{...enriched records...}]'
      ```
   g. Run relevant tests/lint to validate
   h. Mark complete:
      ```bash
      python -m core.pipeline complete {project} {task_id}
      ```
   i. Automatically proceed to the next task (loop back to step 2)

4. If pipeline is complete, show final status and change summary.

5. If pipeline is blocked (failed task), show the failure and suggest fixes.

## Important

- NEVER skip recording decisions and changes
- If a task is too large, consider breaking it into subtasks via register-subtasks
- If you hit a blocker, use `fail` with a reason rather than silently stopping

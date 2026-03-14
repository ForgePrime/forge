---
name: next
id: SKILL-NEXT
version: "1.1"
description: "Get the next task from the pipeline and execute it with full traceability."
---

# Next (Execute Task)

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-NEXT |
| Version | 1.1 |
| Description | Pick the next available task, gather context, execute, validate, record. |

## Success Criteria

- Task instruction fully executed
- All significant decisions recorded with reasoning
- Changes verified: deep-verify passed, guidelines compliance checked
- Minor findings fixed in-place, major findings created as new TODO tasks
- Validation gates pass (or failures explicitly acknowledged)
- Task marked DONE only after verification AND validation

---

## Overview

Execute the next available task from the pipeline with full traceability.
Every code change is recorded, every decision is logged, and validation
gates must pass before completion.

## Prerequisites

- A project exists with tasks in the pipeline
- At least one task is TODO with all dependencies met

---

### Step 1 — Begin (claim task + load context)

```bash
python -m core.pipeline begin {project}
```

This single command:
- Claims the next available task (or resumes an IN_PROGRESS one)
- Prints the full execution context: dependencies, guidelines, knowledge, research, business context, active risks, test requirements

**Follow all MUST guidelines strictly. Follow SHOULD guidelines unless there's a documented reason not to.**

If no task is available, the output explains why (all done, blocked, failed). Follow its guidance.

If a SKILL path is specified on the task, read that SKILL.md and follow
its procedure instead of this generic flow.

**If task has origin from an idea** (origin starts with `I-`), optionally load the idea for extra exploration context:
```bash
python -m core.ideas show {project} {origin_id}
```

**Read the codebase** before writing any code:
- Read the task instruction carefully
- Open and read every file mentioned in the instruction
- Understand the existing code patterns before changing anything

> **Advanced**: `pipeline next` and `pipeline context` are still available as separate commands if needed.

---

### Step 2 — Execute with Decisions

Implement the task following its instruction.

For every significant choice during implementation, load the contract and record per its spec:

```bash
python -m core.decisions contract add
python -m core.decisions add {project} --data '[...]'
```

Use `type: "implementation"`, `task_id: "{task_id}"`, and include `reasoning` and `alternatives`.

**What counts as a significant decision:**
- Choosing between two valid approaches
- Deviating from the task instruction
- Adding something not explicitly requested
- Security-relevant choices
- Performance trade-offs

**What does NOT need a decision:**
- Following the only obvious path
- Standard library usage
- Formatting/style (follow existing patterns)

---

### Step 3 — Record Changes (optional mid-task)

Changes are **auto-recorded at completion** (Step 6) from git diff. This step
is only needed if you want per-file reasoning traces or to link specific
changes to decisions mid-task.

For detailed per-file recording, load the contract first:
```bash
python -m core.changes contract
python -m core.changes record {project} --data '[...]'
```

Already-recorded files are skipped by auto-recording (no duplicates).

---

### Step 4 — Verify Changes

Before validation gates, verify the quality and correctness of your changes.

**a. Guidelines compliance check:**

Review the guidelines loaded in Step 1 context. For each MUST guideline, verify your changes comply. For SHOULD guidelines, verify where practical.

If a guideline was violated:
- **Minor fix** (< 5 minutes): fix it now
- **Major fix** (new feature/refactor needed): create a follow-up TODO task via `python -m core.pipeline add-tasks`, with `type: "chore"` and `depends_on: ["{task_id}"]`.
Record the violation as a decision with `type: "convention"`.

**b. Deep-verify (for non-trivial changes):**

For tasks that create or modify significant logic (not simple config/docs changes), run a lightweight verification using the deep-verify procedure (`skills/deep-verify/SKILL.md`):

- Scope the verification to FILES CHANGED in this task only
- Check for: logical errors, missed edge cases, security issues, inconsistencies with existing code
- Scoring: CRITICAL findings must be fixed. IMPORTANT findings should be fixed or tracked. MINOR findings are optional.

If deep-verify finds issues:
- **Fix immediately** if the fix is small and within scope
- **Create TODO task** if the fix is large or out of scope
- **Record** all findings and fixes as decisions

**Skip deep-verify when:** task is trivial (config change, typo fix, docs-only), or task type is `chore`.

**c. Acceptance Criteria checklist:**

If the task has `acceptance_criteria`, go through each criterion explicitly:

```
AC Verification for {task_id}:
1. [criterion text] — [PASS/FAIL: brief evidence]
2. [criterion text] — [PASS/FAIL: brief evidence]
...
```

All criteria must PASS before proceeding. If any criterion FAILS:
- **Fixable now**: fix it, update changes
- **Not fixable**: fail the task with `pipeline fail` explaining which criterion cannot be met

Compose the AC reasoning summary for Step 6 (used in `--ac-reasoning`).

---

### Step 5 — Validate

Run configured validation gates:

```bash
python -m core.gates check {project} --task {task_id}
```

If gates fail:
- **Required gate fails**: Fix the issue, re-run gates
- **Advisory gate fails**: Note the failure, proceed if acceptable
- **No gates configured**: Skip (but warn)

If git is available and validation passes, commit:

```bash
git add -A && git commit -m "descriptive message"
```

---

### Step 6 — Complete

```bash
python -m core.pipeline complete {project} {task_id} --reasoning "What was done and why" --ac-reasoning "AC verification: 1. [criterion]: met because [evidence]. 2. ..."
```

If the task has acceptance criteria, `--ac-reasoning` is required (from Step 4c).

This auto-records any unrecorded git changes (committed + uncommitted since task start).

Then immediately proceed to the next task (loop back to Step 1).

---

### On Failure

If the task cannot be completed:

1. Record what was attempted and why it failed
2. Mark the task as FAILED:
```bash
python -m core.pipeline fail {project} {task_id} --reason "Clear description of what failed"
```
3. Do NOT silently stop — always mark the failure

If a task is too large, break it into subtasks:
```bash
python -m core.pipeline register-subtasks {project} {task_id} --data '[...]'
```

---

## Error Handling

| Error | Action |
|-------|--------|
| No tasks available | Show status, suggest `/plan` |
| Dependencies not met | Show blocking tasks |
| Gate fails | Fix issue, retry gates |
| Task too large | Register subtasks |
| Unclear instruction | Create OPEN decision asking user for clarification |

## Resumability

- If interrupted, the task remains IN_PROGRESS — `begin` will resume it
- Decisions and changes are persisted incrementally
- Gate results are stored on the task
- Git commits preserve state even if pipeline tracking fails

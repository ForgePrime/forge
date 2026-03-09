---
name: next
id: SKILL-NEXT
version: "1.0"
description: "Get the next task from the pipeline and execute it with full traceability."
---

# Next (Execute Task)

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-NEXT |
| Version | 1.0 |
| Description | Pick the next available task, gather context, execute, validate, record. |

## Read Commands

| ID | Command | Returns | When |
|----|---------|---------|------|
| R1 | `python -m core.pipeline next {project}` | Next available task | Step 1 — get task |
| R2 | `python -m core.pipeline context {project} {task_id}` | Context from dependency tasks | Step 2 — before execution |
| R3 | `python -m core.decisions read {project} --task {task_id}` | Existing decisions for this task | Step 2 — check prior decisions |
| R4 | `python -m core.decisions contract add` | Contract for recording decisions | Before recording |
| R5 | `python -m core.changes contract` | Contract for recording changes | Before recording |
| R6 | `python -m core.gates show {project}` | Configured validation gates | Step 6 — before validation |
| R7 | `skills/deep-verify/SKILL.md` | Verification procedure | Step 5 — verify changes |
| R8 | `python -m core.guidelines context {project} --scopes "{scopes}"` | Active guidelines for task scopes | Step 5 — guidelines compliance |

## Write Commands

| ID | Command | Effect | When |
|----|---------|--------|------|
| W1 | `python -m core.decisions add {project} --data '{json}'` | Records decisions | Step 3 — for significant choices |
| W2 | `python -m core.changes record {project} --data '{json}'` | Records file changes (optional — auto-recorded at completion) | Step 4 — for per-file detail |
| W3 | `python -m core.pipeline add-tasks {project} --data '{json}'` | Creates follow-up tasks for major findings | Step 5 — if verification finds big issues |
| W4 | `python -m core.gates check {project} --task {task_id}` | Runs validation gates | Step 6 — before completion |
| W5 | `git add -A && git commit -m "..."` | Commits changes | Step 6 — after validation |
| W6 | `python -m core.pipeline complete {project} {task_id} --reasoning "..."` | Auto-records changes + marks DONE | Step 7 — after all validation |
| W7 | `python -m core.pipeline fail {project} {task_id} --reason "..."` | Marks task FAILED | On failure |

## Output

| File | Contains |
|------|----------|
| `forge_output/{project}/tracker.json` | Updated task statuses |
| `forge_output/{project}/decisions.json` | New decisions (if any) |
| `forge_output/{project}/changes.json` | Recorded file changes |

## Success Criteria

- Task instruction fully executed
- All significant decisions recorded with reasoning
- All file changes recorded with reasoning_trace
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

### Step 1 — Get the Task

```bash
python -m core.pipeline next {project}
```

If no task is available:
- All done → show final status, suggest `/compound`
- Blocked by failed task → show failure, suggest fix and reset
- No tasks → tell user to run `/plan`

If a SKILL path is specified on the task, read that SKILL.md and follow
its procedure instead of this generic flow.

---

### Step 2 — Gather Context

Before writing any code, understand the full context:

a. **Read context from dependencies, guidelines, and risk decisions** (what previous tasks produced + applicable standards + active risk decisions):
```bash
python -m core.pipeline context {project} {task_id}
```
This includes: dependency outputs, decisions, lessons, applicable guidelines (based on task's `scopes`), AND active risk decisions (linked to this task or its source idea). **Follow all MUST guidelines strictly. Follow SHOULD guidelines unless there's a documented reason not to.**

b. **If task has origin from an idea** (origin starts with `I-`), load the idea context:
```bash
python -m core.ideas show {project} {origin_id}
```
This shows the idea's exploration decisions, risk decisions, and other decisions — full context from the exploration phase.

c. **Check existing decisions** for this task:
```bash
python -m core.decisions read {project} --task {task_id}
```

d. **Read the codebase** — understand files you'll modify:
   - Read the task instruction carefully
   - Open and read every file mentioned in the instruction
   - Understand the existing code patterns before changing anything

e. **Check open decisions** that might affect this task:
```bash
python -m core.decisions read {project} --status OPEN
```

---

### Step 3 — Execute with Decisions

Implement the task following its instruction.

For every significant choice during implementation, record a decision:

```bash
python -m core.decisions contract add
```

Then:
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "{task_id}",
  "type": "implementation",
  "issue": "...",
  "recommendation": "...",
  "reasoning": "...",
  "alternatives": ["..."],
  "confidence": "HIGH|MEDIUM|LOW",
  "decided_by": "claude"
}]'
```

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

### Step 4 — Record Changes (optional mid-task)

Changes are **auto-recorded at completion** (Step 7) from git diff. This step
is only needed if you want per-file reasoning traces or to link specific
changes to decisions mid-task.

For detailed per-file recording:
```bash
python -m core.changes record {project} --data '[{
  "task_id": "{task_id}",
  "file": "path/to/file",
  "action": "create|edit|delete",
  "summary": "What was changed",
  "reasoning_trace": [
    {"step": "design", "detail": "Why this approach"},
    {"step": "implementation", "detail": "How it works"}
  ],
  "decision_ids": ["D-001"],
  "guidelines_checked": ["G-001"],
  "lines_added": N,
  "lines_removed": N
}]'
```

Already-recorded files are skipped by auto-recording (no duplicates).

---

### Step 5 — Verify Changes

Before validation gates, verify the quality and correctness of your changes.

**a. Guidelines compliance check:**

Review the guidelines loaded in Step 2 context (R8). For each MUST guideline, verify your changes comply. For SHOULD guidelines, verify where practical. If you need to reload guidelines for specific scopes:
```bash
python -m core.guidelines context {project} --scopes "{scopes}"
```

If a guideline was violated:
- **Minor fix** (< 5 minutes): fix it now, update change records
- **Major fix** (new feature/refactor needed): create a follow-up TODO task:
```bash
python -m core.pipeline add-tasks {project} --data '[{
  "id": "T-{next}",
  "name": "fix-{description}",
  "description": "Guideline {G-NNN} violated in {task_id}: {what needs fixing}",
  "type": "chore",
  "depends_on": ["{task_id}"]
}]'
```
Record the violation as a decision:
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "{task_id}",
  "type": "convention",
  "issue": "Guideline {G-NNN} not fully met: {details}",
  "recommendation": "Created follow-up task T-{next}",
  "confidence": "HIGH",
  "decided_by": "claude"
}]'
```

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

---

### Step 6 — Validate

Run configured validation gates (including secret scanning if configured as a gate):

```bash
python -m core.gates check {project} --task {task_id}
```

If gates fail:
- **Required gate fails**: Fix the issue, re-record changes, re-run gates
- **Advisory gate fails**: Note the failure, proceed if acceptable
- **No gates configured**: Skip (but warn)

If git is available and validation passes, commit:

```bash
git add -A && git commit -m "descriptive message"
```

---

### Step 7 — Complete

Mark the task as DONE. Use `--reasoning` to explain the changes:

```bash
python -m core.pipeline complete {project} {task_id} --reasoning "What was done and why"
```

This auto-records any unrecorded git changes (committed + uncommitted since task start).

Then immediately proceed to the next task (loop back to Step 1).

---

### On Failure

If the task cannot be completed:

1. Record what was attempted and why it failed
2. Mark the task as FAILED with a clear reason:
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

- If interrupted, the task remains IN_PROGRESS — `next` will resume it
- Decisions and changes are persisted incrementally
- Gate results are stored on the task
- Git commits preserve state even if pipeline tracking fails

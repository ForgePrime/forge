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

For simple tasks (chore, small bug), use lean context to reduce output:
```bash
python -m core.pipeline begin {project} --lean
```
Lean mode skips Knowledge, Research, Business Context, Lessons and shows only must-weight guidelines.

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

**Check for conflicts before writing code:**

After reading the code, before changing anything, check for contradictions:

1. **Instruction vs. existing code**: Does the instruction ask you to do something that contradicts how the existing code works? Example: instruction says "add middleware to app.ts" but app.ts uses a different middleware pattern than assumed.
2. **Instruction vs. upstream contract**: Does a dependency task's `produces` contract describe an interface different from what the instruction expects? Example: upstream says `POST /users → 201 {id, email}` but instruction assumes `{userId, emailAddress}`.
3. **Instruction vs. exclusions**: Does the instruction implicitly require modifying files that another task's exclusions forbid?

**If you find a conflict — STOP. Do not silently pick one interpretation.**

Surface it as an OPEN decision:
```bash
python -m core.decisions add {project} --data '[{"task_id": "{task_id}", "type": "implementation", "issue": "CONFLICT: Instruction says X but code/contract says Y", "recommendation": "Proceed with Y (matches existing code)", "alternatives": ["Follow instruction literally (X)", "Follow existing code (Y)"], "status": "OPEN", "decided_by": "claude"}]'
```

State both versions explicitly. Let the user decide. The failure mode this prevents: agent silently picks one interpretation, builds the wrong thing, discovers the conflict at integration time when it's expensive to fix.

For complex feature tasks, optionally load domain execution guidance:

```bash
python -m core.domain_modules for-scopes --scopes "{task.scopes}" --phase execution --task-type {task.type}
```

Follow domain-specific checklist and produce micro-review after completion.
Bug/chore tasks are auto-skipped by the complexity gate.

> **Advanced**: `pipeline next` and `pipeline context` are still available as separate commands if needed.

---

### Step 2 — Execute with Decisions

Implement the task following its instruction.

For every significant choice during implementation, record it:

```bash
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

### Step 3 — Record Changes (usually skip)

**Most tasks: skip this step.** Changes are auto-recorded from git diff at completion (Step 6). You don't need to manually record anything.

Manual recording is ONLY useful when you need to:
- Link a specific file change to a specific decision ID mid-task
- Add per-file reasoning that goes beyond the task-level `--reasoning`

If neither applies — move to Step 4.

For the rare case when you need manual recording:
```bash
python -m core.changes record {project} --data '[...]'
```

Already-recorded files are skipped by auto-recording (no duplicates).

---

### Step 4 — Verify Changes

Before validation gates, verify the quality and correctness of your changes.

**a. Acceptance Criteria checklist (mandatory):**

If the task has `acceptance_criteria`, go through each criterion explicitly and map each to a test:

```
AC Verification for {task_id}:
1. [criterion text] — PASS → Test: tests/test_users.py::test_create_success
2. [criterion text] — PASS → Test: tests/test_users.py::test_duplicate_email
3. [criterion text] — PASS → No test (UI-only, verified visually)
Alignment check: [success criteria] — [SATISFIED/GAP: explanation]
```

Rules:
- Every AC for feature/bug tasks should map to a test (`→ Test: {file}::{name}`)
- If no test exists for an AC → **write the test** before marking DONE
- UI-only or config-only AC → `→ No test ({reason})` is acceptable
- Gates run all tests — if a mapped test fails, the AC fails

If the task also has an `alignment` contract, verify that the AC collectively satisfy the alignment's `success` criteria.

All criteria must PASS before proceeding. If any criterion FAILS:
- **Fixable now**: fix it, update changes
- **Not fixable**: fail the task with `pipeline fail` explaining which criterion cannot be met

Compose the AC reasoning summary for Step 6 (used in `--ac-reasoning`).

**b. Guidelines compliance (quick scan):**

Scan MUST guidelines from Step 1 context against your changes. Fix violations immediately if small. For major violations, create a follow-up chore task and record a convention decision.

**c. Optional: Deep-verify + Decision drift (complex/critical tasks only):**

For tasks that create or modify significant logic (architecture, security, multi-file changes), optionally run:

1. **Deep-verify** (`skills/deep-verify/SKILL.md`) — scope to files changed. Fix CRITICAL findings, track IMPORTANT.
2. **Decision drift** — `python -m core.decision_checker check {project} --task {task_id}` — only if project has CLOSED decisions. Fix MAJOR drift or record override decision.

**Skip when:** task is trivial (config, docs, chore), or changes are straightforward.

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

**Before completing, verify** (Contract C6):
- If task has `origin: O-NNN` — KR auto-update will run. Check that objective's KRs have `measurement` defined.
- If AC has `kr_link` — verify the referenced KR exists (the pipeline will warn if not).

```bash
python -m core.pipeline complete {project} {task_id} --reasoning "What was done and why" --ac-reasoning "AC 1: [criterion] — PASS: [evidence]. AC 2: [criterion] — PASS: [evidence]. ..."
```

If the task has acceptance criteria, `--ac-reasoning` is required (from Step 4c).
Use the structured format `AC N: [criterion] — PASS|FAIL: [evidence]` — the pipeline validates that each criterion is addressed.

This auto-records any unrecorded git changes (committed + uncommitted since task start).
**KR auto-update runs after completion** — watch for warnings about measurement failures.

Then immediately proceed to Step 6.5 before starting the next task.

---

### Step 6.5 — Post-completion Sanity Check

**Skip for MINIMAL and LIGHT ceremony levels.** Mandatory for STANDARD and FULL.

After completing a task, verify that what you actually changed matches what was asked and what downstream tasks expect.

**a. Review your diff:**

```bash
git diff HEAD~1 --stat
git diff HEAD~1
```

**b. Compare against task instruction:**

- List every file you modified
- Check each file against the task's `instruction` — did you touch only files mentioned?
- If you modified files not in the instruction, ask: was it necessary or scope creep?

**c. Compare against upstream contracts:**

- If dependency tasks had `produces` contracts (shown in `begin` output), verify your implementation honors them
- Example: if upstream says `endpoint: "POST /users → 201 {id, email}"`, verify your code calls that exact endpoint with that exact shape

**d. Check downstream expectations:**

- If THIS task has `produces`, verify your output matches the contract
- Downstream tasks will rely on this — a mismatch here propagates errors

**e. Act on findings:**

- **Files match, contracts match**: proceed to Step 1 (next task)
- **Extra files modified (benign)**: note in reasoning, proceed
- **Contract mismatch or wrong files**: create a follow-up task:
  ```bash
  python -m core.pipeline add-tasks {project} --data '[{"id": "_1", "name": "fix-drift-from-{task_id}", "type": "bug", "description": "Post-completion check found: {description of mismatch}", "depends_on": [], "acceptance_criteria": ["..."]}]'
  ```
  Then proceed to next task — the fix is tracked, not silently ignored.

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

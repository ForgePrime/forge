---
name: next
id: SKILL-NEXT
version: "2.0"
description: "Execute next task with full traceability."
---

# Next (Execute Task)

Pick next available task, gather context, execute, validate, complete.

## Commands

```bash
python -m core.pipeline begin {project}          # claim task + show context
python -m core.pipeline begin {project} --lean   # skip Knowledge, Research, Lessons
python -m core.pipeline complete {project} {task_id} --reasoning "..." --ac-evidence '[...]' --deferred '[]'
python -m core.pipeline fail {project} {task_id} --reason "..."
python -m core.decisions add {project} --data '[...]'
python -m core.changes record {project} --data '[...]'   # usually skip — auto-recorded from git
python -m core.gates check {project} --task {task_id}
```

---

## Step 1 — Begin

```bash
python -m core.pipeline begin {project}
```

This claims the task and prints full context: instruction, dependencies, guidelines, knowledge, decisions.

**After reading context, before writing code:**

### 1a. Read the codebase
- Open and read every file mentioned in the instruction
- Understand existing patterns before changing anything

### 1b. Check for conflicts
Compare instruction against:
1. **Existing code** — does instruction assume something that contradicts how code works?
2. **Upstream contracts** — does dependency's `produces` match what instruction expects?
3. **Exclusions** — does instruction require modifying files that another task owns?

If conflict found → **STOP. Create OPEN decision:**
```bash
python -m core.decisions add {project} --data '[{"task_id": "{task_id}", "type": "implementation", "issue": "CONFLICT: instruction says X but code says Y", "recommendation": "...", "status": "OPEN"}]'
```

### 1c. Source Fidelity Check
If `Source Fidelity Warnings` appear in context (DRIFT warnings), read the full requirement content and compare with instruction. If they diverge → create decision.

---

## Step 2 — Execute

Implement the task following its instruction.

Record significant decisions (choosing between approaches, deviating from instruction, security choices):
```bash
python -m core.decisions add {project} --data '[{"task_id": "{task_id}", "type": "implementation", ...}]'
```

Do NOT record: following the only obvious path, standard library usage, formatting.

---

## Step 3 — Verify

### 3a. AC Checklist (mandatory for feature/bug)
Go through each acceptance criterion:
```
1. [criterion] — PASS → Test: tests/test_x.py::test_y
2. [criterion] — PASS → verified visually
```
Every AC should map to a test. If no test exists → write it.

### 3b. Guidelines compliance
Scan MUST guidelines from context. Fix violations immediately.

### 3c. Deep-verify (optional, for complex/critical tasks)
Run `skills/deep-verify/SKILL.md` scoped to changed files.

---

## Step 4 — Validate

```bash
python -m core.gates check {project} --task {task_id}
```

Fix required gate failures. Then commit:
```bash
git add -A && git commit -m "descriptive message"
```

---

## Step 5 — Complete

```bash
python -m core.pipeline complete {project} {task_id} \
  --reasoning "What was done and why" \
  --ac-evidence '[{"ac_index": 0, "verdict": "PASS", "evidence": "..."}]' \
  --deferred '[]'
```

Rules:
- `--reasoning` required (what changed, why)
- `--ac-evidence` required for feature/bug with manual AC (structured per-AC evidence)
- `--deferred '[]'` required for STANDARD+ ceremony (empty if all requirements covered)
- Fidelity matrix auto-prints (requirement terms vs git diff)
- Feature Registry auto-registers routes/components
- KR auto-updates for objective-linked tasks

---

## On Failure

```bash
python -m core.pipeline fail {project} {task_id} --reason "What failed and why"
```

If task too large → break into subtasks:
```bash
python -m core.pipeline register-subtasks {project} {task_id} --data '[...]'
```

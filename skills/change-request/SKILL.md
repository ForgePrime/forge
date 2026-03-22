---
name: change-request
id: SKILL-CHANGE-REQUEST
version: "1.0"
description: "Handle new or changed requirements during execution — ingest, assess impact, update objectives/plan."
---

# Change Request

New requirements arrived, existing requirements changed, or scope shifted — during an active project. This skill handles the change without breaking the running pipeline.

**The test**: after processing the change, coverage report still shows all requirements mapped to tasks, and no OPEN clarification decisions exist.

---

## When to Use

- New document added to project during execution
- Existing requirement changed (updated spec, client feedback)
- Scope change (feature added, feature dropped)
- Discovered requirement during implementation (something missing from docs)

---

## Step 1 — Assess What Changed

### 1a. New document

If a new document was added:
```bash
python -m core.knowledge read {project} --category source-document
# Check if new doc is already registered
```

If not registered → follow `ingest` skill for the new document only. Then return to Step 2.

### 1b. Changed requirement

If an existing requirement changed:
```bash
python -m core.knowledge show {project} {K-NNN}
# Show current requirement text
```

Update the knowledge object:
```bash
python -m core.knowledge update {project} --data '[{
  "id": "K-NNN",
  "content": "{updated requirement text}",
  "change_reason": "Requirement updated: {what changed and why}"
}]'
```

### 1c. New requirement discovered during implementation

Create it directly:
```bash
python -m core.knowledge add {project} --data '[{
  "title": "{requirement description}",
  "category": "requirement",
  "content": "{full requirement text}",
  "source": {"type": "user", "ref": "discovered during T-NNN execution"},
  "tags": ["requirement", "discovered"],
  "scopes": ["{relevant_scopes}"]
}]'
```

### 1d. Scope change (feature dropped)

Update the requirement status:
```bash
python -m core.knowledge update {project} --data '[{
  "id": "K-NNN",
  "status": "DEPRECATED",
  "change_reason": "Dropped from scope: {reason}"
}]'
```

Create a decision recording the scope change:
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "CHANGE_REQUEST",
  "type": "architecture",
  "issue": "Scope change: {what was dropped/added}",
  "recommendation": "{how this affects the plan}",
  "status": "CLOSED",
  "decided_by": "user"
}]'
```

---

## Step 2 — Impact Assessment

### 2a. Check affected objectives

```bash
python -m core.objectives read {project}
```

For each affected requirement K-NNN, find its linked objective:
```bash
python -m core.knowledge show {project} {K-NNN}
# Look at linked_entities → objective
```

### 2b. Determine impact level

| Impact | Description | Action |
|--------|-------------|--------|
| **Minor** | Change affects AC text or test details but not task structure | Update AC on existing tasks |
| **Moderate** | New requirement needs a new task within existing objective | Add task to existing plan |
| **Major** | New objective needed, or existing objective restructured | Create new objective, run /analyze + /plan |
| **Breaking** | Fundamental change that invalidates completed work | Reset affected tasks, re-plan |

### 2c. Record the change decision

```bash
python -m core.decisions add {project} --data '[{
  "task_id": "CHANGE_REQUEST",
  "type": "architecture",
  "issue": "Change request: {summary}",
  "recommendation": "Impact: {Minor|Moderate|Major|Breaking}. Action: {what to do}",
  "reasoning": "Affects: {K-NNN requirements, O-NNN objectives, T-NNN tasks}",
  "status": "CLOSED",
  "decided_by": "claude"
}]'
```

---

## Step 3 — Apply Changes

### Minor: Update AC

```bash
python -m core.pipeline update-task {project} --data '{
  "id": "T-NNN",
  "acceptance_criteria": [{updated AC}]
}'
```

### Moderate: Add new task(s)

```bash
python -m core.pipeline add-tasks {project} --data '{
  "new_tasks": [{
    "id": "_1",
    "name": "{task name}",
    "description": "{what}",
    "instruction": "{how}",
    "type": "feature",
    "origin": "O-NNN",
    "source_requirements": [{"knowledge_id": "K-NNN", "text": "...", "source_ref": "..."}],
    "depends_on": ["T-NNN"],
    "acceptance_criteria": [{"text": "...", "verification": "test", "test_path": "..."}]
  }]
}'
```

### Major: New objective + plan

1. Link new requirement to objective:
```bash
python -m core.knowledge link {project} --data '[{
  "knowledge_id": "K-NNN",
  "entity_type": "objective",
  "entity_id": "O-NNN",
  "relation": "required"
}]'
```

2. Update objective KR if needed:
```bash
python -m core.objectives update {project} --data '[{
  "id": "O-NNN",
  "key_results": [{updated KRs}]
}]'
```

3. Plan new tasks: follow /plan skill with `--objective O-NNN`

### Breaking: Reset and re-plan

1. Identify affected tasks:
```bash
python -m core.pipeline list {project} --objective O-NNN
```

2. Reset affected tasks:
```bash
python -m core.pipeline reset {project} --from T-NNN
```

3. Re-run analysis and planning: /analyze → /plan

---

## Step 4 — Verify

After applying changes:

```bash
python -m core.pipeline status {project}
# Check: no orphaned tasks, dependencies intact

python -m core.knowledge read {project} --category requirement
# Check: all requirements still ACTIVE or explicitly DEPRECATED

# If objectives modified:
python -m core.objectives show {project} {O-NNN}
# Check: KR still measurable, requirements linked
```

---

## Success Criteria

- Changed/new requirement captured as K-NNN
- Impact decision recorded as D-NNN (CLOSED)
- Affected tasks updated or new tasks added
- Coverage still complete (no MISSING requirements)
- No OPEN clarification decisions
- Pipeline status clean (no orphaned dependencies)

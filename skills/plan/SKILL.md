---
name: plan
id: SKILL-PLAN
version: "2.0"
description: "Decompose goal into tasks. Every mandatory step has a mechanical gate."
---

# Plan

Decompose a user's goal into a tracked task graph with dependency ordering.

**The test**: paste any task's `instruction` into a blank context — does the agent know which file to open first? If not, the plan is not done.

## Prerequisites

- If source documents ingested (K-NNN with category=source-document exist): objectives MUST exist (run `/analyze` first). `draft-plan` BLOCKS without `--objective O-NNN`.
- If no source documents: standalone plan is allowed.

## Commands

```bash
# Read
python -m core.pipeline status {project}
python -m core.guidelines read {project} --weight must
python -m core.knowledge read {project} --category requirement
python -m core.objectives show {project} {objective_id}
python -m core.decisions read {project} --status OPEN
python -m core.feature_registry show {project}

# Write
python -m core.pipeline init {project} --goal "..." --project-dir "{path}"
python -m core.pipeline draft-plan {project} --data '[...]' [--objective O-NNN] [--assumptions '[...]'] [--coverage '[...]']
python -m core.pipeline approve-plan {project}
python -m core.decisions add {project} --data '[...]'
python -m core.knowledge add {project} --data '[...]'
```

---

## Step 1 — Load Context (GATE: mechanical)

`draft-plan` automatically loads and validates:
- OPEN decisions → BLOCKS on unresolved question/architecture/implementation types
- Must-guidelines → BLOCKS if plan doesn't cover their scopes
- Coverage → BLOCKS if any requirement is MISSING
- Assumptions → BLOCKS if 5+ HIGH severity

Before decomposing, you must manually:
1. Read must-guidelines: `python -m core.guidelines read {project} --weight must`
2. Read requirements: `python -m core.knowledge read {project} --category requirement`
3. Read OPEN decisions: `python -m core.decisions read {project} --status OPEN`
4. If planning from objective: `python -m core.objectives show {project} {objective_id}`
5. Check Feature Registry: `python -m core.feature_registry show {project}`

---

## Step 2 — Tag Input (GATE: readiness check)

Tag every statement from the goal/requirements:

| Tag | Meaning | Goes to |
|-----|---------|---------|
| `[REQ]` | Must be implemented | task instruction + AC |
| `[CONSTRAINT]` | Hard limit | task instruction |
| `[DECISION]` | Already decided | follow, don't revisit |
| `[SCOPE-OUT]` | Excluded | never into tasks |
| `[CONFLICT]` | Contradicts something | **HARD STOP — resolve before continuing** |
| `[VAGUE]` | Ambiguous | make explicit assumption |

Rules:
- Every `[CONFLICT]` → STOP. Create OPEN decision. Do NOT plan.
- Every `[VAGUE]` → write assumption with consequence: "I assume X because Y. If wrong, Z changes."
- Every `[SCOPE-OUT]` → ONLY in out-of-scope. If any task implements it = scope leak.

---

## Step 3 — Scan Codebase (GATE: Impact Map)

**Mandatory.** Before decomposing, prove you understand the codebase.

For each file the plan will create or modify:
1. Read the file (or directory)
2. Search for usages: `grep` imports, function calls, references
3. **Search for existing implementations**: For each NEW page/component/endpoint:
   ```bash
   grep -r "{feature_keyword}" src/app/ src/components/ --include="*.tsx" -l
   grep -r "{route_path}" app/modules/ --include="*.py" -l
   ```
   If existing implementation found → **STOP. Create decision: extend existing or justify new.**

Produce table:

```
## Impact Map
| File | Action | Depended on by | Invariants |
|------|--------|----------------|------------|

### Existing Implementation Check
| New task creates | Existing found? | Decision |
|-----------------|----------------|----------|
```

Store as knowledge: `python -m core.knowledge add {project} --data '[{"title": "Impact Map: {goal}", "category": "architecture", ...}]'`

---

## Step 4 — Decompose

Split by vertical slices (end-to-end value), not technical layers.

For each task, provide ALL of:
- `id`: temp IDs `_1`, `_2` (auto-remapped to T-NNN at approval)
- `name`: kebab-case
- `description`: WHAT (include boundary: "This task IS X. NOT Y.")
- `instruction`: HOW — must contain:
  1. Exact files to create (full paths)
  2. Exact files to modify (full paths)
  3. Exact files NOT to touch (owned by sibling task)
  4. Pattern to follow (existing file as model)
  5. Reference to dependency output (if depends_on non-empty)
- `type`: feature, bug, chore, investigation
- `origin`: O-NNN (REQUIRED for feature/bug when objectives exist)
- `depends_on`: prerequisite task IDs
- `produces`: what downstream tasks consume (endpoint, model, component)
- `exclusions`: DO NOT rules (cross-task boundaries, file ownership)
- `scopes`: guideline scopes (only existing ones from project)
- `knowledge_ids`: relevant K-NNN IDs
- `acceptance_criteria`: structured format REQUIRED for feature/bug:
  ```json
  {"text": "what is true when done", "verification": "test|command|manual", "test_path": "...", "command": "...", "check": "..."}
  ```
  Rules: `test` requires `test_path`. `command` requires `command`. 2-5 per task. Functional, not metric-based.

After all tasks defined, derive cross-task exclusions (second pass):
- Group by files/directories modified → add exclusions preventing overlap
- Sequential tasks: later must not undo earlier's work

---

## Step 5 — Verify (GATE: mechanical)

### 5a. Readiness Check
List assumptions: "I ASSUME X BECAUSE Y. If wrong, impact is HIGH/MED/LOW."
- 0-4 HIGH → proceed
- 5+ HIGH → STOP, ask user. `draft-plan` blocks.

### 5b. Coverage Check
For every requirement from source docs:
- **COVERED** — task implements it AND instruction mentions it
- **DEFERRED** — with reason
- **OUT_OF_SCOPE** — with reason
- No MISSING allowed. `draft-plan` blocks on MISSING.

### 5c. Cold Start Test
- Task `_1` instruction → "First file to open: [exact path]." If can't name → fix.
- Last task instruction → same test. Planning fatigue makes last tasks vaguest.

### 5d. Dependency Contract Test
For every task with depends_on:
```
_N depends_on _M → _M.produces.{key} matches _N.instruction reference? YES/NO
```
Any NO = broken contract → fix.

---

## Step 6 — Draft & Approve

```bash
python -m core.pipeline draft-plan {project} --data '[...]' --objective O-NNN \
  --assumptions '[...]' --coverage '[...]'
```

Review output. Fix warnings. Then:
```bash
python -m core.pipeline approve-plan {project}
```

Gates at approval (all mechanical, all blocking):
- AC quality: feature/bug must have structured AC with verification + test_path/command
- Reference validation: origin/knowledge_ids must reference existing entities
- Context validation: scopes must match guidelines
- DAG validation: no cycles, all dependencies exist
- Feature conflicts: new tasks must not duplicate registered features
- Over-coverage: same requirement from different objectives = warning
- Cross-objective overlap: new task similar to DONE task = warning
- Origin required: feature/bug tasks must have origin when objectives exist

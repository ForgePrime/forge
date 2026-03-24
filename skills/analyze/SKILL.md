---
name: analyze
id: SKILL-ANALYZE
version: "1.0"
description: "Analyze extracted knowledge — resolve decisions, group requirements into objectives with measurable KR, prepare for planning."
---

# Analyze

Bridge between ingestion and planning. Transforms flat extracted knowledge into structured objectives with measurable key results.

**The test**: after analysis, `draft-plan` passes all gates — understanding, OPEN decisions, coverage. Every requirement is linked to an objective. Every objective has KR with measurement method.

---

## Prerequisites

- Ingestion completed: K-NNN (requirements, context), D-NNN (decisions), G-NNN (guidelines) exist
- Source documents registered: K-NNN (source-document) present

---

## Read Commands

| ID | Command | Returns | When |
|----|---------|---------|------|
| R1 | `python -m core.knowledge read {project} --category requirement` | Extracted requirements | Step 1 |
| R2 | `python -m core.knowledge read {project} --category domain-rules` | Business rules | Step 1 |
| R3 | `python -m core.knowledge read {project}` | All knowledge | Step 1 |
| R4 | `python -m core.decisions read {project} --status OPEN` | Unresolved decisions | Step 2 |
| R5 | `python -m core.guidelines read {project}` | Existing guidelines | Step 1 |
| R6 | `python -m core.objectives contract add` | Objective schema | Step 3 |
| R7 | `python -m core.research read {project} --category ingestion` | Ingestion records (which doc → which facts) | Step 1 |

## Write Commands

| ID | Command | Creates | When |
|----|---------|---------|------|
| W1 | `python -m core.decisions update {project} --data '[...]'` | Resolved decisions | Step 2 |
| W2 | `python -m core.objectives add {project} --data '[...]'` | Objectives with KR | Step 3 |
| W3 | `python -m core.knowledge link {project} --data '[...]'` | Requirement → Objective links | Step 4 |

---

## Step 1 — Load and Review Extracted Knowledge

Load everything produced by ingestion:
```bash
python -m core.knowledge read {project} --category requirement
python -m core.knowledge read {project} --category domain-rules
python -m core.knowledge read {project} --category source-document
python -m core.research read {project} --category ingestion
python -m core.decisions read {project} --status OPEN
python -m core.guidelines read {project}
```

Review what you have:
- How many requirements? Are they concrete and testable?
- How many OPEN decisions? What types?
- What guidelines exist?
- What are the knowledge gaps (from ingestion summary)?

---

## Step 2 — Resolve OPEN Decisions

Before creating objectives, resolve or triage every OPEN decision.

### 2a. Clarification needed (type=clarification_needed)

For each:
- Can you answer it from other docs or context? → CLOSE with answer
- Does it have a reasonable default? → CLOSE with default, add knowledge
- Must the user answer? → LEAVE OPEN (will block draft-plan)

```bash
python -m core.decisions update {project} --data '[{
  "id": "D-NNN",
  "status": "CLOSED",
  "action": "accept",
  "override_value": "{answer or accepted default}",
  "override_reason": "{why this answer}"
}]'
```

For each closed clarification, create knowledge from the answer:
```bash
python -m core.knowledge add {project} --data '[{
  "title": "{what was clarified}",
  "category": "{appropriate category}",
  "content": "{answer with context}",
  "source": {"type": "user", "ref": "D-NNN resolution"},
  "tags": ["{relevant}"]
}]'
```

### 2b. Assumptions (type=architecture, status=OPEN, confidence=LOW)

For each assumption:
- Is it reasonable given context? → CLOSE with `action: "accept"`
- Is it risky? → Keep OPEN, assess severity

### 2c. Conflicts (type=risk, severity=HIGH)

For each conflict:
- Higher trust source wins → CLOSE with chosen value
- Same trust, can't decide → Keep OPEN (will block draft-plan)

### 2d. Gate check

After resolution, verify **ALL OPEN decisions** — not just clarification_needed:
```bash
python -m core.decisions read {project} --status OPEN
# ALL types: clarification_needed, architecture, implementation, risk, exploration
# Each must be either CLOSED or explicitly left OPEN with documented reason
```

**Rules:**
- `clarification_needed` → MUST be CLOSED (or confirmed as blocking for user)
- `risk` HIGH severity → MUST be CLOSED or mitigated
- `architecture` → MUST be CLOSED before creating objectives that depend on the decision
- Any OPEN decision about **UI placement, feature scope, or implementation approach** → MUST be CLOSED. These silently dictate objective structure if left open.

**Anti-pattern this prevents:** OI-14 ("Schedule maintenance — part of Settings or standalone?") left OPEN → objective title inherited "standalone Maintenance Page" → plan created duplicate page instead of extending Settings.

---

## Step 3 — Create Objectives with Measurable KR

### 3a. Group requirements by business outcome

Read all requirements and group them by what they collectively deliver:

- NOT by technical area ("backend", "frontend") — that's scope, not objective
- BY user-observable outcome ("User can authenticate", "Invoices are processed", "Reports are generated")
- NOT by UI artifact — objective title describes WHAT users can do, not HOW (page, modal, tab)

**Objective title rules:**
- Good: "Auto-Buy Schedule Configuration per SPEC" (outcome)
- Bad: "Auto-Buy Schedule Maintenance Page" (dictates UI: "Page" → /plan creates new page)
- Good: "Priority Reorder with Auto-Buy Lock" (capability)
- Bad: "Priority Management Frontend Modal" (dictates component type)
- Do NOT inherit the source document filename as the objective title. "SPEC-auto-buy-schedule-maintenance.md" is a file, not an outcome.

**Each objective should:**
- Represent a coherent deliverable (demoable, testable)
- Contain 3-15 requirements (fewer = merge, more = split)
- Have 2-5 key results

### 3b. Define KR with measurement

For EACH key result, define HOW to verify it's achieved:

**Numeric KR** (when you can measure a number):
```json
{
  "metric": "API response time p95",
  "baseline": 0,
  "target": 200,
  "measurement": "command",
  "command": "python scripts/measure_latency.py",
  "direction": "down"
}
```

**Test-based KR** (when a test suite proves it):
```json
{
  "description": "All authentication flows work correctly",
  "measurement": "test",
  "test_path": "tests/test_auth.py"
}
```

**Manual KR** (when only human can verify):
```json
{
  "description": "UI matches approved wireframes",
  "measurement": "manual",
  "check": "Compare each screen against wireframes in docs/wireframes/"
}
```

**Every KR MUST have `measurement` field.** If you can't define how to measure it, the KR is too vague — make it more concrete.

### 3c. Create objectives

```bash
python -m core.objectives add {project} --data '[{
  "title": "{user-observable outcome}",
  "description": "{what this objective delivers and why it matters}",
  "key_results": [
    {"metric": "...", "baseline": 0, "target": N, "measurement": "command", "command": "..."},
    {"description": "...", "measurement": "test", "test_path": "..."}
  ],
  "scopes": ["{relevant_scopes}"],
  "tags": ["{tags}"]
}]'
```

---

## Step 4 — Link Requirements to Objectives

For EACH requirement K-NNN, link it to the covering objective:
```bash
python -m core.knowledge link {project} --data '[{
  "knowledge_id": "K-NNN",
  "entity_type": "objective",
  "entity_id": "O-NNN",
  "relation": "required"
}]'
```

### Verification

Check that no requirements are orphaned:
```bash
python -m core.knowledge read {project} --category requirement
# Each should have linked_entities with at least one objective
```

If a requirement doesn't fit any objective:
- Is it out of scope? → Add to assumptions/out-of-scope
- Is it a separate concern? → Create a new objective for it
- Is it not actually a requirement? → Reclassify (context, rule, etc.)

---

## Step 5 — Summary

```
## Analysis Complete: {project}

Decisions resolved: {resolved_count}/{total_open}
  Still OPEN: {remaining_open} (will block planning if clarification_needed or HIGH risk)

Objectives created: {obj_count}
  {O-001}: {title} ({kr_count} KRs, {req_count} requirements)
  {O-002}: {title} ({kr_count} KRs, {req_count} requirements)

Requirements mapping:
  Mapped to objectives: {mapped}/{total_req}
  Unmapped: {unmapped_count} (resolve before planning)

Next: /plan {project} --objective O-NNN
```

### MANDATORY: Verify before exiting

Run the verification command to confirm Contract C2 is satisfied:
```bash
python -m core.objectives verify {project}
```
This checks: ≥1 ACTIVE objective, all KRs have measurement, no orphaned requirements.
If verdict is FAIL — fix before proceeding. `/plan` will BLOCK if this fails.

---

## Success Criteria

- `python -m core.objectives verify {project}` returns PASS or WARN (not FAIL)
- **ALL OPEN decisions**: CLOSED or explicitly documented as non-blocking with reason
- Special attention: `clarification_needed` and `HIGH severity risk` MUST be CLOSED
- Architecture/implementation decisions about UI placement, scope, feature boundaries MUST be CLOSED before objectives that depend on them
- Every requirement K-NNN linked to an Objective
- Every Objective has 2-5 KR with `measurement` field defined (command|test|manual)
- Understanding gate would PASS (9 categories covered)

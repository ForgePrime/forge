---
name: analyze
id: SKILL-ANALYZE
version: "2.0"
description: "Transform extracted knowledge into objectives with measurable KRs."
---

# Analyze

Bridge between ingestion and planning. Groups requirements into objectives, resolves decisions, prepares for `/plan`.

**The test**: after analysis, `draft-plan` passes all gates — every requirement linked to an objective, every objective has measurable KR, no blocking OPEN decisions.

## Commands

```bash
# Read
python -m core.knowledge read {project} --category requirement
python -m core.knowledge read {project} --category domain-rules
python -m core.knowledge read {project} --category source-document
python -m core.decisions read {project} --status OPEN
python -m core.guidelines read {project}

# Write
python -m core.decisions update {project} --data '[{"id": "D-NNN", "status": "CLOSED", ...}]'
python -m core.objectives add {project} --data '[...]'
python -m core.knowledge link {project} --data '[{"knowledge_id": "K-NNN", "entity_type": "objective", "entity_id": "O-NNN", "relation": "required"}]'

# Verify
python -m core.objectives verify {project}
```

---

## Step 1 — Load Everything

```bash
python -m core.knowledge read {project} --category requirement
python -m core.knowledge read {project} --category domain-rules
python -m core.knowledge read {project} --category source-document
python -m core.research read {project} --category ingestion
python -m core.decisions read {project} --status OPEN
python -m core.guidelines read {project}
```

Count: How many requirements? How many OPEN decisions? What categories are covered?

---

## Step 2 — Resolve ALL OPEN Decisions (GATE: blocks /plan)

**Every OPEN decision must be CLOSED or explicitly documented as non-blocking.**

Process by type:
- **clarification_needed** → answer from docs/context, or ask user. MUST close.
- **risk (HIGH)** → mitigate or accept with reasoning. MUST close.
- **architecture/implementation** → decide. MUST close. These silently dictate objective structure if left open.
  - Anti-pattern: OI-14 "standalone page vs Settings?" left OPEN → objective title inherited "Page" → plan created duplicate.
- **exploration** → complete or mark ready_for_tracker. MUST close.
- **Other types** → close or document why non-blocking.

For each closed decision, create knowledge from the answer:
```bash
python -m core.knowledge add {project} --data '[{"title": "...", "category": "...", "content": "...", "source": {"type": "user", "ref": "D-NNN resolution"}}]'
```

**After resolution, verify:**
```bash
python -m core.decisions read {project} --status OPEN
# Should be empty or explicitly non-blocking
```

---

## Step 3 — Create Objectives with Measurable KR

### 3a. Group by business outcome

- BY user-observable outcome ("Users can configure auto-buy schedule", "Invoices are purchased in priority order")
- NOT by technical area ("backend", "frontend")
- NOT by UI artifact ("Maintenance Page", "Priority Modal")

**Title rules:**
- Good: "Auto-Buy Schedule Configuration per SPEC" (outcome)
- Bad: "Auto-Buy Schedule Maintenance Page" (dictates UI — word "Page" forces new page in /plan)
- Do NOT inherit source document filename as objective title.

Each objective: 3-15 requirements, 2-5 KRs.

### 3b. Define KR with measurement

Every KR MUST have `measurement` field:
- **Numeric**: `{metric, baseline, target, measurement: "command", command: "..."}`
- **Test-based**: `{description, measurement: "test", test_path: "..."}`
- **Manual**: `{description, measurement: "manual", check: "..."}`

---

## Step 4 — Link Requirements to Objectives

Every requirement K-NNN must link to an objective:
```bash
python -m core.knowledge link {project} --data '[{"knowledge_id": "K-NNN", "entity_type": "objective", "entity_id": "O-NNN", "relation": "required"}]'
```

If requirement doesn't fit any objective → create new objective or mark out-of-scope.

---

## Step 5 — Verify (GATE: mechanical)

```bash
python -m core.objectives verify {project}
```

Must return PASS or WARN:
- ≥1 ACTIVE objective
- All KRs have measurement
- No orphaned requirements (K-NNN without objective link)
- All OPEN decisions closed or non-blocking

If FAIL → fix before proceeding. `/plan` BLOCKS on failed verification.

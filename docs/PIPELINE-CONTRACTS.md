# Pipeline Contracts

Every transition in the pipeline has a **contract**: what MUST exist before proceeding,
what the step MUST produce, and how the system VERIFIES it.

**Enforcement rule**: Every contract is checked by CODE (hard gate), not by instructions alone.
If a contract can only be checked by the agent reading a skill, it's not a contract — it's a wish.

---

## Overview

```
SOURCE DOC
    │
    ▼
┌─────────┐    Contract C1: ≥1 source-doc, 9 categories assessed
│ /ingest  │──────────────────────────────────────────────────────►
└─────────┘
    │
    ▼
┌──────────┐   Contract C2: ≥1 objective with measurable KR,
│ /analyze  │──────────────────────────────────────────────────────►
└──────────┘   all requirements linked, blocking decisions resolved
    │
    ▼
┌────────┐     Contract C3: all tasks have origin=O-NNN (real),
│ /plan   │──────────────────────────────────────────────────────►
└────────┘     --objective used, coverage passed, AC on feature/bug
    │
    ▼
┌──────────┐   Contract C4: draft approved, DAG valid, context loads
│ /approve  │──────────────────────────────────────────────────────►
└──────────┘
    │
    ▼
┌────────┐     Contract C5: deps met, no blocking decisions
│ /begin  │──────────────────────────────────────────────────────►
└────────┘
    │
    ▼
┌───────────┐  Contract C6: mechanical AC pass, manual AC evidenced,
│ /complete  │──────────────────────────────────────────────────────►
└───────────┘  KR update verified (not silent), gates pass
    │
    ▼
┌────────────┐ Contract C7: all tasks for O-NNN done,
│ O-NNN done  │──────────────────────────────────────────────────────►
└────────────┘ all KRs at target or ACHIEVED
```

---

## C1: /ingest exit contract

**Precondition**: Source document(s) provided by user.

**MUST produce**:
- ≥1 K-NNN with `category: "source-document"` (registered source)
- ≥1 R-NNN with `category: "ingestion"` (extraction record per document)
- Extracted facts: K-NNN with categories from {requirement, domain-rules, technical-context,
  architecture, api-reference, business-context, integration, infrastructure}
- D-NNN for every conflict, ambiguity, or assumption found

**MUST verify** (mechanical gate — blocks /analyze):
- Extraction ratio: ≥2 facts per source document (heuristic floor)
- 9-category coverage check: each of {deployment, stack, users, data-in, data-out,
  persistence, error-handling, scale, definition-of-done} is either:
  - KNOWN (K-NNN exists covering it), or
  - ASSUMED (D-NNN assumption exists), or
  - UNKNOWN (D-NNN clarification_needed exists)
  - NOT: silently missing

**Enforcement point**: New function `validate_ingestion_completeness(project)` called by
`/analyze` before Step 1. Hard gate — blocks analysis if ingestion incomplete.

---

## C2: /analyze exit contract

**Precondition**: C1 satisfied (ingestion complete).

**MUST produce**:
- ≥1 O-NNN objective with status=ACTIVE
- Every O-NNN has ≥1 KR with `measurement` field set (command|test|manual)
- Every K-NNN with category=requirement linked to ≥1 objective
  (via linked_entities [{entity_type: "objective", entity_id: "O-NNN"}])
- All D-NNN with type=clarification_needed: CLOSED or explicitly left OPEN with reason

**MUST verify** (mechanical gate — blocks /plan):
- `objectives.json` exists and has ≥1 ACTIVE objective
- Every ACTIVE objective has ≥1 KR with `measurement` defined
- No orphaned requirements (K-NNN category=requirement without objective link)
  - This is already warned in draft-plan; upgrade to BLOCK
- Blocking decisions resolved (already enforced in draft-plan)

**Enforcement point**: Two places:
1. New function `validate_analysis_completeness(project)` called by `draft-plan` BEFORE
   other gates. Hard gate.
2. `/analyze` skill Step 5 must call a verification command:
   `python -m core.objectives verify {project}` (new command)

---

## C3: /plan (draft-plan) exit contract

**Precondition**: C2 satisfied (analysis complete, objectives exist).

**MUST produce**:
- Draft plan with tasks where:
  - Every task has `origin` pointing to a REAL O-NNN (validated against objectives.json)
  - Every feature/bug task has structured `acceptance_criteria`
  - Every task has `instruction` with enough detail to pass cold-start
  - `--objective O-NNN` flag used (or every task has explicit origin)

**MUST verify** (mechanical gate — blocks approve-plan):
- `origin` on every task references existing ACTIVE objective
  (new validation in draft-plan and approve-plan)
- `knowledge_ids` on every task reference existing K-NNN
  (new validation)
- Coverage: if K-NNN requirements exist, every requirement is in ≥1 task's
  source_requirements OR explicitly DEFERRED/OUT_OF_SCOPE

**Enforcement point**: Upgrade existing warnings to hard gates in `draft-plan` and
`approve-plan`.

---

## C4: /approve exit contract

**Precondition**: C3 satisfied (draft reviewed).

**MUST produce**:
- Tasks materialized in tracker with real IDs (T-NNN)
- DAG valid (no cycles, all deps exist)
- Context validation passed (scopes match guidelines)

**MUST verify** (all already exist as hard gates):
- Duplicate ID check ✓
- AC structure check ✓
- DAG validation ✓
- Context validation ✓
- NEW: origin validation (references real objectives)
- NEW: knowledge_ids validation (references real knowledge)

---

## C5: /begin exit contract

**Precondition**: Task selected by /next (deps met, no conflicts, no blocking decisions).

**MUST produce**:
- Task status = IN_PROGRESS
- Context loaded and printed

**MUST verify** (existing + new):
- Dependencies met ✓
- No blocking decisions ✓
- NEW: If task has origin, verify objective still ACTIVE (not already ACHIEVED)
- NEW: Warn if task instruction references files that changed since plan approval
  (staleness check — already exists as warning)

---

## C6: /complete exit contract

**Precondition**: Task work done, code committed.

**MUST produce**:
- Task status = DONE
- Mechanical AC all PASS
- Manual AC with evidence (≥50 chars, addresses each AC)
- Gates passed
- KR auto-update EXECUTED (not silently skipped)

**MUST verify** (existing + new):
- Mechanical AC ✓
- Manual AC evidence ✓
- Gates ✓
- NEW: If task has origin and objective has numeric KR → KR MUST be updated
  (either via measurement command, AC kr_link, or explicit --kr-update flag)
  If update fails (timeout, bad output) → WARNING with instructions, not silent skip
- NEW: If kr_link in AC references non-existent KR → ERROR, not silent ignore
- NEW: Log KR update result to trace (success/fail/skipped with reason)

---

## C7: Objective completion contract

**Precondition**: All tasks with origin=O-NNN are DONE.

**MUST produce**:
- Objective status updated (ACTIVE → ACHIEVED if all KRs met)
- All KRs either at target (numeric) or ACHIEVED (descriptive)

**MUST verify**:
- NEW: When last task for an objective completes, auto-check:
  - All numeric KRs: current ≥ target → status ACHIEVED
  - All descriptive KRs: status = ACHIEVED
  - If all KRs ACHIEVED → objective status = ACHIEVED
  - If NOT all KRs ACHIEVED → WARNING: "All tasks done but N KRs not met"
    with list of unmet KRs and measurement instructions

---

## Implementation Priority

| Contract | Current State | Work Needed |
|----------|---------------|-------------|
| C1 | No gate exists | New: validate_ingestion_completeness() |
| C2 | Partial (warnings only) | Upgrade warnings → hard gates + new verify command |
| C3 | Partial (objective linkage gate added) | Add origin/knowledge validation |
| C4 | Mostly complete | Add origin/knowledge validation |
| C5 | Mostly complete | Minor: objective staleness check |
| C6 | Strong mechanical AC | Add KR update verification + kr_link validation |
| C7 | Does not exist | New: objective completion check on last task |

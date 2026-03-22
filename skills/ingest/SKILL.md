---
name: ingest
id: SKILL-INGEST
version: "1.0"
description: "Document ingestion — register source documents, extract structured facts, create knowledge with traceability."
---

# Document Ingestion

Transform source documents into structured, traceable Forge knowledge. Every fact extracted links back to its source document and section.

**The test**: after ingestion, `python -m core.pipeline draft-plan` should pass the understanding gate — 9 critical categories covered.

---

## When to Use

- At project start when documentation exists (specs, PRDs, ADRs, API docs)
- During `/onboard` for brownfield projects with existing docs
- During `/discover` before analysis (Phase 0)
- Whenever new documents are added to the project

---

## Step 1 — Register Source Documents

Scan for documentation in the project directory:

```bash
# Check project config for project_dir
cat forge_output/{project}/forge.config.json
```

Look in: `{project_dir}/docs/`, `{project_dir}/requirements/`, `{project_dir}/spec/`, `{project_dir}/README.md`, and any other documentation directories.

For EACH document found, register it as a knowledge object:

```bash
python -m core.knowledge add {project} --data '[{
  "title": "Source: {filename}",
  "category": "source-document",
  "content": "File: {relative_path}\nType: {type}\nTrust: {trust_level}\nSections: {count}",
  "source": {"type": "documentation", "ref": "{relative_path}"},
  "tags": ["source-document", "{type}"],
  "scopes": ["{relevant_scopes}"]
}]'
```

**Trust levels:**
- **HIGH**: Signed specs, ADRs, contracts, existing codebase, API schemas
- **MEDIUM**: PRDs, design docs, meeting notes, README
- **LOW**: Emails, chat exports, brainstorm notes, undated docs

---

## Step 2 — Extract Facts Per Document

For EACH registered document, read it thoroughly looking for:

| What to extract | Knowledge category | Example |
|----------------|-------------------|---------|
| Verifiable requirements ("must", "shall", "required") | `requirement` | "System must support 500 concurrent users" |
| Business rules and constraints | `domain-rules` | "Invoices must be approved by manager before payment" |
| Technical decisions (explicit) | `architecture` | "We use PostgreSQL 15 for persistence" |
| Technical context (implicit) | `technical-context` | "The team uses Python, existing services are on AWS" |
| API contracts and interfaces | `api-reference` | "POST /users returns 201 with {id, email}" |
| Integration points | `integration` | "Connects to SAP ERP via REST API" |
| Infrastructure info | `infrastructure` | "Deployed on AWS ECS Fargate" |
| Business context | `business-context` | "500 internal users, peak at month-end" |

**Extraction rules:**
- Extract what is **explicitly stated**, not inferred
- Preserve original wording in the `text` — do not rephrase
- Note the **source section** (file:section or file:line range)
- Assign trust level from the source document

Create a Research record for the extraction:

```bash
python -m core.research add {project} --data '[{
  "title": "Ingestion: {filename}",
  "topic": "Extract structured facts from {filename}",
  "category": "ingestion",
  "summary": "Extracted {N} requirements, {M} rules, {P} tech context items",
  "skill": "ingest",
  "file_path": "{relative_path}",
  "key_findings": ["Req: {requirement 1}", "Rule: {rule 1}", ...],
  "tags": ["ingestion"]
}]'
```

Create Knowledge objects for extracted facts:

```bash
python -m core.knowledge add {project} --data '[
  {
    "title": "{short requirement description}",
    "category": "requirement",
    "content": "{full requirement text with context}",
    "source": {"type": "documentation", "ref": "{file}:{section}"},
    "tags": ["{domain}", "requirement"],
    "scopes": ["{relevant_scopes}"]
  },
  {
    "title": "{business rule}",
    "category": "domain-rules",
    "content": "{rule with context and conditions}",
    "source": {"type": "documentation", "ref": "{file}:{section}"},
    "tags": ["{domain}"],
    "scopes": ["{relevant_scopes}"]
  }
]'
```

---

## Step 3 — Detect Conflicts

Compare extracted facts across documents. When two documents contradict:

```bash
python -m core.decisions add {project} --data '[{
  "task_id": "INGESTION",
  "type": "risk",
  "issue": "CONFLICT: {doc_a} says {X}, {doc_b} says {Y}",
  "recommendation": "Proceeding with {X} — {reason}. Confirm before planning.",
  "reasoning": "Source A is {trust_level_a}, Source B is {trust_level_b}. Higher trust wins.",
  "confidence": "LOW",
  "severity": "HIGH",
  "status": "OPEN"
}]'
```

**Conflict rules:**
- Surface, do not harmonize. Never merge two conflicting statements.
- Higher trust wins. Same trust → more specific wins.
- Every conflict becomes an OPEN decision — user must confirm.

---

## Step 4 — Verify Completeness

Check the 9 critical categories from the understanding gate:

1. **deployment** — do I know where this runs?
2. **stack** — do I know the tech stack?
3. **users** — do I know who uses this?
4. **data-in** — do I know what data enters?
5. **data-out** — do I know what data leaves?
6. **persistence** — do I know how state is stored?
7. **error-handling** — do I know what happens on failure?
8. **scale** — do I know the expected load?
9. **definition-of-done** — do I know what success looks like?

For each category, one of:
- **KNOWN**: Knowledge object exists with source reference
- **ASSUMED**: No doc states this explicitly — create an assumption for `draft-plan --assumptions`
- **UNKNOWN**: Cannot even assume — create a Decision with `type: "clarification_needed"`

```bash
# For things that need clarification:
python -m core.decisions add {project} --data '[{
  "task_id": "INGESTION",
  "type": "clarification_needed",
  "issue": "Unknown: {category} — {what is missing}",
  "recommendation": "{default assumption if unanswered}",
  "reasoning": "No document addresses this. Default assumption based on: {basis}",
  "confidence": "LOW",
  "status": "OPEN"
}]'
```

---

## Step 5 — Summary

Print ingestion summary:

```
## Ingestion Complete: {project}

Documents registered: {N}
Facts extracted: {total} (requirements: {req_count}, rules: {rule_count}, context: {ctx_count})
Conflicts detected: {conflict_count} (OPEN decisions)
Clarifications needed: {clarification_count} (OPEN decisions)

Understanding coverage:
  KNOWN: {list of covered categories}
  ASSUMED: {list of assumed categories}
  UNKNOWN: {list of uncovered categories}

Next: /plan {project} (or resolve OPEN clarification decisions first)
```

---

## Success Criteria

- Every source document has a K-NNN with `category: source-document`
- Every source document has an R-NNN with `category: ingestion`
- Every verifiable requirement has a K-NNN with `category: requirement`
- Every conflict is recorded as an OPEN decision
- Understanding gate has ≤4 gaps (can proceed to planning)

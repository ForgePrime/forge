---
name: ingest
id: SKILL-INGEST
version: "2.0"
description: "Extract every fact from source documents into structured Forge knowledge."
---

# Document Ingestion

Read source documents and extract **every fact that matters for implementation** — not summaries, but structured, traceable, classified facts.

**The test**: after ingestion, every document sentence that could change what you build is captured as a Knowledge object with source reference.

## Commands

```bash
# Read
python -m core.knowledge read {project}
python -m core.knowledge contract add
python -m core.decisions contract add
python -m core.guidelines contract add

# Write
python -m core.knowledge add {project} --data '[...]'
python -m core.decisions add {project} --data '[...]'
python -m core.guidelines add {project} --data '[...]'
python -m core.research add {project} --data '[...]'
```

---

## Step 1 — Register Documents

For each source document:
1. Assign trust level: HIGH (ADRs, signed specs, API schemas), MEDIUM (PRDs, design docs), LOW (emails, chat, undated)
2. Register as knowledge:
```bash
python -m core.knowledge add {project} --data '[{"title": "Source: {filename}", "category": "source-document", "content": "File: {path}\nType: {type}\nTrust: {level}\nSections: {list}", "source": {"type": "documentation", "ref": "{path}"}, "tags": ["source-document"]}]'
```

---

## Step 2 — Extract Facts

For each document, extract looking for specific answers:

**About the problem**: What is broken? Who suffers? What does success look like?
**About constraints**: What existing systems? What cannot change? Deadlines? Mandated tech stack?
**About scope**: What's included? Excluded? "Later/v2/nice-to-have" → Out of Scope.
**About decisions**: Architecture described? Technologies named? Prior work?

### Classify each fact

| If the fact is... | Create as |
|-------------------|-----------|
| Something testable that MUST be implemented | `category: "requirement"` (Knowledge) |
| Business rule or domain constraint | `category: "domain-rules"` (Knowledge) |
| Technology decision already made | `type: "architecture", status: "CLOSED"` (Decision) |
| Standard/convention to follow | Guideline (weight: must/should/may) |
| Technical context (how things work) | `category: "technical-context"` (Knowledge) |
| API contract or interface | `category: "api-reference"` (Knowledge) |

### Atomization rules (Fidelity Chain)

**One requirement = one testable behavior.**
- If content has "and"/"oraz"/"+"/";" connecting independent behaviors → split into separate K-NNN
- Bad: "System shows eligible invoices list with up/down priority controls and batch approval" (3 requirements)
- Good: K-040 "System shows list of eligible invoices", K-041 "User reorders with up/down controls", K-042 "User batch-approves selected invoices"
- Target: under 200 characters per requirement

### Surface conflicts — do NOT harmonize

When two documents contradict:
1. State both versions explicitly
2. Create OPEN risk decision:
```bash
python -m core.decisions add {project} --data '[{"task_id": "INGESTION", "type": "risk", "issue": "CONFLICT: {doc_a} says X. {doc_b} says Y.", "severity": "HIGH", "status": "OPEN"}]'
```

### Hunt for implicit assumptions

After each document, ask: What data model is assumed? What roles? What happens on error? What scale? What security model?

For each assumption → create OPEN decision:
```bash
python -m core.decisions add {project} --data '[{"task_id": "INGESTION", "type": "architecture", "issue": "ASSUMED: {what}", "reasoning": "Not in docs. Severity if wrong: {HIGH|MED|LOW}", "confidence": "LOW", "status": "OPEN"}]'
```

---

## Step 3 — Verify Completeness

Check 9 critical categories — each must be KNOWN, ASSUMED, or UNKNOWN (never silently missing):

1. deployment, 2. stack, 3. users, 4. data-in, 5. data-out, 6. persistence, 7. error-handling, 8. scale, 9. definition-of-done

For UNKNOWN categories → create `clarification_needed` decision.

Create extraction record per document:
```bash
python -m core.research add {project} --data '[{"title": "Ingestion: {filename}", "topic": "...", "category": "ingestion", "summary": "Extracted {N} requirements, {M} rules, {P} decisions", "key_findings": ["..."], "tags": ["ingestion"]}]'
```

Print summary:
```
Documents: {N} registered
Extracted: {req} requirements, {rule} rules, {dec} decisions, {gl} guidelines
Conflicts: {N} (OPEN risk decisions)
Assumptions: {N} (OPEN decisions)
Coverage: {categories covered}/{9}

Next: /analyze (creates objectives) → /plan (decomposes into tasks)
```

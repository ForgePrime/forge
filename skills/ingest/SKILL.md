---
name: ingest
id: SKILL-INGEST
version: "2.0"
description: "Document ingestion — register, extract, classify, detect conflicts. Transforms chaotic documentation into structured Forge knowledge."
---

# Document Ingestion

Read source documents and extract **every fact that matters for implementation**. Not summaries — structured, traceable, classified facts.

**The test**: after ingestion, every document sentence that could change what you build is captured as a Knowledge object with a source reference. Nothing is silently assumed.

---

## Read Commands

| ID | Command | Returns | When |
|----|---------|---------|------|
| R1 | `cat forge_output/{project}/forge.config.json` | Project dir path | Step 1 |
| R2 | `python -m core.knowledge read {project}` | Existing knowledge (dedup) | Step 1 |
| R3 | `python -m core.knowledge contract add` | Knowledge schema | Reference |
| R4 | `python -m core.decisions contract add` | Decision schema | Reference |
| R5 | `python -m core.guidelines contract add` | Guideline schema | Reference |
| R6 | `python -m core.research contract add` | Research schema | Reference |

## Write Commands

| ID | Command | Creates | When |
|----|---------|---------|------|
| W1 | `python -m core.knowledge add {project} --data '[...]'` | Source-document registry + extracted facts | Steps 1-2 |
| W2 | `python -m core.decisions add {project} --data '[...]'` | Conflicts, assumptions, clarifications | Steps 2-3 |
| W3 | `python -m core.guidelines add {project} --data '[...]'` | Standards and conventions from docs | Step 2 |
| W4 | `python -m core.research add {project} --data '[...]'` | Extraction record per document | Step 2 |

---

## Step 1 — Inventory and Register Documents

### 1a. Scan for documentation

Check project directory for documentation files:
```bash
cat forge_output/{project}/forge.config.json
# Then scan: {project_dir}/docs/, {project_dir}/requirements/, {project_dir}/spec/,
# {project_dir}/README.md, {project_dir}/*.md, and any other doc directories
```

### 1b. Assign trust levels BEFORE reading

For EACH document, assign trust level based on type — not content:

| Trust | Document type | Why |
|-------|--------------|-----|
| **HIGH** | ADRs, signed specs, contracts, API schemas, existing codebase | Reflects actual decisions |
| **MEDIUM** | PRDs, design docs, meeting notes, README, onboarding docs | Reflects intent, may be outdated |
| **LOW** | Emails, chat exports, brainstorm notes, undated docs | Reflects opinions, often contradictory |

**If a document has no date and you can't determine freshness → LOW.**

### 1c. Register each document

For each document, create a Knowledge object:
```bash
python -m core.knowledge add {project} --data '[{
  "title": "Source: {filename}",
  "category": "source-document",
  "content": "File: {path}\nType: {type}\nTrust: {HIGH|MEDIUM|LOW}\nDate: {date or unknown}\nSections: {section_list}",
  "source": {"type": "documentation", "ref": "{relative_path}"},
  "tags": ["source-document"],
  "scopes": ["{relevant_scopes}"]
}]'
```

---

## Step 2 — Extract Facts Per Document

### 2a. Read with purpose — not to summarize

For each document, read looking for specific answers. Do NOT summarize. Extract.

**About the problem:**
- What is broken or missing that this system fixes?
- Who suffers and how? (tells you what's critical)
- What does success look like to the requester?

**About constraints (non-negotiable):**
- What existing systems must this integrate with? (look for system names, API mentions)
- What cannot be changed? (legacy, regulations, contracts)
- Are there hard deadlines or budget limits?
- What tech stack is mandated vs. casually mentioned?

**About scope:**
- What is explicitly included?
- What is explicitly excluded?
- What is mentioned with "later", "v2", "ideally", "nice to have"? → Out of Scope

**About decisions already made:**
- Is architecture described or implied?
- Are technologies named as decisions or examples?
- Has someone already built part of this?

### 2b. Classify each extracted fact

For each fact, determine what it is:

| If the fact is... | Create as | Forge entity |
|-------------------|-----------|-------------|
| Something that MUST be implemented and can be tested | `category: "requirement"` | Knowledge K-NNN |
| A business rule or domain constraint | `category: "domain-rules"` | Knowledge K-NNN |
| An explicit technology decision | `type: "architecture"`, `status: "CLOSED"` | Decision D-NNN |
| A standard/convention to follow | `weight: "must"` or `"should"` | Guideline G-NNN |
| Technical context (how things work) | `category: "technical-context"` | Knowledge K-NNN |
| API contract or interface spec | `category: "api-reference"` | Knowledge K-NNN |
| Integration point with external system | `category: "integration"` | Knowledge K-NNN |
| Infrastructure/deployment info | `category: "infrastructure"` | Knowledge K-NNN |
| Business context (users, scale, goals) | `category: "business-context"` | Knowledge K-NNN |

**Requirement rules:**
- Must be **verifiable** — "system handles errors properly" is NOT a requirement, it's vague. "API returns 500 with error_id on unhandled exception" IS a requirement.
- Preserve **original wording** in content. Add your interpretation separately.
- Include **source reference**: `source.ref: "spec.md:Section 3.2"`

**Atomization rules (Fidelity Chain):**
- One requirement = one testable behavior. If a requirement sentence contains "and" / "oraz" / "+" / ";" connecting independent behaviors, split into separate K-NNN objects.
- Example BAD: "System shows eligible invoices list with up/down priority controls and batch approval" — this is 3 requirements.
- Example GOOD: K-040 "System shows scrollable list of eligible invoices for upcoming Auto-Buy run", K-041 "User can reorder invoice priorities with up/down controls", K-042 "User can batch-approve selected invoices"
- The `knowledge add` command will warn on compound patterns. Fix them before proceeding.
- Target: under 200 characters per requirement. Longer usually means compound.

### 2c. Hunt for implicit assumptions

After reading each document, ask:
- What data model is assumed but never described?
- What user roles are assumed but never listed?
- What happens on error — is any error handling implied?
- What volume/scale is assumed?
- What security model is assumed?
- What does "the user" mean — one type or many?

**When you spot an implicit assumption**: create a Decision immediately:
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "INGESTION",
  "type": "architecture",
  "issue": "ASSUMED: {what you assumed}",
  "recommendation": "{your assumption}",
  "reasoning": "Not stated in docs. Basis: {why this is most likely}. Severity if wrong: {HIGH|MED|LOW}",
  "confidence": "LOW",
  "status": "OPEN",
  "decided_by": "claude"
}]'
```

### 2d. Detect and surface conflicts

**Critical rule: surface, do NOT harmonize.**

When two documents contradict:
1. State both versions explicitly
2. State which you chose and why (higher trust wins)
3. Create OPEN risk decision:

```bash
python -m core.decisions add {project} --data '[{
  "task_id": "INGESTION",
  "type": "risk",
  "issue": "CONFLICT: {doc_a} ({trust_a}) says {X}. {doc_b} ({trust_b}) says {Y}.",
  "recommendation": "Proceeding with {X} — higher trust source. Confirm before planning.",
  "reasoning": "Source A: {trust_a}, Source B: {trust_b}. Higher trust wins.",
  "confidence": "LOW",
  "severity": "HIGH",
  "status": "OPEN"
}]'
```

**Never merge two conflicting statements into one that sounds like they agreed.**

### 2e. Extract guidelines

When a document states standards, conventions, or rules:
```bash
python -m core.guidelines add {project} --data '[{
  "title": "{standard name}",
  "scope": "{backend|frontend|database|general|...}",
  "content": "{full text of the standard}",
  "rationale": "From {document}, trust: {level}",
  "weight": "{must|should|may}",
  "tags": ["{relevant_tags}"]
}]'
```

**Weight rules:**
- `must` — explicit requirement ("MUST use TypeScript", "SHALL encrypt at rest")
- `should` — strong recommendation ("should follow REST conventions")
- `may` — optional preference ("may use Redis for caching")

### 2f. Create extraction record

For each document, create a Research object:
```bash
python -m core.research add {project} --data '[{
  "title": "Ingestion: {filename}",
  "topic": "Extract structured facts from {filename}",
  "category": "ingestion",
  "summary": "Extracted {N} requirements, {M} rules, {P} decisions, {Q} guidelines. Trust: {level}.",
  "skill": "ingest",
  "file_path": "{relative_path}",
  "key_findings": ["{fact 1}", "{fact 2}", ...],
  "tags": ["ingestion"]
}]'
```

---

## Step 3 — Verify Completeness

### 3a. Distrust these patterns

If you extracted any of these, slow down:
- **"Simple X"** — nothing is simple. What specifically does X do?
- **"Standard Y"** — standard according to whom?
- **"Handle Z"** — handle how? What's the expected behavior?
- **"Integrate with..."** — via what protocol? Who owns the API?
- **"Users can manage..."** — CRUD? Partial? What permissions?
- **"Secure"** — auth? Encryption? Audit logs?
- **"Scalable"** — from what to what?
- **"Real-time"** — <100ms? <1s? WebSocket? Polling?

Each pattern needs a concrete interpretation. If you can't determine it from docs → Decision with `type: "clarification_needed"`.

### 3b. Check 9 critical categories

For each category, write KNOWN or ASSUMED:

1. **deployment** — where does it run?
2. **stack** — what language/framework/database?
3. **users** — who uses it, what roles?
4. **data-in** — what data enters?
5. **data-out** — what data leaves?
6. **persistence** — how is state stored?
7. **error-handling** — what happens on failure?
8. **scale** — expected load?
9. **definition-of-done** — what does success look like?

- **KNOWN**: Knowledge object exists with source reference
- **ASSUMED**: No doc states it → create Decision (type=architecture, status=OPEN)
- **UNKNOWN**: Cannot even assume → create Decision (type=clarification_needed, status=OPEN)

```bash
# For unknowns that block planning:
python -m core.decisions add {project} --data '[{
  "task_id": "INGESTION",
  "type": "clarification_needed",
  "issue": "{category}: {what is unknown}",
  "recommendation": "{default assumption if unanswered}",
  "reasoning": "No document addresses this. If unanswered, proceed with default.",
  "confidence": "LOW",
  "status": "OPEN"
}]'
```

### 3c. Print summary

```
## Ingestion Complete: {project}

Documents: {N} registered ({HIGH_count} HIGH, {MED_count} MEDIUM, {LOW_count} LOW trust)
Extracted: {req_count} requirements, {rule_count} rules, {dec_count} decisions, {gl_count} guidelines
Conflicts: {conflict_count} (OPEN risk decisions)
Assumptions: {assumption_count} (OPEN decisions)
Clarifications needed: {clarification_count} (OPEN decisions)

Knowledge coverage:
  KNOWN: {categories with knowledge}
  ASSUMED: {categories with assumptions only}
  UNKNOWN: {categories with clarification_needed}

Next: resolve OPEN clarifications, then /analyze (creates objectives with KRs) → /plan (decomposes into tasks linked to objectives)
NOTE: /plan requires objectives. Always run /analyze before /plan when source documents are ingested.
```

---

## Success Criteria

- Every source document has K-NNN (source-document) + R-NNN (ingestion record)
- Every verifiable requirement has K-NNN (category=requirement) with source.ref
- Every standard/convention has G-NNN with scope + weight
- Every explicit decision has D-NNN (type=architecture, status=CLOSED)
- Every assumption has D-NNN (status=OPEN) with severity
- Every conflict has D-NNN (type=risk, status=OPEN)
- Every unknown has D-NNN (type=clarification_needed, status=OPEN)
- 9 critical categories: each KNOWN, ASSUMED, or UNKNOWN (none silently skipped)

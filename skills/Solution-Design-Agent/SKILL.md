---
name: solution-design-agent
description: >
  Use this skill when working as a Solution Design Agent to create design documents AND implementation plans from business requirements or existing documentation. Trigger whenever a user wants to: design a solution, create an implementation plan, turn design docs into actionable dev tasks, analyze uploaded business documents into structured deliverables, or asks "what should we build and how". This skill covers the full workflow from vision through to a ready-to-implement plan. Use it especially when the user uploads documents to input/ or asks to generate IMP-001 implementation plan documents.
---

# Solution Design Agent

You create design documents and implementation plans that let you (or a dev team) start building immediately — no follow-up questions needed.

**The only test for IMP-001**: after reading it, can you open an editor and know what to build first — without asking anything? If not, fix the document.

**The only test for QA-001**: after reading it, does the human know exactly what decisions they need to make — and what will be built if they don't answer? If not, fix the questions.

---

## Directory Structure

```
workspaces/
├── input/                    # User uploads go here
└── design-documents/
    ├── QA-001-[name].md      # Clarification doc — created instead of IMP-001 when input is too chaotic
    └── IMP-001-[name].md     # Implementation plan — single output, always
```

**One document rule**: Architecture decisions, risks, and dependencies all live inside IMP-001.
Separate ARC-001, RSK-001, DEP-001 files create desynchronization — two places to update,
two places to contradict each other, one of which the developer will not read.
The only exception: if architecture decisions are genuinely complex enough to require their
own document (e.g. multi-system migration with 10+ ADRs), create ARC-001 and cross-reference
it from IMP-001. Do not create it by default.

---

## Step 1: Extract from input documents

This is the most important step. A bad extraction produces a plan with hidden holes — everything looks complete but key things are missing or wrong. Take time here.

### 1a. Inventory and rank documents before reading

Before extracting anything, look at what you have and assign trust levels:

| Trust level | Document type | Why |
|-------------|--------------|-----|
| HIGH | Architecture Decision Records, signed-off specs, contracts, existing codebase | Reflects actual decisions made |
| MEDIUM | PRDs, design docs, meeting notes | Reflects intent, may be outdated or aspirational |
| LOW | Emails, chat exports, brainstorm notes | Reflects opinions, often contradictory |

If a document has no date and you can't determine freshness → treat as LOW.
If documents conflict → higher trust wins. If same trust level conflicts → more specific wins. Document the conflict as HIGH priority Open Question regardless.

**Critical rule on conflicts: surface, do not harmonize.**
The failure mode is: two documents disagree, agent picks one silently, plan proceeds as if no conflict existed. Developer builds the wrong thing.

Correct behavior for every `[CONFLICT]` tag:
1. State both versions explicitly: "Document A (HIGH) says X. Document B (LOW) says Y."
2. State which you chose and why: "Proceeding with X — higher trust source."
3. Write it as HIGH Open Question in IMP-001: "Conflict: A says X, B says Y. Proceeding with X. Confirm before Phase 1."

Never merge two conflicting statements into one that sounds like they agreed. They did not.

### 1b. Read each document with these questions in mind

Don't just read and summarize. Read looking for answers to specific questions:

**About the problem:**
- What is broken or missing today that this system fixes?
- Who suffers from this problem and how? (tells you what's truly critical)
- What does success look like to the person who asked for this?

**About constraints (non-negotiable):**
- What existing systems must this integrate with? (look for system names, API mentions)
- What cannot be changed? (legacy systems, regulations, existing contracts)
- Are there hard deadlines or budget limits?
- What tech stack is mandated vs. just mentioned casually?

**About scope:**
- What is explicitly included?
- What is explicitly excluded?
- What is mentioned but with "later", "v2", "ideally", "nice to have"? → Out of Scope

**About decisions already made:**
- Is the architecture described or just implied?
- Are specific technologies named as decisions or as examples?
- Has someone already built part of this? (look for "existing", "current", "already have")

**About what's missing:**
- After reading, what questions remain unanswered that would block implementation?
- What did the author assume the reader already knows?

### 1c. Hunt for implicit assumptions

While reading, actively look for things no one wrote down because they seemed obvious to the author. These are the most dangerous gaps — they won't appear in any checklist.

Ask yourself after each document:
- What data model is assumed but never described?
- What user roles are assumed but never listed?
- What happens on error — is any error handling implied?
- What volume/scale is assumed? (often completely absent)
- What security model is assumed?
- What does "the user" mean — one type or many types?
- What does "done" mean to the author — and is it the same as what the developer would assume?

When you spot an implicit assumption: write it down immediately with a severity estimate. Do not wait until 1g — you will forget it.

**On classifying ambiguous statements**: "We want PostgreSQL" is a WISH unless there is a signed spec, contract, or ADR behind it. When in doubt: lower trust. Treat it as ASSUMED in 1g and note the source as LOW trust.

### 1d. Spot-check for document completeness

After extracting, check what categories of information are completely absent. Absent ≠ not needed — absent means you need to assume.

Run this checklist against your extraction:

- [ ] Do I know the deployment target? (cloud/on-prem/serverless/hybrid)
- [ ] Do I know the primary tech stack?
- [ ] Do I know who the users are and how they access the system?
- [ ] Do I know how data enters the system?
- [ ] Do I know how data leaves the system?
- [ ] Do I know what persists and where?
- [ ] Do I know what happens when things fail?
- [ ] Do I know the expected scale? (even rough order of magnitude)
- [ ] Do I know what "done" looks like from the requester's perspective?

Every "no" becomes an assumption. Write it down before moving to Step 2.

### 1e. Review assumptions for internal consistency

Read all your ASSUMED lines together. Write answers to these two questions before moving on:

**Question 1: What worries me most about these assumptions, and why?**
Write 2–5 sentences. This is not a checklist — it is a thinking step. The goal is to surface the assumption combination that is most likely to be wrong or most expensive if wrong.

Example: "The biggest risk is auth model + multi-tenancy. I assumed single-tenant but the docs mention 'client organizations' three times without defining what that means. If this is multi-tenant, the data model changes significantly. Second risk: I assumed the external ERP is accessible via REST but no API documentation was provided."

**Question 2: Are there any pairs of assumptions that cannot both be true at the same time?**
Only write this if you find one. If you find none, write "No incompatible pairs found."

Example: "ASSUMED serverless deployment + ASSUMED persistent WebSocket connections — these are incompatible. Resolution: switch to polling or move to containers. Choosing containers, noted in assumptions."

If any concern from Q1 or Q2 cannot be resolved without external input → do NOT proceed. Add it to QA-001. This is the same gate as CONFLICT: if you cannot resolve it alone, it becomes a question, not an assumption.

Do not carry unresolved incompatibilities into Architecture Decisions.

### 1g. Step 1 exit gate — mandatory before proceeding to Step 2

**Do not move to Step 2 until you can produce this output in writing.**

Go through the completeness checklist from 1d item by item and write one of two things for each:

- **KNOWN**: `[category] → [concrete answer from documents, source: document name/trust level]`
- **ASSUMED**: `[category] → [your assumption] | Reason: [why this is most likely] | Severity if wrong: HIGH/MED/LOW`

Example of acceptable output:
```
Deployment target → KNOWN: Azure AKS, source: ADR-003 (HIGH trust)
Tech stack        → ASSUMED: Python 3.11 + FastAPI | Reason: team uses Python per onboarding docs, FastAPI is standard for new APIs in this org | Severity: MED
Users             → ASSUMED: two roles — admin and viewer | Reason: docs mention "access control" without detail; two-role model is most common starting point | Severity: HIGH
Scale             → ASSUMED: <500 concurrent users | Reason: internal tool, company has 300 employees | Severity: LOW
Error handling    → ASSUMED: structured JSON errors with HTTP codes | Reason: REST API context, no custom format mentioned | Severity: LOW
```

If you cannot write KNOWN or ASSUMED for every checklist item — you have not finished reading the documents. Go back.

**Severity definition — apply this here, not from the Assumptions section:**

- **HIGH**: you don't know what the answer would be, OR you can guess but being wrong would change the architecture or data model
- **MED**: you have a reasonable basis for the assumption and being wrong would change one component's design but not the overall structure
- **LOW**: you have a clear basis and being wrong would change an implementation detail only

When in doubt: assign HIGH. MED and LOW require a positive justification for why the risk is limited. "I think it's probably fine" is not a justification — that's HIGH.

**Hard stop rule: count your HIGH-severity ASSUMED lines.**

- 0–2 HIGH ASSUMED: proceed to Step 2.
- 3–4 HIGH ASSUMED: proceed, but flag IMP-001 header as "High assumption risk — verify before Phase 1."
- 5+ HIGH ASSUMED: **do not create IMP-001.** Instead, create QA-001 (see below).

**QA-001 — Questions Before Planning**
When input is too chaotic to plan from, produce this instead of IMP-001:

```markdown
# QA-001 — [Solution Name] Clarification Required

## Why this document exists instead of IMP-001
Planning would require [N] high-risk assumptions. Building on these without confirmation
risks delivering the wrong system. The questions below, answered, would reduce this to
a plannable state.

## Questions (answer all before requesting IMP-001)

### Q1: [Question — specific, not open-ended]
**Why this matters**: [what changes in the plan depending on the answer]
**If you cannot answer now, the default assumption is**: [what we'd proceed with, and the consequence]

### Q2: ...
```

Rules for QA-001 questions:
- Each question has exactly one decision it unlocks
- Each question states the default assumption if unanswered — so the human can approve the assumption instead of answering from scratch
- Maximum 7 questions — if you have more than 7, the scope is unclear and that itself is a question

**QA-001 re-entry — what happens after the human answers:**

When answers arrive, treat them as HIGH-trust input and re-run from Step 1 exit gate (1g):
1. Convert each answered question to a KNOWN line in the 1g table
2. Convert each approved default assumption to an ASSUMED line with severity downgraded by one level (HIGH→MED, MED→LOW) — because the human reviewed it
3. Recount HIGH-severity ASSUMED lines
4. If now below threshold → proceed to Step 2 and create IMP-001
5. If still 5+ HIGH ASSUMED after answers → create QA-001 v2 with only the remaining unresolved questions. Maximum one additional round. If after two QA-001 rounds the input is still too chaotic, state this explicitly: "Scope is insufficiently defined to plan. Recommend a scoping workshop before returning to this process."

**The failure mode this prevents**: agent produces IMP-001 with 12 HIGH assumptions, developer builds for 3 weeks, client says "but we already have X" on demo day. QA-001 surfaces the ambiguity before planning, not after building.

### 1f. Distrust these patterns in documents

When you see these, slow down — they often hide important gaps:

- **"Simple X"** — nothing is simple. What specifically does X do?
- **"Standard Y"** — standard according to whom? Which standard?
- **"The system should handle Z"** — handle how? What's the expected behavior?
- **"Integrate with [external system]"** — via what protocol? Who owns the API? Is it documented?
- **"Users can manage their [entity]"** — CRUD? Partial? With what permissions?
- **"Secure"** — means what exactly? Auth? Encryption at rest? In transit? Audit logs?
- **"Scalable"** — from what to what? What's the current load vs. target load?
- **"Real-time"** — means what? <100ms? <1s? WebSocket? Polling at 5s?

Every one of these patterns needs a concrete interpretation before you can design anything.

---

## Step 2: Design architecture (becomes a section in IMP-001, not a separate file)

Do this before writing IMP-001. It forces you to design the system before breaking it into tasks.
The output of this step is the "Architecture Decisions" section inside IMP-001 — not a separate file.

### What feeds Architecture Decisions from Step 1

This is the explicit bridge. Take your tagged extraction and route it:

| Tag from Step 1 | Goes into Architecture Decisions (IMP-001) as |
|----------------|----------------------|
| `[DECISION]` | "Architecture Decisions" section in IMP-001 — list as closed, with reason from docs |
| `[CONSTRAINT]` | "Constraints" section — these shape all architecture choices |
| `[IMPLICIT]` about tech/infra | Starting point for assumptions, then design around them |
| `[REQ]` grouped by domain | Drives the component list and data flow |
| `[CONFLICT]` about tech | Note as unresolved in Architecture Decisions, pick one to design around |

`[WISH]` and `[VAGUE]` do NOT feed Architecture Decisions — they go to Out of Scope and Open Questions in IMP-001.

### What Architecture Decisions must answer (in this order)

Each answer constrains the next:

1. **Where does it run?** — deployment target: cloud + provider, on-prem, serverless, container, hybrid
2. **What are the hard boundaries?** — what's inside this system vs. external dependency
3. **What's the data model skeleton?** — main entities, what persists vs. transient. Not full schema.
4. **What's the tech stack?** — language, framework, database, key libraries. Derive from `[DECISION]` + `[CONSTRAINT]` first. For remaining gaps, use this context decision tree:
   - Cloud provider named in docs → use that provider's native services first (AWS → Lambda/RDS, Azure → Functions/SQL, GCP → Cloud Run/CloudSQL)
   - Existing codebase language visible → match it, do not introduce a second language
   - Enterprise context (large company, compliance mentioned, existing IT dept) → managed services, established frameworks, avoid bleeding edge
   - Startup / greenfield / "move fast" context → lightweight stack, fewer managed services, optimize for iteration speed
   - No context signals at all → Postgres for persistence, REST over HTTP, containerized deployment. These are the defaults because they have the widest hiring pool, best tooling, and fewest surprises. Document this reasoning explicitly.
5. **What are the main data flows?** — how data enters, moves through, exits. 3–5 flows max. More = too detailed.
6. **What are the integration points?** — external systems, their protocols, who owns them

### Architecture exit gate — traceability and consistency check

Before writing IMP-001 tasks, produce two outputs:

**Output A: Decision traceability**
Every technology choice in Architecture Decisions must trace to a source. Write one line per choice:

```
[Technology choice] → source: [DECISION tag from doc X] / [ASSUMED — reason] / [default — reason]
```

Example:
```
PostgreSQL         → source: ASSUMED — no DB mentioned, relational data model evident from REQ tags, team size suggests ops familiarity with Postgres, default choice
Azure Functions    → source: DECISION — ADR-002 (HIGH trust): "all new services use serverless"
Python 3.11        → source: ASSUMED — existing codebase in Python (seen in repo link in onboarding doc, MEDIUM trust)
FastAPI            → source: default — no framework specified, FastAPI is standard for Python REST APIs with async support
```

Any technology choice with no source line is a gap. Fill it before writing IMP-001 tasks.

**Output B: Consistency verification**
Rerun the same pairs from 1e against the now-written Architecture Decisions (not against assumptions — against actual choices made):

```
Deployment ↔ Runtime: [actual choice] + [actual choice] = OK / CONFLICT
Scale ↔ Database: [actual choice] + [actual choice] = OK / CONFLICT  
Connectivity ↔ Deployment: [actual choice] + [actual choice] = OK / CONFLICT
Integration ↔ Network: [actual choice] + [actual choice] = OK / CONFLICT
Data needs ↔ Storage: [actual choice] + [actual choice] = OK / CONFLICT
```

Any CONFLICT here means your architecture is internally inconsistent. Fix it before IMP-001.
A CONFLICT found here that was not caught in 1e means an assumption changed during design — note why.

---

## Step 3: Create IMP-001

```markdown
# IMP-001 — [Solution Name] Implementation Plan

## TL;DR
What this is, why it exists, and the single most consequential technical decision.
3–5 sentences max. If you can't summarize it in 5 sentences, you don't understand it yet.

## Project is done when...
One or two sentences. Observable, not vague.
Example: "User can submit an invoice via the API, it is persisted in the DB,
and a confirmation email is sent. All endpoints return correct status codes for
happy path and main error cases."

## Out of Scope
Explicit list of things NOT being built now.
This prevents scope creep during implementation.
- [Feature or concern explicitly excluded — and why if it was mentioned in docs]

## Environment & Deployment Target
- Runtime: [e.g. Python 3.11 on AWS Lambda / Node 20 on Fly.io / Java 21 in Docker on GKE]
- Database: [engine + where hosted]
- External services this integrates with: [list]
- Local dev setup: [how to run it locally — even if just "TBD, assume docker-compose"]

## Architecture Decisions
Every technology choice with its source. Replaces separate ARC-001 file.
Format: all entries are rows in the table — no mixing table and narrative blocks.

| Area | Decision | Source |
|------|----------|--------|
| Deployment | [where it runs] | DECISION: [doc] / ASSUMED: [reason] / default: [reason] |
| Runtime | [language + version] | DECISION: [doc] / ASSUMED: [reason] / default: [reason] |
| Framework | [framework] | DECISION: [doc] / ASSUMED: [reason] / default: [reason] |
| Database | [engine + hosting] | DECISION: [doc] / ASSUMED: [reason] / default: [reason] |
| Auth | [auth mechanism] | DECISION: [doc] / ASSUMED: [reason] / default: [reason] |
| Data flow 1 | [how data enters: caller → entry point → action] | DECISION / ASSUMED / default |
| Data flow 2 | [core processing path] | DECISION / ASSUMED / default |
| Data flow 3 | [how data exits: trigger → output → destination] | DECISION / ASSUMED / default |
| Integration: [SystemName] | [protocol], [who owns API], [docs at: URL or UNKNOWN] | DECISION / ASSUMED / default |

Add rows as needed. Remove rows that don't apply. One format throughout — no separate narrative blocks below the table.


## Assumptions
Every gap in documentation becomes an explicit assumption here.
Never silently assume — if you assumed it, it goes here.

| ID | Assumption | Why this is the most likely answer | Risk if wrong |
|----|-----------|-------------------------------------|----------------|
| A1 | [what you assumed] | [reasoning from context] | [consequence + severity: LOW/MED/HIGH] |

Severity guide:
- HIGH = would change the architecture
- MED = would change a component design
- LOW = would change an implementation detail

## Components to Build

Run this completeness checklist first. Every checked item must appear as a component
below, or have an explicit note explaining why it's not needed for this solution.

- [ ] Authentication / authorization — or: "not needed because [reason]"
- [ ] Data persistence layer — or: "not needed because [reason]"
- [ ] Business logic / core processing
- [ ] API / interface layer (how callers interact)
- [ ] Error handling strategy — or: "handled inline in each component, because [reason]"
- [ ] Logging / observability — or: "not needed because [reason]"
- [ ] Background jobs / async processing — or: "not needed because [reason]"
- [ ] External integrations — or: "none"
- [ ] Configuration management — or: "not needed because [reason]"

For each component:

### [Component Name]
**What it does**: one sentence
**Input**: exact format / trigger / caller
**Output**: exact format / side effects / what changes in the world
**Depends on**: components or external systems that must exist first
**Non-obvious logic**: only what's genuinely unclear or tricky — skip boilerplate
**Size**: S (hours) / M (1–2 days) / L (3+ days)

Size determines where AC lives — pick one, not both:
- **S component** → write AC inline here (1–2 criteria sufficient)
- **M or L component** → write a one-line placeholder here, full AC in the AC section

Inline placeholder format: `AC: → see AC section`
Inline full format:
- Given [state], when [action], then [observable result]
- Error case: given [failure], then [expected behavior]

No exceptions for "boring" components. If you can't write an AC, you don't understand the component — clarify the component definition first.

**AC quality test — for every criterion you write, check it against these examples:**

Bad AC (cannot verify):
- "User authentication works correctly"
- "Data is saved to the database"
- "Errors are handled properly"
- "The API returns appropriate responses"

Good AC (can verify by running or checking something):
- "Given valid credentials POST /auth/login returns 200 with JWT token in body; token decodes to correct user_id"
- "Given invoice submission, within 2s a row exists in invoices table with status='pending' and all submitted fields"
- "Given unhandled exception in any endpoint, response is 500 with body {error_id: uuid, message: 'internal error'}; same uuid appears in logs with full stack trace"
- "Given request missing Authorization header, response is 401 with body {error: 'unauthorized'}; no database query is made"

The pattern: Good AC specifies the exact starting state, the exact action, and the exact observable result — including where to look (table name, HTTP status, log line, file path). Bad AC describes intent, not behaviour.

## Implementation Order

### How to phase — write the dependency graph first, phases second

**This is a two-stage process. Do not skip to writing phases.**

**Stage A: Write the dependency graph (required artefact)**

Before writing any phase, produce this explicitly:

```
Component dependency graph:
[Component A] → no dependencies
[Component B] → no dependencies
[Component C] → depends on: A
[Component D] → depends on: A, B
[Component E] → depends on: C, D

Derived layers:
Layer 1 → A, B         (no dependencies)
Layer 2 → C, D         (depend only on Layer 1)
Layer 3 → E            (depends on Layer 2)
```

If you cannot produce this graph, you do not understand the components well enough to phase them.
Go back and fix the "Depends on" field for each component first.

**Hidden dependency checklist — run before closing Stage A:**

For every component in the graph, answer these mechanically:

- Does this component **write** data anywhere? If yes: is the schema/table/format it writes to defined by another component? → that component is a dependency.
- Does this component **read** data? If yes: is there a component that creates that data? → that component is a dependency.
- Does this component call an **external system**? If yes: is there a config/credential component that provides the connection? → that component is a dependency.
- Does this component require **authentication context** (user ID, role, token)? If yes: is there an auth component that provides it? → that component is a dependency.

If any answer reveals a dependency not already in the graph → add it now. A dependency discovered here is better than one discovered in Phase 2.

**Known limit of this checklist**: it finds missing edges in a correctly defined component graph. It does not find incorrectly merged components (two things treated as one) or missing components entirely. Those are caught by Step 4 external verification — not by this checklist. Do not treat a clean checklist as proof the graph is correct.

**Stage B: Convert layers to phases**

- One layer = one phase, unless size check fails
- 2–6 tasks per phase is correct. 7+ → split by independent sub-areas. 1 task → merge with adjacent phase unless it is a genuine hard gate (e.g. external API key required, infra must be provisioned first).
- Name phases by what they deliver: "Working data pipeline", "User-facing API", "Auth and access control" — not "Backend", "Phase 2", "Remaining work"

Ordering within a phase:
- Schema / data model before anything that writes data
- Config and secrets loading before anything that uses them
- Core happy-path logic before error handling and edge cases
- Internal APIs before external-facing APIs
- Sync flow before async — add queues/workers after core flow works

**The failure mode this prevents**: phases invented intuitively instead of derived from dependencies. Developer in Phase 2 discovers they need a component scheduled for Phase 3. Plan collapses at first task breakdown.

### Phase 1: [What this delivers]
Depends on: nothing
- [ ] [Specific task — concrete enough to start coding without clarification]
- [ ] [Next task]

**Exit gate**: [Specific thing you can run, call, or check to confirm phase complete]

### Phase 2: [What this delivers]
Depends on: Phase 1 exit gate
- [ ] [Task]

**Exit gate**: [...]

(add phases as needed — derived from dependency graph above, not invented arbitrarily)

## Acceptance Criteria

Write full AC here for every M and L component (those with `AC: → see AC section` placeholder above).
S components are already covered inline — do not duplicate them here.

### AC: [Component Name]  ← M or L components only
- [ ] Given [starting state], when [action taken], then [specific observable result]
- [ ] Given [starting state], when [action taken], then [specific observable result]
- [ ] Error case: given [failure condition], then [expected behavior]
- [ ] Edge case: given [unusual but valid input], then [expected behavior]

Rule: every AC must be verifiable by running a test, making a request, or checking
a file/DB state. "Works correctly" is not an AC.

## Open Questions

Things that could change the plan. Sorted by impact.

| Priority | Question | Impact if answered differently | Current assumption |
|----------|----------|-------------------------------|-------------------|
| HIGH | [question] | [what changes in architecture] | [what you assumed] |
| MED | [question] | [what changes in a component] | [what you assumed] |
| LOW | [question] | [what changes in a detail] | [what you assumed] |

HIGH = resolve before starting Phase 1 if possible
MED = resolve before the phase they affect
LOW = resolve at implementation time
```

---

## Step 4: External verification

**Run this if a second agent or human reviewer is available. If not, skip to delivery with the flag below.**

If a reviewer is available, pass them IMP-001 + all original input documents with this prompt:

> "Read these documents and then read IMP-001. Find the first thing you would need to clarify before writing any code. Do not look for formatting issues — look for missing information, ambiguous requirements, or assumptions that seem wrong."

- If reviewer finds something → add it to Assumptions or Open Questions, fix, re-deliver.
- If reviewer finds nothing → deliver without flag.

If no reviewer is available: add this line to the IMP-001 header and deliver:
`⚠️ NOT EXTERNALLY VERIFIED — self-certified only. Validate HIGH assumptions before Phase 1.`

**Honest note**: the flag is a disclaimer, not verification. External review with a genuinely independent agent who has not seen the planning process is the only mechanism that catches semantic errors — wrong assumptions that look internally consistent. If this matters for the project, invest in setting up multi-agent review before running this skill.

---

## Quality Check Before Delivering

**Primary test** (run this first):
Read IMP-001 as if you have never seen the input documents. Can you open an editor and know what to build first — without looking anything up? If no: find the gap and fix it. If yes: run the three structural checks below.

**Structural checks** (catch common omissions):
- [ ] Every component has at least one AC that names a specific observable result (table row, HTTP status, log entry, file). None say "works correctly."
- [ ] Phases were derived from the dependency graph. Every phase has an exit gate you can actually run or check.
- [ ] Every HIGH assumption has a note on when it will be resolved (before Phase 1, before Phase N, or never — and if never, why that's acceptable).

If any structural check fails: fix it, re-run the primary test.

**Known limit**: this check catches structural gaps. It does not catch semantic gaps — wrong assumptions that look internally consistent. Only Step 4 external verification catches those. A document that passes this check is structurally complete, not necessarily correct.

---

## What NOT to write

- NFRs without numbers ("must be fast", "must be secure") — useless
- Stakeholder lists with job titles — irrelevant to building
- Timeline with calendar dates — you don't know when work starts
- "Business value" prose that repeats the TL;DR
- Anything you would skip when actually reading this before coding
- Risks as a separate document — they live in Assumptions and Open Questions

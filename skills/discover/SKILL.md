---
name: discover
id: SKILL-DISCOVER
version: "1.1"
description: "Discovery phase — explore options, assess feasibility, analyze risks, and design architecture before planning."
---

# Discover

Discovery answers: "What should we build, is it feasible, what are the risks, and how should we architect it?"

Deep-* skills (`skills/deep-*/SKILL.md`) provide methodology. This skill coordinates analyses and records findings.

> **Note:** `deep-feasibility` lives in `skills/optional/deep-feasibility/SKILL.md`, not `skills/deep-*/`.

**Pipeline position**: `/ingest -> /analyze -> /discover -> /plan -> /run`

## When NOT to Discover

Go straight to `/plan` when:
- Scope is well-defined and small (< 5 tasks)
- Technology and patterns already established in codebase
- No architectural decisions — just implementation
- Low risk, obvious feasibility (CRUD, bugfix, config)

---

### Step 0 — Verify Source Documents

```bash
python -m core.knowledge read {project} --category source-document
```

If documents should exist but none registered: tell user to run `/ingest` and **STOP**.

---

### Step 1 — Scope & Ceremony Level

If discovering for an entity, read its context (do not re-align):
```bash
python -m core.ideas show {project} {idea_id}       # or objectives show
```

If general topic — confirm scope (1-2 questions max).

Load domain-specific questions:
```bash
python -m core.domain_modules for-scopes --scopes "{scopes}" --phase vision
```

**Ceremony level:**

| Level | When | Effect |
|-------|------|--------|
| **LIGHT** (default) | Single concern, known domain | 1 analysis, short record, compact brief |
| **FULL** | `--full`, or auto: cross-cutting, multi-domain, high stakes | Multiple analyses, full record, cross-analysis synthesis |

Auto-detect FULL when 2+ of: multiple scopes, high-severity risks, architectural decisions needed, uncertain feasibility.

**Which analyses:**

| Intent | Analyses |
|--------|----------|
| "What should we do?" | Explore |
| "Should we do X?" | Explore + Feasibility |
| "How to build X?" | Explore + Architecture |
| "Is X risky?" | Risk |
| `--full` | All available |

---

### Step 2 — Gather Context

```bash
python -m core.pipeline status {project}
python -m core.decisions read {project} --status OPEN
python -m core.guidelines context {project} --scopes "{scopes}"
python -m core.lessons read-all
```

`must` guidelines = hard constraints. `should` = note deviations.

---

### Step 3 — Analyze

Order: Explore first, then Feasibility/Risk/Architecture in parallel.

For each analysis, follow the corresponding `deep-*/SKILL.md`. Do not replicate their methodology here.

**Stop conditions:**
- **Feasibility = NO-GO**: STOP. Present to user.
- **Risk = CRITICAL**: Flag prominently. User decides.

---

### Step 4 — Cross-Analysis Synthesis (FULL only)

Follow `skills/deep-aggregate/SKILL.md` for methodology. Key focus areas:

**4a. Contradictions** — Compare conclusions across analyses.
Example: Feasibility=GO but Risk=CRITICAL. What risk did feasibility miss?

**4b. Blind spots** — What did no analysis cover?
Common: operational complexity, migration path, team capability.

**4c. Emergent insights** — 1-3 findings that no single analysis would surface.
Example: "Recommended caching architecture eliminates top performance risk but introduces a consistency risk neither analysis flagged."

---

### Step 5 — Record Findings

If no project exists: `python -m core.pipeline init {slug} --goal "Discovery: {topic}"`

Use `contract` subcommands for field formats (`python -m core.research contract add`, `python -m core.decisions contract add`).

**Update source entity status** (if discovering for an idea/objective):
```bash
python -m core.ideas update {project} --data '[{"id": "{idea_id}", "status": "EXPLORING"}]'
```

**LIGHT**: 1 research object + 1-2 OPEN decisions.
**FULL**: 1 research per analysis + decisions (explorations, risks, architectural).

Example:
```bash
python -m core.research add {project} --data '[{"title": "Explore: {topic}", "topic": "{question}", "category": "domain", "summary": "{key finding}", "skill": "deep-explore", "content": "{full markdown}", "key_findings": ["..."], "scopes": ["..."]}]'
```

Link decisions back: `python -m core.research update {project} --data '[{"id": "R-001", "decision_ids": ["D-001"], "status": "ACTIVE"}]'`

---

### Step 6 — Discovery Brief

Adapt to what was done. Only include relevant sections.

**Always:**
- **Summary** — what was analyzed, key conclusion (2-4 sentences)
- **Recommended Direction** — what to build and why
- **Open Decisions** — list requiring user input before `/plan`
- **Next Steps** — `/decide`, then `/plan {goal}` or `/discover {sub-topic}`

**When relevant:**
- **Cross-Analysis Conflicts** — contradictory conclusions
- **Cross-Cutting Insights** — synthesis from Step 4 (FULL)
- **Top Risks** — if risk analysis performed
- **Feasibility Verdict** — if feasibility analysis performed

---

## Success Criteria

- Findings recorded as research + OPEN decisions with recommendations
- User can make GO / NO-GO decision
- If GO: output ready for `/plan`
- FULL: cross-analysis synthesis covers contradictions, blind spots, emergent insights

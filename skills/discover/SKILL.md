---
name: discover
id: SKILL-DISCOVER
version: "1.1"
description: "Discovery phase — explore options, assess feasibility, analyze risks, and design architecture before planning."
---

# Discover

Discovery answers: "What should we build, is it feasible, what are the risks, and how should we architect it?"

Deep-* skills (`skills/deep-*/SKILL.md`) provide methodology. This skill coordinates analysis and records findings in Forge.

**In the full document-to-code pipeline**: `/ingest → /analyze → /discover → /plan → /run`
Discover comes AFTER analyze (objectives exist) but BEFORE plan (tasks don't exist yet). Use when objectives need deeper technical investigation before decomposing into tasks.

Provenance: [Deep-Process](https://github.com/Deep-Process/deep-process).

---

### Step 0 — Document Ingestion

Before analyzing, check if source documents exist but haven't been ingested:

```bash
python -m core.knowledge read {project} --category source-document
python -m core.research read {project} --category ingestion
```

If documentation files exist in the project but no `source-document` knowledge registered:
1. Check `forge_output/{project}/forge.config.json` for `project_dir`
2. Scan for docs in `{project_dir}/docs/`, `{project_dir}/requirements/`, etc.
3. If found, **follow the ingest skill procedure** (`skills/ingest/SKILL.md`)

If source-documents are registered but some lack ingestion research:
- Ingest unprocessed documents before proceeding.

Load extracted knowledge as context:
```bash
python -m core.knowledge read {project} --category requirement
python -m core.knowledge read {project} --category domain-rules
```

---

### Step 1 — Scope & Approach

**If discovering for an idea/objective**, read its existing alignment — do NOT re-align:
```bash
python -m core.ideas show {project} {idea_id}       # or objectives show
```

The source entity already has description, scopes, and context. Use that. Only ask if discovery scope differs from the entity's scope (1-2 questions max).

**If discovering a general topic** (no entity), briefly confirm scope.

Load domain-specific questions:
```bash
python -m core.domain_modules for-scopes --scopes "{scopes}" --phase vision
```

Then determine which analyses are needed:

| User intent / flag | Analyses | Read methodology from |
|--------------------|----------|----------------------|
| "What should we do?" (open) | Explore | `deep-explore/SKILL.md` |
| "Should we do X?" (evaluate) | Explore + Feasibility | + `optional/deep-feasibility/SKILL.md` |
| "How should we build X?" (design) | Explore + Architecture | + `deep-architect/SKILL.md` |
| "Is X risky?" / `--risk-only` | Risk | `deep-risk/SKILL.md` |
| "Full analysis" / `--full` | All four | All deep-* skills |

Read each needed skill's SKILL.md and `references/` directory for methodology.

---

### Step 2 — Gather Context

**If a project exists:**
```bash
python -m core.pipeline status {project}
python -m core.decisions read {project} --status OPEN
python -m core.lessons read-all
python -m core.guidelines context {project} --scopes "{scopes}"
```

**If no project yet:**
```bash
python -m core.lessons read-all
```

For brownfield projects, also read: directory structure, key config files, existing architecture.

**Guidelines as constraints**: `must` weight = hard constraints (analyses MUST NOT violate). `should` weight = soft constraints (note deviations).

---

### Step 3 — Analyze

Run analyses in dependency order:
1. **Explore first** (provides option map for all others)
2. **Then in parallel**: Feasibility, Risk, Architecture (each builds on explore output)

For each analysis, follow the methodology from the deep-* SKILL.md you read in Step 1. Key outputs per analysis:

| Analysis | Key Output |
|----------|-----------|
| deep-explore | Option map, knowledge audit, consequence trace, recommendation |
| deep-feasibility | GO / CONDITIONAL / NO-GO verdict with evidence |
| deep-risk | Risk register (5D scoring), interactions, mitigations with Cobra Effect check |
| deep-architect | Components, C4 diagrams, ADRs, adversarial findings |

**If feasibility = NO-GO**: STOP. Present to user. Do NOT auto-proceed.
**If risk = CRITICAL**: Flag prominently but continue. User decides.

After all analyses, synthesize: identify cross-analysis contradictions, agreements, and gaps. This replaces the separate aggregate step — you already have all findings in context.

---

### Step 4 — Record Findings

If no project exists, create one:
```bash
python -m core.pipeline init {slug} --goal "Discovery: {topic}"
```

**Determine task_id for decisions:**
- Discovering for **idea** (e.g., `/discover I-001`): use idea ID. Update status to EXPLORING:
  ```bash
  python -m core.ideas update {project} --data '[{"id": "{idea_id}", "status": "EXPLORING"}]'
  ```
- Discovering for **objective** (e.g., `/discover O-001`): use `"DISCOVERY"`. Set `linked_entity_type: "objective"`, `linked_entity_id: "O-001"` on risk decisions.
- **General topic**: use `"DISCOVERY"`.

**Record in this order:**

**a. Research objects** — persist full analysis output per completed analysis:
```bash
python -m core.research add {project} --data '[{
  "title": "...", "topic": "...", "category": "...",
  "summary": "...", "skill": "deep-explore",
  "linked_entity_type": "idea", "linked_entity_id": "I-001",
  "content": "{full analysis markdown}",
  "key_findings": ["..."], "scopes": ["..."], "tags": ["..."]
}]'
```
The `content` field auto-generates `file_path` and writes the research file.

**b. Exploration decisions** (type=exploration) — one per analysis phase:
Use `exploration_type`, `findings`, `options`, `open_questions`, `evidence_refs` (research file path).
Set `status: "OPEN"`, `decided_by: "claude"`.

**c. Risk decisions** (type=risk) — from risk analysis:
Use `severity`, `likelihood`, `mitigation_plan`, `linked_entity_type/id`.

**d. Standard decisions** — significant findings (architecture, implementation, etc.):
Use appropriate `type` with `alternatives`, `evidence_refs`.

**e. Lessons** (optional) — if significant cross-project insights emerged.

**f. Update research with decision IDs:**
```bash
python -m core.research update {project} --data '[{"id": "R-001", "decision_ids": ["D-001", "D-002"], "status": "ACTIVE"}]'
```

**g. Promote to Knowledge** (optional) — only for durable findings that should persist as living docs:
- Architecture design → `category: "architecture"`
- Domain rules → `category: "domain-rules"`
- Integration patterns → `category: "integration"`

Do NOT promote one-time assessments (feasibility, risk register, option comparison) — those stay as Research/Decisions.

---

### Step 5 — Present Discovery Brief

```
## Discovery Brief: {topic}

### Summary
| Analysis | Key Finding |
|----------|-------------|
| Explore | {1-line: recommended option + rationale} |
| Feasibility | {GO/CONDITIONAL/NO-GO} |
| Risk | {top risk + composite score} |
| Architecture | {key ADR or design decision} |

### Recommended Direction
{1-2 paragraphs: what to build and why, informed by all analyses}

### Cross-Analysis Conflicts
{Any contradictions between analyses and how they were resolved}

### Open Decisions ({N} recorded)
{List OPEN decisions requiring user input before /plan}

### Top Risks
{Top 3 risks with proposed mitigations}

### Next Steps
- [ ] Review and close OPEN decisions with `/decide`
- [ ] When ready: `/plan {recommended goal}`
- [ ] Or: `/discover {sub-topic}` for deeper analysis
```

---

## Success Criteria

- At least explore + one other analysis (risk, feasibility, or architect) completed
- Findings recorded as OPEN decisions with clear recommendations
- User has enough information to make a GO / NO-GO decision
- If GO: output is ready to feed into `/plan`

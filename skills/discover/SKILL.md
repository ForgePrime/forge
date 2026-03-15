---
name: discover
id: SKILL-DISCOVER
version: "1.0"
description: "Discovery phase — explore options, assess feasibility, analyze risks, and design architecture before planning."
---

# Discover

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-DISCOVER |
| Version | 1.0 |
| Description | Orchestrate deep-* analysis skills to explore what to build, assess risks, and prepare architecture before committing to a plan. |

## Read Commands

| ID | Command / Path | Returns | When |
|----|----------------|---------|------|
| R1 | `skills/deep-align/SKILL.md` | Alignment procedure | Step 2 — before analysis |
| R2 | `skills/deep-explore/SKILL.md` | Exploration procedure | Step 3 — resolve skills |
| R3 | `skills/deep-risk/SKILL.md` | Risk analysis procedure | Step 3 |
| R4 | `skills/deep-architect/SKILL.md` | Architecture procedure | Step 3 |
| R5 | `skills/optional/deep-feasibility/SKILL.md` | Feasibility procedure | Step 3 |
| R6 | `skills/optional/deep-requirements/SKILL.md` | Requirements procedure | Step 3 (optional) |
| R7 | `python -m core.lessons read-all` | Lessons from past projects | Step 4 — context |
| R8 | `python -m core.decisions read {project} --status OPEN` | Open decisions (if project exists) | Step 4 — context |
| R9 | `ls forge_output/ 2>/dev/null` | Existing projects | Step 4 — context |
| R10 | `python -m core.pipeline status {project}` | Current pipeline state | Step 4 — context (if project exists) |
| R11 | `python -m core.guidelines context {project} --scopes "{idea_scopes}"` | Applicable guidelines (constraints for analysis) | Step 4 — context |
| R12 | `python -m core.decisions contract add` | Contract for recording decisions | Step 6 — before recording |
| R13 | `python -m core.lessons contract` | Contract for recording lessons | Step 6 — before recording |
| R14 | `python -m core.research contract add` | Contract for recording research | Step 5 — before recording |
| R15 | `python -m core.research contract update` | Contract for updating research | Step 6 — before updating |
| R16 | `python -m core.domain_modules for-scopes --scopes "{s}" --phase vision` | Domain-specific questions | Step 2.5 — after alignment |

## Write Commands

| ID | Command | Effect | When | Contract |
|----|---------|--------|------|----------|
| W1 | `python -m core.decisions add {project} --data '{json}'` | Records discovery findings as decisions | Step 6 — after analysis | `decisions:add` |
| W2 | `python -m core.lessons add {project} --data '{json}'` | Records discovery insights as lessons | Step 6 — significant learnings | `lessons:add` |
| W3 | `python -m core.decisions add {project} --data '{json}'` | Records exploration decisions (type=exploration) | Step 6 — after each analysis phase | `decisions:add` |
| W4 | `python -m core.decisions add {project} --data '{json}'` | Records risk decisions (type=risk) | Step 6 — from risk analysis | `decisions:add` |
| W5 | `python -m core.pipeline init {slug} --goal "..."` | Creates project if none exists | Step 6 — before recording | — |
| W6 | `python -m core.ideas update {project} --data '{json}'` | Updates idea status to EXPLORING | Step 6 — if idea-scoped | `ideas:update` |
| W7 | `python -m core.research add {project} --data '{json}'` | Creates R-NNN research object AND writes research file (via `content` field) | Step 5 — after each skill completes | `research:add` |
| W9 | `python -m core.research update {project} --data '{json}'` | Updates R-NNN (add decision_ids, set ACTIVE) | Step 6 — after recording decisions | `research:update` |

## Output

| File | Contains | Written by |
|------|----------|------------|
| `forge_output/{project}/decisions.json` | All discovery findings: standard decisions (W1), exploration decisions (W3), and risk decisions (W4) | W1, W3, W4 |
| `forge_output/{project}/lessons.json` | Discovery insights (if significant) | W2 |
| `forge_output/{project}/research/*.md` | Full deep-* analysis outputs (written by core.research via `content` field) | W7 |
| `forge_output/{project}/research.json` | Structured research objects (R-NNN) linking analyses to entities | W7, W9 |

## Success Criteria

- deep-orchestration was used to coordinate analysis skills (not ad-hoc)
- At least deep-explore + one other skill (risk, feasibility, or architect) completed
- Findings recorded as OPEN decisions with clear recommendations
- User has enough information to make a GO / NO-GO decision
- If GO: output is ready to feed into `/plan`
- Full analysis outputs persisted to `research/` directory with evidence_refs in decisions

## References

- `docs/DESIGN.md` — Architecture overview
- `docs/STANDARDS.md` — Skill standards
- External: deep-orchestration, deep-explore, deep-risk, deep-architect SKILLs (in `skills/`)
- Optional: deep-feasibility, deep-requirements SKILLs (in `skills/optional/`)

---

## Overview

Discovery is the phase BEFORE planning. It answers: "What should we build, is it feasible, what are the risks, and how should we architect it?" — by coordinating deep-* analysis skills in a dependency-aware sequence.

This skill is the bridge between Forge (execution engine) and deep-* analysis skills. Forge provides project context; this skill coordinates analysis; Forge records the results.

## Prerequisites

- User has a topic, question, or proposed direction to explore
- If exploring within an existing project: project exists in forge_output/

Note: Core deep-* analysis skills are built into Forge under `skills/deep-*`. Optional skills (deep-feasibility, deep-requirements) are under `skills/optional/deep-*`.
Provenance: [Deep-Process](https://github.com/Deep-Process/deep-process).

---

### Step 1 — Align on Discovery Scope (medium alignment per `skills/deep-align/SKILL.md`)

Before running analysis, build shared understanding of what to explore:

**a. Restate** the exploration topic: "You want to explore X to understand Y."
Get confirmation before proceeding.

**b. Ask scoping questions** — only where you'd have to guess:
- **Scope:** "Should I explore just X, or also its interaction with Y?"
- **Constraints:** "Any options/technologies already ruled out?"
- **Priority:** "What's most important to learn — feasibility, risks, or architecture?"

Group questions in one message (1-3 questions max). If exploring a specific idea
(`/discover I-001`), the idea's description provides most context — ask fewer questions.

**c. If user says "just explore"** — proceed but focus on the broadest applicable scope.

---

### Step 1.5 — Load Domain Questions

After alignment, load domain-specific vision questions:

```bash
python -m core.domain_modules for-scopes --scopes "{scopes}" --phase vision
```

Ask domain-specific questions from the output alongside generic alignment questions.
Cap at 6-8 questions total across generic + domain-specific. If entity has no scopes
yet, determine them from the description (see scope discovery in `skills/domain-modules/SKILL.md`).

---

### Step 3 — Determine Analysis Skills

Based on the confirmed scope (or explicit flags), determine which analysis skills are needed:

| User intent / flag | Required skills | Optional |
|--------------------|----------------|----------|
| "What should we do?" (open exploration) | deep-explore | deep-feasibility, deep-risk |
| "Should we do X?" (evaluating a proposal) | deep-explore, deep-feasibility | deep-risk |
| "How should we build X?" (design question) | deep-explore, deep-architect | deep-requirements |
| "Is X risky?" / `--risk-only` | deep-risk | deep-explore, deep-feasibility |
| "Full analysis" / `--full` | deep-explore, deep-feasibility, deep-risk, deep-architect | deep-requirements |

Read each needed skill from `skills/deep-{name}/SKILL.md` (or `skills/optional/deep-{name}/SKILL.md` for deep-feasibility and deep-requirements) and its `references/` directory (if present).

---

### Step 4 — Gather Forge Context

Before running analysis, gather project context to feed into the deep-* skills:

**If a project exists:**
```bash
python -m core.pipeline status {project}
python -m core.decisions read {project} --status OPEN
python -m core.lessons read-all
```

**If no project yet:**
```bash
python -m core.lessons read-all
```

Also read the codebase if it's a brownfield project:
- Directory structure
- Key config files
- Existing architecture patterns

**Load applicable guidelines as constraints:**
```bash
python -m core.guidelines context {project} --scopes "{idea_scopes_or_general}"
```

Guidelines with weight `must` are **hard constraints** — deep-* skills MUST NOT propose options that violate them. Guidelines with weight `should` are **soft constraints** — deep-* skills may propose alternatives but must note the deviation.

Pass these constraints as context when executing each deep-* skill in Step 5.

Compile this as context input for the orchestrator.

---

### Step 5 — Execute via deep-orchestration

Follow the deep-orchestration SKILL.md procedure:

1. **Define** — subject is the user's discovery topic, with Forge context gathered in Step 4
2. **Sequence** — build the dependency graph for selected skills:

```
Typical discovery flow:
  deep-explore ──→ deep-feasibility ──→ deep-risk
                                    └──→ deep-architect
```

Skills that can run in parallel (no output dependencies):
- deep-risk and deep-architect can run concurrently AFTER deep-explore
- deep-feasibility can run in parallel with deep-risk if both only need explore output

Skills that must be sequential:
- deep-explore FIRST (provides option map for all others)
- deep-feasibility after deep-explore (needs options to evaluate)

3. **Execute** — run each skill per its SKILL.md procedure

After each skill completes, persist its full output via `core.research add` with the `content` field (W7). The core module writes the research file to disk automatically — **do NOT write files directly**.

Load the research contract first:
```bash
python -m core.research contract add
```

Then record the research object per the contract. Key fields: `title`, `topic`, `category`, `summary`, `linked_entity_type`, `linked_entity_id`, `skill`, `content` (full analysis markdown), `key_findings`, `scopes`, `tags`.

The `content` field causes the core module to:
1. Auto-generate `file_path` as `research/{skill}-{slug}.md`
2. Write the markdown file to that path
3. Store the file_path reference in research.json

This creates a DRAFT research object. It will be updated to ACTIVE with decision_ids after Step 6.

4. **Aggregate** — combine outputs per deep-orchestration Step 5

Track execution:

| Step | Skill | Status | Key Output |
|------|-------|--------|------------|
| 1 | deep-explore | pending | Option map, knowledge audit |
| 2 | deep-feasibility | pending | GO/CONDITIONAL/NO-GO verdict |
| 3 | deep-risk | pending | Risk register, top risks |
| 4 | deep-architect | pending | Components, ADRs, C4 diagrams |

---

### Step 6 — Record Findings in Forge

After orchestration completes, record findings as structured artifacts.

If no project exists yet, create one with a slug derived from the topic:
```bash
python -m core.pipeline init {slug} --goal "Discovery: {topic}"
```

Determine the context for recording:
- If discovering for a **specific idea** (e.g., `/discover I-001`): use the idea ID as `task_id` for all decisions (exploration, risk, and standard). Also update idea status to EXPLORING if it's still DRAFT (W6):
```bash
python -m core.ideas update {project} --data '[{"id": "{idea_id}", "status": "EXPLORING"}]'
```
- If discovering for a **specific objective** (e.g., `/discover O-001`): use `"DISCOVERY"` as `task_id` for decisions (objectives are not valid task_ids). Set `linked_entity_type: "objective"` and `linked_entity_id: "O-001"` on risk decisions. Load the objective context:
```bash
python -m core.objectives show {project} {objective_id}
python -m core.ideas read {project} --status APPROVED
```
Filter to ideas advancing this objective — their exploration notes provide additional context.
- If discovering a **general topic** (no idea, no objective): use `"DISCOVERY"` as task_id.

Load contracts before recording (one call covers all decision types):
```bash
python -m core.decisions contract add
python -m core.lessons contract
python -m core.research contract update
```

**a. Record exploration decisions (W3):**

For each analysis phase completed, create an exploration decision per the decisions contract.
Use `type: "exploration"` with `exploration_type`, `findings`, `options`, `open_questions`, `evidence_refs`.
Set `task_id` to the idea ID or `"DISCOVERY"`, `status: "OPEN"`, `decided_by: "claude"`.

For feasibility exploration decisions, also include `blockers` and `ready_for_tracker: true`.

**b. Record risk decisions (W4):**

From deep-risk findings, create risk decisions per the decisions contract.
Use `type: "risk"` with `severity`, `likelihood`, `mitigation_plan`, `linked_entity_type`, `linked_entity_id`.
Set `evidence_refs` to the research file path.

**c. Record standard decisions (W1):**

Translate significant findings into decisions per the decisions contract.
Use appropriate `type` (architecture, implementation, etc.) with `alternatives`, `evidence_refs`.

**d. Record Lessons (W2, optional):**

If significant insights emerged, record per the lessons contract.
Use `category: "pattern-discovered"`, `task_id: "DISCOVERY"`.

**e. Update research objects with decision IDs (W9):**

After recording all decisions, link them to the corresponding R-NNN research objects:
```bash
python -m core.research update {project} --data '[{"id": "R-001", "decision_ids": ["D-001", "D-002"], "status": "ACTIVE"}]'
```

This marks the research as ACTIVE (ready for context loading) and establishes bidirectional linking:
- Research → Decisions (via `decision_ids`)
- Decisions → Research (via `evidence_refs`)

**f. Promote durable findings to Knowledge (optional):**

If discovery produced findings that should persist as **living reference documents** (not one-time analysis), create Knowledge objects. This bridges discovery output (Research = snapshot) to reusable context (Knowledge = evolving).

When to create Knowledge:
- **Architecture design** — component structure, API contracts, data models → `category: "architecture"`
- **Domain rules** discovered during exploration → `category: "domain-rules"`
- **Integration patterns** — how systems connect, auth flows → `category: "integration"`
- **Code patterns** — conventions established during design → `category: "code-patterns"`

When NOT to create Knowledge:
- Feasibility assessment (one-time → stays as Research)
- Risk analysis (one-time → stays as Risk decisions)
- Option comparison (one-time → stays as Exploration decision)

```bash
python -m core.knowledge contract add
python -m core.knowledge add {project} --data '[...]'
```

Set `scopes` matching the objective/idea scopes — this enables `/plan` to find and assign them to tasks via `knowledge_ids`. Link to the source research/objective for traceability.

---

### Step 7 — Present Discovery Brief

Present the combined findings to the user:

```
## Discovery Brief: {topic}

### Orchestration Summary
| Skill | Status | Key Finding |
|-------|--------|-------------|
| deep-explore | done | {1-line summary} |
| deep-feasibility | done | {GO/CONDITIONAL/NO-GO} |
| deep-risk | done | {top risk + score} |
| deep-architect | done | {key ADR} |

### Recommended Direction
{1-2 paragraphs: what to build and why, informed by all analyses}

### Open Decisions ({N} recorded)
{List OPEN decisions requiring user input before /plan}

### Risks to Accept
{Top 3 risks with proposed mitigations}

### Next Steps
- [ ] Review and close OPEN decisions with `/decide`
- [ ] When ready: `/plan {recommended goal}`
- [ ] Or: request deeper analysis on specific aspect
```

Wait for user response. Offer:
- `/decide` to resolve open decisions
- `/plan {goal}` to proceed to execution
- Another `/discover` on a sub-topic for deeper analysis

---

## Error Handling

| Error | Action |
|-------|--------|
| A built-in deep-* SKILL.md missing | Check `skills/` directory. If missing, re-clone Forge. |
| deep-feasibility returns NO-GO | **PAUSE** — present to user. Do NOT proceed to /plan. Ask if they want to explore alternatives. |
| deep-risk finds CRITICAL risk | **FLAG prominently** — but continue analysis. User decides. |
| No project exists yet | Use `task_id: "DISCOVERY"` for all decisions. Create project when user moves to `/plan`. |

## Resumability

- If interrupted: decisions already recorded are persisted (append-only)
- Re-running `/discover` on same topic: analyses will re-run (no state tracks which skills completed), but existing decisions are preserved (dedup by task_id + type + issue)
- Discovery findings persist regardless of whether `/plan` follows

## Integration with Forge Pipeline

`/discover` sits BEFORE `/plan` in the Forge lifecycle:

```
/discover {topic}     ← NEW: explore, assess, design
    ↓
/decide               ← resolve OPEN discovery decisions
    ↓
/plan {goal}          ← decompose into tasks (informed by discovery)
    ↓
/next or /run         ← execute
    ↓
/compound             ← learn
```

Discovery decisions with `task_id: "DISCOVERY"` are visible in `/plan` context, informing task decomposition. Tasks can reference discovery decisions via `blocked_by_decisions`.

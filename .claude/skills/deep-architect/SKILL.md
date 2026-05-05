---
name: deep-architect
id: SKILL-DEEP-ARCHITECT
description: >
  Use when user needs to design software architecture, system design, or
  technical infrastructure. Triggers: "design the architecture", "system design",
  "how should we build this", "architecture for", "design a service".
version: "1.0.0"
allowed-tools: [Read, Glob, Grep, Bash]
---

> **Provenance**: Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-architect` v1.0.0.
> Forge integration: findings recorded as Forge decisions/lessons. See Forge Integration section below.

# Deep Architect

Design software architecture with a built-in adversarial phase that tries to break the design before shipping it.

## What This Adds

Claude already designs systems. This skill adds:
- **Adversarial phase**: 8 operations that systematically attack the design (STRIDE, FMEA, anti-patterns, pre-mortem, dependency analysis, scale stress, cost projection, ops complexity)
- **C4 diagrams** in mermaid (context, container, component)
- **ADRs** with explicit tradeoff documentation
- **Quality attribute tradeoffs** made visible

## Procedure

### Step 1: Context

Gather from the user (or extract from provided materials):
- Functional requirements (what it does)
- Quality attributes: performance targets, availability SLA, security requirements, scalability expectations
- Constraints: technology mandates, team skills, budget, timeline, existing systems
- Integration points: what does this connect to?

Produce a numbered list of requirements and constraints before proceeding.

### Step 2: Design

Produce:
1. **Component decomposition** — what are the pieces and why those boundaries
2. **API boundaries** — how components talk to each other, sync vs async
3. **Data model** — entities, ownership, consistency boundaries
4. **Technology choices** — what and why for each component

Generate **C4 diagrams** in mermaid:
- **Context**: system + external actors/systems
- **Container**: deployment units (services, databases, queues, etc.)
- **Component**: internal structure of key containers

### Step 3: Adversarial

This is the core value. For each significant design decision, run all 8 challenges.
See `references/adversarial-ops.md` for detailed descriptions.

| # | Challenge | Question |
|---|-----------|----------|
| 1 | STRIDE | What are the threats per component? |
| 2 | FMEA | What fails, how, what's the blast radius, how do you detect it? |
| 3 | Anti-pattern check | Is this a known bad pattern? |
| 4 | Pre-mortem | It's 6 months later and this failed. Why? |
| 5 | Dependency analysis | Single points of failure? |
| 6 | Scale stress test | What happens at 10x, 100x load? |
| 7 | Cost projection | What does this cost at scale? |
| 8 | Ops complexity | Who maintains this at 3am? |

Rate each finding: **Critical** / **High** / **Medium** / **Low**.

### Step 4: Tradeoffs

For each significant decision, document:
- "We chose X over Y because Z. We lose A but gain B."

Generate an **ADR** (Architecture Decision Record) for each:

```
### ADR-{N}: {title}
- **Status**: Accepted
- **Context**: {why this decision was needed}
- **Decision**: {what we chose}
- **Alternatives considered**: {what else we looked at}
- **Consequences**: {what we gain, what we lose}
```

### Step 5: Output

Assemble the final architecture document using the format below.

## Output Format

```markdown
# Architecture: {system}

## Overview
{1-paragraph summary: what, why, key quality attributes}

## C4 Diagrams

### Context
```mermaid
{context diagram}
```

### Container
```mermaid
{container diagram}
```

### Component
```mermaid
{component diagram}
```

## Components
| Component | Responsibility | Technology | Interfaces |
|-----------|---------------|------------|------------|
| ... | ... | ... | ... |

## Architecture Decision Records
| ADR | Decision | Rationale | Tradeoff |
|-----|----------|-----------|----------|
| ... | ... | ... | ... |

{Full ADR details below the table}

## Adversarial Findings
| # | Challenge | Finding | Severity | Mitigation |
|---|-----------|---------|----------|------------|
| ... | ... | ... | ... | ... |

## Tradeoffs
| Chose | Over | Because | Lost | Gained |
|-------|------|---------|------|--------|
| ... | ... | ... | ... | ... |
```

## Safety — Bash Usage

- **Read-only by default**: Use Bash only for reading project structure (`ls`, `find`, `cat`) and running diagram validators.
- **No destructive commands**: Do not run `rm`, `mv`, `chmod`, `git push`, or anything that modifies the filesystem or external systems.
- **No installs**: Do not run `npm install`, `pip install`, `apt-get`, or any package manager commands.
- **No network calls**: Do not use `curl`, `wget`, or any command that contacts external services.
- If a Bash command is needed beyond read-only inspection, describe it to the user and ask for confirmation before executing.

## Rules

- Every component must justify its existence (why not merge with neighbor?)
- Every technology choice must name a rejected alternative
- Adversarial phase is not optional — skip nothing
- If a Critical finding has no mitigation, flag it prominently
- C4 diagrams use mermaid syntax for portability
- ADRs are numbered sequentially

---

## Integration with other skills

- **Input from:** `/plan` Faza 2 (system mapping) — existing architecture to build on
- **Output to:** `/deep-risk` (architecture risks), `/plan` Faza 5 (implementation phases from ADRs)
- **constraint:** Architecture must follow `.ai/standards.md` layering: Repository → Mapper → Domain → Service → Router

## Provenance

Adapted from [Deep-Process](https://github.com/Deep-Process/deep-process) `deep-architect` v1.0.0.

---
name: deep-align
id: SKILL-DEEP-ALIGN
version: "1.0"
description: "Build shared understanding before execution. Every assumption is a question."
---

# Deep Align

Build shared understanding before execution. Every assumption is a question.

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-DEEP-ALIGN |
| Version | 1.0 |
| Description | Alignment protocol — restatement, scoping questions, alignment contract. Prevents wasted work from wrong assumptions. |

## Core Rule

**If you need to assume something to proceed — ask instead.**

"Probably means...", "I think they want...", "Most likely..." — these are not
reasons to proceed. They are triggers to ask.

## Procedure

### Step 1: Listen

Read the user's request. Do not respond with a solution. Instead, produce:

**Restatement** — one sentence: "You want X so that Y."

Get confirmation before proceeding. If the restatement is wrong, the rest
will be wrong too.

### Step 2: Find the walls

Identify every dimension where you would need to guess:

| Dimension | Question pattern |
|-----------|-----------------|
| **Scope** | What's in, what's out? |
| **Form** | What should the output look like? |
| **Audience** | Who is this for? |
| **Constraints** | What must it NOT be? What's off limits? |
| **Quality** | How will you judge if this is good? What can you test or observe to verify? |
| **Boundaries** | What is explicitly NOT in scope? (prevents scope creep during execution) |
| **Context** | What do you already know/have that I should use? |
| **Priority** | What matters most if I have to choose? |

Do NOT ask all dimensions every time. Only ask about dimensions where
you genuinely don't know and where guessing wrong would waste time.

Group your questions. One message, not seven.

### Step 3: Map the bucket

From the answers, produce the alignment contract:

```
## Alignment: {task}

**Goal:** {what, in one sentence}
**Output:** {what form — file, answer, code, analysis, plan}
**Boundaries:**
- Must: {non-negotiable requirements}
- Must not: {explicit exclusions}
- Not in scope: {what this work deliberately does NOT cover}
- Prefer: {soft preferences}
**Success:** {how the user will judge if this is right — what they can test, observe, or verify}
```

Show this to the user. Get confirmation. This is the bucket — stay inside it.

### Step 4: Execute with checks

During execution:
- If you hit a fork where both paths seem valid — ask, don't pick.
- If scope feels like it's growing — pause and confirm.
- If your first instinct is to add something "useful" not in the contract — don't.

After first meaningful output, check: "Is this inside the bucket?"

## Adaptation for Forge Commands

Deep-align adapts its depth based on context:

| Context | Alignment depth | What to do |
|---------|----------------|------------|
| `/objective` | **Full** — restatement + find walls + contract | This is the entry point — align thoroughly |
| `/plan {goal}` (direct) | **Medium** — restatement + scope/constraints/quality | Entry point when no objective — align here |
| `/plan I-001` or `/plan O-001` | **Reference** — read existing alignment, ask only gaps | Alignment exists — don't re-do |
| `/discover` | **Reference** — read source entity, ask only scope gaps | Source entity has alignment — don't re-do |
| `/idea` | **Capture** — quick capture, not alignment | Alignment happens at /objective or /plan |
| `/task` | **Light** — mini-align for scope + AC | Already has built-in alignment |
| Direct task execution | **Skip** — task instruction IS alignment | Trust the pipeline |

**When to skip alignment entirely:**
- Task has clear, unambiguous instruction (from pipeline)
- User explicitly says "just do it" (but flag top 2 assumptions)
- Trivial operations (typo fix, config change)

## Rules

- Never skip Step 1 (restatement). Getting this wrong cascades everything.
- Ask only what you genuinely don't know. Don't ask obvious things to perform thoroughness.
- Group questions in one message. Do not interrogate with one question at a time.
- The alignment contract is a living document — if the user changes direction mid-task, update it.
- If the user says "just do it" — do it, but flag your top 2 riskiest assumptions.
- **Have opinions. Push back.** If something is vague, too broad, unrealistic, or a bad idea — say so directly. Don't just ask neutral questions. State your view: "This is too broad because X", "I'd drop Y because Z", "This will fail without W". Influence the user toward better decisions before committing to execution.

## Anti-Patterns

| Anti-Pattern | Why it fails |
|--------------|-------------|
| Asking 15 questions before doing anything | User loses patience, stops engaging |
| Asking obvious things ("what language do you speak?") | Wastes trust |
| Building alignment doc but then ignoring it | Worse than no alignment — false confidence |
| Assuming "they probably mean X" and proceeding | The core problem this skill exists to solve |
| Over-formalizing simple tasks | "Fix this typo" does not need an alignment contract |
| Full alignment on pipeline tasks | Tasks are pre-aligned — executing alignment again wastes time |

## Success Criteria

- [ ] Restatement confirmed before execution began
- [ ] No assumption was made where a question could have been asked
- [ ] Output matches the alignment contract
- [ ] User did not need to redirect more than once

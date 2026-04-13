---
name: review
id: SKILL-REVIEW
version: "1.0"
description: "Structured code review of task changes before completion."
---

## Quick Reference (6 perspectives)

1. Read changes: `changes read {project}` → filter by task_id
2. Review each perspective: Security | Correctness | Architecture | Testing | Decision Audit | Guidelines
3. Mini-verdict per perspective: PASS / CONCERN / FAIL
4. Record findings as decisions
5. Run gates: `gates check {project} --task {task_id}`
6. Final verdict: APPROVED / APPROVED WITH NOTES / NEEDS CHANGES

---

# Review

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-REVIEW |
| Version | 1.0 |
| Description | Review changes made during a task for correctness, security, and quality. |

## Read Commands

| ID | Command | Returns | When |
|----|---------|---------|------|
| R1 | `python -m core.changes read {project} --task {task_id}` | Changes made in this task | Step 1 — understand scope |
| R2 | `python -m core.decisions read {project} --task {task_id}` | Decisions made in this task | Step 1 — understand reasoning |
| R3 | `python -m core.pipeline status {project}` | Pipeline state | Step 1 — context |
| R4 | `python -m core.gates show {project}` | Configured gates | Step 3 — validation |

## Write Commands

| ID | Command | Effect | When |
|----|---------|--------|------|
| W1 | `python -m core.decisions add {project} --data '{json}'` | Records review findings | Step 2 — for issues found |
| W2 | `python -m core.gates check {project} --task {task_id}` | Runs validation | Step 3 — automated checks |
| W3 | `python -m core.lessons add {project} --data '{json}'` | Records review lessons | Step 4 — patterns found |

## Output

| File | Contains |
|------|----------|
| `forge_output/{project}/decisions.json` | Review findings as decisions |
| `forge_output/{project}/lessons.json` | Patterns discovered during review |

## Success Criteria

- Every changed file has been read and reviewed
- Security concerns identified and recorded
- Decisions validated against their reasoning
- Gate checks pass
- No OPEN decisions left unaddressed

---

## Overview

Structured review of changes made during task execution. The review
examines correctness, security, consistency, and whether decisions
were properly justified.

## Prerequisites

- A task has been executed (changes exist)
- The task is IN_PROGRESS or DONE

---

### Step 1 — Understand Scope

Read what was changed and why:

```bash
python -m core.changes read {project} --task {task_id}
```

```bash
python -m core.decisions read {project} --task {task_id}
```

For each changed file, read the actual file to see the current state.

---

### Step 2 — Multi-Perspective Review

Review each changed file through **6 independent perspectives**.
For each perspective, produce a mini-verdict: PASS / CONCERN / FAIL.

---

#### 2A — Security Perspective

Focus: OWASP Top 10, secrets, attack surface.

- **Injection**: SQL, command injection, XSS, path traversal
- **Secrets**: Configure secret scanning as a gate (e.g., `gitleaks detect --no-git -v`).
  Also manually check for hardcoded credentials, API keys, tokens.
- **Auth/AuthZ**: Are authentication and authorization checks in place?
- **Input validation**: Is user input validated at system boundaries?
- **Dependencies**: Are new dependencies from trusted sources? Known CVEs?

Mini-verdict: `Security: {PASS|CONCERN|FAIL} — {1-line summary}`

---

#### 2B — Correctness Perspective

Focus: Does the code do what was asked? Does it break anything?

- Does the implementation match the task instruction?
- Are edge cases handled (null, empty, overflow, concurrent access)?
- Are error paths properly handled (not swallowed)?
- Do the changes break any existing functionality?
- Are return types and interfaces consistent?

Mini-verdict: `Correctness: {PASS|CONCERN|FAIL} — {1-line summary}`

---

#### 2C — Architecture Perspective

Focus: Design patterns, SOLID, coupling, cohesion.

- Does the code follow existing patterns in the codebase?
- Is the abstraction level appropriate (not over/under-engineered)?
- Are responsibilities properly separated?
- Does this introduce tight coupling or circular dependencies?
- Is the naming clear and consistent?

Mini-verdict: `Architecture: {PASS|CONCERN|FAIL} — {1-line summary}`

---

#### 2D — Testing Perspective

Focus: Testability, coverage gaps, test quality.

- Are the changes testable? (pure functions, injectable dependencies)
- Are tests included if the task required them?
- Do existing tests still pass? (gates will verify, but check logic)
- Are there untested critical paths?
- Do tests test behavior, not implementation details?

Mini-verdict: `Testing: {PASS|CONCERN|FAIL} — {1-line summary}`

---

#### 2E — Decision Audit Perspective

Focus: Were decisions properly justified and recorded?

- Does each recorded decision have valid reasoning?
- Were alternatives properly considered?
- Any LOW confidence decisions that need escalation?
- Are there unrecorded decisions (choices made without a decision record)?
- Do decisions align with project-level patterns from lessons?

Mini-verdict: `Decisions: {PASS|CONCERN|FAIL} — {1-line summary}`

---

#### 2F — Guidelines Compliance

Focus: Were project guidelines followed?

```bash
python -m core.guidelines context {project} --scopes "{task_scopes}"
python -m core.changes read {project} --task {task_id}
```

For each `must` guideline:
- Check if the code changes comply
- Check if `guidelines_checked` in change records includes this guideline
- If violated: FAIL with specific guideline ID and violation

For each `should` guideline:
- Check compliance; note deviations as CONCERN (not FAIL)

Record any findings:
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "{task_id}",
  "type": "convention",
  "issue": "Guideline {G-NNN} compliance: {title}",
  "recommendation": "{compliant|violated|partially}",
  "reasoning": "{what was checked and found}"
}]'
```

Mini-verdict: `Guidelines: {PASS|CONCERN|FAIL} — {1-line summary}`

---

For each CONCERN or FAIL, record a finding as a decision:

```bash
python -m core.decisions add {project} --data '[{
  "task_id": "{task_id}",
  "type": "security|implementation|architecture|testing",
  "issue": "Review finding: ...",
  "recommendation": "Fix: ...",
  "reasoning": "Why this matters: ...",
  "confidence": "HIGH",
  "status": "OPEN",
  "decided_by": "claude"
}]'
```

---

### Step 3 — Run Automated Checks

```bash
python -m core.gates check {project} --task {task_id}
```

If gates fail, record findings as OPEN decisions.

---

### Step 4 — Extract Patterns

If the review reveals reusable patterns or common mistakes:

```bash
python -m core.lessons add {project} --data '[{
  "category": "pattern-discovered|mistake-avoided",
  "title": "...",
  "detail": "...",
  "task_id": "{task_id}",
  "severity": "critical|important|minor",
  "applies_to": "...",
  "tags": ["..."]
}]'
```

---

### Step 5 — Report

Present review results with per-perspective verdicts:

```
## Review: {task_id} — {task_name}

### Perspectives
| Perspective | Verdict | Summary |
|-------------|---------|---------|
| Security | PASS/CONCERN/FAIL | {1-line} |
| Correctness | PASS/CONCERN/FAIL | {1-line} |
| Architecture | PASS/CONCERN/FAIL | {1-line} |
| Testing | PASS/CONCERN/FAIL | {1-line} |
| Decisions | PASS/CONCERN/FAIL | {1-line} |
| Guidelines | PASS/CONCERN/FAIL | {1-line} |

### Files Reviewed
- file1.py — OK
- file2.py — 1 issue (OPEN decision D-NNN)

### Findings (if any)
- D-NNN: {issue} — {recommendation}

### Gates
- test: PASS
- lint: PASS
- secrets: PASS

### Verdict
APPROVED — all perspectives PASS
APPROVED WITH NOTES — CONCERNs noted but non-blocking
NEEDS CHANGES — FAIL in N perspectives (N open decisions)
```

---

## Error Handling

| Error | Action |
|-------|--------|
| No changes for task | Nothing to review — skip |
| Security issue found | Record as OPEN decision with HIGH priority |
| Gate failure | Record finding, recommend fix |
| Decision without reasoning | Flag as incomplete |

## Resumability

- Review findings are persisted as decisions immediately
- Lessons are persisted immediately
- Can be re-run safely (dedup in decisions prevents duplicates)

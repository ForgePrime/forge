# AI-Native Software Delivery Manifesto

**Contract-Governed AI Delivery (CGAID)**

Version 1.0 · 2026-04-19

---

## Core Thesis

**AI will write our code.**
**We decide under what discipline it operates.**

---

## Principles

### 1. AI operates under contract, not assumption.

AI must expose uncertainty, assumptions, and incomplete work.
Silence is treated as a defect.

### 2. We trust evidence, not fluent output.

Every non-trivial claim must be:

- **CONFIRMED** — verified
- **ASSUMED** — explicitly stated
- **UNKNOWN** — resolved or escalated

### 3. Understanding precedes implementation.

We challenge requirements for inconsistencies before planning or coding begins.

### 4. The plan exposes risk, not just work.

We identify decisions, risks, and edge cases before writing code.

### 5. Tests target failure, not just success.

Edge cases and failure modes are first-class.
Happy paths are insufficient.

### 6. Code is not the outcome. Verified behavior is.

Work is complete only when the intended business result is observed.

### 7. Review and verification are mandatory.

Every change must be reviewed, tested, and validated against intent.

### 8. Business intent and implementation remain connected.

Requirements, decisions, code, and validation must be traceable end-to-end.

### 9. We control our tools.

We build, adapt, and improve our AI toolkit.
What does not work is removed.

### 10. Every failure improves the system.

Each incident must result in a rule, test, or tooling improvement.
If it does not, the system is incomplete.

---

## Operational Rules

### Adaptive rigor

We apply the level of discipline based on risk:

- **Fast Track** — minimal overhead for low-risk changes
- **Standard** — full delivery loop
- **Critical** — full traceability and formal validation

### Decision rule

Unknowns must be resolved, explicitly accepted, or escalated.
They must never be ignored.

### Anti-bureaucracy clause

If the framework increases effort without reducing risk or improving outcomes, it must be simplified.

---

## Definition of Done

Work is complete only when:

- the behavior matches the intended outcome
- edge cases are verified
- assumptions are resolved or explicitly accepted
- the change is reviewed
- the result is validated in the target context

---

## Closing

**AI amplifies the system it operates in.**
**We built a system that amplifies engineering discipline.**

---

## Governance

- **Status:** Cultural foundation — this document defines what is true and what is required; the operational *how* lives in `OPERATING_MODEL.md`.
- **Review cadence:** annual — and whenever a principle is violated without consequence
- **Change process:** a principle may only be changed if a delivered incident demonstrates it was wrong or incomplete; language refinement follows the framework change process

### Changelog

- **v1.0 (2026-04-19)** — Initial published manifesto. Ten principles, three operational rules, five-criterion global Definition of Done. Adopted as the cultural foundation of Contract-Governed AI Delivery.

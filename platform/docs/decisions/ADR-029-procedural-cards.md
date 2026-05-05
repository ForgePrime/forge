# ADR-029 — Procedural Cards as Framework-Level Skill Specification

## Status

PROPOSED — DRAFT pending distinct-actor review per [ADR-003](ADR-003-human-reviewer-normative-transition.md).

## Date

2026-05-05

## Context

CGAID framework (`.ai/framework/`) describes:

- cultural foundation (`MANIFEST.md`),
- operational structure — layers, stages, artifacts, metrics (`OPERATING_MODEL.md`),
- Stage 0 instrument (`DATA_CLASSIFICATION.md`),
- empirical foundation (`PRACTICE_SURVEY.md`),
- public case (`WHITEPAPER.md`).

It does **NOT** specify a deterministic procedure for execution — how a contributor moves from "task arrives" to "task closed." That procedural knowledge exists in `platform/docs/USAGE_PROCESS.md` and `platform/docs/MASTER_IMPLEMENTATION_PLAN.md`, but only as Forge-specific instantiations.

Without a framework-level procedural abstraction:

- Repeatability across teams or alternative tooling requires reading `platform/` source code.
- The position from `FRAMEWORK_MAPPING.md §0` ("Forge is a platform-level reference implementation, not the framework itself") is undermined at the procedural layer — there is no framework-level procedure for Forge to be a reference implementation OF.
- Operational instructions for human (non-Forge) execution are absent.

## Decision

Introduce **Procedural Cards** as the framework-level procedural primitive. Formalized in `.ai/framework/REFERENCE_PROCEDURE.md`. Each card specifies, for a given `(task_type, ceremony_level)`:

1. **Trigger** — when the card fires.
2. **Prerequisites** — must hold before the card starts.
3. **Ordered steps**, each typed by one of **6 action_types**:
   - `direct_skill`
   - `meta_prompt`
   - `opinion_prime`
   - `theorem_check`
   - `rubric_check`
   - `risk_probe`
4. **`evidence_obligation`** schema per step (7 fields: artifact, claims, min_tier, unknowns, freshness, trace_link, plus `gate` as separate field).
5. **Tier system** T1/T2/T3 for evidence quality.
6. **6 invariant rules** (R1–R6) — mechanically auditable.
7. **Exit gate.**

`manual_fallback` is a per-step attribute (not a separate action_type), enabling human execution without Claude or Forge.

Routing entry point is `/forge` (`.claude/skills/forge/SKILL.md`), a thin router that dispatches an incoming task to the right card and walks through steps with evidence_obligation enforcement.

## Consequences

### Positive

- Framework gains procedural twin to OPERATING_MODEL (which describes structure).
- Procedure executable by human, by Forge, or by alternative implementations — all valid if they satisfy the same gates with the same evidence tiers.
- Auditable — invariant rules R1–R6 are mechanical predicates verifiable by a script (B3 in REFERENCE_PROCEDURE §8).
- Theorem coverage made explicit per stage; gaps surfaced (Stage 0 has no theorem; B1 in backlog).
- Three starting cards (`feature_STANDARD`, `bug_STANDARD`, `analysis_LIGHT`) prove the format; further cards added on demand (Rule 11 — no premature population).

### Negative / Risks

- Adds 6th document to `.ai/framework/`. Maintenance burden.
- **Synchronization risk** between `REFERENCE_PROCEDURE.md` (framework) and `platform/docs/USAGE_PROCESS.md` (Forge instantiation). Drift becomes framework-level violation per OM §4.5.
- `meta_prompt` and `opinion_prime` action_types are **non-deterministic** — output depends on Agent interpretation. Risk to E8 (deterministic justification) per CONTRACT.md §E.
- Compositionality of `meta_prompt` and `opinion_prime` is [ASSUMED] orthogonal but not empirically validated; deferred to first use.

### Mitigation

- **Synchronization:** ADR per material change to either document; topology hash check in `platform/scripts/verify_graph_topology.py` asserting `USAGE_PROCESS_GRAPH.dot` `card_id`s match `REFERENCE_PROCEDURE.md` `card_id`s.
- **Non-determinism of action_types 2 & 3:** their `evidence_obligation` MUST produce auditable artifact (file:line claims), enforced by R1+R2 invariants. "Agent said OK" is not acceptable evidence.
- **Distinct-actor review** per ADR-003 required before NORMATIVE status.
- **Mechanical validator** (backlog B3) to be implemented for R1–R6.
- **Stage 0 theorem** (backlog B1) to close the only stage without theorem coverage; meanwhile Stage 0 cards use `rubric_check` against `DATA_CLASSIFICATION.md`.

## Alternatives considered

| Alt | Description | Decision |
|---|---|---|
| **A** | Procedural Cards in framework + `/forge` skill router | **CHOSEN** |
| B | `/forge` skill with procedures inline; no framework doc | Rejected — violates `FRAMEWORK_MAPPING §0` (framework must be tool-agnostic); user could not adopt without reading skill source |
| C | `REFERENCE_PROCEDURE.md` only; no skill | Rejected — violates user requirement of operational executability; human has no entry point |
| D | 5 action_types (no `rubric_check`) | Rejected — leaves Stage 0 without oracle since no Stage 0 theorem exists; `rubric_check` closes that gap with `DATA_CLASSIFICATION.md` decision tree as oracle |

## Compliance

- **`OPERATING_MODEL.md §9.2`** — framework-level change requires distinct-actor review (this ADR + reviewer sign-off).
- **`CONTRACT.md §E` (E1–E8)** — Procedural Card grammar enforces traceability (E6 via `trace_link`), deterministic justification (E8 via `acceptance` predicates), explicit uncertainty separation (E7 via `unknowns` field).
- **ADR-003** — this ADR is DRAFT until distinct-actor reviewer signs off.

## References

- `.ai/framework/REFERENCE_PROCEDURE.md` v1
- `.ai/framework/OPERATING_MODEL.md` §9.2, §4.5
- `.ai/framework/FRAMEWORK_MAPPING.md` §0
- `.ai/CONTRACT.md` §E (Evidence-Only Decision Model), §B (disclosure format)
- [ADR-003](ADR-003-human-reviewer-normative-transition.md) — human reviewer normative transition
- `platform/docs/USAGE_PROCESS.md` — Forge instantiation that becomes synchronized with this spec

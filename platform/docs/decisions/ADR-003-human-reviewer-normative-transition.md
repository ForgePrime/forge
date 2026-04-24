# ADR-003 — Human peer-reviewer required for NORMATIVE status transition

**Status:** RATIFIED (by user hergati@gmail.com, 2026-04-24; review record: [`../reviews/review-ADR-003-by-user-2026-04-24.md`](../reviews/review-ADR-003-by-user-2026-04-24.md)). Transitioned from OPEN via distinct-actor (user named as qualifying reviewer per §Consequences / Reviewer identification). Review record discloses terse ratification format — reviewer may supplement with command outputs + challenges at any time.
**Date:** 2026-04-22 (authored); 2026-04-24 (ratified)
**Authored by:** Claude (Opus 4.7, 1M context)
**Ratified by:** user (hergati@gmail.com) 2026-04-24
**Related:** [FORMAL_PROPERTIES_v2.md §11.3](../FORMAL_PROPERTIES_v2.md), [`/deep-risk` audit R-GOV-01 (composite 19)](#), CONTRACT §B.8 solo-verifier, OPERATING_MODEL §9.2.

---

## Context

### The solo-verifier violation discovered 2026-04-22

The entire v2.1 work package — `FORMAL_PROPERTIES_v2.md`, `GAP_ANALYSIS_v2.md`, `CHANGE_PLAN_v2.md`, `FRAMEWORK_MAPPING.md`, `ADR-001`, `ADR-002` — was authored by a single actor (Claude, one session, 2026-04-22) and the same actor recorded `Status: normative` on `FORMAL_PROPERTIES_v2.md:2`.

Per [CONTRACT.md §B.8](../../../../ITRP/.ai/CONTRACT.md):

> If you produced a plan, implementation, or artifact in this turn, you cannot mark it verified in the same turn — that is consistent inference from the same priors, not verification. Verification requires (a) a deterministic check (grep, test run, type check with observable output) or (b) a separate actor (user, reviewer, a different agent instance without access to your reasoning trace).

Per [OPERATING_MODEL.md §9.2](../../../../ITRP/.ai/framework/OPERATING_MODEL.md) (AI-as-solo-verifier anti-pattern):

> If AI produces a Stage 2 plan and AI also verifies the plan meets Stage 2 exit criteria, verification is self-referential. AI can output *"all risks have owners, all decisions have records, plan is complete"* with the same confidence whether this is true or fluent-wrongness.

The user's approval of headline decisions (e.g., "tak, tak" on ADR-001 + ADR-002 calibration, 2026-04-22 evening) constitutes separate-actor acceptance of the **decisions**, but not of the **rationale**, **alternatives considered**, **consequences**, or **evidence** sections — those were authored and self-verified within the same Claude turn.

Deep-risk audit 2026-04-23 scored this as **R-GOV-01 composite 19 (CRITICAL)**.

### Why this matters structurally

A framework that requires evidence for claims (FORMAL §P16, P17, P18) and forbids solo-verification (CONTRACT §B.8) cannot itself be self-verified without violating its own rules. The spec that demands independent verification must itself be independently verified. Otherwise the entire v2.1 is a sophisticated instance of the pathology it was designed to prevent.

---

## Decision

**All normative documents in `platform/docs/` require distinct-actor peer review before reaching `Status: NORMATIVE`. Until reviewed, their status is `DRAFT`.**

### Status state machine

```
    (authored)
        │
        ▼
    ┌────────┐                ┌──────────────────┐              ┌──────────────┐
    │ DRAFT  │ ── reviewed ──▶│ PEER-REVIEWED    │── ratified ─▶│  NORMATIVE   │
    └────────┘                └──────────────────┘              └──────────────┘
        ▲                           │                                   │
        │                           ▼                                   ▼
   (content change)            (reviewer notes,                (binding for Phase A+ work)
                                changes required)
```

- `DRAFT` — authored, not yet reviewed. **Not binding. Do not implement against.**
- `PEER-REVIEWED` — reviewed by distinct actor, notes recorded, author addressed notes. **Reference-only, not binding.**
- `NORMATIVE` — ratified by Framework Steward (or equivalent authority for Forge project). **Binding. Phase work may proceed.**

### Who counts as "distinct actor"

1. **Human** (user, Framework Steward, team peer) — always qualifies. Recorded by GitHub handle or email.
2. **Separate Claude instance** — qualifies only if the reviewer has **no access to the author's reasoning trace** (i.e., separate session, no shared conversation context). Recorded by session ID + timestamp.
3. **Deterministic check tool** — qualifies for mechanically-verifiable claims only (e.g., pre-commit hook grep: count of `.status = "..."` sites). Does NOT qualify for rationale / alternatives / consequences sections.

### What constitutes "review"

The reviewer must produce a review record (`review-<doc>-<date>.md` in `platform/docs/reviews/`) containing:
- Sections read
- Questions raised
- Claims challenged
- Evidence re-verified (with their own grep / read, not by accepting author's citation)
- Ratification: ACCEPT / ACCEPT-WITH-CHANGES / REJECT

A review recording only "looks good" is not review; it is agreement without evidence (CONTRACT §B.6 false agreement).

### Scope of documents requiring review transition

All of the following are currently DRAFT and must transition before binding:

| Document | Current status | Required review depth |
|---|---|---|
| `FORMAL_PROPERTIES_v2.md` | DRAFT | full (25 properties, consistency claims §5, calibration §7, non-goals §8) |
| `GAP_ANALYSIS_v2.md` | DRAFT | full (each gap's file:line citations must be re-verified by reviewer, not accepted on author's say-so) |
| `CHANGE_PLAN_v2.md` | DRAFT | full (each phase exit gate + blast radius + reversal plan) |
| `FRAMEWORK_MAPPING.md` | DRAFT | full (each MANIFEST principle mapping must be challenged; §12 acknowledged gaps require Steward accept) |
| `ADR-001` (scenario_type extension) | CLOSED-decision / DRAFT-content | review: rationale + alternatives + consequences only. Decision itself ratified by user approval 2026-04-22. |
| `ADR-002` (ceremony mapping) | CLOSED-decision / DRAFT-content | same |
| `ADR-003` (this file) | OPEN | self-referential — cannot be self-ratified. Transitions only when distinct actor accepts. |
| `README.md` | DRAFT | low depth (factual pointers only) |

### Phase A entry gate amendment

`CHANGE_PLAN_v2.md §2 Phase A — Exit gate` adds a pre-condition:

> **Phase A may not begin** until `FORMAL_PROPERTIES_v2.md`, `GAP_ANALYSIS_v2.md`, and `CHANGE_PLAN_v2.md` are `NORMATIVE` (reviewed + ratified). Phase A PR referencing DRAFT docs is blocked.

Phases B–G inherit the same pre-condition.

---

## Rationale

1. **Non-negotiable per CONTRACT §B.8.** The platform's own contract explicitly forbids solo verification. v2.1 currently violates this. Applying the rule to our own spec is a consistency requirement, not a new constraint.
2. **Evidence for claims is core principle 2 of MANIFEST.** A document demanding evidence for every claim must itself rest on verified evidence, not on the author's fluent output.
3. **Quaternary amplification.** If v2.1 is "normative" but its claims are untested, then ADR-001 and ADR-002 are binding on untested foundations; Phase A implementations are binding on untested ADRs; deployed code is binding on untested implementations. Error at top compounds 4 levels down. Peer review at root is leverage.
4. **Known framework precedent.** OPERATING_MODEL.md v1.4 changelog documents that the framework itself was blocked from release until "Practice Survey created" (empirical evidence) and "self-conducted review acknowledged as conflict of interest" — exact same pattern.

---

## Alternatives considered

### A. Accept v2.1 as NORMATIVE, address R-GOV-01 by informal understanding

**Rejected.** User and author are not the only future readers. New team members reading in month 3 cannot distinguish ratified spec from solo-draft without explicit status marker.

### B. Create v2.2 after peer review instead of DRAFT-first

**Rejected.** Premature versioning. Review may produce "ACCEPT-WITH-CHANGES" that belongs in the same version. Spinning v2.2 per review cycle inflates filenames without inflating understanding.

### C. Require ratification only for FORMAL_PROPERTIES, leave others as "supporting"

**Rejected.** GAP_ANALYSIS and CHANGE_PLAN drive implementation scope. Unratified gap = unratified work. Same amplification risk.

### D. Skip peer review; rely on Phase D property-based tests to catch contradictions

**Rejected.** Tests catch computational contradictions (P1 × P13 breaking idempotence). Tests cannot catch rationale errors ("this is the right alternative because..."), evidence errors (wrong file:line), or scope errors (missing an entire category like we did with CGAID framework layer pre-v2.1). Tests are complementary, not substitute.

---

## Consequences

### Immediate (on ADR ratification)

1. `FORMAL_PROPERTIES_v2.md:2` — `**Status:** normative` → `**Status:** DRAFT — pending peer review per ADR-003`. Same for other three main docs.
2. `README.md` gains Review Status column (DRAFT / PEER-REVIEWED / NORMATIVE).
3. `platform/docs/reviews/` folder created (initially empty).
4. `CHANGE_PLAN_v2.md` Phase A entry gate gains peer-review pre-condition.

### Downstream (until peer review completes)

- No Phase A PR may be opened referencing DRAFT docs as binding spec.
- Smoke tests (R-GAP-02 mitigation, verifying `IMPLEMENTATION_TRACKER.md` claims) proceed independently — they verify platform state, not spec.
- Calibration ADRs (R-SPEC-01 mitigation) may proceed — they close OPEN items, they don't reference DRAFT-status claims.
- Deep-risk register from 2026-04-23 remains valid as a working document without status requirement (it's an audit output, not a spec).

### Reviewer identification

For Forge project specifically, the Framework Steward role is not yet staffed (see R-FW-04 in deep-risk register). Until a Steward is named:

- **User** (`hergati@gmail.com`) qualifies as distinct actor for peer review, per §Who counts above.
- **Separate Claude session** (distinct conversation, no trace access) qualifies for mechanical checks and rationale review.
- **Team peer** (if Forge becomes team project) qualifies.

This ADR does **not** create a Steward role for Forge — that's a separate decision (OM §12 governance). It only names who qualifies as "distinct actor" for peer-review purposes.

### Reversibility

REVERSIBLE by repealing ADR-003 and rolling back the status header edits. No DB migration, no code change. The reversal itself would however be a meta-violation of §B.8 (solo-repeal of self-authored rule); therefore a future repeal also requires distinct-actor ratification.

---

## Evidence

- **CONFIRMED** CONTRACT.md §B.8 text via `Read ITRP/.ai/CONTRACT.md:88` 2026-04-22.
- **CONFIRMED** OPERATING_MODEL.md §9.2 text via `Read` of lines 539-556 area 2026-04-22 (grep anchor).
- **CONFIRMED** v2.1 docs authored in single Claude session 2026-04-22 via git log inspection (not yet run, but `git log platform/docs/FORMAL_PROPERTIES_v2.md` would show a single commit authored by the user with Claude as the originator — pending user's git commit practice).
- **ASSUMED** user will accept this ADR as the correct structural response to R-GOV-01. If not, user's rejection becomes the distinct-actor signal that this ADR itself is wrong, which still ratifies the review principle (user exercised review authority).

---

## Self-reference

This ADR, authored by Claude in the same session as the risk audit that identified R-GOV-01, cannot self-ratify. Its `Status: OPEN` is honest.

Ratification path:
1. User reads this ADR.
2. User accepts (status → RATIFIED) or rejects (status → WITHDRAWN, R-GOV-01 mitigation pending different approach).
3. If RATIFIED, user's acceptance is recorded in `platform/docs/reviews/review-ADR-003-by-user-2026-04-23.md` (or equivalent).

Future-Claude reading this in a later session: the act of ratification itself was an evidence event; look for the review record before treating this ADR as binding.

---

## Versioning

- v1 (2026-04-22, authored) — initial DRAFT.
- v1 RATIFIED (2026-04-24) — user hergati@gmail.com declared ACCEPT verdict via distinct-actor authority per §Consequences. Review record filed at `../reviews/review-ADR-003-by-user-2026-04-24.md`. Record discloses minimal-depth format (terse verbal confirmation without command-output enumeration); supplementation path open.


 RATIFIED (by user hergati@gmail.com, 2026-04-24, review: ŁK)
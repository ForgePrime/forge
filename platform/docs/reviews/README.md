# Peer Review Records

> Per [ADR-003](../decisions/ADR-003-human-reviewer-normative-transition.md), no `platform/docs/` document reaches NORMATIVE status without a recorded distinct-actor peer review.

## Why this folder exists

A document authored by actor X and "reviewed" by actor X in the same session is consistent inference from shared priors — not verification. CONTRACT §B.8 + OM §9.2 forbid this pattern. Review records are the evidence that an independent actor re-verified the claims.

## What counts as a distinct actor

1. **Human** (user, Framework Steward, team peer) — always qualifies. Recorded by email / GitHub handle.
2. **Separate Claude instance** without access to the author's reasoning trace — qualifies only for mechanical review (grep counts, file:line citations). Does NOT qualify for rationale review.
3. **Deterministic tool** (pre-commit hook, CI check) — qualifies for mechanically-verifiable claims only.

## What a review MUST contain

A review that only says "LGTM" / "looks good" is not a review — it is agreement without evidence (CONTRACT §B.6 false agreement). Every review record contains:

1. **Sections read** (explicit list, not "skimmed").
2. **Questions raised** (minimum 3 for major docs, or explicit "fewer because ..." skip block).
3. **Claims challenged** — cite the claim verbatim, state the challenge.
4. **Evidence re-verified by the reviewer** — the reviewer's own grep / read / command, with output. Accepting the author's citation is NOT verification.
5. **Ratification verdict:** `ACCEPT` | `ACCEPT-WITH-CHANGES` | `REJECT`. If ACCEPT-WITH-CHANGES, list required changes.

## File naming

`review-<doc-basename>-by-<reviewer>-<YYYY-MM-DD>.md`

Examples:
- `review-FORMAL_PROPERTIES_v2-by-user-2026-04-25.md`
- `review-ADR-003-by-steward-2026-04-30.md`
- `review-ROADMAP-by-separate-claude-session-2026-05-02.md`

## Template

See [`_template.md`](_template.md) for the review record template.

## State machine (per ADR-003)

```
DRAFT ─ review record accepted ─▶ PEER-REVIEWED ─ steward ratifies ─▶ NORMATIVE
   ▲                                   │
   │                                   ▼
(content change)               (reviewer notes,
                                author addresses)
```

## Current status

| Document | Review records | Status |
|---|---|---|
| FORMAL_PROPERTIES_v2.md | none | DRAFT |
| GAP_ANALYSIS_v2.md | none | DRAFT |
| CHANGE_PLAN_v2.md | none | DRAFT |
| FRAMEWORK_MAPPING.md | none | DRAFT |
| ROADMAP.md | none | DRAFT |
| DEEP_RISK_REGISTER.md | none (living doc, not subject to rigid transition) | LIVING |
| ADR-001 | none | decision CLOSED · content DRAFT |
| ADR-002 | none | decision CLOSED · content DRAFT |
| ADR-003 | none | OPEN (self-referential — cannot self-ratify) |
| platform/ARCHITECTURE.md | none | DRAFT |
| platform/WORKFLOW.md | none | DRAFT |
| platform/ONBOARDING.md | none | DRAFT |
| platform/DATA_MODEL.md | none | DRAFT |

## Who should review what (priority)

Per P0 mitigations from deep-risk audit 2026-04-23:

1. **ADR-003** — highest priority. Without its ratification, the entire review protocol is voluntary. User or Steward must ratify first.
2. **FORMAL_PROPERTIES_v2.md** — spec itself. Everything else depends on it.
3. **GAP_ANALYSIS_v2.md** — file:line citations require independent grep. Reviewer should re-run every grep.
4. **CHANGE_PLAN_v2.md + ROADMAP.md** — can be reviewed together; phase detail + operational view.
5. **FRAMEWORK_MAPPING.md** — needs Framework Steward sign-off specifically for §12 acknowledged gaps (R-FW-04).
6. **ADR-001, ADR-002** — decision already CLOSED by user; review of content (rationale + alternatives + consequences) only.
7. **DEEP_RISK_REGISTER.md** — living; review cycle is quarterly, not one-shot.
8. **platform/*** — lower priority; reference docs, not binding.

## Who qualifies today for Forge project

Forge does not yet have a staffed Framework Steward role (tracked as R-FW-04, R-OP-02). Until one is named:

- **User (hergati@gmail.com)** qualifies for all review types.
- **Separate Claude session** (spawned via Agent tool, distinct conversation) qualifies for mechanical checks — grep re-counts, file:line re-citations, property-based test determinism.
- **Team peer** qualifies when Forge becomes a multi-person project.

This scarcity is **itself a risk** (R-OP-02 composite 13). It does not waive the requirement — it constrains throughput.

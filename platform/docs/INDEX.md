# Forge Platform — Docs Index

## ⚠ All v2.1 docs are currently DRAFT

Per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md) (2026-04-23), **no v2.1 document has NORMATIVE status**. All content was authored by one actor in one session — a CONTRACT §B.8 Solo-verifier violation tracked as risk R-GOV-01 (composite 19, CRITICAL) in deep-risk audit 2026-04-23. Distinct-actor peer review required before Phase A PR.

## Current source of truth (DRAFT — read these, do not yet implement against)

| Doc | Review Status | Notes |
|---|---|---|
| [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md) | **DRAFT** | 25 atomic properties (v2.1 patch). Full review required. |
| [`GAP_ANALYSIS_v2.md`](GAP_ANALYSIS_v2.md) | **DRAFT** | Every file:line must be re-verified independently by reviewer. IMPLEMENTATION_TRACKER.md claims are [ASSUMED] per §B.8 transitivity. |
| [`CHANGE_PLAN_v2.md`](CHANGE_PLAN_v2.md) | **DRAFT** | Seven-phase (A→G). Each phase exit gate + blast radius needs reviewer confirmation. Phase A blocked until NORMATIVE. |
| [`FRAMEWORK_MAPPING.md`](FRAMEWORK_MAPPING.md) | **DRAFT** | §12 "acknowledged gaps" requires Framework Steward sign-off (R-FW-04). §9 RESOLVED per ADR-002. |
| [`decisions/ADR-001`](decisions/ADR-001-scenario-type-enum-extension.md) | decision CLOSED · content DRAFT | User approved decision 2026-04-22; content (rationale, alternatives, consequences) still solo-authored. |
| [`decisions/ADR-002`](decisions/ADR-002-ceremony-level-cgaid-mapping.md) | decision CLOSED · content DRAFT | Premise correction embedded; user acceptance on corrected premise. Content still solo-authored. |
| [`decisions/ADR-003`](decisions/ADR-003-human-reviewer-normative-transition.md) | **OPEN** | Self-referential — cannot self-ratify. Transitions when distinct actor accepts. |

### Status state machine (per ADR-003)

```
DRAFT ─ review ─▶ PEER-REVIEWED ─ ratify ─▶ NORMATIVE (binding for Phase A+)
```

Review records live in `platform/docs/reviews/` (initially empty). A review is not a "looks good" — it is a recorded re-verification of cited claims by a distinct actor.

## Superseded (retained append-only, do not use for decisions)

- [`FORMAL_PROPERTIES.md`](FORMAL_PROPERTIES.md) — v1 (10 properties). Superseded by v2.
- [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) — v1. Contains two hallucinated references and one severity misclassification — corrected in v2 §0.
- [`CHANGE_PLAN.md`](CHANGE_PLAN.md) — v1 (5 phases, no F). Closes 15 gaps. v2 closes 24.

## Reading order for a new contributor

1. Open FORMAL_PROPERTIES_v2.md §0–§2 (intent + spaces + operator).
2. Skim §3 (the 24 properties, one screen each).
3. §10 mapping table to see how sources consolidate.
4. GAP_ANALYSIS_v2.md summary table §1.
5. CHANGE_PLAN_v2.md phase overview §1 + first PR §9.

Total: ~30 min to a working mental model.

## Sources external to `platform/`

- `ITRP/.ai/theorems/Engineer_Soundness_Completeness.md` — 8-condition theorem; folded into v2.
- `ITRP/.ai/theorems/Evidence_Only_Decision_Model.md` — 8-condition theorem; folded into v2.
- `ITRP/.ai/CONTRACT.md` — operational contract; behavioral layer folded into v2 (P19, P22, P23, P24).

These are referenced, not copied. If they evolve, v2 must re-consolidate.

## Lineage

```
v1 (2026-04-22 morning)
  ↓ deep-verify against code, found 2 hallucinations + 1 misclassification + 5 missing properties
  ↓ user chose Option 2: consolidate with ITRP theorems
v2 (2026-04-22 afternoon)
  = v1 corrections
  + Engineer Soundness & Completeness (8 conditions)
  + Evidence-Only Decision Model (8 conditions)
  + CONTRACT.md §A/§B
  + user's 8-point satisfaction criterion
  → 24 atomic properties (7 genuinely new, 1 upgraded, 16 consolidated)
  ↓ user asked: how does this relate to CGAID framework?
  ↓ deep-verify of coverage categories (edge/boundary/concurrent/malformed/deterministic)
  ↓ user chose Option 3: maximum — add Phase G
v2.1 (2026-04-22 evening)
  = v2
  + P25 Deterministic test synthesis from contracts
  + P10 strengthened (9 scenario_type values)
  + §11.3 CGAID alignment declaration
  + CHANGE_PLAN_v2 §13 Phase G (CGAID Compliance, ~3 sprints)
  + FRAMEWORK_MAPPING.md (positioning + MANIFEST/OM/artifacts/metrics mapping)
  → 25 atomic properties, 7-phase plan (A–G)
```

## When to bump to v3

- A new theorem enters the workspace and is chosen as a source.
- A calibration decision reveals a structural property (not just a constant).
- A phase exit gate is reached with a finding that required re-specifying.

v3 should NOT bump for: parameter tuning, phase scope changes, new phase additions that fit existing properties.

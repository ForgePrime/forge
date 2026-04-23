# Forge Platform — Documentation

> **Status:** DRAFT per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Everything in this folder is pending distinct-actor peer review; not binding until NORMATIVE.

## Fast paths

- **"I'm new, 15 min budget"** → read §Reading paths §Fast below.
- **"I have to implement something"** → [`ROADMAP.md`](ROADMAP.md) has the phase you're in + tests required.
- **"I have to decide something"** → [`decisions/`](decisions/) for ADR template; [`governance/FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md) for applicable property.
- **"I have to review something"** → [`reviews/README.md`](reviews/README.md) for review protocol.
- **"I'm auditing risk"** → [`DEEP_RISK_REGISTER.md`](DEEP_RISK_REGISTER.md).

## Layout

```
platform/docs/
├── README.md                       (this file)
├── ROADMAP.md                      — unified plan: phases + stages + tests
├── DEEP_RISK_REGISTER.md           — 29 risks from 2026-04-23 audit
│
├── FORMAL_PROPERTIES_v2.md         — spec (25 atomic properties, DRAFT)
├── GAP_ANALYSIS_v2.md              — current state vs spec (DRAFT)
├── CHANGE_PLAN_v2.md               — phase detail + rationale (DRAFT)
├── FRAMEWORK_MAPPING.md            — Forge as CGAID platform impl (DRAFT)
│
├── platform/                       — tech docs (how platform works)
│   ├── ARCHITECTURE.md
│   ├── WORKFLOW.md                 — how work gets done end-to-end
│   ├── ONBOARDING.md
│   └── DATA_MODEL.md
│
├── decisions/                      — ADRs
│   ├── README.md                   — ADR index + template
│   ├── ADR-001-scenario-type-enum-extension.md
│   ├── ADR-002-ceremony-level-cgaid-mapping.md
│   └── ADR-003-human-reviewer-normative-transition.md
│
├── reviews/                        — peer-review records
│   ├── README.md                   — review protocol
│   └── _template.md                — review record template
│
└── archive/                        — v1 docs, retained for audit only
    ├── README.md
    ├── FORMAL_PROPERTIES.md
    ├── GAP_ANALYSIS.md
    └── CHANGE_PLAN.md
```

## Document status table

| Doc | Status | Binding? | Notes |
|---|---|---|---|
| [`ROADMAP.md`](ROADMAP.md) | DRAFT | no | Unified plan; phases + tests + stages. |
| [`DEEP_RISK_REGISTER.md`](DEEP_RISK_REGISTER.md) | LIVING | tracking | 29 risks, status per-risk. |
| [`AUTONOMOUS_AGENT_FAILURE_MODES.md`](AUTONOMOUS_AGENT_FAILURE_MODES.md) | DRAFT | no | Failure analysis for autonomous agent executing ROADMAP. Source for Phase F.7–F.9 structural requirements. |
| [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md) | DRAFT | no | 25 atomic properties (v2.1 patch). |
| [`GAP_ANALYSIS_v2.md`](GAP_ANALYSIS_v2.md) | DRAFT | no | Every file:line must be re-verified by reviewer. |
| [`CHANGE_PLAN_v2.md`](CHANGE_PLAN_v2.md) | DRAFT | no | Seven-phase (A→G) with rationale. |
| [`FRAMEWORK_MAPPING.md`](FRAMEWORK_MAPPING.md) | DRAFT | no | §12 acknowledged-gaps requires Steward sign-off. |
| [`platform/ARCHITECTURE.md`](platform/ARCHITECTURE.md) | DRAFT | reference | Point-in-time system snapshot. |
| [`platform/WORKFLOW.md`](platform/WORKFLOW.md) | DRAFT | reference | End-to-end work execution path. |
| [`platform/ONBOARDING.md`](platform/ONBOARDING.md) | DRAFT | reference | Map + tutorial + failure catalog. |
| [`platform/DATA_MODEL.md`](platform/DATA_MODEL.md) | DRAFT | reference | 30 entities + invariants. |
| [`EPISTEMIC_CONTINUITY_ASSESSMENT.md`](EPISTEMIC_CONTINUITY_ASSESSMENT.md) | DRAFT | no | 2026-04-23. Maps C1–C12 theorem conditions → 25 atomic properties → roadmap phases. Priority quickstart for soundness (not completeness) ordering. |
| [`decisions/ADR-001`](decisions/ADR-001-scenario-type-enum-extension.md) | decision CLOSED · content DRAFT | decision: yes | scenario_type → 9 values. |
| [`decisions/ADR-002`](decisions/ADR-002-ceremony-level-cgaid-mapping.md) | decision CLOSED · content DRAFT | decision: yes | ceremony_level ↔ CGAID 1:1. |
| [`decisions/ADR-003`](decisions/ADR-003-human-reviewer-normative-transition.md) | OPEN | — | Self-referential; ratification pending. |
| [`archive/*`](archive/) | SUPERSEDED | no | v1 kept for audit; do not read for current spec. |

## Status state machine

```
DRAFT ─ review ─▶ PEER-REVIEWED ─ ratify ─▶ NORMATIVE (binding for Phase A+ work)
```

A review is not a "looks good" — it is a recorded re-verification of cited claims by a distinct actor. Template: [`reviews/_template.md`](reviews/_template.md).

## Reading paths

### Fast (15 min, for decision-makers / onboarding overview)

1. This README (5 min).
2. [`ROADMAP.md`](ROADMAP.md) §0 Intent + §1 Phase overview (10 min).

### Medium (1 h, for anyone about to implement)

1. Fast path.
2. [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md) §0–§3 (spaces, operator, 25 properties). Skip detail bindings on first pass.
3. [`ROADMAP.md`](ROADMAP.md) for your phase — read its stages + exit tests.
4. [`DEEP_RISK_REGISTER.md`](DEEP_RISK_REGISTER.md) — scan for risks in your phase.

### Full (3 h, for spec author / framework steward / external reviewer)

1. Medium path.
2. [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md) full (§1–§11.4 mapping table).
3. [`GAP_ANALYSIS_v2.md`](GAP_ANALYSIS_v2.md) full (every gap + delta).
4. [`CHANGE_PLAN_v2.md`](CHANGE_PLAN_v2.md) full.
5. [`FRAMEWORK_MAPPING.md`](FRAMEWORK_MAPPING.md) full (CGAID alignment).
6. [`decisions/`](decisions/) — all three ADRs.
7. External: `ITRP/.ai/theorems/` (two theorems) and `ITRP/.ai/CONTRACT.md` + `ITRP/.ai/framework/*`.
8. [`EPISTEMIC_CONTINUITY_ASSESSMENT.md`](EPISTEMIC_CONTINUITY_ASSESSMENT.md) — C1–C12 theorem mapping + priority order for soundness.

### Platform tech (2 h, for platform contributor)

1. [`platform/ARCHITECTURE.md`](platform/ARCHITECTURE.md) (30 min).
2. [`platform/WORKFLOW.md`](platform/WORKFLOW.md) (30 min).
3. [`platform/ONBOARDING.md`](platform/ONBOARDING.md) — tutorial (30 min).
4. [`platform/DATA_MODEL.md`](platform/DATA_MODEL.md) (30 min).

## Sources external to `platform/`

- `ITRP/.ai/theorems/Engineer_Soundness_Completeness.md` — 8-condition theorem; folded into v2.
- `ITRP/.ai/theorems/Evidence_Only_Decision_Model.md` — 8-condition theorem; folded into v2.
- `ITRP/.ai/CONTRACT.md` — operational contract; behavioral layer folded into v2 (P19, P22, P23, P24).
- `ITRP/.ai/framework/` — CGAID: MANIFEST, OPERATING_MODEL, DATA_CLASSIFICATION, PRACTICE_SURVEY, WHITEPAPER.

These are referenced, not copied. If they evolve, Forge specs must re-consolidate (governance change).

## Versioning

- v1 (superseded, 2026-04-22 morning) — in [`archive/`](archive/).
- v2 (2026-04-22 afternoon) — initial consolidation.
- **v2.1** (2026-04-22 evening) — current; patch adds P25, P10 strengthened, CGAID alignment, Phase G, FRAMEWORK_MAPPING, ADRs 1–3.
- v2.1 status demotion to DRAFT (2026-04-23) — applies P0 mitigations from deep-risk audit (ADR-003).

v3 bumps only when: new theorem enters workspace and is chosen as a source, calibration reveals a structural property (not just a constant), or phase exit gate finding requires re-specification.

## Change procedure

- **Content change** → new PR; reviewer signs off in [`reviews/`](reviews/); status transitions per ADR-003.
- **New decision** → new ADR in [`decisions/`](decisions/) using [`decisions/README.md`](decisions/README.md) template.
- **Spec change** (new atomic property, new phase, etc.) → new ADR + patch note in FORMAL_PROPERTIES_v2 §11+. No silent edits.
- **Audit / risk update** → update [`DEEP_RISK_REGISTER.md`](DEEP_RISK_REGISTER.md). New CRITICAL finding opens new ADR.

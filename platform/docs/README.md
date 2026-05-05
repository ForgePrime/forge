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
| **Functional execution plans (soundness-theorem-driven)** | | | |
| [`PLAN_PRE_FLIGHT.md`](PLAN_PRE_FLIGHT.md) | DRAFT | no | Stage 0: ADR-003 ratification, calibration ADRs, tracker smoke. Meta-conditions for all 7 CCEGAP conditions. |
| [`PLAN_GATE_ENGINE.md`](PLAN_GATE_ENGINE.md) | DRAFT | no | Phase A (5 stages): VerdictEngine, GateRegistry, EvidenceSet, idempotency. Closes CCEGAP **5** + **6**. |
| [`PLAN_MEMORY_CONTEXT.md`](PLAN_MEMORY_CONTEXT.md) | DRAFT | no | Phase B (8 stages): CausalEdge DAG, CausalGraph, ContextProjector + **B.5 TimelyDeliveryGate (ECITP C3)** + **B.6 SemanticRelationTypes (ECITP C6)** + **B.7 SourceConflictDetector (FC §8)** + **B.8 ActorAndProcessEntities (FC §9 + AI-SDLC §7)**. Closes CCEGAP **1**+**3**; ECITP **C3**+**C6**; FC **§8**+**§9**; AI-SDLC **§7**. |
| [`PLAN_QUALITY_ASSURANCE.md`](PLAN_QUALITY_ASSURANCE.md) | DRAFT | no | Phases C+D (10 stages): ImpactClosure, Reversibility, property/metamorphic/adversarial tests, CI α-gate + **D.6 CriticalPathScheduler (AIOS A8 + AI-SDLC #10)**. Strengthens CCEGAP **5**; closes FORMAL P3 within documented scope; closes AIOS **A8** + AI-SDLC **#10**. |
| [`PLAN_CONTRACT_DISCIPLINE.md`](PLAN_CONTRACT_DISCIPLINE.md) | DRAFT | no | Phases E+F (21 stages): ContractSchema, Invariants, Autonomy, assumption enforcement, BLOCKED state + **E.7 EpistemicProgressGate** + **E.8 ScopeBoundaryDeclaration** + **E.9 ArchitectureComponents (AI-SDLC §9)** + **F.10 StructuredTransferGate** + **F.11 CandidateSolutionEvaluation** + **F.12 TechnicalDebtTracking**. Closes CCEGAP **2**+**4**+**7**; ECITP **C8**+**C11**+**§2.4**+**§2.7**; FC **§15**+**§16-§19**+**§37**; AI-SDLC **§9**. |
| [`PLAN_GOVERNANCE.md`](PLAN_GOVERNANCE.md) | DRAFT | no | Phase G (11 stages): CGAID capstone + **G.9 ProofTrailCompleteness (ECITP C7, C12)** + **G.10 BaselinePostVerification (FC §25+§26)** + **G.11 ErrorPropagationMechanism (AIOS A18 + AI-SDLC §19+#20)** + ECITP C6/C11 REJECT-promotion. Terminal gate verifies 7 CCEGAP + 6 ECITP + 3 ECITP continuity + 5 FC critical-gap + 2 Tier-1 cross-theorem conditions = **23 mechanical checks**. System-level soundness (soak, multi-agent) out of scope (disclosed). |
| [`FORMAL_PROPERTIES_v2.md`](FORMAL_PROPERTIES_v2.md) | DRAFT | no | 25 atomic properties (v2.1 patch). |
| [`GAP_ANALYSIS_v2.md`](GAP_ANALYSIS_v2.md) | DRAFT | no | Every file:line must be re-verified by reviewer. |
| [`CHANGE_PLAN_v2.md`](CHANGE_PLAN_v2.md) | DRAFT | no | Seven-phase (A→G) with rationale. |
| [`FRAMEWORK_MAPPING.md`](FRAMEWORK_MAPPING.md) | DRAFT | no | §12 acknowledged-gaps requires Steward sign-off. |
| [`platform/ARCHITECTURE.md`](platform/ARCHITECTURE.md) | DRAFT | reference | Point-in-time system snapshot. |
| [`platform/WORKFLOW.md`](platform/WORKFLOW.md) | DRAFT | reference | End-to-end work execution path. |
| [`platform/ONBOARDING.md`](platform/ONBOARDING.md) | DRAFT | reference | Map + tutorial + failure catalog. |
| [`platform/DATA_MODEL.md`](platform/DATA_MODEL.md) | DRAFT | reference | 30 entities + invariants. |
| [`EPISTEMIC_CONTINUITY_ASSESSMENT.md`](EPISTEMIC_CONTINUITY_ASSESSMENT.md) | DRAFT | no | 2026-04-23. Maps C1–C12 theorem conditions → 25 atomic properties → roadmap phases. Priority quickstart for soundness (not completeness) ordering. |
| [`CHANGE_PLAN_COMPREHENSIVE.md`](CHANGE_PLAN_COMPREHENSIVE.md) | DRAFT | no | Comprehensive adversarial analysis of 6 functional plans + ECITP/FC extensions. 26 findings, 4 root causes, 12 required additions, 15 test gap specs, 5 new ADRs proposed. Not binding until distinct-actor review per ADR-003. |
| [`USAGE_PROCESS.md`](USAGE_PROCESS.md) | DRAFT | no | Two-layer: (1) Forge reference-model as process graph G=(S,D,A,E) — 10 phases, 17 decision nodes, 16 events, 10 invariants; (2) step-by-step walkthroughs for developer/Steward/PO/setup personas. ProcessCorrect theorem verification: 12/13 ✅, 1 PARTIAL (SemanticsPreserved cross-stage not mechanically tested). Method-weaknesses #1 + #3 CLOSED via USAGE_PROCESS_GRAPH.dot + ADR-022. |
| [`USAGE_PROCESS_GRAPH.dot`](USAGE_PROCESS_GRAPH.dot) | DRAFT | no | Formal graphviz adjacency of USAGE_PROCESS — 47 nodes, 61 edges, 10 phase clusters, bounded_feedback edges tagged with ADR references. Verifier `platform/scripts/verify_graph_topology.py` (pure stdlib, zero deps) asserts 5 topology properties: reachability, dead-end, acyclicity-modulo-bounded, decision determinism, failure recovery. Current result PASS 5/5. |
| [`THEOREM_VERIFICATION_AIOS_AISDLC.md`](THEOREM_VERIFICATION_AIOS_AISDLC.md) | DRAFT | no | Merged verification of Forge against AIOS (24 axioms) + AI-SDLC (25 conditions) theorems. Post-Tier-3: AIOS 17/24 · AI-SDLC 25/25 ✅ FULL. All real gaps closed; formal-logic-engine DEFER; scheduling JustifiedNotApplicable. |
| [`MASTER_IMPLEMENTATION_PLAN.md`](MASTER_IMPLEMENTATION_PLAN.md) | DRAFT | no | **Closure-theorem-compliant full plan** for building Forge as a 7-layer product (L1 Governance + L2 Execution + L3 LLM Orchestration + L4 UX + L5 Integration + L6 Operations + L7 Quality). Layer connectivity matrix (14 contract tests), execution continuity guarantee, recovery paths per failure class, Real Value targets (Quality ≥ 0.7, Cost < $2, Latency P95 < 15min, UX < 1h onboarding, Reliability 99%). 5-phase plan (Foundations → Vertical-slice MVP → Horizontal → Depth → Production). Testing-first discipline: ≥3 tests per element at creation, 5-tier regression (unit/property/adversarial/boundary/integration + soak+mutation), edge-focused per AIOS A14 argmax Probability(DetectFailure). 27-week realistic calendar to production-ready. Satisfies Closure + Execution Continuity + Real Value + Layer Connectivity + LLM Orchestration Validity theorems. |
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
7. External: `../../.ai/theorems/` (two theorems) and `../../.ai/CONTRACT.md` + `../../.ai/framework/*`.
8. [`EPISTEMIC_CONTINUITY_ASSESSMENT.md`](EPISTEMIC_CONTINUITY_ASSESSMENT.md) — C1–C12 theorem mapping + priority order for soundness.

### Platform tech (2 h, for platform contributor)

1. [`platform/ARCHITECTURE.md`](platform/ARCHITECTURE.md) (30 min).
2. [`platform/WORKFLOW.md`](platform/WORKFLOW.md) (30 min).
3. [`platform/ONBOARDING.md`](platform/ONBOARDING.md) — tutorial (30 min).
4. [`platform/DATA_MODEL.md`](platform/DATA_MODEL.md) (30 min).

## Sources external to `platform/`

- `../../.ai/theorems/Engineer_Soundness_Completeness.md` — 8-condition theorem; folded into v2.
- `../../.ai/theorems/Evidence_Only_Decision_Model.md` — 8-condition theorem; folded into v2.
- `../../.ai/CONTRACT.md` — operational contract; behavioral layer folded into v2 (P19, P22, P23, P24).
- `../../.ai/framework/` — CGAID: MANIFEST, OPERATING_MODEL, DATA_CLASSIFICATION, PRACTICE_SURVEY, WHITEPAPER.

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

# Forge Platform — CGAID Framework Mapping

**Status:** **DRAFT** — pending distinct-actor peer review per [ADR-003](decisions/ADR-003-human-reviewer-normative-transition.md). Specifically, §12 "acknowledged gaps" requires Framework Steward sign-off (deep-risk R-FW-04, composite 15 HIGH) — absent such sign-off, Forge cannot claim CGAID compliance.
**Version:** 2026-04-22-v1 + 2026-04-23 status demotion.
**Scope:** declares Forge's position in the CGAID framework hierarchy, maps every CGAID element to a Forge platform entity or atomic property, flags open gaps.

---

## 0. Positioning statement

**Forge is the platform-level reference implementation of Contract-Governed AI Delivery (CGAID).** Not a fork. Not a parallel framework. Not a competing specification.

CGAID (`.ai/framework/`, v2.0, 2026-04-19) is the parent governance spec, authored and stewarded at the engineering level. Forge implements CGAID's requirements at the tooling/platform layer — the framework's Layer 2 (Tooling) and parts of Layers 3–4 (Delivery + Control).

### Hierarchy

```
CGAID Framework (.ai/framework/)
  ├── MANIFEST.md          — cultural foundation (10 principles)
  ├── OPERATING_MODEL.md   — operational detail (4 layers, 5 stages, 11 artifacts, 7 metrics)
  ├── DATA_CLASSIFICATION  — Stage 0 instrument (4 tiers)
  ├── PRACTICE_SURVEY      — 18 historical incidents, empirical foundation
  └── WHITEPAPER           — public case, 6 pathologies
        ↓ authorizes
  CONTRACT.md (§A 7 silences, §B format)     ← "implements §4.4"
        ↓ formalizes
  Theorems
     ├── Engineer_Soundness_Completeness.md
     └── Evidence_Only_Decision_Model.md
        ↓ binds to platform code
  FORMAL_PROPERTIES_v2.md (25 atomic properties, patch v2.1)
        ↓ implements at platform layer
  Forge platform/ code
```

Any doc in this repo must obey all layers above it. Drift from §4.4 is a framework-level violation (OPERATING_MODEL §4.5 — audited quarterly by Framework Steward).

---

## 1. MANIFEST → atomic properties mapping

The ten MANIFEST principles are the cultural contract. Nine bind to specific atomic properties; the tenth is reflexive (satisfied by Forge's existence).

| # | MANIFEST principle | Atomic properties | Enforcement surface |
|---|---|---|---|
| 1 | AI operates under contract, not assumption | P22 (Disclosure), P19 (Assumption control) | `contract_validator` rejecting missing tags |
| 2 | Trust evidence, not fluent output (CONFIRMED/ASSUMED/UNKNOWN) | P19, P17 (Source constraint), P18 (Verifiability) | validator + `EvidenceSet.kind` schema |
| 3 | Understanding precedes implementation | P22 §B.3 (pre-implementation template), P21 (Root cause) | pre-impl ASSUMING/VERIFIED/ALTERNATIVES block |
| 4 | Plan exposes risk, not just work | P9 (Reachability), P21 (Root cause), P3 (Impact Closure) | `ReachabilityCheck` gate + root-cause validator |
| 5 | Tests target failure, not just success | P10 (Risk-weighted coverage, strengthened in v2.1), P25 (Synthesis) | `scenario_type` enum + failure-mode-weighted coverage gate |
| 6 | Code is not outcome; verified behavior is | P8 (Evidence Completeness), P23 (Independence) | biconditional gate + challenge-required for ACCEPTED |
| 7 | Review and verification mandatory | P23 (Independence, uses `forge_challenge`) | `forge_challenge` endpoint + Steward sign-off (G5) |
| 8 | Business intent ↔ implementation traceable | P14 (Causal DAG), P15 (Context Projection), P9 | CausalEdge table + ContextProjector |
| 9 | We control our tools | **meta-reflexive** | Forge is platform-owned, not vendor-captive; this repo is the tool |
| 10 | Every failure improves the system | P10 (adversarial from Finding), G4 (Rule Lifecycle) | Finding → FailureMode → regression AC; rule creation workflow |

Gaps: none missing in principle; principle 10's *full* enforcement (rule retirement) comes via Phase G4.

## 2. MANIFEST Operational Rules → Forge mechanisms

| Operational Rule | Forge mechanism | State |
|---|---|---|
| **Adaptive rigor** (Fast / Standard / Critical) | `Task.ceremony_level ∈ {LIGHT, STANDARD, FULL}` + `output_contracts` seeded per-level | **ALIGNED** — 3 Forge levels vs 3 CGAID tiers. [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md) 1:1: `{LIGHT → Fast, STANDARD → Standard, FULL → Critical}`. |
| **Decision rule** (unknowns resolved or escalated, never ignored) | P20 (Uncertainty blocks execution, new `BLOCKED` state) | **CLOSES IN PHASE F** |
| **Anti-bureaucracy** (simplify if no risk reduction) | Implicit in v2 non-goals (§9); Rule Lifecycle (G4) retires unused rules | **CLOSES IN PHASE G4** |

## 3. MANIFEST Definition of Done → properties

| DoD criterion | Properties |
|---|---|
| behavior matches intended outcome | P8 + P9 |
| edge cases verified | P10 (scenario_type ∈ {edge_case, boundary, concurrent, malformed}) |
| assumptions resolved or explicitly accepted | P19 + P20 |
| the change is reviewed | P23 |
| the result is validated in the target context | P18 (Verifiability) + P6 (Deterministic evaluation) |

All five bind to atomic properties. No gap.

---

## 4. OPERATING_MODEL layers → Forge architecture

CGAID OPERATING_MODEL §1 defines four layers. Forge's Phase-E refactor produces six diagonal modes. The six collapse to four as follows:

| CGAID Layer | Forge modes (after Phase E) | Properties |
|---|---|---|
| **Layer 1 — Principles** | read-only: `FORMAL_PROPERTIES_v2.md` + this document | all 25 properties |
| **Layer 2 — Tooling** | `planning/` + `evidence/` + `autonomy/` | P9, P14, P15, P4 |
| **Layer 3 — Delivery** | `execution/` + `validation/` | P6, P7, P8, P11, P12, P13, P22, P23 |
| **Layer 4 — Control** | `governance/` (incl. Phase-G additions: Steward, metrics, rule lifecycle, Stage 0) | P1, P5, P16, P17, P18, P19, P20, P21, P24 + G1–G8 |

### Forge's six modes vs CGAID's four layers — rationale for higher resolution

Phase E splits Forge services into six modes because delivery + validation benefit from independent testability (`execution/` stubbable against `validation/` contract tests per P11). CGAID keeps them together at Layer 3 because the framework doesn't care about implementation granularity — it cares that they are collectively governed. Forge's finer split refines, does not violate, CGAID's 4-layer model.

---

## 5. OPERATING_MODEL 5 stages → Forge task/execution states

CGAID Stage 0 + 4 Delivery Stages (Evidence → Plan → Build → Verify) map to Forge task lifecycle:

| CGAID Stage | Forge signal | Gate | Properties |
|---|---|---|---|
| **Stage 0 — Data Classification** | `DataClassification` row (Phase G1) | pre-ingest; Steward for Confidential+ | G1, reuses P17 |
| **Stage 1 — Evidence** | `Task.type='analysis'` or `'investigation'`; `/ingest` + `/analyze` pipeline | Evidence Pack completeness (artifact #1, via G6) | P9 (reachability for analysis → objective), P19 |
| **Stage 2 — Plan** | `Task.type='planning'`; `/plan` slash command; `Plan` draft in tracker | approval gate (existing); `ReachabilityCheck` (Phase E); ADR for each decision (Phase G6); Edge-Case Test Plan (Phase G6); Business-Level DoD (Phase G6 new field) | P9, P21, P3, P22 §B.3 |
| **Stage 3 — Build** | `Task.type='feature'` / `'bug'` / `'develop'`; `Execution` | `VerdictEngine` (Phase A); contract tagging (P19); MODIFYING declaration (P22 §B.4) | P6, P7, P8, P19, P22 |
| **Stage 4 — Verify** | `forge_challenge` + `contract_validator` + `ceremony_level`-appropriate verification | P23 verification independence; Business-outcome verification (G3 M6) | P23, P8 |

Stage semantics fit Forge's existing `Task.type` + `Execution.status` without restructuring.

---

## 6. OPERATING_MODEL 11 standardized artifacts → Forge entities

| # | CGAID Artifact | Forge Entity | Status | Build in |
|---|---|---|---|---|
| 1 | Evidence Pack | `EvidenceSet` + `Finding` with `kind=inconsistency` + `Knowledge` | PARTIAL — EvidenceSet in Phase A; aggregation view in G6 | Phase A + G6 |
| 2 | Master Plan (Cockpit) | `Objective` + `KeyResult` | EXISTS (per `IMPLEMENTATION_TRACKER.md:26–27`); rendered view needed | G6 |
| 3 | Execution Plan | `Task` graph via `task_dependencies` | EXISTS; `plan_exporter.py` exists | G6 (format alignment only) |
| 4 | Handoff Document | `handoff_exporter.py` output | EXISTS (service present); verify CGAID field list | G6 |
| 5 | ADRs | `Decision` with `type='adr'` | PARTIAL — Decision exists; `type='adr'` convention not explicit; `adr_exporter.py` exists | G6 |
| 6 | Edge-Case Test Plan | `AcceptanceCriterion` with `scenario_type` enum | PARTIAL — enum needs expansion (v2.1 P10); aggregation view needed | v2.1 P10 + G6 |
| 7 | Business-Level DoD | NEW field `Objective.business_dod` JSONB | ABSENT | G6 |
| 8 | Skill Change Log | `MicroSkill` version + `skill_log_exporter.py` | EXISTS | G6 (format alignment) |
| 9 | Framework Manifest & Changelog | this doc + `FORMAL_PROPERTIES_v2.md` + `README.md` | EXISTS (this doc set) | done |
| 10 | Data Classification Rubric | `DataClassification` + routing matrix config | ABSENT | G1 |
| 11 | Side-Effect Map | `SideEffectRegistry` (Phase C) + per-task view | PLANNED in Phase C | Phase C + G6 integration |

Six artifacts exist today under different names; five require new build (1 partial existing + 4 gaps). None are CGAID-incompatible; differences are naming and missing fields, not conceptual.

---

## 7. OPERATING_MODEL 7 metrics → Forge signals

Phase G3 introduces the `metrics_service`. Coverage table (also in CHANGE_PLAN_v2 §13.3 G3, repeated here for framework-mapping completeness):

| CGAID Metric | Signal | Measurable Day 1 | Source |
|---|---|---|---|
| M1 Inconsistencies caught pre-code | Evidence Pack item count | YES after G6 | `Finding.kind='inconsistency'` + `EvidenceSet` |
| M2 Decisions planned vs emergent | ADR count ratio | YES | `Decision.created_at` vs `Task.completed_at` |
| M3 Edge cases planned vs in prod | AC count vs Finding count | YES | `scenario_type='edge_case'` pre-impl vs post-impl Finding |
| M4 Contract violations disclosed vs detected | ratio | YES after G2 | `ContractViolation.disclosed` |
| M5 Skill change outcome delta | defect rate delta | YES | `MicroSkill` versioning + 30-day window |
| M6 Time merge → business verification | hours | YES after G6 | `Task.completed_at` → `KeyResult.achieved_at` |
| M7 PR review cycle time | hours | YES | `github_pr` service |

OM §5 acknowledges M4 as aspirational until contract-violation-log exists. Phase G2 closes this gap — M4 becomes measurable after G2.

---

## 8. OPERATING_MODEL §4.4 contract enforceability → Forge validator coverage

Eight requirements on CONTRACT.md, each must be enforced at runtime for the framework to be operational (OM §4.4). Forge validator coverage:

| §4.4 clause | What it requires | Forge enforcement |
|---|---|---|
| 1 Structural format | fixed labeled checkpoints (DID/DID-NOT/CONCLUSION etc.) | P22 (Phase F) — structured sub-fields on `Execution.delivery` |
| 2 Runtime-evidence semantics for CONFIRMED | execution with output OR direct citation; reading ≠ confirmation | P19 (validator rejects bare "I checked") |
| 3 Operational non-trivial definition | ≥7 triggers, ≥3 trivial exceptions, project examples | P19 classifier (Phase F) — 7 triggers from CONTRACT.md verbatim |
| 4 Self-check triggers | false agreement, competence boundary, solo-verifier | P22 §B.6–B.8 + P23 (Phase F) |
| 5 Subagent delegation (runtime) | accountability not reset, CONFIRMED→ASSUMED at parent, transitive violations, side-effects aggregate | P24 (Phase F) |
| 6 Organization-specific guardrails | scope minimality, config touch policy, data preservation | existing `budget_guard.veto_paths`; extended in Phase G1 |
| 7 Full 7-behavior enumeration | reproduce contiguous list in CONTRACT | referenced via `prompt_parser` (existing); validator rules per behavior (Phase F) |
| 8 Cascade compression rule with good/bad examples | named invariant + verification + scope | validator rule (Phase F) |

All eight close at Phase F exit — which is the condition for G5 Steward quarterly audit to pass OM §4.5.

---

## 9. OPERATING_MODEL §7 Adaptive Rigor → Forge ceremony_level

CGAID: 3 tiers (Fast Track / Standard / Critical).
Forge: 3 `ceremony_level` values — `{LIGHT, STANDARD, FULL}`. Verified `execute.py:53-60` `_determine_ceremony`, `seed_data.py:21,29,57,85`. (An earlier draft of this document claimed 4 levels including `MINIMAL`; that was a cross-source error — outer `forge/.claude/CLAUDE.md` describes the legacy `core/` pipeline, not `platform/`. Corrected 2026-04-22 via [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md).)

### Mapping CLOSED 2026-04-22 per [ADR-002](decisions/ADR-002-ceremony-level-cgaid-mapping.md)

**1:1, no collapse needed.**

| Forge `ceremony_level` | CGAID tier | Required artifacts (OM §7.1 subset) | Triggered by `_determine_ceremony` |
|---|---|---|---|
| `LIGHT` | Fast Track | AC tagging (always); PR review (always); tests-in-PR; Evidence Pack inline in PR acceptable | `chore`, `investigation`, or `bug` with `ac_count ≤ 3` |
| `STANDARD` | Standard | + Evidence Pack; + Execution Plan; + Handoff; + ADRs (non-trivial decisions); + Edge-Case Test Plan; + Business-Level DoD; + Side-Effect Map (when external systems / mutating ops / cross-module) | `feature` with `ac_count ≤ 3` |
| `FULL` | Critical | Standard + Master Plan in Cockpit; + ADRs for every material decision; + Edge-Case Test Plan with explicit failure-mode enumeration (all 9 `scenario_type` categories per [ADR-001](decisions/ADR-001-scenario-type-enum-extension.md)); + Business-outcome evidence artifact; + second reviewer with domain expertise; + Steward sign-off | all other tasks (default) |

### Fast Track preconditions (OM §7.2, all must hold — validator rule)

1. change < [scope threshold calibrated]
2. no new external integration
3. no mutation of production data
4. existing test coverage ≥ 80% on touched files

Violating any → block Fast Track tier; require Standard-tier retrofit.

### Tier escalation triggers (OM §7.4, engineer-initiated + reviewer-verified)

- unexpected side-effect discovered at Stage 3
- new regulatory/compliance implication
- cross-module cascade detected during `ImpactClosure`
- Steward flags scope drift

All encoded as validator rules on `Task.ceremony_level` transitions.

---

## 10. OPERATING_MODEL §9 Gate mechanics spectrum → Forge gate registry

OM §9.1 classifies gates as **Deterministic / Rubric-based / Judgment-based**. Forge `GateRegistry` (Phase A) must record this classification per gate so Steward audit (G5) knows which gates are policy (need human discipline) vs technical (enforced by code).

Mapping (partial, based on OM §9.1 examples):

| CGAID Gate | Classification | Forge implementation |
|---|---|---|
| Classification log exists per ingested file | Rubric-based (→ Deterministic with DLP) | Phase G1 trigger |
| Client consent for Confidential+ | Rubric-based | G1 Steward sign-off |
| Evidence Pack produced | Judgment-based (→ Rubric) | Phase G6 schema validator |
| Every decision has ADR | Judgment-based (→ **Deterministic**) | G6 PR description grep |
| Edge-case test list exists | Judgment-based (→ Rubric) | Phase D + G6 template |
| Side-Effect Map present | Judgment-based (→ **Deterministic** on tier trigger) | Phase C registry + G6 tier check |
| Every non-trivial assumption tagged | Judgment-based | P19 validator (Phase F) |
| No UNKNOWN at merge | Judgment-based (→ **Deterministic**) | P20 BLOCKED state (Phase F) + pre-merge grep |
| Mandatory PR review | Judgment → **Deterministic** (branch protection) | existing + Steward role (G5) |
| Business outcome observed | Judgment-based (inherent) | G3 M6 metric |

Forge's `GateRegistry.classification` field (added in Phase G to existing Phase A table) carries one of `{deterministic, rubric, judgment}` per registered gate.

---

## 11. PRACTICE_SURVEY 18 incidents → Forge regression fixtures

`PRACTICE_SURVEY.md` lists 18 historical incidents classified against the 10 principles. Every incident that reveals a coverage gap is a candidate for Forge `FailureMode` + adversarial test (per OM §4.3 v1.5 runtime-incident rule + Forge Phase D adversarial suite).

Phase D `build_adversarial_fixtures.py` seed data should read `PRACTICE_SURVEY.md` incidents as well as Forge's own `Finding` history. Cross-project learning: the cascade-invalidation incident `f6d24dc` becomes a Forge regression test even though it occurred in a different codebase — the *pattern* (cascade decision without named invariant) transfers.

---

## 12. Gaps acknowledged, not closed

> **⚠ Deep-risk audit 2026-04-23** flagged this section as **R-FW-04 composite 15 HIGH** — Framework Steward may reject these "acknowledged gaps" during quarterly audit (OM §4.5) as non-compliance. This list is **not self-certifying**; it requires distinct-actor Steward sign-off before Forge can claim CGAID compliance.
>
> Additionally, the culturally-induced gap around **R-FW-02 Stage 0 policy-only** (composite 19 CRITICAL) means Forge cannot safely be adopted for Confidential+ material without deployed DLP. That is NOT "not Forge's responsibility" — that is an adoption precondition Forge must enforce at UI + Steward-audit level (see CHANGE_PLAN §13.3 G1 escalation).

Forge is a CGAID implementation at the platform layer. CGAID elements that are **not Forge's responsibility**:

- **Culture** — MANIFEST adoption, team onboarding, printed-on-the-wall posters. Forge enforces discipline; it does not produce culture.
- **Framework Stewards as people** — G5 adds `steward_role` to schema, but the human rotation policy is org-level (OM §12). Forge cannot rotate Stewards; it can only record who is Steward.
- **Regulatory alignment (EU AI Act, GDPR)** — OM Appendix B + §6 Data Handling. Forge participates via Stage 0 (G1) and PII scanner (exists: `pii_scanner.py`). Deeper regulatory mapping is per-adopting-org.
- **Kill criteria (OM §12)** — deciding to abandon CGAID is a governance decision, not a platform decision. Forge can report metrics that feed kill-criteria evaluation; it cannot decide.
- **Emergency Response Pattern (OM §7.5)** — production-fire bypass path. Orthogonal operational capability; not in Phase G scope; deferred to separate decision.

These are **ACKNOWLEDGED gaps**, not "missing features". Framework Steward quarterly audit (OM §4.5) covers them separately.

---

## 13. Version trail

- **v1 (2026-04-22)** — this document. Created as part of patch v2.1 to close "Forge vs framework" positioning gap identified during deep-verify.

Future changes to this document require ADR per OM §9.2 (no solo-authorship of framework-mapping changes by the same actor that wrote the change).

# Theorems — Audit & Action Register

> Master registry of theorem files in `.ai/theorems/`. Records: verdict per file (from /deep-verify run 2026-05-05), canonical declaration per topic, action register for NEEDS-WORK files, deferred-work tracking.
> Companion: `CANONICAL.md` (gospel set declaration + supersedes mappings).
> Source verification: 6 parallel /deep-verify subagents, 2026-05-05; subagents' [CONFIRMED] = audit's [ASSUMED] until spot-checked (per CONTRACT §B Subagent).

---

## Verdict summary (26 files)

| Verdict | Count | % |
|---|---:|---:|
| ACCEPT | 7 | 27% |
| NEEDS-WORK | 17 | 65% |
| REJECT | 2 | 8% |

## Verdict register (full)

### ACCEPT (canonical reference set — see `CANONICAL.md` for topic mapping)

| File | Domain | Operational |
|---|---|---|
| `test/Topologically Closed Data Regression Testing Theorem.md` | data regression testing | HIGH |
| `verify/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` | epistemic soundness | HIGH |
| `decide/Evidence_Only_Decision_Model.md` | decision validity (E1-E8) | HIGH |
| `develop/Unified_Evidence_Grounded_Development_Soundness_Theorem.md` | develop phase soundness | HIGH |
| `plan/Evidence_Constrained_Planning_Theorem.md` | planning gates | HIGH |
| `Adaptive Contract-Governed Work Evolution Theorem.md` | process evolution + loop detection | HIGH |
| `analysis/Evidence-Driven Iterative Analysis Closure Theorem.md` | iterative analysis loops | MEDIUM |

### NEEDS-WORK (use with awareness of gaps; do not cite as gospel)

| File | Top gap | Priority |
|---|---|---|
| `test/CODE-GROUNDED TEST REALIZATION THEOREM.md` | Polish addendum; thresholds undefined; no anchor | T2 |
| `test/COMPREHENSIVE TEST OBLIGATION CLOSURE THEOREM.md` | derive_obligations() blackbox; magic numbers; overlaps Rational | T1 (merge candidate) |
| `test/Rational Test Space Closure Theorem.md` | threshold undefined; redundancy with COMPREHENSIVE | T1 (merge candidate) |
| `verify/Adaptive_Process_Degradation_under_Missing_Information.md` | InformationLoss/DependencyMismatch undefined; mixed lang | T1 (merge into Epistemic Continuity §6) |
| `verify/Engineer_Soundness_Completeness.md` | ∃! h conflicts CONTRACT §B.10 (≥3 hyp); Suff/Closure undefined | T2 |
| `verify/Information_Topology_Preservation_and_Error_Propagation.md` | d_X/d_Y/d_Z metrics undefined; redundant with Epistemic Continuity | T1 (merge candidate) |
| `debug/Completeness and Error Discovery.md` | duplicate of Error_Discovery; circular sufficiency proof | T1 (merge candidate) |
| `debug/Error_Discovery.md` | conflicts §A.10 (uniqueness vs ≥3 hyp); G undefined | T1 (merge w/ Completeness) |
| `spec/Scope - SPEC Execution Protocol.md` | reconstruct() undefined; Polish; F termination | T2 |
| `develop/Forge Unified Development Theorem.md` | differentiability metaphor; Score units; no anchor | T1 (declare relation to Unified_Evidence_Grounded canonical) |
| `plan/Equivalent Planning Realization Theorem.md` | Essential() circular; Lipschitz vacuous | T2 |
| `Anti-Defect Answer Projection Theorem.md` | λ weights undefined; Polish/English; two formulations | T2 |
| `Forge Complete Evidence-Guided Development Theorem.md` | typo "differentientiable"; Score units; predicates undefined | T2 |
| `UX/Human-AI Workflow Realization Theorem.md` | UXCost incommensurate; ||ΔUXG|| metaphor; no screen anchor | T3 |
| `business analysis/Business-Consistent Deterministic Development and Architecture Selection.md` | Score formula malformed (no operators); FitBiz undefined | T2 |
| `business analysis/Topologically Consistent Differentiable Business Process Construction Theorem.md` | differentiability metaphor; Semantics undefined; bilingual | T3 |
| `completness/Implementation Closure Theorem.md` | embeds personal review; L1-L7 unjustified; LLM hardcoded | T2 |

### REJECT (active remediation)

| File | Resolution | Status |
|---|---|---|
| `decide/Decision Correctness Condition.md` | Mark SUPERSEDED by `Evidence_Only_Decision_Model.md`. Demoted to "exploration operator catalogue" — content kept for §1 operator taxonomy reference only. | Done 2026-05-05 |
| `theorms.md` | Mark as MATH REFERENCE CATALOG (not theorem). Update CONTRACT.md §C cross-ref to point to `Anti-Defect Answer Projection Theorem.md` for AUP. | Done 2026-05-05 |

---

## Cross-cutting patterns (system-level gaps)

| # | Pattern | Affected files | Severity | System-level fix |
|---|---|---|---|---|
| C1 | Polish/English mix | 12+ files | violates "All English" rule (memory `project_ai_dir_structure.md`) | Translate canonical (7) first; NEEDS-WORK on demand |
| C2 | Undefined core predicates: `Suff()`, `Closure()`, `Score()`, `parse()`, `behaviors()`, `derive_obligations()`, `Critical()` | 15+ files | unfalsifiable | Centralize definitions in CONTRACT.md §F (Primitives Glossary) — single source |
| C3 | Magic thresholds (≥1.3, ≥2.0, ≥0.5, ε, λ, δ) | 10+ files | non-operational | Each threshold needs justification OR mark as heuristic |
| C4 | Differentiability/Lipschitz as metaphor | 5 files (Forge Unified, Equivalent Planning, Topologically Consistent Differentiable, UX, Forge Complete) | math-theater | Rename to "predictable change locality" OR remove |
| C5 | Score formulas with incommensurate units | 6+ files | argmax non-deterministic | Either (a) weights + units OR (b) lexicographic ordering OR (c) drop scoring → ordered checklist |
| C6 | No  empirical anchors | 22/26 files | violates CONTRACT §A | Each theorem needs ≥1  incident citation (TD-20, 986-row CREST, BE W17, etc.) |
| C7 | Cross-theorem overlap without canonical declaration | several pairs | conflicting verdicts | Resolved by `CANONICAL.md` (this registry) |
| C8 | Uniqueness `∃! h*` conflicts CONTRACT §B.10 (≥3 hypotheses) | Engineer_Soundness, Error_Discovery, Unified_Evidence | brittle gates | Distinguish generation (≥3) vs selection (1) — clarify in each |

---

## Action register

### Done 2026-05-05

- [x] /deep-verify of all 26 theorem files (6 parallel subagents)
- [x] AUDIT.md (this file) created
- [x] CANONICAL.md created — gospel set declaration
- [x] REJECT remediation: `decide/Decision Correctness Condition.md` SUPERSEDED header added
- [x] REJECT remediation: `theorms.md` MATH-REFERENCE-CATALOG header added
- [x] CONTRACT.md §C updated — AUP cross-ref redirected to `Anti-Defect Answer Projection Theorem.md`
- [x] 7 ACCEPT files: empirical anchor section added (1  incident each)

### T1 (next 30 days) — Canonical/merge work

| Task | Owner | Notes |
|---|---|---|
| Merge `verify/Adaptive_Process_Degradation` → `Epistemic Continuity §6` (or formalize standalone) | TBD | sister theorems duplicate; consolidate |
| Merge `verify/Information_Topology_Preservation` → `Epistemic Continuity` (declare canonical) | TBD | redundant |
| Merge `debug/Completeness and Error Discovery` ↔ `debug/Error_Discovery` (pick one) | TBD | near-duplicates |
| Merge `test/COMPREHENSIVE TEST OBLIGATION` ↔ `test/Rational Test Space` | TBD | overlap |
| Declare `develop/Forge Unified` as abstract counterpart to `Unified_Evidence_Grounded` (canonical) | TBD | pair, not duplicates |

### T2 (next quarter) — Definitional & translation work

| Task | Owner | Notes |
|---|---|---|
| Translate Polish fragments → English in 12+ NEEDS-WORK files | TBD | start with most-cited |
| Add Primitives Glossary to CONTRACT.md §F: define `Suff`, `Closure`, `Score`, `Critical` operationally | TBD | centralize, then theorems cross-ref |
| Reconcile uniqueness `∃! h*` vs `≥3 hypotheses` in: `Engineer_Soundness`, `Error_Discovery`, `Unified_Evidence_Grounded` | TBD | distinguish generation (≥3) vs selection (1) |
| Strip "differentiability" metaphor from 5 files OR reframe as "predictable change locality" with edit-distance bound | TBD | currently mathematics-theater |
| Define magic thresholds OR mark heuristic in 10+ files | TBD | threshold derivation OR honest "heuristic" tag |

### T3 (when triggered) — Lower-priority

| Task | Owner | Notes |
|---|---|---|
| `business analysis/Topologically Consistent Differentiable` rewrite | when business modelling work hits gap | low usage today |
| `UX/Human-AI Workflow` operational anchors to  frontend | when UX review triggers | no current screen |

---

## Process evolution

### When to add a new theorem

Per Part 8.4 of `PROCESS.md`:
1. Failure mode happens 2+ times despite existing rules
2. Existing theorems do not cover it
3. Add at level 2 or 3 (per `RULES.md §6`)

### When to demote / supersede a theorem

| Trigger | Action |
|---|---|
| Theorem cited in PR but reviewer cannot operationally apply | NEEDS-WORK (this register) |
| Theorem contradicted by empirical evidence | REJECT (this register) |
| Theorem subsumed by another | SUPERSEDED header + redirect in CANONICAL.md |

### Quarterly health check

Re-run /deep-verify on theorem set. Track:
- Verdict distribution shift
- Cross-cutting patterns added/closed
- Action register completion rate

If 30%+ of theorems remain NEEDS-WORK after 90 days → process gap (theorems not being maintained as code evolves).

---

## Reference

- `CANONICAL.md` — gospel set declaration + supersedes mappings
- `CONTRACT.md` — operational contract referencing select theorems
- `PROCESS.md` Part 8 — knowledge management & evolution
- `MEMORY.md` (`~/.claude/projects/.../memory/`) — references to theorems

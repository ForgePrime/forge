# Theorems — Canonical Declaration

> Per topic, declares ONE theorem as canonical (gospel). Other theorems on the same topic are either: supersedes (deprecated), abstract counterpart (kept), or pending merger.
> Written 2026-05-05 from /deep-verify audit (`AUDIT.md`).
> Rule: when in doubt which theorem governs a verdict — **cite the canonical one**. Non-canonical theorems may still be referenced for operator catalogues, examples, or commentary, but cannot adjudicate disputes.

---

## Canonical theorem per topic (7 entries)

### Topic 1 — Decision validity

**Canonical**: `decide/Evidence_Only_Decision_Model.md` (E1–E8 conditions)

| Related file | Relationship |
|---|---|
| `CONTRACT.md §E` | Operational mirror — same E1-E8 |
| `decide/Decision Correctness Condition.md` | **SUPERSEDED** — preserved for §1 operator taxonomy reference only; do not cite as decision criterion |

Use it when: validating any decision (which alternative to pick, which fix to ship). Every recommendation is auditable against E1-E8.

### Topic 2 — Test design (data regression)

**Canonical**: `test/Topologically Closed Data Regression Testing Theorem.md` (§1–§22 + §24 runtime template)

| Related file | Relationship |
|---|---|
| `test/CODE-GROUNDED TEST REALIZATION THEOREM.md` | NEEDS-WORK — code-side companion; not data-graph-aware. Use only when theorem above does not apply (e.g., pure logic without data graph). |
| `test/COMPREHENSIVE TEST OBLIGATION CLOSURE THEOREM.md` | NEEDS-WORK — overlaps Rational; merge candidate |
| `test/Rational Test Space Closure Theorem.md` | NEEDS-WORK — overlaps COMPREHENSIVE; merge candidate |
| `.ai/templates/PROMPT-test-scenarios-from-code.md` | Operational implementation of canonical theorem |
| `.claude/skills/test-orchestrate/SKILL.md` | Orchestrator using canonical theorem |
| `.ai/TESTING.md` | Process doc citing canonical theorem |

Use it when: any change to data-processing code (settlement, PP, , marker emission, etc.). Required for changes touching CREST output.

### Topic 3 — Epistemic soundness (information topology)

**Canonical**: `verify/Epistemic_Continuity_and_Information_Topology_Preservation_for_AI_Agent_Systems.md` (C1–C12)

| Related file | Relationship |
|---|---|
| `verify/Information_Topology_Preservation_and_Error_Propagation.md` | NEEDS-WORK — redundant; merge into canonical §6 |
| `verify/Adaptive_Process_Degradation_under_Missing_Information.md` | NEEDS-WORK — sub-corollary; merge into canonical or formalize standalone |
| `verify/Engineer_Soundness_Completeness.md` | NEEDS-WORK — engineer-side projection; uniqueness conflict with CONTRACT §B.10 |

Use it when: assessing whether AI agent's reasoning preserves required relations / propagates error correctly across stages. Stage-gate test for CGAID stages.

### Topic 4 — Develop-phase soundness

**Canonical**: `develop/Unified_Evidence_Grounded_Development_Soundness_Theorem.md` (3-phase A→P→D + 5 detectors)

| Related file | Relationship |
|---|---|
| `develop/Forge Unified Development Theorem.md` | Abstract counterpart. Kept; declared as ontological/axiomatic frame; canonical above is operational version. |

Use it when: evaluating whether a development pass (analyze → plan → develop) is sound. The 5 detectors (InfoLoss, SemShift, RelDestruction, Overinterp, Underspec) are runtime-applicable.

### Topic 5 — Planning gates

**Canonical**: `plan/Evidence_Constrained_Planning_Theorem.md` (11-step model + slot completeness + Cost(skip) > Cost(step))

| Related file | Relationship |
|---|---|
| `plan/Equivalent Planning Realization Theorem.md` | NEEDS-WORK — `§19` (canonical structure) + `§25` (14-question test) are usable; rest is supplementary commentary |

Use it when: assessing whether a PLAN.md is approval-gated correctly. Slot completeness, cross-reference, and prediction accuracy 0.5 threshold are immediately checkable.

### Topic 6 — Process evolution & loop detection

**Canonical**: `Adaptive Contract-Governed Work Evolution Theorem.md` (ACGWE — 6 gates + loop detector)

| Related file | Relationship |
|---|---|
| `theorms.md` | **MATH REFERENCE CATALOG** — not a theorem; do not cite as authority |
| `Anti-Defect Answer Projection Theorem.md` | NEEDS-WORK — sister (AUP) for single-answer-quality side; ACGWE governs model evolution |

Use it when: deciding whether to evolve the operating model (process update, new rule). Required after every process gap discovered.

### Topic 7 — Iterative analysis (loops, hypothesis evolution)

**Canonical**: `analysis/Evidence-Driven Iterative Analysis Closure Theorem.md` (Observe → Hypothesize → Refute → Update → Reframe; closure when VOA(next) ≤ 0)

| Related file | Relationship |
|---|---|
| (no overlap among 26) | — |

Use it when: investigating ambiguous problem; multiple competing hypotheses; closure condition prevents premature stop or infinite iteration.

---

## Topics WITHOUT canonical (remediation needed)

### Debug / error discovery

Two near-duplicate files: `debug/Completeness and Error Discovery.md` and `debug/Error_Discovery.md`. Neither has been declared canonical because both are NEEDS-WORK with different gaps.

**Action**: T1 task (next 30 days) — pick one as canonical (Error_Discovery.md is cleaner per audit), mark other SUPERSEDED.

### SPEC execution

Single file: `spec/Scope - SPEC Execution Protocol.md` (NEEDS-WORK). Provisional canonical pending fixes (Polish→English, define `reconstruct()`, add  SPEC anchor).

### Business analysis

Two files: `business analysis/Business-Consistent Deterministic Development and Architecture Selection.md` and `business analysis/Topologically Consistent Differentiable Business Process Construction Theorem.md`. Both NEEDS-WORK. No canonical declared.

**Action**: T2-T3 — depends on whether business modelling work resumes; not blocking today.

### UX / Human-AI workflow

Single file: `UX/Human-AI Workflow Realization Theorem.md` (NEEDS-WORK). Provisional canonical for now; no competing theorems.

### Implementation closure

Single file: `completness/Implementation Closure Theorem.md` (NEEDS-WORK — embeds personal review, L1-L7 unjustified). Provisional canonical for L1-L7 layer-completeness checks; cite with awareness.

---

## Citation rules

When writing a PR description, plan, audit, or memory entry that cites a theorem:

1. **First choice**: cite a CANONICAL theorem (the 7 above).
2. **If non-canonical**: state explicitly "(non-canonical, cited for X-feature)".
3. **NEVER cite SUPERSEDED**: `decide/Decision Correctness Condition.md` and `theorms.md` are not authoritative.
4. **For multi-topic claims**: cite multiple canonical theorems by topic, not "all theorems imply X".

### Example

Bad:
> "Per the theorems, this fix is correct."

Good:
> "Per `decide/Evidence_Only_Decision_Model.md` E4 (sufficiency), the evidence supports the fix. Per `test/Topologically Closed Data Regression Testing Theorem.md` §6, the regression test plan covers ImpactClosure(v0)."

---

## Maintenance protocol

This file is updated when:

| Trigger | Action |
|---|---|
| New theorem added | Declare canonical or relate to existing canonical |
| Theorem promoted from NEEDS-WORK to ACCEPT | Consider promoting to canonical for its topic (compete with current canonical) |
| Two canonicals conflict on a verdict | Quarterly review; one is demoted (record reason in AUDIT.md action register) |
| AUDIT.md re-run shows verdict drift | Re-evaluate canonicals; may demote |

Audit cadence: quarterly per `PROCESS.md` Part 10.3.

---

## Reference

- `AUDIT.md` — full register, action items, cross-cutting patterns
- `CONTRACT.md` — operational contract that references several canonical theorems
- `PROCESS.md` — end-to-end process; cites canonical theorems
- `TESTING.md` — testing process; cites canonical test theorem

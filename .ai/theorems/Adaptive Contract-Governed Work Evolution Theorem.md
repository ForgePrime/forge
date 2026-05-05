# Adaptive Contract-Governed Work Evolution Theorem

> Formal foundation for how the work model itself improves over time.
> Sister theorem to **Meta-Answer Optimality Theorem (AUP)** — AUP governs single answers, ACGWE governs evolution of the system that produces them.
>
> Practical enforcement is encoded in:
> - `.ai/CONTRACT.md` §C (Anti-A₀ + Loop-detection gates) — per-change behavior
> - `.ai/RULES.md` Rule 8 (Challenge before fix) — operational checklist
> - `.ai/LESSONS_LEARNED.md` (TD ladder incident 2026-04-25) — empirical grounding
> - `.ai/framework/OPERATING_MODEL.md` (Stage 0 + Decision Algorithm) — workflow integration

---

## 1. Spaces

```
H   = work history (tasks, decisions, errors, fixes, regressions)
M   = work model (framework + manifest + workflow + contract)
C   = constraints (business, technical, operational)
O   = observed outcomes (success / failure / cost / latency / regressions)
ΔM  = proposed change to the work model
```

## 2. Base problem (empirical from TD ladder, 2026-04-25)

Without governance:

```
fix₁ → regression → fix₂ → regression → fix₃ → ...
```

Formally:

```
M₀ → M₁ → M₂ → ... → M_k
```

with `Quality(M_k)` not monotonically increasing. The system finds local optima and stays there.

## 3. Quality function

```
Q(M) =
    − ErrorRate
    − RegressionRate
    − TimeToResolution
    − Uncertainty
    + Predictability
    + Reproducibility
    + EarlyDetection
```

Goal: `M* = argmax Q(M)`.

## 4. Main theorem

A work model `M` converges toward an optimal state `M*` **iff** every proposed change `ΔM` satisfies the **6-gate admission**:

```
Accept(ΔM)  ⇔
    Derived(ΔM, H)              -- empirical grounding (real failure)
∧   Challenged(ΔM)              -- adversarial reasoning
∧   AlternativesExist(ΔM, ≥2)   -- comparison space
∧   Evidenced(ΔM, O)            -- validated against outcomes
∧   Contracted(ΔM)              -- encoded as enforceable rule
∧   Reversible(ΔM) ∨ Bounded(ΔM)  -- rollback or limited blast radius
```

Plus the **failure-reduction invariant**:

```
ExpectedError(M + ΔM) < ExpectedError(M)
```

If `ΔM` doesn't reduce expected future error of a class (only the current incident), it is patch-work, not model evolution.

## 5. Operators

### 5.1 Inference from history
`Infer(H) → {ΔM₁, ΔM₂, ...}` — change candidates derived from real failures (not theoretical).

Example from TD ladder:
- `H = {TD-20→regression, TD-23→regression, TD-25→regression}`
- `Infer(H) = "fix-first strategy without model re-evaluation is unstable"`
- `ΔM = "add loop-detector: after 2 consecutive defensive fixes, mandatory model re-evaluation"`

### 5.2 Adversarial challenge
For each `ΔM`:
```
Challenge(ΔM) = {c₁, c₂, ..., c_n}
   where c_i = counterargument | failure scenario | hidden assumption
```

Minimum: 3 counterarguments. Empty challenge = `ΔM` rejected (treated as A₀ from AUP).

### 5.3 Alternatives
`Alt(ΔM) = {ΔM₁, ΔM₂, ..., ΔM_k}` with `|Alt| ≥ 2`.

Without alternatives there is no decision, only confirmation bias. This is the **enforced ALTERNATIVES rule** from `CONTRACT.md` §B.3.

### 5.4 Evidence
`Evidence(ΔM) = data ∪ experiments ∪ historical_matches`

Evidence quality (per CGAID):
- post-hoc verification → weak (system is already in failure state, baseline ambiguous)
- pre-code validation → strong (test before write, falsifiable hypothesis)

### 5.5 Decision
```
ΔM* = argmax_i [
    ExpectedImprovement(ΔM_i)
  − Risk(ΔM_i)
  − Complexity(ΔM_i)
]
```

### 5.6 Contracting (the gate that closes the loop)
```
ΔM* → Rule ∈ CONTRACT
```

A change that does not become an enforceable rule is decoration. Per `RULES.md` Rule 6: lessons must move to blocking mechanisms (hooks, tests), not stay as markdown notes.

## 6. Anti-A₀ enforcement (sister to AUP)

Every `ΔM` is rejected if it is:

- `first_plausible_fix` — the obvious one
- `pattern_match_only` — by analogy from prior unrelated case
- `surface_level` — addresses symptom not cause
- `not_challenged` — no adversarial pass
- `single_alternative` — no comparison space
- `unbounded_blast_radius` — no rollback or scope limit
- `defensive_against_prior_fix` (without model re-evaluation) — sign of fixpoint loop

## 7. Loop-detection rule (anti-fixpoint)

Define a **defensive fix** as one whose justification is: "to undo a regression introduced by fix N−1".

Then:

```
if count_consecutive_defensive_fixes ≥ 2:
    STOP
    require: model_reevaluation()
    output: "fix N+1 is rejected. Stack: fix N defensive vs fix N−1.
             Re-evaluate baseline before next change."
```

Empirically validated by TD ladder (2026-04-25):
- TD-20 (active fix) → regression
- TD-23 (defensive vs TD-20) → regression
- TD-24+25 (defensive vs TD-23) → continued regression
- Resolution: revert TD-20, TD-23, TD-24, TD-25 (4 commits) — kept only TD-21+22 (independent real bug)

Total cost of skipping loop-detection: ~5 hours of reactive work + 4 wasted commits.

## 8. Spatial validation

`ΔM` must be evaluated in 6 dimensions before admission:

```
S = {
    logical,      -- is the fix logically sound?
    operational,  -- can it be deployed/rolled-back?
    temporal,     -- does it introduce/hide latency?
    cost,         -- compute/storage/human cost?
    systemic,     -- effect on other components?
    dependency,   -- callers, consumers, side effects (per RULES.md Rule 7)
}
```

Skipping any dimension = `ΔM` rejected.

## 9. Early detection (shift-left)

```
DetectionTime(M + ΔM) < DetectionTime(M)
```

A `ΔM` that improves Q must shift error detection earlier in the workflow:
- best: detected at planning (Stage 0/1)
- good: detected at code review (Stage 2)
- weak: detected at runtime (Stage 4)
- failure: detected in production

## 10. Final form (canonical statement)

> A model of work evolves correctly **only if** every change to it:
> 1. is derived from real failures (not theoretical worry)
> 2. is challenged by adversarial reasoning (≥3 counterarguments)
> 3. is compared against alternatives (≥2)
> 4. is supported by evidence (pre-code preferred over post-hoc)
> 5. is encoded into enforceable rules (not markdown notes)
> 6. reduces future error probability (class, not single incident)
> 7. improves early detection capability (shift-left)
> 8. is reversible or bounded in blast radius
>
> **Defensive fixes more than 1 deep without model re-evaluation are forbidden.**

---

## Appendix A — Mapping to existing docs

| ACGWE element | Existing enforcement | Gap |
|---|---|---|
| Derived from H | LESSONS_LEARNED.md exists | not auto-consulted before fix |
| Challenged | CONTRACT.md §B.5 FAILURE SCENARIOS (≥3) | applied inconsistently |
| Alternatives | CONTRACT.md §B.3 ALTERNATIVES (≥2) | skipped for "simple bugs" |
| Evidenced | CONTRACT.md §B.1 DID/DID NOT/CONCLUSION | strong |
| Contracted | RULES.md Rule 6 (block, not note) | strong principle, weak tooling |
| Reversible | not formalized | **NEW** — added in CONTRACT §C |
| Loop-detection | not formalized | **NEW** — added in CONTRACT §C |

## Appendix B — Why this theorem (problem this solves)

The TD ladder incident (2026-04-25) showed that:
- All individual rules in CONTRACT/MANIFEST/RULES were technically followed
- Each fix in isolation passed disclosure (DID/DID NOT, CONFIRMED, etc.)
- Yet the **system as a whole** drifted away from optimum
- 5 fixes deep, the cumulative state was worse than baseline

Single-change rules (CONTRACT §B) are necessary but not sufficient. They prevent local errors, not strategic loops. ACGWE adds the **meta-loop**: rules about how rules accumulate, when to step back, when to revert.

This is the difference between **AUP** (don't give A₀ for one answer) and **ACGWE** (don't let A₀-answers compound across the work model).

---

## Empirical anchors (2026)

## Notes on cross-references

- §5.6, §6, §8 reference `RULES.md` Rule 6/7/8 — `.ai/RULES.md` does exist and contains the 8 rules; references confirmed valid as of 2026-05-05.

## Status (per `AUDIT.md` 2026-05-05)

ACCEPT — canonical for process evolution + loop detection. Sister `Anti-Defect Answer Projection Theorem.md` (NEEDS-WORK) covers AUP single-answer side.

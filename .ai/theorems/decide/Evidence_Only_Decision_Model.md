Theorem (Evidence-Only Decision Model)

A decision d is valid if and only if all of the following conditions hold:

1. Evidence Existence (No Decision Without Evidence)

∀ d ∈ Decisions:

Decision(d) implies ∃ E(d)

Meaning:

no decision may exist without evidence
absence of evidence automatically invalidates the decision
2. Evidence Source Constraint

∀ d ∈ Decisions:

E(d) ⊆ Data ∪ Code ∪ Requirements

Meaning:

all evidence must come from:
observed data
system code
defined requirements
no external assumptions or intuition are allowed
3. Evidence Verifiability

∀ e ∈ E(d):

Verifiable(e)

Meaning:

every piece of evidence must be:
reproducible
inspectable
independently verifiable
4. Evidence Sufficiency

∀ d ∈ Decisions:

Suff(E(d), d)

Meaning:

the evidence must be sufficient to justify the decision
partial or weak evidence is not acceptable
5. Assumption Elimination

∀ a ∈ Assumptions:

Validated(a)
or
Explicit(a)

Additionally:

unverified assumptions must be explicitly marked
hidden assumptions are not allowed
6. Traceability

∀ d ∈ Decisions:

Traceable(d)

Meaning:

it must be possible to show:
what was checked
how it was checked
why the conclusion was made
7. Explicit Uncertainty Separation

State = (Certain, Uncertain)

and:

Certain ∩ Uncertain = empty

Meaning:

clearly separate:
what is proven
what is uncertain
no mixing of facts and assumptions
8. Deterministic Justification

For the same inputs:

Justification(d) is deterministic

Meaning:

same data → same conclusion
no subjective interpretation allowed

---

## Empirical anchors (2026)

| Anchor | Condition violated |
|---|---|
| **Option B refactor R1** (CONTRACT.md §E line 208, 2026-04-27) | E4 Sufficiency — recommendation passed §A and §B disclosure but had zero BQ rows queried before recommending. Hidden assumption "markers in BQ are post-Option B". Collapsed within one verification turn. |
| **22 "multi-week recurring residual"** (`feedback_simulation_must_match_filters.md`) | E2 Source constraint — simulation evidence was not from `Data ∪ Code ∪ Requirements` (it was from a sim that lacked prod filters). Decision based on it was invalid. |
| **`project_reappeared_business_rule.md` memory drift** | E1 Evidence existence — memory cited as evidence; later refuted empirically. Memory ≠ evidence. |

## Status (per `AUDIT.md` 2026-05-05)

ACCEPT — canonical for decision validity. Mirrored as enforceable in `CONTRACT.md §E`. Supersedes `decide/Decision Correctness Condition.md` (REJECT).
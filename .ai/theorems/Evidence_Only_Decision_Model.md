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
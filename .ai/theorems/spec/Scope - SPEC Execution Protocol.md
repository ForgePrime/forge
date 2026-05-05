Scope → SPEC Execution Protocol (SSEP)
0. Global Contract (hard rules)
1. No assumption may be silently embedded in SPEC.
2. Every SPEC element must be traceable to ScopeClosure.
3. Every uncertainty must be classified: UNKNOWN / ASSUMPTION / DECISION_REQUIRED.
4. No element may enter SPEC without justification.
5. SPEC must be executable without further interpretation.
6. Reverse reconstruction must be possible: reconstruct(SPEC) ≡ ScopeClosure.
7. If any gate fails → STOP and report.
1. Phase A — Scope Decomposition
Input
Raw Scope (unstructured or structured)
Output
SC_explicit = {
    business,
    functional,
    technical,
    non-functional,
    data,
    security,
    performance,
    UX,
    integration,
    operational
}
Required structure (per item)
sc_id
type
statement
source
confidence
ambiguity_level
Gate A1 — Completeness
Every statement from input must be mapped.
No loss allowed.
2. Phase B — Interpretation Layer
Goal

Nie wolno przejść dalej bez interpretacji.

Output
I(sc) = {
    intended_meaning,
    business_goal,
    expected_behavior,
    constraints,
    ambiguity,
    interpretation_confidence
}
Gate B1 — Interpretation Validity
CorrectInterpretation(sc) ⇔
    ambiguity = 0
    OR explicitly_marked_as_unknown
Gate B2 — No Silent Assumptions
If interpretation introduces new info:
    mark as ASSUMPTION or INFERRED
3. Phase C — Implicit Scope Derivation
Goal

Zbudować pełny ScopeClosure.

Output
SC_implicit = {
    dependencies,
    data contracts,
    state transitions,
    failure modes,
    retries,
    concurrency,
    permissions,
    lifecycle,
    observability,
    validation rules,
    temporal behavior
}
Definition
ScopeClosure = SC_explicit ∪ SC_implicit ∪ TechnicalNecessities
Gate C1 — Closure Completeness
∀ consequence(sc):
    must be present in SC_implicit
Gate C2 — No Missing Consequences
Gap = ScopeClosure − covered_elements
Gap must be empty
4. Phase D — Uncertainty Model
Output
U = {
    UNKNOWN,
    ASSUMPTION,
    DECISION_REQUIRED,
    CONFLICT
}
Rule
UNKNOWN → must block execution OR be resolved
ASSUMPTION → must have risk
DECISION_REQUIRED → must have options
Gate D1 — Full Exposure
No hidden uncertainty allowed
5. Phase E — Scope Boundary Enforcement
Output
OUT = elements not traceable to ScopeClosure
Rule
∀ sp :
    must trace to ScopeClosure
Gate E1 — Over-Spec Detection
If no trace → reject(sp)
6. Phase F — Realization Strategy
For each scope item
R(sc) = {
    implementation approach,
    alternatives,
    rejected alternatives,
    trade-offs,
    risks,
    constraints,
    confidence
}
Gate F1 — Justification
justified(sc) ⇔
    necessary ∧ sufficient ∧ no simpler solution exists
7. Phase G — SPEC Construction
SPEC Unit
SpecUnit(sc) = {
    business_intent
    functional_behavior
    technical_design
    data_contract
    state_model
    dependency_model
    constraints
    risk_model
    failure_model
    edge_cases
    acceptance_criteria
    test_obligations
    observability
    rollback/recovery
    ownership
}
Gate G1 — Execution Readiness
A developer can implement without asking:
    "what does this mean?"
8. Phase H — Traceability Matrix
Output
TRACE = {
    sc_id → sp_id → test_id → runtime_behavior
}
Gate H1 — Full Coverage
Coverage(ScopeClosure, SPEC) = 1
Coverage(SPEC, ScopeClosure) = 1
9. Phase I — Test Model (Edge-Driven)
Required test types
- edge cases
- boundary conditions
- invalid inputs
- failure modes
- retry / reprocessing
- concurrency
- temporal
- integration
- data quality
- security
- permissions
Gate I1 — Domain Equality
Domain(Scope) = Domain(Tests)
Gate I2 — No Fake Coverage
happy-path-only ⇒ FAIL
10. Phase J — Topology & Consistency
Build graph
G = (Scope, Spec, Dependencies, Tests, Risks)
Gate J1
Connected(G) = true
No isolated nodes
No contradictions
11. Phase K — Reverse Reconstruction
Test
SC_reconstructed = reconstruct(SPEC)
Gate K1
SC_reconstructed ≡ ScopeClosure

If not:

SPEC invalid
12. Phase L — Implementation Readiness
Check
1. No ambiguity
2. No missing behavior
3. All dependencies defined
4. All edge cases defined
5. All tests defined
6. All risks addressed
7. All unknowns resolved or surfaced
Gate L1
ReadyToImplement = true
13. Final Output (mandatory)

Agent MUST produce:

1. Executable SPEC
2. Scope decomposition
3. Interpretation model
4. Implicit scope matrix
5. Uncertainty register
6. Realization strategy per item
7. Traceability matrix
8. Edge-case test matrix
9. Out-of-scope rejection list
10. Reverse reconstruction proof
11. Implementation readiness verdict
14. Failure Conditions (hard stop)
STOP if:

- ambiguity unresolved
- implicit scope missing
- traceability incomplete
- over-spec detected
- test domain mismatch
- reverse reconstruction fails
- execution not possible without guessing
15. Core Principle
Do not transform Scope into text.

Transform Scope into an executable, justified, closed system
that removes all future interpretation work.
16. One-line Definition
A correct SPEC is a lossless, justified, uncertainty-aware,
fully closed and executable transformation of Scope.
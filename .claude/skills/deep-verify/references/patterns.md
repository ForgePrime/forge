# Known Impossibility Patterns

Check findings against these patterns during Step 2 (Scan).
A pattern match = high confidence in finding + enables early REJECT if S >= 6.

## Definitional Contradictions

| ID | Name | Signals | Why Impossible |
|----|------|---------|----------------|
| DC-001 | PFS + Escrow | "perfect forward secrecy" + "key recovery" | PFS = past sessions unrecoverable. Escrow = recoverable. Mutually exclusive by definition. |
| DC-002 | Gradual Typing + Guaranteed Termination | "dynamic types" + "always terminates" | Rice's theorem: non-trivial semantic properties undecidable for arbitrary programs with dynamic typing. |
| DC-003 | Deterministic + Adaptive | "reproducible" + "self-improving" | Same input = same output vs. output changes from learning. Valid ONLY if scope clearly separated (deterministic inference, adaptive training). |
| DC-004 | CAP Theorem Violation | "strong consistency" + "high availability" + "partition tolerance" | Brewer/Gilbert-Lynch: must choose 2 of 3. Cannot have all simultaneously. |

## Theorem Violations

| ID | Name | Signals | Theorem |
|----|------|---------|---------|
| TV-001 | VCG + Balanced Budget | "strategy-proof" + "balanced budget" + "individually rational" | Green-Laffont impossibility |
| TV-002 | FLP Impossibility | "async network" + "consensus" + "fault tolerance" + "guaranteed termination" | FLP theorem: async consensus impossible with even one faulty process requiring termination |
| TV-003 | Universal Termination | "detects all infinite loops" / "proves termination for any program" | Halting problem (Turing) |
| TV-004 | Universal Detection | "100% recall" / "finds all bugs" / "no false negatives" | Rice's theorem: non-trivial semantic properties undecidable |
| TV-005 | Arrow's Impossibility | "fair voting" + "non-dictatorship" + "Pareto" + "IIA" | Arrow's theorem: no system satisfies all four criteria |

## Statistical Impossibilities

| ID | Name | Signals | Why |
|----|------|---------|-----|
| SI-001 | Accuracy Without N | "99.9% accuracy" without sample size | High accuracy claims require sufficient N to be meaningful |
| SI-002 | Quantum Hype | "achieved quantum speedup" (not theoretical) | Current NISQ devices: ~100-1000 noisy qubits. No proven general optimization speedup. |
| SI-003 | Unverifiable Optimum | "finds global optimum" for NP-hard problem | Verifying global optimality requires exhaustive search |
| SI-004 | Fictional Benchmarks | Performance claims in past tense for future tech | Presenting projections as achieved results |

## Regulatory Contradictions

| ID | Name | Signals | Why |
|----|------|---------|-----|
| RC-001 | FDA Class III + Learning | "Class III" + "continuous learning" | Each model change requires new PMA. Exception: Class II with PCCP. |
| RC-002 | HIPAA + Rich Analytics | "HIPAA compliant" + "patient data analytics" | De-identification required. Rich analytics may enable re-identification. |
| RC-003 | Automated Legal Advice | "legally defensible" / "binding assessments" | UPL — Unauthorized Practice of Law. Valid only as assistant to licensed attorneys. |

## Ungrounded Core Concepts

| ID | Name | Signals | Why |
|----|------|---------|-----|
| UG-001 | Undefined Central Concept | Key term used repeatedly without operational definition | If central concept undefined, value proposition unverifiable |
| UG-002 | Circular Definition | X defined in terms of Y, Y defined in terms of X | Provides no actual meaning |
| UG-003 | Scope Creep Definition | Same term means different things in different sections | Enables equivocation fallacy |

---

## How to Use

1. During Step 2, scan for **signals** (keywords in the artifact)
2. If signals match a pattern, verify with the **check question**: does the artifact actually claim both sides?
3. Confirmed match → finding is CRITICAL + pattern bonus (+1 to score)
4. If S >= 6 with pattern match → can skip to Step 5 (early REJECT)
5. If finding looks like a pattern but no match → proceed normally, it may be a novel issue

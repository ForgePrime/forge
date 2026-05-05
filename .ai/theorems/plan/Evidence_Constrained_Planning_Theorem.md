1. Definicje

Niech:

R — user request
P — plan
S = (S1, S2, ..., S11) — sekwencja kroków planu
A_i — artefakt wyprodukowany przez krok i
E_i — evidence dla kroku i
Slot_i — zbiór wymaganych slotów w kroku i
Filled_i — zbiór slotów faktycznie wypełnionych w kroku i
U — zbiór UNKNOWN
K — zbiór ASSUMED
C — zbiór CONFIRMED
G_i — gate dla kroku i
Approve — approval gate
Impl — implementacja
Pred — przewidywania z Kroku 1
Obs — obserwacje z kroków 2–10
Impact(Δ) — zbiór wpływu zmiany
Skip_i — jawne pominięcie kroku i
Cost(step_i) — koszt wykonania kroku i
Cost(skip_i) — koszt pominięcia kroku i
Phase_j — faza implementacji
ExitGate_j — testowalny warunek wyjścia fazy j
2. Obowiązek artefaktowy

Każdy krok musi wyprodukować artefakt.

∀ i ∈ [1..10]:

A_i ≠ empty

Mocniejsza wersja:

∀ i ∈ [1..10]:

Filled_i = Slot_i
or
Skip_i = explicit

Znaczenie:

każdy krok jest albo wykonany
albo jawnie pominięty przez visible skip
3. Reguła ekonomii skrótu

Skrót ma koszt większy niż wykonanie kroku.

∀ i ∈ [1..10]:

Cost(skip_i) > Cost(step_i)

Można to zapisać też jako funkcję decyzyjną:

Choose(step_i) iff Cost(step_i) < Cost(skip_i)

Znaczenie:

system jest zaprojektowany tak, żeby wykonanie kroku było tańsze niż oszustwo lub pominięcie
4. Slot completeness

Krok jest kompletny tylko wtedy, gdy wszystkie sloty są wypełnione.

Complete(S_i) iff Filled_i = Slot_i

Jeżeli nie:

Filled_i ≠ Slot_i => Skip_i required

5. Evidence constraint

Każdy niebanalny claim w planie musi mieć evidence.

∀ claim ∈ Claims(P):

NonTrivial(claim) => ∃ E(claim)

Tagging:

CONFIRMED(claim) => Verified(E(claim))
ASSUMED(claim) => not Verified(E(claim))
UNKNOWN(claim) => not Decidable(claim)

6. UNKNOWN stop rule

Jeżeli istnieje element UNKNOWN, plan nie może przejść dalej.

U ≠ empty => STOP

Formalnie:

U ≠ empty => G_8 = false

oraz:

G_8 = true iff U = empty

Znaczenie:

UNKNOWN blokuje przejście do Kroku 9 i dalej
7. Approval gate

Implementacja jest zablokowana do momentu approval.

Impl allowed iff Approve = true

równoważnie:

Approve = false => Impl = blocked

To jest centralny gate procesu.

8. Prediction consistency

Przewidywania z Kroku 1 muszą być porównane z obserwacją.

Accuracy_files = |Pred_files ∩ Obs_files| / |Pred_files|

Accuracy_modules = |Pred_modules ∩ Obs_modules| / |Pred_modules|

Accuracy_modify = Actual_modified_files / Predicted_modified_files

Jeżeli różnica jest zbyt duża:

|Actual_modified_files - Predicted_modified_files| / Predicted_modified_files > 0.5
=> Explanation required

9. Read-before-plan constraint

Każdy plik użyty później jako podstawa claimu powinien być wcześniej przeczytany albo jawnie oznaczony jako nieprzeczytany.

∀ f ∈ ReferencedFiles(P):

Read(f)
or
DeclaredNotRead(f)

Mocniejsza wersja:

ClaimAbout(f) => Read(f) or ASSUMED(claim)

10. Impact completeness

Plan jest poprawny tylko wtedy, gdy wpływ zmiany obejmuje domknięcie po zależnościach.

Impact(Δ) = Closure(dependencies, consumers, side_effects, ordering)

Znaczenie:

nie tylko bezpośrednio zmieniane pliki
ale też consumery, typy, cache, pipeline, restore, frontend, ordering
11. Failure scenario completeness

Niech F oznacza wymagany zbiór scenariuszy błędu:

F = {
null_or_empty_input,
timeout_or_dependency_failure,
repeated_execution,
missing_permissions,
migration_or_old_data_shape,
frontend_not_updated,
rollback_or_restore,
monday_morning_user_state,
warsaw_missing_data
}

Plan jest kompletny tylko wtedy, gdy:

∀ f ∈ F:

Handled(f)
or
JustifiedNotApplicable(f)

12. Phase correctness

Każda faza musi mieć testowalny exit gate.

∀ Phase_j ∈ Plan:

∃ ExitGate_j

oraz:

Testable(ExitGate_j) = true

Niedopuszczalne:

ExitGate_j = "works"

Dopuszczalne:

ExitGate_j = "Endpoint X returns field Y for input Z"

13. Self-check honesty constraint

Plan musi ujawniać własne ograniczenia.

∃ NotVerified(P)

lub, jeśli brak:

ProofOfNoUnverified(P)

Znaczenie:

nie wolno twierdzić, że wszystko zostało zweryfikowane bez jawnego uzasadnienia
14. Causal cross-reference property

Każdy krok powinien odwoływać się do poprzednich.

∀ i > 1:

A_i depends_on (A_1 ... A_i-1)

Praktycznie:

Krok 6 odnosi się do Kroku 1 i 2
Krok 8 odnosi się do Kroku 2
Krok 9 odnosi się do Kroku 3, 5, 7, 8
Krok 10 odnosi się do 2, 5, 6, 9

To daje planowi własność śledzalności.

15. Twierdzenie główne
Theorem (Anti-Shortcut Planning Soundness)

A plan P is anti-shortcut sound if and only if all of the following hold:

Every mandatory step produces a non-empty artifact
Every step is either complete or explicitly skipped
Every non-trivial claim is evidence-backed and tagged
UNKNOWN claims block further progression
Implementation is blocked until approval
Impact analysis covers dependency closure
Failure scenarios are either handled or explicitly justified
Each phase has a testable exit gate
Predictions are cross-checked against observed reality
Shortcut cost is greater than execution cost

Formal compact form:

AntiShortcutSound(P) iff

∀ i ∈ [1..10]: A_i ≠ empty
∀ i ∈ [1..10]: Complete(S_i) or Skip_i
∀ claim ∈ Claims(P): NonTrivial(claim) => Tagged(claim) and ∃ E(claim)
U = empty before Step 9
Impl allowed iff Approve = true
Impact(Δ) = Closure(dependencies, consumers, side_effects, ordering)
∀ f ∈ FailureScenarios: Handled(f) or JustifiedNotApplicable(f)
∀ Phase_j: ∃ ExitGate_j and Testable(ExitGate_j)
CrossCheck(Pred, Obs) performed
∀ i: Cost(skip_i) > Cost(step_i)
16. Twierdzenie komplementarne
Theorem (Visible-Skip Completeness)

The planning process is shortcut-resistant if and only if omission is more observable than execution.

Formalnie:

∀ i ∈ [1..10]:

Visibility(Skip_i) > Visibility(step_i omission hidden)

oraz

Cost(skip_i) > Cost(step_i)

Znaczenie:

ukryte pominięcie jest niemożliwe lub droższe niż wykonanie pracy
pusty slot staje się widocznym dowodem braku pracy
17. Twierdzenie gate’ów
Theorem (Plan-to-Implementation Gate Discipline)

No implementation may begin unless the planning state is complete, uncertainty-free, and approved.

Formalnie:

Impl allowed iff

Complete(S_1 ... S_10)
U = empty
Approve = true

równoważnie:

Impl allowed iff
for all i in [1..10], G_i = true
and G_approve = true

18. Wersja ultra-krótka do wklejenia
Definitions:
R = request
P = plan
S1..S11 = plan steps
Ai = artifact of step i
Ei = evidence of step i
U = UNKNOWN
Approve = approval gate
Impl = implementation
Pred = predictions
Obs = observations

Artifact rule:
forall i in [1..10]:
    Ai != empty

Slot completeness:
Complete(Si) iff Filled_i = Slot_i
Filled_i != Slot_i => explicit Skip_i required

Shortcut economics:
forall i in [1..10]:
    Cost(skip_i) > Cost(step_i)

Evidence rule:
forall claim in Claims(P):
    NonTrivial(claim) => exists E(claim)

Tagging:
CONFIRMED(claim) => Verified(E(claim))
ASSUMED(claim) => not Verified(E(claim))
UNKNOWN(claim) => not Decidable(claim)

Unknown stop:
U != empty => STOP

Approval gate:
Impl allowed iff Approve = true

Impact completeness:
Impact(Delta) = Closure(dependencies, consumers, side_effects, ordering)

Failure scenarios:
forall f in FailureScenarios:
    Handled(f) or JustifiedNotApplicable(f)

Phase gate:
forall Phase_j:
    exists ExitGate_j
    Testable(ExitGate_j) = true

Prediction cross-check:
CrossCheck(Pred, Obs) required

Theorem:
AntiShortcutSound(P) iff
- every mandatory step has an artifact
- every non-trivial claim has evidence
- UNKNOWN blocks progression
- implementation waits for approval
- impact analysis is complete
- failure scenarios are handled
- every phase has a testable exit gate
- predictions are checked against reality
- skipping is more expensive than doing

---

## Empirical anchors ( 2026)

| Anchor | Theorem clause demonstrated |
|---|---|
| **2026-04-13 Settlement: 9-fix-pendulum, no PLAN** (`WORKFLOW.md §2.1`) | All clauses violated: no slot completeness, no prediction consistency, no failure scenarios planned. 9 commits in 1 day, fix A reverts to pre-A state. |
| **2026-04-22 Settlement: same area, with PLAN** (`PLAN_settlement_event_log_refactor.md`, `WORKFLOW.md §2.2`) | All clauses satisfied: 4 validation files first, then PLAN with §4 test scenarios + §5 invariants + §6 stages. 1-commit fix, no rollbacks. |
| **TD-20..25 ladder, 5 fixes 4 reverts, 5h** (`LESSONS_LEARNED.md` 2026-04-25) | Cost(skip planning) >> Cost(plan); §3 economic rule confirmed empirically. |
| **Credit-memo single-cycle CA W17, 24/24 PASS** (commit `b615063`, 2026-05-04) | Prediction consistency §8: prediction "fix X resolves 24 wash invoices" verified against reality (24/24 match). Accuracy = 1.0 > 0.5 threshold. |

## Status (per `AUDIT.md` 2026-05-05)

ACCEPT — canonical for planning gates. §17 plan-to-implementation gate aligns 1:1 with `CONTRACT.md §B.7` approval discipline. Slot completeness (§4) is mechanically checkable.
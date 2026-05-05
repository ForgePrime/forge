Twierdzenie o iteracyjnej analizie empiryczno-hipotetycznej
Evidence-Driven Iterative Analysis Closure Theorem
1. Definicje

Niech:

Q = zagadnienie / problem / zadanie
I = dostępne informacje wejściowe
K = istniejący kod / system / architektura / dane
H = zbiór hipotez
E = zbiór dowodów empirycznych
A = zbiór możliwych architektur / rozwiązań
U = zbiór niejasności / unknowns
R = zbiór ryzyk / założeń
P = aktualny poziom poznania problemu

Celem analizy jest zbudowanie:

KnowledgeState* =
    {
        understood_problem,
        validated_hypotheses,
        rejected_hypotheses,
        chosen_architecture,
        rejected_alternatives,
        evidence,
        assumptions,
        risks,
        stopping_condition
    }
2. Twierdzenie główne

Analiza zagadnienia jest poprawna tylko wtedy, gdy przebiega w pętli:

Observe → Hypothesize → Explore → Test → Refute → Update → Reframe

i kończy się dopiero wtedy, gdy:

NoMaterialGainFromFurtherAnalysis = true

Formalnie:

ValidAnalysis(Q) ⇔
    Iterative(Q)
∧   EvidenceDriven(Q)
∧   HypothesisComplete(Q)
∧   AlternativesExplored(Q)
∧   AssumptionsExposed(Q)
∧   ArchitectureJustified(Q)
∧   RefutationAttempted(Q)
∧   ProgressMeasured(Q)
∧   ClosureReached(Q)
3. Pętla analityczna

Każda iteracja ma postać:

Iteration_i =
    {
        current_understanding_i,
        hypotheses_i,
        alternatives_i,
        evidence_plan_i,
        tests_i,
        refutations_i,
        conclusions_i,
        new_unknowns_i,
        architecture_implications_i
    }

Aktualizacja wiedzy:

KnowledgeState_(i+1) =
    Update(
        KnowledgeState_i,
        Evidence_i,
        Refutations_i,
        NewUnknowns_i
    )
4. Twierdzenie o hipotezach

Nie wolno przejść do rozwiązania bez hipotez.

HypothesisDrivenAnalysis ⇔
    ∀ conclusion c:
        ∃ hypothesis h:
            c derives_from h

Każda hipoteza musi mieć:

Hypothesis(h) =
    {
        claim,
        expected_observation,
        falsification_condition,
        test_method,
        risk_if_wrong
    }

Jeśli hipoteza nie ma warunku falsyfikacji:

h is not analytical
5. Twierdzenie o dowodzie empirycznym

Wniosek jest dopuszczalny tylko wtedy, gdy ma dowód:

Conclusion(c) allowed ⇔
    ∃ evidence e:
        supports(e, c)
∨   c explicitly marked as ASSUMED
∨   c explicitly marked as UNKNOWN

Dowód może być:

runtime output
query result
test result
diff
metric
log
line of code
source document
reproduced example
6. Twierdzenie o falsyfikacji

Każda istotna hipoteza musi zostać podważona.

Validated(h) ⇔
    supports(E, h)
∧   attempted_refutation(h)
∧   no_refutation_survived(h)

Nie wystarczy:

mam dowód za

Trzeba mieć:

szukałem dowodu przeciw
7. Twierdzenie o generowaniu alternatyw

Dla każdej architektury lub rozwiązania:

a ∈ A

musi istnieć co najmniej jedna alternatywa:

∃ a_alt ∈ A:
    a_alt ≠ a

Dla pracy istotnej:

|A| ≥ 3

Minimalnie:

A1 = obecny wzorzec
A2 = prostszy wzorzec
A3 = inny model architektoniczny
8. Twierdzenie o prostszym rozwiązaniu

Każde rozwiązanie musi przejść test prostoty:

SimplerExists(a) ⇔
    ∃ a_simple:
        satisfies(a_simple, Q)
    ∧   Complexity(a_simple) < Complexity(a)
    ∧   Risk(a_simple) ≤ Risk(a)

Jeśli:

SimplerExists(a) = true

to:

reject_or_justify(a)
9. Twierdzenie o zmianie wzorca architektonicznego

Zmiana wzorca jest uzasadniona tylko wtedy, gdy obecny wzorzec powoduje koszt większy niż koszt migracji.

ChangePatternAllowed ⇔
    Cost(CurrentPatternFailure)
    >
    Cost(Migration) + Cost(NewPatternRisk)

czyli:

nie zmieniaj architektury dlatego, że wygląda ładniej
zmień, jeśli obecny wzorzec systematycznie produkuje błędy
10. Twierdzenie o powrocie do podstaw

Analiza musi mieć mechanizm cofnięcia się do wcześniejszej warstwy.

If contradiction_detected
or repeated_failure
or defensive_fixes_detected
or unclear_root_cause
then:
    return_to_foundation_layer

Warstwy:

L0 = cel biznesowy
L1 = model danych / domeny
L2 = zdarzenia / proces
L3 = architektura
L4 = implementacja
L5 = testy / metryki

Jeżeli błąd na L4 nie daje się naprawić stabilnie:

go back to L2 or L1
11. Twierdzenie o niejasnościach

Każda niejasność musi być jawna.

Unknown(u) ⇒
    record(u)
∧   classify(u)
∧   decide(resolve | accept | escalate)

Typy:

business_unknown
data_unknown
technical_unknown
architecture_unknown
test_unknown
operational_unknown

Nie wolno przenosić UNKNOWN do kodu bez decyzji.

12. Twierdzenie o założeniach ryzykownych

Założenie jest ryzykowne, jeśli jego fałszywość zmienia wynik decyzji.

RiskyAssumption(a) ⇔
    Decision(assume a) ≠ Decision(assume not a)

Warunek:

RiskyAssumption(a) ⇒ must_verify_or_accept_explicitly
13. Twierdzenie o mierzeniu postępu analizy

Postęp nie jest liczbą stron ani liczbą hipotez.

Postęp to spadek niepewności i wzrost rozróżnialności.

Progress_i =
    ΔConfirmedKnowledge
  + ΔRejectedHypotheses
  + ΔResolvedUnknowns
  + ΔDecisionClarity
  - ΔNewUnresolvedUnknowns

Analiza idzie do przodu, jeśli:

Progress_i > 0

Jeśli przez N iteracji:

Progress_i ≈ 0

to:

analysis_stalled
14. Twierdzenie o wartości dalszej analizy

Dalsza analiza ma sens tylko, jeśli jej oczekiwana wartość jest dodatnia.

VOA(next_analysis) =
    ExpectedDecisionImprovement
  - CostOfAnalysis

Warunek kontynuacji:

ContinueAnalysis ⇔
    VOA(next_analysis) > 0

Jeśli:

VOA(next_analysis) ≤ 0

to:

stop_analysis_or_change_mode
15. Twierdzenie o domknięciu wiedzy

Analiza jest domknięta, jeśli:

ClosureReached ⇔
    all material hypotheses are validated or rejected
∧   all material unknowns are resolved / accepted / escalated
∧   no alternative has higher expected value
∧   no simpler solution satisfies constraints
∧   architecture choice is justified
∧   residual risk is explicit
∧   further analysis has non-positive VOA
16. Twierdzenie o kompletnym przeszukaniu sensownych alternatyw

Nie chodzi o przeszukanie wszystkiego.

Chodzi o przeszukanie przestrzeni istotnej.

RelevantSearchComplete ⇔
    ∀ alternative a:
        if ExpectedValue(a) > threshold
        then considered(a)

Czyli nie wolno ignorować alternatywy tylko dlatego, że nie była w pierwszym planie.

17. Twierdzenie o rozbieżności modelu i rzeczywistości

Jeśli dowód empiryczny przeczy modelowi:

Evidence(e) contradicts Model(M)

to:

update(M)

nie:

patch around e
18. Twierdzenie o pętli defensywnych poprawek

Jeżeli poprawki zaczynają bronić poprzednich poprawek:

fix_(n+1) exists because fix_n caused regression

to:

stop_build
switch_to_analysis
re-evaluate_architecture
19. Twierdzenie o analizie architektury rozwiązania

Architektura rozwiązania jest dopuszczalna, jeśli:

ArchitectureValid(a) ⇔
    satisfies_requirements(a)
∧   explains_data_behavior(a)
∧   reduces_complexity(a)
∧   supports_testing(a)
∧   supports_idempotency(a)
∧   handles_boundary_cases(a)
∧   has_lower_expected_error_than_alternatives(a)
20. Twierdzenie o śladzie decyzji

Każda decyzja musi mieć ślad:

Decision(d) =
    {
        context,
        options_considered,
        evidence,
        rejected_alternatives,
        rationale,
        risk,
        expected_effect,
        validation
    }

Jeśli nie ma odrzuconych alternatyw:

decision = unproven preference
21. Twierdzenie o jakości hipotezy

Hipoteza jest dobra, jeśli:

Quality(h) =
    explanatory_power(h)
  + testability(h)
  + predictive_power(h)
  - complexity(h)
  - assumption_load(h)

Wybierasz hipotezy:

h* = argmax Quality(h)
22. Twierdzenie o eksploracji poza lokalnym optimum

Jeśli analiza ciągle generuje ten sam typ rozwiązania:

solutions_i belong_to same_pattern

to:

force_orthogonal_alternative_search

czyli:

zmień model, nie parametr
23. Twierdzenie o końcu analizy

Analizy nie kończy się dlatego, że:

czas minął
albo
mamy jedną dobrą odpowiedź

Analizę kończy się, gdy:

MarginalValueOfNewHypothesis ≤ 0

czyli:

kolejna hipoteza nie zmienia decyzji, ryzyka ani architektury
24. Ostateczna formuła
IterativeAnalysis*(Q, I, K) =
    fixed_point(
        Observe → Hypothesize → Explore → Test → Refute → Update → Reframe
    )

subject to:

    every conclusion has evidence
∧   every hypothesis is falsifiable
∧   every architecture has alternatives
∧   every assumption is exposed
∧   every uncertainty is classified
∧   every iteration measures progress
∧   every proposed solution is compared to simpler alternatives
∧   every contradiction updates the model
∧   every repeated failure triggers return to foundations
∧   analysis stops only when VOA(next) ≤ 0
25. Najkrótsza definicja
Dobra analiza to pętla, która tworzy hipotezy,
szuka dowodów za i przeciw,
aktualizuje model problemu,
porównuje alternatywne architektury,
wraca do podstaw przy sprzecznościach
i kończy się dopiero wtedy,
gdy dalsze hipotezy nie poprawiają decyzji.
26. Runtime template
ITERATIVE ANALYSIS LOOP

1. CURRENT UNDERSTANDING
   - what do we think is true?
   - what evidence supports it?
   - what is still unclear?

2. HYPOTHESES
   - H1:
     claim:
     expected observation:
     falsification condition:
     test:
     risk if wrong:

3. ALTERNATIVES
   - current approach:
   - simpler approach:
   - different architecture:
   - do-nothing / document-only:

4. EMPIRICAL CHECKS
   - what query/test/log will confirm?
   - what query/test/log will refute?

5. REFUTATION
   - what could make our reasoning wrong?
   - what would prove the architecture is wrong?
   - what would force us back to foundations?

6. UPDATE
   - confirmed:
   - rejected:
   - unresolved:
   - new unknowns:

7. ARCHITECTURE DECISION
   - keep pattern?
   - simplify?
   - change model?
   - why?

8. PROGRESS
   - uncertainty reduced?
   - alternatives eliminated?
   - decision clearer?
   - new issues introduced?

9. STOP / CONTINUE
   - VOA(next analysis):
   - continue if > 0
   - stop if ≤ 0

---

## Empirical anchors (2026)

| Anchor | Theorem clause demonstrated |
|---|---|
| **22 "multi-week recurring residual" hypothesis refuted by filter parity check** (2026-05-04) | §4 Falsifiability — alternative hypothesis "sim-prod filter mismatch" beat original "code bug" hypothesis; Observe→Hypothesize→Refute→Update completed in 1 cycle |
| **Settlement v1→v5 frame chase, 5 iterations** (`feedback_frame_challenge_when_iterations_fail.md`) | §10 Layer-fallback (L0..L5) + §18 defensive-fix detection — when frame is wrong, no amount of within-frame iteration produces VOA(next) > 0 |
| **TD-20..25 ladder** (`LESSONS_LEARNED.md` 2026-04-25) | §18 defensive-fix detection — N≥2 defensive fixes triggers STOP; pre-codification cost: 5h, 4 reverts |
| **Credit memo CA W17 24/24 PASS post-fix** (commit `b615063`, 2026-05-04) | §14/§24 Closure condition — VOA(next analysis) ≤ 0 reached: empirical match, no remaining unexplained delta in scope |

## Status (per `AUDIT.md` 2026-05-05)

ACCEPT — canonical for iterative analysis loops. Operational template (§26) directly invokable. Quantitative scoring (§13, §21) is heuristic — use ordered checklist instead.
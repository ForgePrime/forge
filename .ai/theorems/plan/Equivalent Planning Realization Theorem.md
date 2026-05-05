Twierdzenie o ekwiwalentnej realizacji planu
Equivalent Planning Realization Theorem

albo po polsku:

Twierdzenie o ekwiwalentnym przekształceniu informacji i kodu w plan wykonawczy
1. Definicje

Niech:

I = informacje wejściowe

czyli:

I = requirements ∪ notes ∪ decisions ∪ constraints ∪ assumptions ∪ goals

Niech:

K = istniejący kod / repozytorium / aktualny stan systemu

Niech:

P = plan wykonawczy

Niech transformacja planująca będzie funkcją:

Planify(I, K) = P

Plan jest poprawny wtedy, gdy zachowuje pełną informację potrzebną do wykonania zmiany:

InformationEquivalent(I, K, P) = true
2. Twierdzenie główne

Plan P jest poprawnym planem wykonawczym wtedy i tylko wtedy, gdy:

P = Planify(I, K)

oraz:

∀ e ∈ Essential(I ∪ K) :
    ∃ p ∈ P :
        trace(e, p)

oraz:

Reconstruct(P) ≈ Essential(I ∪ K)

oraz:

Execute(P, K) = K'

gdzie:

K' spełnia wszystkie wymagania wynikające z I
3. Najważniejsza postać twierdzenia
GoodPlan(P) ⇔
    Complete(P, I, K)
∧   Consistent(P)
∧   Traceable(P, I, K)
∧   Executable(P, K)
∧   Idempotent(P)
∧   Differentiable(P)
∧   Reconstructable(P)
∧   Verifiable(P)
4. Ekwiwalencja informacyjna planu

Plan nie może być streszczeniem. Plan musi być ekwiwalentem wykonawczym.

P ≡_exec (I, K)

czyli:

P zawiera dokładnie tyle informacji,
ile potrzeba do poprawnego wykonania zmiany,
bez utraty semantyki wejścia i bez zgadywania.

Formalnie:

∀ q ∈ QuestionsNeededForExecution :
    answer(q, P) = answer(q, I ∪ K)

Jeśli plan nie potrafi odpowiedzieć na pytanie potrzebne do wykonania, to:

P is incomplete
5. Twierdzenie o kompletności planu
Complete(P, I, K) ⇔
    ∀ required_change c :
        ∃ step s ∈ P :
            implements(s, c)

oraz:

∀ affected_area a ∈ ImpactClosure(I, K) :
    ∃ step s ∈ P :
        touches_or_validates(s, a)

Czyli plan musi pokrywać nie tylko żądanie, ale też pełny obszar wpływu.

6. Twierdzenie o zachowaniu semantyki
SemanticPreserving(Planify) ⇔
    meaning(I ∪ K) = meaning(P)

W praktyce:

business intent nie może zostać zamieniony w techniczny skrót,
który zmienia sens wymagania.

Przykład:

"manual override dominates automatic rule"

nie może w planie stać się tylko:

"add override flag"

bo to traci semantykę dominacji, kolejności i konfliktu reguł.

7. Twierdzenie o śledzalności
Traceable(P, I, K) ⇔
    ∀ step s ∈ P :
        ∃ source e ∈ I ∪ K :
            trace(s, e)

oraz odwrotnie:

∀ e ∈ Essential(I ∪ K) :
    ∃ step s ∈ P :
        trace(e, s)

Czyli traceability działa w obie strony:

source → plan
plan → source
8. Twierdzenie o odwracalności reprezentacyjnej

Plan powinien umożliwiać odtworzenie informacji wejściowych na poziomie wykonawczym:

Reconstruct(P) = Essential(I ∪ K)

Nie chodzi o odtworzenie każdego słowa, tylko każdego faktu, decyzji, ograniczenia i zależności potrzebnej do wykonania.

Loss(P) = 0 dla informacji krytycznej
9. Twierdzenie o idempotentności planu

Plan jest idempotentny, jeśli jego ponowne wykonanie nie powoduje dodatkowego niezamierzonego efektu:

Execute(P, Execute(P, K)) = Execute(P, K)

Czyli:

P(P(K)) = P(K)

Wymaga to:

upsert zamiast blind insert
guarded changes
existence checks
deterministic file updates
stable generated artifacts
repeatable tests
safe retries
10. Twierdzenie o różniczkowalności planu

Plan jest różniczkowalny, jeśli mała zmiana w informacjach lub kodzie powoduje małą, lokalną zmianę planu:

||ΔP|| ≤ L * ||Δ(I ∪ K)||

gdzie:

L = współczynnik wrażliwości planu

Jeśli małe wymaganie przebudowuje cały plan, to:

P is unstable

Dobry plan powinien być:

locally editable
modular
incremental
impact-bounded
11. Twierdzenie o domknięciu wpływu

Nie wystarczy zaplanować to, co użytkownik powiedział wprost.

Trzeba zaplanować też skutki.

ImpactClosure(I, K) =
    DirectImpact
  ∪ IndirectImpact
  ∪ TestImpact
  ∪ DataImpact
  ∪ APIImpact
  ∪ UXImpact
  ∪ SecurityImpact
  ∪ OperationalImpact

Plan jest poprawny tylko jeśli:

∀ impact ∈ ImpactClosure(I, K) :
    covered(impact, P)
12. Twierdzenie o braku sprzeczności
Consistent(P) ⇔
    ¬∃ s_i, s_j ∈ P :
        contradicts(s_i, s_j)

oraz:

¬∃ e_i, e_j ∈ I ∪ K :
    unresolved_contradiction(e_i, e_j)

Jeśli sprzeczność istnieje i nie jest rozwiązana, plan nie może być wykonawczy.

13. Twierdzenie o minimalnej wystarczalności planu

Dobry plan nie powinien być ani za mały, ani za duży.

P* = argmin Complexity(P)

pod warunkiem:

Complete(P, I, K) = true
Traceable(P, I, K) = true
Executable(P, K) = true
Verifiable(P) = true

Czyli:

minimum planu,
które nadal zachowuje pełną zdolność wykonania.
14. Twierdzenie o wykonywalności

Plan jest wykonywalny, jeśli każdy krok ma jawne wejście, wyjście i warunek zakończenia.

Executable(P) ⇔
    ∀ step s ∈ P :
        has_input(s)
    ∧   has_output(s)
    ∧   has_precondition(s)
    ∧   has_exit_test(s)

Minimalna forma kroku:

step = {
    goal,
    input,
    action,
    output,
    affected_files,
    validation,
    rollback_or_recovery
}
15. Twierdzenie o walidowalności
Verifiable(P) ⇔
    ∀ claim c ∈ P :
        ∃ validation v :
            validates(v, c)

Walidacja może być:

test
invariant
static analysis
schema check
golden dataset comparison
manual approval
runtime metric
16. Twierdzenie o zachowaniu topologii kodu

Plan nie może naruszać struktury istniejącego systemu bez jawnej decyzji.

TopologyPreserving(P, K) ⇔
    architecture_graph(K') is compatible with architecture_graph(K)

chyba że:

explicit_refactor_decision = true

Czyli:

zmiana lokalna nie może przypadkiem zmienić architektury globalnej.
17. Twierdzenie o wyborze ścieżki wykonania

Jeśli istnieje wiele planów:

P1, P2, ..., Pn

wybieramy:

P* = argmin ScoreCost(P)

gdzie:

ScoreCost(P) =
    implementation_cost
  + risk
  + complexity
  + regression_risk
  + cognitive_load
  + operational_cost

pod warunkiem:

Complete(P) = true
Verifiable(P) = true
Idempotent(P) = true
18. Twierdzenie o niedegradujących alternatywach

Alternatywa planu jest dopuszczalna, jeśli:

P_alt acceptable ⇔
    Complete(P_alt) = true
∧   Risk(P_alt) ≤ Risk(P_base) + ε
∧   Complexity(P_alt) ≤ Complexity(P_base) + ε
∧   Quality(P_alt) ≥ Quality(P_base)

Czyli planowanie powinno generować alternatywy, ale tylko takie, które nie degradują systemu.

19. Twierdzenie o kanonicznej postaci planu

Każdy plan powinien mieć stałą strukturę:

Plan =
    Intent
  + KnownFacts
  + ExistingState
  + Constraints
  + Assumptions
  + ImpactClosure
  + DecisionOptions
  + ChosenPath
  + Steps
  + ExitTests
  + Risks
  + Recovery
  + Traceability

Bez tej struktury plan jest trudny do wykonania i trudny do audytu.

20. Twierdzenie o zachowaniu informacji krytycznej
CriticalInfo(I ∪ K) ⊆ Information(P)

oraz:

LostCriticalInfo(P) = ∅

To jest rdzeń Twojej idei:

suma informacji z treści i kodu
musi zostać zachowana jako plan wykonawczy.
21. Twierdzenie o równoważności wykonawczej
P ≡_exec (I, K)

jeśli:

Execute(P, K)

prowadzi do takiego samego efektu, jaki wynikałby z pełnego, poprawnego rozumienia:

I ∪ K

czyli:

Effect(Execute(P, K)) = IntendedEffect(I, K)
22. Twierdzenie o zamknięciu cyklu planowania

Proces planowania musi być cyklem zamkniętym:

I ∪ K
    → Planify
    → P
    → Execute
    → K'
    → Validate
    → Evidence
    → UpdatePlanOrAccept

Warunek:

∀ failure f :
    ∃ repair_path(f)
23. Ostateczna formuła
Planify*(I, K) =
    argmin_P Complexity(P)

subject to:
    Complete(P, I, K)
∧   Consistent(P)
∧   Traceable(P, I, K)
∧   SemanticPreserving(P)
∧   Reconstructable(P)
∧   Executable(P, K)
∧   Idempotent(P)
∧   Differentiable(P)
∧   ImpactClosed(P, I, K)
∧   Verifiable(P)
∧   TopologyPreserving(P, K)
24. Najkrótsza definicja
Dobry plan to odwracalna, śledzalna i wykonywalna reprezentacja
sumy informacji wejściowych oraz istniejącego kodu,
która zachowuje semantykę, domyka wpływ zmian,
minimalizuje złożoność wykonania,
jest idempotentna przy ponownym uruchomieniu
i różniczkowalna względem małych zmian wymagań lub kodu.
25. Test poprawności planu dla Forge

Plan jest akceptowalny tylko jeśli przejdzie pytania:

1. Czy każde wymaganie ma krok wykonawczy?
2. Czy każdy krok ma źródło w informacji albo kodzie?
3. Czy plan pokrywa istniejący stan kodu?
4. Czy plan pokrywa impact closure?
5. Czy plan nie zgubił informacji krytycznej?
6. Czy plan da się wykonać bez dopowiadania?
7. Czy plan da się wykonać ponownie bez skutków ubocznych?
8. Czy mała zmiana wejścia zmienia tylko lokalny fragment planu?
9. Czy każdy krok ma exit test?
10. Czy z planu da się odtworzyć, dlaczego powstał?
11. Czy plan zachowuje topologię istniejącego systemu?
12. Czy plan wskazuje alternatywy i uzasadnia wybraną ścieżkę?
13. Czy każdy błąd ma recovery path?
14. Czy wynik wykonania planu spełnia intencję wejściową?
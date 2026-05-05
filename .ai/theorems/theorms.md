# MATHEMATICAL REFERENCE CATALOG (NOT a theorem file)

> **Status (per `AUDIT.md` 2026-05-05): MATH REFERENCE CATALOG — not authoritative.**
>
> This file is a catalog of textbook mathematical results (gradient descent, Bayes, Dijkstra, Banach fixed point, Pareto, etc.), not domain-specific theorems for  work. It contains 55 generic "Twierdzenie o X" entries grouped into two unrelated batches (lines 1+ and ~266+).
>
> **DO NOT cite as authority** in PR descriptions, plans, audits, or memory. For:
> - Decision validity → cite `decide/Evidence_Only_Decision_Model.md` (canonical)
> - Answer-quality / AUP → cite `Anti-Defect Answer Projection Theorem.md` (canonical for AUP, despite NEEDS-WORK status)
> - Iterative analysis → cite `analysis/Evidence-Driven Iterative Analysis Closure Theorem.md` (canonical)
> - Other theorem topics → see `CANONICAL.md`
>
> **Filename**: `theorms.md` (typo of "theorems") preserved for backwards compatibility with `CONTRACT.md §C` cross-reference pending update. Do not rename without coordinated cross-reference fix.
>
> **Use as**: study reference for mathematical concepts only. Translate-to-English work is T2-deferred (this file is non-canonical, low priority).

---

## Catalog (preserved verbatim — historical, in Polish)

1. Twierdzenie o funkcji celu w przestrzeni rozwiązań

Niech:

X = przestrzeń rozwiązań
f(x) = funkcja celu (koszt / jakość / ryzyko)

Optimum:

x* = argmin_{x ∈ X} f(x)

Warunek stacjonarności (różniczka):

∇f(x*) = 0

Użycie:

każde rozwiązanie musi mieć jawnie zdefiniowaną funkcję celu
brak f(x) ⇒ brak racjonalnego wyboru
2. Twierdzenie o stabilności rozwiązania (warunek drugiego rzędu)
∇f(x*) = 0  ∧  H(x*) > 0  ⇒  x* = minimum lokalne

gdzie:

H(x) = macierz Hessego

Użycie:

rozwiązanie nie może być tylko „najlepsze lokalnie”, ale stabilne
płaskie minima ⇒ niestabilne decyzje
3. Twierdzenie o Lipschitzu (kontrola wrażliwości)
||f(x1) - f(x2)|| ≤ L * ||x1 - x2||

Interpretacja:
mała zmiana wejścia ⇒ ograniczona zmiana wyniku

Użycie:

system powinien być odporny na małe zmiany wymagań
wysoka wrażliwość ⇒ niestabilna architektura
4. Twierdzenie o wypukłości (convexity)
f(λx + (1-λ)y) ≤ λf(x) + (1-λ)f(y)

dla:

λ ∈ [0,1]

Implikacja:

convex f ⇒ każde minimum lokalne = globalne

Użycie:

projektuj przestrzeń decyzji tak, żeby była „quasi-wypukła”
unikasz pułapek lokalnych optimum
5. Twierdzenie o dominacji (Pareto)
x1 ≼ x2 ⇔ ∀ i : f_i(x1) ≤ f_i(x2)

Jeśli:

x1 ≼ x2 ∧ ∃ j : f_j(x1) < f_j(x2)

to:

x2 eliminujemy

Użycie:

redukcja przestrzeni rozwiązań
unikanie over-analysis
6. Twierdzenie o projekcji na zbiór dopuszczalny

Niech:

C = zbiór constraintów

Rozwiązanie:

x* = argmin_{x ∈ C} f(x)

Jeśli rozwiązanie wychodzi poza C:

x' = Proj_C(x)

Użycie:

każdy pomysł musi być „rzutowany” na realne constraints
eliminuje nierealne decyzje
7. Twierdzenie o minimalizacji błędu (least squares)
min Σ (y_i - f(x_i))^2

Gradient:

∇ = 2 Σ (f(x_i) - y_i)

Użycie:

dopasowanie modelu decyzji do rzeczywistości
kalibracja heurystyk
8. Twierdzenie o propagacji błędu
Var(f(x)) ≈ (∂f/∂x)^2 * Var(x)

dla wielu zmiennych:

Var(f) = J * Cov(x) * J^T

gdzie:

J = Jacobian

Użycie:

identyfikacja najbardziej wrażliwych miejsc
tam trzeba dodać walidację
9. Twierdzenie o informacji (entropia)
H(X) = - Σ p(x) log p(x)

Użycie:

wysoka entropia ⇒ niepewność ⇒ trzeba więcej danych
niska entropia ⇒ stabilna decyzja
10. Twierdzenie Bayesa (aktualizacja przekonań)
P(H|D) = P(D|H) * P(H) / P(D)

Użycie:

każda decyzja powinna aktualizować przekonania
przeciwdziała biasom typu:
anchoring
confirmation bias
11. Twierdzenie o minimalnej długości opisu (MDL)
L(model) + L(data | model) = minimum

Użycie:

balans:
zbyt prosty model ⇒ niedopasowanie
zbyt złożony ⇒ overfitting
12. Twierdzenie o stałym punkcie (fixed point)
f(x) = x

Iteracja:

x_{n+1} = f(x_n)

zbiega jeśli:

|f'(x)| < 1

Użycie:

iteracyjne ulepszanie planów
convergence guarantee
13. Twierdzenie o gradient descent
x_{n+1} = x_n - α ∇f(x_n)

Użycie:

iteracyjne ulepszanie decyzji
małe kroki ⇒ stabilność
14. Twierdzenie o całce jako sumie efektów
∫ f(x) dx ≈ Σ f(x_i) Δx

Użycie:

globalny efekt = suma lokalnych decyzji
optymalizuj mikro → poprawiasz makro
15. Twierdzenie o ciągłości
lim_{x→a} f(x) = f(a)

Użycie:

brak skoków w UX / architekturze
zmiana musi być płynna
16. Twierdzenie o topologicznej spójności

Graf:

G = (V, E)

Spójność:

∀ v_i, v_j ∈ V : ∃ path(v_i, v_j)

Użycie:

każdy element systemu musi być osiągalny
brak „martwych” komponentów
17. Twierdzenie o domknięciu (closure)
∀ x ∈ X : f(x) ∈ X

Użycie:

każda operacja systemu musi prowadzić do poprawnego stanu
brak „undefined state”
18. Twierdzenie o kontrakcji (Banach)
||f(x) - f(y)|| ≤ k ||x - y||,   k < 1

⇒ istnieje unikalny punkt stały

Użycie:

gwarancja zbieżności systemu
brak oscylacji
19. Twierdzenie o minimalizacji energii (principle of least action)
S = ∫ L(x, x', t) dt
δS = 0

Użycie:

system wybiera „najbardziej ekonomiczną ścieżkę”
dokładnie to chcesz w UX i planowaniu
20. Twierdzenie o ograniczeniu poznawczym
CognitiveLoad ≤ Capacity

Model:

Load = Σ information_units + Σ decisions + Σ context_switch

Użycie:

bezpośrednio do UX
redukcja błędów poznawczych
21. Twierdzenie o minimalizacji błędu poznawczego
Error ≈ f(uncertainty, overload, bias)

Minimalizacja:

min Error ⇒
    reduce uncertainty
    reduce overload
    enforce structured reasoning
22. Twierdzenie o racjonalnej decyzji
Decision = argmax E[Utility(x)]

Użycie:

każda decyzja musi mieć:
wartość
prawdopodobieństwo
koszt
23. Twierdzenie o ograniczeniu przestrzeni
|X| = k^n

Redukcja:

X' ⊆ X

Użycie:

heurystyki, pruning, constraints
24. Twierdzenie o informacji wystarczającej
Information ≥ threshold ⇒ decision stable
Information < threshold ⇒ decision random-like
25. Najważniejsza synteza dla FORGE
OptimalSystem ⇔
    argmin_x Cost(x)
    ∧ stable(x)
    ∧ robust(x)
    ∧ low_entropy_decision
    ∧ bounded_error_propagation
    ∧ topologically_connected
    ∧ cognitively_feasible


1. Twierdzenie o eksplozji kombinatorycznej (problem źródłowy)
|X| = Π_i |D_i|

gdzie:

X = przestrzeń rozwiązań
D_i = decyzje

Implikacja:

|X| rośnie wykładniczo

Wniosek:

brute_force ⇒ niemożliwe
2. Twierdzenie o redukcji przestrzeni przez constraints

Niech:

X' = { x ∈ X : constraints(x) = true }

to:

|X'| << |X|

Użycie:

najpierw ogranicz przestrzeń, potem optymalizuj
3. Twierdzenie o dekompozycji problemu

Jeśli:

X = X1 × X2 × ... × Xn

i:

f(x) = f1(x1) + f2(x2) + ... + fn(xn)

to:

argmin f(x) = (argmin f1, argmin f2, ..., argmin fn)

Użycie:

rozbij problem na niezależne komponenty
eliminujesz złożoność wykładniczą
4. Twierdzenie Bellmana (dynamic programming)
V(x) = min_u [ cost(x,u) + V(f(x,u)) ]

Interpretacja:
optymalna decyzja = lokalna decyzja + optymalne dalsze decyzje

Użycie:

planowanie krok po kroku
eliminacja błędów „globalnego zgadywania”
5. Twierdzenie o grafie decyzji

Niech:

G = (S, A)

gdzie:

S = stany
A = akcje

Ścieżka:

P = (s0 → s1 → ... → sn)

Koszt:

Cost(P) = Σ cost(s_i, s_(i+1))

Optimum:

P* = argmin Cost(P)
6. Twierdzenie o najkrótszej ścieżce

Dijkstra (dla dodatnich wag):

d(s) = min Σ weights

Użycie:

wybór najtańszej ścieżki decyzji
UX flow / execution flow
7. Twierdzenie o A* (heurystyczne przeszukiwanie)
f(n) = g(n) + h(n)

gdzie:

g(n) = koszt dotychczasowy
h(n) = heurystyka

Warunek:

h(n) ≤ true_cost(n)

Implikacja:

gwarancja optymalności
8. Twierdzenie o branch and bound
if lower_bound(node) ≥ best_solution:
    prune(node)

Użycie:

agresywne cięcie przestrzeni
unikanie bezsensownych analiz
9. Twierdzenie o dominacji decyzji
x1 dominates x2 ⇔
    ∀ i : f_i(x1) ≤ f_i(x2)
    ∧ ∃ j : f_j(x1) < f_j(x2)

Implikacja:

x2 można usunąć z przestrzeni
10. Twierdzenie o minimalnym zbiorze decyzji

Nie wszystkie decyzje są niezależne:

|IndependentDecisions| << |AllDecisions|

Użycie:

najpierw znajdź minimalny zbiór decyzji
11. Twierdzenie o separacji decyzji (orthogonality)
Decisions independent ⇔
    ∂f/∂x_i does not depend on x_j

Użycie:

oddziel decyzje niezależne
redukujesz złożoność
12. Twierdzenie o pokryciu przestrzeni (set cover)

Problem:

min |S|
subject to:
    ⋃ S_i = universe

Użycie:

minimalny zestaw funkcji / testów / przypadków
eliminacja redundancji
13. Twierdzenie o hitting set (dual)
min H
such that:
    H ∩ S_i ≠ ∅ ∀ i

Użycie:

minimalny zestaw kontroli wykrywających błędy
14. Twierdzenie o maksymalnym przepływie
max_flow = min_cut

Użycie:

identyfikacja bottlenecków
gdzie ograniczyć przestrzeń
15. Twierdzenie o spójności grafu
∀ v_i, v_j ∈ V :
    ∃ path(v_i, v_j)

Użycie:

brak „martwych ścieżek”
UX i pipeline muszą być spójne
16. Twierdzenie o cyklach

Jeśli:

∃ cycle without progress

to:

system = stuck

Użycie:

wykrywanie pętli w procesie
retry bez progresu
17. Twierdzenie o minimalnym drzewie (MST)
min Σ weights(edges)

Użycie:

minimalna struktura połączeń
minimalny koszt architektury
18. Twierdzenie o NP-trudności (realność problemu)
optimal solution ∈ NP-hard

Implikacja:

use heuristics
19. Twierdzenie o heurystyce

Heurystyka dobra jeśli:

heuristic_error small

czyli:

|h(x) - true_cost(x)| minimal
20. Twierdzenie o eksploracji vs eksploatacji
maximize:
    E[reward] = exploration + exploitation

Użycie:

balans:
nowe rozwiązania
sprawdzone rozwiązania
21. Twierdzenie o rozkładzie problemu na przypadki
X = ⋃ disjoint_cases

Użycie:

rozbij problem na scenariusze
upraszcza decyzje
22. Twierdzenie o kanonicznej reprezentacji

Każdy problem powinien mieć formę:

state + action + transition + cost
23. Twierdzenie o minimalnej informacji do decyzji
Decision possible ⇔
    Information ≥ threshold
24. Twierdzenie o eliminacji symetrii

Jeśli:

x1 ≡ x2

to:

rozważ tylko jeden przypadek
25. Twierdzenie o porządku częściowym
(x ≤ y) ∧ (y ≤ z) ⇒ (x ≤ z)

Użycie:

budowa hierarchii decyzji
redukcja chaosu
26. Twierdzenie o lokalności decyzji
optimal decision depends on local state

Użycie:

nie analizuj wszystkiego globalnie
skup się na aktualnym stanie
27. Twierdzenie o minimalnej liczbie stanów
|States| minimal
subject to:
    correctness preserved
28. Twierdzenie o dekompozycji potrzeb

Niech:

Need = Σ atomic_needs

Warunek:

atomic_need = indecomposable

Użycie:

dekompozycja wymagań
eliminacja niejasności
29. Twierdzenie o mapowaniu potrzeb → decyzje
Need_i → Decision_j

warunek:

bijective mapping preferred
30. Synteza dla FORGE (najważniejsze)
OptimalDecisionSystem ⇔
    minimize(|X|)
    ∧ prune(dominated)
    ∧ decompose(problem)
    ∧ use_graph_search
    ∧ apply_constraints_first
    ∧ use_heuristics
    ∧ ensure connectivity
    ∧ eliminate cycles
    ∧ reduce decisions to minimal set
    ∧ map needs → decisions clearly
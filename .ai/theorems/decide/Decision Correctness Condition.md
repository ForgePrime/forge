# SUPERSEDED — preserved as exploration-operator catalogue

> **Status (per `AUDIT.md` 2026-05-05): SUPERSEDED.**
> **Canonical for decision validity**: `decide/Evidence_Only_Decision_Model.md` (E1–E8) — also mirrored in `CONTRACT.md §E`.
>
> /deep-verify (2026-05-05) found this file:
> - Mixed Polish/English (violates "All English" rule per memory `project_ai_dir_structure.md`)
> - All predicates undefined: `C(x)`, `F(x)`, `threshold`, `explainable`, `traceable`, `quality`, `improvement`, `heuristic`, `expected_improvement`, `distance`, `δ`, `ε`, `λ`, `budget`, `potential_gain`
> - Title vs content mismatch: titled "Decision Correctness Condition" but is actually a 19-section exploration-operator theorem about generating alternatives, not deciding
> - Internal contradiction: §3 Non-Degradation `F_i(x) ≤ F_i(x0) + ε` vs §7 `Score = λ·exploit + (1-λ)·explore` allowing degradation
> - No relationship declared with sister `Evidence_Only_Decision_Model.md`
> - No empirical anchor
>
> **Use only as**: §1 operator catalogue (refine / generalize / substitute / compose / decompose) — useful for thinking about alternative-generation moves. Do NOT cite the `DecisionCorrect(x)` predicate.
>
> **Action**: T1 (next 30 days) — either complete rewrite (translate, define predicates, reconcile §3 vs §7, bind to `Evidence_Only_Decision_Model.md`), or split into a standalone "Exploration Operator Catalogue" file under a new neutral name.

---

## Original content (preserved verbatim — historical)

Warunek poprawności decyzji (Decision Correctness Condition)

Każda alternatywa musi spełniać:

DecisionCorrect(x) ⇔
    C(x) = true
∧   F(x) ≼ threshold
∧   explainable(x) = true
∧   traceable(x) = true
1. Operator eksploracji (kluczowy mechanizm)

Alternatywy nie są losowe — powstają przez operatory transformacji:

N(x) = {
    refine(x),        // uszczegółowienie
    generalize(x),    // uogólnienie
    substitute(x),    // zamiana komponentu
    compose(x),       // połączenie z innym rozwiązaniem
    decompose(x),     // rozbicie na części
    reorder(x),       // zmiana kolejności procesu
    relax(x),         // poluzowanie constraintu
    constrain(x),     // dodanie constraintu
    parallelize(x),   // równoleglenie
    serialize(x)      // sekwencyjne uproszczenie
}
2. Twierdzenie o zachowaniu poprawności (Correctness Preservation)
If:
    x0 is valid
    ∧ transform T preserves constraints
Then:
    T(x0) is valid

Formalnie:

C(x0) = true ∧ preserves(T, C)
⇒ C(T(x0)) = true
3. Twierdzenie o niedegradacji (Non-Degradation)
x ∈ N(x0) is acceptable ⇔
    ∀ i : F_i(x) ≤ F_i(x0) + ε

gdzie:

ε = tolerancja (np. koszt może minimalnie wzrosnąć)
4. Twierdzenie o generowaniu nowości (Novelty Condition)

Nowe rozwiązanie musi wnosić informację:

Novel(x) ⇔
    distance(x, X_known) ≥ δ

czyli:

x nie jest kopią istniejącego rozwiązania
5. Twierdzenie o przestrzeni sąsiedztwa (Local Exploration)
N_k(x) = { rozwiązania w odległości ≤ k }

Eksploracja:

search space = ⋃ N_k(x0)

Implikacja:

najlepsze rozwiązania są często „blisko” obecnego
6. Twierdzenie o eksploracji kontrolowanej (Bounded Exploration)
|Explored| ≤ budget

oraz:

explore(x) tylko jeśli:
    potential_gain(x) ≥ threshold
7. Twierdzenie o równowadze eksploracja vs eksploatacja
Score(x) =
    λ * exploitation(x)
  + (1-λ) * exploration(x)

gdzie:

exploration(x) = novelty(x)
exploitation(x) = quality(x)
8. Twierdzenie o heurystycznym prowadzeniu eksploracji
choose next x:
    x = argmax heuristic(x)

warunek:

heuristic(x) ≈ expected_improvement(x)
9. Twierdzenie o dekompozycji idei

Niech:

x0 = {c1, c2, ..., cn}

Eksploracja:

modify only subset:
    x' = replace(ci)

czyli:

lokalne zmiany → nowe rozwiązania
10. Twierdzenie o rekombinacji (combinatorial innovation)
x_new = combine(x_a, x_b)

Jeśli:

components(x_a) ∩ components(x_b) ≠ ∅

to:

x_new często lepsze niż oba
11. Twierdzenie o dominacji (filtr)
remove x if:
    ∃ y : F(y) ≼ F(x)

czyli:

zostaw tylko Pareto frontier
12. Twierdzenie o uzasadnieniu alternatywy

Każde rozwiązanie musi mieć dowód:

Justified(x) ⇔
    ∃ argument ∧ ∃ evidence ∧ ∃ comparison
13. Twierdzenie o eksploracji bez utraty ciągłości
distance(x, x0) small ⇒
    system stability preserved

czyli:

nie rób skoków — rób iteracje
14. Twierdzenie o minimalnej zmianie (principle of least change)
argmin ||x - x0||
subject to:
    improvement(x)
15. Twierdzenie o eksploracji kierunkowej

Eksploracja powinna iść w kierunku gradientu:

x_next = x + direction

gdzie:

direction ≈ ∇ improvement
16. Twierdzenie o pokryciu przestrzeni
ExplorationComplete ⇔
    ∀ region R_i :
        visited(R_i)

praktycznie:

różne typy rozwiązań zostały sprawdzone
17. Twierdzenie o poprawności końcowej

Ostateczne rozwiązanie:

x* ∈ S

gdzie:

S = zbiór:
    valid
    non-degrading
    justified
    non-dominated
18. Synteza (najważniejsza forma)
Explore(x0) =
    generate N*(x0)
    filter:
        C(x) = true
        F(x) ≤ baseline
        Novel(x)
        Justified(x)
    remove dominated
    select best
19. Minimalna procedura dla FORGE
1. Define baseline x0
2. Define F(x) (co optymalizujesz)
3. Generate alternatives via operators
4. Filter by constraints
5. Remove dominated solutions
6. Keep only justified ones
7. Rank by score
8. Iterate locally (small changes)
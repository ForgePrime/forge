# Theorem (Unified Evidence-Grounded Development Soundness)

## 0. Definicje

```
Wejście:  D, G, C, DB, M
Wyjście:  Φ(D, G, C, DB, M) → (P, Δ, T, V, E_rt, M_next)

D   = dokumenty, źródła, materiały biznesowe
G   = cel biznesowy
C   = istniejący kod
DB  = istniejące dane, modele, schematy, tabele
M   = pamięć poprzednich incydentów, decyzji, odrzuconych założeń

K   = wyekstrahowana wiedza potwierdzona
A   = niejasności (ambiguities)
H   = ukryte założenia
U   = unknown blockers
F   = zbiór failure modes
DM  = model danych (entities, grain, contracts, nulls, ordering, ownership)

R   = wymagania (BR = biznesowe, TR = techniczne)
AC  = acceptance criteria
Spec = oczekiwane zachowanie systemu

Graph  = graf zależności: kod · dane · API · procesy · decyzje · testy
Impact = domknięcie przejściowe po Graph

E_static  = evidence ze źródeł, analizy, kodu
E_rt      = evidence z egzekucji: testy · query · log · diff · snapshot
E         = E_static ∪ E_rt

Inv    = business i technical invariants
Gate_i = deterministyczna brama etapu i
```

### Stan informacyjny

Każdy etap operuje na stanie informacyjnym:

```
S_i = (K_i, A_i, H_i, U_i, E_i, R_i, DM_i, F_i, Rel_i)
```

`Rel_i` jest **topologią informacji** — zbiorem relacji semantycznych między elementami:

```
source → fact
fact → requirement
assumption → risk
ambiguity → blocker
requirement → AC
requirement → test_obligation
decision → rationale
risk → mitigation
change → affected_invariant
claim → E_rt
```

Utrata `Rel_i` jest głównym źródłem globalnych błędów przy lokalnie poprawnych etapach.

### Pełny proces

```
Φ = f_D ∘ f_P ∘ f_A

z detektorem topologicznym D(S_i, S_{i+1}) na każdym przejściu
uruchamianym przed przyjęciem S_{i+1}
```

---

## 1. Detektor topologiczny — definicja ogólna

Detektor `D(S_i → S_{i+1})` mierzy pięć składników degradacji.

### D1. Utrata treści (Information Loss)

```
InfoLoss(i) = max(0, I(S_i) − I(S_{i+1}) − ε_i)

gdzie ε_i = uzasadniona, jawna kompresja

Dozwolone:   kompresja z zachowaniem source reference i decision relevance
Niedozwolone: ε_i niejawne lub niemożliwe do odtworzenia
```

### D2. Przesunięcie semantyczne (Semantic Shift)

```
SemShift(i) = |{x : Meaning_i(x) ≠ Meaning_{i+1}(x)
                    ∧ ¬ExplicitMappingRule(x)}|

Przykłady:
  "klient" w analizie = osoba fizyczna
  "klient" w planie   = konto w systemie
  → bez jawnej reguły mapowania: SemShift wykryty

  "walidacja" w wymaganiu = sprawdzenie formatu
  "walidacja" w kodzie    = zapis do audit logu
  → semantyczna nadbudowa bez uzasadnienia: SemShift wykryty
```

### D3. Zniszczenie relacji (Relation Destruction)

```
RelDestruction(i) = |{rel ∈ Rel_i : rel ∉ Rel_{i+1}
                           ∧ ¬ExplicitInvalidation(rel)}|

Chronione relacje (nie mogą zniknąć bez jawnego unieważnienia):
  source → fact
  fact → requirement
  requirement → AC
  requirement → test_obligation
  decision → rationale
  risk → mitigation
  change → affected_invariant
  assumption → dependent_requirement
```

### D4. Nadinterpretacja (Overinterpretation)

```
Overinterp(i) = |{x ∈ S_{i+1} : x ∉ closure(S_i)
                      ∧ ¬EvidenceForExpansion(x)}|

Przykłady:
  analiza mówi o module X
  plan planuje moduły X, Y, Z bez źródła rozszerzenia → nadinterpretacja

  wymaganie opisuje jeden przypadek
  implementacja obsługuje pięć bez zatwierdzonego rozszerzenia zakresu
```

### D5. Niedoszacowanie treści (Underspecification)

```
Underspec(i) = |{x ∈ S_i : x ∉ S_{i+1}
                     ∧ ¬ExplicitExclusion(x)}|

Przykłady:
  analiza wykryła 8 failure modes
  plan testuje 3 bez uzasadnienia pominięcia 5 → underspec

  wymaganie miało 4 acceptance criteria
  implementacja realizuje 2 bez jawnej decyzji o pominięciu
```

### Miara degradacji i reguła przejścia

```
Degradation(i) = InfoLoss(i) + SemShift(i) + RelDestruction(i)
               + Overinterp(i) + Underspec(i)

Reguła przejścia:

  if Degradation(i) = 0:
      Accept(S_{i+1})

  else if ∀ składnik: Justified(składnik) ∧ Bounded(składnik):
      Accept(S_{i+1}) with DegradationRecord(i)

  else:
      BLOCK
      return S_i with Diagnosis(i)
      STOP ∨ ESCALATE
```

---

## 2. Faza A — Analiza

```
S_0 → S_A = (K, A, H, U, F, DM_0, Rel_A)
```

### A1. Source completeness

```
∀ d ∈ D:
  Read(d) ∧ Classified(d) ∧ EvidenceExtracted(d)

Dla każdego d ∈ D:
  Used(d)
  ∨ Irrelevant(d) with reason
  ∨ Ambiguous(d) with question
  ∨ Conflicting(d) with conflict record

Żadne źródło nie może zniknąć milcząco.
```

### A2. Wykrywanie niejasności (Ambiguity Detection)

Niejasności dzielą się na trzy typy:

- **leksykalna** — jeden termin ma wiele znaczeń w różnych kontekstach
- **strukturalna** — relacja między elementami jest nieokreślona
- **zakresowa** — brak granicy tego, co jest w zakresie

```
∀ a ∈ A:
  Explicit(a)
  ∧ Question(a)
  ∧ Tag(a) ∈ {CONFIRMED, ASSUMED, UNKNOWN}
  ∧ (Resolved(a) ∨ RiskAccepted(a))

Unresolved(a) ∧ downstream(a) ⟹ BLOCK

Zakaz: niejasność nie może przejść do planu
jako milcząca interpretacja agenta.
```

### A3. Wykrywanie niespójności (Inconsistency Detection)

Niespójności mają trzy warstwy:

- **między źródłami** — dwa dokumenty twierdzą sprzeczne rzeczy
- **wewnątrz źródła** — sekcja 2 sprzeczna z sekcją 7 tego samego dokumentu
- **wymaganie vs istniejący kod/dane** — spec mówi X, system robi Y

```
∀ x, y ∈ Claims:
  Contradicts(x, y) ⟹ ConflictRecorded(x, y)

∀ conflict c:
  Resolved(c) ∨ STOP ∨ ESCALATE

UnresolvedConflict(c) ⟹ ¬ProceedToPlanning

Zakaz: agent nie może scalić sprzecznych źródeł
w płynną odpowiedź bez jawnego rozwiązania konfliktu.
```

### A4. Wyciąganie założeń wewnętrznych (Assumption Extraction)

Typy założeń:

- **AI-generated bridges** — agent wypełnił lukę w danych własnym prior-em
- **domain defaults** — "w tej branży zawsze tak się robi" bez weryfikacji
- **stability assumptions** — "ta tabela się nie zmieni" bez potwierdzenia

```
∀ h ∈ H:
  HiddenAssumption(h) ⟹
    Expose(h)
    ∧ ConvertToQuestion(h)
    ∧ AnalyzeRisk(h)

Tag(h) ∈ {CONFIRMED, ASSUMED, UNKNOWN}

CONFIRMED(h) ⟹ ∃ E(h) ∧ Verified(E(h))
ASSUMED(h)   ⟹ ¬Verified(E(h)) ∧ Explicit(h)
UNKNOWN(h)   ⟹ STOP ∨ ESCALATE

Zakaz: agent nie może kontynuować przy UNKNOWN
wypełniając lukę z prior-a statystycznego.
```

### A5. Wstępny model danych DM_0

```
DM_0 zawiera dla każdej encji:
  entities, grain, contracts, nulls,
  ordering, ownership, duplicates, refresh semantics

∀ entity e ∈ DM_0:
  Source(e) ∧ Target(e) ∧ Schema(e) ∧ Type(e)
  ∧ NullBehavior(e) ∧ DuplicateBehavior(e)
  ∧ OrderingBehavior(e) ∧ Ownership(e)
```

### A6. Topologia relacji Rel_A

```
Rel_A zawiera:
  source → fact
  fact → requirement
  assumption → risk
  ambiguity → blocker
  entity → contract
  conflict → resolution_status
```

### Gate_A

```
Gate_A = true iff:
  U = ∅
  ∧ ∀ conflict: Resolved ∨ Escalated
  ∧ ∀ a ∈ A: Tagged ∧ (Resolved ∨ RiskAccepted)
  ∧ ∀ h ∈ H: Exposed ∧ Tagged
  ∧ DM_0 complete
  ∧ Rel_A complete

Gate_A = false ⟹ Faza P zablokowana
```

### Detektor D(A→P)

```
D(A→P) weryfikuje:
  Rel_A ⊆ Rel_P (wszystkie relacje przejęte przez plan)
  ∧ DM_0 nie przekształcony bez jawnej reguły mapowania
  ∧ żadna ambiguity nie zniknęła bez rozwiązania
  ∧ żadne assumption nie zniknęło bez tagu

Degradation(A→P) = 0 ∨ BLOCK
```

---

## 3. Faza P — Plan

```
S_A → S_P = (R, AC, DM_1, Impact, x*, T_plan, Rel_P)
```

### P1. Completeness wymagań

```
∀ r ∈ R:
  Input(r) ∧ Output(r) ∧ Rule(r)
  ∧ AC(r) ∧ Test(r) ∧ Verification(r)
  ∧ EvidenceRequired(r)
  ∧ ∃ br ∈ BR: Trace(r → br)

Każde wymaganie techniczne ma uzasadnienie biznesowe.
Każdy element kodu ma wymaganie.
```

### P2. Impact closure

```
Impact(Δ) = Closure(Graph,
  direct deps + transitive deps + consumers
  + schemas + jobs + UI + tests + side effects
  + ordering assumptions + data contracts)

Niedopuszczalne: analiza impact tylko bezpośrednich zmian.
```

### P3. Selekcja rozwiązania

```
X_feasible = {x ∈ X : H1(x) ∧ H2(x) ∧ ... ∧ H7(x)}

Hard constraints (warunki konieczne feasibility):
  H1. BusinessTraceability: ∀ c ∈ C(x): ∃ br ∈ BR: Justifies(br, c)
  H2. Determinism: same input ∧ state ∧ config ⟹ same output
  H3. Consistency: ∀ s: Inv(s) ⟹ Inv(Apply(x, s))
  H4. SingleSourceOfTruth: ∀ f ∈ F: exactly one representation
  H5. ExplicitDependencies: ∀ d ∈ D(x): explicit ∧ justified
  H6. AntiOverengineering: ∀ c ∈ C(x): Removing(c) ⟹ violation
  H7. Completeness: ∀ r ∈ R: impl ∧ AC ∧ verification

x* = argmax Score(x) over X_feasible

Score(x) = BusinessFit + Determinism + Consistency
         + Traceability + Testability + Evolvability + Resilience
         − Complexity − Coupling − Duplication
         − TechnicalDebt − OperationalRisk − ExpectedFutureCost

ExpectedFutureCost(x) = Σ_{ω ∈ Ω} P(ω) · AdaptationCost(x, ω)
```

### P4. Failure mode completeness

```
∀ f ∈ F: Handled(f) ∨ JustifiedNotApplicable(f)

F zawiera co najmniej:
  null/empty input
  timeout lub dependency failure
  repeated execution
  missing permissions
  migration lub old data shape
  frontend not updated
  rollback/restore
  concurrent execution
  ordering violation
```

### P5. Model danych DM_1

```
DM_1 ⊇ refine(DM_0)

∀ zmiana DM_0 → DM_1:
  ExplicitMappingRule(zmiana) ∧ BusinessJustification(zmiana)

DM_1 zawiera dodatkowo:
  schema migrations (idempotentne)
  data contracts między komponentami
  invariants wynikające z wymagań
```

### P6. Topologia relacji Rel_P

```
Rel_P ⊇ Rel_A, rozszerzona o:
  requirement → AC
  requirement → test_obligation
  decision → rationale
  risk → mitigation
  change → affected_invariant
  assumption → dependent_requirement
  phase → exit_gate
```

### P7. Gate'y fazowe

```
∀ Phase_j ∈ P:
  ∃ ExitGate_j ∧ Testable(ExitGate_j)

ExitGate_j = "works" → niedopuszczalne
ExitGate_j = "Endpoint X zwraca pole Y dla wejścia Z" → dopuszczalne
```

### Gate_P

```
Gate_P = true iff:
  U = ∅
  ∧ Approve = true
  ∧ Impact(Δ) = Closure(Graph)
  ∧ ∀ r ∈ R: complete
  ∧ ∀ f ∈ F: Handled ∨ JustifiedNotApplicable
  ∧ DM_1 ⊇ DM_0 z jawnymi regułami mapowania
  ∧ Rel_P ⊇ Rel_A
  ∧ x* spełnia H1..H7

Gate_P = false ⟹ Faza D zablokowana
```

### Detektor D(P→D)

```
D(P→D) weryfikuje:
  Rel_P ⊆ Rel_D (wszystkie relacje przejęte przez development)
  ∧ DM_1 nie ulega semantic shift przy przejściu do implementacji
  ∧ Impact(Δ) nie zmniejszył się
  ∧ żaden failure mode nie zniknął
  ∧ każde AC jest traceable do wymagania

Degradation(P→D) = 0 ∨ BLOCK
```

---

## 4. Faza D — Development

```
S_P → S_D = (Δ, DM_impl, E_rt, Baseline, Post, Diff, Rel_D)
```

### D1. Runtime evidence

```
∀ claim o zachowaniu systemu:
  Accept(claim) ⟹ ∃ E_rt(claim)

E_rt ∈ {
  executed test output,
  SELECT query result,
  API response,
  job run output,
  log output,
  metric,
  snapshot,
  before-after diff
}

Kod nie jest dowodem.
Rozumowanie nie jest dowodem.
AI confidence nie jest dowodem.
```

### D2. Stepwise error detection

```
∀ failure f:
  ∃ sequence d_0 → d_1 → … → d_n
  gdzie:
    d_0 = earliest valid state
    d_n = first invalid state
    ∀ transition d_i → d_{i+1}: responsible transformation known

∃! h* ∈ H: Consistent(h*, data)
∀ h ≠ h*: ¬Consistent(h, data)

Root cause jest unikalny.
Wszystkie alternatywy są jawnie odrzucone.

∀ defect b:
  ∃ minimal reproducible example m(b): Reproduces(m(b), b)
```

### D3. Implementacja modelu danych i idempotencja

```
DM_impl = deploy(DM_1)

Idempotencja egzekucji:
  Apply(Δ, Apply(Δ, s)) = Apply(Δ, s)

Zachowanie niezmienników:
  ∀ s ∈ ValidStates: Inv(s) ⟹ Inv(Apply(Δ, s))

Dotyczy: migracji · ładowania danych · retry · sync ·
         rejestracji jobów · deploymentu · generowania raportów
```

### D4. Diff verification

```
Baseline = ObservedOutputs(before Δ)
Post     = ObservedOutputs(after Δ)
Diff     = Compare(Baseline, Post)

Warunek poprawności:
  Diff = ExpectedDiff
  ∧ UnexpectedDiff = ∅

System zmienia się dokładnie tak jak oczekiwano.
Nie mniej. Nie więcej.
```

### D5. Brak długu technicznego

```
Debt(Δ) = 0 within known required scope

Jeśli dług jest nieunikniony:
  ExplicitDebt
  ∧ BusinessAccepted
  ∧ RiskRecorded
  ∧ CompletionPlanExists

W przeciwnym razie: rozwiązanie nieważne.
```

### D6. Topologia relacji Rel_D

```
Rel_D ⊇ Rel_P, rozszerzona o:
  code → requirement
  test → AC
  fix → root_cause
  migration → invariant
  runtime_output → behavior_claim
```

### Gate_D

```
Gate_D = true iff:
  ∀ behavior claim: E_rt ≠ ∅
  ∧ Diff = ExpectedDiff
  ∧ UnexpectedDiff = ∅
  ∧ ∀ s: Inv(s) ⟹ Inv(Apply(Δ, s))
  ∧ Debt(Δ) = 0 ∨ ExplicitDebt with plan
  ∧ Rel_D ⊇ Rel_P
  ∧ ∃! h*: root cause unique and proven

Gate_D = false ⟹ output nieważny
```

### Detektor D(D→Verify)

```
D(D→Verify) weryfikuje ciągłość całego łańcucha:

  ∃ causal chain dla każdego artefaktu Z:
    D ∨ G ∨ C ∨ DB ∨ M
    → K → A/H/Q → R → AC → Spec
    → Impact → Δ → T → V → Z

  ∧ E_rt istnieje dla każdego behavior claim
  ∧ Rel_D ⊇ Rel_P ⊇ Rel_A (topologia kompletna end-to-end)
  ∧ żaden element planu nie jest "osieroconY" (bez causal origin)

Degradation(D→Verify) = 0 ∨ BLOCK
```

---

## 5. Learning loop

```
Po fazie D:

M_next = Update(M,
  E_rt,
  Diff,
  UnexpectedDiff,
  defects,
  rejected_assumptions,
  accepted_decisions,
  runtime_failures
)

Warunek jakości:
  ExpectedLoss(Φ_{n+1}) ≤ ExpectedLoss(Φ_n)

Gdzie loss obejmuje:
  bugs + regressions + requirement mismatch
  + wrong assumptions + rework
  + hidden dependencies + technical debt
  + runtime failures

Pamięć może wpływać na decyzje tylko traceably:
  MemoryInfluence(decision) ⟹ Trace(memory_item → learned_rule → decision)

Evidence overrides memory:
  Evidence contradicts MemoryRule ⟹ Evidence wins
```

---

## 6. Właściwości globalne procesu Φ

### Idempotencja planowania

```
Φ(D, G, C, DB, M) = Φ(D, G, C, DB, M)

Dozwolone różnice: formatting · timestamps · kolejność bez znaczenia semantycznego
Niedozwolone:      zmienione wymagania · zmieniony impact · zmieniona selekcja · zmienione testy
```

### Idempotencja egzekucji

```
Apply(Δ, Apply(Δ, s)) = Apply(Δ, s)
```

### Ciągłość

```
małe Change(D, G, C, DB, M) ⟹ bounded Change(P, Δ, T, V)

Małe wyjaśnienie nie może przebudować niezwiązanej architektury.
Lokalna zmiana wymagania wpływa tylko na swój subgraf zależności.
```

### Różniczkowalność

```
Change(x) affects DependentSubgraph(x)
unless GlobalDependency(x) is explicit

Impact zmiany jest przewidywalny i lokalizowalny.
```

### Monotoniczność topologiczna

```
Rel_D ⊇ Rel_P ⊇ Rel_A ⊇ Rel_0

Relacje semantyczne mogą tylko rosnąć lub być jawnie unieważniane.
Nigdy nie mogą znikać bez śladu.
```

### Ograniczona propagacja błędu

```
E_total ≤ Σ e_i · ρ_i

gdzie:
  e_i = lokalny błąd wprowadzony na etapie i
  ρ_i = centrality(node_i in Graph) × sensitivity(f_i)

ρ_i unbounded ⟹ STOP przed przejściem do następnego etapu
```

---

## 7. Twierdzenie główne — forma kompaktowa

```
Φ jest sound iff:

  SourceComplete(A)
∧ AmbiguitiesTagged(A)              ← leksykalne · strukturalne · zakresowe
∧ AssumptionsExposed(A)             ← AI bridges · domain defaults · stability
∧ ConflictsResolved(A)              ← inter-source · intra-source · req vs code
∧ DataModelInitialized(A)           ← DM_0: entities · grain · contracts · nulls
∧ D(A→P): Degradation = 0

∧ RequirementsComplete(P)           ← input · output · rule · AC · test · trace
∧ ImpactClosed(P)                   ← Closure(Graph) pełne
∧ SolutionOptimal(P)                ← x* = argmax Score over X_feasible
∧ FailureModesHandled(P)            ← ∀ f: handled ∨ justified N/A
∧ DataModelRefined(P)               ← DM_1 ⊇ DM_0 z jawnymi regułami
∧ D(P→D): Degradation = 0

∧ RuntimeEvidenceExists(D)          ← E_rt dla każdego behavior claim
∧ ErrorDetectionComplete(D)         ← ∃! h* · first invalid state · minimal repro
∧ DataModelDeployed(D)              ← DM_impl idempotent · Inv preserved
∧ DiffVerified(D)                   ← Diff = Expected · Unexpected = ∅
∧ NoTechnicalDebt(D)                ← Debt(Δ) = 0 ∨ explicit with plan
∧ D(D→Verify): Degradation = 0

∧ Rel_D ⊇ Rel_P ⊇ Rel_A            ← monotoniczność topologiczna end-to-end
∧ Idempotent(Φ)                     ← planning ∧ execution
∧ Continuous(Φ)                     ← małe ΔInput ⟹ bounded ΔOutput
∧ Differentiable(Φ)                 ← change(x) affects DependentSubgraph(x)
∧ LearningLoopClosed(M_next)        ← ExpectedLoss(n+1) ≤ ExpectedLoss(n)
```

---

## 8. Wnioski

### Wniosek 1 — Lokalny sukces nie implikuje globalnej poprawności

```
Failure(any Gate_i) ∨ Degradation(any D_i) > 0 (unjustified)
  ⟹ ¬Guarantee(Correctness(Φ))

Jeśli topologia informacji nie jest zachowana między etapami,
każdy etap może wyglądać sensownie, a wynik końcowy być błędny.
```

### Wniosek 2 — Prior substitution jest źródłem degradacji

```
MissingCriticalInfo(stage_i) ∧ ContinueByGuess(stage_i)
  ⟹ PriorSubstitution(i)
  ⟹ Degradation(j) > 0 for all j ≥ i

Agent statystyczny bez governed process nie może być sound.
Soundness pochodzi z procesu, nie z agenta.
```

### Wniosek 3 — Detektor jest konieczny, nie opcjonalny

```
∀ przejście S_i → S_{i+1}:
  ¬D(S_i, S_{i+1}) ⟹ ¬Guarantee(Soundness(Φ))

Detektor topologiczny nie jest quality check.
Jest warunkiem koniecznym przejścia między etapami.
```

### Wniosek 4 — Kompaktowa esencja

```
Φ produkuje poprawny output wtedy i tylko wtedy, gdy:

  każdy etap dodaje wiedzę epistемicznie
  każdy detektor przechodzi z Degradation = 0
  Rel rośnie monotonicznie przez wszystkie etapy
  E_rt istnieje dla każdego claim o zachowaniu
  root cause jest unikalny i udowodniony przez reprodukcję
```

---

*Theorem (Unified Evidence-Grounded Development Soundness)*  
*Φ(D, G, C, DB, M) → (P, Δ, T, V, E_rt, M_next)*  
*kompletne · idempotentne · topologicznie zachowujące · odporne na prior substitution*

---

## Empirical anchors ( 2026)

| Anchor | Detector that fires |
|---|---|
| **Settlement v1→v5 chasing CREST per-row when business needed only Δ=0** (`feedback_frame_challenge_when_iterations_fail.md`) | D5/Underspec — agent operated under stricter constraint than spec required; 5 iterations of dead chase before frame challenge |
| **22 "multi-week recurring residual" sim artifact** (`feedback_simulation_must_match_filters.md`, 2026-05-04) | D3/RelDestruction — relation `prod-filter ↔ row-set` destroyed in sim; D(P→D) gate would have caught: simulated evidence ≠ runtime evidence |
| **TD-20..25 ladder, 5 fixes 4 reverts** (`LESSONS_LEARNED.md` 2026-04-25) | D2 stepwise error: no unique root cause `h*` selected; multiple defensive fixes layered without convergence |
| **`project_reappeared_business_rule.md` memory drift** (memory said one thing, empirical refuted) | D4/Overinterp — closure operation took stale memory as fact; should have re-derived |

## Status (per `AUDIT.md` 2026-05-05)

ACCEPT — canonical for develop-phase soundness. Sister `develop/Forge Unified Development Theorem.md` is abstract counterpart (kept). 5 detectors (InfoLoss, SemShift, RelDestruction, Overinterp, Underspec) directly applicable as runtime checks.

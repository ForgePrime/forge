---
name: plan
description: >
  Anti-shortcut planning. Each step produces verifiable artifact that
  cross-references previous steps. Skip = SKIP BLOCK longer than the step.
  APPROVE gate blocks implementation. Greppable facts make lying expensive.
  Invoke for: plan, feature, implement, add, change, build, design.
user-invocable: true
disable-model-invocation: true
argument-hint: "[feature or change description]"
---

# /plan — Anti-Shortcut Planning

## Reguła ekonomii

Każdy krok produkuje slot. Slot pusty = visible skip.
Skip wymaga SKIP BLOCK który jest dłuższy niż wykonanie kroku.
**Skrót kosztuje więcej niż praca.**

Implementacja jest **ZABLOKOWANA** dopóki nie dostaniesz APPROVE.

## Kiedy /plan, /analyze, /grill?

- **`/grill`** — wymagania niejasne, wymuszenie disambiguation
- **`/analyze`** — masz dokumenty, wyciągnij CO i DLACZEGO
- **`/plan`** — wymagania jasne, zaprojektuj JAK i CO MOŻE SIĘ ZEPSUĆ

Flow: `/grill` → `/analyze` → `/plan` → APPROVE → `/develop`

---

## TASK

$ARGUMENTS

---

## KROK 1 — Pre-commitment (verbatim slots)

Wypełnij KAŻDY slot. Pusty slot = wracaj.

```
1.1 VERBATIM user request:
    "$ARGUMENTS"

1.2 Restate one sentence:
    "Potrzeba: ___ żeby ___ dla ___"

1.3 Pliki które PRZEWIDUJĘ że będę musiał czytać (minimum 3 LUB explicit "fewer because"):
    P1: ___
    P2: ___
    P3: ___

1.4 Modules I PREDICT will be affected:
    M1: ___
    M2: ___

1.5 BQ tables I PREDICT will be touched:
    T1: ___ (or "none — explain why")

1.6 Estimated number of phases: ___
1.7 Estimated number of files to modify: ___
```

Wyświetl te przewidywania. Krok 6 będzie je weryfikował.

---

## KROK 2 — Code reading (każdy plik osobno z DOWODEM)

Uruchom najpierw:

```!
git log --oneline -15
```

```!
ls -1 backend/app/modules/
```

Dla każdego pliku który czytasz, wyprodukuj slot:

```
FILE: <exact path>
LINES: <line count>
PREDICTED IN 1.3: [P1/P2/P3/NEW — not in prediction]
ONE SPECIFIC FACT FROM THIS FILE: <function name + line OR class + line — must be greppable>
RELEVANT BECAUSE: <one sentence>
```

Cross-check (mandatory slot):

```
2.X PREDICTION ACCURACY:
    Predicted in 1.3: [P1, P2, P3]
    Actually read: [list]
    Predicted but NOT read: [list + reason per file]
    Read but NOT predicted: [list + what I learned]
```

Jeśli pominąłeś plik z 1.3 → SKIP BLOCK 2:

```
SKIP BLOCK 2 (per pominięty plik):
- Dlaczego ten plik nie jest istotny po przeczytaniu innych: [3+ zdań]
- 3 rzeczy które mogą się zepsuć jeśli się mylę:
  R1: ___
  R2: ___
  R3: ___
- Jak user może zweryfikować że dobrze zdecydowałem:
  V1: ___
```

Czytanie pliku jest tańsze niż SKIP BLOCK 2.

---

## KROK 3 — Lista plików których zmiana dotknie (3 listy obowiązkowe)

```
3.1 PLIKI KTÓRYCH ZMIANA DOTKNIE BEZPOŚREDNIO:
    - <plik> — co konkretnie się zmieni: <jedno zdanie>
    (minimum 1 OR explicit "zero because")

3.2 PLIKI KTÓRYCH ZMIANA DOTKNIE POŚREDNIO (consumery, importy, typy):
    - <plik> — przez co: <jedno zdanie>
    (minimum 1 OR explicit "zero because")

3.3 PLIKI KTÓRE MOGŁYBY BYĆ DOTKNIĘTE A NIE BĘDĄ:
    - <plik> — dlaczego pomijam: <uzasadnienie>
    (minimum 1 — jeśli zero: "zero because" + 3+ zdań)
```

Lista 3.3 wymaga jednej pozycji. Jest to TWÓJ explicit dowód że pomyślałeś co MOGŁOBY być dotknięte i wybrałeś co nie.

---

## KROK 4 — Co się stanie dla każdego pliku z 3.1 i 3.2

Dla KAŻDEGO pliku z 3.1 i 3.2:

```
[plik]:
  Co robi teraz: <jedna konkretna rzecz, nie "obsługuje logikę">
  Co się zmieni: <jedna konkretna rzecz>
  Co może się zepsuć: <konkretny scenariusz LUB "nic — bo [uzasadnienie]">
  Kto tego używa (callerzy): <lista plików:linii LUB "nikt poza modułem — verified by grep">
```

Jeśli "co może się zepsuć" jest puste dla WSZYSTKICH plików → red flag. Wypisz dlaczego nic nie może się zepsuć (3+ zdań). Czytanie nawet jednego scenariusza jest tańsze.

---

## KROK 5 — ITRP impact z evidence (każdy obszar)

Każdy obszar musi mieć IMPACTED/NOT + grep evidence (nie samo "NOT IMPACTED").

```
5.1 Pipeline (data loading, gap check, buy gate)
    Status: IMPACTED / NOT IMPACTED
    Evidence: <grep result OR "no references found by: grep -rn '<keyword>' warsaw_data_pipeline/">

5.2 Buying (eligible invoices, credit limits, overrides)
    Status: IMPACTED / NOT IMPACTED
    Evidence: <grep result OR "no references found by: grep -rn '<keyword>' backend/app/modules/buying/">

5.3 Reporting (settlement, ITRP report, daily estimation)
    Status: IMPACTED / NOT IMPACTED
    Evidence: <grep result OR explanation>

5.4 Restore/Timeline (cascade restore, snapshots)
    Status: IMPACTED / NOT IMPACTED
    Evidence: <grep result OR explanation>

5.5 Override pattern (COALESCE, override table)
    Status: IMPACTED / NOT IMPACTED
    Evidence: <grep result OR explanation>

5.6 Frontend (cache invalidation, state management)
    Status: IMPACTED / NOT IMPACTED
    Evidence: <grep result OR explanation>
```

"NOT IMPACTED" bez evidence = visible skip. Wpisanie "NOT IMPACTED — verified by grep '<keyword>' returned 0 matches" jest tańsze niż SKIP BLOCK.

---

## KROK 6 — Cross-check przewidywań z Kroku 1

```
6.1 Pliki przewidziane w 1.3 vs faktycznie czytane w Kroku 2:
    Predicted: [from 1.3]
    Actually read: [from KROK 2]
    Match: <X of Y>

6.2 Modules przewidziane w 1.4 vs zidentyfikowane jako affected w Kroku 5:
    Predicted: [from 1.4]
    Actually affected: [from 5.X = IMPACTED]
    Difference: ___

6.3 Liczba phases przewidziana w 1.6 vs zaplanowana w Kroku 8:
    Predicted: <from 1.6>
    Actual: <from KROK 8>

6.4 Liczba plików do modyfikacji przewidziana w 1.7 vs faktyczna z 3.1:
    Predicted: <from 1.7>
    Actual: <count of 3.1>
    Difference > 50%: requires explanation
```

Złe predictions wymagają tłumaczenia. Dobre — nie. Dokładne czytanie Kroku 2 redukuje koszt.

---

## KROK 7 — Scenariusze co może pójść nie tak

Każdy scenariusz ma odpowiedź. Pusty = widoczne pominięcie.

```
[ ] Co gdy dane wejściowe są null/puste?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co gdy BQ/Firestore nie odpowie?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co gdy operacja wykona się dwa razy (idempotency)?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co gdy user nie ma uprawnień?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co gdy stare dane mają inną strukturę (migration)?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co gdy frontend nie jest jeszcze zaktualizowany?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co gdy zmiana zostanie odwrócona (restore)?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___

[ ] Co user zobaczy w poniedziałek rano po deploy?
    Obsłużone: TAK/NIE — opis: ___

[ ] Co gdy Warsaw nie dostarczy danych?
    Obsłużone: TAK/NIE — gdzie/co zrobię: ___
```

"Nie dotyczy" wymaga uzasadnienia DLACZEGO. Krótkie uzasadnienie jest tańsze niż wpisanie "TAK [gdzie]".

---

## KROK 8 — Założenia

```
CONFIRMED (sprawdzone w kodzie w Kroku 2):
| # | Fakt | Gdzie sprawdziłem (file:line) |
|---|------|-------------------------------|
| C1 | ___ | ___ |

ASSUMED (nie sprawdzone — kandydaci na pytania):
| # | Założenie | RYZYKO jeśli nieprawda | Sprawdzić w kodzie? |
|---|-----------|----------------------|---------------------|
| A1 | ___ | HIGH/MED/LOW | TAK [gdzie] / NIE — bo: |

UNKNOWN (blokują plan):
| # | Pytanie | Blokuje |
|---|---------|---------|
| Q1 | ___ | ___ |
```

Jeśli UNKNOWN nie jest pusta → **STOP. Zadaj pytania. Nie kontynuuj do Kroku 9.**

User override dla UNKNOWN: "A{N}: ASSUMED (USER OVERRIDE — originally UNKNOWN). Risk: ___"

---

## KROK 9 — Plan implementacji (Phase z exit gates)

```
Phase 1: <nazwa — co dostarcza>
  Zależy od: <nic / Phase N>
  Pliki do zmiany:
    - <plik> — konkretna zmiana (jedna linijka)
  Modele:
    - Storage: TypedDict w types.py
    - Domain: dataclass/Pydantic w models.py
    - API: Pydantic
  BQ schema changes: <NONE / ALTER TABLE ...>
  Deployment order: <→ /plan-deploy if schema before code>
  Exit gate (testowalne): <"Endpoint zwraca 200 z polem X" — NIE "działa">
  AC z Kroku poprzedniego: <które AC to spełnia>

Phase 2: ...
```

Każdy Phase ma exit gate. "Działa" nie jest exit gate. "Endpoint X zwraca pole Y dla input Z" jest.

---

## KROK 10 — Self-check (honesty)

```
[ ] Czy faktycznie OTWORZYŁEM (Read tool) pliki w Kroku 2 czy zgadywałem z pamięci?
    Otworzone: <count>
    Z pamięci: <count + lista — dlaczego nie otworzyłem>

[ ] Czy 5.X grep'y faktycznie uruchomiłem czy je wymyśliłem?
    Faktycznie uruchomione: <count>
    Wymyślone: <count + dlaczego>

[ ] Czy lista 3.1 jest zgodna z plikami czytanymi w Kroku 2?

[ ] Czy każdy Phase z Kroku 9 ma jasny exit gate który jest testowalny?

[ ] Czy zatrzymałem się przy UNKNOWN?

[ ] Czy 6.4 prediction accuracy była dobra (różnica < 50%)?

Najtrudniejsza część tego planu: ___
Największe ryzyko: ___
Czego NIE zweryfikowałem mimo przejścia kroków: ___
```

"Nothing not verified" wymaga 5+ zdań uzasadnienia. Jedna prawdziwa rzecz — 1 zdanie.

---

## KROK 11 — Czekaj na APPROVE

Po pokazaniu Kroków 1-10 — **czekaj**.

Implementacja zaczyna się dopiero po `APPROVE` lub korekcie.

Zapisz plan do `.ai/PLAN_<feature_name>.md`.

---

## Anti-shortcut economics

| Shortcut | Cost | Cheap alternative |
|----------|------|-------------------|
| Pominąć Krok 2 (read code) | SKIP BLOCK 2 per plik | Read tool call |
| Sfałszować "ONE FACT FROM FILE" | Wymyślić nazwę funkcji + linia | grep | User wykryje |
| Sfałszować 5.X grep evidence | Wymyślić 0 results | Bash grep |
| Pominąć 3.3 (mogłyby ale nie) | "zero because" + 3 zdania | 1 plik z uzasadnieniem |
| Pominąć Krok 7 scenariusz | "nie dotyczy" + uzasadnienie | "TAK [gdzie]" |
| Pominąć 10 honesty | "nothing" + 5 zdań | 1 prawdziwa rzecz |
| Sfałszować 6.X prediction | Pamiętać żeby kłamać konsystentnie | Skopiować z 1.3 |
| Zignorować APPROVE | User przerywa, więcej tokenów rework | Czekać 1 wiadomość |

**Każdy slot ma kontrę.**

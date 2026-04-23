---
name: analyze
description: >
  Anti-shortcut requirements analysis. Each step produces verifiable artifact
  cross-referencing previous steps. Greppable facts. Hard STOP on UNKNOWN.
  Skip = SKIP BLOCK longer than the step. Output: PRD-style with C/A/U taxonomy.
  Invoke for: analyze requirements, review spec, meeting notes, gaps, ambiguities.
user-invocable: true
disable-model-invocation: true
argument-hint: "[document path, feature description, or paste of meeting notes]"
allowed-tools: Read, Glob, Grep, WebFetch
---

# /analyze — Anti-Shortcut Business Analysis

## Reguła ekonomii

Każdy krok produkuje slot. Slot pusty = visible skip.
Skip wymaga SKIP BLOCK który jest dłuższy niż wykonanie kroku.
**Skrót kosztuje więcej niż praca.**

## Nie uznawaj analizy za zakończoną dopóki:
- problem biznesowy nie jest w pełni zdefiniowany
- każda informacja trafiła do CONFIRMED / ASSUMED / UNKNOWN
- każdy UNKNOWN ma "blokuje"
- każdy fakt ma cytowane źródło

---

## TASK

$ARGUMENTS

---

## KROK 1 — Pre-commitment

Wypełnij KAŻDY slot. Pusty slot = wracaj.

```
1.1 VERBATIM input:
    "$ARGUMENTS"

1.2 Restate one sentence:
    "Pytanie biznesowe: ___ ponieważ ___"

1.3 Źródła które PRZEWIDUJĘ że muszę przeczytać (minimum 3):
    P1: ___
    P2: ___
    P3: ___

1.4 Liczba CONFIRMED facts którą przewiduję że znajdę: ___
1.5 Liczba UNKNOWNs którą przewiduję: ___
1.6 Estimated complexity: TRIVIAL / SIMPLE / MEDIUM / COMPLEX
```

Wyświetl. Krok 8 będzie weryfikował predictions.

---

## KROK 2 — Znajdź i przeczytaj WSZYSTKIE źródła

Najpierw uruchom (output dosłowny):

```!
ls .documentation/Meeting-notes/ 2>/dev/null
```

```!
ls .ai/SPEC-* .ai/PLAN_* .ai/ANALYSIS_* 2>/dev/null
```

```!
ls .documentation/REQ-* .documentation/VIS-* 2>/dev/null
```

Następnie przeczytaj każdy znaleziony plik. Nie streszczaj na podstawie nazwy.

**OUTPUT KROKU 2 — wymagany przed dalszym ruchem:**

```
ŹRÓDŁA ZNALEZIONE I PRZECZYTANE: [N]
| # | Plik | Co zawiera (1 zdanie) | Wiarygodność HIGH/MED/LOW | Czego NIE mówi | Cytowalna fraza z dokumentu |
|---|------|----------------------|---------------------------|----------------|----------------------------|
| 1 | ___ | ___                  | ___                       | ___            | "<dosłowny cytat>"          |

Cross-check vs 1.3:
- Predicted: [P1, P2, P3]
- Actually read: [list]
- Predicted but NOT read: [list + dlaczego per file]
- Read but NOT predicted: [list]

ŹRÓDŁA NIE ZNALEZIONE:
- <czego szukałem> — konsekwencja: <co to oznacza dla analizy>

ŹRÓDŁA KTÓRE SĄ ALE NIE PRZECZYTAŁEM:
- <plik> — dlaczego pomijam: <uzasadnienie>
```

"Cytowalna fraza" musi być greppable w dokumencie. User może to sprawdzić.

Jeśli pomijasz źródło → SKIP BLOCK 2:

```
SKIP BLOCK 2 (per pominięte źródło):
- Dlaczego nie istotne: [3+ zdań]
- 3 rzeczy które mogą być niezauważone:
  R1: ___
  R2: ___
  R3: ___
- Jak user może zweryfikować że dobra decyzja: ___
```

---

## KROK 3 — CONFIRMED / ASSUMED / UNKNOWN (każdy fakt z cytatem)

**Reguła faktu:** Fakt musi być na tyle konkretny żeby zweryfikować w kodzie lub dokumencie. "System przetwarza faktury" to NIE fakt — to parafraza. "Tabela `open_invoice_SE_002` filtruje `is_active = TRUE` w `repository.py:47`" to fakt.

```
CONFIRMED — jawnie powiedziane lub widoczne:
C1. <konkretny fakt> — źródło: <plik:linia LUB dokument:sekcja> — cytat: "<dosłowny>"
C2. ___
(minimum tyle ile ma sens dla tematu — < 5 to red flag, wytłumacz)

ASSUMED — wynika logicznie ale nie potwierdzone:
A1. <założenie> — dlaczego zakładam: <rozumowanie> — RYZYKO jeśli błędne: HIGH/MED/LOW + co się psuje
A2. ___

UNKNOWN — nie mogę wydedukować ze źródeł:
U1. <czego nie wiem> — blokuje: <co konkretnie nie może być zdecydowane>
U2. ___
```

**Jeśli UNKNOWN nie jest pusta → STOP.**

Wypisz użytkownikowi:
```
ANALIZA ZABLOKOWANA.
Nie mogę kontynuować bez odpowiedzi na:
U1: <pytanie> — blokuje: <co>
U2: ...
Odpowiedz na powyższe zanim przejdziemy dalej.
```

Nie kontynuuj do Kroku 4 dopóki UNKNOWN nie jest pusta.

---

## KROK 4 — Scenariusze (każdy ma odpowiedź)

Dla tematu z $ARGUMENTS przejdź przez KAŻDY scenariusz. Pusty slot = wracaj.

```
SCENARIUSZ: Happy path
  Obsłużony: TAK/NIE
  Gdzie zdefiniowany: <plik:linia / dokument:sekcja / "nigdzie — założenie">
  Co się stanie jeśli nie: <konkretna konsekwencja>

SCENARIUSZ: Dane null/puste
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: Duplikaty (operacja dwa razy)
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: Partial failure
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: Rollback / cofnięcie
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: Brak uprawnień / zły user
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: BQ/Firestore timeout
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: Stare dane / migration
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___

SCENARIUSZ: Loading state (co user widzi w toku)
  Obsłużony: TAK/NIE
  Gdzie: ___
  Co się stanie: ___
```

Każdy NIE z brakiem "gdzie" = luka → trafia do Kroku 7 jako pytanie.

---

## KROK 5 — Niespójności (active search)

**Instrukcja:** Weź KAŻDY CONFIRMED fact z Kroku 3 i zapytaj: "czy coś w innych źródłach temu zaprzecza?"

```
NIESPÓJNOŚCI ZNALEZIONE: [N]

NIESPÓJNOŚĆ #1:
  Źródło A: <plik:linia LUB dokument — dosłowny cytat>
  Źródło B: <plik:linia LUB dokument — dosłowny cytat>
  Konflikt: <konkretnie co jest sprzeczne>
  Konsekwencja jeśli nie rozwiążemy: <co się zepsuje>
  Rekomendacja: <co wybrać i dlaczego — miej opinię>

NIESPÓJNOŚCI NIE ZNALEZIONO: [TAK/NIE]
Jeśli TAK — wyjaśnienie: <dlaczego jestem pewien — które fakty porównałem, nie tylko "nie zauważyłem">
```

"Nie znaleziono" wymaga uzasadnienia (które fakty porównałeś). Jedna znaleziona niespójność jest tańsza do opisania niż uzasadnienie zero.

---

## KROK 6 — Wpływ na system (grep evidence)

```bash
grep -rn "{keyword_z_ARGUMENTS}" backend/app/modules/ --include="*.py" | grep -i "SELECT\|INSERT\|MERGE"
grep -rn "{keyword_z_ARGUMENTS}" frontend/src/ --include="*.tsx" -l
```

Dla każdego znalezionego pliku/modułu:

```
IMPACT: <moduł/plik>
  Co robi teraz: <jedna konkretna rzecz>
  Co się zmieni: <konkretna zmiana>
  Co może się zepsuć: <konkretny scenariusz LUB "nic — bo [uzasadnienie]">
  Ryzyko: HIGH/MED/LOW — dlaczego: <jedno zdanie>
```

Jeśli "co może się zepsuć" puste dla WSZYSTKICH → red flag, wymaga 3+ zdań wyjaśnienia.

---

## KROK 7 — Pytania i decyzje

Zbierz wszystko z poprzednich kroków:
- każdy UNKNOWN z Kroku 3
- każdy ASSUMED z HIGH ryzykiem z Kroku 3
- każdy NIE z Kroku 4 bez "gdzie"
- każda niespójność z Kroku 5

```
PYTANIA DO UŻYTKOWNIKA / KLIENTA:
Q1. <konkretne pytanie> — kontekst: <dlaczego pytam> — blokuje: <co nie może być zrobione>
Q2. ___

DECYZJE DO PODJĘCIA:
D1. <co trzeba zdecydować> — opcje: A/B/C — rekomendacja: <co wybieram i dlaczego>
D2. ___
```

Każde pytanie MUSI mieć "blokuje". Pytanie bez "blokuje" = ciekawostka, nie analiza.

---

## KROK 8 — Cross-check predictions

```
8.1 Źródła: predicted (1.3) vs actually read (Krok 2)
    Predicted: <count from 1.3>
    Read: <count from Krok 2>
    Difference: ___

8.2 CONFIRMED facts: predicted (1.4) vs actual (Krok 3)
    Predicted: <from 1.4>
    Actual: <count of C* in Krok 3>
    Difference > 50%: explain

8.3 UNKNOWNs: predicted (1.5) vs actual (Krok 3)
    Predicted: <from 1.5>
    Actual: <count of U* in Krok 3>
```

Złe predictions wymagają tłumaczenia. Bliskie — nie.

---

## KROK 9 — Self-check (honesty)

```
[ ] Czy faktycznie OTWORZYŁEM (Read tool) źródła w Kroku 2 czy zgadywałem z tytułów?
    Otworzone: <count>
    Z tytułu: <count + lista>

[ ] Czy każda "cytowalna fraza" w tabeli źródeł jest faktycznie w dokumencie?
    Sprawdziłem: <count> / <count> 
    Niepewne: <count + które>

[ ] Czy każdy CONFIRMED fact ma greppable źródło?
    Tak: <count> / <count>

[ ] Czy zatrzymałem się przy UNKNOWN?

[ ] Czy aktywnie szukałem niespójności (Krok 5) czy "nie zauważyłem"?

[ ] Czy każde pytanie w Kroku 7 ma "blokuje"?

Najtrudniejsza część analizy: ___
Największe ryzyko: ___
Czego NIE zweryfikowałem mimo przejścia wszystkich kroków: ___
```

"Nothing not verified" = 5+ zdań uzasadnienia. 1 prawdziwa rzecz = 1 zdanie.

---

## KROK 10 — Podsumowanie (PRD-style)

```
# Analiza: <temat>

## Status: KOMPLETNA / WYMAGA ODPOWIEDZI (Q1-QN) / ZABLOKOWANA (U1-UN)

## Problem Statement
<Problem z perspektywy użytkownika>

## Proposed Solution
<Rozwiązanie z perspektywy użytkownika>

## User Stories
1. As a <role>, I want <feature>, so that <benefit>
2. ...

## Confirmed (<N>)
<lista C1-CN z Kroku 3>

## Assumed (<N>, w tym <M> high-risk)
<lista A1-AN z Kroku 3>

## Unknown (<N>)
<lista U1-UN — jeśli nie pusta = ZABLOKOWANA>

## Niespójności (<N>)
<z Kroku 5 z rekomendacjami>

## Braki w pokryciu (<N> scenariuszy NIE)
<z Kroku 4 — tylko te z NIE>

## Decyzje do podjęcia (<N>)
<z Kroku 7 z rekomendacjami>

## Pytania (<N>)
<z Kroku 7 — pogrupowane, z "blokuje">

## Wpływ na system
<z Kroku 6>

## Out of Scope
<Co explicite NIE jest częścią — zapobiega scope creep>

## Gotowość do /plan
<GOTOWE — wszystkie unknowns resolved / NIE GOTOWE — wymaga Q1-QN>
```

Jeśli Status = WYMAGA ODPOWIEDZI → czekaj. Nie przechodź do /plan.

---

## Anti-shortcut economics

| Shortcut | Cost | Cheap alternative |
|----------|------|-------------------|
| Pominąć Krok 2 (read sources) | SKIP BLOCK 2 per źródło | Read tool call |
| Sfałszować "cytowalną frazę" | Wymyślić frazę | grep | User wykryje |
| Skip Krok 3 (C/A/U) | Visible empty slots | Wpisać każdy fakt z cytatem |
| Pominąć scenariusz w Kroku 4 | "nie dotyczy" + uzasadnienie | "TAK [gdzie]" |
| "Niespójności nie znaleziono" | 3+ zdania uzasadnienia | 1 znaleziona |
| Skip Krok 6 grep | Visible empty | Bash grep |
| 9 honesty "nothing" | 5+ zdań | 1 prawdziwa rzecz |
| Sfałszować 8.X predictions | Konsystentne kłamstwo | Skopiować z 1.X |
| Kontynuować z UNKNOWN | User wraca z gniewem | STOP i zapytaj |

---

## Czego NIE wolno

- Napisać "przeczytałem dokumenty" bez tabeli źródeł z Kroku 2
- Fakt bez źródła + cytatu
- Kontynuować do Kroku 4 gdy UNKNOWN z Kroku 3 nie jest pusta
- "Scenariusz nie dotyczy" bez DLACZEGO
- "Niespójności nie znaleziono" bez wyjaśnienia co porównałeś
- Pytanie bez "blokuje"
- Pominąć Krok 9 self-check
- Status: KOMPLETNA gdy są nierozwiązane UNKNOWN

---

## Integration

- **Output →** `/plan` (analiza kompletna → fazy implementacji)
- **Output →** `/deep-risk` (zidentyfikowane ryzyka → 5D scoring)
- **Output →** `/deep-explore` (zbyt wiele opcji → structured exploration)
- **Input ←** meeting notes, specs, user stories, Figma designs, existing code

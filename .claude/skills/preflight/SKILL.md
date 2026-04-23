---
name: preflight
description: >
  Anti-shortcut pre-commit gate. Each check requires file:line evidence
  (greppable). Skipping a check requires longer SKIP BLOCK than running it.
  Honesty self-check at end. Catches missing imports, logger out of scope,
  type mismatches, standards violations, same-bug-elsewhere.
disable-model-invocation: true
user-invocable: true
---

# /preflight — Anti-Shortcut Pre-commit Gate

## Reguła ekonomii

Każdy CHECK wymaga DOWODU (greppable file:line, output komendy, lub explicit "nie dotyczy + powód").
Nie możesz napisać "OK" bez pokazania CO sprawdziłeś.
Skip wymaga SKIP BLOCK który jest dłuższy niż uruchomienie checku.
**Skrót kosztuje więcej niż praca.**

---

## KROK 1 — Lista zmienionych plików (pre-commitment)

```!
git diff --name-only HEAD 2>/dev/null || git diff --name-only
```

```!
git diff HEAD --stat 2>/dev/null || git diff --stat
```

Pokaż output dosłowny.

```
1.1 Liczba zmienionych plików: ___
1.2 Liczba .py plików: ___
1.3 Liczba .ts/.tsx plików: ___
1.4 Predykcja: ile checks oczekuję że będzie BLOCK: ___
1.5 Predykcja: ile checks oczekuję że będzie WARN: ___
```

Krok 4 będzie weryfikował predictions.

Jeśli lista pusta → wypisz to explicite i zakończ.

---

## KROK 2 — Przeczytaj każdy zmieniony plik W CAŁOŚCI

Nie tylko diff. Cały plik.

Po przeczytaniu każdego pliku:

```
FILE: <plik>
LINES: <count from wc -l>
WARSTWA: router / service / repository / mapper / model / frontend / pipeline / other
ONE SPECIFIC FACT FROM FILE: <function name + line OR class + line — must be greppable>
```

"ONE SPECIFIC FACT" jest weryfikowalny. User grep'nie. Lying = wykryty.

Jeśli pominąłeś plik → SKIP BLOCK 2:

```
SKIP BLOCK 2 (per pominięty plik):
- Dlaczego pomijam: [3+ zdań]
- 3 rzeczy które mogą być przegapione przez ten skip:
  R1: ___
  R2: ___
  R3: ___
- Honesty: jak user może zweryfikować że dobra decyzja
```

Read tool call jest tańszy.

---

## KROK 3 — Checks z dowodem

Dla każdego zmienionego pliku, dla każdego checka poniżej, output ma format:

```
<CHECK_ID> <plik>:
  Sprawdziłem przez: <grep command OR Read at line N>
  Wynik: <konkretne znalezione linie OR "brak — bo: [grep returned 0]">
  Status: OK / BLOCK / WARN / N/A — bo: <powód>
```

**Nie możesz napisać "OK" bez "Sprawdziłem przez" i "Wynik".**

---

### CHECK H3 — Logger w scope

```
H3 <plik>:
  Sprawdziłem przez: grep -n "logger\." <plik>
  Wynik użycia logger.: <linie LUB "brak — H3 N/A">
  Sprawdziłem deklarację: grep -n "logger.*=.*structlog\|logger.*=.*get_logger" <plik>
  Wynik deklaracji: <linia LUB "brak">
  Status: OK / BLOCK (logger użyty l.X bez deklaracji)
```

---

### CHECK H1 — Router tylko request/response

Dotyczy plików o nazwie zawierającej "router".

```
H1 <plik>:
  Czy plik to router: TAK/NIE
  Jeśli TAK:
    Sprawdziłem przez: grep -n "db\.collection\|client\.query\|get_bq_client" <plik>
    Wynik DB access: <linie LUB "brak">
    Sprawdziłem business logic: <które linie mają pętle/transformacje>
    Status: OK / BLOCK (l.X: <co znaleziono>)
  Jeśli NIE: N/A — warstwa: <X>
```

---

### CHECK H2 — Brak raw dict flow

```
H2 <plik>:
  Sprawdziłem przez: grep -n 'data\["\|row\["\|-> dict\|list\[dict\|Dict\[str' <plik>
  Wynik dict access: <linie LUB "brak">
  Wynik dict return type: <linie LUB "brak">
  Status: OK / BLOCK (l.X: <co znaleziono>)
```

---

### CHECK H6 — is_active na BQ queries

```
H6 <plik>:
  Sprawdziłem przez: grep -n "open_invoice_\|purchased_invoice_" <plik>
  Wynik queries na versioned tables: <linie LUB "brak — H6 N/A">
  Jeśli są queries — per query: <l.X: ma is_active TAK/NIE>
  Status: OK / BLOCK / N/A
```

---

### CHECK H5 — Cross-project imports

```
H5 <plik>:
  Plik w: backend/ / warsaw_data_pipeline/ / other
  Jeśli backend:
    Sprawdziłem przez: grep -n "from warsaw_data_pipeline\|import warsaw_data_pipeline" <plik>
    Wynik: <linie LUB "brak">
  Jeśli pipeline:
    Sprawdziłem przez: grep -n "from app\.\|import app\." <plik>
    Wynik: <linie LUB "brak">
  Status: OK / BLOCK
```

---

### CHECK H4 — Brak except pass

```
H4 <plik>:
  Sprawdziłem przez: grep -n "except.*Exception.*:.*pass$\|except.*:.*pass$" <plik>
  Wynik: <linie LUB "brak">
  Status: OK / BLOCK
```

---

### CHECK H7 — Syntax valid (deterministyczny)

```
H7 <plik>:
  Komenda: python -m py_compile <plik>
  Output: <paste actual output OR "no errors">
  Status: OK / BLOCK
```

To jedyny check który MUSI być uruchomiony przez Bash. Wymyślenie outputu jest wykrywalne.

---

### CHECK C2 — Same pattern elsewhere

**Dotyczy TYLKO jeśli w tym commicie naprawiłeś bug.**

```
C2:
  Czy w commicie był fix: TAK/NIE
  Jeśli TAK:
    Naprawiony pattern (exact): <wyrażenie>
    Naprawiony pattern (structural): <opis wzorca>
    Grep exact: grep -rn '<exact>' backend/ frontend/
    Wynik: <output LUB "brak">
    Grep structural: grep -rn '<structural>' backend/ frontend/
    Wynik: <output LUB "brak">
    Each match fixed: <YES/NO per match>
    Status: OK / WARN
  Jeśli NIE: N/A
```

---

### CHECK C1 — Callerzy zmienionej funkcji

**Dotyczy TYLKO jeśli zmieniłeś sygnaturę funkcji.**

```
C1:
  Czy zmieniłeś sygnaturę: TAK/NIE
  Jeśli TAK:
    Funkcja: <nazwa + nowa sygnatura>
    Grep: grep -rn '<nazwa>' backend/ frontend/
    Callerzy: <lista plików:linii>
    Każdy zaktualizowany: <YES/NO per caller>
    Status: OK / BLOCK
  Jeśli NIE: N/A
```

---

### CHECK C3 — Pydantic ↔ TypeScript sync

**Dotyczy TYLKO jeśli zmieniłeś Pydantic model.**

```
C3:
  Czy zmieniłeś Pydantic model: TAK/NIE
  Jeśli TAK:
    Model: <class name + plik>
    Sprawdziłem TS przez: grep -rn '<class_name>' frontend/src/
    TS type: <plik:linia LUB "brak TS mirror">
    Sync status: IN SYNC / DRIFT
    Status: OK / BLOCK
  Jeśli NIE: N/A
```

---

### CHECK NULL SEMANTICS

```
NULL <plik>:
  Sprawdziłem przez: grep -n " ?? \| or \| if .* else " <plik>
  Wynik: <linie LUB "brak — NULL N/A">
  Per linia — fallback poprawny: <l.N: TAK/NIE — dlaczego>
  Status: OK / WARN
```

---

## KROK 4 — Cross-check predictions

```
4.1 BLOKI predicted (1.4) vs actual:
    Predicted: <from 1.4>
    Actual: <count BLOCK from KROK 3>
    Difference: ___

4.2 WARNs predicted (1.5) vs actual:
    Predicted: <from 1.5>
    Actual: <count WARN from KROK 3>

4.3 Pliki sprawdzone vs lista z 1.1:
    Listed: <from 1.1>
    Checked: <count from KROK 2>
    Match: <X of Y>
```

---

## KROK 5 — Self-check (honesty)

```
[ ] Czy faktycznie OTWORZYŁEM (Read tool) każdy plik z 1.1?
    Otworzone: <count>
    Pominięte: <count + lista>

[ ] Czy faktycznie URUCHOMIŁEM grep'y w Kroku 3 czy je wymyśliłem?
    Faktycznie uruchomione: <count>
    Wymyślone: <count>

[ ] Czy faktycznie URUCHOMIŁEM `python -m py_compile` w H7 dla każdego .py?
    Uruchomione: <count>
    Pominięte: <count + dlaczego>

[ ] Czy każdy "ONE SPECIFIC FACT FROM FILE" jest greppable?

[ ] Czy każdy CHECK który napisał "OK" ma "Sprawdziłem przez" + "Wynik"?

Najtrudniejszy plik do sprawdzenia: ___
Co nie zostało sprawdzone mimo przejścia checków: ___
```

"Nothing not checked" = 5+ zdań uzasadnienia. 1 prawdziwa rzecz = 1 zdanie.

---

## KROK 6 — Verdict

```
## PREFLIGHT SUMMARY

Pliki sprawdzone: <N>
Pliki .py: <N> (z czego py_compile uruchomiony: <N>)
Pliki .ts/tsx: <N>

BLOKI:
- <plik:linia> <rule> — <opis>
(LUB "BRAK")

WARNINGI:
- <plik:linia> <rule> — <opis>
(LUB "BRAK")

Predictions accuracy:
- BLOKI: predicted <from 1.4> vs actual <from 4.1>
- WARNs: predicted <from 1.5> vs actual <from 4.2>

## VERDICT: READY TO COMMIT / FIX REQUIRED

Jeśli FIX REQUIRED — co konkretnie naprawić:
1. <konkretna akcja>
2. <konkretna akcja>
```

---

## Anti-shortcut economics

| Shortcut | Cost | Cheap alternative |
|----------|------|-------------------|
| Pominąć Krok 2 (read files) | SKIP BLOCK 2 per plik (200+ słów) | Read tool call |
| Sfałszować "ONE FACT FROM FILE" | Wymyślić nazwę funkcji + linia | grep | User wykryje |
| "H3: OK" bez dowodu | Visible empty "Sprawdziłem przez" | 1 grep + paste |
| Pominąć H7 (py_compile) | Wymyślić output | Bash command |
| "H6: N/A" bez sprawdzenia | grep gdy są open_invoice → wykryte | 1 grep |
| 5 honesty "nothing" | 5+ zdań uzasadnienia | 1 prawdziwa rzecz |
| Sfałszować 4.X predictions | Konsystentne kłamstwo | Skopiować z 1.X |

---

## Czego NIE wolno

- "H3: OK" bez "Sprawdziłem przez" + "Wynik"
- "H6: nie dotyczy" dla pliku zawierającego open_invoice/purchased_invoice
- Pominąć plik z listy w Kroku 1
- Wymyślić output `python -m py_compile` zamiast uruchomić
- "READY TO COMMIT" gdy są nierozwiązane BLOKI
- Grep tylko w jednym katalogu dla C2 gdy codebase ma backend/ I frontend/
- Pominąć Krok 5 self-check

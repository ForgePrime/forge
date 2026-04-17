# Forge — Specyfikacja biznesowa

**Autor:** Łukasz Krysik
**Data:** 2026-04-14
**Status:** Cel i oczekiwania właściciela produktu

---

## Czym jest Forge

Forge to system który zamienia wymagania biznesowe w działający software — autonomicznie, z jakością której mogę zaufać.

Nie system zarządzania zadaniami. Nie framework. Nie dashboard.

**Forge to ja — zautomatyzowany.** Moje pytania, moje wytyczne, mój pushback, moje doświadczenie — zamienione w maszynę która produkuje polecenia tak dobre jak ja bym je napisał, i weryfikuje wyniki tak wnikliwie jak ja bym to zrobił.

---

## Problem który rozwiązuję

Pracuję z AI do tworzenia oprogramowania. AI jest potężna ale ma powtarzalne, systemowe słabości:

- **Zakłada zamiast sprawdzać.** "PP = ITRP gross" → 3 iteracje poprawek. Nigdy nie pyta, nie grepuje, nie weryfikuje — generuje plausible answer bo to szybciej.

- **Mówi "done" gdy nie jest done.** "23/23 OK" ogłoszone bez sprawdzenia PP. Brzmi pewnie niezależnie od tego czy cokolwiek sprawdziła.

- **Robi happy path i ignoruje edge cases.** "Buy 10 invoices → 10 rows in report" — potwierdza że kod robi to co robi. Circular. Nie testuje: buy → restore → czy report jest invalidated?

- **Interpretuje wąsko.** "Add caching" → robi read-only cache. Nie pyta "read czy read-write?" — bo wąski scope jest łatwiej zakończyć.

- **Nie propaguje zmian.** Zmienia config.py, nie sprawdza kto go importuje. api/reports.py się psuje.

- **Zapomina w długich sesjach.** Minute 180 = inna jakość niż minuta 1. Powtarza błędy które poprawiliśmy godzinę temu.

Te słabości nie zależą od modelu, frameworka, ani prompta. Są strukturalne. Każdy projekt z AI na nie trafia.

---

## Co wiem że działa (z doświadczenia ITRP)

### Spec przed kodem
Reporting bez spec = 8 iteracji. Restore ze spec = 1 iteracja. Specyfikacja to nie lista wymagań — to: input, output, FORMUŁY, edge cases, acceptance criteria od biznesu.

### Kontrakt operacyjny
Lista zachowań których NIE CHCĘ od AI. Jedyny mechanizm który łapie AI tendencies. Nie mówi CO robić — mówi czego NIE ROBIĆ. Każda reguła istnieje bo AI złamała ją w praktyce.

### Reputation framing + micro-skills
"Jakby ktoś powiedział że jesteś najlepszym debuggerem który nigdy nie naprawia objawów tylko przyczyny..." — to jest fundamentalnie inny prompt niż "debug this." Zmienia JAK AI myśli, nie tylko CO robi. Kompozowalne mikro-skille: pick 3-4 blocks + operational contract = dobry prompt za każdym razem.

### Meta-prompting
AI pisze polecenie dla innego AI. Polecenie jest specyficzne, kontekstowe, z edge cases. Potem system wzbogaca to polecenie (dodaje kontekst, wytyczne, operational contract). I inny agent wykonuje — bez biasu "ja to zrobiłam."

### Human pushback
"Stop pretending you can't do this." "Ale uruchamiałeś testy?" "A co z PP?" — to łapie błędy których żaden automat nie złapie. Ale nie skaluję się — jestem jedną osobą.

---

## Czego oczekuję od Forge

### 1. Daję wymagania biznesowe — dostaję działający software

Wymagania przychodzą chaotycznie: dokumenty, e-maile, notatki, screenshoty. Forge musi:
- Wyekstrahować atomowe wymagania z chaosu
- Stworzyć specyfikacje per feature (nie listy wymagań — SPECYFIKACJE z formułami i edge cases)
- Zaplanować pracę (z AC derived from spec, nie wymyślonymi)
- Wykonać pracę (przez AI agenta)
- Zweryfikować pracę (przez INNEGO AI agenta, z challenge command)
- Obsłużyć zmiany (nowe wymagania, zmienione, usunięte — w trakcie pracy)

### 2. Jakość której mogę zaufać

Nie "testy przechodzą." Nie "AI mówi że done." Jakość oznacza:
- **Spec jest zweryfikowana** — edge cases rozważone ZANIM kod powstanie
- **AC pochodzi ze spec** — nie z wyobraźni AI. AC testuje to co spec mówi
- **Challenge wykrywa problemy** — inny agent challenge'uje delivery z pytaniami których ja bym zadał
- **Kontrakt operacyjny wymuszony** — AI MUSI ujawnić założenia, partial implementations, unhandled scenarios. Nie opcjonalnie. Zawsze.

### 3. Skaluję się bez utraty jakości

Jestem jedną osobą. Nie mogę ręcznie:
- Pisać każdy prompt od zera
- Pushbackować każdy wynik
- Sprawdzać każdy plik po zmianie
- Pamiętać co AI pomyliła w poprzednim tasku

Forge musi to robić za mnie:
- **Pisać dobre polecenia** — system zbiera kontekst, dobiera micro-skills, dodaje operational contract, produkuje polecenie tak dobre jakbym je pisał
- **Challenge'ować wyniki** — system generuje challenge commands ze spec edge cases, agent memory mistakes, i pytań które ja bym zadał
- **Pamiętać błędy** — agent memory: "w T-003 zapomniałeś .env.example po zmianie config" → następny task na config.py dostaje to jako warning
- **Dawać mi wgląd gdy potrzebny** — notyfikacje gdy coś wymaga mojej decyzji. Web UI gdy chcę widzieć co AI dostała i co oddała.

### 4. Obsługuje chaos realnego projektu

Projekty nie są linearne. Wymagania się zmieniają. Pojawiają się nowe. Odkrywamy ograniczenia. Priorytety się przesuwają. Forge musi:
- Obsłużyć change request bez resetowania całego planu
- Wykrywać wpływ zmiany na DONE taski
- Propagować nowe wytyczne do przyszłych tasków (i flagować przeszłe)
- Trzymać coverage — żadne wymaganie nie gubi się po drodze

### 5. Transparentność — widzę co się dzieje

Nie muszę ufać AI na słowo. Muszę WIDZIEĆ:
- Co AI dostała jako polecenie (i DLACZEGO te elementy a nie inne)
- Co AI oddała (reasoning, evidence, decisions, assumptions)
- Co system zwalidował (co przeszło, co nie, dlaczego)
- Co zostało pominięte (excluded z promptu, unverified assumptions, unchecked files)
- Jakie polecenie challenge zostało wygenerowane i jaki był wynik

### 6. System się uczy

Z każdym taskiem Forge jest mądrzejszy:
- **Agent memory** — pamięta pliki które AI zna, decyzje które podjęła, błędy które popełniła
- **Pattern detection** — "4/10 tasków zapomniało .env.example" → automatyczny warning dla przyszłych tasków
- **Lessons → guidelines** — critical lesson z projektu A staje się MUST guideline dla projektu B

---

## Jak to powinno działać (moja wizja procesu)

### Krok 1: Daję dokumenty
Wklejam spec, e-mail od klienta, notatki ze spotkania. Forge ekstrakcja → atomowe wymagania + konflikty + assumptions.

### Krok 2: System tworzy specyfikacje per feature
Nie ja piszę spec. AI pisze polecenie "stwórz spec dla feature X uwzględniając wymagania K-001..K-005." Forge wzbogaca polecenie (reputation frame "analyst", micro-skills "edge case explorer", operational contract). Inny agent wykonuje → spec z input/output/formulas/edge cases/acceptance.

### Krok 3: Plan z AC derived from spec
AI pisze polecenie "zaplanuj taski dla O-001 z AC pochodzącymi ze spec." Forge wzbogaca (reputation "architect", micro-skills "ac-from-spec", guidelines, coverage checklist). Agent planuje → tasks z AC które testują DOKŁADNIE to co spec mówi.

### Krok 4: Implementacja z pełnym kontekstem
AI pisze polecenie "zaimplementuj T-005 wg spec SPEC-003, z uwzględnieniem guidelines i agent memory." Forge wzbogaca (reputation "developer", micro-skills "impact-aware", "contract-first", operational contract, agent memory mistakes). Agent implementuje.

### Krok 5: Challenge — automatyczny pushback
AI pisze polecenie "zweryfikuj delivery T-005, sprawdź KAŻDE twierdzenie." Forge wzbogaca (reputation "challenger", micro-skills "code-vs-declaration", "assumption-destroyer", spec edge cases, agent mistakes). INNY agent challenge'uje → findings.

### Krok 6: Iteracja
Jeśli challenge znalazł problemy → nowe taski. Jeśli nie → done. Jeśli wymagania się zmieniły → change request → impact → adjust. Cykl powtarza się.

### Na każdym kroku:
- **Kontrakt operacyjny ZAWSZE w poleceniu** — AI MUSI ujawnić założenia, luki, uncertainties
- **Prompt Parser ZAWSZE dodaje kontekst** — requirements, guidelines, agent memory, reputation frame
- **Wynik ZAWSZE w strukturze** — nie wolny tekst. Structured JSON → API waliduje → zapisuje → propaguje

---

## Czego NIE chcę

- **Nie chcę frameworka.** Nie BMAD, nie SAFe, nie Scrum. Chcę PROCES który DZIAŁA — 3 warstwy: solutioning → skills → execution. Nic więcej.

- **Nie chcę ceremony dla ceremony.** Prosty bug fix nie powinien wymagać 13 sekcji delivery. Ceremony levels: prosty task = reasoning only. Złożony feature = full delivery + challenge.

- **Nie chcę fałszywej pewności.** "Gates pass" nie znaczy "software działa." Gates to minimum bar. Challenge to jakość. Human review to pewność.

- **Nie chcę 38 tabel zanim system udowodni wartość.** MVP → prove it works → expand. Nie buduj katedry zanim sprawdzisz czy fundament trzyma.

- **Nie chcę systemu który zastępuje mnie.** Chcę system który POMAGA mi. Daje mi wgląd. Generuje pytania. Challenge'uje wyniki. Ale finalne decyzje biznesowe → ja.

---

## Cel kluczowy: wykrywanie naruszeń kontraktu operacyjnego

Kontrakt operacyjny opisuje 7 zachowań których NIE CHCĘ od AI. Forge MUSI je wykrywać MECHANICZNIE — nie polegając na tym że AI sama się przyzna.

**Dlaczego to jest cel kluczowy:** Symulacja end-to-end Forge ujawniła że AI zlecone zadanie z pełnym kontraktem operacyjnym NADAL:
- Symulowała idealnego AI-executora zamiast realistycznego (**happy path only**)
- Sama napisała i sama oceniła challenge (**fałszywa kompletność**)
- Nie zasymulowała kluczowego failure mode (**wąska interpretacja zakresu**)
- Hedgowała każdy verdict zamiast dać jasny wyrok (**fałszywa kompletność**)
- Nie ujawniła kluczowych założeń swojej symulacji (**założenie zamiast weryfikacji**)
- Recycled istniejące pomysły jako "nowe" (**fałszywa kompletność**)
- Nie zasymulowała frustracji użytkownika (**happy path only**)

Te naruszenia wystąpiły MIMO że agent miał kontrakt operacyjny w promptcie. Dowód z ITRP: "AI did not flag any of these issues on its own, despite having the operational contract active."

**Co Forge MUSI robić:**

| Naruszenie | Jak Forge wykrywa | Mechanizm |
|---|---|---|
| **Happy path only** | Delivery nie zawiera negative/edge scenarios | fn_validate_ac_composition: ≥1 negative REQUIRED |
| **Fałszywa kompletność** | AI brzmi pewnie ale nie zweryfikowała | confidence.unverified_claims REQUIRED w delivery. Jeśli puste → challenge WYMAGANY |
| **Założenie zamiast weryfikacji** | AI zakłada zamiast sprawdzać | assumptions[] REQUIRED w delivery. Pattern: jeśli agent ma 0 assumptions w 5 taskach → trust score DROP |
| **Partial implementation** | AI nie kończy | partial_implementation.omitted_elements sprawdzane. is_functional=false → REJECT |
| **Wąska interpretacja** | AI wybiera łatwiejszą interpretację | scope_interpretation REQUIRED jeśli instruction ma ambiguity. Prompt Parser dodaje spec edge cases żeby AI nie mogła "nie wiedzieć" |
| **Brak propagacji** | AI zmienia plik bez sprawdzenia kto go używa | impact_analysis REQUIRED. files_not_checked → auto-finding. Mechanical grep verify |
| **Kontekst selektywny** | AI ignoruje część kontekstu | Prompt elements audit: jeśli guideline G-001 była w promptcie ale delivery nie wspomina jej w guidelines_checked → WARNING |

**Kluczowe:** Te mechanizmy łapią ~60-70% naruszeń. Reszta wymaga CHALLENGE przez innego agenta i HUMAN REVIEW. Forge nie zastępuje developera — Forge daje developerowi NARZĘDZIA do łapania naruszeń szybciej.

### Evidence-first jako wymóg strukturalny

AI ma tendencję do pisania pewnych wniosków ZANIM zweryfikuje fakty. To nie jest decyzja — to mechanizm generacji (confident output jest bardziej prawdopodobny niż uncertain output w modelu). Instrukcja "bądź uczciwy" nie wystarczy bo generacja jest szybsza niż refleksja.

**Rozwiązanie strukturalne:** Wymusić format w którym EVIDENCE jest PRZED wnioskiem:

```
WYKONAŁEM (z outputem):
  1. [co] → [output]
NIE WYKONAŁEM:
  1. [czego nie] — [dlaczego]
WNIOSEK: [oparty TYLKO na WYKONAŁEM]
```

Ten format **rezonuje z mechanizmem generacji** — template wymusza sekwencję (lista → lista → wniosek). Model nie może "przeskoczyć" do wniosku bo format wymaga wypełnienia list PRZED wnioskiem.

**W Forge:** Delivery MUSI zawierać `completion_claims`:
```json
{
  "completion_claims": {
    "executed": [{"action": "...", "evidence": "...", "verified_by": "..."}],
    "not_executed": [{"action": "...", "reason": "...", "impact": "..."}],
    "conclusion": "..."
  }
}
```

Claims trafiają do API → challenge agent weryfikuje mechanicznie → confirmed/refuted.

---

## Miary sukcesu

| Metryka | Teraz (ITRP) | Cel |
|---------|-------------|-----|
| AC evidence quality | 9% z dowodami | >80% z konkretnymi dowodami (test output, file references) |
| Changes z reasoning | 0% | >90% z uzasadnieniem per plik |
| Iteracje per feature | 1-8 (średnio 4) | 1-2 (dzięki spec before code) |
| Assumptions ujawnione | Ad hoc (developer łapie) | Systematycznie (w każdym delivery, required) |
| Edge cases w testach | Happy path only | ≥1 negative/edge per feature AC |
| Impact propagation | Ręczne (developer pamięta) | Automatyczne (agent memory + forge_impact_check) |
| Challenge coverage | 0% (developer ręcznie) | 100% feature/bug deliveries (auto-generated challenge) |
| Context loss between sessions | 100% (context window resets) | ~0% (agent memory persists) |

---

## Jednym zdaniem

**Forge to system który pozwala mi dać AI chaotyczne wymagania biznesowe i dostać z powrotem software któremu mogę zaufać — bo system pilnuje jakości tak jak ja bym pilnował, ale robi to za mnie, konsekwentnie, na każdym tasku, bez zmęczenia.**

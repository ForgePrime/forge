# UX — persony i scenariusze end-to-end

Cel: dać implementatorowi (frontend agent) konkretną wiedzę o tym **kto** używa Forge i **co** robi krok po kroku. Każdy element UI w pozostałych dokumentach odnosi się do jednej z poniższych ról albo jednego ze scenariuszy — jeśli czegoś tu nie ma, to znaczy że w UI tego nie trzeba.

---

## 1. Persony

Zidentyfikowałem trzy persony. Dwie pierwsze to użytkownicy core; trzecia (Audytor) pojawia się rzadziej, ale jej ograniczone potrzeby dyktują niektóre decyzje (np. linki permanentne do raportów, widoki read-only).

### Persona A — "Tech Lead pilotujący"
> Marta, 34 l., tech lead w Lingaro. Dostaje SOW od account managera, ma 2 tygodnie i $200 budżetu na LLM żeby ocenić czy Forge da radę na tej domenie.

- **Rola:** prowadzi pilot dla konkretnego klienta. Decyduje czy iść dalej.
- **Cele:**
  - W 1 dzień zobaczyć czy analiza nie zgubiła requirementów z SOW.
  - W 3 dni zobaczyć pierwsze 3 taski DONE z przechodzącymi testami.
  - Zdążyć przed review z klientem — w piątek ma prezentować pierwsze endpointy.
- **Frustracje:**
  - "Kliknąłem Orchestrate i nic się nie dzieje. Serwer żyje? Agent żyje? Ile to potrwa?" (Problem F)
  - "Analyze wygenerował 5 objectives — 4 OK, 1 jest bez sensu bo zlepił requirementy dwóch dokumentów. Jak to poprawić?" (Problem A)
  - "Claude znalazł finding 'brak walidacji input'. Chcę to zrobić jako T-010 zanim idzie dalej. Jak?" (Problem A — triage)
- **Poziom techniczny:** senior. Czyta SQL, pytest, git diff. Nie będzie czytał dokumentacji UI, ale umie odpalić curl jak musi.
- **Success state:** w piątek pokazuje klientowi 5 endpointów, każdy ma tabelę „AC: 3/3 pass, cross-model challenge: PASS, cost: $2.40" i klient mówi „idziemy w produkcję".
- **Alternatywy jeśli Forge nie dowozi:** rozpisze taski ręcznie w Linearze i wyśle do zespołu. Forge musi być szybszy niż to.

### Persona B — "Solution Architect z iteracją"
> Piotr, 41 l., SA. Prowadzi 3 projekty jednocześnie. Wraca do Forge po tygodniu żeby zobaczyć "co się zmieniło" i czy trzeba reagować.

- **Rola:** buduje coś przez wiele tygodni, nie w jednym push. Zleca orchestrate, wraca, koryguje, zleca kolejne.
- **Cele:**
  - Po 2 tyg. przerwy w 30 sek. zrozumieć stan projektu — co zostało zrobione, co się nie udało, gdzie są blokery.
  - Dodać 2 nowe taski które wymyślił pod prysznicem, przepiąć jeden objective, odpalić dalej.
  - Porównać 2 projekty które prowadzi równolegle (WarehouseFlow vs AppointmentBooking) — który ma więcej findings HIGH?
- **Frustracje:**
  - "Otwieram projekt i widzę tablicę 47 tasków. Co się zmieniło od ostatniej wizyty? Nie wiem." (Problem E)
  - "Chcę dodać AC do T-014 bo klient doprecyzował. Nie mogę — musiałbym usuwać task i rozpisywać na nowo." (Problem A)
  - "Przed chwilą zatwierdziłem 20 findings jednym po drugim klikając. To jest absurd." (Problem G)
- **Poziom techniczny:** staff. Pisze w czterech językach, ale woli klikać niż curlować.
- **Success state:** wchodzi → activity feed → „3 taski DONE, 4 findings HIGH czekają, $4.20" → triage w 2 min → dodaje 2 taski → orchestrate → wychodzi.

### Persona C — "Audytor / Stakeholder"
> Aneta, 48 l., PM klienta. Nie ma konta w Forge. Dostaje od Marty link do raportu T-007 i chce zobaczyć czy task faktycznie zrobiony.

- **Rola:** odbiór, compliance. Patrzy, nie edytuje.
- **Cele:**
  - Otworzyć link z emaila, zobaczyć przejrzysty raport bez logowania (lub z minimalnym).
  - Wydrukować / zapisać PDF do dokumentacji odbioru.
  - Zobaczyć: jakie były requirementy, jakie testy przeszły, ile to kosztowało.
- **Frustracje:** nie ma widoku „shareable" poza raportem surowym.
- **Poziom techniczny:** średni. Rozumie tabelki, nie pisze kodu.

**Decyzja projektowa:** persona C nie dyktuje własnego flow — wystarczy że widok `task_report` ma trwały URL, „Export PDF/MD" i ukrywa przyciski edycji gdy user nie jest zalogowany. Nie projektuję dla niej osobnej sekcji.

---

## 2. Kluczowe definicje „success state"

Dla Marty (A): **raport T-XXX pokazuje: 100% requirementów z SOW pokryte, testy PASS, challenger PASS, koszt w budżecie.** Jeśli którykolwiek nie — wie od razu co kliknąć (diff / retry / edit AC).

Dla Piotra (B): **w 90 sek. od wejścia rozumie 'co się zmieniło' i 'co wymaga mojej uwagi dziś'.** Jeśli nic nie wymaga — zamyka. Jeśli wymaga — wie dokładnie gdzie iść (activity feed → link → akcja).

---

## 3. Scenariusze end-to-end

Pięć scenariuszy pokrywa 95% realnych przypadków. Każdy podaje co user widzi i klika krok po kroku. Nawiasy `[View: X]` odnoszą się do widoków w `UX_SCREENS_MAP.md`.

### Scenariusz 1 — Greenfield pilot (Marta)

**Kontekst:** Klient WarehouseFlow przysłał 3 pliki (SOW.md, stakeholder_email.md, glossary.md). Marta ma $200, 14 dni. Pierwsze użycie Forge.

**Narracja:**
Marta otwiera `/ui/`. Widzi pustą listę projektów z wyraźnym empty state: **"Nie masz jeszcze projektu. Zacznij od utworzenia pierwszego."** z jednym dużym CTA **"+ Nowy projekt"**. Klika.

Otwiera się wizard (nie inline form jak teraz) — 3 kroki: (1) nazwa + slug + goal, (2) upload dokumentów źródłowych z drag-drop, (3) podsumowanie z checklistą „następne kroki". Marta wypełnia `warehouseflow / WarehouseFlow MVP / System zarządzania stanami magazynu`, w kroku 2 upuszcza 3 pliki md, w kroku 3 widzi **„Zaplanuj: 1) Analyze (15 min, ~$2) 2) Review objectives 3) Plan pierwszy objective 4) Orchestrate pierwsze 3 taski"**. Klika **„Analyze teraz"**.

[View: Project Overview] UI pokazuje banner „Analyze w toku — 2/3 min" (SSE live log: „parsing SRC-001... extracting objectives... found 5 objectives..."). Po ~3 min banner gaśnie, pojawia się toast „Analyze zakończone: 5 objectives, 12 KR, 2 konflikty, 3 open questions — $1.87". Widok przełącza się sam na tab **Objectives**.

Marta klika O-003 — bo tytuł wygląda dziwnie. [View: Objective Detail] widzi `title="Auth i Stock"`, business_context zlepiony z dwóch dokumentów. Marta klika „Edytuj", rozdziela na 2 objectives (O-003 Auth, O-006 Stock), zapisuje. Widzi też 2 konflikty w sekcji „Konflikty do rozwiązania" (D-001: „SOW mówi JWT, email mówi sesje"). Klika D-001 [View: Decision Resolve Modal], czyta oba dokumenty side-by-side (UI pokazuje fragmenty SRC-001 §2.4 i SRC-002), wybiera „JWT — bo SRC-001 jest oficjalny", pisze 80-znakową notkę. Zamyka.

Wraca do [Project Overview]. Top-bar pokazuje **"Następny krok: Plan O-001 (Login endpoint)"** — to pierwszy objective priority=1 bez planu. Klika „Plan O-001". Banner SSE „Planowanie... generuję 7 tasków... weryfikuję AC..." przez ~90 sek. Toast „Plan wygenerowany: 7 tasków, 21 AC". UI przełącza się na tab Tasks.

Marta przegląda tabelę — T-001..T-007. Klika T-001 [View: Task Detail] — widzi instruction, 3 AC, requirement_refs (SRC-001 §2.4), completes_kr_ids (KR0, KR1). Jedno AC ma verification=manual — Marta zmienia na verification=test, dopisuje test_path `tests/test_auth.py::test_login_rate_limit`. Zapisuje.

Wraca do [Project Overview], widzi banner **"7 tasków TODO, budżet pozostały $198.13"**. Klika **"Orchestrate"** — w modal ustawia max_tasks=3, stop_on_failure=on, budget_guard=$50. Potwierdza.

[View: Live Orchestrate] otwiera się automatycznie. Widzi:
- Top: pasek postępu „Task 1/3 — T-001 Login endpoint"
- Środek: 3 kolumny (T-001 IN_PROGRESS, T-002 queued, T-003 queued)
- Prawa kolumna: live log „Claude CLI running 2:14 / cost $0.34 / agent wrote app/auth.py, app/models/user.py / running pytest..."
- Down: timeline eventów

Marta zostawia zakładkę. Wraca po 25 min. Widzi T-001 DONE (zielony), T-002 DONE, T-003 FAILED (czerwony, „max retries, 1 AC failed: test_logout_invalidates_token"). Klika T-003 [View: Task Report] — widzi per-AC: 2 PASS, 1 FAIL z log pytest, 1 finding HIGH „logout nie invalidate JWT w Redis". Klika „Retry z poprawionym promptem" → otwiera się modal z obecnym instruction + polem "dopisz wskazówkę"; Marta pisze „Upewnij się że logout dodaje token do Redis blacklist z TTL=exp_time", odpala. Nowy execution, 8 min, DONE.

Marta eksportuje raport T-001 (menu w prawym górnym rogu „Eksport MD") żeby pokazać klientowi. Kopiuje link — Aneta dostaje `forge.lingaro.pl/ui/projects/warehouseflow/tasks/T-001?public=1`.

**Co UI musi zapewnić (referencja do problemów):**
- Wizard onboardingu zamiast pustego inline form (D)
- „Następny krok" contextual prompt zamiast 4 przycisków obok siebie (D)
- Edycja objective / AC / task po utworzeniu (A)
- Resolve decision z UI zamiast curl (A)
- Live orchestrate z SSE (F)
- Retry taska z poprawionym hintem (E, error-recovery)
- Export MD (G)

---

### Scenariusz 2 — Returning user (Piotr)

**Kontekst:** Piotr wraca po 8 dniach do projektu AppointmentBooking. W międzyczasie inny developer uruchomił kilka orchestrate.

**Narracja:**
Piotr otwiera `/ui/`. [View: Projects List] widzi 3 projekty jako kafelki. Kafelek appointmentbooking ma badge **"od ostatniej wizyty: +5 DONE, +2 FAILED, 4 nowe findings HIGH"** (kolorowy dot pulsuje jeśli są rzeczy HIGH). Piotr klika.

[View: Project Overview] — teraz ma nową sekcję **"Since last visit (8 dni temu)"** na górze, przed statystykami:
```
Od 2026-04-09:
  ✓ 5 tasków DONE (T-012..T-016)
  ✗ 2 taski FAILED (T-017, T-019)
  ⚠ 4 findings HIGH nie wystriage'owane
  💰 $12.40 wydane (budżet pozostały: $87.60)
  [Pokaż wszystko] [Triage findings →] [Zobacz failed →]
```

Piotr klika **"Triage findings →"**. [View: Findings Triage] — 12 findings posortowane domyślnie po severity DESC + status=OPEN. Checkbox multi-select. Piotr zaznacza 4 HIGH, klika bulk action „Approve wszystkie → utwórz taski jako T-020..T-023". Toast „4 taski utworzone, status=TODO, dependencies=[]".

Przełącza się na tab Tasks, filtruje status=FAILED. Widzi T-017 (test_refund failed), T-019 (test_reminder_email failed). Klika T-017 [View: Task Report]. Czyta per-AC, widzi że test_refund oczekuje waluty PLN ale kod dostaje EUR. Klika „Edit instruction" inline, dopisuje „Currency hardcoded to PLN". Klika „Retry" → execution #3 startuje. Nie czeka, wraca.

Piotr przegląda tab Activity (nowy, cross-entity audit timeline). Widzi porządek czasowy: „2026-04-14 09:12 — T-014 DONE (agent orchestrator-cli, cost $0.82); 2026-04-14 09:23 — F-007 auto-extracted (HIGH, źródło: challenger)". Dobrze wie kto co zrobił.

Chce dodać 2 nowe taski które wymyślił. Klika ikonę „+" na tabeli Tasks [View: Add Task Modal] — formularz z polami: name, type, origin (dropdown z objectives), instruction (markdown editor), AC (repeater), requirement_refs (tag input autocomplete z Knowledge external_ids), depends_on (multi-select z existing tasks). Wypełnia. Klika „Dodaj i zaplanuj" (alternatywa: „Dodaj jako draft"). Task zapisany. Drugi — kopiuje poprzedni jako template.

Klika Orchestrate, max_tasks=6. Zamyka przeglądarkę. Orchestrate leci dalej (persistent background job). Następnego dnia otwiera — widok pokazuje kompletny status.

**Co UI musi zapewnić:**
- "Since last visit" — diff state między wizytami (E)
- Kolorowane kafelki projektów z alertami (E)
- Bulk triage findings (G)
- Retry failed task z edytą instruction (E, error-recovery)
- Add Task modal z autocomplete dla requirement_refs/depends_on (B)
- Activity timeline (E, F)
- Persistent background job — zamknięcie karty nie zatrzymuje orchestrate (F)

---

### Scenariusz 3 — Power-user batch (Piotr w krótszym flow)

**Kontekst:** Piotr dostaje od klienta nową wersję SOW z 15 zmianami. Musi szybko ponownie przeanalizować i odpalić 10 tasków.

**Narracja:**
Piotr otwiera projekt. Naciska `Cmd+K` [Command Palette].
Wpisuje „re-ingest" — widzi „Re-ingest source documents". Enter. Modal z listą istniejących SRC-001..SRC-003, przy każdym „Replace" lub „Version up". Piotr upuszcza nowy SOW.md, zaznacza „Replace SRC-001", potwierdza. Toast „SRC-001 v2 aktywne, v1 oznaczone jako DEPRECATED".

`Cmd+K` → „analyze" → Enter. SSE banner. 2 min. 3 nowe objectives, 2 konflikty. Automatycznie pojawia się sekcja **"Wymaga decyzji"** z 2 konfliktami + open questions. Piotr przechodzi po kolei z keyboard shortcuts (J/K dla następny/poprzedni, 1/2/3 dla opcji). Wszystko zamknięte w 4 min.

`Cmd+K` → „plan O-008" → Enter. `Cmd+K` → „plan O-009" → Enter. `Cmd+K` → „plan O-010" → Enter.

Przegląda tasks, multi-select (Shift+klik), masowo przypisuje scope "backend". Ustawia Orchestrate max_tasks=20, stop_on_failure=off (chce zobaczyć wszystkie failures na raz). Zostawia zakładkę.

Rano sprawdza: 17/20 DONE, 3 FAILED. Bulk-retry 3 failed z checkboxa + przycisk „Retry selected". Po 12 min wszystko DONE.

**Co UI musi zapewnić:**
- Command palette Cmd+K z fuzzy search po akcjach (D, H)
- Keyboard shortcuts w decision resolve (H)
- Multi-select w tabeli Tasks z bulk actions (G)
- Re-ingest z wersjonowaniem Knowledge (A)

---

### Scenariusz 4 — Error recovery (Marta po failure)

**Kontekst:** Marta odpaliła orchestrate w tle. Wraca po obiedzie i widzi że orchestrate zawiódł — nie jeden task, tylko całe orchestrate skończyło się błędem „infra setup failed: postgres port conflict".

**Narracja:**
[View: Projects List] kafelek warehouseflow ma czerwony pasek **"orchestrate FAILED 14:22 — workspace infra error"** z CTA „Zobacz szczegóły".

Klika. [View: Orchestrate Run Detail] — widzi timeline:
- 13:58 Orchestrate started (max_tasks=5)
- 13:58 Infra setup: postgres port 5433 IN USE → retry port 5434 → IN USE → FAIL
- 13:58 Orchestrate aborted, 0 tasks executed
- Error detail: ports 5433-5440 all occupied

Każdy etap ma „Show log" (expand). Na dole **"Możliwe akcje"**:
- „Uruchom z innym zakresem portów" (pokazuje field „port_start: 5450", „port_end: 5460")
- „Uruchom z skip_infra=true" (z ostrzeżeniem „tests używające Postgres nie przejdą")
- „Zatrzymaj procesy na portach 5433-5440" (pokazuje pstree / netstat)

Marta klika pierwsze, wpisuje 5450, odpala. Nowy orchestrate run startuje. Live view — wszystko OK.

Inny przypadek: task T-005 skończył w `FAILED` bo Claude 3x zwrócił non-JSON. [View: Task Report] Marta widzi 3 execution attempts — każdy z llm_call link. Klika attempt #3 link [View: LLM Call] — widzi full prompt (30 KB), full response (Claude napisał tekst zamiast JSON). „Dlaczego? Prompt chyba był niejasny." Marta klika „Edit prompt template" → GLOBAL scope lub per-task → dopisuje ostrzeżenie „MUSISZ zwrócić JSON, nic więcej". Klika „Retry T-005 with updated prompt". Execution #4 startuje.

**Co UI musi zapewnić:**
- Orchestrate run detail ze szczegółowym timeline (F)
- Per-error „suggested recovery actions" (E)
- Drill-down exec attempts → LLM call (już jest, trzeba łączyć w UI)
- Edycja prompt templates z UI (C)

---

### Scenariusz 5 — Iterative refinement (Marta w środku pracy)

**Kontekst:** Po T-001..T-003 DONE Marta widzi że plan dla O-001 był zbyt optymistyczny — klient dopytał o "forgot password" którego nie było w SOW. Trzeba dodać task, przepiąć objective, poprawić KR.

**Narracja:**
Marta w [View: Project Overview] klika **„+ Change request"** (globalny przycisk górny). [View: Change Request Modal] — 3 zakładki:
1. **Nowy wymóg** — text area „co klient chce"
2. **Scope change** — które objective/task zmienić
3. **Clarification** — dopytanie, nie zmiana

Wybiera 1. Wpisuje „Klient chce forgot password flow — email z linkiem reset, ważność 1h". Klika „Wygeneruj impact". Backend (potrzebny nowy endpoint — zob. Open Questions) wywołuje LLM żeby zidentyfikować: które objectives dotknięte (O-001), które taski trzeba dodać/zmodyfikować, jakie nowe KR. UI pokazuje preview:
```
Impact analysis:
  + Dodać Knowledge SRC-004 „Forgot password spec" (z wklejonego tekstu)
  + Dodać KR3 do O-001: „Password reset completed in < 3 clicks"
  + Dodać 2 taski: T-008 „reset_token endpoint", T-009 „email sender for reset"
  ~ Zmodyfikować AC T-001: dopisać negative scenario „login fails after password change"
  Estymacja kosztu: $2.40
```
Marta edytuje preview (np. usuwa automatyczną zmianę T-001 bo nie chce tam ruszać), akceptuje resztę. Klika „Zastosuj". Toast „4 zmiany wprowadzone, Plan O-001 wersja 2".

Przegląda new tasks, klika Orchestrate dla T-008, T-009.

Po deploymencie T-009 widzi że email sender działa, ale challenger wykrył finding MEDIUM „email używa plain HTTP link — powinien HTTPS". Klika finding → **"Create task + link to T-009"** → task T-010 utworzony z depends_on=T-009 i origin=O-001. Odpala.

Na koniec Marta chce skopiować plan O-001 do siostrzanego projektu `appointmentbooking` (ma podobną auth). Otwiera tab Objectives → hover na O-001 → menu trzy-kropki → "Duplicate to project..." → wybiera docelowy projekt → preview co zostanie skopiowane (objective + KRs, opcjonalnie tasks z AC, NIE executions/findings). Akceptuje. W drugim projekcie pojawia się O-001 jako draft — można edytować przed Plan.

**Co UI musi zapewnić:**
- Change Request UI z impact preview (iterative refinement)
- Edycja AC taska po utworzeniu (A)
- Finding → create task jednym klikiem z linkowaniem (B, already partially in API)
- Duplicate objective/plan across projects (B — wymaga nowego endpointu, zob. CRUD matrix)

---

## 4. Kontekst użycia — rozstrzygnięcia

- **Desktop 1920×1080 (95%):** główny target. Layouty 2-3 kolumnowe.
- **Laptop 1366×768 (4%):** testuj żeby tabele nie łamały się poziomo — przewidzieć `overflow-x-auto` i sticky first column.
- **Tablet 1024×768 (1%):** brief wspomniał o kierownikach magazynu — to jest persona USERÓW WAREHOUSEFLOW, NIE userów Forge. Odrzucam tablet jako target Forge UI. Flag jako open question jeśli user się nie zgadza.
- **Mobile:** OUT OF SCOPE dla Forge — to tool do pracy głębokiej, nie do klikania w metrze.
- **Dark mode:** SHOULD-have. Developerzy go oczekują. Prosty toggle w navbar, Tailwind `dark:` classes.
- **Accessibility WCAG AA:** baseline — kontrast, focus visible, aria-labels na ikonach. Nie projektuję dedykowanego trybu, tylko nie psujemy podstaw.

---

## 5. Co świadomie ODRZUCAM z brief'u

- **Kierownicy magazynu na tabletach** — to nie są użytkownicy Forge (zob. wyżej).
- **Mobile responsive** — out of scope, flag.
- **Pełny native app** — nope, brief to zabrania.
- **Onboarding tutorial z interactive overlay** — przesadzone dla tej klasy toola; wystarczy wizard tworzenia projektu + empty states.

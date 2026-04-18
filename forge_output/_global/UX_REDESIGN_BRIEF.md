# Brief dla UX agenta — przeprojektowanie interfejsu Forge

**Dla kogo:** nowy agent (inna sesja), który dostaje ten dokument + surowe zrzuty kodu
**Cel:** kompletny redesign UI Forge z sensowną UX, mockupami i user journey
**Rola agenta:** UX designer + product thinking, NIE frontend developer
**Output oczekiwany:** w 5 deliverables (patrz sekcja "DELIVERABLES" na końcu)

---

## 1. KONTEKST — co to jest Forge i dla kogo

Forge to platforma "meta-prompting" do prowadzenia AI agentów przez cykl:
**Ingest dokumentów → Analiza → Planowanie → Orchestracja → Walidacja (Phase A/B/C) → Raport**

Użytkownik wrzuca dokumenty źródłowe (SOW, emaile od stakeholderów, glossary, NFR), Forge automatycznie:
- Wyciąga objectives + KRs
- Wyłapuje konflikty między dokumentami (→ OPEN decisions)
- Rozbija objective na zadania z graphem zależności i AC
- Uruchamia agenta Claude CLI który fizycznie pisze kod w workspace
- **Forge sam weryfikuje** (pytest, git diff, KR measurement — nie ufa self-reportowi agenta)
- **Drugi model (Opus) challenge'uje** wynik → znajduje dodatkowe bugs
- Extractor wyciąga ukryte decyzje + findings z reasoning agenta

**Użytkownik typowy:** senior developer / tech lead / solution architect, który chce kontroli nad projektami AI-generated. Nie typowy end user — techniczny.

**Typowe scenariusze użycia:**
1. Klient daje SOW + email → Forge proponuje rozbicie na tasky, user reviewuje zanim uruchomi
2. Pilot MVP — user chce zobaczyć czy Forge da radę na tej domenie zanim commituje budget
3. Iteracyjne budowanie — user uruchamia 2-3 taski, sprawdza wyniki, koryguje plan, dalej
4. Audit / compliance — user chce zobaczyć dokładnie jaki prompt AI dostała, co odpowiedziała, ile kosztowało

---

## 2. STAN OBECNY — co już jest zbudowane

### Dane w bazie (Postgres — SQLAlchemy)
Tabele (i co znaczą):
- `projects` (slug, name, goal)
- `knowledge` (source documents + requirements + specs, kategoria)
- `objectives` (cele biznesowe z `business_context`, `priority`, `scopes`)
- `key_results` (per objective; numeric z `target_value` + `measurement_command`, albo descriptive)
- `tasks` (external_id, name, instruction, type=feature|bug|chore|investigation, status, `origin` → objective, `requirement_refs` → lista SRC refs, `completes_kr_ids`)
- `acceptance_criteria` (per task; `scenario_type`=positive|negative|edge_case|regression, `verification`=test|command|manual, `test_path`)
- `executions` (per task uruchomienie; `prompt_text`, `contract`, `delivery`, `validation_result`)
- `llm_calls` (każde wywołanie Claude CLI — full prompt, full response, tokens, cost, duration, purpose=analyze|plan|execute|extract|challenge)
- `test_runs` (Forge-executed pytest — per-AC pass/fail mapping)
- `decisions` (konflikty, open_questions, implementation choices — OPEN/CLOSED, severity)
- `findings` (bug|smell|opportunity|gap|risk z severity, file_path, suggested_action — OPEN/APPROVED/DEFERRED/REJECTED)
- `changes` (pliki zmienione per task)
- `execution_attempts` (retry history z hash duplikatu)

### API endpointy (`/api/v1/*`)
```
POST /projects (slug, name, goal)
GET  /projects (list)
GET  /projects/{slug}/status

POST /projects/{slug}/ingest (multipart files)
POST /projects/{slug}/analyze
POST /projects/{slug}/plan {objective_external_id}
POST /projects/{slug}/orchestrate {max_tasks, stop_on_failure, skip_infra, enable_redis}

POST /projects/{slug}/tasks (list of task JSON)
GET  /projects/{slug}/tasks
GET  /projects/{slug}/tasks/{ext}
GET  /projects/{slug}/tasks/{ext}/report         ← "trustworthy DONE report"
POST /projects/{slug}/tasks/{ext}/generate-scenarios

POST /projects/{slug}/objectives (list)
GET  /projects/{slug}/objectives
PATCH /objectives/{id}/key-results/{pos}         ← manual KR edit

POST /projects/{slug}/guidelines (list)
GET  /projects/{slug}/guidelines

POST /projects/{slug}/knowledge (list)
GET  /projects/{slug}/knowledge

POST /projects/{slug}/decisions (list)
GET  /projects/{slug}/decisions
POST /decisions/{id}/resolve {status, resolution_notes}

GET  /projects/{slug}/findings
POST /findings/{id}/triage {action=approve|defer|reject, reason}   ← approve tworzy Task z finding

GET  /projects/{slug}/executions
GET  /executions/{id}
GET  /executions/{id}/prompt                     ← raw prompt dla tej execution

GET  /projects/{slug}/llm-calls
GET  /llm-calls/{id}                             ← full prompt + response + cost

POST /execute (claim next TODO task, start execution)
POST /execute/{id}/deliver (agent submits delivery)
POST /execute/{id}/heartbeat
POST /execute/{id}/fail
POST /execute/{id}/challenge                     ← generate challenge command
```

### UI obecne (`/ui/*`)
Stack: **Jinja2 server-side templates + HTMX + Tailwind CDN** (zero npm, zero build).

5 szablonów:
1. `templates/base.html` — layout z navbar "Forge" + main
2. `templates/index.html` — lista projektów, każdy jako kartka z statystykami (tasks/cost/findings/decisions). Button "+ New project" otwiera inline form.
3. `templates/project.html` — szczegół projektu:
   - Góra: 4 kafelki stats (tasks total/done/todo/failed, objectives count, total cost, findings/decisions count)
   - Pasek 4 akcji: **Ingest** (multipart upload), **Analyze** (button), **Plan** (select objective + submit), **Orchestrate** (number max_tasks + 2 checkboxy)
   - 6 tabs: Objectives (lista card), Tasks (tabela), LLM-calls (tabela), Findings (lista card), Decisions (lista card), Knowledge (lista card)
4. `templates/task_report.html` — trustworthy DONE report:
   - Nagłówek z cost by purpose
   - 2 kolumny: Requirements covered + Objective+KRs
   - Tests executed BY FORGE (aggregate + per-AC + expandable per-test)
   - Cross-model challenge (verdict badge + claims + per-claim details expandable)
   - Findings (color-coded severity, badge extractor/challenger)
   - Decisions (severity + recommendation + reasoning)
   - Acceptance criteria (scenario_type + verification + test_path)
   - Not-executed claims (jeśli są)
5. `templates/llm_call.html` — full prompt text + response text + parsed delivery JSON + stderr

Akcje HTMX:
- `POST /ui/projects` (form create)
- `POST /ui/projects/{slug}/{ingest|analyze|plan|orchestrate}` — każdy submit blokuje request (**synchronicznie czeka 2-30 min**), HTMX wywołuje `window.location.reload()` po sukcesie

### Co działa w UI
- View-only renderowanie istniejących danych: projekty, objectives, tasks, llm_calls, findings, decisions, knowledge
- Trigger 4 długich operacji (ingest/analyze/plan/orchestrate)
- Drill-down: klik na task → report, klik na LLM call → full prompt+response

---

## 3. PROBLEM — dlaczego "UI jest bezsensu"

Użytkownik powiedział wprost:
> "obecny interfejs jest bezsensu"

Moja (poprzedni agent) identyfikacja braków bez UX-owego spojrzenia:

### A. Brak edycji po utworzeniu
- **Objective**: Claude wyekstrahował → user nie może poprawić title/business_context/priority/scopes
- **KR**: jest PATCH endpoint dla `status` + `current_value`, ale UI nie ma formularza
- **Task**: user nie może edytować `instruction`, `requirement_refs`, `completes_kr_ids`, `scopes`, `depends_on` po utworzeniu
- **AC**: nie można dodać/usunąć/zmienić scenario_type po utworzeniu
- **Decision**: POST resolve istnieje, UI nie ma przycisku
- **Finding**: triage endpoint istnieje (approve→create task / defer / reject), UI nie ma przycisków
- **Knowledge**: nie można edytować treści, kategorii, scopes po upload
- **Guideline**: endpoint POST istnieje, UI w ogóle tej tabeli nie pokazuje

### B. Brak manualnego dodawania
- Nie można ręcznie dodać objective (tylko przez analyze)
- Nie można dodać KR do istniejącego objective (tylko przez analyze)
- Nie można dodać taska poza planem (np. "trzeba jeszcze X zrobić")
- Nie można dodać guideline (żadnego UI)
- Nie można dodać decision / finding ręcznie
- Nie można dodać knowledge poza upload

### C. Brak skills / customization
- Forge-starszy-system miał "skills" (slash commands: /plan, /analyze, /decide, /discover itd.) — **w nowym platform/ tego nie ma**
- User nie widzi jakie operacje są dostępne
- Nie może skonfigurować własnego skill/template
- Nie ma UI do edycji operational_contract text
- Nie ma UI do wyboru modelu (executor/challenger) per task
- Nie ma UI do edycji prompt_parser priorytetów

### D. Brak sensu w flow
- Pierwszy user landuje na `/ui/`, widzi pustą listę projektów. Klik "+ New project" — tworzy. I co dalej? Nie wie.
- Brak onboardingu / wizardu
- Akcje na `/projects/{slug}` są obok siebie bez jasnej kolejności — ingest? analyze? plan? które pierwsze?
- Orchestrate blokuje request 10-30 min — user myśli że się zawiesiło, nie ma progress, nie ma cancel, nie ma ETA
- Po kliknięciu orchestrate user patrzy na terminal serwera żeby zobaczyć co się dzieje (bo UI nic nie pokazuje)

### E. Brak wartościowej informacji
- Dashboard "tasks total = 47, cost = $15.42" — co to znaczy? Czy to dobrze? Czy trzeba coś zrobić?
- Nie ma alertów "masz 3 OPEN findings HIGH severity — wymaga uwagi"
- Nie ma quick actions "oto 5 rzeczy które powinieneś teraz zrobić"
- Nie ma śledzenia "w ciągu ostatnich 24h zmieniło się X"
- Brak diff viewera — user nie widzi co Claude fizycznie zmienił w plikach
- Brak workspace file browsera — user nie wie co jest w `forge_output/{slug}/workspace/`

### F. Brak obserwacji live operacji
- Orchestrate w tle 30 min — zero visibility
- Powinno być: strumień eventów "task T-004 IN_PROGRESS 2:15 elapsed, execute cost $0.47 do teraz, agent wrote 3 files, pytest running..."
- Powinno być: możliwość przerwania bieżącego taska
- Powinno być: log output Claude CLI na żywo

### G. Brak export / share
- Nie można pobrać trustworthy report jako PDF/MD
- Nie można wysłać linku do konkretnego raportu
- Nie ma multi-select (np. zatwierdź 5 findings na raz)

### H. Brak UX podstawowych
- Brak search/filter
- Brak sortowania (lista findings per severity?)
- Brak keyboard shortcuts
- Brak dark mode
- Brak mobile responsive (tablety — kierownicy magazynu używają tabletów według WarehouseFlow SOW)
- Brak breadcrumbs
- Brak confirmation dialogs dla destructive actions

---

## 4. TWOJE ZADANIE — konkretne kroki myślowe

### Krok 1: Zrozum użytkownika
Zanim coś zaprojektujesz, odpowiedz NA PIŚMIE (w deliverable 1):
- **Kim jest docelowy user?** (persona: rola, cele, frustracje, level techniczny)
- **Co dla niego znaczy "Forge mu pomógł"?** (jaki jest jego "success state")
- **Jakie ma presja w kontekście biznesowym?** (deadline, budget, odpowiedzialność)
- **Jakie ma alternatywy?** (jeśli Forge nie dowozi, co robi zamiast)

### Krok 2: Zmapuj CRUD per każda encja
W tabeli, dla każdej encji (Project, Objective, KR, Task, AC, Knowledge, Guideline, Decision, Finding) odpowiedz:
| Encja | Create manual | Create auto | Read | Update | Delete | Bulk ops |
|-------|---------------|-------------|------|--------|--------|----------|
| Project | ... | ... | ... | ... | ... | ... |
| Objective | ... | ... | ... | ... | ... | ... |
...

**Dla każdej operacji która istnieje w API ale brak UI — zaznacz jako MUST-HAVE.**
**Dla każdej operacji której brakuje w API — zaznacz "potrzebny nowy endpoint" i uzasadnij.**

### Krok 3: Zmapuj end-to-end user journey
Napisz PROSE (w deliverable 2) pełny scenariusz "nowy user, greenfield project":
1. User loguje się pierwszy raz (jakie UI widzi?)
2. Tworzy projekt (przez jaki formularz/wizard?)
3. Uploaduje dokumenty (jak widzi że są w systemie, jak może je edytować?)
4. Analizuje (co widzi w trakcie — progress bar? spinner? log stream?)
5. Przegląda wyekstrahowane objectives (co może tam zrobić? edit? add KR? reorder?)
6. Rozwiązuje konflikty (jakie są w formacie? jak user decyduje?)
7. Planuje objective (co widzi? jakie opcje? może edytować plan przed zatwierdzeniem?)
8. Orchestruje (live view? ETA? cancel? per-task progress?)
9. Review DONE report (jakie akcje ma? zaakceptować? zrobić retry? eksportować?)
10. Triage findings (UI do oceny każdego?)
11. Iteruje — co jeśli po tasku #5 user chce zmienić kolejność, dodać AC, uruchomić inne skill?

Opisz RÓWNIEŻ scenariusze "power user":
- User wraca do projektu po tygodniu — co widzi? (recent activity? co się zmieniło?)
- User chce porównać 2 scenariusze (np. WarehouseFlow vs AppointmentBooking) — gdzie to zobaczy?
- User w batch chce zatwierdzić 20 findings jednym klikiem
- User chce skopiować objective do innego projektu
- User chce re-run tasku z poprawionym promptem

### Krok 4: Znajdź punkty bólu i napraw
Dla każdego z 8 punktów (A-H z sekcji PROBLEM), zaproponuj KONKRETNE rozwiązanie UI:
- Jakie komponenty
- Jaka kolejność interakcji
- Jakie widoki / modale / inline edity
- Jakie feedbacki (toast? modal? inline validation?)
- Jak user rozumie progress / cost / co jest w toku

### Krok 5: Dodaj pattern'y których brakuje
Zastanów się nad wzorcami UX, których Forge obecnie nie ma:
- **Command palette** (Cmd+K) — szybki dostęp do akcji
- **Recent activity feed** — "od ostatniej wizyty: 3 taski DONE, 2 findings HIGH, $4.20 wydane"
- **Progressive disclosure** — zaawansowane opcje ukryte do rozwinięcia
- **Inline help** — każdy tricky pojęcie z tooltipem
- **Empty states** — zamiast pustej listy pokaż "Zacznij od uploadu SOW"
- **Confirmation patterns** — destructive actions z potwierdzeniem + undo window
- **Error recovery** — jak user recoveruje z failed orchestrate bez curl'a
- **Cost budget guards** — "Zostało $15 z $50 budgetu — kontynuować?"

### Krok 6: Zdefiniuj content hierarchy
Projects → Objectives → Tasks → ACs → Executions → LLM calls
Knowledge → Decisions → Findings

Czy user rozumie tę hierarchię? Czy UI pokazuje ją jasno? Breadcrumbs? Sidebar navigation?

Zastanów się:
- Czy niektóre encje powinny być "globalne" (guidelines per user, nie per project)?
- Czy user potrzebuje "workspace" w znaczeniu IDE (widok plików które Claude utworzył)?
- Czy llm_calls powinny być w osobnym "debug mode" czy domyślnie widoczne?

### Krok 7: Uwzględnij konteksty użycia
- **Desktop 1920×1080** — 95% przypadków
- **Tablet 1024×768** — jeśli będą kierownicy magazynu albo manager z walk-around
- **Mobile** — prawdopodobnie zbędne dla tej klasy tool, ale confirm
- **Dark mode** — developerzy używają często
- **High contrast / accessibility** — WCAG AA minimum
- **Cost visibility** — użytkownik na budżecie musi widzieć $ bieżący vs budżet zawsze

### Krok 8: Zaproponuj async operation pattern
Orchestrate to 10-30 min. Nie może blokować UI. Zaprojektuj:
- Jak user triggeruje
- Jak widzi progress (SSE? polling? WebSocket?)
- Jak cancel
- Jak odzyskuje po zamknięciu karty (persistent background jobs?)
- Jak wraca do tego jutro

---

## 5. CO MA NIE BYĆ

- **Nie projektuj native mobile app** — web only
- **Nie proponuj npm/build pipeline** — jeśli frontend, to Jinja+HTMX+Tailwind CDN albo Alpine.js CDN. Zero build.
- **Nie proponuj rewrite backendu** — API endpointy są gotowe, dopracuj gdzie brakuje
- **Nie pisz pełnego React SPA z Reduxem** — over-engineering dla tej klasy tool
- **Nie zakładaj że user będzie czytał dokumentację** — UI musi mówić samo

---

## 6. CO MA BYĆ

- **Mockupy** — mogą być ASCII / pseudo-HTML / Mermaid / figma-style prose. Każdy główny widok pokazany strukturalnie.
- **Screens map** — diagram/lista wszystkich widoków z linkami między nimi
- **User journey** — krok po kroku dla 3-5 realistycznych scenariuszy
- **Priorytetyzacja** — MUST / SHOULD / COULD per feature
- **Uzasadnienia UX** — "to rozwiązanie bo użytkownik robi X i Y dlatego Z"

---

## 7. FILES REFERENCE

Agent ma dostęp do tych plików (jeśli pracuje w tym repo):
```
platform/app/api/ui.py                     ← aktualny routing UI
platform/app/api/pipeline.py               ← endpointy ingest/analyze/plan/orchestrate + task_report
platform/app/api/projects.py               ← CRUD projects/objectives/tasks/...
platform/app/api/execute.py                ← execution lifecycle endpointów
platform/app/templates/base.html           ← layout
platform/app/templates/index.html          ← projects list
platform/app/templates/project.html        ← project detail + 6 tabs + 4 action buttons
platform/app/templates/task_report.html    ← trustworthy DONE report
platform/app/templates/llm_call.html       ← full prompt+response

platform/app/models/                       ← wszystkie SQLAlchemy tabele
platform/app/services/prompt_parser.py     ← jak prompt jest składany (P0-P99 + contract)
platform/app/services/contract_validator.py ← wszystkie walidacje

forge_output/_global/FORGE_*.md            ← raporty z każdej fazy (kontekst co Forge robi)
forge_output/warehouseflow/                ← przykład realnego projektu
forge_output/appointmentbooking/           ← drugi przykład
```

---

## 8. DELIVERABLES — co ma zwrócić agent

Zorganizuj output w 5 plików:

### 8.1 `UX_PERSONA_AND_JOURNEYS.md`
- Persona (2-3 warianty jeśli są)
- Scenariusze end-to-end (5 realistycznych: greenfield, returning, power-user-batch, error-recovery, iterative-refinement)

### 8.2 `UX_CRUD_MATRIX.md`
- Tabela encji × operacji (create manual/auto, read, update, delete, bulk)
- Per każda luka: propozycja (endpoint+UI+priorytet)

### 8.3 `UX_SCREENS_MAP.md`
- Lista wszystkich widoków (obecnych + proponowanych)
- Graf przejść między widokami (mermaid diagram albo ASCII)
- Każdy widok: purpose + key actions + info shown

### 8.4 `UX_MOCKUPS.md`
- Pseudo-HTML / ASCII mockup każdego głównego widoku
- Opis interakcji step-by-step
- Adnotacje "tu pokazujemy X bo użytkownik potrzebuje Y"

### 8.5 `UX_IMPLEMENTATION_PLAN.md`
- Priorytety MUST / SHOULD / COULD
- Kolejność implementacji (co jako pierwsze, co można odłożyć)
- Estymacja effort (S/M/L per feature)
- Które istniejące API endpointy wystarczą, które trzeba dopisać
- Lista open questions / decyzji które wymagają user input

---

## 9. ZASADA KAŻDEGO CHOICE'U

Przy każdym decyzji projektowej **napisz dlaczego** odnosząc się do:
1. Potrzeby użytkownika (który scenariusz?)
2. Frustracji którą rozwiązuje
3. Danych które już są w systemie (nie wymyślaj nowych encji bez potrzeby)
4. Alternatywy które odrzuciłeś (i dlaczego)

---

## 10. RED FLAGS — przed wysłaniem output sprawdź

- [ ] Czy zaadresowałeś każdy z 8 punktów (A-H) z sekcji PROBLEM?
- [ ] Czy odpowiedziałeś na "co user robi kiedy klika X" dla każdego widoku?
- [ ] Czy przeszedłeś całą ścieżkę end-to-end nie pomijając kroków?
- [ ] Czy rozróżniłeś "edit objective" od "edit KR" od "edit task"?
- [ ] Czy pokazałeś jak user widzi live progress orchestracji?
- [ ] Czy zaprojektowałeś empty states (nowy user, projekt bez zadań, tasks bez findings)?
- [ ] Czy uwzględniłeś error states (orchestrate failed, API timeout, workspace corrupt)?
- [ ] Czy każda proponowana funkcja ma uzasadnienie w potrzebie?
- [ ] Czy nie dodałeś ficzer-ow "bo ładnie" bez uzasadnienia?
- [ ] Czy dark mode / mobile / accessibility rozważone (nawet jako "out of scope")?

---

## 11. FORMAT INTERAKCJI

**Nie implementuj kodu** — Twoim zadaniem jest zaprojektować, nie napisać. Implementation zrobi kolejny agent po twoich mockupach.

**Zadawaj pytania** jeśli coś jest niejasne — zapisz je w `UX_IMPLEMENTATION_PLAN.md` sekcja "Open questions".

**Nie kopiuj mojego tekstu** — twoja wartość jest w syntezie, nie reprodukcji.

**Pomijaj oczywiste** — np. nie opisuj że "menu powinno być na górze" jeśli jest to standardem.

---

## 12. OCZEKIWANA TONALNOŚĆ

- Zdecydowana ale pokorna — "proponuję X bo Y" zamiast "X to najlepsze rozwiązanie"
- Konkretna — konkretny placeholder tekst, konkretne akcje, konkretne dane
- Skoncentrowana na user, nie na implementacji
- Bez buzzwords typu "seamless UX" albo "intuitive interface" — pokaż KONKRETNIE co to znaczy

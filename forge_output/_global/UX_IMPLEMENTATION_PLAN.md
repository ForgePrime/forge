# UX — plan implementacji

Cel dokumentu: dać frontend-dev-agent jasną listę **co**, **w jakiej kolejności**, **jakim kosztem**, i **co wymaga decyzji użytkownika zanim zacznie**.

Całość projektowana dla stacku obecnego: Jinja2 server-side + HTMX + Tailwind CDN + opcjonalnie Alpine.js CDN (dla command palette, multi-select, live updates). Zero npm, zero build.

---

## 1. Priorytetyzacja (MUST / SHOULD / COULD)

### MUST-have — bez tego UI jest dalej bezsensu
Wszystkie wymienione tu elementy rozwiązują problemy blokujące core flow (Scen. 1, 2, 4). Pominięcie dowolnego = user zostaje sparaliżowany na tym kroku.

| # | Feature | Scenariusz | Problem | Effort |
|---|---------|-----------|---------|--------|
| M1 | Onboarding wizard (P4) zamiast inline form | 1 | D | S |
| M2 | Project Overview z "Next step" + "Since last visit" (P1 rozbudowa) | 1,2 | D,E | M |
| M3 | Live Orchestrate View z SSE (X2) + async backend | 1,2,4 | F | L |
| M4 | Orchestrate Launch Modal (X1) z budget cap | 1 | D,E | S |
| M5 | Task Edit (T2) — wszystkie pola + AC repeater + requirement_refs | 1,5 | A,B | M |
| M6 | Task Create Modal (T4) — ad-hoc task | 2,5 | B | S |
| M7 | Findings Triage UI (F1 tabela + F2 detail modal + F3 bulk) | 1,2 | A,G | M |
| M8 | Decision Resolve UI (D2 modal z side-by-side docs) | 1 | A | M |
| M9 | Objective Edit (O2 szczegół z inline edit title/context/KR) | 1 | A | M |
| M10 | Task Retry (T6 modal) | 1,4 | E | S |
| M11 | Task Diff Viewer (T5) — unified diff per task | 1,4 | E | M |
| M12 | Guidelines Tab (Gu1 + Gu2) | ogólny | C | S |
| M13 | Knowledge Detail (K2) z full content rendered | 2 | E | S |
| M14 | Orchestrate Cancel + persistent job | 1,4 | F | L |
| M15 | Confirmation dialogs dla destructive actions | ogólny | H | S |

**Suma MUST effort:** 6×S + 6×M + 3×L ≈ 50-65 dni dev (1 fullstack).

### SHOULD-have — znacznie poprawia UX ale nie blokuje

| # | Feature | Scenariusz | Problem | Effort |
|---|---------|-----------|---------|--------|
| S1 | Activity Timeline (E4) | 2 | E | M |
| S2 | Projects List rozbudowa (search, sort, since-last-visit badge) | 2 | E | S |
| S3 | Bulk actions w Tasks tab (multi-select + retry/skip/delete) | 3 | G | M |
| S4 | Project Settings (P2) — edit name/goal/budget | ogólny | A | S |
| S5 | Export MD/PDF raportu (T3) + public link | audit | G | M |
| S6 | Command Palette (G3) Cmd+K | 3 | D,H | M |
| S7 | Dark mode toggle (Tailwind dark:) | developer | H | S |
| S8 | Execution Detail view (E3) | debug | C | S |
| S9 | Knowledge Re-ingest modal (K3) z wersjonowaniem | 3 | A,C | M |
| S10 | Orchestrate Runs History tab (X3, X4) | 2 | E | M |
| S11 | Objective Create Modal (O3) — manual | 1 | B | S |
| S12 | Add AC do istniejącego taska (z T2) | 5 | A,B | S |
| S13 | KR measure on-demand | ogólny | E | S |
| S14 | Workspace File Browser (W1, W2) | debug | E | M |
| S15 | Task delete + Objective delete + Knowledge deprecate | porządek | A | S |

### COULD-have — nice-to-have, odłóż

| # | Feature | Effort |
|---|---------|--------|
| C1 | Duplicate objective cross-project (O4) | M |
| C2 | Change Request Modal z LLM impact analysis (P3) | L |
| C3 | DAG view dependencies | L |
| C4 | Manual finding/decision create | S |
| C5 | Re-play LLM call | S |
| C6 | Kanban view findings | M |
| C7 | Link finding to existing task (zamiast nowego) | S |
| C8 | "Stop after this task" w live orchestrate | S |
| C9 | Notification center (zamiast toast-only) | M |
| C10 | Preset kombinacje orchestrate | S |

---

## 2. Kolejność implementacji (co odblokowuje co)

### Faza 0 — Backend contracts (API gaps before UI)
Przed UI trzeba dopisać endpointy których brakuje w API, żeby UI MUST miało do czego pisać.

**Tydzień 0-1 (S-M):**
- `PATCH /tasks/{ext}` (update wszystkich pól) — blokuje M5
- `POST /tasks/{ext}/retry {hint, model?, budget?}` — blokuje M10
- `DELETE /tasks/{ext}` — blokuje S15
- `POST /tasks/{ext}/acceptance-criteria`, `PATCH /acceptance-criteria/{id}`, `DELETE /acceptance-criteria/{id}` — blokuje M5/S12
- `PATCH /objectives/{id}` (update), `DELETE /objectives/{id}` — blokuje M9/S15
- `POST /objectives/{id}/key-results`, rozszerzony `PATCH /key-results/{id}` — blokuje M9
- `GET /tasks/{ext}/diff` (zwraca unified git diff z git_verify service) — blokuje M11
- `POST /findings/bulk-triage` — blokuje M7 bulk

**Tydzień 1-2 (L):**
- Orchestrate async:
  - Tabela `orchestrate_runs` (id, project_id, status, started_at, completed_at, config, result_summary, cancelled_by, error)
  - `POST /orchestrate/async` zwraca `run_id` od razu (FastAPI BackgroundTasks — prostsze; docelowo Celery/RQ)
  - `GET /orchestrate/{run_id}` — status
  - `GET /orchestrate/{run_id}/events` SSE — eventy live log
  - `POST /orchestrate/{run_id}/cancel`
  - `GET /projects/{slug}/orchestrate-runs` — historia
  - Blokuje M3, M14

### Faza 1 — MUST UI foundation (tydzień 2-5)
Kolejność zaprojektowana tak, żeby każdy tydzień odblokowywał sensowny demo.

**Tydzień 2:**
- M15 Confirmation dialogs pattern (common component) — wymaga wcześnie bo wszystko destructive z niego korzysta
- M1 Onboarding wizard — pozwala testować całość end-to-end dla nowego usera
- M12 Guidelines tab (najprostsze, endpoint jest)
- M13 Knowledge Detail view

**Tydzień 3:**
- M2 Project Overview rozbudowa: "Next step", "Since last visit", stats w nowej strukturze, 4 nowe przyciski akcji
- M4 Orchestrate Launch Modal
- M6 Task Create Modal

**Tydzień 4:**
- M9 Objective Edit + O2 detail
- M5 Task Edit (T2) z AC repeater, requirement_refs autocomplete
- M10 Task Retry Modal

**Tydzień 5:**
- M7 Findings Triage (najpierw pojedynczy F2, potem F1 tabela, na końcu F3 bulk)
- M8 Decision Resolve z side-by-side
- M11 Task Diff Viewer

**Tydzień 6 (critical path):**
- M3 Live Orchestrate View (X2) — potrzebuje SSE + Alpine.js dla progressive updates
- M14 Orchestrate Cancel + background job wiring

**Milestone 6 weeks:** Forge UI jest sensowny end-to-end. Marta może przejść Scen. 1 bez curl.

### Faza 2 — SHOULD (tydzień 7-10)
Dodawane w kolejności impaktu:
- S2 Projects List (szybkie) + S7 Dark mode (developer happiness)
- S1 Activity Timeline + S10 Runs History
- S6 Command Palette (rewards power-users, niska invaziveness)
- S3 Bulk actions w Tasks
- S4 Project Settings
- S9 Knowledge Re-ingest
- S5 Export MD/PDF
- S8 Execution Detail
- S14 Workspace File Browser
- reszta S11-S13, S15

### Faza 3 — COULD (odłożone)
Po feedbacku usera. Prawdopodobnie C2 (Change Request) skoczy do MUST jeśli scenariusz 5 okaże się codzienny.

---

## 3. Decyzje architektoniczne frontend

Bazując na constraintach (Jinja2 + HTMX + Tailwind CDN, no npm):

### Podstawowe wzorce
- **Server-side render pierwotny**: wszystkie widoki /ui/* dalej przez Jinja2. HTMX zwraca fragmenty HTML, nie JSON.
- **HTMX dla inline edit**: `hx-patch` + `hx-target` na tym samym elemencie. Przykład (pseudokod):
  ```html
  <span hx-patch="/api/v1/objectives/{id}"
        hx-target="this"
        hx-swap="outerHTML"
        hx-include="[name=title]"
        contenteditable>
    {{ title }}
  </span>
  ```
- **Alpine.js CDN dla client state** tam gdzie HTMX nie wystarczy:
  - Multi-select checkboxes z action bar (M7 bulk, S3)
  - Command palette (S6)
  - Live orchestrate progressive updates (M3) — Alpine słucha SSE i aktualizuje UI
  - Modale (open/close state)
- **SSE dla live updates** (M3):
  ```html
  <div hx-ext="sse"
       sse-connect="/api/v1/orchestrate/{run_id}/events"
       sse-swap="message"
       hx-target="#log-tail"
       hx-swap="beforeend"></div>
  ```
  HTMX ma built-in SSE extension — żadnych dodatkowych lib.
- **Tailwind utility-first** + 3-4 custom komponenty w `@layer components` (pill, card, modal, toast) w `base.html`.
- **Dark mode**: `class` strategy. Toggle w navbar, zapis w localStorage, Tailwind `dark:` prefixy.

### Struktura plików szablonów (propozycja)
```
templates/
  base.html                        (layout + navbar + cmdk mount + toast container)
  _partials/
    confirmation_modal.html        (reużywalny)
    toast.html
    pill.html
    breadcrumbs.html
    empty_state.html
    sse_banner.html                (analyze/plan live progress)
  index.html                       (G1 rozbudowany)
  projects/
    new.html                       (P4 wizard)
    overview.html                  (P1 — current project.html rozbity)
    settings.html                  (P2)
    _tabs/
      objectives.html
      tasks.html
      knowledge.html
      guidelines.html
      decisions.html
      findings.html
      llm_calls.html
      activity.html
      runs.html
  objectives/
    detail.html                    (O2)
    _create_modal.html
  tasks/
    report.html                    (T3 — current task_report)
    edit.html                      (T2)
    diff.html                      (T5)
    _create_modal.html
    _retry_modal.html
  findings/
    _triage_modal.html             (F2, single)
    _bulk_modal.html               (F3)
  decisions/
    _resolve_modal.html            (D2)
  knowledge/
    detail.html                    (K2)
    _reingest_modal.html
  guidelines/
    _edit_modal.html
  runs/
    live.html                      (X2)
    detail.html                    (X4)
    _launch_modal.html             (X1)
  executions/
    detail.html                    (E3)
  workspace/
    browser.html                   (W1)
    file.html                      (W2)
  llm_call.html                    (E2 — current)
```

### Routing nowych UI endpointów (w `app/api/ui.py`)
Trzeba dopisać:
```
GET  /ui/projects/new                              → P4 wizard
GET  /ui/projects/{slug}/settings                  → P2
GET  /ui/projects/{slug}/objectives/{ext}          → O2
GET  /ui/projects/{slug}/tasks/{ext}/edit          → T2
GET  /ui/projects/{slug}/tasks/{ext}/diff          → T5
GET  /ui/projects/{slug}/knowledge/{ext}           → K2
GET  /ui/projects/{slug}/runs                      → X3 (tab)
GET  /ui/projects/{slug}/runs/{run_id}             → X2 jeżeli RUNNING, X4 jeżeli zakończony
GET  /ui/projects/{slug}/workspace                 → W1
GET  /ui/projects/{slug}/workspace/files/{path:path} → W2
GET  /ui/executions/{id}                           → E3
POST /ui/projects/{slug}/change-request            → obsługuje P3 modal

Modale: fragmenty, HTMX hx-get ładuje je do mount point:
GET  /ui/projects/{slug}/_partials/task-create     → T4
GET  /ui/tasks/{id}/_partials/retry                → T6
GET  /ui/findings/{id}/_partials/triage            → F2
GET  /ui/projects/{slug}/_partials/bulk-triage     → F3
GET  /ui/decisions/{id}/_partials/resolve          → D2
GET  /ui/objectives/{id}/_partials/create          → O3
GET  /ui/objectives/{id}/_partials/duplicate       → O4
GET  /ui/knowledge/{id}/_partials/reingest         → K3
GET  /ui/projects/{slug}/_partials/orchestrate-launch → X1
GET  /ui/projects/{slug}/_partials/change-request  → P3
```

---

## 4. Effort summary

| Faza | Scope | Effort | Cumulative |
|------|-------|--------|-----------|
| 0 | Backend endpoints (MUST) | 2 tyg | 2 |
| 1 | MUST UI (M1-M15) | 4 tyg | 6 |
| 2 | SHOULD (S1-S15) | 3 tyg | 9 |
| 3 | COULD (selektywnie) | 2 tyg | 11 |

**Total MVP do demo-ready (Faza 0+1):** 6 tygodni pojedynczego dev.
**Production-ready (Faza 0+1+2):** 9 tygodni.

---

## 5. Które istniejące endpointy wystarczą, które nie

### Wystarczą bez zmian (tylko UI)
- GET /projects, POST /projects, GET /projects/{slug}/status
- POST /projects/{slug}/ingest, /analyze, /plan
- GET /projects/{slug}/objectives, /tasks, /knowledge, /decisions, /findings, /llm-calls
- GET /executions/{id}, /executions/{id}/prompt
- GET /llm-calls/{id}
- GET /projects/{slug}/tasks/{ext}/report
- POST /findings/{id}/triage
- POST /decisions/{id}/resolve
- PATCH /objectives/{id}/key-results/{pos}  (dla status+current_value)
- POST /projects/{slug}/guidelines, GET /projects/{slug}/guidelines
- POST /projects/{slug}/objectives  (create manual)
- POST /projects/{slug}/knowledge, /decisions, /tasks
- POST /tasks/{ext}/generate-scenarios

### Wymagają dodania (szczegóły w CRUD matrix)
Priorytetyzacja tych, które blokują MUST UI:

**Krytyczne (bez nich MUST niemożliwe):**
1. `PATCH /tasks/{ext}` — M5
2. `POST /tasks/{ext}/retry` — M10
3. `POST /tasks/{ext}/acceptance-criteria` + PATCH/DELETE — M5
4. `PATCH /objectives/{id}` — M9
5. `POST /objectives/{id}/key-results` + rozszerzony PATCH — M9
6. `GET /tasks/{ext}/diff` — M11
7. `POST /findings/bulk-triage` — M7 (alternatywa: pętla na froncie przez /triage N razy — slow but works; preferuje endpoint)
8. `POST /orchestrate/async` + `GET /orchestrate/{run_id}/events` SSE + cancel — M3, M14

**Ważne (SHOULD features):**
9. `GET /projects/{slug}/activity` — S1
10. `GET /projects/{slug}/orchestrate-runs` — S10
11. `GET /projects/{slug}/workspace/files` + file content — S14
12. `PATCH /knowledge/{id}` + status/version — S9
13. `PATCH /guidelines/{id}` + DELETE — S15
14. `DELETE /tasks/{ext}`, `DELETE /objectives/{id}` — S15
15. `PATCH /projects/{slug}` — S4

---

## 6. Open questions — wymagają decyzji użytkownika zanim implementacja

### Architektura
1. **Async orchestrate: FastAPI BackgroundTasks czy Celery/RQ?**
   - BackgroundTasks: prostsze, 0 zero infra (działa w jednym procesie), ale nie przeżyje restart aplikacji
   - Celery+Redis: robust, survives restarts, ale +infra
   - **Rekomendacja:** BackgroundTasks na Fazę 1 (MVP). Refactor do Celery w Fazie 3 jeśli user zgłosi „mam zawieszony run po deploy".

2. **SSE vs WebSocket dla live orchestrate?**
   - SSE: prostsze, jednokierunkowe (serwer→klient wystarczy), HTMX ma built-in extension
   - WebSocket: dwukierunkowe (cancel przez socket), overkill tutaj bo cancel to jedna akcja POST
   - **Rekomendacja:** SSE. Cancel przez normalny POST.

3. **"Since last visit" — user tracking czy localStorage?**
   - localStorage: 0 backend, per-browser (user widzi inne "since" na innym laptopie)
   - Backend user table: poprawne, ale wymaga auth
   - **Rekomendacja:** localStorage MVP. Auth + user-side state na później.

4. **Auth w ogóle?**
   - Brief milczy. Forge obecnie nie ma auth (FastAPI bez dependencies). MEMORY.md wskazuje user email (hergati@gmail.com) ale to z CLI, nie app.
   - **To blokuje:** public link do raportu (F3), multi-user "since last visit", ochrona destructive actions.
   - **Rekomendacja:** flag jako decyzja — user musi wybrać (single-user no-auth vs simple auth).

5. **Rozmiar workspace — czy UI file browser streamuje?**
   - WarehouseFlow workspace ma ~kilkadziesiąt plików, każdy <10 KB — można ładować przez zwykły GET.
   - Jeśli kiedyś będą projekty z 10 GB → pagination / lazy load.
   - **Rekomendacja:** MVP zwykły GET. Flag jako open scale-question.

### UX / scope
6. **Tablet jako target?** (brief wspomina kierownicy magazynu z tabletami z SOW WarehouseFlow)
   - **Moja interpretacja:** to są users APLIKACJI WarehouseFlow, nie users FORGE. Forge to dev tool, nie warehouse app.
   - **Potwierdzenie od usera potrzebne** — czy mam zaplanować tablet responsive dla samego Forge?

7. **Mobile Forge — out of scope czy "best effort"?**
   - **Rekomendacja:** out of scope, dodać viewport meta ale nie optymalizować. Flag.

8. **Dark mode — priorytet?**
   - Ja dałem S7 (SHOULD). Developer persona sugeruje, ale żaden scenariusz nie ginie bez niego.
   - **Rekomendacja:** SHOULD. Potwierdź.

9. **Command palette — może być Fazie 2?**
   - Niektóre user flows (Scen. 3 power-user batch) zależą od Cmd+K.
   - **Rekomendacja:** zostawić w SHOULD (S6), ale NIE odkładać za Fazę 2. Jeśli user chce power-user flow wcześniej → MUST.

10. **Change Request modal (P3) z LLM impact analysis — czy jest MVP?**
    - C2 bo wymaga nowego prompt template + endpointu + testów.
    - Scenariusz 5 (iterative refinement) bez tego jest bolesny — user musi ręcznie edytować wszystko.
    - **Rekomendacja:** start bez P3 (user może ręcznie PATCH po jednym w UI). Jeśli scenariusz 5 okaże się codzienny → podnieś do MUST w Fazie 2.

11. **Export PDF — kto generuje?**
    - Prosta droga: Markdown z T3 + print CSS (@media print) → user sam drukuje do PDF. 0 backend.
    - Druga droga: weasyprint na backend. Koszty infra.
    - **Rekomendacja:** MVP print CSS + "Eksport MD" (zwykły download .md). PDF → user sam.

12. **Edycja prompt_parser templates z UI (C — missing skills)?**
    - Stary Forge miał slash commands / skills. Nowy nie. Brief wspomina „user powinien móc edytować operational_contract text".
    - To jest GŁĘBOKI refactor — prompts są obecnie stringami w kodzie (`ANALYZE_PROMPT_TEMPLATE`, `PLAN_PROMPT_TEMPLATE`).
    - **Rekomendacja:** OUT OF SCOPE UI redesign. To jest redesign prompt management system — osobny projekt. Flag w tym dokumencie.

### Backend gaps z konsekwencjami dla architektury
13. **Gdzie trzymać cost budget per project?**
    - Obecnie `projects.config JSONB`. Trzeba ustalić klucz (np. `config.budget_usd`).
    - **Rekomendacja:** dodać kolumnę explicit `projects.budget_usd FLOAT` albo używać config JSON. Flag.

14. **"Orchestrate run" jako encja — czy `executions` ich już nie reprezentuje?**
    - `executions` to per-task. Run to kolekcja executions zainicjowana jednym `orchestrate` callem.
    - **Potrzebna nowa tabela `orchestrate_runs`** (zob. plan) żeby mieć koncept „Run-042 miał 5 tasków, 2 done, 3 fail".

15. **Diff viewer source of truth — z delivery.changes czy z git?**
    - Obecnie validation zapisuje `verification_report.git_diff` z `diff_report()` serwisu.
    - Problem: zapisuje tylko metadata (phantom/undeclared). Pełny unified diff nie jest persistent.
    - **Rozwiązanie:** T5 odczytuje fresh git diff z workspace HEAD→HEAD^N (trudne jak kilka tasków), ALBO dodać `changes.diff_content TEXT` i zapisywać podczas commit_all.
    - **Rekomendacja:** dodać kolumnę w `changes` lub osobną tabelę `change_diffs`. Flag.

---

## 7. Red flags verified (checklist z brief sekcja 10)

Przegląd każdego punktu checklisty i potwierdzenie.

- [x] **Zaadresowałem każdy z 8 punktów (A-H) z sekcji PROBLEM?**
  - A (brak edycji): M5, M9 (task edit, objective edit), Decision Resolve M8, AC edit w M5
  - B (brak manualnego dodawania): M6 Task Create, S11 Objective Create, M12 Guideline create, S12 Add AC
  - C (brak skills/customization): M12 Guidelines (minimum), S14 workspace. **Flaguję:** pełny skills-system (edit prompt templates) = OUT OF SCOPE tego redesign'u, bo to backend refactor (open question #12)
  - D (brak sensu w flow): M1 Onboarding wizard, M2 "Next step" suggestion w P1, S6 Command palette
  - E (brak wartościowej informacji): M2 Since last visit + Next step, M11 Diff viewer, S1 Activity, S14 Workspace, S5 Export
  - F (brak live operacji): M3 Live orchestrate X2, M14 Cancel + async
  - G (brak export/share): S5 Export + public link, M7 bulk triage, S3 bulk tasks
  - H (brak UX podstawowych): M15 confirmations, S7 dark mode, S6 Cmd+K, S2 Projects List filters, breadcrumbs w całości

- [x] **Odpowiedziałem na "co user robi kiedy klika X" dla każdego widoku?**
  - Tak, każdy widok w `UX_SCREENS_MAP.md` ma sekcję "Key actions" + flow interakcji w `UX_MOCKUPS.md`.

- [x] **Przeszedłem całą ścieżkę end-to-end nie pomijając kroków?**
  - Tak, 5 scenariuszy w `UX_PERSONA_AND_JOURNEYS.md` + 3 detalowane interaction flows na końcu `UX_MOCKUPS.md`.

- [x] **Rozróżniłem "edit objective" od "edit KR" od "edit task"?**
  - Tak: O2 Objective Detail (edytuje title/context/scopes/priority), inline KR edit w O2 (edytuje tekst/target/command), T2 Task Edit (edytuje instruction/AC/deps/refs). Każdy ma osobny modal/widok i osobny endpoint (PATCH /objectives/{id}, PATCH /key-results/{id}, PATCH /tasks/{ext}).

- [x] **Pokazałem jak user widzi live progress orchestracji?**
  - Tak, X2 pełny mockup w `UX_MOCKUPS.md` — pasek postępu, queue, phases panel, live log tail (SSE), timeline, cancel.

- [x] **Zaprojektowałem empty states?**
  - Tak: G1 empty (brak projektów), Tasks tab empty ("dwie drogi"), Findings tab empty (nie pokazałem explicitly ale wzorzec), Onboarding upload "pominę później".

- [x] **Uwzględniłem error states?**
  - Tak, sekcje w mockupach: P1 Analyze failed, X2 Cancel confirmation, X scenario 4 (orchestrate fail → recovery actions), Retry modal, per-error "suggested recovery".

- [x] **Każda funkcja ma uzasadnienie?**
  - Każdy mockup ma adnotację "※ UX (Scen. N, Prob. X): uzasadnienie". Każdy element w implementation plan odnosi się do scenariusza + problemu.

- [x] **Nie dodałem ficzerów "bo ładnie" bez uzasadnienia?**
  - Świadomie wyciąłem:
    - Notification center (flag: over-engineering dla MVP)
    - Tablet responsive (out of scope — open question #6)
    - Mobile (out of scope)
    - DAG graph view dependencies (C3 COULD — ładne, niekrytyczne)
    - Edycja prompt templates z UI (open question #12 — out of scope)

- [x] **Dark mode / mobile / accessibility?**
  - Dark mode: S7 (SHOULD), Tailwind `dark:` strategy.
  - Mobile: explicit OUT OF SCOPE (open question #7).
  - Accessibility: WCAG AA baseline (kontrast, focus visible, aria-labels na ikonach). Nie projektuję dedykowanego screen-reader mode — flag jeśli user chce.

---

## 8. Success criteria dla frontend-dev-agent

Implementator powinien móc, czytając te 5 dokumentów, odpowiedzieć:
- Co kliknę w G1 żeby dodać projekt? → P4 wizard.
- Jakie pola edytuję w T2? → lista w mockupie + CRUD matrix.
- Który endpoint wywołuje "Resolve decision"? → POST /decisions/{id}/resolve (istnieje).
- Gdzie żyje logika "Next step suggestion"? → backend w ui.py project_view, heurystyka: brak X → CTA.
- Jak cancel orchestrate działa? → POST /orchestrate/{run_id}/cancel → X2 toast → P1.

Jeżeli na któreś pytanie dev-agent nie znajdzie odpowiedzi — flag w Open Questions i pytaj użytkownika zanim koduje.

---

## 9. Potwierdzenie deliverables

| # | Plik | Status |
|---|------|--------|
| 1 | `UX_PERSONA_AND_JOURNEYS.md` | ✓ |
| 2 | `UX_CRUD_MATRIX.md` | ✓ |
| 3 | `UX_SCREENS_MAP.md` | ✓ |
| 4 | `UX_MOCKUPS.md` | ✓ |
| 5 | `UX_IMPLEMENTATION_PLAN.md` | ✓ (ten plik) |

Wszystkie w `forge_output/_global/`. Języka docelowy: polski (zgodnie z preferencją użytkownika).

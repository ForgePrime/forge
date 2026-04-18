# UX — CRUD matrix per encja

Cel: dla każdej encji podać czy istnieje tworzenie manualne / automatyczne / read / update / delete / bulk, czy istnieje endpoint i czy jest UI, oraz priorytet (MUST/SHOULD/COULD) i czy luka jest "UI only" czy wymaga dodania endpointu.

**Legenda:**
- API: `✓` istnieje, `✗` brak, `~` częściowy
- UI: `✓` jest, `✗` brak, `~` częściowy (tylko read albo niepełny formularz)
- Priorytet: **MUST** (blokuje core flow), **SHOULD** (znacznie poprawia UX), **COULD** (nice-to-have)
- Fix: `UI-only` (wystarczy dopisać formularz, endpoint jest), `API+UI` (trzeba dopisać endpoint), `N/A`

Wszystkie referencje do endpointów pochodzą z lektury `platform/app/api/projects.py`, `pipeline.py`, `execute.py`, `ui.py`.

---

## Project

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual | ✓ POST /projects | ✓ inline form | — | — | OK, ale wizard > inline (zob. personas) |
| Create auto | N/A | N/A | — | — | Projekty tworzy tylko user |
| Read list | ✓ GET /projects | ✓ index.html | — | — | OK |
| Read detail | ✓ GET /projects/{slug}/status | ✓ project.html | — | — | OK, statystyki ubogie |
| Update (rename, goal) | ✗ | ✗ | **SHOULD** | API+UI | Użytkownik chce skorygować goal po utworzeniu — zwłaszcza jak slug jest ładny ale goal zły |
| Delete | ✗ | ✗ | **SHOULD** | API+UI | Konieczne dla porządku — pilot projects do kasowania. Uwaga: cascade delete wszystkich encji + workspace folder |
| Archive / soft-delete | ✗ | ✗ | **COULD** | API+UI | Alternatywa dla delete, bez utraty danych |
| Duplicate to new project | ✗ | ✗ | **COULD** | API+UI | Scenariusz 5 — kopiowanie objective/plan; najpierw w zakresie objective, niepotrzebne na całym projekcie |

---

## Objective

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual | ✓ POST /projects/{slug}/objectives | ✗ | **MUST** | UI-only | Endpoint jest (zob. `create_objectives`), UI nie pokazuje formularza |
| Create auto | ✓ /analyze tworzy z dokumentów | ✓ | — | — | OK |
| Read list | ✓ GET /projects/{slug}/objectives | ✓ tab Objectives | — | — | OK |
| Read detail | ~ lista ma szczegóły | ~ | **SHOULD** | UI-only | Brak osobnego widoku szczegółu — rozpatrzeć inline expand albo dedicated `/ui/projects/{slug}/objectives/{ext}` |
| Update (title, business_context, scopes, priority, status) | ✗ | ✗ | **MUST** | API+UI | Kluczowy brak — Marta rozbijała O-003 na dwa, nie mogła |
| Delete | ✗ | ✗ | **SHOULD** | API+UI | Gdy analyze wygeneruje śmieciowy objective |
| Bulk reorder (priority) | ✗ | ✗ | **COULD** | API+UI | Drag-drop priorytetów (nice) |
| Duplicate to another project | ✗ | ✗ | **COULD** | API+UI | Scenariusz 5 |

---

## Key Result

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual (dodaj do objective) | ~ tylko wraz z objective POST | ✗ | **MUST** | API+UI | Brak endpointu „dodaj KR do istniejącego". Dziś można tylko przez POST /objectives z całą strukturą |
| Create auto | ✓ w /analyze | ✓ | — | — | OK |
| Read | ✓ w liście objectives | ✓ | — | — | OK |
| Update status / current_value | ✓ PATCH /objectives/{id}/key-results/{pos} | ✗ | **SHOULD** | UI-only | Endpoint jest — UI potrzebuje formularza (inline pencil icon) |
| Update text / kr_type / target_value / measurement_command | ✗ (PATCH tylko status + current_value) | ✗ | **MUST** | API+UI | Trzeba rozszerzyć PATCH — user chce poprawić KR text jak analyze wygenerował bez sensu |
| Delete | ✗ | ✗ | **SHOULD** | API+UI | Gdy KR wygenerowany nie ma sensu. Dziś można tylko usuwać obj cały. |
| Measure now (on-demand) | ~ tylko w orchestrate loop | ✗ | **SHOULD** | API+UI | User chce sprawdzić KR bez uruchamiania orchestrate — endpoint „measure kr N now" |

---

## Task

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual (ad-hoc task) | ✓ POST /projects/{slug}/tasks | ✗ | **MUST** | UI-only | Scenariusz 2 — Piotr dodaje 2 własne taski, nie ma UI |
| Create auto (z plan) | ✓ /plan | ✓ | — | — | OK |
| Create from finding | ✓ POST /findings/{id}/triage action=approve | ✗ | **MUST** | UI-only | Triage UI nie istnieje — kluczowa luka |
| Read list | ✓ GET /projects/{slug}/tasks | ✓ tab Tasks | — | — | OK, ale potrzebne filtry / sort / search |
| Read detail | ✓ GET /projects/{slug}/tasks/{ext} | ~ tylko report | **SHOULD** | UI-only | Task report jest DONE-centric; brak widoku „detail edit" przed wykonaniem |
| Read report (DONE state) | ✓ /report endpoint | ✓ task_report.html | — | — | OK |
| Update (instruction, requirement_refs, completes_kr_ids, scopes, depends_on, origin, type, produces) | ✗ | ✗ | **MUST** | API+UI | PATCH /tasks/{ext} nie istnieje. Bez tego iteracja niemożliwa |
| Update status manualnie (np. SKIP z reason) | ✗ | ✗ | **SHOULD** | API+UI | User chce zaskipować task którego nie zamierza wykonać |
| Delete | ✗ | ✗ | **SHOULD** | API+UI | Gdy plan wygenerował bezsensowny task |
| Retry (re-run) | ~ pośrednio przez orchestrate | ✗ | **MUST** | API+UI | Wprost: „retry T-005 z tym hintem" — endpoint `POST /tasks/{ext}/retry {hint}` |
| Bulk update status (skip, retry) | ✗ | ✗ | **SHOULD** | API+UI | Scenariusz 3 — batch |
| Reorder dependencies (DAG view) | ✗ | ✗ | **COULD** | API+UI | Graph view — ładne, ale nie krytyczne |

---

## Acceptance Criterion (AC)

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual (add AC do istniejącego task) | ✗ | ✗ | **MUST** | API+UI | Kluczowe — user dopisuje AC po zmianie scope |
| Create auto (plan) | ✓ | ✓ | — | — | OK |
| Read | ✓ w task detail | ✓ w task_report | — | — | OK |
| Update (text, scenario_type, verification, test_path, command) | ✗ | ✗ | **MUST** | API+UI | Scenariusz 1 — Marta poprawia verification=test |
| Delete | ✗ | ✗ | **SHOULD** | API+UI | Gdy AC nie ma sensu |
| Generate scenarios (skeletons) | ✓ POST /tasks/{ext}/generate-scenarios | ✗ | **SHOULD** | UI-only | Endpoint istnieje — dodać przycisk w Task Detail |
| Reorder (position) | ✗ | ✗ | **COULD** | API+UI | Drag-drop |

---

## Knowledge (source documents + specs)

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual | ✓ POST /projects/{slug}/knowledge | ✗ | **SHOULD** | UI-only | Alternatywa dla upload — wkleić text |
| Create via upload | ✓ POST /ingest | ✓ | — | — | OK |
| Read list | ✓ GET /knowledge | ~ tab Knowledge (ograniczony, 200 znaków preview) | **SHOULD** | UI-only | Obecnie nie pokazuje pełnej treści — nie da się przeczytać co wgrał |
| Read content (full) | ~ endpoint zwraca content | ✗ | **MUST** | UI-only | Trzeba widok Knowledge Detail z markdown rendering |
| Update (content, category, scopes, title, status) | ✗ | ✗ | **SHOULD** | API+UI | Re-ingest scenariusz — korekty dokumentu |
| Delete / deprecate | ✗ (status=DEPRECATED można ustawić w DB) | ✗ | **SHOULD** | API+UI | Gdy klient przysyła nową wersję |
| Version up (replace with new, keep history) | ✗ | ✗ | **COULD** | API+UI | Scenariusz 3 — re-ingest z wersjonowaniem |

---

## Guideline (project-specific rules)

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual | ✓ POST /projects/{slug}/guidelines | ✗ | **MUST** | UI-only | Endpoint jest, UI nie pokazuje w ogóle Guidelines |
| Create auto | ✗ | ✗ | — | — | Nie ma autogeneracji — guidelines to manual |
| Read | ✓ GET /guidelines | ✗ | **MUST** | UI-only | Nie ma tab'u Guidelines w UI projektu — dodać |
| Update (content, weight, scope) | ✗ | ✗ | **SHOULD** | API+UI | — |
| Delete / deprecate | ✗ | ✗ | **SHOULD** | API+UI | — |
| Share across projects (global scope) | ~ `project_id` może być NULL | ✗ | **COULD** | UI-only | DB to pozwala; UI musi mieć przełącznik „global / per-project" |

---

## Decision

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual | ✓ POST /projects/{slug}/decisions | ✗ | **SHOULD** | UI-only | User sam zapisuje decyzję architektoniczną |
| Create auto (conflicts z analyze, auto-extracted z delivery) | ✓ | ✓ pokazuje listę | — | — | OK |
| Read list | ✓ GET /decisions | ✓ tab Decisions | — | — | OK |
| Read detail | ✓ | ~ inline w liście | **SHOULD** | UI-only | Dla długich reasoning + alternatives_considered potrzebny detailed view |
| Update / Resolve | ✓ POST /decisions/{id}/resolve | ✗ | **MUST** | UI-only | Scenariusz 1 — bez tego Marta nie rozwiąże konfliktu w UI. Endpoint JEST, UI nie używa |
| Delete | ✗ | ✗ | **COULD** | API+UI | Rzadko potrzebne |
| Bulk resolve | ✗ | ✗ | **COULD** | API+UI | Side-by-side ze ignore wszystkich open questions |

---

## Finding

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create manual | ✗ | ✗ | **COULD** | API+UI | User może sam dopisać finding ręcznie — niepotrzebne często |
| Create auto (extractor + challenger) | ✓ | ✓ | — | — | OK |
| Read list | ✓ GET /findings | ✓ tab Findings | — | — | OK, ale bez filtrów |
| Read detail | ~ inline | ~ | **SHOULD** | UI-only | Dla długich description potrzebny widok szczegółu |
| Triage (approve/defer/reject) | ✓ POST /findings/{id}/triage | ✗ | **MUST** | UI-only | Najważniejsza akcja po orchestrate — endpoint JEST, UI nie używa |
| Bulk triage | ✗ | ✗ | **MUST** | API+UI | Scenariusz 2 — Piotr triaguje 4 HIGH naraz |
| Update severity / status | ✗ (triage zmienia status, poza tym nie) | ✗ | **COULD** | API+UI | Gdy user uważa że challenger przeszacował severity |
| Link to existing task (zamiast nowego) | ✗ (approve zawsze tworzy nowy task) | ✗ | **SHOULD** | API+UI | Finding może być identyczny z już istniejącym zadaniem — chce dolinkować, nie duplikować |
| Delete | ✗ | ✗ | **COULD** | API+UI | — |

---

## Execution

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create (claim task) | ✓ GET /execute / POST /orchestrate | ~ | — | — | OK przez orchestrate |
| Read list (per project) | ✓ GET /projects/{slug}/executions | ✗ | **SHOULD** | UI-only | Activity feed — użyteczne dla debugu |
| Read detail | ✓ GET /executions/{id} | ~ inline w task_report | **SHOULD** | UI-only | Detail z full prompt, validation_result, attempts |
| Read prompt (raw) | ✓ GET /executions/{id}/prompt | ✗ | **SHOULD** | UI-only | Debug — pokaz „co agent dostał" |
| Deliver | ✓ POST /execute/{id}/deliver | N/A | — | — | Server-side tylko |
| Heartbeat | ✓ | N/A | — | — | Server-side |
| Fail | ✓ | ✗ | **COULD** | UI-only | User manualnie zaznacza jako FAILED z 50-char reason |
| Challenge | ✓ POST /execute/{id}/challenge | ✗ | **COULD** | UI-only | Trigger extra challenge round dla ACCEPTED — debug tool |
| Cancel in-flight | ✗ | ✗ | **MUST** | API+UI | Scenariusz 1 — user chce zatrzymać orchestrate w środku |

---

## Orchestrate Run

(nie ma dzisiaj osobnej encji — orchestrate zwraca wynik, ale nie zapisuje „runu" jako obiektu. To lukę trzeba wypełnić dla persistent background job)

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Start async | ~ POST /orchestrate (sync) | ~ blokuje | **MUST** | API+UI | Trzeba BackgroundTask / redis queue. Endpoint zwraca `run_id` natychmiast |
| Read status live | ✗ | ✗ | **MUST** | API+UI | SSE endpoint `GET /orchestrate/{run_id}/events` |
| Read history (past runs) | ✗ | ✗ | **SHOULD** | API+UI | Tabela „orchestrate_runs" — nowa |
| Cancel | ✗ | ✗ | **MUST** | API+UI | `POST /orchestrate/{run_id}/cancel` |
| Resume (po dc/closure) | ✗ | ✗ | **COULD** | API+UI | Persistent state pozwoli |

---

## LLM Call

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create | N/A (auto) | — | — | — | Zapisywane przez serwer |
| Read list | ✓ GET /projects/{slug}/llm-calls | ✓ tab LLM-calls | — | — | OK, potrzebne filtry po purpose/cost/error |
| Read detail | ✓ GET /llm-calls/{id} | ✓ llm_call.html | — | — | OK |
| Delete | ✗ | ✗ | — | — | Audit trail — nie kasujemy |
| Re-play (odpal ten sam prompt ponownie) | ✗ | ✗ | **COULD** | API+UI | Debug — „chcę zobaczyć czy odpowiedź jest deterministyczna" |

---

## Change (file-level)

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Create | N/A (auto z delivery) | — | — | — | Server |
| Read list (per task) | ~ (w delivery.changes) | ~ task_report | **SHOULD** | UI-only | Dedykowany Diff Viewer — obecnie pokazuje tylko summary tekst |
| Read diff (rzeczywisty git diff) | ~ przez git_verify | ✗ | **MUST** | API+UI | Kluczowa luka — user nie widzi co fizycznie zmienione. Nowy endpoint `GET /tasks/{ext}/diff` zwraca unified diff |

---

## Workspace files

(nie encja DB — system plików)

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| List files | ✗ | ✗ | **SHOULD** | API+UI | File browser — user chce zobaczyć co jest w workspace |
| Read file content | ✗ | ✗ | **SHOULD** | API+UI | Read-only view, syntax highlight (Prism) |
| Edit file | ✗ | ✗ | **COULD** | API+UI | Niebezpieczne — user może popsuć; flag jako out-of-scope MVP |
| Search in files | ✗ | ✗ | **COULD** | API+UI | — |

---

## AuditLog

| Operation | API | UI | Priorytet | Fix | Uwaga |
|---|---|---|---|---|---|
| Read (activity feed) | ✗ (tabela istnieje, brak endpointu) | ✗ | **SHOULD** | API+UI | Nowy endpoint `GET /projects/{slug}/activity` — scenariusz 2 „since last visit" |

---

## Podsumowanie luk

### Endpointy do DODANIA (API+UI)

1. `PATCH /projects/{slug}` — update name/goal [SHOULD]
2. `DELETE /projects/{slug}` — cascade [SHOULD]
3. `PATCH /objectives/{id}` — update title/business_context/scopes/priority/status [MUST]
4. `DELETE /objectives/{id}` [SHOULD]
5. `POST /objectives/{id}/key-results` — dodaj nowy KR [MUST]
6. `PATCH /key-results/{id}` — rozszerzyć obecny (teraz tylko status+current_value) o text/target/command [MUST]
7. `DELETE /key-results/{id}` [SHOULD]
8. `POST /key-results/{id}/measure` — on-demand measurement [SHOULD]
9. `PATCH /tasks/{ext}` — update wszystkich pól task [MUST]
10. `DELETE /tasks/{ext}` [SHOULD]
11. `POST /tasks/{ext}/retry` — re-run z optional hint [MUST]
12. `POST /tasks/{ext}/skip` — z reason [SHOULD]
13. `POST /tasks/{ext}/acceptance-criteria` — add AC [MUST]
14. `PATCH /acceptance-criteria/{id}` — update AC [MUST]
15. `DELETE /acceptance-criteria/{id}` [SHOULD]
16. `PATCH /knowledge/{id}` — update content/scopes/category/status [SHOULD]
17. `DELETE /knowledge/{id}` / PATCH status=DEPRECATED [SHOULD]
18. `POST /knowledge/{id}/replace` — re-ingest z wersjonowaniem [COULD]
19. `PATCH /guidelines/{id}` [SHOULD]
20. `DELETE /guidelines/{id}` [SHOULD]
21. `PATCH /decisions/{id}` — beyond resolve (reasoning fix) [COULD]
22. `POST /findings/bulk-triage` — wielu naraz [MUST]
23. `POST /findings/{id}/link-to-task` — zamiast nowego taska [SHOULD]
24. `POST /orchestrate/async` — background, zwraca run_id [MUST]
25. `GET /orchestrate/{run_id}` — status [MUST]
26. `GET /orchestrate/{run_id}/events` — SSE stream [MUST]
27. `POST /orchestrate/{run_id}/cancel` [MUST]
28. `GET /projects/{slug}/orchestrate-runs` — history [SHOULD]
29. `GET /projects/{slug}/activity` — audit log [SHOULD]
30. `GET /tasks/{ext}/diff` — unified git diff per task [MUST]
31. `GET /projects/{slug}/workspace/files` — file tree [SHOULD]
32. `GET /projects/{slug}/workspace/files/{path}` — file content [SHOULD]
33. `POST /objectives/{id}/duplicate` — cross-project [COULD]

### Luki "UI-only" (endpoint istnieje, brak UI)

1. POST /objectives — create manual objective [MUST]
2. PATCH /objectives/{id}/key-results/{pos} — UI formularza [SHOULD]
3. POST /projects/{slug}/tasks — create ad-hoc [MUST]
4. POST /findings/{id}/triage — buttons approve/defer/reject [MUST]
5. POST /decisions/{id}/resolve — forma resolve [MUST]
6. POST /guidelines — create/list/view (cały tab brakuje) [MUST]
7. POST /knowledge — create (wkleić tekst, nie tylko upload) [SHOULD]
8. GET /executions/{id}/prompt — widok debug prompt [SHOULD]
9. POST /tasks/{ext}/generate-scenarios — przycisk w Task Detail [SHOULD]
10. GET /projects/{slug}/executions — activity view [SHOULD]
11. POST /decisions — create manual [SHOULD]

**Mapa priorytetowa dla implementacji** → zob. `UX_IMPLEMENTATION_PLAN.md`.

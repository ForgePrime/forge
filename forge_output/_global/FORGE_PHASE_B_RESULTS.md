# Faza B — Traceability + Auto-extraction Results

**Data:** 2026-04-17
**Zbudowane:**
- B1: kolumny `task.requirement_refs` + `task.completes_kr_ids` + plan prompt wymusza
- B2: `delivery_extractor.py` — drugi Claude call po ACCEPTED, parsuje reasoning→Decision/Finding
- B3: `GET /projects/{slug}/tasks/{ext}/report` — trustworthy DONE report

## Live test: O-004 (AppointmentBooking reminders) T-001, T-002, T-003

### Task → Requirement linking DZIAŁA
Wszystkie 11 tasków O-004 ma wypełnione requirement_refs. Przykład T-002:
```
requirement_refs: ["SRC-001 §Funkcje punkt 5", "SRC-002 punkt 9",
                   "SRC-003 §Reminder", "SRC-004 §Powiadomienia (external)"]
```
Plan sam powiązał każdy task z konkretnymi paragrafami dokumentów źródłowych.

### completes_kr_ids selektywne (nie noise)
Na 11 tasków:
- 8 z `[]` (foundation, support)
- T-005 `["KR0"]` (fallback email, ma bezpośredni wpływ na delivery rate)
- T-010 `["KR1"]` (admin audit 100%)
- T-011 `["KR0"]` (metrics confirming KR0)

### Decisions auto-extracted — 4 per task
T-002 (Reminder model) przykładowe:

**D-012 [MEDIUM] Granica blokady przypomnień ustawiona na ściśle <2h**
- Rec: block when (appointment_datetime - now) < 2h, boundary 2h00m00s traktowana jako dopuszczalna
- Why: Decyzja niejawna — instrukcja mówiła '>2h before', agent zaimplementował strict less-than bez explicit testu dla exactly 2h

**D-013 [MEDIUM] Strategia reschedule: delete pending + insert nowych rekordów zamiast update**
- Rec: DELETE WHERE status=PENDING + INSERT two new rows on every reschedule
- Why: Traci historię prób wysyłki (attempt_count, sent_at) dla anulowanych reminders. Brak audit trail dla poprzednich schedulingów.

**D-014 [MEDIUM] schedule_reminders nie commituje — odpowiedzialność delegowana do callera**
- Rec: flush-only pattern: caller (create_appointment) wykonuje commit obejmujący appointment + reminders atomowo
- Why: Decyzja architektoniczna niejawna — każdy przyszły caller musi wiedzieć że musi sam zrobić commit

**D-015 [LOW] Dwa fixed typy przypomnień: SMS_24H i EMAIL_1H — hardcoded offsets**

### Findings auto-extracted — 4 per task

**F-001 [HIGH] [gap] Brak testu dla granicy dokładnie 2h**
- Desc: Test no_reminders_for_imminent sprawdza <2h, ale brak testu dla appointment_datetime = now+2h00m00s (boundary condition). Off-by-one w warunku blokady nie zostałby wykryty.
- Fix: Dodać test parametryczny: exactly 2h → should create, 2h-1s → should not create

**F-002 [MEDIUM] [gap] Brak testu dla appointment_datetime w przeszłości**

**F-003 [MEDIUM] [gap] FK appointments→reminders nie testowana**
- Desc: Testy używają SQLite bez FK enforcement — testy tworzą Reminder z losowym uuid.uuid4() bez Appointment. Błąd FK constraint w PostgreSQL nie zostałby wykryty w CI.
- Fix: Dodać jeden test tworzący prawdziwy Appointment przed Reminder, lub włączyć PRAGMA foreign_keys=ON

**F-004 [LOW] [smell] provider_message_id w modelu bez żadnej logiki zapisu**

T-003 (Cron dispatcher) ujawnił dodatkowe:

**F-005 [HIGH] Brak migracji / indeksu na reminders.scheduled_at + status**
- Krytyczne dla wydajności (query każde 5 min, scan full table bez indeksu)

**F-006 [HIGH] Brak retry logic dla ProviderError — failed reminder nie jest ponawiane**

**F-007 [MEDIUM] Monkeypatch with_for_update w testach maskuje brak testu na PostgreSQL**

**F-008 [MEDIUM] Brak konfiguracji Celery broker/backend przez env vars — brak fallback i walidacji**

## Wartość Fazy B w liczbach

Dla 3 tasków (T-001, T-002, T-003 O-004):
- Łączny koszt: ~$2.14 ($1.95 execute + **$0.19 extract**, 9%)
- Wyciągnięte artefakty: **12 decisions + 12 findings** z reasoning (które normalnie gubią się w tekście)
- Czas extract per task: ~20-30s
- 100% automatycznie, bez human review

## Wydobyte rzeczy których nie było w delivery.changes ani delivery.assumptions

Decyzje: off-by-one w boundary, pessimistic lock strategy, hardcoded constants, flush pattern, delete-insert vs update
Findings: missing integration tests, missing DB indexes, silent config, unused fields, race condition test masked by monkeypatch

**Te wszystkie rzeczy byłyby niewidoczne w Forge pre-B.** Leżały w `reasoning` text, zapominane po 1 tygodniu.

## Bugs znalezione podczas budowy Fazy B

1. **Finding CHECK constraint** miał tylko `bug|improvement|risk|dependency|question`, ale extractor prompt specyfikował `bug|smell|opportunity|gap`. Pierwsze findings zawiodły. FIX: rozszerzony constraint.

2. **External_id kolizja** — plan per-objective generuje T-001..T-0NN w scope per-plan-call. Gdy O-004 zaplanowane po O-003, collision na T-001..T-009. FIX: auto-remap planning IDs → unique project-wide IDs w `create_tasks`.

3. **Extractor throw → rollback całej transakcji** → task DONE zniknął. FIX: try/except wokół extractor + wokół Decision/Finding inserts.

4. **Report endpoint nie rozróżnia kolizji** — 2 taski T-002 (jeden O-003 DONE, drugi O-004 DONE), endpoint zwracał pierwszy. FIX: `order_by(Task.id.desc())`.

Wszystkie 4 znalezione i fix'owane w trakcie live test — Phase A+B verification dosłownie pokazały bugi w trakcie runu.

## Status po Fazie B

| Komponent | Stan |
|-----------|------|
| Ingest → Analyze → Plan → Orchestrate | DZIAŁA |
| Phase A: test_runner + git_verify + kr_measurer | DZIAŁA, Scenario 2 potwierdził |
| Phase B: requirement_refs + completes_kr_ids | DZIAŁA, 11/11 O-004 tasków z refs |
| Phase B: auto-extract Decisions + Findings | **DZIAŁA, senior-quality outputs** |
| Phase B: DONE report endpoint | DZIAŁA |
| Challenge auto-run | **Nie zbudowane** (Faza C) |
| Workspace infra (docker-compose bootstrap) | **Nie zbudowane** (Faza C) |
| Dashboard UI | **Nie zbudowane** (Faza D) |

## Następny krok — Faza C

1. **Challenge auto-run** z Opus 4.7 po każdym ACCEPTED delivery (weryfikuje claims przez "drugi mózg")
2. **Workspace docker-compose bootstrap** — auto-start postgres/redis per projekt, connection strings w env — eliminuje "brak hasła do PG" blocker + umożliwia KR measurement na running app

Dopiero po Fazie C pełen "trustworthy autonomous engineer" — kod pisany + Forge-testowany + cross-model-challenged + services-available.

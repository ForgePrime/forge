# UX — mockupy

Konwencja:
- ASCII layout 120 kolumn.
- `[btn]` = przycisk, `[▼]` = dropdown, `[✎]` = ikona edit, `☐` = checkbox, `◉` = radio, `⎘` = duplicate, `⚠` = warning, `●` = online/aktywne
- Adnotacje `※ UX: ...` pod sekcją — uzasadnienie projektowe.
- Każdy mockup linkuje do scenariusza (`Scen. X`) i problemu (`Prob. A-H`) z brief'u.

---

## G1. Projects List `/ui/`

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚒ Forge                                                                   hergati@gmail.com   [🌙/☀]   ⌘K              │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                        │
│ Projects                                                                              [🔍 search...]  [+ New project]  │
│ ────────                                                                                                               │
│                                                                                                                        │
│ ┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐                    │
│ │ WarehouseFlow                    warehouseflow│  │ AppointmentBooking             appointmentb.│                    │
│ │ System zarządzania stanami magazynu           │  │ Rezerwacje wizyt dla kliniki                │                    │
│ │                                               │  │                                              │                    │
│ │ 🟢 Since 2h — nic nowego                      │  │ 🔴 Since 8 dni: +5 DONE  ✗2 FAILED  ⚠4 HIGH │                    │
│ │                                               │  │                                              │                    │
│ │ tasks 12  DONE 8  •  $8.42 / $50 budget      │  │ tasks 23  DONE 15  2 FAILED  $34.12 / $100  │                    │
│ │ 0 findings HIGH  •  0 decisions OPEN          │  │ 4 findings HIGH  •  1 decision OPEN         │                    │
│ │                                               │  │                                              │                    │
│ │ last: 2026-04-17 09:04 T-012 DONE             │  │ last: 2026-04-15 22:11 orchestrate failed   │                    │
│ └──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘                    │
│                                                                                                                        │
│ ┌──────────────────────────────────────────────┐                                                                       │
│ │ ➕  Stwórz nowy projekt                        │                                                                       │
│ │    Wgraj SOW i zobacz jak Forge rozkłada go   │                                                                       │
│ │    na zadania, planuje i wykonuje.            │                                                                       │
│ └──────────────────────────────────────────────┘                                                                       │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Empty state (G1, user bez projektów)
```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ Projects                                                                                   │
│                                                                                            │
│       Nie masz jeszcze projektu.                                                           │
│       Forge pomoże ci: (1) wgrać SOW, (2) rozbić na taski, (3) wykonać i zweryfikować.     │
│                                                                                            │
│                      [ + Stwórz pierwszy projekt ]                                         │
│                                                                                            │
│       Nie wiesz od czego zacząć? Zerknij na [przykładowy projekt] (placeholder data).      │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Scen. 1, Prob. D): pusta lista zamiast „you have no projects" jest barierą. Jeden duży CTA, drugorzędny link do przykładu. Zamiast inline form — wizard P4 (3 kroki).

※ UX (Scen. 2, Prob. E): "since last visit" wymaga zapisu `last_visited_at` per user. Wariant MVP: localStorage — prostszy, wystarczy. Wariant full: tabela user_visits. Flag jako open question.

---

## P4. Onboarding Wizard `/ui/projects/new`

**Krok 1/3 — Basics**
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ Nowy projekt                                                       Krok 1/3  ● ○ ○          │
│                                                                                             │
│ Slug (URL-friendly, nie zmienisz później)                                                   │
│ [warehouseflow                                             ]                                │
│     ⓘ tylko małe litery, cyfry, myślniki. To będzie część URL i nazwa folderu workspace.   │
│                                                                                             │
│ Nazwa projektu                                                                              │
│ [WarehouseFlow MVP                                         ]                                │
│                                                                                             │
│ Cel (krótki opis)                                                                           │
│ ┌───────────────────────────────────────────────────────────┐                              │
│ │ System zarządzania stanami magazynu dla klienta X.        │                              │
│ │ Auth + stock + ruchy + alerty email.                      │                              │
│ └───────────────────────────────────────────────────────────┘                              │
│                                                                                             │
│                                                            [Anuluj]  [Dalej →]              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Krok 2/3 — Dokumenty źródłowe**
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ Nowy projekt                                                       Krok 2/3  ● ● ○          │
│                                                                                             │
│ Wgraj dokumenty źródłowe (SOW, emaile od klienta, glossary, NFR)                            │
│                                                                                             │
│ ╔═══════════════════════════════════════════════════════════════════════════════════════╗  │
│ ║                                                                                       ║  │
│ ║        ⬆                                                                              ║  │
│ ║   Przeciągnij pliki tu lub [wybierz z dysku]                                          ║  │
│ ║   Akceptowane: .md, .txt (max 10MB / plik)                                            ║  │
│ ║                                                                                       ║  │
│ ╚═══════════════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                             │
│ Już wgrane:                                                                                 │
│  ✓ SOW.md (12.4 KB)                                                  [usuń]                │
│  ✓ stakeholder_email.md (3.2 KB)                                     [usuń]                │
│  ✓ glossary.md (1.8 KB)                                              [usuń]                │
│                                                                                             │
│ ⓘ Jeżeli nie masz dokumentów, możesz je dodać później albo pracować bez nich.              │
│   Wtedy Forge pominie fazę /analyze i będziesz planować ręcznie.                           │
│                                                                                             │
│                                    [← Wstecz]  [Pominę upload]  [Dalej →]                   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Krok 3/3 — Co dalej**
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ Projekt utworzony ✓                                                Krok 3/3  ● ● ●          │
│                                                                                             │
│ Następne kroki dla warehouseflow:                                                           │
│                                                                                             │
│ 1. Analyze — Claude przeczyta 3 dokumenty, wyciągnie objectives i KR.                       │
│    Szacowany czas: 2-4 min. Szacowany koszt: $1.50-$3.                                      │
│                                                                                             │
│ 2. Review objectives — poprawisz tytuły, scope, priorytety. Rozwiążesz konflikty.           │
│                                                                                             │
│ 3. Plan — wybierzesz jeden objective i Claude rozpisze go na zadania.                       │
│    Szacowany czas: 1-2 min per objective. Szacowany koszt: $0.50-$1.                        │
│                                                                                             │
│ 4. Orchestrate — Claude zacznie pisać kod w workspace, Forge sam zweryfikuje.               │
│    Szacowany czas: 5-15 min per task. Szacowany koszt: $0.40-$2 per task.                   │
│                                                                                             │
│        [Przejdź do projektu]                [ Analyze teraz → ]                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Scen. 1, Prob. D): trzystopniowy wizard eliminuje "utworzyłem projekt i nie wiem co dalej". Krok 3 to explicit next-steps z kosztami — Marta potrzebuje tego żeby ocenić budżet.

---

## P1. Project Overview `/ui/projects/{slug}`

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚒ Forge                                                           Forge / projects / warehouseflow          [🌙] ⌘K  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ WarehouseFlow MVP                                                                                        [⚙ Settings]  │
│ warehouseflow • System zarządzania stanami magazynu [✎]                                                                │
│                                                                                                                        │
│ ┌─ Od ostatniej wizyty (2h temu) ────────────────────────────────────────────────────────────────────────┐             │
│ │ ✓ 2 taski DONE (T-011, T-012)    ⚠ 1 finding HIGH nie wystriageowany    💰 $2.40 wydane (pozostało $41)│             │
│ │                                                    [Triage finding →]   [Zobacz wszystko →]            │             │
│ └─────────────────────────────────────────────────────────────────────────────────────────────────────┘               │
│                                                                                                                        │
│ ┌─ Tasks ──────┐ ┌─ Objectives ─┐ ┌─ Koszt ──────┐ ┌─ Do triage ─────┐                                                │
│ │  12  total   │ │  5           │ │  $8.42       │ │ ⚠ 1 HIGH finding│                                                │
│ │  8 DONE      │ │  2 ACHIEVED  │ │  analyze $2  │ │ 1 LOW finding   │                                                │
│ │  3 TODO      │ │  3 ACTIVE    │ │  plan $0.60  │ │ 0 OPEN decisions│                                                │
│ │  1 FAILED    │ │              │ │  execute $5  │ │                 │                                                │
│ └──────────────┘ └──────────────┘ └──────────────┘ └─────────────────┘                                                │
│                                                                                                                        │
│ ┌─ Następny krok ────────────────────────────────────────────────────────────────────────────────────────┐             │
│ │ ▶ Masz 3 taski TODO gotowe do wykonania. Najdłuższy planowany: T-013 (~12 min, ~$0.80).                │             │
│ │   [Orchestrate teraz →]        lub        [Najpierw zaplanuj O-005]                                    │             │
│ └─────────────────────────────────────────────────────────────────────────────────────────────────────┘               │
│                                                                                                                        │
│ [📥 Ingest] [🔍 Analyze] [📋 Plan: O-005 Stock endpoint ▼] [⚙ Orchestrate] [+ Change Request]           [⌘K szybciej]  │
│                                                                                                                        │
│ ╔ Objectives ╦ Tasks ╦ Knowledge ╦ Guidelines ╦ Decisions ╦ Findings (1) ╦ LLM Calls ╦ Activity ╦ Runs ╗               │
│ ╚════════════╩══════╩═══════════╩════════════╩══════════╩════════════╩═══════════╩═════════╩═════╝                   │
│                                                                                                                        │
│ [active tab content here]                                                                                              │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Scen. 2, Prob. E): "Since last visit" + "Next step" to dwa najważniejsze elementy nowego P1 vs obecnego. Marta/Piotr NATYCHMIAST wie co ma zrobić, bez analizy tabeli.

※ UX (Prob. D): 4 przyciski akcji stały się 5 z `+ Change Request`, ale "Next step" suggestion od razu wskazuje który. Przycisk `Plan` ma inline dropdown zamiast osobnego formularza.

※ UX (Prob. E): tabs mają badge z liczbą OPEN items (Findings (1), Decisions (0), itd). Activity i Runs to nowe taby.

### Loading state (Analyze w trakcie)
```
┌─ Analyze w toku ────────────────────────────────────────────────────────────────────┐
│ ▰▰▰▰▰▰▱▱▱▱ 2:14 / szac. 3:30         [Przerwij]                                    │
│                                                                                     │
│ Ostatnie logi:                                                                      │
│   09:14:03  parsing SRC-001 (12.4 KB)... OK                                         │
│   09:14:12  parsing SRC-002 (3.2 KB)... OK                                          │
│   09:14:15  parsing SRC-003 (1.8 KB)... OK                                          │
│   09:14:18  ⎘ Claude CLI started (opus-4-7-1m, budget $5)                          │
│   09:16:14  ◉ extracting objectives... found 5                                      │
│   09:16:22  ◉ extracting conflicts... found 2                                       │
│   09:16:28  ⏳ generating KRs...                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. F): SSE stream zamiast blokującego requestu. User wie że system żyje. Można przerwać.

### Error state (Analyze failed)
```
┌─ Analyze nie powiodło się ⚠ ────────────────────────────────────────────────────────┐
│ Claude CLI zwrócił odpowiedź która nie jest prawidłowym JSON.                       │
│ Szczegóły: parse_error = "Expecting value: line 1 column 5 (char 4)"                │
│                                                                                     │
│ Co możesz zrobić:                                                                   │
│  • [Zobacz pełną odpowiedź] (LLM Call #42)                                          │
│  • [Retry] (ta sama prośba)                                                         │
│  • [Retry z inną wersją modelu] — obecnie opus-4-7-1m                              │
│  • [Retry z twardszym ostrzeżeniem w prompcie] (może pomoże)                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## O1. Objectives Tab

```
Tabs: ╔ Objectives (5) ╗ Tasks (12) | Knowledge (3) | ...

Filter: [wszystkie ▼]  [ACTIVE ▼]  Sort: [priorytet ▼]                              [+ Add objective]

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ O-001  Login endpoint                                        P1   🟢 ACTIVE   [✎] [⎘] [🗑]           │
│ ─────                                                                                                │
│ Użytkownik loguje się emailem + hasłem, dostaje JWT z TTL=2h. ...                                    │
│ Scopes: backend, auth                                                                                │
│                                                                                                      │
│ Key Results:                                                                                         │
│  🟢 ACHIEVED  KR0: Login endpoint returns 200 in < 200ms   [target: 200  current: 178]  [✎] [📊]    │
│  🔵 IN_PROGR  KR1: 0 failed login attempts in test suite   [target: 0    current: 0  ]  [✎] [📊]    │
│  ⚪ NOT_START KR2: Tokens expire after 2h                  [descriptive              ]  [✎]        │
│                                                              [+ Add KR]                              │
│                                                                                                      │
│ Progress: ▰▰▰▰▰▰▱▱▱▱ 60% (3/5 tasks DONE)        [Zobacz taski →]                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. A, Scen. 1): inline `[✎]` = edit, `[⎘]` = duplicate, `[🗑]` = delete. Każdy KR ma własne [✎] (edit tekst/target) i [📊] (measure now). `[+ Add KR]` na dole.

### O2. Objective Detail `/ui/projects/warehouseflow/objectives/O-001`

```
Forge / warehouseflow / objectives / O-001                                    [⎘ Duplicate] [🗑 Delete]

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ O-001 — Login endpoint                                                                  🟢 ACTIVE    │
│                                                                                         Priority: 1  │
│                                                                                                      │
│ [✎ Title] Login endpoint                                                                             │
│ [✎ Status] ACTIVE ▼  [✎ Priority] 1 ▼                                                                │
│                                                                                                      │
│ [✎ Business context]                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│ │ Użytkownik musi móc zalogować się na system. Wymagania:                                        │  │
│ │ - email + hasło (SRC-001 §2.4)                                                                 │  │
│ │ - JWT token z TTL=2h (SRC-001 §2.5)                                                            │  │
│ │ - rate limit 5 prób/min (SRC-002 stakeholder email)                                            │  │
│ └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                      │
│ Scopes: [backend ×] [auth ×] [+ dodaj]                                                              │
│                                                                                                      │
│ ── Key Results ───────────────────────────────────────────────────────────────────────────────────   │
│                                                                                                      │
│ KR0  🟢 ACHIEVED                                                                [✎] [📊 measure] [🗑]│
│ Login endpoint returns 200 in < 200ms                                                                │
│ Type: numeric   Target: 200   Current: 178   Measurement: curl -w '%{time_total}' ... [view]        │
│ Last measured: 2026-04-17 09:04  →  178ms ✓                                                          │
│                                                                                                      │
│ KR1  🔵 IN_PROGRESS                                                             [✎] [📊 measure] [🗑]│
│ 0 failed login attempts in test suite                                                                │
│ ...                                                                                                  │
│                                                                                                      │
│ [+ Add KR]                                                                                           │
│                                                                                                      │
│ ── Related tasks ─────────────────────────────────────────────────────────────────────────────────   │
│ ✓ T-001  Login endpoint impl                    DONE   $0.82   ac 3/3                                │
│ ✓ T-002  Login tests                            DONE   $0.41   ac 5/5                                │
│ ○ T-003  Rate limiting                          TODO                                                 │
│ ✗ T-004  Session cleanup job                    FAILED $0.38   ac 1/2           [Retry →]            │
│ [+ Add task]                                   [Plan remaining tasks...]                             │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. A): wszystkie pola inline-editable. Measurement command z view-link (tooltip z pełnym tekstem).

### O3. Objective Create Modal

```
┌─ Nowy objective ────────────────────────────────────────────────────────────────────────────────┐
│ External ID [O-006      ]   (auto-generated — zmień jeśli potrzebujesz)                         │
│ Title       [                                                                                ]   │
│ Priority    [3 ▼]                                                                               │
│ Scopes      [+ dodaj]                                                                           │
│                                                                                                 │
│ Business context                                                                                │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│ │                                                                                           │   │
│ │                                                                                           │   │
│ └──────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                 │
│ Key Results (min 1):                                                                            │
│                                                                                                 │
│ KR0  Type [numeric ▼]                                                                           │
│ Text:   [                                                                                   ]   │
│ Target: [       ]   Measurement cmd: [                                                      ]   │
│                                                                                       [🗑]      │
│                                                                                                 │
│ [+ Add KR]                                                                                      │
│                                                                                                 │
│                                                              [Anuluj]  [Zapisz objective]       │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## T1. Tasks Tab (rozbudowany)

```
Tabs: Objectives | ╔ Tasks (12) ╗ | ...

Filters:  Status [ALL ▼]  Type [ALL ▼]  Origin [ALL ▼]  Scope [ALL ▼]   🔍 [search name/instr...]
Sort by:  [ID ▼]  Direction [↑]
                                                                      [+ Add task] [⎘ Duplicate plan]

┌────┬────────┬─────────────────────────────┬────────┬─────────┬────┬──────┬─────┬─────────┬────────┐
│ ☐  │ ID     │ Name                        │ Origin │ Status  │ AC │ Refs │ KRs │ Cost    │ Actions│
├────┼────────┼─────────────────────────────┼────────┼─────────┼────┼──────┼─────┼─────────┼────────┤
│ ☐  │ T-001  │ Login endpoint impl         │ O-001  │ 🟢 DONE │ 3/3│  2   │ KR0 │ $0.82   │ ⋮      │
│ ☐  │ T-002  │ Login tests                 │ O-001  │ 🟢 DONE │ 5/5│  1   │ KR1 │ $0.41   │ ⋮      │
│ ☐  │ T-003  │ Rate limiting               │ O-001  │ ⚪ TODO │ 2  │  1   │ KR0 │ —       │ ⋮      │
│ ☐  │ T-004  │ Session cleanup job         │ O-001  │ 🔴 FAIL │ 1/2│  1   │  —  │ $0.38   │ ⋮      │
│ ☐  │ T-005  │ Stock inventory endpoint    │ O-002  │ 🔵 RUN  │ 0/4│  3   │ KR2 │ $0.34↑  │ ⋮      │
│    │        │                             │        │ 2:14    │    │      │     │         │        │
│ ☐  │ T-006  │ Stock movement ledger       │ O-002  │ ⚪ TODO │ 3  │  2   │  —  │ —       │ ⋮      │
└────┴────────┴─────────────────────────────┴────────┴─────────┴────┴──────┴─────┴─────────┴────────┘

Wybrano 0 z 12  [Zaznacz widoczne]

--- gdy cokolwiek zaznaczone, nad tabelą pojawia się ---
[Wybrano 4]  [▶ Retry]  [⊙ Skip]  [🗑 Delete]  [Assign scope ▼]  [Export...]
```

※ UX (Prob. E, H): filtry + sort + search rozwiązują problem "brak search". Multi-select dla bulk ops (Scen. 3).

※ UX: `Cost ↑` przy T-005 pokazuje live cost — w trakcie orchestrate ta liczba rośnie. Ikona ⋮ to menu (Edit, Retry, Skip, Delete, View report).

### Empty state w Tasks
```
Nie masz jeszcze tasków.
Dwie drogi:
  • [ + Dodaj task ręcznie ]
  • [ 📋 Zaplanuj z objective: O-001 ▼ ]
```

### T4. Task Create Modal

```
┌─ Nowy task ────────────────────────────────────────────────────────────────────────────────────┐
│ ID        [T-013    ]  auto-gen                                                                │
│ Name      [                                                                  ]                  │
│ Type      (◉) feature  ( ) bug  ( ) chore  ( ) investigation                                   │
│ Origin    [O-002 Stock inventory ▼]   (obligatoryjne dla feature/bug)                          │
│ Scopes    [backend ×] [+ dodaj]                                                                │
│                                                                                                │
│ Instruction (markdown)                                                                         │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│ │ ## Cel                                                                                    │  │
│ │                                                                                           │  │
│ │ ## Pliki do zmiany                                                                        │  │
│ │                                                                                           │  │
│ │ ## Wskazówki                                                                              │  │
│ └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                │
│ Requirement refs  [SRC-001 §2.4 ×] [+ dodaj z Knowledge]                                       │
│ Completes KRs    [KR0 ×] [KR1 ×] [+ dodaj]  (opcjonalne)                                       │
│ Depends on       [T-005 ×] [+ dodaj]                                                           │
│                                                                                                │
│ ── Acceptance Criteria ────────────────────────────────────────────────────────────────────── │
│                                                                                                │
│ AC-0  [positive ▼]  [test ▼]                                                        [🗑]       │
│ Text: [ GET /stock zwraca 200 z listą pozycji stanu ... min 20 znaków               ]         │
│ Test path: [tests/test_stock.py::test_get_stock_ok                                  ]         │
│                                                                                                │
│ AC-1  [negative ▼]  [test ▼]                                                        [🗑]       │
│ Text: [ GET /stock bez auth header zwraca 401 ...                                   ]         │
│ Test path: [tests/test_stock.py::test_get_stock_no_auth                             ]         │
│                                                                                                │
│ [+ Add AC]                 [🪄 Generate scenarios z AC text (LLM)]                             │
│                                                                                                │
│                                  [Anuluj]  [Zapisz jako draft]  [Zapisz i retry]               │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Scen. 1, Prob. A/B): AC editor z scenario_type + verification + test_path w jednym widoku. `🪄 Generate scenarios` triggeruje istniejący endpoint.

---

## T3. Task Report (rozbudowany vs obecny)

```
Forge / warehouseflow / tasks / T-001                                  [✎ Edit] [🔁 Retry] [📄 Diff] [📥 Export MD] [🔗 Public link]

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ T-001 — Login endpoint impl                                                             🟢 DONE       │
│ type: feature  ceremony: FULL  attempts: 1  cost: $0.82                                               │
│ analyze=$0.15 · execute=$0.47 · extract=$0.08 · challenge=$0.12                                       │
│                                                                                                       │
│                 ┌────────────┐                                                                        │
│ TOC (sticky):   │  Requirements      ← sticky side-nav                                                │
│                 │  Objective+KR                                                                       │
│                 │  Tests (3/3 ✓)                                                                      │
│                 │  Challenge (PASS)                                                                   │
│                 │  Findings (0)                                                                       │
│                 │  Decisions (1)                                                                      │
│                 │  AC (3)                                                                             │
│                 │  Attempts (1)                                                                       │
│                 └────────────┘                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

[reszta jak w obecnym task_report.html — Requirements, Objective, Tests, Challenge, Findings, Decisions, AC]
+ na dole nowa sekcja:

┌─ Attempts (1) ───────────────────────────────────────────────────────────────────────────────────────┐
│ #1  ACCEPTED  exec-id 42  2026-04-17 08:14  cost $0.47  2 min 14 s                                   │
│      Prompt: [View full (18 KB)]  LLM call: [#87]                                                     │
│      Validation: all_pass=true, 4 checks passed                                                       │
│      Verification: git_diff OK, tests PASS 3/3, KR0 hit (178ms)                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. E): top-bar z [Edit] [Retry] [Diff] [Export] [Public link] — 5 najważniejszych akcji. Sticky TOC bo raport długi, user gubi się przy scrollu.

### T5. Task Diff Viewer `/ui/projects/{slug}/tasks/T-001/diff`

```
Forge / warehouseflow / tasks / T-001 / diff                    [⎘ Copy all] [📥 Download .patch]

Commit: abc123..def456  (parent: d86e4e2)                           Files changed: 4  +127 −15

┌─ Files ────────────────┐ ┌─ Diff app/auth.py ─────────────────────────────────────────────────┐
│ 📂 workspace/           │ @@ -1,5 +1,45 @@                                                     │
│ ├─ app/                 │ +from jwt import encode                                                │
│ │  ├─ auth.py  +47 −0 ● │ +from passlib.hash import bcrypt                                       │
│ │  └─ models/           │                                                                        │
│ │     └─ user.py +32 −3 │ @@ -10,0 +11,35 @@                                                    │
│ ├─ tests/               │ +def login(email: str, password: str):                                 │
│ │  └─ test_auth.py +48  │ +    user = db.query(User).filter(User.email == email).first()        │
│ └─ migrations/          │ +    if not user or not bcrypt.verify(password, user.password_hash): │
│    └─ 001_users.py +12  │ +        raise HTTPException(401)                                     │
│                         │ +    token = encode({"sub": user.id, "exp": ...}, SECRET)             │
│ [show unchanged ☐]      │ +    return {"access_token": token, "token_type": "bearer"}           │
│                         │                                                                        │
│ Search in diff...       │ [continue...]                                                          │
└─────────────────────────┘ └────────────────────────────────────────────────────────────────────┘

Nawigacja: F/G prev/next file  •  E edit w IDE  •  Esc back
```

※ UX (Prob. E): obecnie user NIE WIDZI co Claude fizycznie zmienił, tylko summary. Diff viewer to krytyczna luka.

---

## X2. Live Orchestrate View `/ui/projects/{slug}/runs/{run_id}` — PEŁNY MOCKUP

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚒ Forge                                           Forge / warehouseflow / runs / run-042        ● LIVE          ⌘K    │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Orchestrate run #042                                                              Started 09:14:03  Elapsed 12:47       │
│                                                                                                                        │
│ ▰▰▰▰▰▰▰▱▱▱ 2 / 5 tasks done              $3.14 / $50 budget  ▰▱▱▱▱▱▱▱▱▱ (6%)           [⏸ Pause] [✗ Cancel run]      │
│                                                                                                                        │
│ ┌─ Queue ─────────────────────────┐ ┌─ T-005 Stock endpoint — IN PROGRESS (2:14) ──────────────────────────────────┐  │
│ │                                 │ │                                                                                │  │
│ │ ✓ T-003 Rate limiting           │ │ Phases:                                                                       │  │
│ │   DONE  8 min 22 s  $0.61       │ │   ✓ Prompt assembled     18:32.1 KB     09:14:05                              │  │
│ │                                 │ │   ✓ Claude CLI running   ongoing        09:14:06 → ...                       │  │
│ │ ✓ T-004 Session cleanup         │ │   ○ Delivery received                                                         │  │
│ │   DONE  4 min 11 s  $0.34       │ │   ○ Validation                                                                │  │
│ │                                 │ │   ○ Phase A: tests                                                            │  │
│ │ ▶ T-005 Stock endpoint          │ │   ○ Phase B: extract                                                          │  │
│ │   RUNNING  2:14 elapsed  $0.34↑ │ │   ○ Phase C: challenge                                                        │  │
│ │                                 │ │                                                                                │  │
│ │ ○ T-006 Movement ledger         │ │ Current step: Claude CLI writing files...                                     │  │
│ │   queued                        │ │                                                                                │  │
│ │                                 │ │ Activity:                                                                     │  │
│ │ ○ T-007 Stock alerts            │ │   09:16:02  agent: Edit tool → app/api/stock.py                              │  │
│ │   queued                        │ │   09:16:14  agent: Write tool → tests/test_stock.py (new)                    │  │
│ │                                 │ │   09:16:28  agent: Bash → pytest tests/test_stock.py                         │  │
│ │                                 │ │   09:16:31  agent: pytest output: 3 passed, 1 failed                          │  │
│ │                                 │ │                                                                                │  │
│ │                                 │ │ Actions: [Skip this task] [Stop after this task]                              │  │
│ └─────────────────────────────────┘ └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                        │
│ ┌─ Live log tail ────────────────────────────────────────────────────────────────────────────────────────────────┐    │
│ │ 09:16:28 [T-005] exec/cli.stdout > running pytest tests/test_stock.py                                          │    │
│ │ 09:16:30 [T-005] exec/cli.stdout > platform linux -- Python 3.13                                               │    │
│ │ 09:16:31 [T-005] exec/cli.stdout > collected 4 items                                                           │    │
│ │ 09:16:31 [T-005] exec/cli.stdout > tests/test_stock.py::test_get_ok PASSED                                     │    │
│ │ 09:16:31 [T-005] exec/cli.stdout > tests/test_stock.py::test_post_create PASSED                                │    │
│ │ 09:16:31 [T-005] exec/cli.stdout > tests/test_stock.py::test_no_auth PASSED                                    │    │
│ │ 09:16:32 [T-005] exec/cli.stdout > tests/test_stock.py::test_patch_partial FAILED                              │    │
│ │ ☑ Auto-scroll                                                                                      [Clear]     │    │
│ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                                        │
│ ┌─ Timeline ─────────────────────────────────────────────────────────────────────────────────────────────────────┐    │
│ │ 09:14:03 ● Run started (max_tasks=5, stop_on_failure=true, budget=$50)                                         │    │
│ │ 09:14:06 ▶ T-003 claimed, exec #40                                                                              │    │
│ │ 09:22:28 ✓ T-003 DONE (cost $0.61)                                                                              │    │
│ │ 09:22:30 ▶ T-004 claimed, exec #41                                                                              │    │
│ │ 09:26:41 ✓ T-004 DONE (cost $0.34)                                                                              │    │
│ │ 09:26:42 ▶ T-005 claimed, exec #42                                                                              │    │
│ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. F): to serce odpowiedzi na "orchestrate blokuje 30 min, user patrzy na terminal". Każdy element ma powód:
- **Pasek postępu + budget** na górze = user w 1 sek. wie ogólny stan.
- **Queue** = wie co już, co teraz, co jutro.
- **Phases panel** = wie dokładnie co aktualnie Claude robi (prompt / CLI / tests / challenge).
- **Activity** = streszczone akcje agenta (nie raw stdout).
- **Live log tail** = raw stdout dla power-userów którzy chcą detal.
- **Timeline** = agregat eventów, po zakończeniu runu zostanie jako historical view (X4).
- **[Cancel run]** i **[Skip this task]** = user odzyskuje kontrolę.

※ UX (Prob. F, Scen. 2): "zamknij kartę → run leci dalej" wymaga backend async. User dostaje notification przy następnym wejściu. Implementacja: FastAPI BackgroundTasks (prosta) lub Redis queue (docelowa).

### X2 Cancel confirmation
```
┌─ Przerwać run? ─────────────────────────────────────────────────────────────────────┐
│ T-005 jest w połowie. Jeżeli przerwiesz teraz:                                      │
│  • T-005 zostanie oznaczone jako FAILED (reason: cancelled by user)                 │
│  • workspace zostanie zostawiony w stanie bieżącym (git diff zachowany)             │
│  • T-006 i T-007 nie wystartują (pozostaną TODO)                                    │
│  • koszt $3.14 już wydany (nie zwracamy)                                            │
│                                                                                     │
│  [Wróć]  [Przerwij po tym task]  [Przerwij teraz]                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### X1. Orchestrate Launch Modal

```
┌─ Uruchom orchestrate ───────────────────────────────────────────────────────────────────────────┐
│                                                                                                 │
│ Zakolejkowane taski (dependency order):                                                         │
│  1. T-003  Rate limiting              (est. 4 min, ~$0.40)                                      │
│  2. T-004  Session cleanup             (est. 3 min, ~$0.30)                                     │
│  3. T-005  Stock endpoint              (est. 12 min, ~$0.80)                                    │
│  4. T-006  Movement ledger             (est. 8 min, ~$0.60)                                     │
│  5. T-007  Stock alerts                (est. 6 min, ~$0.50)                                     │
│                                                                                                 │
│ Ustawienia:                                                                                     │
│   Max tasks          [5  ] (z 5 dostępnych)                                                    │
│   Stop on failure    ☑  (przerwij run po pierwszym FAIL)                                       │
│   Workspace infra    ☑ postgres    ☐ redis (dla Celery)                                        │
│                                                                                                 │
│   Model executor     [claude-sonnet-4-5 ▼]                                                      │
│   Model challenger   [claude-opus-4-7-1m ▼]                                                     │
│                                                                                                 │
│   Budget cap         [$25     ]  (estymacja całego runu: ~$2.60)                                │
│                       ▲ przerwij run jeśli suma wydatków przekroczy                             │
│                                                                                                 │
│ ⓘ Run będzie kontynuować w tle jeśli zamkniesz kartę. Zobaczysz notification przy powrocie.     │
│                                                                                                 │
│                                  [Anuluj]  [Zapisz jako preset]  [ ▶ Uruchom ]                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. E): estymacja czasu i kosztu zanim user odpali. Budget cap to "guard" — jeżeli coś zacznie się sypać i kosztować $100 zamiast $3, run sam się zatrzyma.

---

## F1. Findings Triage Board

```
Tabs: ... ╔ Findings (14) ╗ ...

Views:  [⊞ Tabela] [⊡ Kanban]           Filter: Severity [HIGH ▼] Source [ALL ▼] Status [OPEN ▼]
                                                                                        [🔍 search]

Zaznaczono 0 z 14
─ gdy zaznaczone ─
[▼ Bulk: Approve — utwórz taski  |  Defer  |  Reject]

┌──┬────────┬──────┬──────┬──────────────────────────────────────────┬──────────┬───────────┐
│☐ │ ID     │ Sev  │ Type │ Title                                    │ Source   │ Actions   │
├──┼────────┼──────┼──────┼──────────────────────────────────────────┼──────────┼───────────┤
│☐ │ F-007  │ 🔴H  │ bug  │ logout nie invalidate JWT w Redis        │challenger│[Triage ▼] │
│  │        │      │      │ app/auth.py:142  T-001 exec #42          │          │           │
├──┼────────┼──────┼──────┼──────────────────────────────────────────┼──────────┼───────────┤
│☐ │ F-006  │ 🔴H  │ gap  │ brak walidacji input na POST /stock      │extractor │[Triage ▼] │
│  │        │      │      │ app/api/stock.py:23                       │          │           │
├──┼────────┼──────┼──────┼──────────────────────────────────────────┼──────────┼───────────┤
│☐ │ F-005  │ 🟡M  │ smell│ duplicated validation logic              │challenger│[Triage ▼] │
│  │        │      │      │ app/api/stock.py, app/api/auth.py        │          │           │
└──┴────────┴──────┴──────┴──────────────────────────────────────────┴──────────┴───────────┘
```

### F2. Finding Detail / Triage Modal
```
┌─ F-007 — logout nie invalidate JWT w Redis ──────────────────────── 🔴 HIGH · challenger · OPEN ─┐
│                                                                                                   │
│ Description:                                                                                      │
│  Endpoint /logout zwraca 204, ale JWT token pozostaje ważny w ciągu całego TTL (2h). Powinno     │
│  być: dodać token do Redis blacklist z TTL równym pozostały czas życia.                          │
│                                                                                                   │
│ File: app/auth.py:142                                                                             │
│ Evidence:                                                                                         │
│  Test test_logout_invalidates_token failed. Wykonano requests: POST /logout → 204, potem          │
│  GET /protected z tym samym token → 200 (powinno 401).                                           │
│                                                                                                   │
│ Suggested action:                                                                                 │
│  Dodać `redis.setex(f"blacklist:{token}", ttl, "1")` w logout handler i sprawdzać w JWT middleware│
│                                                                                                   │
│ Extracted by: challenger (claude-opus-4-7-1m, cost $0.12) in execution #42                        │
│                                                                                                   │
│ ── Co z tym zrobić? ──────────────────────────────────────────────────────────────────────────   │
│                                                                                                   │
│ (◉) Approve — utwórz nowy task                                                                    │
│      Name:   [fix-f-007-logout-not-invalidate-jwt-in-redis    ]                                  │
│      Type:   (◉) bug  ( ) feature                                                                │
│      Instruction (pre-filled, możesz edytować):                                                   │
│      ┌──────────────────────────────────────────────────────────────────────────────────────┐   │
│      │ Fix: logout nie invalidate JWT w Redis                                                │   │
│      │ Suggested action: Dodać redis.setex(...) w logout + check w middleware               │   │
│      └──────────────────────────────────────────────────────────────────────────────────────┘   │
│      Link to objective: [O-001 Login endpoint ▼]                                                  │
│      Depends on: [T-001 ×] [+ dodaj]                                                              │
│                                                                                                   │
│ ( ) Approve — dolinkuj do istniejącego taska                                                      │
│      [Select task ▼]                                                                              │
│                                                                                                   │
│ ( ) Defer — wrócę do tego później                                                                 │
│      Reason: [                                                                           ]        │
│                                                                                                   │
│ ( ) Reject — nie dotyczy / false positive                                                         │
│      Reason: [                                                                           ]        │
│                                                                                                   │
│                                                              [Anuluj]  [Zastosuj triage]          │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. A): kluczowa akcja dla Marty i Piotra. Triage z możliwością pre-edycji instruction dla nowego taska oszczędza kolejny krok.

### F3. Bulk Triage Modal
```
┌─ Bulk triage — 4 findings ────────────────────────────────────────────────────────────────┐
│ Wybrano:                                                                                  │
│  • F-007 HIGH bug — logout nie invalidate JWT                                             │
│  • F-006 HIGH gap — brak walidacji input POST /stock                                      │
│  • F-004 MED smell — duplicated validation                                                │
│  • F-003 LOW opport. — add request logging                                                │
│                                                                                           │
│ Akcja dla wszystkich:                                                                     │
│ (◉) Approve all — utwórz 4 nowe taski (jeden per finding)                                 │
│     Origin for all: [O-001 ▼]  (możesz zmienić później)                                   │
│ ( ) Defer all    Reason: [                                                       ]       │
│ ( ) Reject all   Reason: [                                                       ]       │
│                                                                                           │
│                                                              [Anuluj]  [Zastosuj]         │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## D2. Decision Resolve Modal

```
┌─ D-002 — SOW mówi JWT, email mówi sesje ─────────────────────── conflict · HIGH · OPEN ─┐
│                                                                                          │
│ Issue:                                                                                   │
│  Dokument SOW (SRC-001 §2.4) precyzuje: "uwierzytelnianie JWT z TTL=2h".                │
│  Email stakeholdera (SRC-002, 2026-04-10) precyzuje: "session cookies, server-side".    │
│                                                                                          │
│ ── Dokumenty źródłowe (side-by-side) ─────────────────────────────────────────────────── │
│                                                                                          │
│ ┌─ SRC-001 §2.4 ──────────────────────┐  ┌─ SRC-002 (stakeholder email) ──────────────┐ │
│ │ "Auth implemented with JWT tokens.   │  │ "We prefer server-side sessions for       │ │
│ │  Access token TTL = 2 hours.         │  │  easier revocation and simpler mental     │ │
│ │  Refresh tokens NOT in scope."       │  │  model for our developers."               │ │
│ └──────────────────────────────────────┘  └────────────────────────────────────────────┘ │
│                                                                                          │
│ Recommendation (Claude):                                                                 │
│  JWT (SRC-001 priority — formalny SOW). Jeżeli stakeholder nalega na sesje, trzeba       │
│  zaktualizować SOW formalnie.                                                            │
│                                                                                          │
│ ── Twoja decyzja ─────────────────────────────────────────────────────────────────────── │
│                                                                                          │
│ (◉) 1. Accept recommendation (JWT)                                                       │
│ ( ) 2. JWT but with session-like revocation (Redis blacklist)                            │
│ ( ) 3. Session cookies (override SOW — wymaga potwierdzenia od klienta)                  │
│ ( ) 4. Inne — [                                                                ]         │
│                                                                                          │
│ Resolution notes (min 80 znaków):                                                        │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Wybieram JWT bo SOW ma priorytet nad luźnym email'em. Refresh tokens out of scope. │ │
│ │ Revocation w przyszłości jeśli stakeholder nalega — otwarty ticket.               │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
│ Keyboard:  1/2/3/4 wybór  · Tab textarea · Enter submit · Esc anuluj                     │
│                                                                                          │
│                                                        [Anuluj]  [✓ Resolve CLOSED]      │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Scen. 3, Prob. A/H): side-by-side dla konfliktów między dokumentami. Keyboard 1/2/3 dla power-userów Piotra.

---

## K1. Knowledge Tab + K2. Knowledge Detail

### K1 (tab)
```
Tabs: ... ╔ Knowledge (3) ╗ ...

Filter: Category [ALL ▼]  Status [ACTIVE ▼]   🔍 [search]                  [+ Add] [+ Upload] [↻ Re-ingest]

┌───────┬──────────────────────────────┬─────────────────┬──────────┬────────┬─────┬──────────┐
│ ID    │ Title                        │ Category        │ Chars    │ Status │ Ver │ Actions  │
├───────┼──────────────────────────────┼─────────────────┼──────────┼────────┼─────┼──────────┤
│SRC-001│ WarehouseFlow_SOW.md         │ source-document │ 12,400   │ ACTIVE │ 1   │ [⋮]     │
│SRC-002│ stakeholder_email_2026-04-10 │ source-document │ 3,200    │ ACTIVE │ 1   │ [⋮]     │
│SRC-003│ glossary.md                  │ source-document │ 1,800    │ ACTIVE │ 1   │ [⋮]     │
└───────┴──────────────────────────────┴─────────────────┴──────────┴────────┴─────┴──────────┘
```

### K2 (detail)
```
Forge / warehouseflow / knowledge / SRC-001                [✎ Edit] [↻ Version up] [🗑 Deprecate] [⎘ Duplicate]

SRC-001 — WarehouseFlow_SOW.md                                           source-document · v1 · ACTIVE
source: upload (filename: WarehouseFlow_SOW.md)       created: 2026-04-17 09:00 by system

Scopes: [+ add]

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ # WarehouseFlow — Statement of Work                                                                  │
│                                                                                                      │
│ ## 1. Context                                                                                        │
│ Klient X potrzebuje systemu do zarządzania stanami magazynu...                                       │
│                                                                                                      │
│ ## 2. Scope                                                                                          │
│ ### 2.1 Auth                                                                                         │
│ ### 2.2 Stock                                                                                        │
│ ...                                                                                                  │
│                                                                                                      │
│ [pełny markdown rendered]                                                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

Used by:
 - O-001 Login endpoint (requirement_refs: §2.4, §2.5)
 - O-002 Stock endpoint (requirement_refs: §3.1, §3.2)
 - 8 tasks mention this source
```

※ UX (Prob. E): obecnie Knowledge tab pokazuje tylko tytuł i pierwsze 200 znaków — user NIE WIDZI co wgrał. Full render jest MUST.

---

## Gu1. Guidelines Tab (nowy)

```
Tabs: ... ╔ Guidelines (7) ╗ ...

Scope: [ALL ▼]  Weight: [must ▼]  View: [project-specific ▼  |  global  |  oba]              [+ Add]

┌──────┬──────┬────────────┬───────────────────────────────────────┬──────┬──────────┐
│ ID   │Scope │Weight      │ Title                                 │Status│ Actions  │
├──────┼──────┼────────────┼───────────────────────────────────────┼──────┼──────────┤
│G-001 │backend│ 🔴 must   │ No SELECT *                            │ACT   │[✎][🗑]  │
│G-002 │backend│ 🟡 should │ Use pydantic schemas, not dict         │ACT   │[✎][🗑]  │
│G-003 │general│ 🔴 must   │ No hardcoded credentials               │ACT   │[✎][🗑]  │
│G-004 │tests  │ 🟡 should │ Test naming: test_<thing>_<scenario>   │ACT   │[✎][🗑]  │
└──────┴──────┴────────────┴───────────────────────────────────────┴──────┴──────────┘
```

※ UX (Prob. C): obecnie UI w ogóle NIE POKAZUJE guidelines mimo że endpoint istnieje. Kluczowa luka.

---

## E4. Activity Timeline (nowy)

```
Tabs: ... ╔ Activity ╗ ...

Filter: Entity type [ALL ▼]  Actor [ALL ▼]  Date range [ostatnie 24h ▼]   🔍 [search]

2026-04-17
─────────
 09:16:41  ● task       T-005   completed     system              cost $0.34, 3/4 AC pass
 09:16:38  🔴 finding    F-007   auto-created  challenger          HIGH bug — logout JWT
 09:16:28  🟢 execution  #42     ACCEPTED      orchestrator-cli    validation 4/4
 09:14:06  ○ execution   #42     created       orchestrator-cli    task T-005
 09:14:03  ▶ run         #042    started       hergati             5 tasks queued
 09:04:11  🟢 task       T-012   completed     system              cost $0.22
 ...

2026-04-16
─────────
 22:11:34  ✗ run         #041    FAILED        hergati             infra error: port 5433
 ...
```

※ UX (Prob. E, Scen. 2): Piotr wraca po tygodniu i chce zobaczyć "co się zmieniło". Feed chronologiczny z filtrem to minimum.

---

## W1. Workspace File Browser (nowy)

```
Forge / warehouseflow / workspace                                              [⟳ Refresh] [📦 Download zip]

┌─ Tree ─────────────────────────┐ ┌─ Preview ──────────────────────────────────────────────────────┐
│ 📂 workspace/                   │                                                                  │
│ ├─ .git/                        │  Wybierz plik żeby podejrzeć zawartość.                          │
│ ├─ app/                         │                                                                  │
│ │  ├─ __init__.py    2.1 KB    │  Filter: [   ]  Search in files: [                      ]        │
│ │  ├─ api/                      │                                                                  │
│ │  │  ├─ auth.py     3.4 KB    │                                                                  │
│ │  │  └─ stock.py    1.8 KB    │                                                                  │
│ │  ├─ models/                   │                                                                  │
│ │  └─ main.py        0.8 KB    │                                                                  │
│ ├─ tests/                       │                                                                  │
│ │  ├─ test_auth.py   5.2 KB    │                                                                  │
│ │  └─ test_stock.py  4.7 KB    │                                                                  │
│ ├─ migrations/                  │                                                                  │
│ ├─ requirements.txt  0.3 KB    │                                                                  │
│ └─ pytest.ini        0.1 KB    │                                                                  │
└─────────────────────────────────┘ └──────────────────────────────────────────────────────────────────┘
```

### W2 (file selected)
```
Forge / warehouseflow / workspace / app / api / auth.py                       [📥 Download] [📄 Diff]

Last modified: 2026-04-17 09:16 by T-001 exec #42

  1  from fastapi import APIRouter, HTTPException
  2  from jwt import encode
  3  from passlib.hash import bcrypt
  4
  5  router = APIRouter(prefix="/auth", tags=["auth"])
  ...
```

※ UX (Prob. E): user może zobaczyć co Claude utworzył bez sięgania po explorer.

---

## P3. Change Request Modal

```
┌─ Change request ──────────────────────────────────────────────────────────────────────────────┐
│                                                                                               │
│ [Nowy wymóg]  [Scope change]  [Clarification]                                                 │
│  ─────────                                                                                    │
│                                                                                               │
│ Opisz zmianę (co klient chce)                                                                 │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│ │ Klient chce forgot password flow — email z linkiem reset, ważność 1h,                    │  │
│ │ link zawiera token o charakterze one-time-use.                                           │  │
│ └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                               │
│                                                           [🔍 Wygeneruj impact analysis]      │
│                                                                                               │
│ ── Proponowane zmiany (impact analysis, $0.40) ──────────────────────────────────────────────│
│                                                                                               │
│ ☑ + Dodać Knowledge SRC-004 "Forgot password spec" (z twojego tekstu)                        │
│ ☑ + Dodać KR3 do O-001: "Password reset completed in < 3 clicks" (numeric, target 3)         │
│ ☑ + Dodać task T-008 "reset_token endpoint" (feature, depends_on=T-001, ~$0.70)              │
│ ☑ + Dodać task T-009 "email sender for reset" (feature, depends_on=T-008, ~$0.60)            │
│ ☐ ~ Zmodyfikować AC T-001: dopisać negative "login fails after password change" (odznacz)    │
│                                                                                               │
│ Szacunek kosztu wykonania tych zmian: $2.40                                                  │
│                                                                                               │
│                                            [Anuluj]  [Save draft]  [✓ Zastosuj zaznaczone]   │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Scen. 5): zamiast ręcznego rozpisywania zmian user widzi impact i odznacza co nie chce. Wymaga nowego endpointu (LLM-based impact analyzer) — zob. Open questions w implementation plan.

---

## G3. Command Palette (Cmd+K)

```
   ┌──────────────────────────────────────────────────────────────────────────────────────┐
   │  🔍 analyze_                                                                          │
   ├──────────────────────────────────────────────────────────────────────────────────────┤
   │  AKCJE w warehouseflow                                                               │
   │  ──────────────────────                                                              │
   │  ▶  Analyze documents now                                    /analyze                │
   │     Uruchom fazę analyze dla 3 dokumentów źródłowych                                 │
   │  ○  Re-analyze (force)                                                               │
   │                                                                                      │
   │  NAWIGACJA                                                                           │
   │  ─────────                                                                           │
   │     Go to Objectives tab                                     g, j                    │
   │     Go to Analysis report (last)                                                     │
   │                                                                                      │
   │  WYSZUKAJ                                                                            │
   │  ────────                                                                            │
   │     Search "analyze" w Knowledge...                                                  │
   │     Search "analyze" w tasks/instruction...                                          │
   └──────────────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. H, Scen. 3): fuzzy search + grupowanie. Skrót obok akcji uczy usera.

### Kontekstowe sugestie Cmd+K (gdy otwarty task)
```
  Plan O-001                          Last plan 2 dni temu
  Retry T-005                         Last fail 3h temu
  Resolve D-002                       HIGH · conflict
  Triage F-007                        HIGH · challenger
  Orchestrate (3 TODO)                est. ~$1.80
```

---

## P2. Project Settings

```
Forge / warehouseflow / settings                                                       [← back]

┌─ General ─────────────────────────────────────────────────────────────────────────────────────┐
│ Name    [WarehouseFlow MVP                                      ]                             │
│ Slug    warehouseflow  (nie zmienisz)                                                         │
│ Goal    [System zarządzania stanami magazynu dla klienta X...]                                │
│                                                                                          [Save]│
└───────────────────────────────────────────────────────────────────────────────────────────────┘

┌─ Models & Budgets ────────────────────────────────────────────────────────────────────────────┐
│ Executor model         [claude-sonnet-4-5 ▼]                                                  │
│ Challenger model       [claude-opus-4-7-1m ▼]                                                 │
│ Default budget / task  [$5.00 ]                                                               │
│ Warning at             [80%    ]                                                              │
│ Total project budget   [$200.00] (obecnie $8.42 wykorzystane)                                 │
│                                                                                          [Save]│
└───────────────────────────────────────────────────────────────────────────────────────────────┘

┌─ Danger zone ─────────────────────────────────────────────────────────────────────────────────┐
│ [⚠ Archive project]      Zachowa dane, ukryje z listy.                                        │
│ [🗑 Delete project]      Usuwa cascade: tasks, executions, workspace folder. Nieodwracalne.   │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Pattern: Confirmation dla destructive actions

```
┌─ Usunąć projekt "warehouseflow"? ──────────────────────────────────────────┐
│ To usunie TRWALE:                                                          │
│   • 12 tasków, 18 executions, 87 LLM calls                                 │
│   • 14 findings, 3 decisions                                               │
│   • Folder forge_output/warehouseflow/workspace/                           │
│                                                                            │
│ Wpisz slug żeby potwierdzić:                                               │
│ [                     ]   musi dokładnie = "warehouseflow"                 │
│                                                                            │
│ ⓘ Możesz zamiast tego [zarchiwizować] — ukryje z listy, zachowa dane.     │
│                                                                            │
│                                    [Anuluj]  [🗑 Usuń trwale]              │
└────────────────────────────────────────────────────────────────────────────┘
```

※ UX (Prob. H): wymuszenie wpisania slug = brak przypadkowego delete. Alternatywa archiwizacji offered.

---

## Pattern: Toast notifications (top-right)

```
                                              ┌─ ✓ T-005 oznaczony jako DONE ──┐
                                              │ 3/3 AC pass · $0.47 · 3:14     │
                                              │ [Zobacz raport]        [×]     │
                                              └────────────────────────────────┘

                                              ┌─ ⚠ Budget alert ───────────────┐
                                              │ Wydano $42 z $50 (84%)         │
                                              │ [Ustaw limit]          [×]     │
                                              └────────────────────────────────┘

                                              ┌─ ✗ Orchestrate failed ─────────┐
                                              │ Infra setup: port conflict     │
                                              │ [Zobacz szczegóły]     [×]     │
                                              └────────────────────────────────┘
```

Auto-dismiss po 4s dla success, persistent dla error/warning.

---

## Interaction flows — step by step dla 3 kluczowych

### Flow 1: First-time user → pierwszy task DONE

1. User ląduje `/ui/` (pusta). Widzi empty state `G1` + CTA **"+ Stwórz pierwszy projekt"**.
2. Klika CTA → redirect do `/ui/projects/new` (`P4`, krok 1).
3. Wypełnia slug/name/goal → **Dalej**.
4. Krok 2: drag-drop 3 pliki md. Pliki pojawiają się w liście "Już wgrane" natychmiast (client-side preview) → **Dalej**.
5. Krok 3: czyta kosztorys, klika **"Analyze teraz"**.
6. Backend: POST /projects + POST /ingest + spawn background task /analyze. Redirect do `/ui/projects/{slug}` z ?live_analyze=1.
7. `P1` pokazuje banner "Analyze w toku" (SSE z backend). Po ~3 min toast "Analyze done: 5 objectives, 2 conflicts". Banner gaśnie.
8. `P1` auto-select tab Objectives. Widzi 5 kart.
9. User klika O-001 → `O2` (edit mode już aktywny jeśli title wygląda dziwnie). Poprawia title inline → Save.
10. Wraca do `P1`, "Next step" suggestion teraz: **"Rozwiąż 2 konflikty zanim Plan"**. Klika.
11. Tab Decisions, F-001 top. Klika → `D2` modal. Reading side-by-side, wybiera opcję 1, pisze notes 80+ chars, **Resolve**.
12. Modal się zamyka. Następny decision auto-open (chain mode). Drugi resolve w 40 sek.
13. Wraca `P1`. "Next step": **"Plan O-001"**. Klika dropdown Plan, wybiera O-001, Submit.
14. SSE "Planning... 90 sec." Toast "Plan: 7 tasks". Tab Tasks auto-switch.
15. Przegląda T-001..T-007. Klika T-003 → `T2` edit → zmienia verification na "test", dodaje test_path → Save.
16. Wraca `P1`. "Next step": **"Orchestrate 7 tasks (~$4.20)"**. Klika Orchestrate btn.
17. `X1` modal. Ustawia max=3, stop_on_failure=on, budget=$15. **▶ Uruchom**.
18. Auto-redirect do `X2` (live). Watch 25 min (może zamknąć kartę — run leci dalej).
19. Toast "Run complete: 2 DONE, 1 FAILED". Klika toast → `X4` run detail.
20. Klika T-003 (FAILED) → `T3` report. Widzi per-AC, 1 fail. Klika **🔁 Retry** → `T6` modal. Wpisuje hint. **Retry now**.
21. Nowy exec, 8 min. T-003 DONE. Toast. Raport OK.

### Flow 2: Returning user → triage 4 findings w 2 min

1. User otwiera `/ui/`. `G1` kafelek ma czerwony badge **"+5 DONE, +4 HIGH"**.
2. Klika kafelek → `P1` z banerem "Since last visit".
3. Banner ma CTA **"Triage findings →"**. Klika → `F1` tab.
4. Filter auto-zastosowany: Severity=HIGH, Status=OPEN. 4 wiersze.
5. User klika checkbox header → zaznacza wszystkie 4.
6. W górnym pasku pojawia się action bar **"Wybrano 4"** z **"Approve all"**.
7. Klika **"Approve all → utwórz taski"**. Modal `F3` bulk.
8. User ustawia Origin = O-001 dla wszystkich, potwierdza.
9. Toast "4 taski utworzone: T-020..T-023". Tab Tasks pokazuje nowe.
10. Koszt tej operacji: 2 min od wejścia.

### Flow 3: Debug failed execution

1. User w `T3` (task report) T-005 status FAILED.
2. Scrolls do sekcji "Attempts". Widzi 3 attempts, wszystkie REJECTED.
3. Klika link do LLM call #89 attempt #3.
4. `E2` pokazuje full prompt + response. User widzi że Claude zwrócił opis zamiast JSON.
5. User klika breadcrumb back → `T3`.
6. Klika **🔁 Retry** → `T6`. W "dodatkowa wskazówka" wpisuje "Koniecznie odpowiedź w JSON, nie tekst".
7. **Retry now**. Execution #4 startuje. User zamyka kartę.
8. Wraca za 10 min. `G1` kafelek: "T-005 DONE".

---

Dalsze widoki (error states, loading states):
- orchestrate timeout → retry dialog
- workspace infra fail → suggested recovery (scen. 4)
- Claude API error → retry z innym modelem
- Network error → auto-retry backoff z wskaźnikiem

Te są niezbędne ale pominąłem pełne mockupy bo wzorce są powtarzalne (kolorowany banner + akcje + link do szczegółu). Frontend impl może użyć template'u `error-banner.html` z 4 warianty (info/warning/error/critical).

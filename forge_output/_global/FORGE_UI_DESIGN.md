# Forge — Design interfejsu webowego

**Status:** Wygenerowany przez agenta na podstawie FORGE_PROCESS_AND_UI_COMMAND.md
**Zasada:** Web UI = PASYWNY interfejs (monitoring, review, triage). Claude Code = AKTYWNY (execution, decisions).

---

## Hierarchia nawigacji

```
Dashboard (przegląd)
├── Pipeline View (DAG zadań)
│   └── Task Detail (szczegóły zadania)
│       ├── Execution Detail (co AI dostała/oddała)
│       │   ├── Prompt Inspector (element po elemencie)
│       │   └── Challenge Results (co challenger znalazł)
│       └── Spec Viewer (specyfikacja feature)
├── Finding Triage (kolejka odkryć)
├── Decision Center (decyzje do podjęcia)
├── Change Request (obsługa zmian)
├── Guidelines Manager (wytyczne)
├── Agent Memory Viewer (co system pamięta)
└── Audit Trail (historia)
```

---

## Widok 1: DASHBOARD

**Cel:** "Co wymaga mojej uwagi TERAZ?" Jednym spojrzeniem.
**Krok procesu:** Wszystkie — punkt wejścia.
**Dane:** `GET /status`, `GET /findings?status=OPEN`, `GET /decisions?status=OPEN`

```
┌─────────────────────────────────────────────────────────────────────┐
│  FORGE — my-project                              [Notifications: 5] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │  TASKS       │  │  FINDINGS    │  │  DECISIONS   │  │  KR     │ │
│  │  12/20 done  │  │  3 OPEN      │  │  2 waiting   │  │  O-001  │ │
│  │  ████████░░  │  │  1 HIGH ❗   │  │  1 blocking  │  │  78%    │ │
│  │  2 in-prog   │  │  2 MEDIUM    │  │              │  │  O-002  │ │
│  │  6 todo      │  │  [Triage →]  │  │  [Decide →]  │  │  30%    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘ │
│                                                                      │
│  ⚠ ATTENTION NEEDED                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ ❗ F-001 HIGH "pool.py no reconnect"              [Triage]      ││
│  │ ❗ D-014 OPEN "Redis client choice" (blocks T-005) [Decide]     ││
│  │ ⚠ T-005 delivery confidence 0.3                   [Review]     ││
│  │ ℹ K-001 updated, T-001 (DONE) affected            [Impact]     ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ACTIVE EXECUTIONS                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ T-005 "Redis caching"  IN_PROGRESS  claude-1  42min  ♥ alive   ││
│  │ T-008 "Event bus"      IN_PROGRESS  claude-2  15min  ♥ alive   ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  RECENT ACTIVITY                                                     │
│  │ 14:32  T-004 → DONE  (2 changes, 0 findings)                    │
│  │ 14:15  T-005 delivery REJECTED (reasoning too short)             │
│  │ 13:50  D-013 CLOSED by operator                                  │
│  │ 13:30  F-001 created (HIGH, pool.py)                             │
└─────────────────────────────────────────────────────────────────────┘
```

**Akcje:** Click card → detail view. Click attention item → relevant view. Click execution → Execution Detail.

---

## Widok 2: PIPELINE VIEW (DAG)

**Cel:** Graf zadań z dependencies, statusami, ścieżką postępu.
**Krok procesu:** 5 (Planowanie), 6 (Implementacja).
**Dane:** `GET /tasks`

```
┌────────────────────────────────────────────────────────────────────┐
│  PIPELINE — my-project    Objective: [All ▼]        [Zoom +/-]    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ■ DONE  ◆ IN_PROGRESS  □ TODO  ✕ FAILED  ○ SKIPPED              │
│                                                                    │
│       ┌─────┐     ┌─────┐                                        │
│       │T-001│────→│T-003│──┐                                     │
│       │■DONE│     │■DONE│  │  ┌─────┐     ┌─────┐               │
│       └─────┘     └─────┘  └→│T-005│────→│T-008│               │
│                            ┌→│◆PROG│     │□TODO│               │
│       ┌─────┐     ┌─────┐ │ │42min│     │     │               │
│       │T-002│────→│T-004│─┘ └─────┘     └─────┘               │
│       │■DONE│     │■DONE│                                       │
│       └─────┘     └─────┘                                       │
│                                                                    │
│  ─────────────────────────────────────────────────────────────── │
│  SELECTED: T-005 "Redis caching" [feature] origin: O-001        │
│  AC: 3 (1 pos, 1 neg, 1 edge)  Deps: T-003 ✓, T-004 ✓          │
│  [Open Detail →]  [Skip]  [Re-assign]                             │
└────────────────────────────────────────────────────────────────────┘
```

**Akcje:** Click node → bottom panel. Double-click → Task Detail. Objective filter → shows subset.

---

## Widok 3: TASK DETAIL

**Cel:** Pełne szczegóły zadania — instruction, AC, spec, executions.
**Krok procesu:** 5-8.
**Dane:** `GET /tasks/{id}`, `GET /executions?task={id}`

```
┌────────────────────────────────────────────────────────────────────┐
│  T-005 "setup-redis-adapter"  [feature]  Status: IN_PROGRESS      │
│  Origin: O-001  Scopes: [backend]                                  │
├────────────────────────────────────────────────────────────────────┤
│  [Instruction] [AC & Scenarios] [Executions] [Changes] [Decisions]│
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INSTRUCTION:                                                      │
│  Create cache/redis.py implementing StorageAdapter protocol.       │
│  Follow pattern from db/pool.py. Add REDIS_URL to config.py.      │
│                                                                    │
│  EXCLUSIONS: Do NOT modify db/pool.py                              │
│  PRODUCES: CacheAdapter, GET /api/cache/stats                      │
│  DEPS: T-003 (DONE) ✓, T-004 (DONE) ✓                            │
│  SPEC: SPEC-003 "Redis Caching" [View →]                          │
│                                                                    │
│  AC & SCENARIOS:                                                   │
│  AC-0 [positive] [test] ✓  "Given valid REDIS_URL..."             │
│  AC-1 [negative] [test] ✓  "Given Redis unavailable..."           │
│  AC-2 [edge]     [test] ✓  "Given corrupt JSON..."                │
│  ──────────────────────────                                        │
│  TS-001 [G-001] "StorageAdapter compliance"        ✓               │
│  TS-002 [R-002] "Redis SPOF mitigation"            ✓               │
│                                                                    │
│  [Challenge]  [Skip]  [Re-open]                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 4: EXECUTION DETAIL (kluczowy widok)

**Cel:** Co AI DOKŁADNIE dostała i co DOKŁADNIE oddała. Pełny audit.
**Krok procesu:** 6-8.
**Dane:** `GET /executions/{id}`, `GET /executions/{id}/prompt`

```
┌────────────────────────────────────────────────────────────────────┐
│  EXECUTION #42 — T-005    Attempt: 2/5    ACCEPTED                 │
│  Agent: claude-1  Duration: 42 min                                 │
├──────────────────┬──────────────────┬──────────────────────────────┤
│  PROMPT (left)   │  DELIVERY (mid)  │  VALIDATION (right)          │
├──────────────────┼──────────────────┼──────────────────────────────┤
│                  │                  │                               │
│ ■ Reputation     │ REASONING:       │ reasoning:          PASS     │
│   "developer"    │ Added Redis...   │   length: 284 ✓             │
│                  │ redis-py chosen  │   file_ref: ✓               │
│ ■ Command        │ because...       │   no_reject: ✓              │
│   (from Agent-A) │                  │                               │
│                  │ AC EVIDENCE:     │ ac_evidence:                  │
│ ■ Skills         │ AC-0: PASS ✓    │   [0]: PASS ✓               │
│   impact-aware   │   "3ms avg"     │   [1]: PASS ✓               │
│   contract-first │ AC-1: PASS ✓    │   [2]: PASS ✓               │
│                  │   "200 OK DB"   │                               │
│ ■ G-001 MUST ✓   │ AC-2: PASS ✓    │ composition: PASS ✓         │
│ ✕ G-007 excluded │   "evicted"     │   negative AC passed         │
│   (scope)        │                  │                               │
│ ■ K-003 ✓        │ ASSUMPTIONS:     │ scenarios: 5/5 PASS         │
│ ✕ K-012 excluded │ Redis localhost  │                               │
│   (budget)       │   UNVERIFIED ⚠   │ anti_patterns: PASS         │
│                  │                  │   duplicates: ✓              │
│ ■ Agent memory   │ IMPACT:          │   placeholders: ✓            │
│   "forgot .env"  │ checked: 2 files │                               │
│                  │ NOT: reports.py  │ OVERALL: ACCEPTED             │
│ ■ Op. Contract   │                  │                               │
│   (always)       │ CONFIDENCE: 0.7  │ KR-1: 4/7 (updated)         │
├──────────────────┴──────────────────┴──────────────────────────────┤
│  CHALLENGE (bottom)                                                │
│  Challenger: claude-2   Verdict: NEEDS_REWORK                      │
│  F-003 [HIGH] AC-3 test uses mock not real Redis failure           │
│  F-004 [PASS] CacheAdapter implements all 6 methods                │
│  [Approve Findings]  [Reject Finding]  [Re-challenge]              │
└────────────────────────────────────────────────────────────────────┘
```

**Kluczowe:** LEFT panel = co AI dostała (z prompt_elements, each clickable). CENTER = co oddała. RIGHT = co przeszło/nie przeszło. BOTTOM = challenge results.

---

## Widok 5: PROMPT INSPECTOR

**Cel:** Element po elemencie — skąd, dlaczego, co excluded i dlaczego.
**Dane:** `GET /executions/{id}/prompt`

```
┌────────────────────────────────────────────────────────────────────┐
│  PROMPT INSPECTOR — Execution #42                                  │
│  Total: 48.3 KB / 50 KB    Elements: 10/12                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INCLUDED (10):                                                    │
│  P0  reputation_frame  "developer"              0.4 KB             │
│      Source: micro_skills.reputation_developer                     │
│      Reason: reputation_frame (always)          [Expand ▼]         │
│                                                                    │
│  P1  must_guideline    G-001 "StorageAdapter"   0.8 KB             │
│      Source: guidelines.G-001                                      │
│      Reason: scope_match:backend                [Expand ▼]         │
│      Scope: task=[backend,general] element=backend ✓               │
│                                                                    │
│  P2  knowledge         K-003 "Redis config"     1.2 KB             │
│      Source: knowledge.K-003                                       │
│      Reason: explicit_reference                 [Expand ▼]         │
│                                                                    │
│  EXCLUDED (2):                                                     │
│  ✕  G-007 "React hooks"                        0.6 KB             │
│     Exclusion: scope_mismatch:frontend∉[backend,general]           │
│                                                                    │
│  ✕  K-012 "Perf benchmarks"                    3.8 KB             │
│     Exclusion: budget_exceeded:52.1KB>50KB                         │
│     Budget: used=48.3KB, element=3.8KB, would_exceed=true          │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 6: SPEC VIEWER

**Cel:** Specyfikacja feature — input/output/rules/edge_cases/acceptance.
**Krok procesu:** 3 (tworzenie), 5 (source dla AC).

```
┌────────────────────────────────────────────────────────────────────┐
│  SPEC: Settlement Report (K-015)         Status: APPROVED          │
│  Linked: O-001  Tasks: T-005, T-006                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INPUT:  BQ rpt_daily_estimation, invoices, Firestore buy_runs     │
│  OUTPUT:                                                           │
│  │ beginning_balance  │ SUM(prior_period.ending_balance)           │
│  │ newly_submitted    │ SUM(invoices WHERE period=current)         │
│  │ collected          │ SUM(settlements WHERE period=current)      │
│  │ ending_balance     │ beginning + newly - collected              │
│                                                                    │
│  EDGE CASES:                                                       │
│  EC1: settlement_date < purchase_date → include in current         │
│  EC2: no data for period → return 0, not NULL                      │
│  EC3: partial settlement → exclude from collected                  │
│                                                                    │
│  ACCEPTANCE: Cross-check SUM(newly) == ITRP gross. Owner: Tuan    │
│                                                                    │
│  [Approve]  [Request Changes]  [Add Edge Case]                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 7: FINDING TRIAGE

**Cel:** Kolejka odkryć do decyzji operatora. 1-click actions.

```
┌────────────────────────────────────────────────────────────────────┐
│  FINDING TRIAGE — 3 OPEN                    [Sort: Severity ▼]     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  F-001 [HIGH] [bug] "pool.py no reconnect"                        │
│  Source: T-005  File: db/pool.py:78                                │
│  Evidence: "no try/except on connection acquisition"               │
│  [Approve → Task]  [Defer]  [Reject]                               │
│                                                                    │
│  F-003 [HIGH] [challenge] "AC-3 test uses mock"                    │
│  Source: Challenge T-005  Claim: "Redis down fallback"             │
│  Evidence: "test uses mock.patch, not docker stop"                 │
│  [Approve → Task]  [Defer]  [Reject]                               │
│                                                                    │
│  F-002 [MEDIUM] [risk] ".env.example missing REDIS_URL"            │
│  Source: T-005 propagation_check                                   │
│  [Approve → Task]  [Defer]  [Reject]                               │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 8: DECISION CENTER

**Cel:** Decyzje wymagające rozstrzygnięcia.

```
┌────────────────────────────────────────────────────────────────────┐
│  DECISION CENTER — 2 OPEN                                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  D-014 [OPEN] [implementation] ⚠ BLOCKS T-005                     │
│  "Redis client: redis-py vs aioredis"                              │
│  AI says: redis-py (aioredis deprecated since 2023)                │
│  Impact if wrong: migration cost later                             │
│  [Accept AI]  [Override]  [Defer]                                  │
│                                                                    │
│  D-015 [OPEN] [clarification]                                      │
│  "'Add caching' — read-only or read-write?"                        │
│  AI says: read-only (write-through needs event bus)                │
│  User loses: stale data up to TTL after writes                     │
│  [Accept AI]  [Override: "read-write"]  [Defer]                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 9: CHANGE REQUEST

```
┌────────────────────────────────────────────────────────────────────┐
│  CHANGE REQUEST                                                    │
├────────────────────────────────────────────────────────────────────┤
│  WHAT CHANGED:                                                     │
│  + K-026 NEW: "PDF export"                                         │
│  ~ K-001 UPDATED: "5 statuses" (was: 3)                           │
│  - K-010 DEPRECATED: "CSV export"                                  │
│                                                                    │
│  IMPACT:                                                           │
│  T-001 (DONE) implemented K-001 v1 → NEEDS REWORK                 │
│  T-004 (TODO) references K-010 → SHOULD SKIP                      │
│  NEW TASK needed for K-026 (PDF export)                            │
│                                                                    │
│  [Apply Changes]  [Reject]  [Defer]                                │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 10: GUIDELINES MANAGER

```
┌────────────────────────────────────────────────────────────────────┐
│  GUIDELINES         [Project ▼] [Global ▼]   [+ Add]              │
├────────────────────────────────────────────────────────────────────┤
│  MUST (4):                                                         │
│  G-001 [backend] "StorageAdapter Protocol"  checked: 8/12 tasks    │
│  G-010 [backend] "No hardcoded config"      checked: 8/12 tasks    │
│  G-OP  [general] "Operational Contract"     checked: 12/12 ALWAYS  │
│                                                                    │
│  SHOULD (3):                                                       │
│  G-005 [general] "Composition over inheritance"  never checked ⚠   │
│         Reason: budget excluded in 12/12 tasks                     │
│         [Promote to MUST]  [Deprecate]                             │
│                                                                    │
│  COMPLIANCE:                                                       │
│  G-001 MUST   │ 8/12 checked │ 4 unchecked (frontend scope)       │
│  G-005 SHOULD │ 0/12 checked │ always budget excluded              │
│  G-OP  MUST   │ 12/12 ✓     │ mandatory_always                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 11: AGENT MEMORY VIEWER

```
┌────────────────────────────────────────────────────────────────────┐
│  AGENT MEMORY — claude-1           Trust Score: 0.72               │
├────────────────────────────────────────────────────────────────────┤
│  FILES KNOWN (12):                                                 │
│  config.py   "INI-style, [database],[cache]"  T-005  STALE ⚠      │
│  redis.py    "StorageAdapter impl"            T-005  current       │
│                                                                    │
│  MISTAKES LEARNED (2):                                             │
│  "Forgot .env.example after config change"  × 2 (T-003, T-007)    │
│  Fix: "Always update .env.example"          [Clear if resolved]    │
│                                                                    │
│  UNVERIFIED ASSUMPTIONS (1):                                       │
│  "Max 20 concurrent users" MEDIUM  T-005  [Verify] [Mark stale]   │
│                                                                    │
│  DECISIONS MADE (3):                                               │
│  "redis-py over aioredis" T-005 D-008                              │
│  "pgbouncer pattern" T-003 D-004                                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Widok 12: AUDIT TRAIL

```
┌────────────────────────────────────────────────────────────────────┐
│  AUDIT TRAIL    [Entity: All ▼]  [Actor: All ▼]  [Date: today]    │
├────────────────────────────────────────────────────────────────────┤
│  14:32  task.completed    T-004  claude-1   DONE [Details →]       │
│  14:15  execution.reject  #42   system      reasoning<100         │
│  13:50  decision.closed   D-013 operator    "Firestore"           │
│  13:30  finding.created   F-001 claude-1    HIGH pool.py          │
│  13:15  execution.created #42   system      48.3KB prompt         │
│  [Load more...]                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Ujawnione braki w UI

1. **Challenge endpoint nie w MVP** — BOTTOM panel w Execution Detail nie będzie działać w MVP
2. **Agent Memory to Tier 2** — widok 11 będzie pusty w MVP
3. **Change Request brak endpointu** — widok 9 wymaga kilku API calls zamiast jednego
4. **Spec approval workflow** — knowledge nie ma DRAFT/APPROVED status, Spec Viewer nie może pokazać workflow
5. **Micro-skills i reputation framing** — Tier 2, LEFT panel w Execution Detail nie pokaże tych sekcji w MVP

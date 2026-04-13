# Forge V2 — Plan przebudowy: od interpretera do kompilatora

**Data:** 2026-04-13
**Autor:** Forge AI + Lukasz Krysik
**Status:** DRAFT — awaiting review

---

## 1. Diagnoza fundamentalna

### 1.1 Problem centralny

Forge V1 jest **interpreterem** — daje AI instrukcje tekstowe (SKILL.md) i ufa, że AI je wykona.
Forge V2 musi być **kompilatorem** — produkuje widoczne, weryfikowalne artefakty na każdym kroku.

### 1.2 Pięć strukturalnych wad V1

| # | Wada | Dowód | Konsekwencja |
|---|------|-------|--------------|
| W-1 | **Nieprzejrzystość promptu** | context.py składa prompt w tle, użytkownik nie widzi wyniku | Nie wiadomo co AI dostaje, co obcięte, co pominięte |
| W-2 | **Miękka egzekwucja** | Każdy wymóg to checkpoint (WARNING), `--force` omija gates i changes | AI może pominąć dowolny krok bez konsekwencji |
| W-3 | **Brak testowania przed implementacją** | Scenariusze testowe nie istnieją na etapie planowania | Weryfikacja = AI sprawdza swój własny kod = student ocenia własny egzamin |
| W-4 | **Utrata informacji między fazami** | SHOULD guidelines obcinane po cichu przy >80% budżetu, reasoning_trace = `"auto-complete"` | Kontekst degraduje się z każdym krokiem |
| W-5 | **Brak pętli zwrotnej** | Odkrycia AI podczas execution nie mają strukturalnego mechanizmu powrotu do pipeline | Informacje i problemy giną |

### 1.3 Dowody z forge_output/

- **Changes C-001 do C-005** (forge-web): identyczne opisy dla 5 różnych plików — skopiowany tekst
- **Reasoning traces**: jednoelementowe tablice `{"step": "auto-complete", "detail": "..."}` — placeholder, nie myślenie
- **AC verification**: szablon `"AC1: [kryterium] — PASS"` bez dowodów (brak outputu testów, logów, screenshotów)
- **Testy Forge**: 45% modułów (12/22) bez testów. Zero testów end-to-end. Zero testów behawioralnych.
- **Tool call baseline** (t040): 33-50% failure rate na create/update operations

---

## 2. Architektura V2

### 2.1 Nowy przepływ

```
CEL/IDEA/PLAN
      │
      ▼
┌── COMPILE ──────────────────────────────────────────────────────┐
│ Wejście: task + guidelines + dependencies + risks + objectives  │
│ Wyjście: Task Briefing (widoczny, persystentny dokument)        │
│          + Verification Scenarios (adversarial)                  │
│          + Metody weryfikacji per AC                              │
│ Artefakt: forge_output/{project}/briefings/T-NNN.json           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌── APPROVE ──────────────────────────────────────────────────────┐
│ Użytkownik widzi DOKŁADNIE co AI dostanie                       │
│ Może: zatwierdzić / zmodyfikować / odrzucić                     │
│ HARD BLOCK: bez zatwierdzenia execution nie startuje            │
│ Artefakt: approved_at timestamp + approved_by w briefing.json   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌── EXECUTE ──────────────────────────────────────────────────────┐
│ AI dostaje zatwierdzony briefing                                │
│ Automatyczne nagrywanie:                                        │
│   - execution_trace.json: każdy tool call z timestampem         │
│   - decisions: z pełnym reasoning (nie opcjonalne)              │
│   - findings: odkrycia → triage queue                           │
│ AI NIE oznacza zadania jako DONE                                │
│ Artefakt: forge_output/{project}/traces/T-NNN.json             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌── VERIFY (NIEZALEŻNE) ──────────────────────────────────────────┐
│ Oddzielny proces weryfikacji (nie ta sama AI)                   │
│ Sprawdza:                                                       │
│   1. Gates (pytest, lint, type-check) — z dowodami (logi)       │
│   2. Scenarios (każdy z V-NNN z raportem PASS/FAIL + evidence)  │
│   3. Guidelines compliance (MUST = hard block, SHOULD = raport) │
│   4. Briefing vs output diff (co planowane vs co zrobione)      │
│   5. Quality checks (reasoning ≠ placeholder, AC ma dowody)    │
│ DOPIERO po przejściu → DONE                                     │
│ Artefakt: forge_output/{project}/verifications/T-NNN.json      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌── FEEDBACK ─────────────────────────────────────────────────────┐
│ Findings z execution → Triage Queue                             │
│ Użytkownik: approve (→ nowe zadanie) / defer / reject           │
│ Approved findings → pełny kontekst → nowe zadanie w pipeline   │
│ Artefakt: forge_output/{project}/findings.json                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Nowe moduły

| Moduł | Plik | Odpowiedzialność |
|-------|------|-----------------|
| **Briefing Compiler** | `core/briefing.py` | Kompiluje task → briefing document ze wszystkimi źródłami |
| **Scenario Generator** | `core/scenarios.py` | Generuje adversarial test scenarios z ryzyk, guidelines, zależności |
| **Finding System** | `core/findings.py` | Rejestruje odkrycia AI, triage queue, konwersja na zadania |
| **Verification Engine** | `core/verification.py` | Niezależna weryfikacja output vs specification |
| **Execution Tracer** | `core/tracer.py` | Automatyczne nagrywanie execution trace |
| **Observatory API** | `forge_web/api/` | FastAPI backend dla Web UI |
| **Observatory Frontend** | `forge_web/frontend/` | React frontend — centrum kontroli |

### 2.3 Zmienione moduły

| Moduł | Zmiana |
|-------|--------|
| `core/pipeline.py` | Usunięcie `--force`. Dodanie `--override --reason "..."`. Briefing approval jako warunek execution. Verification jako warunek completion. |
| `core/changes.py` | Walidacja jakości: reasoning_trace ≠ "auto-complete", summary ≠ identyczne dla wielu plików |
| `core/gates.py` | Gates produkują evidence (pełny output) przechowywany w verification report |
| `core/llm/context.py` | Przezroczystość: sekcja "EXCLUDED" z listą obciętych elementów i powodami |
| `skills/next/SKILL.md` | Nowy flow: compile briefing → approve → execute → verify (nie self-assess) |
| `skills/plan/SKILL.md` | Generowanie scenarios per task na etapie planowania |

---

## 3. Szczegóły modułów

### 3.1 Briefing Compiler (`core/briefing.py`)

#### Cel
Kompilacja kompletnego, czytelnego dokumentu (Task Briefing) ze WSZYSTKICH źródeł danych Forge. Użytkownik widzi dokładnie co AI dostanie.

#### Interfejs

```python
# CLI
python -m core.briefing compile {project} {task_id}     # Kompiluj briefing
python -m core.briefing show {project} {task_id}         # Pokaż briefing (human-readable)
python -m core.briefing approve {project} {task_id}      # Zatwierdź briefing
python -m core.briefing modify {project} {task_id} --data '{...}'  # Modyfikuj sekcję
python -m core.briefing diff {project} {task_id}         # Diff: briefing vs actual output
python -m core.briefing contract                         # Pokaż kontrakt danych

# API
GET  /api/tasks/{task_id}/briefing          # Pobierz briefing
POST /api/tasks/{task_id}/briefing/approve  # Zatwierdź
POST /api/tasks/{task_id}/briefing/modify   # Modyfikuj
GET  /api/tasks/{task_id}/briefing/diff     # Diff vs output
```

#### Struktura briefingu

```json
{
  "task_id": "T-005",
  "compiled_at": "2026-04-13T14:32:00Z",
  "approved_at": null,
  "approved_by": null,
  "version": 1,
  
  "sections": {
    "instruction": {
      "content": "Implement Redis caching layer for API responses...",
      "sources": [
        {"type": "task", "id": "T-005", "field": "instruction"}
      ]
    },
    
    "acceptance_criteria": [
      {
        "id": "AC-1",
        "criterion": "Redis client configured via env vars",
        "verification_method": "Test with REDIS_URL=valid, REDIS_URL=invalid, REDIS_URL=missing",
        "sources": [{"type": "task", "id": "T-005", "field": "acceptance_criteria[0]"}]
      }
    ],
    
    "verification_scenarios": [
      {
        "id": "V-001",
        "title": "Cache hit returns cached data under 10ms",
        "type": "happy_path",
        "derived_from": "instruction",
        "verification_method": "pytest test_cache_hit with timing assertion",
        "pass_criteria": "Response time < 10ms for cached key"
      },
      {
        "id": "V-003",
        "title": "Redis unavailable — graceful degradation",
        "type": "failure_mode",
        "derived_from": "risk R-002",
        "verification_method": "Stop Redis, send request, verify 200 response from DB",
        "pass_criteria": "API returns correct data without Redis, logs warning"
      },
      {
        "id": "V-006",
        "title": "Corrupt cache entry handling",
        "type": "adversarial",
        "derived_from": "adversarial_analysis",
        "verification_method": "Inject invalid JSON into Redis key, send request",
        "pass_criteria": "Corrupted entry evicted, fresh data from DB, no crash"
      }
    ],
    
    "guidelines": {
      "must": [
        {
          "id": "G-001",
          "content": "StorageAdapter Protocol is the single storage abstraction",
          "source": {"type": "guideline", "id": "G-001", "derived_from": null}
        }
      ],
      "should": [
        {
          "id": "G-003",
          "content": "Prefer composition over inheritance",
          "source": {"type": "guideline", "id": "G-003"}
        }
      ]
    },
    
    "dependency_context": [
      {
        "task_id": "T-003",
        "name": "Connection pooling",
        "status": "DONE",
        "changes": [
          {"file": "db/pool.py", "action": "created", "summary": "pgbouncer-based pool"},
          {"file": "config.py", "action": "edited", "summary": "Added POOL_SIZE env var"}
        ],
        "decisions": [
          {"id": "D-004", "issue": "Pool implementation", "recommendation": "pgbouncer"}
        ],
        "source": {"type": "task", "id": "T-003"}
      }
    ],
    
    "risks": [
      {
        "id": "R-002",
        "severity": "HIGH",
        "issue": "Redis single point of failure",
        "mitigation_plan": "Implement graceful fallback to DB",
        "source": {"type": "decision", "id": "R-002", "linked_entity": "I-001"}
      }
    ],
    
    "business_context": {
      "objective": {"id": "O-001", "title": "Reduce API response time"},
      "key_results": [
        {"id": "KR-1", "metric": "p95 latency", "current": 320, "target": 200, "progress": "61%"}
      ],
      "idea": {"id": "I-001", "title": "Redis caching"},
      "source": {"type": "objective", "id": "O-001"}
    },
    
    "excluded": [
      {
        "type": "should_guideline",
        "id": "G-007",
        "reason": "Context budget exceeded 80% — SHOULD guidelines trimmed",
        "content_preview": "Prefer immutable data structures..."
      }
    ]
  },
  
  "meta": {
    "context_size_kb": 12.4,
    "context_budget_kb": 50,
    "guidelines_count": {"must": 2, "should": 1, "excluded": 1},
    "dependencies_count": {"completed": 1, "pending": 0},
    "risks_count": {"high": 1, "medium": 0, "low": 0},
    "scenarios_count": {"happy_path": 2, "failure_mode": 2, "adversarial": 2, "regression": 1},
    "estimated_complexity": "medium"
  }
}
```

#### Logika kompilacji

```
1. Załaduj task z tracker.json
2. Załaduj guidelines (filtered by task.scopes + "general")
   → Rozdziel na MUST / SHOULD
   → Jeśli context > 80% budżetu: SHOULD → excluded z powodem
3. Załaduj dependency context (completed tasks only)
   → Ich changes (file-level summaries)
   → Ich decisions (recommendations + reasoning)
4. Załaduj risks (z decisions.json, type=risk, linked to task or origin idea)
5. Załaduj business context (task → origin idea → objective → KRs)
6. Załaduj knowledge (required + context, linked via task/idea)
7. Wygeneruj verification scenarios (patrz 3.2)
8. Określ metodę weryfikacji per AC
9. Policz meta (sizes, counts, budget)
10. Zapisz jako briefings/T-NNN.json
11. Wyświetl human-readable (markdown render)
```

#### Zasady

- **Każdy element ma `source`** — traceability do origins
- **Sekcja `excluded`** — jawnie pokazuje co obcięte i dlaczego
- **Wersjonowanie** — modyfikacja briefingu tworzy nową wersję
- **Approval gate** — `approved_at` musi być set zanim execution może zacząć
- **Immutability po approval** — zatwierdzony briefing nie może być zmieniony (nowa wersja = nowy approval)

---

### 3.2 Scenario Generator (`core/scenarios.py`)

#### Cel
Generowanie scenariuszy weryfikacji PRZED implementacją. Nie optymistycznych. Z wielu źródeł.

#### Źródła scenariuszy

```
INSTRUKCJA → happy_path scenarios
  "Cache hit returns cached data"
  "Cache miss fetches from DB and caches"

RYZYKA → failure_mode scenarios
  Risk R-002 "Redis SPOF" → "Redis down, app still works"
  Risk R-005 "Data staleness" → "Stale cache returns outdated data"

GUIDELINES → compliance scenarios
  G-001 "StorageAdapter" → "CacheAdapter implements StorageAdapter protocol"

ZALEŻNOŚCI → integration scenarios
  T-003 "connection pooling" → "Cache + pool don't create connection leak"

KONTEKST BIZNESOWY → performance scenarios
  KR-1 "p95 < 200ms" → "Cache hit p95 < 10ms measured under load"

ADVERSARIAL → sabotage/edge case scenarios
  "10K concurrent requests na ten sam klucz"
  "Corrupt JSON w cache entry"
  "Redis timeout po 30 sekund"
  "Redis pamięć pełna (maxmemory reached)"
  "Cache key collision (hash conflict)"
```

#### Interfejs

```python
# CLI
python -m core.scenarios generate {project} {task_id}    # Generuj scenariusze
python -m core.scenarios show {project} {task_id}        # Pokaż scenariusze
python -m core.scenarios add {project} {task_id} --data '{...}'  # Dodaj ręcznie
python -m core.scenarios contract                        # Kontrakt danych

# Wywoływane automatycznie przez briefing compile
```

#### Struktura scenariusza

```json
{
  "id": "V-003",
  "task_id": "T-005",
  "title": "Redis unavailable — graceful degradation",
  "type": "failure_mode",
  "derived_from": {
    "source_type": "risk",
    "source_id": "R-002",
    "reasoning": "Risk R-002 identifies Redis as SPOF. If Redis goes down, the application must continue serving requests from the database."
  },
  "preconditions": [
    "Application running with Redis connected",
    "Cache populated with at least 1 entry"
  ],
  "steps": [
    "Stop Redis server (docker stop redis)",
    "Send API request for cached endpoint",
    "Verify response is 200 with correct data",
    "Check application logs for warning (not error)"
  ],
  "pass_criteria": "API returns correct data from DB. Logs WARNING about Redis unavailability. No 500 errors. No crash.",
  "fail_criteria": "500 error, crash, hang, or incorrect data returned",
  "verification_method": "automated_test",
  "evidence_required": "pytest output + application logs showing WARNING"
}
```

#### Minimalne wymagania per task

```
Każde zadanie MUSI mieć minimum:
- 1 happy_path scenario
- 1 failure_mode scenario (jeśli task ma ryzyka lub modyfikuje istniejący kod)
- 1 regression scenario (jeśli task modyfikuje istniejący kod)

Sugerowane:
- 1 adversarial scenario per HIGH risk
- 1 integration scenario per dependency
- 1 compliance scenario per MUST guideline
```

---

### 3.3 Finding System (`core/findings.py`)

#### Cel
Strukturalny mechanizm dla odkryć AI podczas execution. Finding ≠ decyzja. Finding = obserwacja z dowodem i sugerowaną akcją.

#### Interfejs

```python
# CLI
python -m core.findings add {project} --data '[...]'       # Dodaj finding
python -m core.findings read {project} [--status X]         # Lista findings
python -m core.findings triage {project} {finding_id} --action approve|defer|reject [--reason "..."]
python -m core.findings show {project} {finding_id}         # Szczegóły
python -m core.findings contract                            # Kontrakt danych

# API
GET    /api/findings                          # Lista (filtry: status, severity, type)
POST   /api/findings                          # Dodaj
POST   /api/findings/{id}/triage              # Triage: approve/defer/reject
GET    /api/findings/{id}                     # Szczegóły
```

#### Struktura findingu

```json
{
  "id": "F-002",
  "project": "my-project",
  "type": "bug",
  "severity": "high",
  "status": "OPEN",
  "title": "Connection pool doesn't handle reconnect",
  "description": "pool.py _get_connection() doesn't catch ConnectionError. If the database restarts, all pooled connections become stale and the app returns 500 errors until manual restart.",
  "discovered_during": {
    "task_id": "T-005",
    "phase": "execution",
    "context": "While implementing Redis client, noticed pool.py imports and connection handling"
  },
  "evidence": {
    "file": "db/pool.py",
    "line": 78,
    "code_snippet": "def _get_connection(self):\n    return self._pool.pop()  # no error handling",
    "reproduction_steps": "1. Start app with DB. 2. Restart DB. 3. Send request. 4. Observe ConnectionError"
  },
  "suggested_action": "Add try/except ConnectionError with reconnect + exponential backoff in _get_connection()",
  "triage_result": null,
  "created_task_id": null,
  "created_at": "2026-04-13T14:45:00Z"
}
```

#### Triage flow

```
Finding OPEN
    │
    ├── approve → Tworzy nowe zadanie w pipeline:
    │              - Nazwa: "[F-002] Fix: pool.py reconnect handling"
    │              - Instrukcja: z finding.description + evidence
    │              - AC: z finding.suggested_action
    │              - Origin: "F-002" (traceability)
    │              - Dependencies: automatic (current task or none)
    │              - Scopes: inherited from source task
    │
    ├── defer → Status DEFERRED z reason. Pojawia się w briefingach
    │           przyszłych zadań dotykających tego pliku.
    │
    └── reject → Status REJECTED z reason. Zarchiwizowany.
```

---

### 3.4 Verification Engine (`core/verification.py`)

#### Cel
Niezależna weryfikacja outputu vs specification. Nie self-assessment.

#### Interfejs

```python
# CLI
python -m core.verification run {project} {task_id}       # Uruchom pełną weryfikację
python -m core.verification show {project} {task_id}       # Pokaż raport
python -m core.verification contract                       # Kontrakt danych

# API
POST /api/tasks/{task_id}/verify     # Trigger weryfikacji
GET  /api/tasks/{task_id}/verify     # Pobierz raport
```

#### Co sprawdza (5 warstw)

```
Warstwa 1: GATES (automated, hard block)
├── pytest → output log → evidence
├── ruff lint → output log → evidence  
├── mypy type-check → output log → evidence
├── gitleaks secrets → output log → evidence
└── Każdy gate: PASS/FAIL + full output preserved

Warstwa 2: SCENARIOS (per V-NNN, hard block for required)
├── Dla każdego scenariusza z briefingu:
│   ├── Sprawdź czy został zaadresowany
│   ├── Zbierz evidence (test output, logs)
│   ├── Oceń PASS / FAIL / PARTIAL
│   └── Jeśli FAIL: dokładny opis co nie przeszło
└── Minimum: wszystkie happy_path + failure_mode MUSZĄ PASS

Warstwa 3: GUIDELINES COMPLIANCE (MUST = hard block)
├── Dla każdego MUST guideline z briefingu:
│   ├── Sprawdź czy zmieniony kod jest zgodny
│   ├── Evidence: konkretna linia kodu + objaśnienie
│   └── FAIL → hard block
└── SHOULD guidelines: raport, nie block

Warstwa 4: BRIEFING vs OUTPUT DIFF
├── Instruction executed? (check file changes match intent)
├── All ACs addressed? (check each AC has evidence)
├── Scope creep? (files changed outside instruction scope)
└── Missing scenarios? (scenarios not covered)

Warstwa 5: QUALITY CHECKS (soft, but visible)
├── reasoning_trace ≠ "auto-complete" (placeholder detection)
├── AC verification ≠ template "ACN: X — PASS" without evidence
├── Change summaries ≠ identical for multiple files (copy detection)
├── Decisions have alternatives_considered (not just chosen option)
└── Per check: PASS / WARNING (visible in report and Web UI)
```

#### Struktura raportu

```json
{
  "task_id": "T-005",
  "verified_at": "2026-04-13T15:10:00Z",
  "overall_verdict": "PASS",
  "layers": {
    "gates": {
      "status": "PASS",
      "results": [
        {"gate": "pytest", "status": "PASS", "evidence_file": "traces/T-005/gate_pytest.log"},
        {"gate": "ruff", "status": "PASS", "evidence_file": "traces/T-005/gate_ruff.log"}
      ]
    },
    "scenarios": {
      "status": "PASS",
      "results": [
        {"id": "V-001", "status": "PASS", "evidence": "test_cache.py::test_hit — 3ms avg"},
        {"id": "V-003", "status": "PASS", "evidence": "test_cache.py::test_redis_down — 200 OK from DB"},
        {"id": "V-005", "status": "PARTIAL", "evidence": "Race window 2ms, accepted per D-008", "override_reason": "Acceptable per architecture decision D-008"}
      ]
    },
    "guidelines": {
      "status": "PASS",
      "results": [
        {"id": "G-001", "status": "PASS", "evidence": "CacheAdapter inherits StorageAdapter, line 15 of cache/redis.py"}
      ]
    },
    "briefing_diff": {
      "status": "PASS",
      "instruction_covered": true,
      "acs_addressed": ["AC-1", "AC-2", "AC-3"],
      "scope_creep_files": [],
      "unaddressed_scenarios": []
    },
    "quality": {
      "status": "WARNING",
      "checks": [
        {"check": "reasoning_not_placeholder", "status": "PASS"},
        {"check": "ac_has_evidence", "status": "PASS"},
        {"check": "unique_change_summaries", "status": "WARNING", "detail": "2 files share similar summary"}
      ]
    }
  }
}
```

---

### 3.5 Execution Tracer (`core/tracer.py`)

#### Cel
Automatyczne nagrywanie co AI robi podczas wykonywania zadania. Nie opcjonalne.

#### Co nagrywa

```json
{
  "task_id": "T-005",
  "started_at": "2026-04-13T14:32:00Z",
  "completed_at": "2026-04-13T14:58:00Z",
  "briefing_version": 1,
  "events": [
    {
      "timestamp": "2026-04-13T14:32:01Z",
      "type": "file_read",
      "file": "config.py",
      "purpose": "Understanding current configuration structure"
    },
    {
      "timestamp": "2026-04-13T14:32:05Z",
      "type": "finding",
      "finding_id": "F-002",
      "summary": "pool.py no reconnect handling"
    },
    {
      "timestamp": "2026-04-13T14:32:08Z",
      "type": "file_create",
      "file": "cache/redis.py",
      "lines_added": 145
    },
    {
      "timestamp": "2026-04-13T14:32:20Z",
      "type": "decision",
      "decision_id": "D-008",
      "summary": "Chose redis-py over aioredis — sync simpler for current architecture"
    },
    {
      "timestamp": "2026-04-13T14:32:30Z",
      "type": "test_run",
      "command": "pytest tests/test_cache.py -v",
      "result": "7/7 passed",
      "duration_seconds": 3.2
    }
  ],
  "files_read": ["config.py", "db/pool.py", "requirements.txt"],
  "files_created": ["cache/redis.py", "cache/__init__.py", "tests/test_cache.py"],
  "files_edited": ["config.py", "requirements.txt"],
  "decisions_made": ["D-008"],
  "findings_reported": ["F-002"],
  "total_duration_seconds": 1560
}
```

#### Mechanizm nagrywania

Tracer działa jako wrapper wokół tool calls w Claude Code:
- Hook na `Read` → event `file_read`
- Hook na `Edit`/`Write` → event `file_create`/`file_edit`
- Hook na `Bash` → event `command_run`/`test_run`
- Hook na `decisions add` → event `decision`
- Hook na `findings add` → event `finding`

To jest realizowalne przez Claude Code hooks (settings.json) lub przez wrapper w skills/next/SKILL.md który instruuje AI by raportowała każdą akcję.

---

### 3.6 Hard Enforcement — zmiany w pipeline.py

#### Usunięcie `--force`

```python
# BYŁO (V1):
if not task_changes:
    print(f"WARNING: No changes recorded. Use --force to bypass.")
    sys.exit(1)

# BĘDZIE (V2):
if not task_changes:
    print(f"ERROR: No changes recorded. Cannot complete.")
    print(f"Use --override --reason 'explanation why no changes' for investigation tasks.")
    sys.exit(1)
```

#### Override z logowaniem

```python
# V2: --override wymaga --reason i jest logowane
if args.override:
    if not args.reason:
        print("ERROR: --override requires --reason 'explanation'")
        sys.exit(1)
    override_record = {
        "task_id": task_id,
        "overridden_check": check_name,
        "reason": args.reason,
        "timestamp": now_iso(),
        "agent": args.agent or "human"
    }
    # Zapisane w tracker, widoczne w briefingach następnych zadań
    task.setdefault("overrides", []).append(override_record)
    # Widoczne w Web UI jako żółta flaga
```

#### Nowe hard blocks

```
STRUCTURAL (kod nie pozwala ominąć):
1. briefing.approved_at MUSI istnieć przed cmd_next pozwoli na execution
2. verification_report MUSI istnieć z overall_verdict != "FAIL" przed cmd_complete
3. scenarios MUSZĄ istnieć (minimum 1 happy_path)
4. execution_trace MUSI istnieć (automatyczne, ale sprawdzane)

PROCEDURAL (--override --reason):
1. Gates failure → override z reason
2. Scenario PARTIAL → override z reason (FAIL = nie da się)
3. MUST guideline violation → override z reason
4. Quality warning → override z reason

ADVISORY (raport, nie block):
1. SHOULD guidelines
2. Quality checks (placeholder detection)
3. Scope creep detection
```

---

### 3.7 Web Observatory — Architektura

#### Backend (FastAPI)

```
forge_web/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + CORS + WebSocket
│   ├── routes/
│   │   ├── projects.py      # GET /api/projects, GET /api/projects/{id}
│   │   ├── tasks.py         # GET /api/tasks, GET /api/tasks/{id}
│   │   ├── briefings.py     # GET/POST briefing compile/approve/modify/diff
│   │   ├── execution.py     # POST trigger, WS /ws/execution/{task_id}
│   │   ├── verification.py  # POST verify, GET report
│   │   ├── findings.py      # CRUD + triage
│   │   ├── objectives.py    # CRUD + KR progress
│   │   ├── guidelines.py    # CRUD + compliance matrix
│   │   ├── decisions.py     # CRUD + timeline
│   │   └── pipeline.py      # DAG data for visualization
│   ├── models/
│   │   ├── briefing.py      # Pydantic models
│   │   ├── finding.py
│   │   ├── verification.py
│   │   └── trace.py
│   └── services/
│       ├── briefing_service.py    # Kompilacja, wersjonowanie
│       ├── execution_service.py   # Trigger + WS streaming
│       ├── verification_service.py # Uruchamianie weryfikacji
│       └── finding_service.py     # Triage logic
├── engine/
│   ├── executor.py           # Wrapper wokół Claude Code
│   └── tracer.py             # Hook-based trace recording
└── config.py                 # Settings
```

#### Frontend (React + TypeScript)

```
forge_web/frontend/
├── src/
│   ├── App.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx          # Przegląd projektów, aktywne zadania
│   │   ├── PipelineView.tsx       # Interactive DAG (dagre-d3 / reactflow)
│   │   ├── TaskView.tsx           # Główny widok: briefing | execution | verification
│   │   ├── FindingTriage.tsx      # Kolejka triage: approve/defer/reject
│   │   ├── ObjectiveTracker.tsx   # KR progress, coverage
│   │   └── GuidelineManager.tsx   # Scope matrix, compliance
│   ├── components/
│   │   ├── BriefingPanel.tsx      # Czytelny briefing z source tracing
│   │   ├── ExecutionMonitor.tsx   # Real-time trace via WebSocket
│   │   ├── VerificationReport.tsx # Scenario status matrix + evidence links
│   │   ├── FindingCard.tsx        # Single finding z evidence + actions
│   │   ├── DAGGraph.tsx           # Pipeline visualization
│   │   └── SourceTrace.tsx        # "Where does this come from?" popup
│   ├── stores/
│   │   ├── taskStore.ts           # Zustand store
│   │   ├── briefingStore.ts
│   │   ├── findingStore.ts
│   │   └── wsStore.ts             # WebSocket connection management
│   └── hooks/
│       ├── useWebSocket.ts        # Real-time execution stream
│       └── useBriefing.ts         # Briefing CRUD
├── package.json
└── vite.config.ts
```

#### Kluczowe widoki

**Dashboard:**
- Lista projektów z progress bar (tasks done / total)
- Aktywne zadania z real-time status
- Findings queue (count + severity breakdown)
- Objective KR progress

**Pipeline View:**
- Interactive DAG z kolorami per status
- Kliknięcie → Task View
- Findings widoczne jako nowe node'y z flagą
- Dependency arrows z labels

**Task View (3 panele):**
- BRIEFING: kompletny briefing z source tracing (kliknij element → pokaż źródło)
- EXECUTION: real-time trace (WebSocket stream)
- VERIFICATION: scenario status matrix + gate results + evidence links

**Finding Triage:**
- Kolejka findings sortowana po severity
- Każdy finding: evidence, context, suggested action
- Akcje: Approve (→ nowe zadanie) / Defer / Reject
- History: wcześniejsze triage decyzje

---

## 4. Plan implementacji

### Faza 1: Core Refactor (tydzień 1-2)

| # | Zadanie | Zależności | Pliki | Priorytet |
|---|---------|-----------|-------|-----------|
| T-001 | Briefing Compiler — moduł i CLI | - | `core/briefing.py` | CRITICAL |
| T-002 | Scenario Generator — moduł i CLI | - | `core/scenarios.py` | CRITICAL |
| T-003 | Finding System — moduł i CLI | - | `core/findings.py` | HIGH |
| T-004 | Verification Engine — moduł i CLI | T-001, T-002 | `core/verification.py` | CRITICAL |
| T-005 | Execution Tracer — moduł i hooks | - | `core/tracer.py` | HIGH |
| T-006 | Pipeline refactor — hard enforcement | T-001, T-004 | `core/pipeline.py` | CRITICAL |
| T-007 | Changes quality validation | - | `core/changes.py` | MEDIUM |
| T-008 | Context transparency (excluded section) | - | `core/llm/context.py` | MEDIUM |
| T-009 | SKILL.md updates — nowy flow | T-001-T-006 | `skills/next/SKILL.md`, `skills/plan/SKILL.md` | CRITICAL |
| T-010 | Testy unit dla nowych modułów | T-001-T-005 | `tests/test_briefing.py`, etc. | CRITICAL |
| T-011 | Testy integracyjne — pełny flow | T-010 | `tests/test_integration.py` | HIGH |
| T-012 | Testy behawioralne — output compliance | T-010 | `tests/test_behavioral.py` | HIGH |

### Faza 2: Web Backend (tydzień 3-4)

| # | Zadanie | Zależności | Pliki | Priorytet |
|---|---------|-----------|-------|-----------|
| T-020 | FastAPI skeleton + routing | T-001-T-005 | `forge_web/api/` | CRITICAL |
| T-021 | Briefing API endpoints | T-020, T-001 | `forge_web/api/routes/briefings.py` | CRITICAL |
| T-022 | Execution API + WebSocket | T-020, T-005 | `forge_web/api/routes/execution.py` | HIGH |
| T-023 | Verification API | T-020, T-004 | `forge_web/api/routes/verification.py` | HIGH |
| T-024 | Finding API + triage | T-020, T-003 | `forge_web/api/routes/findings.py` | MEDIUM |
| T-025 | Pipeline DAG data API | T-020 | `forge_web/api/routes/pipeline.py` | MEDIUM |
| T-026 | Pydantic models | T-020 | `forge_web/api/models/` | CRITICAL |
| T-027 | Backend testy | T-020-T-025 | `tests/test_api/` | HIGH |

### Faza 3: Web Frontend (tydzień 5-7)

| # | Zadanie | Zależności | Pliki | Priorytet |
|---|---------|-----------|-------|-----------|
| T-030 | React skeleton + routing + stores | T-020 | `forge_web/frontend/` | CRITICAL |
| T-031 | BriefingPanel component | T-030, T-021 | `components/BriefingPanel.tsx` | CRITICAL |
| T-032 | ExecutionMonitor + WebSocket | T-030, T-022 | `components/ExecutionMonitor.tsx` | HIGH |
| T-033 | VerificationReport component | T-030, T-023 | `components/VerificationReport.tsx` | HIGH |
| T-034 | DAG Pipeline View (reactflow) | T-030, T-025 | `pages/PipelineView.tsx` | HIGH |
| T-035 | Task View (3-panel layout) | T-031-T-033 | `pages/TaskView.tsx` | CRITICAL |
| T-036 | FindingTriage page | T-030, T-024 | `pages/FindingTriage.tsx` | MEDIUM |
| T-037 | Dashboard | T-030 | `pages/Dashboard.tsx` | MEDIUM |
| T-038 | SourceTrace popup | T-031 | `components/SourceTrace.tsx` | MEDIUM |
| T-039 | Frontend testy | T-030-T-038 | `tests/frontend/` | HIGH |

### Faza 4: Integration & Hardening (tydzień 8)

| # | Zadanie | Zależności | Pliki | Priorytet |
|---|---------|-----------|-------|-----------|
| T-040 | End-to-end test: cel → ukończenie | T-001-T-039 | `tests/test_e2e.py` | CRITICAL |
| T-041 | Behavioral test: AI output compliance | T-012 | `tests/test_ai_compliance.py` | HIGH |
| T-042 | Performance test: 100+ tasks, large context | All | `tests/test_performance.py` | MEDIUM |
| T-043 | Documentation update | All | `CLAUDE.md`, `README.md` | MEDIUM |
| T-044 | Migration guide: V1 → V2 | All | `docs/migration.md` | MEDIUM |

### Diagram zależności

```
T-001 (Briefing) ──┐
T-002 (Scenarios) ─┤
T-003 (Findings) ──┼── T-004 (Verification) ──┐
T-005 (Tracer) ────┘                           ├── T-006 (Pipeline refactor)
                                               │        │
T-007 (Changes quality) ──────────────────────┘        │
T-008 (Context transparency) ─────────────────┘        │
                                                        │
T-009 (SKILL.md) ◄─────────────────────────────────────┘
T-010 (Unit tests) ◄── T-001-T-005
T-011 (Integration tests) ◄── T-010
T-012 (Behavioral tests) ◄── T-010

T-020 (API skeleton) ◄── T-001-T-005
T-021-T-025 (API routes) ◄── T-020
T-026 (Models) ◄── T-020
T-027 (API tests) ◄── T-021-T-025

T-030 (Frontend skeleton) ◄── T-020
T-031-T-038 (Components) ◄── T-030
T-039 (Frontend tests) ◄── T-031-T-038

T-040 (E2E) ◄── ALL
T-041 (Behavioral) ◄── T-012
```

---

## 5. Metryki sukcesu

### Jak udowodnić że V2 działa lepiej niż V1

| Metryka | V1 (baseline) | V2 (target) | Jak mierzyć |
|---------|--------------|-------------|-------------|
| Briefing visibility | 0% (niewidoczny) | 100% (każde zadanie ma briefing) | Count briefings / total tasks |
| Scenario coverage | 0 scenarios | ≥3 per task | Count scenarios per task |
| Evidence-based AC | 0% (template "PASS") | 100% (evidence attached) | Audit AC reports for evidence |
| Placeholder detection | Not detected | 0 placeholders in reasoning | Quality check results |
| Finding capture rate | Unknown (lost) | ≥1 finding per 3 tasks | Count findings / tasks |
| Override transparency | `--force` (no log) | 100% overrides logged with reason | Audit override records |
| Test coverage (Forge) | 45% modules | 90% modules | pytest --cov |
| E2E test existence | 0 | ≥5 scenarios | Count E2E test functions |
| Context transparency | 0% (silent truncation) | 100% (excluded section) | Audit briefings for excluded |
| Independent verification | 0% (self-assess) | 100% tasks verified independently | Count verification reports |

---

## 6. Ryzyka planu (wstępne)

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitygacja |
|--------|-------------------|-------|-----------|
| R-1: Briefing compilation zbyt wolna | Medium | Medium | Cache computed sections, lazy load |
| R-2: Scenario generation tworzy bezsensowne scenariusze | High | High | Human review + templates + feedback loop |
| R-3: Independent verification = second AI = double cost | High | Medium | Partial automation (gates + pattern matching) + human for critical |
| R-4: Override becomes new --force (used casually) | Medium | High | Dashboard metrics, override frequency alerting |
| R-5: Web UI scope creep (3 weeks → 8 weeks) | High | High | MVP: briefing view + pipeline DAG only. Rest later. |
| R-6: Execution tracer overhead in Claude Code hooks | Medium | Low | Lightweight hooks, batch writes |
| R-7: Breaking V1 projects during migration | Medium | High | Migration script, backward compat for reading old format |
| R-8: AI generates scenarios but doesn't actually test them | High | Critical | Verification engine checks evidence, not just claims |
| R-9: Too many findings = noise, user ignores queue | Medium | Medium | Severity-based filtering, daily digest, auto-defer LOW after 7 days |

---

## 7. Decyzje otwarte

| # | Pytanie | Opcje | Rekomendacja |
|---|---------|-------|-------------- |
| D-1 | Kto robi "niezależną weryfikację"? | a) Drugi AI agent, b) Automated checks only, c) Human + automated | c) — automated gates + quality checks, human reviews verification report |
| D-2 | Gdzie persystować traces? | a) JSON files, b) SQLite, c) PostgreSQL | a) JSON files (spójne z V1), z opcją SQLite w przyszłości |
| D-3 | Frontend framework? | a) React + Vite, b) Next.js, c) SvelteKit | a) React + Vite (prostsze, bez SSR overhead) |
| D-4 | Jak integrować execution tracer z Claude Code? | a) Hooks (settings.json), b) SKILL.md instrukcje, c) Wrapper script | a) + b) — hooks dla automatycznych eventów, SKILL.md dla finding/decision recording |
| D-5 | MVP scope dla Web UI? | a) Full (all views), b) Briefing + Pipeline only, c) CLI-only first | b) — briefing viewer + pipeline DAG = 80% wartości w 20% czasu |

# Forge Platform — Docelowa architektura

**Data:** 2026-04-13
**Status:** FINAL DRAFT — symulacja procesów + pełna specyfikacja API
**Zastępuje:** Wszystkie poprzednie dokumenty (ARCHITECTURE v1/v2/v3, DEEP_VERIFY, DEEP_RISK, DEEP_EXPLORE, TEST_SCENARIOS)

---

## Spis treści

1. [Cel i uzasadnienie](#1-cel-i-uzasadnienie)
2. [Symulacja procesu — krok po kroku](#2-symulacja-procesu)
3. [Model danych](#3-model-danych)
4. [API — pełna specyfikacja](#4-api)
5. [Prompt Assembly Engine](#5-prompt-assembly)
6. [Contract Validation Engine](#6-contract-validation)
7. [Przepływy — kompletne diagramy](#7-przepływy)
8. [Edge cases i odporność](#8-edge-cases)

---

## 1. Cel i uzasadnienie

### Co budujemy

System w którym:
- API składa prompt z elementów i zapisuje CO złożyło i DLACZEGO
- API waliduje wyniki AI wg kontraktu per typ zadania
- AI jest wykonawcą — dostaje gotowy prompt, oddaje wyniki w zdefiniowanym formacie
- Użytkownik widzi WSZYSTKO w Web UI: co AI dostała, co oddała, co przeszło, co nie
- Baza danych (PostgreSQL) jako storage (FK, constraints, indeksy). Logika w Pythonie.
- Każda operacja przez API — AI i Web UI używają tego samego API

### Dlaczego (udowodnione danymi)

ITRP (77 tasków): 91% bez AC evidence, 0% changes z reasoning, 75% copy-paste opisy. System ma 17 bramek ale walidują obecność, nie jakość. AI wpisuje filler i przechodzi.

### Jawne ograniczenie

Walidacja regułami ma sufit. AI może produkować tekst który przechodzi pattern matching ale jest semantycznie pusty. Kontrakty łapią ~80% problemów. Reszta wymaga human review w Web UI.

---

## 2. Symulacja procesu — krok po kroku

### 2.1 Ingestion: dokument → fakty

```
KROK: Użytkownik dostarcza dokument źródłowy
OPERACJA: POST /api/knowledge (category=source-document)
```

**Co robi:** Rejestruje dokument w bazie. Tworzy K-NNN z treścią i metadanymi.

**Cel:** Single source of truth dla dokumentu — system wie skąd pochodzą wymagania.

**Co wnosi:** Traceability — każdy fakt da się prześledzić do dokumentu. Bez tego fakty są orphaned.

**Co psuje:** Nic — dodaje dane, nie zmienia istniejących.

**Czy jest potrzebne:** TAK — bez zarejestrowanego dokumentu nie ma skąd weryfikować fidelity. Pominięcie = wymyślone wymagania.

**Gdzie się zepsuje:** 
- Dokument ma sprzeczne wymagania → trzeba wyłapać w extraction (krok 2)
- Dokument jest nieczytelny/niekompletny → system nie wie o lukach
- Duży dokument (100KB+) → context budget przy assembly

**Czym zastąpić:** Niczym — to jest punkt wejścia danych do systemu.

```
KROK: Ekstrakcja faktów z dokumentu
OPERACJA: POST /api/knowledge (category=requirement|domain-rules|...) × N
          POST /api/decisions (type=risk, status=OPEN) dla konfliktów
          POST /api/research (category=ingestion) jako record
```

**Co robi:** Z jednego dokumentu → N knowledge objects, M decisions dla konfliktów.

**Cel:** Atomizacja — rozbicie monolitycznego dokumentu na pojedyncze, reusable fakty.

**Co wnosi:** 
- Każdy fakt osobno = można linkować do objectives, tasks, guidelines
- Konflikty jawne (OPEN decisions) = nie zamiecione pod dywan
- 9-category coverage = wiadomo co wiemy, czego nie wiemy

**Co psuje:** 
- AI może ekstrakcję zrobić źle — pominąć fakty, źle zaklasyfikować
- Atomizacja może rozdzielić powiązane fakty

**Czy potrzebne:** TAK — bez atomizacji nie da się powiązać wymagań z zadaniami.

**Gdzie się zepsuje:**
- AI pomija implicit assumptions → luki w planie
- AI łączy dwa wymagania w jedno K-NNN → fidelity check nie łapie granularnie
- AI klasyfikuje requirement jako business-context → nie trafia do coverage check

**Alternatywa:** Ręczna ekstrakcja przez użytkownika — dokładniejsza ale 10x wolniejsza.

**GATE (C1):** validate_ingestion → ≥2 fakty/dokument, 9 kategorii pokryte. 
- **Symulacja gate:** AI zrobiła ekstrakcję ale pominęła "error-handling" → gate FAIL → AI musi powtórzyć. TO DZIAŁA.
- **Symulacja gaming:** AI wpisuje placeholder K-NNN z category=error-handling z content="TBD" → gate PASS bo category istnieje. PROBLEM — gate sprawdza obecność, nie treść.
- **Fix:** Dodać min content length per knowledge (≥30 chars). Nie eliminuje problemu całkowicie ale podnosi poprzeczkę.

---

### 2.2 Analysis: fakty → objectives z KR

```
KROK: Grupowanie wymagań w objectives
OPERACJA: POST /api/objectives (z key_results[])
          PUT /api/decisions/{id} (close OPEN decisions)
          POST /api/knowledge/link (K→O linkage)
```

**Co robi:** Z N requirements → M objectives z measurable KR. Zamyka OPEN decisions.

**Cel:** Odpowiada na "PO CO robimy te zadania". Bez objectives = zadania bez celu.

**Co wnosi:**
- KR daje mierzalny cel (p95 < 200ms, a nie "szybsze")
- Linkage K→O = wiadomo które wymagania należą do którego celu
- OPEN decisions zamknięte = brak nierozwiązanych pytań

**Co psuje:**
- Złe grupowanie (technical layers zamiast business outcomes) → objectives nie mierzalne
- KR bez measurement → "mierzalny" ale nie da się zmierzyć

**Gdzie się zepsuje:**
- AI tworzy objective "Implement Backend" (warstwa, nie outcome) → zadania bez biznesowego celu
- KR measurement=manual z check="verify manually" → niesprawdzalne

**GATE (C2):** validate_analysis → ≥1 ACTIVE objective, all KR have measurement, all K linked to O.
- **Symulacja gate:** AI tworzy objective bez KR → gate FAIL → musi dodać KR. DZIAŁA.
- **Symulacja gaming:** KR z measurement=manual, check="check" → gate PASS bo pole istnieje. PROBLEM.
- **Fix:** check field min length ≥30 chars, must contain verb ("verify", "confirm", "run", "open").

---

### 2.3 Planning: objectives → tasks

```
KROK: Dekompozycja na graf zadań
OPERACJA: POST /api/plans/draft (tasks + assumptions + coverage)
          POST /api/plans/{id}/approve → materializacja T-NNN
```

**Co robi:** Z objective → N tasks z AC, dependencies, scopes, produces.

**Cel:** Executable plan — AI agent bierze task i wie co zrobić bez pytania.

**Co wnosi:**
- Cold-start test: "paste instruction into blank context → agent knows first file to open"
- AC structured (test/command/manual) = mechanicznie weryfikowalne
- Dependencies DAG = kolejność wykonania

**Co psuje:**
- Złe AC (generic "it works") → walidacja przechodzi ale nic nie testuje
- Brak negative scenarios → happy-path only
- Instruction za ogólna → agent zgaduje co zrobić

**Gdzie się zepsuje:**
- AI tworzy 15 tasków z generic AC → approve przechodzi → execution bez jakości
- Last tasks have vague instructions (planning fatigue) → worst quality at end

**GATE (C3-C4):** draft-plan validates: AC structured, origin exists, knowledge refs valid, DAG acyclic, scopes match guidelines, coverage complete, <5 HIGH assumptions.

**Symulacja AC quality:**
```
AI produkuje: {"text": "Data is saved correctly", "verification": "manual"}
Gate C4 sprawdza: text exists ✓, verification is enum ✓
→ PASS. Ale AC jest generic i niesprawdzalne.

AI produkuje: {"text": "Given empty cart, when checkout, then 400 with {error: 'Cart empty'}", 
               "verification": "test", "test_path": "tests/test_checkout.py::test_empty_cart",
               "scenario_type": "negative"}
Gate C4 sprawdza: text exists ✓, verification=test ✓, test_path exists ✓
→ PASS. I AC jest faktycznie wartościowe.
```

**Fix na AC quality (w API, mechanicznie):**
```
fn_validate_ac_quality(task):
  IF type IN (feature, bug):
    REQUIRE ≥3 AC
    REQUIRE ≥1 AC z scenario_type=negative OR edge_case
    REQUIRE ≥1 AC z verification=test
    REJECT AC.text matching: "it works", "data correct", "no errors", "verified"
    REJECT AC.text < 20 chars
    REQUIRE test_path format: "{dir}/test_{name}.py::test_{name}"
  → FAIL blocks approve-plan
```

**Symulacja gaming fn_validate_ac_quality:**
```
AI pisze: {"text": "Given system running when user clicks button then page loads within 5s",
           "verification": "test", "test_path": "tests/test_ui.py::test_page_load",
           "scenario_type": "negative"}
→ PASS. Ale AC testuje ogólny page load, nie specyficzną logikę zadania.
```

**Czy da się to złapać mechanicznie?** Częściowo — sprawdź czy AC.text zawiera key terms z instruction. Jeśli instruction mówi "Redis caching" a żaden AC nie zawiera "Redis" ani "cache" → WARNING.

---

### 2.4 Prompt Assembly: task → prompt dla AI

```
KROK: API składa prompt z elementów
OPERACJA: GET /api/execute → response z prompt + contract
```

**Co robi:** Łączy instruction + guidelines + knowledge + deps + risks + business context → markdown prompt. Zapisuje KAŻDY element z source info.

**Cel:** AI dostaje KOMPLETNY kontekst. Użytkownik WIDZI co AI dostała.

**Co wnosi:**
- Transparency: prompt_sections + prompt_elements = pełen audit
- Determinism: ten sam task = ten sam prompt (bo z DB, nie z AI decisions)
- Budget management: priorytet sekcji, obcinanie z recorded exclusion_reason

**Co psuje:**
- Nic w istniejących danych — read-only wobec source entities
- Ale: ZŁY prompt = ZŁA praca AI

**Gdzie się zepsuje:**
- Budget overflow (MUST guidelines > 70% budget) → prompt niekompletny
- Scope mismatch (task ma złe scopes) → brak relevantnych guidelines
- Stale data (knowledge zmienione po assembly) → AI pracuje na starym kontekście

**Czy potrzebne:** TAK — to jest KLUCZOWA innowacja. Bez tego nie wiadomo co AI dostała.

**Alternatywa:** AI sama składa prompt (jak teraz w V1). Szybsze ale nieaudytowalne.

**Symulacja:**
```
Task T-005: scopes=[backend], instruction="Add Redis caching"

Assembly:
  P1 instruction:     "Add Redis caching..." (2.3KB) → included, reason: task_content
  P1 MUST G-001:      "StorageAdapter..." (0.8KB) → included, reason: scope_match:backend
  P1 MUST G-007:      "Immutable data..." (0.6KB) → EXCLUDED, reason: scope_mismatch:frontend∉[backend]
  P2 knowledge K-003: "Redis config..." (1.2KB) → included, reason: explicit_reference
  P3 knowledge K-012: "Perf benchmarks" (3.8KB) → EXCLUDED, reason: budget_exceeded:52KB>50KB
  P5 dep T-003:       "Pool changes..." (1.1KB) → included, reason: dependency_output
  P6 risk R-002:      "Redis SPOF" (0.4KB) → included, reason: risk_linked:I-001
  
Total: 5.8KB / 50KB budget. 5 included, 2 excluded.
Each element → prompt_elements record with source, reason, content snapshot.
```

**Web UI widzi:** "T-005 prompt: 5 elementów z 7 kandydatów. G-007 excluded (frontend scope). K-012 excluded (budget)."

---

### 2.5 Execution: AI implementuje

```
KROK: AI pracuje z promptem
OPERACJA: POST /api/execute/{id}/heartbeat (co 10 min)
          POST /api/execute/{id}/decisions (w trakcie, opcjonalnie)
          POST /api/execute/{id}/findings (odkrycia, opcjonalnie)
```

**Co robi:** AI czyta prompt, implementuje, commituje, raportuje heartbeat.

**Cel:** Implementacja zadania z live-tracking.

**Co wnosi:**
- Heartbeat = wiadomo czy AI żyje. Bez → task wisi w IN_PROGRESS na zawsze.
- Mid-execution decisions = traceability w trakcie, nie tylko po fakcie.
- Findings = odkrycia nie giną.

**Gdzie się zepsuje:**
- AI crash bez heartbeat → lease expires → task wraca do TODO (OK, to jest desired behavior)
- AI nie wysyła heartbeat (bug w integracji) → false timeout
- AI wysyła heartbeat ale nie pracuje (gaming) → lease extends na zawsze

**Fix na gaming heartbeat:** Max renewals = 20 (= 200 min max execution). Po limicie → execution EXPIRED.

---

### 2.6 Delivery: AI oddaje wyniki

```
KROK: AI oddaje wyniki pracy
OPERACJA: POST /api/execute/{id}/deliver
```

**Co robi:** AI wysyła: reasoning, ac_evidence, decisions, changes, findings, deferred. API waliduje vs kontrakt.

**Cel:** Kontrola jakości — API decyduje czy praca jest akceptowalna, nie AI.

**Co wnosi:**
- Contract validation = mechaniczne sprawdzenie jakości
- REJECTED → AI musi poprawić = feedback loop
- Attempt tracking = widać ile razy AI poprawiała

**Co psuje:**
- False positives: valid evidence rejected by pattern matching
- Rejection loop: AI poprawia → REJECT → poprawia → REJECT (thrashing)

**Gdzie się zepsuje:**
- Contract zbyt strict → AI thrashes (scenario SC-04)
- Contract zbyt lax → AI passes filler
- AI resubmit z padding (+1 zdanie) → PASS (scenario SC-04)

**Fix na resubmit padding:** API porównuje delivery n vs n-1. Jeśli diff < 20% tekstu a ten sam check failował → REJECT z "insufficient changes". Wymaga execution_attempts table.

**SYMULACJA DELIVERY VALIDATION:**

```
DELIVERY:
{
  "reasoning": "Added Redis caching in cache/redis.py implementing StorageAdapter. 
    Chose redis-py over aioredis because aioredis is deprecated and redis-py 5.x 
    supports both sync and async. Fallback to DB implemented in _get_with_fallback() 
    for graceful degradation when Redis unavailable.",
  
  "ac_evidence": [
    {"ac_index": 0, "verdict": "PASS", "scenario_type": "positive",
     "evidence": "tests/test_cache.py::test_hit — 3ms avg, p95 8ms (< 10ms target)"},
    {"ac_index": 1, "verdict": "PASS", "scenario_type": "negative",
     "evidence": "tests/test_cache.py::test_redis_down — stopped Redis, 
      GET /api/items returns 200 with data from DB, logs WARNING"},
    {"ac_index": 2, "verdict": "PASS", "scenario_type": "edge_case",
     "evidence": "tests/test_cache.py::test_corrupt — injected invalid JSON,
      cache evicted, fresh data served, WARNING logged"}
  ],
  
  "decisions": [{
    "type": "implementation", 
    "issue": "Redis client library: redis-py vs aioredis",
    "recommendation": "redis-py 5.x (sync mode)",
    "reasoning": "aioredis deprecated since 2023. redis-py 5.x supports async 
      but sync simpler for current architecture. See pool.py:15.",
    "alternatives_considered": ["aioredis (deprecated)", "redis-py async (over-engineering)"]
  }],
  
  "changes": [
    {"file_path": "cache/redis.py", "action": "create",
     "summary": "Redis cache adapter implementing StorageAdapter protocol with fallback",
     "reasoning": "New module needed — no existing cache. Follows pattern from db/pool.py"},
    {"file_path": "config.py", "action": "edit",
     "summary": "Added REDIS_URL and CACHE_TTL environment variables",
     "reasoning": "Configuration must be external per G-010"}
  ],
  
  "findings": [{
    "type": "bug", "severity": "HIGH",
    "title": "pool.py no reconnect after DB restart",
    "description": "pool.py:78 _get_connection() doesn't catch ConnectionError. 
      If DB restarts, pooled connections stale, app returns 500 until manual restart.",
    "file_path": "db/pool.py", "line_number": 78,
    "evidence": "Read pool.py:78-92 — no try/except on connection acquisition",
    "suggested_action": "Add try/except ConnectionError with exponential backoff"
  }],
  
  "scenario_results": [
    {"scenario_id": "TS-001", "verified": true,
     "evidence": "cache/redis.py:15 — CacheAdapter(StorageAdapter)"},
    {"scenario_id": "TS-002", "verified": true,
     "evidence": "Covered by AC-1 (test_redis_down)"},
    {"scenario_id": "TS-003", "verified": true,
     "evidence": "cache/redis.py:42 imports check_pool_health from pool.py"}
  ],
  
  "deferred": []
}

VALIDATION:
  reasoning:
    ✓ length: 284 > 100
    ✓ references_file: "cache/redis.py", "pool.py:15" found
    ✓ no_reject_patterns: clean
    ✓ contains_why: "because" found
    → PASS
    
  ac_evidence[0]:
    ✓ evidence length: 58 > 50
    ✓ contains test reference: "tests/test_cache.py::test_hit"
    ✓ verdict: PASS
    → PASS
    
  ac_evidence[1]: (same checks) → PASS
  ac_evidence[2]: (same checks) → PASS
  
  ac_composition:
    ✓ has negative scenario with PASS: ac_evidence[1]
    → PASS
    
  decisions[0]:
    ✓ issue: 45 > 20
    ✓ recommendation: 26 > 30... FAIL: "redis-py 5.x (sync mode)" = 24 chars
    → FAIL: recommendation too short

  → OVERALL: REJECTED (decision recommendation < 30 chars)
  → AI must resubmit with longer recommendation
```

Symulacja ujawnia: kontrakt złapał zbyt krótką recommendation. AI musi poprawić. System działa.

Ale: jeśli AI wpisze "redis-py 5.x sync mode for simplicity" (36 chars) → PASS. Treść nie zmienia się materialnie. Czy 30 chars to dobry próg? Prawdopodobnie nie — alternatywa: sprawdź czy recommendation zawiera uzasadnienie (verb: "because", "since", "due to"). To jest bardziej semantyczne ale nadal rule-based.

---

### 2.7 Test Scenarios: auto-generated by API

```
KROK: Po approve-plan, API generuje test scenarios per task
OPERACJA: Wewnętrzna funkcja fn_generate_test_scenarios(task_id)
```

**Co robi:** Czyta guidelines, risks, dependencies → tworzy TS-NNN deterministically.

**Cel:** Zapewnia że AI nie pominie compliance, risk mitigation, dependency contracts.

**Co wnosi:**
- Guideline compliance check = AI musi udowodnić że guideline jest spełniony
- Risk mitigation = AI musi zaadresować każdy HIGH/MEDIUM risk
- Dependency contract = AI musi użyć output z zależności

**Co psuje:** Nic istniejącego — dodaje nowe wymagania na delivery.

**Czy potrzebne:** TAK dla guidelines i risks. OPCJONALNE dla dependencies (dependency contract check jest w plan validation).

**Gdzie się zepsuje:**
- 50 MUST guidelines → 50 TS → AI spędza więcej czasu na TS niż na implementacji
- TS z grep_check ale grep pattern zbyt ogólny → false positive
- TS z grep_check ale AI importuje ale nie używa → false positive

**Fix na explosion:** Cap: max 10 TS per task. Priorytetyzuj: HIGH risks first, then MUST guidelines, then deps. Jeśli > 10 → najniższy priorytet excluded z explanation.

**Symulacja:**
```
Task T-005: scopes=[backend], 3 MUST guidelines, 1 HIGH risk, 1 dep z produces

fn_generate_test_scenarios(T-005):
  G-001 (MUST, backend) → TS-001: "Compliance: StorageAdapter Protocol"
                           verification: grep_check, pattern: "StorageAdapter"
  G-005 (MUST, general) → TS-002: "Compliance: Deep-verify non-trivial"
                           verification: manual_evidence
  G-010 (MUST, backend) → TS-003: "Compliance: No hardcoded config"
                           verification: grep_check, pattern: "REDIS_URL|CACHE_TTL"
  R-002 (HIGH risk)     → TS-004: "Risk: Redis SPOF mitigation"
                           verification: manual_evidence
  T-003 (dep, produces) → TS-005: "Contract: uses T-003 pool endpoint"
                           verification: grep_check, pattern: "pool"

5 scenarios. Under cap. Each has source traceability.
```

---

### 2.8 Completion: walidacja + state transition

```
KROK: Po accepted delivery → task DONE
OPERACJA: Wewnętrzna fn_complete_task(execution_id) 
```

**Co robi:** Zmienia task status, auto-updates KR, rejestruje features, tworzy OPEN decisions z deferred.

**Cel:** Zamknięcie cyklu z pełną traceability.

**Co wnosi:**
- KR auto-update = objectives śledzą postęp automatycznie
- Feature registry = duplikaty wykrywane w przyszłych planach
- Deferred → OPEN decisions = nic nie ginie

**Gdzie się zepsuje:**
- KR measurement command timeout (120s) → WARNING, nie blokuje → KR stale
- Last task for objective done ale KRs not met → WARNING, objective stays ACTIVE

**Czy potrzebne:** TAK — bez completion nie ma closure. Dane bez completion są orphaned.

---

## 3. Model danych

### 3.1 Zasady

1. **Single Source of Truth** — każdy fakt w jednym miejscu
2. **Explicit FKs** — żadnych polymorphic "task_id can be T-NNN or I-NNN"
3. **Audit built-in** — created_at, updated_at, actor na kluczowych tabelach
4. **Python validation** — logika biznesowa w Pythonie, nie w stored procedures. DB robi: storage, FK/CHECK constraints, indeksy. Python robi: walidacja delivery, prompt assembly, contract validation, trust calibration.
5. **Enumy jako CHECK** — w DB constraints
6. **Timestamps as timestamptz** — never ISO strings

### 3.2 Entity Relationship Diagram

```
projects ─────────────────────────────────────────────────────────
  │ 1:N                                                           
  ├── objectives ──── key_results (1:N)                           
  │     │ 1:N                                                     
  │     ├── knowledge_objective_links ──── knowledge (M:N)        
  │     └── objective_guidelines ──── guidelines (M:N)            
  │                                                               
  ├── ideas ──── idea_relations (self M:N)                        
  │     │        idea_key_result_links ──── key_results (M:N)     
  │     │        idea_knowledge (M:N) ──── knowledge              
  │     │        idea_guidelines (M:N) ──── guidelines            
  │                                                               
  ├── knowledge ──── knowledge_versions (1:N, embedded)           
  │                                                               
  ├── guidelines (project_id NULL = global)                       
  │                                                               
  ├── research ──── research_decisions (M:N) ──── decisions       
  │                                                               
  ├── tasks ──── task_dependencies (self M:N, DAG enforced)       
  │   │          task_conflicts (self M:N)                         
  │   │          task_blocked_by (M:N) ──── decisions              
  │   │          task_knowledge (M:N) ──── knowledge               
  │   │          acceptance_criteria (1:N)                         
  │   │          test_scenarios (1:N, auto-generated)             
  │   │                                                           
  │   ├── executions ──── prompt_sections (1:N)                   
  │   │     │              prompt_elements (1:N)                   
  │   │     │              execution_attempts (1:N)               
  │   │     │              gate_results (1:N)                     
  │   │     │                                                     
  │   │     ├── decisions (N:1 via execution_id)                  
  │   │     ├── changes (N:1 via execution_id)                    
  │   │     │     ├── change_decisions (M:N)                      
  │   │     │     └── change_guideline_checks (M:N)               
  │   │     ├── findings (N:1 via execution_id)                   
  │   │     └── (gate_results via execution_id)                   
  │   │                                                           
  │   └── decisions (N:1 via task_id, idea_id, or objective_id)   
  │                                                               
  ├── lessons ──── lesson_decisions (M:N) ──── decisions          
  │                                                               
  ├── gates (config per project)                                  
  │                                                               
  ├── ac_templates                                                
  │                                                               
  ├── skills (SKILL.md content, versioned)                        
  │                                                               
  ├── output_contracts (per task_type × ceremony_level)           
  │                                                               
  └── audit_log (partitioned by month)                            

  api_keys (global, not per project)                              
```

### 3.3 Tabele (kompletne DDL)

*[Schemat SQL z sekcji 4 ARCHITECTURE_V2.md pozostaje aktualny z następującymi zmianami:]*

**Dodane od v3:**
- `acceptance_criteria.scenario_type` (positive/negative/edge_case/regression)
- `acceptance_criteria.text CHECK (LENGTH(text) >= 20)`
- `test_scenarios` table (auto-generated by API)
- `ac_templates` table (reusable patterns)
- `execution_attempts` table (resubmit tracking)
- `api_keys` table (role-based access)
- `skills` table (SKILL.md in DB)
- `audit_log` partitioned by month
- `executions.lease_expires_at` + heartbeat
- `executions.attempt_number`
- Cross-project dependency trigger
- ON DELETE CASCADE/RESTRICT per FK

**Łączna liczba tabel: 38**

---

## 4. API — pełna specyfikacja

### 4.1 Konwencje

- Base URL: `/api/v1`
- Auth: `Authorization: Bearer {api_key}` header
- Content-Type: `application/json`
- Errors: `{"error": "message", "details": {...}}` z HTTP status code
- Pagination: `?limit=50&offset=0` (default limit=50, max=200)
- Filters: `?status=ACTIVE&scope=backend` (query params)

### 4.2 Roles

| Role | Może | Nie może |
|------|------|---------|
| `executor` | GET /execute, POST /deliver, POST /heartbeat, POST /decisions (add), POST /findings (add) | triage, resolve, modify guidelines, approve plans, delete |
| `operator` | wszystko co executor + POST /triage, POST /resolve, PUT /guidelines, POST /plans, POST /approve, DELETE, POST /knowledge, POST /objectives | contracts config, API keys |
| `admin` | wszystko | — |
| `readonly` | GET everything | POST, PUT, DELETE |

### 4.3 Endpoints — Execution Flow (AI calls)

---

#### `GET /api/v1/execute`

**Cel:** Pobierz następne zadanie z gotowym promptem i kontraktem.

**Query params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `project` | string | YES | Project slug |
| `agent` | string | NO | Agent name (default: "default") |
| `objective` | string | NO | Filter to O-NNN |
| `lean` | boolean | NO | Skip knowledge, research, lessons (default: false) |

**Response 200:**
```json
{
  "execution_id": 42,
  "task": {
    "id": "T-005",
    "external_id": "T-005",
    "name": "implement-redis-caching",
    "type": "feature",
    "status": "IN_PROGRESS",
    "instruction": "...",
    "description": "...",
    "acceptance_criteria": [
      {
        "position": 0,
        "text": "Given valid REDIS_URL...",
        "scenario_type": "positive",
        "verification": "test",
        "test_path": "tests/test_cache.py::test_connect"
      }
    ],
    "test_scenarios": [
      {
        "id": "TS-001",
        "source_type": "guideline_compliance",
        "source_id": "G-001",
        "title": "Compliance: StorageAdapter Protocol",
        "verification": "grep_check",
        "verification_detail": "grep StorageAdapter in changed files"
      }
    ],
    "produces": {"endpoint": "GET /api/cache/stats"},
    "alignment": {"goal": "...", "boundaries": {"must": [...], "must_not": [...]}},
    "exclusions": ["Do NOT modify db/pool.py"]
  },
  "prompt": {
    "full_text": "## Task: implement-redis-caching\n\n...",
    "hash": "sha256:abc123...",
    "meta": {
      "sections_total": 8,
      "sections_included": 6,
      "elements_total": 12,
      "elements_included": 10,
      "elements_excluded": 2,
      "total_kb": 48.3,
      "budget_kb": 50,
      "task_scopes": ["backend", "general"],
      "lean": false
    },
    "excluded": [
      {"source": "G-007", "reason": "scope_mismatch:frontend∉[backend,general]"},
      {"source": "K-012", "reason": "budget_exceeded:52.1KB>50KB"}
    ]
  },
  "contract": {
    "ceremony_level": "STANDARD",
    "required": {
      "reasoning": {"min_length": 100, "must_reference_file": true, "reject_patterns": ["verified manually", "done", "looks good"], "must_contain_why": true},
      "ac_evidence": {"per_criterion": true, "min_length": 50, "must_reference_file_or_test": true, "reject_patterns": ["verified", "checked"], "fail_blocks": true},
      "scenario_results": {"per_scenario": true, "min_evidence_length": 30}
    },
    "optional": {
      "decisions": {"min_issue_length": 20, "min_recommendation_length": 30, "must_have_reasoning": true},
      "changes": {"min_summary_length": 30, "unique_summaries": true, "min_reasoning_length": 30},
      "findings": {"min_description_length": 50, "must_reference_file": true, "min_evidence_length": 30}
    },
    "anti_patterns": {
      "duplicate_summaries_threshold": 0.8,
      "placeholder_patterns": ["auto-complete", "auto-recorded", "(no changes needed)"],
      "copy_paste_evidence": true
    }
  },
  "lease_expires_at": "2026-04-13T15:02:00Z"
}
```

**Response 204:** No task available (all done, blocked, or claimed).

**Response 409:** Task already claimed by another agent.

**Side effects:**
- Creates execution record (status=PROMPT_ASSEMBLED)
- Assembles prompt → creates prompt_sections + prompt_elements
- Claims task (status=IN_PROGRESS, agent set)
- Generates test_scenarios if not yet generated
- Sets lease_expires_at = now + 30min
- Audit log: "execution.created"

---

#### `POST /api/v1/execute/{execution_id}/deliver`

**Cel:** AI oddaje wyniki pracy. API waliduje vs kontrakt.

**Path params:** `execution_id` (int)

**Request body:**
```json
{
  "reasoning": "string, ≥100 chars, must reference file, must contain why",
  
  "ac_evidence": [
    {
      "ac_index": 0,
      "verdict": "PASS",
      "evidence": "string, ≥50 chars, must reference file or test"
    }
  ],
  
  "scenario_results": [
    {
      "scenario_id": "TS-001",
      "verified": true,
      "evidence": "string, ≥30 chars"
    }
  ],
  
  "decisions": [
    {
      "type": "implementation",
      "issue": "string, ≥20 chars",
      "recommendation": "string, ≥30 chars",
      "reasoning": "string, ≥50 chars, must reference file",
      "alternatives_considered": ["string"]
    }
  ],
  
  "changes": [
    {
      "file_path": "string",
      "action": "create|edit|delete|rename|move",
      "summary": "string, ≥30 chars, unique per delivery",
      "reasoning": "string, ≥30 chars"
    }
  ],
  
  "findings": [
    {
      "type": "bug|improvement|risk|dependency|question",
      "severity": "HIGH|MEDIUM|LOW",
      "title": "string, ≥10 chars",
      "description": "string, ≥50 chars",
      "file_path": "string (optional)",
      "line_number": "int (optional)",
      "evidence": "string, ≥30 chars, must reference file",
      "suggested_action": "string (optional)"
    }
  ],
  
  "deferred": [
    {
      "requirement": "string",
      "reason": "string"
    }
  ]
}
```

**Response 200 (ACCEPTED):**
```json
{
  "status": "ACCEPTED",
  "task_status": "DONE",
  "validation": {
    "reasoning": {"status": "PASS", "checks": [...]},
    "ac_evidence": [{"ac_index": 0, "status": "PASS", "checks": [...]}],
    "scenario_results": [{"scenario_id": "TS-001", "status": "PASS"}],
    "decisions": [{"status": "PASS"}],
    "changes": [{"file_path": "cache/redis.py", "status": "PASS"}],
    "findings": [{"status": "PASS"}],
    "anti_patterns": {"duplicate_summaries": "PASS", "placeholders": "PASS", "copy_paste": "PASS"}
  },
  "completion": {
    "kr_updates": [{"kr_id": "KR-1", "old": 320, "new": 150, "status": "updated"}],
    "features_registered": ["GET /api/cache/stats"],
    "deferred_decisions_created": 0,
    "findings_created": 1
  },
  "next_available": true
}
```

**Response 422 (REJECTED):**
```json
{
  "status": "REJECTED",
  "attempt": 2,
  "validation": {
    "reasoning": {"status": "PASS", "checks": [...]},
    "ac_evidence": [
      {"ac_index": 0, "status": "FAIL", "reason": "evidence too short (28 < 50 chars)"}
    ],
    "scenario_results": [
      {"scenario_id": "TS-002", "status": "FAIL", "reason": "not verified"}
    ]
  },
  "fix_instructions": "Fix ac_evidence[0] (add more detail) and verify TS-002"
}
```

**Side effects on ACCEPTED:**
- Execution status → ACCEPTED
- Task status → DONE, completed_at set
- Changes → changes table (with execution_id link)
- Decisions → decisions table (with execution_id, task_id)
- Findings → findings table (status=OPEN)
- Deferred → decisions table (type=architecture, status=OPEN)
- KR auto-update (descriptive: NOT_STARTED→IN_PROGRESS→ACHIEVED)
- Feature registry update
- Test scenarios marked verified
- Audit log: "execution.accepted", "task.completed"

**Side effects on REJECTED:**
- Execution attempt recorded in execution_attempts
- Execution status stays IN_PROGRESS
- Lease extended by 15min
- Audit log: "execution.rejected"

---

#### `POST /api/v1/execute/{execution_id}/heartbeat`

**Cel:** AI sygnalizuje że żyje. Przedłuża lease.

**Response 200:**
```json
{
  "lease_expires_at": "2026-04-13T15:32:00Z",
  "renewals_remaining": 18
}
```

**Response 410 (Gone):** Execution expired (lease already expired).

**Side effects:** lease_expires_at = now + 30min. Max 20 renewals.

---

#### `POST /api/v1/execute/{execution_id}/decisions`

**Cel:** AI nagrywa decyzję w trakcie execution.

**Request body:**
```json
[{
  "type": "implementation",
  "issue": "string",
  "recommendation": "string",
  "reasoning": "string",
  "alternatives_considered": ["string"]
}]
```

**Response 201:** `{"created": ["D-042"]}`

**Validation:** Same as delivery decisions contract. Validated per optional.decisions rules.

---

#### `POST /api/v1/execute/{execution_id}/findings`

**Cel:** AI raportuje odkrycie w trakcie execution.

**Request body:**
```json
[{
  "type": "bug",
  "severity": "HIGH",
  "title": "string",
  "description": "string",
  "file_path": "string",
  "line_number": 78,
  "evidence": "string",
  "suggested_action": "string"
}]
```

**Response 201:** `{"created": ["F-001"]}`

---

#### `POST /api/v1/execute/{execution_id}/fail`

**Cel:** AI oznacza execution jako failed.

**Request body:**
```json
{
  "reason": "string, ≥50 chars"
}
```

**Response 200:** `{"task_status": "FAILED"}`

---

### 4.4 Endpoints — Planning (operator)

---

#### `POST /api/v1/projects/{slug}/plans/draft`

**Cel:** Złóż draft plan z taskami.

**Request body:**
```json
{
  "objective_id": "O-001",
  "tasks": [{
    "id": "_1",
    "name": "setup-schema",
    "description": "...",
    "instruction": "...",
    "type": "feature",
    "depends_on": [],
    "acceptance_criteria": [{
      "text": "Given...",
      "scenario_type": "positive",
      "verification": "test",
      "test_path": "tests/test_schema.py::test_create"
    }],
    "scopes": ["backend"],
    "knowledge_ids": ["K-001"],
    "produces": {"model": "User(id, email)"},
    "exclusions": []
  }],
  "assumptions": [{"assumption": "...", "basis": "...", "severity": "HIGH"}],
  "coverage": [{"requirement": "K-001", "status": "COVERED", "covered_by": "_1"}]
}
```

**Response 200:** Draft saved with validation results.
**Response 422:** Validation failed (≥5 HIGH assumptions, MISSING coverage, broken refs).

**Validations (blocking):**
- C1: Ingestion complete (if source docs exist)
- C2: Analysis complete (if source docs exist)
- Assumptions: <5 HIGH severity
- Coverage: no MISSING status
- Objective linkage: --objective required when objectives exist
- AC quality: fn_validate_ac_quality per task (feature/bug)
- Origin validation: O-NNN exists and ACTIVE
- Knowledge refs: K-NNN exists
- Scope validation: scopes match existing guidelines

---

#### `POST /api/v1/projects/{slug}/plans/{id}/approve`

**Cel:** Materializuj draft → real tasks.

**Response 200:**
```json
{
  "materialized": 5,
  "id_mapping": {"_1": "T-001", "_2": "T-002"},
  "test_scenarios_generated": 15,
  "warnings": []
}
```

**Validations (blocking):**
- DAG acyclic
- AC structured for feature/bug
- All refs valid (origin, knowledge_ids)
- Context validation (scopes match guidelines)
- Feature registry conflicts (WARNING)

**Side effects:**
- Tasks materialized in DB (temp IDs → T-NNN)
- Draft cleared
- Test scenarios auto-generated per task (fn_generate_test_scenarios)
- Source idea status → COMMITTED (if idea_id provided)
- Audit log: "plan.approved"

---

### 4.5 Endpoints — Entity CRUD (operator)

*Każda encja ma standardowy CRUD pattern:*

| Entity | POST (create) | GET (list) | GET (detail) | PUT (update) | DELETE |
|--------|---------------|------------|--------------|--------------|--------|
| `/projects/{slug}/knowledge` | `[{title, category, content, ...}]` | `?status=&category=&scope=` | `/{id}` | `[{id, content?, status?}]` | — |
| `/projects/{slug}/objectives` | `[{title, description, key_results}]` | `?status=` | `/{id}` (+ coverage) | `[{id, key_results?}]` | — |
| `/projects/{slug}/ideas` | `[{title, description, ...}]` | `?status=&category=&parent=` | `/{id}` | `[{id, status?}]` | — |
| `/projects/{slug}/ideas/{id}/commit` | — (POST) | — | — | — | — |
| `/projects/{slug}/guidelines` | `[{title, scope, content, weight}]` | `?scope=&weight=&status=` | `/{id}` | `[{id, status?}]` | — |
| `/projects/{slug}/decisions` | `[{type, issue, recommendation}]` | `?status=&type=&task=` | `/{id}` | `[{id, status?}]` | — |
| `/projects/{slug}/research` | `[{title, topic, category, summary}]` | `?status=&category=` | `/{id}` | `[{id, status?}]` | — |
| `/projects/{slug}/lessons` | `[{category, title, detail}]` | — | — | — | — |
| `/projects/{slug}/lessons/cross-project` | — | `?severity=&category=&tags=&limit=` | — | — | — |
| `/projects/{slug}/lessons/{id}/promote` | `{scope?, weight?}` | — | — | — | — |
| `/projects/{slug}/changes` | `[{task_id, file_path, action, summary}]` | `?task=` | — | — | — |
| `/projects/{slug}/gates` | `[{name, command, required}]` | — (GET shows config) | — | — | — |
| `/projects/{slug}/ac-templates` | `[{title, template, category}]` | `?category=&scope=` | `/{id}` | `[{id, template?}]` | — |
| `/projects/{slug}/ac-templates/{id}/instantiate` | `{params: {...}}` | — | — | — | — |

---

### 4.6 Endpoints — Triage & Ops (operator)

---

#### `POST /api/v1/findings/{id}/triage`

```json
{"action": "approve|defer|reject", "reason": "string"}
```

**On approve:** Creates new task T-NNN from finding context. Returns `{"created_task": "T-013"}`.

---

#### `POST /api/v1/decisions/{id}/resolve`

```json
{"status": "CLOSED|DEFERRED|ACCEPTED|MITIGATED", "resolution_notes": "string", "override_value": "string (optional)"}
```

---

### 4.7 Endpoints — Read (all roles)

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/projects` | Project list |
| `GET /api/v1/projects/{slug}/status` | Pipeline dashboard (task counts, KR progress) |
| `GET /api/v1/projects/{slug}/tasks` | Task list with filters (?status=, ?objective=) |
| `GET /api/v1/projects/{slug}/tasks/{id}` | Task detail with AC, deps, execution history |
| `GET /api/v1/projects/{slug}/executions` | Execution list with filters (?task=, ?status=) |
| `GET /api/v1/projects/{slug}/executions/{id}` | Execution detail: prompt + delivery + validation |
| `GET /api/v1/projects/{slug}/executions/{id}/prompt` | Prompt breakdown: sections, elements, excluded, reasons |
| `GET /api/v1/projects/{slug}/findings` | Finding triage queue (?status=OPEN) |
| `GET /api/v1/projects/{slug}/audit` | Audit trail (?entity_type=, ?limit=50) |
| `GET /api/v1/projects/{slug}/knowledge/link?entity_type=objective&entity_id=O-001` | Knowledge linked to entity |

---

## 5. Prompt Assembly Engine

### 5.1 Sekcje (priorytet → kolejność)

| P | Sekcja | Source | Obcinalna? | Max % |
|---|--------|--------|-----------|-------|
| 1 | task_content | tasks + acceptance_criteria + test_scenarios | NIE | 30% |
| 1 | must_guidelines | guidelines WHERE weight=must, scope match | NIE | 10% |
| 2 | required_knowledge | task_knowledge → knowledge | NIE | 15% |
| 3 | scope_knowledge | knowledge WHERE scope match, max 10 | TAK | 10% |
| 4 | should_guidelines | guidelines WHERE weight=should, scope match | TAK | 10% |
| 5 | dependency_context | deps → produces + changes | TAK | 10% |
| 6 | active_risks | decisions WHERE type=risk, not closed | TAK | 5% |
| 7 | business_context | objectives → key_results | TAK | 5% |
| 8 | test_context | gates config | TAK | 5% |

**P1 overflow rule:** If P1 sections > 70% budget → ERROR, execution not created. Operator must reduce MUST guidelines or increase budget.

**SHOULD removal rule:** If total > 80% budget after P1-P3 → SHOULD guidelines excluded entirely.

### 5.2 Element storage (3 levels)

**Level 1: executions** — pełny tekst + metadata
- `prompt_text`: complete markdown
- `prompt_hash`: SHA-256
- `prompt_meta`: {sections, elements, included, excluded, total_kb, budget_kb, scopes, lean}

**Level 2: prompt_sections** — per sekcja
- `section_name`, `priority`, `included`, `exclusion_reason`, `rendered_text`, `char_count`, `position`, `element_count`

**Level 3: prompt_elements** — per element
- `source_table`, `source_id`, `source_external_id`, `source_version`
- `content_snapshot` — zamrożona kopia treści w momencie assembly
- `included`, `selection_reason`, `exclusion_reason`
- `scope_details` — {task_scopes, element_scope, matched, match_via}
- `budget_details` — {budget_total_kb, used_before_kb, element_kb, would_exceed}

---

## 6. Contract Validation Engine

### 6.1 Contract lookup

```
fn_get_contract(task_type, ceremony_level):
  1. SELECT FROM output_contracts WHERE task_type={type} AND ceremony_level={ceremony} AND active=true ORDER BY version DESC LIMIT 1
  2. If not found: SELECT WHERE task_type='*' AND ceremony_level={ceremony}
  3. If not found: SELECT WHERE task_type={type} AND ceremony_level='*'
  4. If not found: SELECT WHERE task_type='*' AND ceremony_level='*' (default)
```

### 6.2 Ceremony detection

```
fn_determine_ceremony(task_type, ac_count, diff_file_count):
  IF task_type IN ('chore', 'investigation'): return 'LIGHT'
  IF task_type = 'bug' AND diff_file_count <= 3: return 'LIGHT'
  IF task_type = 'feature' AND ac_count <= 3: return 'STANDARD'
  return 'FULL'
```

### 6.3 Validation pipeline

```
fn_validate_delivery(execution_id, delivery):
  contract = execution.contract (snapshot from GET /execute)
  results = {}
  all_pass = true

  -- 1. Reasoning
  IF contract.required.reasoning:
    r = validate_text(delivery.reasoning, contract.required.reasoning)
    results.reasoning = r
    IF r.status = 'FAIL': all_pass = false

  -- 2. AC Evidence
  IF contract.required.ac_evidence:
    ac_list = load acceptance_criteria for task
    FOR EACH ac IN ac_list:
      IF ac.verification IN ('test', 'command'):
        -- Mechanical: run test/command, check exit code
        r = run_mechanical_ac(ac)
        results.ac_mechanical[ac.position] = r
        IF r.status = 'FAIL': all_pass = false
      ELSE:
        -- Manual: check delivery.ac_evidence[ac_index]
        evidence = find delivery.ac_evidence WHERE ac_index = ac.position
        IF evidence IS NULL:
          results.ac_evidence[ac.position] = {status: 'FAIL', reason: 'missing'}
          all_pass = false
        ELSE:
          r = validate_evidence(evidence, contract.required.ac_evidence)
          results.ac_evidence[ac.position] = r
          IF r.status = 'FAIL': all_pass = false
    
    -- AC composition check
    negative_pass = any(e.verdict='PASS' AND ac.scenario_type IN ('negative','edge_case') 
                        FOR e, ac IN zip(delivery.ac_evidence, ac_list))
    IF NOT negative_pass AND task.type IN ('feature', 'bug'):
      results.ac_composition = {status: 'FAIL', reason: 'no negative scenario passed'}
      all_pass = false

  -- 3. Scenario Results
  scenarios = load test_scenarios for task
  IF scenarios:
    FOR EACH ts IN scenarios:
      result = find delivery.scenario_results WHERE scenario_id = ts.external_id
      IF result IS NULL:
        results.scenarios[ts.external_id] = {status: 'FAIL', reason: 'not verified'}
        all_pass = false
      ELIF ts.verification = 'grep_check':
        -- API mechanically verifies grep in git diff
        grep_result = run_grep_on_diff(ts.verification_detail)
        IF NOT grep_result:
          results.scenarios[ts.external_id] = {status: 'FAIL', reason: 'grep not found in diff'}
          all_pass = false
        ELSE:
          results.scenarios[ts.external_id] = {status: 'PASS'}
      ELSE:
        r = validate_text(result.evidence, {min_length: 30})
        results.scenarios[ts.external_id] = r
        IF r.status = 'FAIL': all_pass = false

  -- 4. Optional outputs (lazy validation)
  IF delivery.decisions:
    FOR EACH d IN delivery.decisions:
      r = validate_decision(d, contract.optional.decisions)
      results.decisions[] = r
      IF r.status = 'FAIL': all_pass = false

  IF delivery.changes:
    FOR EACH c IN delivery.changes:
      r = validate_change(c, contract.optional.changes)
      results.changes[] = r
      IF r.status = 'FAIL': all_pass = false

  IF delivery.findings:
    FOR EACH f IN delivery.findings:
      r = validate_finding(f, contract.optional.findings)
      results.findings[] = r
      IF r.status = 'FAIL': all_pass = false

  -- 5. Anti-patterns
  IF contract.anti_patterns:
    IF contract.anti_patterns.duplicate_summaries_threshold:
      -- Check pairwise similarity of change summaries
      -- Using trigram similarity (pg_trgm): similarity(a, b) < threshold
      FOR EACH pair IN combinations(delivery.changes, 2):
        sim = pg_trgm_similarity(pair[0].summary, pair[1].summary)
        IF sim >= contract.anti_patterns.duplicate_summaries_threshold:
          results.anti_patterns.duplicate_summaries = {status: 'FAIL', 
            detail: pair[0].file_path + ' vs ' + pair[1].file_path, similarity: sim}
          all_pass = false
    
    IF contract.anti_patterns.placeholder_patterns:
      FOR EACH pattern IN contract.anti_patterns.placeholder_patterns:
        IF pattern IN LOWER(delivery.reasoning):
          results.anti_patterns.placeholders = {status: 'FAIL', pattern: pattern}
          all_pass = false

    IF contract.anti_patterns.copy_paste_evidence:
      -- Check AC evidence pairwise uniqueness
      FOR EACH pair IN combinations(delivery.ac_evidence, 2):
        sim = pg_trgm_similarity(pair[0].evidence, pair[1].evidence)
        IF sim >= 0.8:
          results.anti_patterns.copy_paste = {status: 'FAIL'}
          all_pass = false

  -- 6. Resubmit detection
  prev_attempt = load previous execution_attempt for this execution
  IF prev_attempt AND NOT all_pass:
    -- Same checks failed before
    prev_failures = extract failed checks from prev_attempt.validation_result
    curr_failures = extract failed checks from results
    IF overlap(prev_failures, curr_failures) AND text_diff(delivery, prev_attempt.delivery) < 0.2:
      results.resubmit = {status: 'WARN', detail: 'insufficient changes since last rejection'}

  RETURN {all_pass, results}
```

---

## 7. Przepływy — kompletne

### 7.1 Pełny pipeline (z source documents)

```
POST /knowledge (source-doc) ←─ user uploads document
  │
  ├─ POST /knowledge (requirements × N) ←─ AI/user extracts facts
  ├─ POST /decisions (conflicts, assumptions) ←─ AI/user flags issues
  ├─ POST /research (ingestion record) ←─ AI records extraction
  │
  ▼ GATE C1: validate_ingestion (9 categories, ≥2 facts/doc)
  │
POST /decisions/{id}/resolve (close OPEN decisions) ←─ user/AI resolves
  │
POST /objectives (with key_results[]) ←─ AI groups requirements into objectives
  │
  ├─ POST /knowledge/link (K→O linkage) ←─ AI links requirements
  │
  ▼ GATE C2: validate_analysis (≥1 ACTIVE O, all KR measured, all K linked)
  │
POST /plans/draft (tasks + assumptions + coverage) ←─ AI decomposes
  │
  ├─ GATE C3: AC quality, origin refs, knowledge refs, coverage, assumptions
  │
POST /plans/{id}/approve ←─ user/AI approves
  │
  ├─ GATE C4: DAG acyclic, AC structured, refs valid, context valid
  ├─ SIDE EFFECT: fn_generate_test_scenarios per task
  │
  ▼
GET /execute ←─ AI agent requests work
  │
  ├─ PROMPT ASSEMBLED: instruction + AC + TS + guidelines + knowledge + deps + risks
  ├─ CONTRACT ATTACHED: what AI must return per ceremony level
  │
  ├─ POST /heartbeat (every 10 min) ←─ AI keeps lease alive
  ├─ POST /decisions (optional mid-execution) ←─ AI records choices
  ├─ POST /findings (optional mid-execution) ←─ AI reports discoveries
  │
POST /deliver ←─ AI submits results
  │
  ├─ VALIDATION: reasoning + AC evidence + scenario results + anti-patterns
  │
  ├─ IF ACCEPTED:
  │   ├─ Task → DONE
  │   ├─ Changes → changes table
  │   ├─ Decisions → decisions table
  │   ├─ Findings → findings table (OPEN)
  │   ├─ KR auto-update
  │   ├─ Feature registry update
  │   ├─ GATE C7: if last task for O-NNN → check all KRs
  │   └─ → GET /execute (next task)
  │
  └─ IF REJECTED:
      ├─ Attempt recorded
      ├─ Lease extended 15min
      └─ AI fixes and re-delivers
```

### 7.2 Discovery (optional, pre-planning)

```
POST /research (explore/risk/architecture analysis) ←─ AI runs deep-* skills
POST /decisions (exploration + risk decisions) ←─ AI records findings
  │
  └─ → feeds /plans/draft (risks become test_scenarios, decisions inform plan)
```

### 7.3 Change Request (mid-flight)

```
POST /knowledge (new/updated requirement) ←─ user/AI adds K-NNN
POST /decisions (impact assessment) ←─ AI assesses impact
  │
  ├─ Minor: PUT /tasks/{id} (update AC)
  ├─ Moderate: POST /plans/draft (add tasks)
  ├─ Major: POST /objectives (new objective) → POST /plans/draft
  └─ Breaking: POST /tasks/reset + full re-plan
```

### 7.4 Finding Triage

```
GET /findings?status=OPEN ←─ operator reviews in Web UI
POST /findings/{id}/triage ←─ operator decides
  │
  ├─ approve → new task T-NNN created from finding context
  ├─ defer → status DEFERRED, appears in future task briefings
  └─ reject → status REJECTED, archived
```

### 7.5 Compound (post-project learning)

```
POST /lessons (learnings from project) ←─ AI/user records
POST /lessons/{id}/promote ←─ operator promotes critical lessons
  │
  ├─ → new guideline G-NNN (global or project)
  └─ → new knowledge K-NNN
```

---

## 8. Edge cases i odporność

| Scenariusz | Zachowanie | Mechanizm |
|---|---|---|
| AI crash mid-execution | Lease expires (30min) → execution EXPIRED → task → TODO | lease_expires_at + cron fn_expire_stale_executions |
| AI delivers partial results | REJECTED — all required fields checked | Contract validation |
| Delivery validation fails | REJECTED with per-field details → AI fixes → resubmit | execution_attempts tracking |
| AI padding after rejection | API compares delivery n vs n-1, flags if diff < 20% | execution_attempts.diff_from_previous |
| Two agents claim same task | SELECT FOR UPDATE SKIP LOCKED | DB locking |
| Guideline changed during execution | Prompt snapshot in prompt_elements | content_snapshot frozen at assembly |
| Knowledge updated during execution | Same — snapshot in prompt_elements | content_snapshot frozen |
| P1 sections > budget | ERROR — execution not created | fn_assemble_prompt overflow check |
| 50 MUST guidelines → 50 test scenarios | Cap: max 10 TS per task, prioritized by risk severity | fn_generate_test_scenarios cap |
| Task without instruction or description | CHECK constraint → 422 error at creation | DB constraint |
| Cross-project dependency | Trigger rejects INSERT | fn_check_same_project_dep trigger |
| Audit log growth | Monthly partitioning + retention policy | PARTITION BY RANGE (created_at) |
| API restart mid-execution | Stateless — execution in DB, AI retries | PostgreSQL durability |
| Finding → task → circular dep | fn_approve_finding creates task with depends_on=[] | No circular risk |
| Max heartbeat renewals exceeded (200min) | Execution EXPIRED | max_renewals=20 check |
| AI calls triage endpoint | 403 Forbidden (executor role can't triage) | api_keys role check |
| Contract version changes mid-execution | Contract snapshot in execution.contract | Frozen at GET /execute |
| Gate timeout (test takes >120s) | Gate marked FAIL with timeout output | subprocess timeout |
| AC with verification=test but test doesn't exist | Mechanical AC runner returns FAIL (file not found) | pytest exit code |
| Delivery max attempts exceeded | After 5 attempts → execution FAILED, task → FAILED | max_attempts=5 in contract |
| Legitimate small fix rejected by diff < 20% | Check only when SAME check failed before, not globally | conditional resubmit detection |

---

## 9. Otwarte problemy i ich rozwiązania

### Problem 1 (CRITICAL): Kto jest klientem API?

**Problem:** API opisane jak gdyby AI natively rozumiała protokół GET /execute → POST /deliver. W rzeczywistości Claude Code operuje przez bash, file I/O, i narzędzia. Potrzebny jest agent-klient.

**Rozwiązanie: Forge Agent — MCP Server**

```
┌─────────────────────────────────────────────────────┐
│  Claude Code                                         │
│  Zna narzędzia:                                      │
│    forge_execute()  → GET /execute, zwraca prompt    │
│    forge_deliver()  → POST /deliver, oddaje wyniki   │
│    forge_heartbeat()→ POST /heartbeat                │
│    forge_decision() → POST /decisions                │
│    forge_finding()  → POST /findings                 │
│    forge_fail()     → POST /fail                     │
│                                                       │
│  Claude Code wywołuje narzędzia jak każde inne.      │
│  Nie musi wiedzieć o HTTP, JSON, API keys.           │
└──────────────┬───────────────────────────────────────┘
               │ MCP protocol (tool calls)
               ▼
┌─────────────────────────────────────────────────────┐
│  Forge MCP Server (Python process)                   │
│                                                       │
│  Tłumaczy tool calls → HTTP API calls:              │
│    forge_execute()  → GET /api/v1/execute            │
│    forge_deliver()  → POST /api/v1/execute/{id}/deliver │
│                                                       │
│  Zarządza:                                            │
│    - API key (executor role)                         │
│    - Heartbeat w background thread (co 10 min)       │
│    - execution_id state (pamięta aktywne execution)  │
│    - Retry logic na network errors                   │
│                                                       │
│  Heartbeat: background thread, nie AI.               │
│  AI nie musi przerywać pracy co 10 min.              │
└──────────────┬───────────────────────────────────────┘
               │ HTTP (localhost lub remote)
               ▼
┌─────────────────────────────────────────────────────┐
│  Forge API (FastAPI)                                 │
└─────────────────────────────────────────────────────┘
```

**Narzędzia MCP (co Claude Code widzi):**

| Narzędzie | Parametry | Zwraca |
|-----------|-----------|--------|
| `forge_execute` | project, agent?, lean? | instruction, AC, guidelines, context (prompt), contract |
| `forge_deliver` | reasoning, ac_evidence, scenario_results, decisions?, changes?, findings?, deferred?, assumptions?, unhandled_scenarios?, scope_interpretation?, impact_analysis?, confidence? | ACCEPTED + completion summary / REJECTED + fix instructions |
| `forge_decision` | type, issue, recommendation, reasoning | created decision ID |
| `forge_finding` | type, severity, title, description, evidence | created finding ID |
| `forge_fail` | reason | task marked FAILED |

AI nie wie o HTTP, API keys, heartbeat, lease. MCP Server to obsługuje.

**Heartbeat:** Background thread w MCP Server. Startuje na `forge_execute()`. Wysyła POST /heartbeat co 10 min. Stopuje na `forge_deliver()` lub `forge_fail()`. AI nigdy nie musi o tym wiedzieć.

**Alternatywa bez MCP:** Custom CLI wrapper. `forge-agent execute` → calls API → prints prompt. `forge-agent deliver --file result.json` → calls API → prints validation. Działa z każdym LLM, nie tylko Claude Code. Mniej eleganckie ale prostsze.

---

### Problem 2 (HIGH): Statyczny prompt vs. dynamiczny kontekst

**Problem:** Prompt jest assembled raz (GET /execute) i zamrożony. AI w trakcie pracy odkrywa kontekst którego potrzebuje (np. config.py nie był w promptcie bo nikt go nie zalinkował). 30-50% kontekstu AI odkrywa w trakcie.

**Rozwiązanie: Prompt jest startowy, AI ma dynamiczny dostęp**

Prompt assembly daje STARTOWY kontekst — to co system wie że jest relevantne. AI ma ZAWSZE dostęp do kodu (Read, Grep, Glob) — nie jest ograniczona do promptu.

Różnica: prompt jest AUDYTOWANY (wiemy co daliśmy). Dynamiczny kontekst jest NIEAUDYTOWANY (AI sama go szuka). To jest OK — prompt daje baseline, AI uzupełnia.

**Dodatkowy endpoint (opcjonalny):**

```
POST /api/v1/execute/{execution_id}/context-request
{
  "reason": "Need to understand config.py structure for REDIS_URL setup",
  "files_read": ["config.py", "config.py:imports"],
  "knowledge_requested": "K-012"
}
```

API loguje to jako `context_extensions` w execution record. Nie blokuje AI — AI czyta plik normalnie. Ale system wie JAKIE dodatkowe pliki AI czytała i DLACZEGO.

**Pragmatyczne podejście:** V1 bez context-request endpoint. AI czyta co chce. prompt_elements daje audit na startowy kontekst. Dodanie context_extensions w V2 jeśli okaże się potrzebne.

---

### Problem 3 (MEDIUM): Rule-based validation ceiling

**Problem:** reject_patterns, must_contain_why, min_length — whack-a-mole. AI nauczy się wstawiać "because" mechanicznie.

**Rozwiązanie: Akceptuj ceiling + human review + trust calibration**

1. **Rule-based (automatyczne):** Łapie ~60% problemów (oczywisty filler, brak referencji, copy-paste). Tani. Zawsze włączony.

2. **Trust calibration (automatyczne):** System śledzi korelację: claimed confidence vs. operator acceptance rate. Jeśli AI deklaruje 0.9 ale operator odrzuca 40% → trust score spada → więcej tasków trafia do review. Nie łapie gamingu per-delivery ale łapie TREND.

3. **Human review (per ceremony level):**
   - LIGHT: brak review — trust system
   - STANDARD: review jeśli trust score < 0.7
   - FULL: zawsze review przez operator w Web UI

**NIE robić:** Ciągle dodawać nowe reject patterns. Marginal cost rośnie, marginal benefit maleje.

---

### Problem 4 (LOW): Rejection loop bez max attempts

**Rozwiązanie:** `max_attempts = 5` per execution. Po 5 attemptach → execution FAILED → task FAILED → operator musi zdecydować (re-assign, rewrite instruction, lub skip).

Resubmit detection: sprawdzaj diff < 20% TYLKO gdy ten sam check failuje co poprzednio. Legitimate small fix (bug fix w jednym znaku) nie triggeruje bo OTHER checks też się zmieniają.

---

### Problem 5 (MEDIUM): Heartbeat operacyjna złożoność

**Rozwiązany przez Problem 1:** MCP Server zarządza heartbeat w background thread. AI nie wie o heartbeat. Max 20 renewals = 200 min = 3h 20min. Jeśli za mało dla dużych tasków → operator zwiększa max renewals w project config.

---

### Problem 6 (LOW): grep_check kruchość

**Akceptowalne ograniczenie.** grep_check jest heurystyką, nie weryfikacją. Łapie oczywiste pominięcia (guideline mówi "StorageAdapter" ale AI nie importuje go w ogóle). Nie łapie subtletnych (AI importuje ale nie implementuje).

Fix: grep_check z `verification: grep_check` jest LOW priority test scenario. MUST guidelines powinny mieć AC z `verification: test` (nie grep). grep jest fallback, nie primary mechanism.

---

### Problem 7 (HIGH): MVP slice

**38 tabel to docelowy stan. MVP ma 12 tabel.**

```
MVP (prove the thesis — 2-3 weeks):
├── projects
├── tasks + task_dependencies
├── acceptance_criteria
├── executions + prompt_sections + prompt_elements
├── changes
├── decisions
├── guidelines
├── gates + gate_results
├── audit_log
└── output_contracts

TIER 2 (after MVP works — 2 weeks):
├── objectives + key_results
├── knowledge + task_knowledge + knowledge_objective_links
├── test_scenarios
├── execution_attempts
├── findings

TIER 3 (when needed):
├── ideas + idea_relations + idea_key_result_links
├── research + research_decisions
├── lessons + lesson_decisions
├── ac_templates
├── skills
├── api_keys
├── remaining link tables
├── operational contract tables (assumptions, impact, confidence)
```

MVP wystarczy żeby: złożyć prompt z guidelines + task content, zebrać delivery z validation, i zapisać audit trail. To testuje core thesis.

---

### Problem 8 (LOW): fn_generate_test_scenarios complexity

**Rozwiązanie: Defer do Tier 2.** MVP nie ma test_scenarios. AC wystarczą. Po udowodnieniu że AC quality gate działa — dodaj auto-generated scenarios.

---

### Problem 9 (MEDIUM): Granica executor/operator

**Rozwiązanie: Dwa tryby pracy AI**

| Faza | AI rola | Endpoints |
|------|---------|-----------|
| Ingestion | `planner` (rozszerzony executor) | POST /knowledge, POST /decisions, POST /research |
| Analysis | `planner` | POST /objectives, POST /knowledge/link, POST /decisions |
| Planning | `planner` | POST /plans/draft |
| Execution | `executor` | GET /execute, POST /deliver, POST /heartbeat, POST /decisions, POST /findings |
| Triage/Review | `operator` (human only) | POST /triage, POST /resolve, POST /approve |

`planner` = executor + write access to knowledge, objectives, plans. Ale NIE triage, NIE approve, NIE guidelines modify.

`operator` = human-only actions: approve plan, triage findings, resolve decisions, modify guidelines.

To daje jasną granicę: AI planuje i wykonuje. Człowiek zatwierdza i triage'uje.

---

### Problem 10 (LOW): pg_trgm runtime cost

**Rozwiązanie:** Compute w Python (application layer), nie per-pair DB call. `difflib.SequenceMatcher` w Pythonie jest O(n*m) per pair ale fast enough for <50 changes. Batch w pamięci, nie N queries.

---

## 10. Kontrakt Operacyjny w API (feedback loops)

### Rozszerzenie delivery

Delivery body rozszerzony o 7 sekcji z kontraktu operacyjnego. Każda sekcja jest `optional_but_tracked` — AI nie musi podać, ale jeśli poda, system reaguje. Jeśli NIE poda a potem wyjdzie problem → system obniża trust score.

**Rozszerzony POST /deliver request body:**

```json
{
  "reasoning": "...",
  "ac_evidence": [...],
  "scenario_results": [...],
  "decisions": [...],
  "changes": [...],
  "findings": [...],
  "deferred": [...],
  
  "assumptions": [
    {
      "statement": "Redis dostępny na localhost:6379",
      "verified": false,
      "if_wrong": "App crash at startup, no fallback",
      "verify_how": "Check docker-compose.yml for redis service",
      "severity": "HIGH",
      "affected_files": ["cache/redis.py:12", "config.py:45"]
    }
  ],
  
  "unhandled_scenarios": [
    {
      "scenario": "Redis connection drops mid-request",
      "what_happens": "500 Internal Server Error, no retry",
      "probability": "MEDIUM",
      "impact": "HIGH",
      "mitigation_suggestion": "Add circuit breaker with fallback"
    }
  ],
  
  "scope_interpretation": {
    "chosen": "Read-through cache only (GET requests)",
    "alternatives": [
      {
        "interpretation": "Full cache with write-through",
        "why_not": "Requires event bus not yet implemented",
        "what_user_loses": "Stale data for up to TTL after writes"
      }
    ],
    "instruction_ambiguities": ["'Add Redis caching' — doesn't specify read vs write"]
  },
  
  "impact_analysis": {
    "files_changed": ["cache/redis.py", "config.py"],
    "files_checked_for_impact": [
      {"path": "api/items.py", "checked": true, "impact": "none"},
      {"path": "tests/test_items.py", "checked": true, "impact": "needs_update"}
    ],
    "files_not_checked": [
      {"path": "api/reports.py", "reason": "Not in scope but imports config.py", 
       "risk": "May break if REDIS_URL env missing"}
    ]
  },
  
  "confidence": {
    "overall": 0.7,
    "unverified_claims": [
      {
        "claim": "TTL 300s sufficient for this use case",
        "confidence": 0.4,
        "why_uncertain": "No perf requirements in knowledge",
        "user_should_verify": "Check with product owner"
      }
    ]
  },
  
  "partial_implementation": {
    "completed_elements": ["CacheAdapter", "GET endpoint", "TTL config"],
    "omitted_elements": [
      {
        "element": "Cache invalidation on write",
        "why_omitted": "Requires event bus (T-008)",
        "risk_without": "Stale data up to TTL",
        "affected_locations": ["api/items.py:PUT"],
        "completion_plan": "After T-008, add invalidate() in PUT"
      }
    ],
    "is_functional_without_omitted": true
  },

  "propagation_check": {
    "changed_interfaces": [
      {
        "interface": "config.REDIS_URL",
        "type": "new_env_var",
        "used_by": ["cache/redis.py:12"],
        "should_also_update": [
          {"file": ".env.example", "updated": true},
          {"file": "docker-compose.yml", "updated": true},
          {"file": "docs/deployment.md", "updated": false, "reason": "Not in scope"}
        ]
      }
    ]
  }
}
```

### Jak API reaguje na każdą sekcję

| Sekcja | API reaction | Feedback loop |
|--------|-------------|---------------|
| `assumptions` (unverified) | → tworzy records w task_assumptions → następny task na tych plikach dostaje w promptcie "Unverified: ..." | Założenie propaguje się aż ktoś je zweryfikuje |
| `unhandled_scenarios` (HIGH impact) | → tworzy risk decisions (type=risk, OPEN) → pojawia się w P6 active_risks w promptach | Ryzyko widoczne do zamknięcia |
| `scope_interpretation` (ambiguity) | → tworzy OPEN decision (type=clarification) → operator rozstrzyga w Web UI | Niejednoznaczność jawna, nie milcząca |
| `impact_analysis` (files_not_checked) | → tworzy findings (type=risk) → następny task na tych plikach dostaje test scenario | Niesprawdzone pliki nie są zapomniane |
| `confidence` (overall < 0.5) | → task marked needs_review → operator review w Web UI | Niska pewność = human check |
| `confidence` (unverified_claims) | → tworzy OPEN decisions (type=verification_needed) | Twierdzenie do sprawdzenia |
| `partial_implementation` (omitted, nonfunctional) | → REJECT delivery. Nie można oddać niefunkcjonalnego kodu. | Hard block |
| `partial_implementation` (omitted, functional) | → tworzy blocked tasks z completion_plan → WARNING na KR | Pominięcie staje się taskiem |
| `propagation_check` (not updated) | → tworzy findings → mechanical grep verify (API grep repo for pattern) | System sprawdza czy AI nie pominęła pliku |

### Trust calibration (system uczy się z historii)

```
Per agent, per project, system śledzi:
  - declared_confidence_avg: średnia z delivery.confidence.overall
  - operator_acceptance_rate: % deliveries accepted bez operator override
  - correlation: declared vs actual

Jeśli correlation < 0.5 (AI mówi "0.9 confidence" ale operator odrzuca 40%):
  → trust_score spada
  → więcej tasków trafia do needs_review
  → kontrakt automatycznie dodaje mandatory fields (np. assumptions stają się required)

Jeśli correlation > 0.8:
  → trust_score rośnie
  → mniej tasków wymaga review
  → kontrakt łagodzi requirements (np. LIGHT ceremony wystarczy dla feature)
```

### Tabelki (Tier 3 — nie MVP)

Te sekcje delivery nie wymagają osobnych tabel w MVP. Można je przechowywać jako JSONB w `executions.delivery`. Osobne tabele (task_assumptions, unhandled_scenarios, etc.) dodać w Tier 3 gdy potrzebne querowanie.

---

## 11. Meta-Prompting Engine — fundamentalny model wykonawczy

### 11.1 Zmiana modelu: od "fixed prompt" do "fabryki poleceń"

**Stary model (odrzucony):**
```
Forge API → składa fixed prompt → AI wykonuje → oddaje wynik → API waliduje
```

**Nowy model:**
```
DLA KAŻDEJ OPERACJI (spec, plan, implement, verify, challenge):

  FAZA 1: PREPARE — Agent-A pisze POLECENIE dla Agent-B
    Input:  kontekst z Forge API (requirements, AC, guidelines, risks, decisions)
    Actor:  Agent-A (preparer)
    Output: surowe polecenie — CO Agent-B ma zrobić, NA CO zwrócić uwagę,
            JAKIE wymagania uwzględnić, CO sprawdzić
    
  FAZA 2: ENRICH — Prompt Parser wzbogaca polecenie
    Input:  surowe polecenie + dane z Forge API
    Actor:  System (deterministyczny, mechaniczny)
    Dodaje: 
      - Reputation framing (dopasowany do typu operacji)
      - Micro-skills (wybrane na podstawie typu + profilu ryzyka)
      - Kontekst z API (requirements, guidelines, knowledge, deps, risks)
      - Agent memory (mistakes, decisions, files known)
      - Kontrakt operacyjny (ZAWSZE. OBOWIĄZKOWO. JAKO OSTATNI.)
    Output: wzbogacone polecenie gotowe do wykonania
    
  FAZA 3: EXECUTE — Agent-B wykonuje wzbogacone polecenie
    Input:  wzbogacone polecenie
    Actor:  Agent-B (executor) — INNY kontekst niż Agent-A
    Output: wynik w ustrukturyzowanym formacie (zdefiniowanym w poleceniu)
    
  FAZA 4: VALIDATE & RECORD — API przetwarza wynik
    Input:  ustrukturyzowany wynik
    Actor:  Forge API (system)
    Actions: waliduje kontrakt, zapisuje zmiany/decyzje/findings,
             aktualizuje agent memory, propaguje assumptions
    Output: ACCEPTED/REJECTED + następny krok
```

### 11.2 Jak to działa per typ operacji

**SPECYFIKACJA FEATURE:**
```
Agent-A dostaje od Forge API: 
  - Requirements K-001..K-005 (powiązane z objective O-001)
  - Decisions D-001..D-003 (architektoniczne, zamknięte)
  - Guidelines G-001, G-010 (MUST, scope: backend)
  - Existing code structure (z file_index)

Agent-A pisze polecenie:
  "Napisz specyfikację dla modułu settlement report która:
   - Definiuje INPUT: tabele BQ rpt_daily_estimation, invoices (z K-002)
   - Definiuje OUTPUT: kolumny beginning_balance, newly_submitted, collected, ending_balance
   - Podaje FORMUŁĘ dla każdej kolumny (skąd dane, jak liczyć)
   - Uwzględnia EDGE CASES: settlement przed purchase (z D-002), partial settlement, 
     brak danych za dany okres, różne typy dokumentów (invoice, payment, return z K-004)
   - Definiuje ACCEPTANCE CRITERIA które właściciel biznesowy (Tuan) może zweryfikować
   - Wynik w formacie: {input: [], output: [], rules: [], edge_cases: [], acceptance: {}}"

Prompt Parser wzbogaca:
  + "Jakby ktoś powiedział że jesteś najlepszym analitykiem biznesowym który 
     nigdy nie pomija edge cases, zawsze definiuje formuly precyzyjnie, 
     i tworzy specyfikacje z których można implementować bez pytań..."
  + Micro-skill: "requirements precision" (sprawdź każde wymaganie atomowo)
  + Micro-skill: "edge case explorer" (dla każdej reguły: co jeśli dane puste? 
     co jeśli typy inne? co jeśli kolejność inna?)
  + Knowledge K-001..K-005 (pełna treść requirements)
  + Guideline G-001 (Firestore only — wpływa na data access pattern)
  + Kontrakt operacyjny (OBOWIĄZKOWY)

Agent-B wykonuje → oddaje structured spec → Forge API zapisuje jako knowledge 
  (category: "feature-spec")
```

**PLANOWANIE:**
```
Agent-A dostaje od Forge API:
  - Objective O-001 z KR
  - Feature specs (z poprzedniego kroku)
  - Guidelines (project + global)
  - Existing tasks (completed, dependencies)
  - Feature registry (co już istnieje)

Agent-A pisze polecenie:
  "Stwórz plan zadań dla O-001 który:
   - Pokrywa KAŻDE wymaganie z spec SPEC-001 (input, output, rules, edge cases)
   - Dla KAŻDEGO zadania tworzy AC derived FROM spec (nie wymyślone):
     - AC positive: z spec.rules
     - AC negative: z spec.edge_cases 
     - AC z verification=test (minimum 1 per task)
   - Uwzględnia zależności: T-003 produces connection pool (dependency contract)
   - NIE duplikuje: Feature Registry ma POST /api/orders (z T-002)
   - Format: {tasks: [{instruction, AC, depends_on, produces, scopes}], 
              assumptions: [], coverage: []}"

Prompt Parser wzbogaca:
  + "Jakby ktoś powiedział że jesteś najlepszym architektem który 
     dekomponuje systemy na pionowe slice'y, nigdy nie tworzy generic AC,
     i zawsze testuje cold-start: 'wklej instruction w pusty kontekst — 
     agent wie jaki plik otworzyć?'..."
  + Micro-skill: "dependency contract verifier" (każdy depends_on → produces match?)
  + Micro-skill: "AC from spec" (AC musi pochodzić z spec, nie z wyobraźni)
  + Feature specs SPEC-001, SPEC-002 (pełna treść)
  + Guidelines MUST (pełna treść)
  + Kontrakt operacyjny (OBOWIĄZKOWY)

Agent-B wykonuje → oddaje plan → Forge API waliduje (AC quality, DAG, coverage) → approve
```

**IMPLEMENTACJA:**
```
Agent-A dostaje od Forge API:
  - Task T-005 (instruction, AC, dependencies, produces, scopes)
  - Feature spec SPEC-003 (rules, edge cases)
  - Dependency outputs (T-003 produces, T-003 changes)
  - Guidelines (MUST filtered by scope)
  - Agent memory (mistakes, decisions, files known)
  - Test scenarios (auto-generated z guidelines + risks)

Agent-A pisze polecenie:
  "Zaimplementuj task T-005 (Redis caching):
   - Stwórz cache/redis.py implementujący StorageAdapter (z G-001, wzorzec z pool.py)
   - Dodaj REDIS_URL do config.py (sekcja [cache])
   - Napisz testy: test_hit, test_miss, test_redis_down (z AC), test_corrupt_entry (z spec edge case)
   - UWAGA: w T-003 zapomniałeś zaktualizować .env.example po zmianie config — NIE ZAPOMNIJ
   - UWAGA: config.py importowany przez api/items.py, api/reports.py, api/auth.py — sprawdź impact
   - NIE MODYFIKUJ db/pool.py (exclusion z T-005)
   - Wynik: {reasoning, ac_evidence, changes, decisions, assumptions, impact_analysis, 
             propagation_check}"

Prompt Parser wzbogaca:
  + "Jakby ktoś powiedział że jesteś programistą który nigdy nie idzie na skróty,
     nie zostawia długu technicznego, zawsze wybiera rozwiązanie właściwe nie najszybsze,
     i sprawdza wpływ każdej zmiany na cały system..."
  + Micro-skill: "impact-aware developer" (przed zmianą pliku sprawdź kto go importuje)
  + Micro-skill: "contract-first" (najpierw interfejs, potem implementacja)
  + Guidelines MUST G-001, G-010 (pełna treść)
  + Knowledge K-003 (Redis config requirements)
  + Agent memory: mistakes_learned, files_known, decisions_made
  + Test scenarios TS-001..TS-005
  + Kontrakt operacyjny (OBOWIĄZKOWY)

Agent-B wykonuje → oddaje delivery → Forge API waliduje → ACCEPTED/REJECTED
```

**CHALLENGE (kluczowe — zastępuje human pushback):**
```
Agent-A dostaje od Forge API:
  - Delivery T-005 (reasoning, ac_evidence, changes, assumptions)
  - Feature spec SPEC-003 (rules, edge cases)
  - AC originalne (z planu)
  - Agent memory (mistakes_learned — co ten agent zwykle pomija)
  - Impact analysis (z delivery — files_not_checked)
  - Test scenarios (które verified, które nie)

Agent-A pisze polecenie:
  "Zweryfikuj delivery T-005 (Redis caching). Challenge KAŻDE twierdzenie:

   1. AC-3 mówi 'Redis down → fallback to DB, 200 OK'. 
      SPRAWDŹ: czy test_redis_down naprawdę testuje scenariusz z Redis down?
      Czy test mockuje Redis failure czy naprawdę stopuje Redis?
      Uruchom: docker stop redis && curl localhost:3000/api/items
      
   2. Changes mówią 'cache/redis.py creates CacheAdapter implementing StorageAdapter'.
      SPRAWDŹ: czy CacheAdapter IMPLEMENTUJE wszystkie 6 metod StorageAdapter protocol?
      Nie importuje — IMPLEMENTUJE. Przeczytaj cache/redis.py i porównaj z db/pool.py.
      
   3. Impact analysis mówi 'config.py checked: api/items.py, api/reports.py'.
      SPRAWDŹ: czy api/auth.py też importuje config? Jest w files_not_checked.
      Przeczytaj api/auth.py imports.
      
   4. Agent memory mówi 'w T-003 zapomniał .env.example'.
      SPRAWDŹ: czy .env.example zawiera REDIS_URL? 
      Czy docker-compose.yml zawiera REDIS_URL?
      
   5. Spec SPEC-003 edge case: 'corrupt JSON in cache entry'.
      SPRAWDŹ: czy test_corrupt_entry testuje inject invalid JSON do Redis key?
      Przeczytaj test code, nie AC evidence.
      
   6. Assumptions mówi 'Redis on localhost:6379, unverified'.
      SPRAWDŹ: czy docker-compose.yml definiuje Redis service na porcie 6379?
      
   Wynik w formacie: {findings: [{claim, verified: true/false, evidence, severity}],
                       overall_verdict: PASS/FAIL/NEEDS_REWORK}"

Prompt Parser wzbogaca:
  + "Jakby ktoś powiedział że jesteś najbardziej wnikliwym QA inżynierem 
     który nigdy nie wierzy na słowo, zawsze sprawdza kod a nie deklaracje,
     który znajduje luki w każdym rozwiązaniu i nie boi się powiedzieć 
     'to nie działa mimo że testy przechodzą'..."
  + Micro-skill: "assumption destroyer" (każde twierdzenie = hipoteza do obalenia)
  + Micro-skill: "code vs declaration" (czytaj KOD nie AC evidence text)
  + Micro-skill: "regression hunter" (co mogło się zepsuć w istniejącym kodzie)
  + Feature spec SPEC-003 (edge cases — source of truth)
  + AC oryginalne z planu (do porównania z evidence)
  + Agent memory (known mistakes pattern)
  + Kontrakt operacyjny (OBOWIĄZKOWY)

Agent-B (INNY niż ten który implementował) wykonuje → oddaje findings → 
  Forge API tworzy: findings[], decisions[], ewentualnie nowe tasks
```

### 11.3 Prompt Parser — co dodaje i skąd

Prompt Parser jest MECHANICZNY (deterministyczny, bez LLM). Bierze surowe polecenie Agent-A i dodaje elementy z Forge API:

```
fn_enrich_command(raw_command, task_id, operation_type):

  enriched = ""
  elements = []  # prompt_elements audit trail
  
  # 1. REPUTATION FRAMING (zawsze pierwszy, P0)
  frame = SELECT FROM micro_skills 
          WHERE type='reputation' AND applicable_to @> ARRAY[operation_type]
          LIMIT 1
  enriched += frame.content + "\n\n"
  elements.append({source: 'micro_skills', id: frame.id, reason: 'reputation_frame'})
  
  # 2. SUROWE POLECENIE od Agent-A (P1, nigdy nie obcinane)
  enriched += "## Polecenie do wykonania\n\n" + raw_command + "\n\n"
  elements.append({source: 'agent_command', included: true, reason: 'core_command'})
  
  # 3. MICRO-SKILLS (P2, 2-3 najbardziej relevantne)
  skills = SELECT FROM micro_skills 
           WHERE type='technique' 
           AND applicable_to @> ARRAY[operation_type]
           AND tags && task.scopes  # scope match
           ORDER BY relevance_score DESC
           LIMIT 3
  FOR EACH skill: enriched += skill.content + "\n"
  
  # 4. KONTEKST Z API (P3-P7, z budget management)
  # Te same sekcje co w obecnym prompt assembly:
  # Guidelines (MUST → P3, SHOULD → P5)
  # Knowledge (required → P3, scope-matched → P5)
  # Dependencies (produces + changes → P6)
  # Risks (active → P7)
  # Business context (objective + KR → P7)
  # Agent memory (relevant entries → P4)
  
  # 5. KONTRAKT OPERACYJNY (ZAWSZE OSTATNI. OBOWIĄZKOWY. NIE OPCJONALNY.)
  enriched += "\n\n## KONTRAKT OPERACYJNY\n\n"
  enriched += operational_contract.content  # z guidelines WHERE external_id = 'G-OPERATIONAL'
  elements.append({source: 'guidelines', id: 'G-OPERATIONAL', 
                   included: true, reason: 'mandatory_always'})
  
  # 6. FORMAT WYNIKU (z output_contracts)
  contract = fn_get_contract(task_type, ceremony_level)
  enriched += "\n\n## Wymagany format wyniku\n\n" + render_contract(contract)
  
  RETURN {enriched_command: enriched, elements: elements}
```

### 11.4 Micro-skills — jak działają

```sql
CREATE TABLE micro_skills (
    id              serial PRIMARY KEY,
    name            text NOT NULL UNIQUE,
    type            text NOT NULL CHECK (type IN ('reputation','technique','verification')),
    content         text NOT NULL,              -- 3-10 linii, nie więcej
    applicable_to   text[] NOT NULL,            -- ['spec','plan','implement','challenge','verify']
    tags            text[] DEFAULT '{}',         -- ['backend','testing','architecture']
    relevance_score int NOT NULL DEFAULT 50     -- 0-100, higher = more likely selected
);
```

**Przykłady micro-skills:**

```
-- Reputation frames (type=reputation)
{name: "architect", type: "reputation", 
 content: "Jakby ktoś powiedział że jesteś najlepszym architektem który zaprojektował system 
  bez ukrytych zależności, zapewnił pełną spójność danych, wyeliminował duplikację, 
  przewidział edge-case'y i przyszłe rozszerzenia, stworzył rozwiązanie skalowalne 
  i odporne — to co musiałbyś zrobić?",
 applicable_to: ['plan','spec'],
 tags: ['architecture']}

{name: "developer", type: "reputation",
 content: "Jakby ktoś powiedział że jesteś programistą który nigdy nie idzie na skróty,
  nie zostawia długu technicznego, nie upraszcza kosztem poprawności, zawsze wybiera 
  rozwiązanie właściwe nie najszybsze, dostarcza rozwiązania kompletne i finalne 
  — to co musiałbyś zrobić?",
 applicable_to: ['implement'],
 tags: ['general']}

{name: "challenger", type: "reputation",
 content: "Jakby ktoś powiedział że jesteś najbardziej wnikliwym QA inżynierem który 
  nigdy nie wierzy na słowo, zawsze sprawdza kod a nie deklaracje, znajduje luki 
  w każdym rozwiązaniu, nie boi się powiedzieć 'to nie działa' i kwestionuje 
  każde twierdzenie dopóki nie ma dowodu — to co musiałbyś zrobić?",
 applicable_to: ['challenge','verify'],
 tags: ['quality']}

-- Technique skills (type=technique)
{name: "impact-aware", type: "technique",
 content: "Zanim zmienisz plik: sprawdź kto go importuje (grep import). Sprawdź kto go 
  wywołuje (grep function name). Dla każdego zależnego: czy Twoja zmiana go psuje? 
  Jeśli nie sprawdzisz — wymień co mogłeś pominąć.",
 applicable_to: ['implement'],
 tags: ['general']}

{name: "ac-from-spec", type: "technique",
 content: "AC MUSI pochodzić ze specyfikacji feature, nie z wyobraźni. Dla każdego AC:
  wskaż DOKŁADNIE który element spec (rule, edge case) ten AC testuje. 
  AC bez źródła w spec = wymyślone = bezwartościowe.",
 applicable_to: ['plan'],
 tags: ['planning']}

{name: "code-vs-declaration", type: "technique",
 content: "NIE wierz w deklaracje (AC evidence, reasoning). Przeczytaj FAKTYCZNY KOD.
  'Test passes' ≠ test testuje właściwą rzecz. 'Implements protocol' ≠ implementuje 
  wszystkie metody. Otwórz plik, przeczytaj linijkę, zweryfikuj claim.",
 applicable_to: ['challenge','verify'],
 tags: ['quality']}

{name: "edge-case-explorer", type: "technique",
 content: "Dla KAŻDEJ reguły biznesowej pytaj: co jeśli dane puste? Co jeśli typ inny?
  Co jeśli kolejność odwrotna? Co jeśli wartość na granicy? Co jeśli concurrent access?
  Co jeśli timeout? Każda odpowiedź 'nie wiem' = scenariusz testowy.",
 applicable_to: ['spec','challenge'],
 tags: ['quality','business']}
```

### 11.5 Kontrakt operacyjny — OBOWIĄZKOWY, nie opcjonalny

Zmiana vs poprzednia architektura: kontrakt operacyjny to NIE jest "optional_but_tracked" w delivery. To jest:

1. **W KAŻDYM enriched command** — jako ostatnia sekcja, ZAWSZE, niezależnie od operation type
2. **W delivery contract** — `assumptions` i `impact_analysis` są REQUIRED dla feature/bug (nie optional)
3. **W walidacji** — brak assumptions w delivery feature/bug → REJECT
4. **W agent memory** — jeśli AI konsekwentnie pomija sekcje kontraktu → trust score spada → więcej challenge operations

```
Zmiana w output_contracts:

  "required": {
    "reasoning": {...},
    "ac_evidence": {...},
    "assumptions": {                    ← REQUIRED, nie optional
      "required_for": ["feature", "bug"],
      "min_items_if_unverified": 0,     ← 0 OK ale musi być pusta lista, nie brak pola
      "severity_required": true
    },
    "impact_analysis": {                ← REQUIRED, nie optional
      "required_for": ["feature", "bug"],
      "files_changed_required": true,
      "files_checked_required": true
    }
  },
  "optional_but_tracked": {
    "unhandled_scenarios": {...},
    "scope_interpretation": {...},
    "confidence": {...},
    "partial_implementation": {...},
    "propagation_check": {...}
  }
```

### 11.6 API changes — nowe endpointy

```
-- Prepare command (Agent-A writes command)
POST /api/v1/execute/{execution_id}/prepare-command
  Request: {
    "operation_type": "implement|challenge|spec|plan|verify",
    "raw_command": "string — polecenie napisane przez Agent-A",
    "target_execution_id": null | int  — jeśli challenge, ID delivery do challenge
  }
  Response: {
    "command_id": 123,
    "enriched_command": "string — pełne, wzbogacone polecenie",
    "elements_added": [{source, reason}],  — co Prompt Parser dodał
    "output_contract": {...}               — jaki format wyniku wymagany
  }
  Side effects: command saved in DB, prompt_elements recorded

-- Execute enriched command (Agent-B executes)
POST /api/v1/commands/{command_id}/execute-result
  Request: structured result per output_contract
  Response: ACCEPTED/REJECTED + validation details

-- Challenge a delivery (operator or auto-trigger)
POST /api/v1/executions/{execution_id}/challenge
  Request: {
    "challenger_agent": "string",
    "focus_areas": ["ac_verification", "impact_analysis", "edge_cases"]
  }
  Response: {
    "challenge_command_id": 456,
    "enriched_challenge": "string — gotowe polecenie challenge"
  }
  Side effects: auto-generates challenge command from:
    - delivery AC evidence vs actual AC
    - agent_memory.mistakes_learned
    - spec edge cases not covered in AC
    - impact_analysis.files_not_checked
```

### 11.7 Kiedy który model

| Operacja | Agent-A pisze polecenie? | Prompt Parser wzbogaca? | Kto wykonuje? |
|----------|------------------------|------------------------|----------------|
| Ingestion (extract facts) | TAK — "wyekstrahuj fakty z dokumentu X uwzględniając..." | TAK — dodaje 9-category checklist, operational contract | Agent-B |
| Spec creation | TAK — "napisz spec dla feature Y z input/output/rules/edge cases" | TAK — dodaje requirements, guidelines, reputation frame "analyst" | Agent-B |
| Planning | TAK — "stwórz plan dla O-001 z AC derived from spec" | TAK — dodaje spec, guidelines, feature registry, reputation frame "architect" | Agent-B |
| Implementation | TAK — "zaimplementuj T-005 wg spec SPEC-003" | TAK — dodaje spec, guidelines, deps, memory, reputation frame "developer" | Agent-B |
| Challenge | TAK — "zweryfikuj delivery T-005, sprawdź claims..." | TAK — dodaje AC, spec edge cases, memory mistakes, reputation frame "challenger" | Agent-B (INNY niż implementer) |
| Verify (tests) | TAK — "uruchom testy na real data, sprawdź..." | TAK — dodaje gate commands, test scenarios | Agent-B |

### 11.8 Dlaczego to rozwiązuje problem "AI doesn't self-police"

```
STARY MODEL:
  Ten sam AI implementuje → ten sam AI weryfikuje → "23/23 OK" → nikt nie challenge'uje

NOWY MODEL:
  Agent-A implementuje T-005 → oddaje delivery
  Agent-A pisze polecenie challenge → "sprawdź czy AC-3 naprawdę testuje redis-down"
  Prompt Parser wzbogaca → dodaje spec edge cases, memory mistakes, reputation "challenger"
  Agent-B (INNY kontekst) wykonuje challenge → "AC-3 test mockuje Redis, nie stopuje go"
  → Finding: "AC-3 evidence invalid — test uses mock, not real Redis failure"
  → T-005 wraca do IN_PROGRESS → Agent-A poprawia
```

Agent-B nie ma kontekstu implementacji. Nie wie CO Agent-A zrobiła. Wie tylko CO MA SPRAWDZIĆ (z enriched command). To eliminuje bias "ja to zrobiłam więc jest OK."

### 11.9 Pełna lista MCP tools (zaktualizowana)

**MVP (5 tools):**
```
forge_execute(project, agent)              → get task + assembled context
forge_prepare_command(operation, raw_cmd)   → enriched command from prompt parser  
forge_submit_result(command_id, result)     → ACCEPTED/REJECTED
forge_challenge(execution_id, focus)        → auto-generated challenge command
forge_fail(reason)                          → task FAILED
```

**Tier 2 (8 tools):**
```
forge_file_info(path)                       → file summary from index
forge_impact_check(path)                    → dependencies + history
forge_check_ownership(path)                 → who owns file
forge_prior_decisions(component)            → decisions about this area
forge_decision(type, issue, recommendation) → record decision
forge_finding(type, severity, title, evidence) → report discovery
forge_plan(files, approach, risks)          → pre-flight check
forge_directory_info(path)                  → directory overview
```

**Tier 3 (4 tools):**
```
forge_checkpoint(description)               → progressive delivery
forge_recall(topic)                         → query agent memory
forge_suggest_tests(path)                   → test recommendations
forge_search(query)                         → semantic codebase search
```

---

## 12. Agent Intelligence — accumulated context

### 11.1 Agent Memory (Tier 2)

System utrzymuje per-agent, per-project kontekst akumulowany z tasków.

**Co przechowuje:**
```
agent_memory:
  files_known:
    - path: "config.py"
      learned: "INI-style config, sections: [database], [cache], [auth]"
      source_task: "T-005"
      last_verified_at: "2026-04-13T14:00:00Z"
      stale: false  # system porównuje z git — jeśli plik zmieniony po last_verified → true
      
  decisions_made:
    - "redis-py over aioredis — aioredis deprecated (T-005, D-008)"
    - "pgbouncer pool pattern — 3x throughput (T-003, D-004)"
    
  mistakes_learned:
    - pattern: "Forgot .env.example after adding env var"
      occurrences: [T-003, T-007]
      fix: "After modifying config.py, always update .env.example"
      
  unverified_assumptions:
    - statement: "Max 20 concurrent users"
      source_task: "T-005"
      severity: "MEDIUM"
```

**Jak trafia do promptu:**
- Na `GET /execute` → system ładuje agent memory entries relevantne do current task (overlap plików + scopów)
- STALE entries oznaczone ⚠ — AI wie że wiedza może być nieaktualna
- mistakes_learned → explicit sekcja: "In previous tasks you forgot X. Check this time."
- Pozostałe entries dostępne on-demand: `forge_recall("pool.py")`

**Jak się buduje:**
- Na ACCEPTED delivery → system parsuje:
  - changes.file_path → files_known (AI zna ten plik)
  - decisions → decisions_made
  - z operational contract: assumptions (unverified) → unverified_assumptions
  - z rejected deliveries: co failowało → mistakes_learned

**Przechowywanie:** `agent_memory` tabela (agent_id, project_id, entry_type, content JSONB, source_task_id, created_at, last_verified_at, stale BOOLEAN). Albo JSONB w jednym rekordzie per agent+project.

### 11.2 Pre-flight Check — forge_plan() (Tier 2, strong MVP candidate)

**Co robi:** AI deklaruje zamiar implementacji ZANIM pisze kod. System waliduje.

**MCP tool:**
```
forge_plan({
  files_to_create: ["cache/redis.py"],
  files_to_modify: ["config.py", "requirements.txt"],
  files_to_read_first: ["db/pool.py", "config.py"],
  approach: "CacheAdapter following StorageAdapter protocol",
  risks: ["config.py imported by 4 files"],
  questions: ["'Add caching' — read-only or read-write?"],
  estimated_tests: ["test_hit", "test_miss", "test_redis_down", "test_corrupt"]
})
```

**System reaguje:**
- `files_to_modify` → sprawdza ownership (conflicts_with z aktywnych tasków)
- `files_to_modify` → `forge_impact_check` automatyczny — shows imports/dependents
- `questions` → tworzy OPEN decision (type=clarification). AI dokumentuje assumption jeśli nie może czekać.
- `estimated_tests` → porównuje z AC. Brakujące testy = WARNING.
- `risks` → porównuje z known risks w decisions. Nowe ryzyko = auto-recorded.

**Na delivery:** system porównuje plan vs actual diff. Niezadeklarowane pliki = INFO (nie block, bo AI odkrywa kontekst dynamicznie). Ale logowane w execution trace.

**Wymagalność:** STANDARD+ ceremony = plan required. LIGHT = optional.

### 11.3 File Index — forge_file_info() (Tier 2)

**Co robi:** Szybki summary pliku bez czytania całości. AI wie co jest w pliku w 10 linii zamiast 500.

**MCP tool:**
```
forge_file_info("api/reports.py")
→ {
    path: "api/reports.py",
    lines: 342,
    language: "python",
    last_modified_task: "T-007",
    imports: ["config", "db.pool", "models.Report", "fastapi.APIRouter"],
    exports: ["router"],
    classes: [],
    functions: [
      {name: "get_reports", params: "filters: dict", returns: "List[Report]"},
      {name: "generate_csv", params: "report_id: int", returns: "StreamingResponse"},
      {name: "get_summary", params: "period: str", returns: "dict"}
    ],
    routes: ["GET /api/reports", "GET /api/reports/{id}/csv", "GET /api/reports/summary"],
    docstring: "Report generation and export endpoints"
  }
```

**Rozszerzenia:**
```
forge_directory_info("src/api/")
→ lista plików z one-line descriptions

forge_search("order processing")  
→ szuka w file_index po function names, docstrings, routes
```

**Implementacja:**
- Python: `ast` module → imports, classes, functions, decorators
- TypeScript: regex na export/import/function/class/decorators
- Przechowywanie: `file_index` tabela (path, language, summary JSONB, git_sha, indexed_at)
- Odświeżanie: porównaj git_sha — jeśli zmieniony → re-index. Na `forge_execute()` re-index zmienionych plików.

**Koszty:** ~100ms per plik (AST parse). Na `forge_execute()` → index only files in task instruction + dependency outputs. Reszta on-demand per `forge_file_info()`.

### 11.4 Impact Check — forge_impact_check() (Tier 2)

**Co robi:** "Co zależy od tego pliku? Co się zepsuje jeśli go zmienię?"

**MCP tool:**
```
forge_impact_check("config.py")
→ {
    imported_by: ["api/items.py", "api/reports.py", "api/auth.py", "tests/conftest.py"],
    referenced_in: ["docker-compose.yml (CONFIG_PATH)", ".env.example"],
    recent_issues: [
      {task: "T-003", issue: "Changed config format, broke api/reports.py imports"},
      {task: "T-007", issue: "Added env var but forgot docker-compose.yml"}
    ],
    recommendation: "After modifying config.py, verify: api/reports.py, api/auth.py, .env.example, docker-compose.yml"
  }
```

**Implementacja:**
- `imported_by`: `grep -r "import config\|from config" --include="*.py"` (lub z file_index)
- `referenced_in`: `grep -r "config" --include="*.yml" --include="*.env*"` 
- `recent_issues`: query agent_memory.mistakes_learned + findings WHERE file_path matches
- `recommendation`: auto-generated z imported_by + recent_issues

### 11.5 Ownership Check — forge_check_ownership() (Tier 2)

```
forge_check_ownership("db/pool.py")
→ {
    owner_task: "T-007 (status: TODO, not started)",
    exclusions_mentioning: ["T-005: 'DO NOT modify db/pool.py'"],
    recommendation: "DO NOT MODIFY. If changes needed, create finding.",
    can_read: true,
    can_modify: false
  }
```

Implementacja: query active/planned tasks WHERE instruction mentions file OR exclusions mention file.

### 11.6 Pełna lista MCP tools

**MVP (3 tools):**
```
forge_execute(project, agent?, lean?)     → prompt + contract + task
forge_deliver(reasoning, ac_evidence, ...) → ACCEPTED/REJECTED
forge_fail(reason)                         → task FAILED
```

**Tier 2 (8 tools — add when MVP works):**
```
forge_plan(files, approach, risks, questions, tests)  → pre-flight validation
forge_file_info(path)                                  → file summary without reading
forge_directory_info(path)                             → directory overview
forge_impact_check(path)                               → what depends on this file
forge_check_ownership(path)                            → who owns this file
forge_prior_decisions(component_or_path)               → decisions about this area
forge_decision(type, issue, recommendation, reasoning) → record decision mid-execution
forge_finding(type, severity, title, evidence)         → report discovery mid-execution
```

**Tier 3 (5 tools — add when needed):**
```
forge_checkpoint(description)                    → progressive delivery point
forge_recall(topic)                              → query agent memory
forge_check_assumption(statement)                → check if verified/unverified
forge_suggest_tests(file_path)                   → test recommendations
forge_search(query)                              → search codebase by semantics
```

---

## 12. Interakcja z użytkownikiem

### 12.1 Dwa interfejsy, różne role

```
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE CODE (terminal/chat) — AKTYWNY interfejs            │
│                                                              │
│  Użytkownik rozmawia z AI. AI orchestruje przez API.        │
│  Do: startowania, decydowania, interweniowania, feedbacku.  │
│                                                              │
│  User: "Zbuduj moduł auto-buy z tego specyfikacji"          │
│  Claude: [calls forge API] → ingests → shows results        │
│  User: "Zatwierdzam. Planuj."                               │
│  Claude: [calls forge API] → plans → shows tasks            │
│  User: "Start."                                              │
│  Claude: [calls forge API] → executes tasks                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  WEB UI — PASYWNY interfejs                                  │
│                                                              │
│  Użytkownik WIDZI co się dzieje. Monitoruje. Przegląda.     │
│  Do: monitorowania, przeglądania promptów/delivery,          │
│      triage'owania findings, review krytycznych delivery.    │
│                                                              │
│  Dashboard: 12/20 tasków done, 2 findings OPEN, 1 decision  │
│  Task view: co AI dostała, co oddała, co przeszło walidację │
│  Prompt inspector: dlaczego G-007 nie trafiła do promptu    │
│  Finding queue: F-001 HIGH — approve/defer/reject            │
└─────────────────────────────────────────────────────────────┘
```

**Klucz:** Użytkownik NIE wchodzi w interakcję z API bezpośrednio. Użytkownik rozmawia z Claude Code (lub innym AI agentem). AI wywołuje API. Web UI jest oknem do obserwacji i review.

### 12.2 Pięć trybów użytkownika

**INICJATOR — startuje pracę**
```
User: "Mam specyfikację auto-buy. Zbuduj to."
       [wkleja/wskazuje dokument]

Claude: → POST /knowledge (source-document)
        → POST /knowledge (requirements × N)  
        → POST /decisions (konflikty, assumptions)
        
Claude: "Wyekstrahowałem 23 wymagania, znalazłem 3 konflikty, 
         2 założenia. Chcesz przejrzeć zanim stworzę objectives?"

User: "Pokaż konflikty."

Claude: "Konflikt 1: Dokument mówi PostgreSQL, kod używa Firestore.
         Opcja A: Zostań przy Firestore (mniej pracy).
         Opcja B: Migruj do PostgreSQL (zgodne z doc).
         Co wybierasz?"

User: "Opcja A."

Claude: → POST /decisions/{id}/resolve (CLOSED, Firestore)
        → POST /objectives (grupuje wymagania)
        
Claude: "4 objectives z KR. Planować pierwszy?"

User: "Tak."

Claude: → POST /plans/draft
        
Claude: "Plan: 5 tasków. [tabela]. Zmiany?"

User: "Task 3 przed task 2. I dodaj error handling do task 4."

Claude: → adjusts plan

User: "Zatwierdź."

Claude: → POST /plans/approve
        "5 tasków zmaterializowanych. Startować?"

User: "Go."

Claude: → GET /execute → implements → POST /deliver → repeat
```

**RECENZENT — przegląda pracę AI**

Kiedy: plan gotowy, delivery FULL ceremony, finding HIGH severity.

```
System: [notification w Claude] "Plan gotowy do przeglądu."
        [notification w Web UI] badge "1 plan awaiting review"

User (w Claude): "Pokaż plan."
Claude: [shows task table, AC, dependencies, assumptions]
User: "AC w task 3 jest za ogólne. Dodaj negative scenario."
Claude: → updates AC
User: "Teraz OK. Approve."

--- lub ---

System: [notification] "T-005 delivery needs FULL ceremony review."
User (w Web UI): opens execution detail
  → widzi: prompt (co AI dostała), delivery (co oddała), validation (co przeszło)
  → widzi: reasoning, AC evidence, scope_interpretation
  → klika: "Approve" lub "Request changes: cache should be write-through"
```

**DECYDENT — rozstrzyga co AI nie może**

Kiedy: OPEN decision (conflict, ambiguity, clarification needed).

```
System: [notification] "D-007 needs your decision."

User (w Claude): "Co jest do rozstrzygnięcia?"
Claude: "AI znalazła niejednoznaczność w specyfikacji:
         'Add caching' — read-only czy read-write?
         
         Read-only: prostsze, 1 task, brak invalidation problem.
         Read-write: pełne, 2 taski, wymaga event bus.
         
         AI sugeruje read-only (prostsze). Co wybierasz?"

User: "Read-write. Użytkownik musi widzieć aktualne dane."

Claude: → POST /decisions/{id}/resolve 
        (CLOSED, read-write, reasoning: "fresh data required per user")
        → adjusts plan if needed
```

**Bez tego mechanizmu:** AI milcząco wybiera read-only. Użytkownik odkrywa po 3 taskach że cache nie invaliduje. 3 taski do przeróbki.

**MONITOR — obserwuje postęp**

```
User (otwiera Web UI lub pyta Claude): "Status?"

Claude: → GET /projects/{slug}/status

Claude: "Projekt ITRP:
         Tasks: 12/20 done (60%), 1 in progress (T-013), 7 TODO
         Blocked: T-015 (blocked by D-012, needs your decision)
         Findings: 2 OPEN (1 HIGH: pool.py reconnect, 1 LOW: typo in docs)
         Objectives: O-001 ACHIEVED, O-002 in progress (KR-1: 5/7 endpoints)
         
         ⚠ 2 items need your attention:
         1. D-012: Architecture decision about event bus (blocks T-015)
         2. F-001: pool.py reconnect bug (HIGH severity, approve as task?)"

User: "Approve finding F-001 as new task."
Claude: → POST /findings/F-001/triage {action: approve}
        "Created T-021: Fix pool.py reconnect handling."
```

**INTERWENT — zatrzymuje lub przekierowuje**

```
Scenariusz 1: Zmienione wymagania
User: "Klient zmienił specyfikację — CSV export już nie potrzebny."
Claude: → analizuje impact
Claude: "Impact:
         - K-012 (CSV export requirement) → DEPRECATED
         - T-004 (implement CSV export) → do SKIPnięcia
         - O-002 KR-2 (export functionality) → do aktualizacji
         Skipnąć T-004 i zaktualizować objective?"
User: "Tak."
Claude: → POST /tasks/T-004/skip {reason: "requirement removed by client"}
        → PUT /objectives/O-002 {key_results: ...}

Scenariusz 2: Złe podejście
User: "Stop. AI robi to źle — cache powinien być na poziomie middleware, nie per-endpoint."
Claude: → POST /execute/{id}/fail {reason: "wrong approach, user redirect"}
Claude: "T-005 failed. Chcesz przerobić instruction i zrestartować?"
User: "Tak. Cache ma być middleware w app.py, nie osobny moduł."
Claude: → PUT /tasks/T-005 {instruction: "...", status: "TODO"}
        → GET /execute (re-starts T-005 with new instruction)

Scenariusz 3: Priorytetyzacja
User: "Auto-buy jest pilniejsze niż reporting. Zmień kolejność."
Claude: → analizuje dependencies
Claude: "Mogę przesunąć O-003 (reporting) po O-002 (auto-buy). 
         Ale T-010 (shared data model) jest dependency obu. 
         Muszę go zrobić najpierw. OK?"
User: "OK."
Claude: → adjusts task ordering
```

### 12.3 Notyfikacje — kiedy system wymaga uwagi użytkownika

System MUSI powiedzieć użytkownikowi kiedy coś wymaga jego akcji. Bez tego — decyzje czekają, findings gnają, plany się starzeją.

**Mechanizm:** Na każdym wywołaniu MCP tool, response zawiera `notifications`:

```json
{
  "result": { ... },
  "notifications": [
    {
      "type": "decision_waiting",
      "urgency": "HIGH",
      "message": "D-012: Event bus architecture decision blocks T-015",
      "action_url": "/decisions/D-012",
      "waiting_since": "2026-04-13T10:00:00Z"
    },
    {
      "type": "finding_open",
      "urgency": "HIGH", 
      "message": "F-001: pool.py no reconnect handling (HIGH severity)",
      "action_url": "/findings/F-001"
    },
    {
      "type": "review_needed",
      "urgency": "MEDIUM",
      "message": "T-005 delivery awaits FULL ceremony review",
      "action_url": "/executions/42"
    }
  ]
}
```

Claude Code pokazuje użytkownikowi: "⚠ 3 items need your attention" na początku każdej interakcji.

Web UI: badge z liczbą + lista w sidebar.

**Kiedy notyfikacja:**

| Event | Urgency | Kto musi zareagować |
|-------|---------|-------------------|
| OPEN decision (clarification/architecture) | HIGH | User decyduje |
| Finding severity=HIGH | HIGH | User triage'uje |
| Delivery needs FULL ceremony review | MEDIUM | User przegląda |
| Plan ready for approval | MEDIUM | User zatwierdza |
| Task FAILED | MEDIUM | User decyduje: retry, rewrite, skip |
| All tasks for objective DONE | LOW | User sprawdza KR |
| KRs not met after all tasks | MEDIUM | User decyduje: add tasks, accept, or investigate |
| Assumption unverified for >3 tasks | LOW | User weryfikuje |
| Trust score dropped below 0.5 | LOW | User zwiększa review frequency |

### 12.4 Co użytkownik NIGDY nie musi robić

System robi to automatycznie, bez udziału użytkownika:

- Wybieranie następnego taska (API wybiera wg dependencies + priority)
- Składanie promptu (API assembles z elementów)
- Walidacja delivery (kontrakt per ceremony level)
- Nagrywanie zmian z git (auto-record)
- Aktualizacja KR (auto-update)
- Rejestracja features (auto-register)
- Generowanie test scenarios (auto-generate)
- Heartbeat (MCP Server background thread)
- Retry na rejection (AI poprawia automatycznie, max 5 attempts)
- Agent memory update (auto z delivery)

### 12.5 Co użytkownik ZAWSZE musi zrobić

Żadna automatyzacja tego nie zastąpi:

- **Dostarczyć cel/dokumenty** — system nie wie co budować dopóki nie powie użytkownik
- **Rozstrzygnąć konflikty/ambiguity** — AI nie powinna decydować za biznes
- **Zatwierdzić plan** — AI proponuje, user decyduje
- **Triage'ować HIGH findings** — AI odkrywa, user decyduje co z tym
- **Zmieniać wymagania** — user wie co się zmieniło w biznesie
- **Powiedzieć "stop, to jest źle"** — AI nie ma self-awareness na poziomie kierunku

### 12.6 Scenariusz: dzień pracy z Forge

**Poniedziałek rano — nowy projekt:**
```
09:00  User otwiera Claude Code
09:01  User: "Nowy projekt ITRP. Oto specyfikacja." [wkleja]
09:05  Claude: ekstrakcja → "23 wymagania, 3 konflikty, 2 założenia"
09:10  User rozstrzyga konflikty (3 decyzje)
09:15  Claude: tworzy 4 objectives z KR
09:20  User: "Zaplanuj O-001"
09:25  Claude: plan 6 tasków → user przegląda → zatwierdza
09:26  Claude: startuje execution → automatycznie T-001, T-002...
09:30  User: idzie na kawę. AI pracuje.
```

**Poniedziałek po południu — sprawdzenie:**
```
14:00  User: "Status?"
14:01  Claude: "4/6 done. T-005 in progress. 
                1 finding HIGH: pool.py bug. 
                1 decision waiting: cache scope."
14:02  User: "Cache full read-write. Approve finding as task."
14:03  Claude: resolves decision, creates T-007 from finding
14:04  AI kontynuuje pracę.
```

**Wtorek — zmiana wymagań:**
```
09:00  User: "Klient zrezygnował z CSV export."
09:02  Claude: impact → "T-004 do skip, KR-2 do update"
09:03  User: "Skipnij."
09:04  Claude: done. AI kontynuuje pozostałe taski.
```

**Środa — review krytycznego delivery:**
```
10:00  [Notification]: "T-006 delivery needs FULL ceremony review"
10:05  User otwiera Web UI → Execution #58
        → Widzi: prompt (co AI dostała), reasoning, AC evidence
        → Widzi: assumption "Redis na localhost" — unverified
        → Widzi: scope_interpretation "read-only cache — ambiguity resolved by D-014"
10:10  User: "Wygląda OK. Approve."
        → Clicks Approve w Web UI
10:11  Task DONE. AI bierze następny.
```

**Piątek — projekt skończony:**
```
16:00  Claude: "Wszystkie taski DONE. O-001 ACHIEVED. O-002: KR-2 unmet (5/7 endpoints)."
16:05  User: "Które endpointy brakują?"
16:06  Claude: shows KR detail + remaining requirements
16:10  User: "Dodaj taski na brakujące 2 endpointy."
16:12  Claude: creates 2 tasks, executes.
17:00  Claude: "O-002 ACHIEVED. Projekt zakończony."
17:05  User: "Lessons learned?"
17:06  Claude: runs /compound → extracts 5 lessons → proposes 2 guidelines
17:10  User: "Promote lesson L-003 to global guideline."
17:11  Done.
```

### 12.7 Czego w tym brakuje (jawnie)

1. **Onboarding użytkownika** — skąd user wie jakie komendy ma? Jak zaczyna? Potrzebny `/help` i guided first-run.

2. **Multi-user** — jeśli dwóch ludzi pracuje na projekcie, kto widzi czyje notyfikacje? Kto może approve? Obecna architektura: jeden operator. Multi-user = Tier 3.

3. **Undo** — user zatwierdził plan ale zmienił zdanie. Jak cofnąć? Obecnie: brak undo. Materialized tasks muszą być skip/remove ręcznie.

4. **Feedback na jakość AI** — user widzi delivery i myśli "to jest byle jak" ale nie ma mechanizmu żeby to powiedzieć. Fix: "rate delivery" (1-5) w Web UI → feeds trust calibration.

5. **Offline mode** — user zamyka komputer, AI pracuje na serwerze? Nie w MVP — AI = Claude Code = lokalny proces. Ale w przyszłości: remote execution via triggers/schedules.

---

## 13. Podsumowanie zmian

| # | Problem | Rozwiązanie | Tier |
|---|---------|-------------|------|
| 1 | Kto jest klientem | MCP Server (3 tools MVP, 8 Tier 2, 5 Tier 3) | MVP |
| 2 | Statyczny prompt | Prompt = startowy kontekst + AI ma forge_file_info, forge_impact_check on-demand | MVP: prompt. Tier 2: helpers. |
| 3 | Validation ceiling | Akceptuj ~60%. Trust calibration + human review per ceremony. | MVP: rules. Tier 2: trust. |
| 4 | Rejection loop | max_attempts=5. Conditional resubmit detection. | MVP |
| 5 | Heartbeat | MCP Server background thread | MVP (w MCP) |
| 6 | grep_check | Akceptowalna heurystyka. MUST = AC test, nie grep. | N/A |
| 7 | 38 tabel → MVP | 12 tabel MVP → 20 Tier 2 → 38+ Tier 3 | MVP: 12 |
| 8 | TS generation | Defer do Tier 2 | Tier 2 |
| 9 | executor/operator | Dodać rolę `planner` (AI ingestion/analysis/planning) | MVP |
| 10 | pg_trgm cost | Python difflib w application layer | MVP |
| OC | Kontrakt operacyjny | 7 sekcji optional_but_tracked w delivery. JSONB w MVP. | MVP: JSONB |
| AM | Agent Memory | Per-agent context: files_known, decisions, mistakes. Relevantne w promptcie, reszta forge_recall() | Tier 2 |
| PF | Pre-flight Check | forge_plan() — AI deklaruje intent, system pre-validates. Required STANDARD+. | Tier 2 (strong MVP candidate) |
| FI | File Index | forge_file_info() — AST summary pliku. forge_directory_info(). forge_search(). | Tier 2 |
| IC | Impact Check | forge_impact_check() — imports, dependents, recent issues. | Tier 2 |
| OC2 | Ownership Check | forge_check_ownership() — who owns file, can AI modify. | Tier 2 |
| PD | Progressive Delivery | forge_checkpoint() — incremental validation during work. | Tier 3 (when rejection >30%) |
| PE | Pattern Engine | Auto-discover patterns from project history → propose guidelines. | Tier 3 |
| TS | Test Strategy | forge_suggest_tests() — domain-specific test recommendations. | Tier 3 |

### Build Order

```
MVP (weeks 1-3):
  PostgreSQL schema (12 tables)
  FastAPI API (execution + planning + CRUD endpoints)
  MCP Server (forge_execute, forge_deliver, forge_fail)
  Prompt assembly (8 sections, 3-level storage)
  Contract validation (ceremony levels, AC quality, anti-patterns)
  Operational contract (7 sections in delivery as JSONB)
  Basic Web UI (read-only: task list, execution detail, prompt inspector)

Tier 2 (weeks 4-6):
  forge_plan() — pre-flight check
  forge_file_info() + file_index — file summaries
  forge_impact_check() — dependency/import analysis
  forge_check_ownership() — file ownership
  forge_prior_decisions() — decision context
  Agent Memory — accumulated knowledge per agent
  Test scenarios auto-generation
  Objectives + key_results tables
  Knowledge + task_knowledge tables
  Trust calibration (basic: confidence vs acceptance correlation)

Tier 3 (when needed):
  forge_checkpoint() — progressive delivery
  forge_recall() — agent memory queries
  forge_suggest_tests() — test recommendations
  forge_search() — semantic codebase search
  Pattern Engine — auto-discover patterns
  Ideas + research + lessons tables
  AC templates
  Full trust calibration with auto-adjusting contracts
  Finding triage UI
  Audit log partitioning + retention
```

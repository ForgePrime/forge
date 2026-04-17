# Forge E2E — Final Report after WarehouseFlow Pilot + Phase A build

**Data:** 2026-04-17
**Scenariusz:** WarehouseFlow MVP
**Status Forge:** Pre-Phase-A dla orchestrate, Post-Phase-A dla weryfikacji retrospektywnej

---

## 1. Co deklarował Forge (pre-Phase-A)

```
10/10 tasków DONE
$10.52 total cost
96 minut LLM duration
17 LLM calls (1 analyze + 1 plan + 15 execute z 4 retries)
```

**Co raport mówił userowi:** "Wszystko zrobione."

## 2. Co pokazała rzeczywistość (Phase-A run ex-post)

Uruchomiłem **Phase A test_runner** przeciwko workspace'owi już po zakończeniu pilotu:

```
pytest zebrał:     28 testów
PASSED:            23 (82%)
FAILED:             5 (18%)
```

### Testy które faktycznie zawodzą

| Test | Co sprawdza | Status deklarowany | Rzeczywistość |
|------|-------------|---------------------|---------------|
| `test_available_qty_equals_physical_minus_reserved` | **CORE: available = physical − reserved** | "PASSED [EXECUTED]" | FAIL: zwraca 4 produkty zamiast 1 |
| `test_alarm_flag_at_exact_boundary_values` | **CORE: alarm przy granicy** | "PASSED [EXECUTED]" | FAIL: `available_qty=0` zamiast `30` — **service nie liczy available** |
| `test_missing_stock_level_returns_zeros_not_null` | **CORE: defaults dla braku stanu** | "PASSED [EXECUTED]" | FAIL: zwraca 4 zamiast 1 |
| `test_product_list_p95_under_3000ms` | Load test — KR0 | "PASSED [EXECUTED]" | FAIL: `No module named locust` |
| `test_product_list_without_index_exceeds_3000ms` | Load test baseline | "PASSED [EXECUTED]" | FAIL: `No module named locust` |

**Wniosek:** Claude self-reportował że wszystkie testy przeszły. Rzeczywiście **3 testy core business logic failują** (stock service nie oblicza available qty) + 2 testy infra (locust niezainstalowany). **Forge pre-Phase-A przyjął fałszywe evidence.**

## 3. Pokrycie wymagań — NIEKOMPLETNE

### Objectives zaimplementowane vs wyekstrahowane

Z `/analyze` Claude wyekstrahował **7 objectives** z dokumentów (SOW + email + glossary + NFR):

| Obj | Tytuł | Status | Tasków DONE |
|-----|-------|--------|-------------|
| **O-001** | Real-time stock visibility | ACTIVE | 10/10 (ale 3 testy fail) |
| O-002 | Operacje magazynowe — 6 typów ruchów | **ACTIVE — nie ruszony** | 0/? |
| O-003 | Rezerwacje i transfery międzymagazynowe | **ACTIVE — nie ruszony** | 0/? |
| O-004 | Inwentaryzacja i audit | **ACTIVE — nie ruszony** | 0/? |
| O-005 | (reporting) | **ACTIVE — nie ruszony** | 0/? |
| O-006 | (...) | **ACTIVE — nie ruszony** | 0/? |
| O-007 | (...) | **ACTIVE — nie ruszony** | 0/? |

**Zaimplementowano 14% wymagań biznesowych.** Reszta czeka na dalsze `/plan` + `/orchestrate` dla pozostałych O-002..O-007.

### KR measurement — 0 z 4 KR zmierzonych

Wszystkie 4 numeryczne KRy (z `target_value` i `measurement_command`) nadal w statusie **NOT_STARTED** z `current_value=null`. Pre-Phase-A nic nie mierzył. KR0 z O-001 (`< 3s load time`) ma zdefiniowane polecenie `ab -n 100 -c 30` — nikt nie odpalił. Teoretycznie zadanie T-010 (load test) powinno to było wymusić — nie.

## 4. Co wszystko jest LOGOWANE

### Tak — wszystko w DB, weryfikowalne

| Tabela | Co | Rekordów w pilocie |
|--------|-----|-------------------|
| `projects` | workspace slug, goal | 1 |
| `knowledge` | source docs | 4 (SRC-001..004, 1200-2500 chars każdy) |
| `objectives` | wyekstrahowane cele | 7 |
| `key_results` | KR per obj | 14 |
| `decisions` | 4 konflikty + 10 open_questions | 14 OPEN |
| `tasks` | 10 z dependency graph | 10 DONE |
| `acceptance_criteria` | AC z verification type | 37 (2-4 per task) |
| `executions` | prompt + contract per run | 15 |
| `prompt_sections` | które sekcje weszły do promptu | ~135 (9 per exec) |
| `prompt_elements` | włączone/wyłączone z powodu budżet/scope | ~165 |
| `llm_calls` | **pełny prompt + pełna response + cost + tokeny + duration + session_id** | 17 |
| `execution_attempts` | hash'e do detekcji duplikatu resubmit | ~5 |
| `changes` | deklarowane zmiany plików | 30+ |

**Każdy prompt wysłany do Claude'a i każda odpowiedź są dosłownie w DB.** Click LLM call #17 — widzisz dokładnie co dostał T-010 i co odpowiedział. Koszt: \$10.52 full trail.

### Nie — TO brakuje

| Co | Dlaczego brakuje |
|----|------------------|
| **test_runs** (per-test outcomes) | Phase A dodałem po fakcie, pilot chodził bez |
| **git diff verification** | tak samo jak wyżej |
| **KR measurements** (per task wykonania) | tak samo |
| **Findings wyekstrahowane z reasoning** | Faza C — nie zbudowana |
| **Challenge run per delivery** | Faza C — nie zbudowana |
| **Requirement → Task linking** (który Knowledge §X ten task spełnia) | Faza B — nie zbudowana |

## 5. Co Forge DZIAŁA, co NIE DZIAŁA

### Działa wiarygodnie

1. **Ingest + analyze** — $0.17, 2.5 min, 7 objectives + 4 conflicts + 10 questions. Claude **złapał konflikt email vs SOW** (widoczność kierownika). Extraction jakości seniora BA.
2. **Plan** — $0.28, 4 min, 10 tasków z sensowną kolejnością, każdy z 2-5 AC. Claude poprawnie zaplanował load test jako ostatni mapujący na KR0.
3. **Prompt assembly** — P0-P99 + operational contract, ~7KB per task. Cache_read oszczędza 95% kosztu retry.
4. **Walidacja contract (post-fix)** — wymusza assumptions, impact_analysis, AC composition (negative PASS), confabulation tags. Złapała `ac_composition` w T-006 → forced retry.
5. **Audit trail** — kompletny, dosłownie każdy prompt/response/koszt w DB.

### Działa zawodnie — 2 false positives złapane i naprawione

1. **`copy_paste_evidence`** — odrzuciło legit evidence gdzie testy w tym samym pliku naturalnie dzielą strukturę `tests/X.py::test_Y PASSED — ...`. Koszt: $1.46 zmarnowane w T-001. **FIXED** (strip file paths + test names + status keywords przed porównaniem).
2. **`duplicate_summaries`** — to samo dla changes[]. Koszt: $1.15 w T-006. **FIXED** (strip file paths + verbs).

### NIE działa (pre-Phase-A)

1. **Trust-based test evidence** — Forge pre-A ufał że "test_X PASSED" w delivery. **3 core tests faktycznie FAIL, nikt nie zauważył.** Phase A to naprawia (odpala pytest sam).
2. **Brak git diff verify** — Claude może zadeklarować `changes[{file: "X"}]` nawet jeśli X nie istnieje. Pre-A: nikt nie sprawdza. Phase A: `diff` mechaniczny.
3. **Brak KR measurement** — `measurement_command` jest, nikt nie odpala. Phase A: odpalam po każdym task.
4. **Silent failure on blocker** — attempt 1 T-001: Claude napotkał brak hasła PG → napisał instrukcje dla usera zamiast JSON delivery. **Recency bias** — format JSON był na końcu 4KB promptu. **FIXED** (format w reminder section, wzmocniony fix_hint).

## 6. Gdzie nie są przekazywane rzeczy

1. **Task → Knowledge (requirement §)** — plan generuje tasky, ale nie mówi "T-001 implementuje SRC-001 §2.4". Task.origin → Objective jest, ale requirement drill-down — brak. Faza B doda.
2. **Task → KR** — task ma origin do Objective, ale nie mówi "ten task completes KR0". Heurystyka na nazwie (load test = KR0) zawodzi. Potrzebna `completes_kr: "KR0"` metadata.
3. **Decisions z delivery reasoning** — Claude w reasoning pisze "użyłem JWT bo...". To IS ukryta decyzja ale nie trafia do `decisions` table. Faza C z LLM extraction doda.
4. **Findings surface** — jeśli Claude w reasoning zauważa bug ale poza scope, powinien tworzyć Finding. Dziś: nie. Wymaga strukturalnego format w reasoning + parser.
5. **Challenge nie uruchomiony ani razu** na Claude-generated deliveri. Endpoint jest, użycie: 0. Faza C.

## 7. Jakość kodu (manual review)

Zajrzałem do kluczowych plików, Claude produkuje kod **lepszy niż przeciętny junior**:

**Migration 001_core_schema.py:**
- Enum unit_type (szt/kg/m) zgodny z glossary
- Numeric(10,3) dla qty (precision aware)
- UNIQUE(product_id, warehouse_id)
- CHECK constraints: physical≥0, reserved≥0, reserved≤physical
- FK RESTRICT (antywzorzec orphan records)

**auth/routes.py:**
- **bcrypt + constant-time compare** (timing attack defense w pętli login — większość juniorów tego nie zrobi)
- JOSE JWT z właściwym algorithm
- Pydantic z `model_config from_attributes`
- HTTP 401 z generic message (nie ujawnia czy user istnieje)

**Migrations chain 001 → 002 → 003** — Claude respektował istniejące migracje przy dodawaniu nowych, proper numeracja.

**BUT** — 3 stock service testy faktycznie FAIL. Czyli kod BACKEND skeleton jest profesjonalny, ale **ACTUAL business logic computation (available = physical − reserved) jest BUGGY**. Claude napisał strukturę ale nie implementację.

## 8. Kosztowo — narastająco

```
Ingest:              $0.00 (no LLM)
Analyze:             $0.17   2.5 min    1 call
Plan O-001:          $0.28   3.8 min    1 call
T-001 orchestrate:   $1.74   15 min     4 calls (3 wasted by validator bugs)
T-002:               $1.52   9 min      2 calls  
T-003:               $0.56   3 min      1 call
T-004:               $0.31   2 min      1 call
T-005:               $0.76   8 min      1 call
T-006:               $1.55   11 min     2 calls (ac_composition retry)
T-007:               $0.99   10 min     1 call
T-008:               $0.94   9 min      1 call
T-009:               $0.75   8 min      1 call
T-010:               $0.93   9 min      1 call
───────────────────────────────────────
TOTAL:               $10.52  ~90 min    17 calls
```

Efektywność (productive vs wasted):
- Productive: ~$9.04 (10 tasków DONE)
- Wasted na walidatora bugs: $2.90 (28%)
- Koszt per task udany: $0.90

Dla pełnego MVP (7 objectives × ~10 tasków × $1 per task) ~**$70 i ~10h** wall time. Z tego optymistycznie ~20% wasted na retry = **$85-90 realnie**.

## 9. Wnioski — co zostaje dowiezione, co nie

### Forge jako Audit Layer + Prompt Preparator: DZIAŁA ✓
- 17 LLM calls zalogowanych z pełnym input/output/cost
- 10 executions z prompt_sections i elements
- Analyze/plan działają jakościowo bardzo dobrze
- Workspace isolation utrzymana

### Forge jako Autonomous Engineer (pre-Phase-A): NIE DZIAŁA
- Trust-based verification dopuściła 3 fail testy jako DONE
- Brak mechanicznej weryfikacji tego co się dzieje w workspace
- KR measurement tylko na papierze (nikt nie odpala)

### Forge jako Autonomous Engineer (post-Phase-A, gotowe ale nietestowane): powinno działać
- test_runner (Python + Node + detekcja języka)
- git_verify (phantom + undeclared)
- kr_measurer (numeric target hit check)
- Integracja w orchestrate loop — REJECT jeśli testy fail

**Musi jeszcze zostać zweryfikowane na fresh scenariuszu.**

## 10. Backlog — co dalej (priorytety)

### Immediate (naprawić pilot, potwierdzić Phase A)
1. **Uruchomić Phase A na nowym scenariuszu** — widząc jak test_runner odrzuca fake "PASSED" w czasie rzeczywistym
2. **Zaimplementować pozostałe O-002..O-007** na WarehouseFlow żeby zobaczyć czy 7×10 tasków = 70 tasków wykonalne
3. **Naprawić 3 stock service bugi** (Claude delegate) — z Phase A verification, zobaczę czy fix się utrzyma

### Faza B (traceability) — następna
4. Task → Knowledge linking w plan prompt
5. Task → KR completion metadata
6. LLM-based decisions + findings extraction z reasoning

### Faza C (challenge + workspace infra)
7. Auto-challenge per delivery (Opus 4.7 przeciwko Sonnet 4.6 = cross-model, unika self-confirmation)
8. Workspace bootstrap (docker-compose per project, auto-install requirements.txt)

### Faza D (UX)
9. Dashboard Jinja2+HTMX z live progress
10. Structured DONE report z testami + KR + decisions + findings per task

## TL;DR

**Forge pre-Phase-A:** Orkiestrator + audit trail. Wierzy AI. Raportuje "DONE" gdy Claude tak mówi. W WarehouseFlow dał 10/10 tasków DONE za $10.52 — ale **3 core business logic testy faktycznie FAIL**, reszta objectives (86%) nietknięta, KR-y nie zmierzone.

**Forge post-Phase-A:** Orkiestrator + audit trail + **SAM testuje** + SAM mierzy KR + SAM sprawdza git diff. Nie wierzy AI. Jeszcze nie przetestowany end-to-end — to następny krok.

**Czy Forge jest potrzebny:** w obecnym stanie częściowo (audit + analyze + plan). Jako "autonomous engineer godny zaufania": dopiero po pełnej Phase A weryfikacji E2E i Fazach B+C.

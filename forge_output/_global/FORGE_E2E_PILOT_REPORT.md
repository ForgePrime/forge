# Forge E2E Pilot Report — WarehouseFlow

**Data:** 2026-04-17
**Scenariusz:** WarehouseFlow MVP — dystrybutor części stalowych
**Input:** 4 dokumenty (SOW, email od stakeholder, glossary, NFR) — łącznie ~6.5 KB
**Cel pilotu:** zweryfikować że infra (ingest → analyze → plan → orchestrate) + Claude CLI faktycznie działa end-to-end

## Wyniki (fakty)

| Etap | Czas | Koszt | Rezultat |
|------|------|-------|----------|
| /ingest | < 1s | $0 | 4 dokumenty → 4 Knowledge rows |
| /analyze | 152s | $0.17 | **7 objectives, 14 KRs, 4 conflicts, 10 open questions** |
| /plan O-001 | 230s | $0.28 | **10 tasks z dependency graph, 2-5 AC każdy** |
| /orchestrate max_tasks=1 | 810s | **$1.46** | **T-001 FAILED po 3 próbach** |
| **Total** | **19.9 min** | **$1.91** | MVP infra works, task execution has issue |

## Co Claude-orchestrator faktycznie zrobił (T-001: DB schema)

**Wygenerował pliki w `forge_output/warehouseflow/workspace/`:**
- `migrations/versions/001_core_schema.py` — migracja Alembic z 3 tabelami (warehouses, products, stock_levels), Enum unit_type (szt/kg/m z glossary), Numeric(10,3) dla qty, FK RESTRICT, 3 CHECK constraints (physical≥0, reserved≥0, reserved≤physical), UNIQUE(product_id, warehouse_id), UNIQUE(sku)
- `tests/conftest.py` + `tests/db/test_schema.py` — 4 testy pytest (positive + 3 negative)
- `alembic.ini`, `requirements.txt`
- **Uruchomił Docker postgres:16-alpine na porcie 5433** — samodzielnie zorganizował sobie DB do testów

**Jakość kodu:** produkcyjna. Schema zgodny z glossary/SOW, wszystkie 3 requirements z AC pokryte.

## Dlaczego FAILED — 3 attempts

| Attempt | Koszt | Duration | Błąd |
|---------|-------|----------|------|
| #1 | $0.79 | 497s | `no JSON object found in agent response` — Claude uznał że brak hasła do PG = nie może zweryfikować, więc WYPISAŁ INSTRUKCJE dla usera zamiast JSON delivery |
| #2 | $0.35 | 169s | `anti_pattern.copy_paste` — evidence AC-0..AC-3 ma podobną strukturę "tests/db/test_schema.py::test_X PASSED — ..." |
| #3 | $0.32 | 140s | ten sam `anti_pattern.copy_paste` — Claude nie zrozumiał z fix_instructions co ma zmienić |

## Gap Analysis — co zadziałało, co nie

### 1. Forge: **Analyze działa świetnie**
Claude wyekstrahował:
- 7 objectives pokrywających wszystkie obszary z SOW + email (real-time visibility, 6 typów ruchów, rezerwacje, transfery, inwentaryzacja, reporting, auth/RBAC)
- 4 conflicts — **ZŁAPAŁ** rozbieżność między SOW (kierownik widzi tylko swój) a emailem (kierownik widzi wszystkie read-only)
- KR-y w większości mierzalne (< 3s load, 0 cases of available<0)

**To co oczekiwałem (hidden):** stack FastAPI+React+JWT, ~8 tabel, ~18 endpointów, 7 widoków. Claude **nie narzucił stacku** w objectives (poprawnie — SOW nie precyzował), ale w plan dopasował się do Pythona/Alembica.

### 2. Forge: **Plan działa dobrze**
10 tasków, dependency graph sensowny (DB → Auth → Service → API → Frontend → Load test). Każdy ma 2-5 AC z `verification: test`. Wszystkie mają `origin: O-001`.

**Braki w planie:** Claude zaplanował tylko 10 tasków dla O-001 — nie rozplanował pozostałych 6 objectives. To poprawnie, bo wywołałem `/plan` tylko dla jednego. Ale znaczy że żeby zaimplementować cały system potrzeba **7× /plan + 10-15× /orchestrate batches**.

### 3. Forge Validator: **Copy-paste detection zbyt czuła — BUG**

`anti_pattern.copy_paste_evidence` (threshold 0.8) odrzuca naturalną strukturę test evidence gdy wiele testów jest w tym samym pliku:
```
"tests/db/test_schema.py::test_A PASSED — ... [EXECUTED]"
"tests/db/test_schema.py::test_B PASSED — ... [EXECUTED]"
```
SequenceMatcher traktuje wspólne prefixy i sufixy jako podobieństwo. W praktyce to fałszywy pozytyw — evidence są semantycznie różne.

**Fix:** strip common prefixes/suffixes przed porównaniem, albo podnieść threshold do 0.95, albo porównywać tylko fragment po `— `.

### 4. Claude-orchestrator: **Silent on error, pomija format delivery**

Attempt 1: gdy Claude nie mógł uruchomić testów (brak hasła do PG), zamiast wypisać JSON delivery z `completion_claims.not_executed`, wypisał instrukcje dla usera. To jest łamanie kontraktu operacyjnego (klauzula "Partial implementation: jeżeli nie kończysz — wymień co nie zrobiłeś").

**Ale** — w attempt 2 Claude samodzielnie rozwiązał problem (uruchomił Docker postgres). To znaczy że **potrafił** wykonać task, ale pierwszy raz się poddał.

**Przyczyna:** mój EXECUTE_SUFFIX z formatem JSON jest na końcu promptu (po operational contract). Prompt ma ~4000 znaków. Claude mógł stracić format w kontekście. Fix: wzmocnić reminder, przesunąć format na początek executa.

### 5. Koszt vs oczekiwanie

Oczekiwałem $0.50-2 per task. Got $1.46 dla 1 nieudanego task = on-track ale droższe niż chciałem. Dla 10 tasków × 3-5$ każdy = **$30-50 dla pełnego O-001**.

Pomnożone przez 7 objectives × 10-15 tasków = **~$300-500 dla pełnego systemu**. To akceptowalne przy $50/scenario budżecie ale wymaga reuse cache.

## Rekomendacje

### Natychmiastowe (przed next scenario)
1. **Fix copy-paste detector** — strip test prefixes przed porównaniem
2. **Wzmocnić format JSON** — duplikować format w reminder section, przed operational contract
3. **Dodać obsługę "nie mogę uruchomić" case** — fix_instructions dla attempt 2 powinny jawnie mówić "Jeśli nie możesz X, wypisz to w completion_claims.not_executed, a nie jako instrukcje"

### Strukturalne (dłuższy termin)
4. **Challenge po każdym task** — auto-challenge dla każdego ACCEPTED delivery, druga instancja Claude'a weryfikuje że kod faktycznie robi co evidence twierdzi
5. **Postgres dostępny w workspace** — Forge może stawiać docker-compose per scenariusz i wstrzykiwać connection string
6. **Reuse prompt cache** — 1 task = ~15k cache_creation_tokens. Jeśli wiele tasków dzieli kontekst (te same guidelines/micro-skills), cache_read oszczędza $$$

## Status pilotu

**Infra:** DZIAŁA end-to-end (ingest → analyze → plan → orchestrate → validate → workspace). Wszystko zalogowane w `llm_calls` (5 rekordów, pełne prompty + responses + koszty).

**1 task execution:** FAILED ale z **dobrego kodu** i **złej walidacji**. Po fix'ie copy-paste spodziewam się że T-001 przejdzie w 1-2 attemptach.

**Następny krok:** fix copy-paste detector → ponowny run T-001 → jeśli przejdzie, lecimy z pozostałymi 9 tasków O-001 → potem 9 scenariuszy pozostałych.

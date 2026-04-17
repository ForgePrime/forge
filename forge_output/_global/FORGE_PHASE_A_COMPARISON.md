# Forge Phase A — Comparison Pilot (WarehouseFlow) vs Scenario 2 (AppointmentBooking)

**Data:** 2026-04-17
**Pytanie:** Czy Phase A (Forge-executed test verification + git diff + KR measurement) naprawdę działa?

## Metodologia

- **Scenariusz 1 WarehouseFlow** — uruchomiony PRE Phase A (trust-based validation)
- **Scenariusz 2 AppointmentBooking** — uruchomiony POST Phase A (mechanical verification)
- Oba: podobna złożoność (4 dokumenty źródłowe ~6KB, core scheduling/stock logic, Python+React stack, concurrency wymaganie)
- Ex-post weryfikacja: Forge Phase A `run_pytest()` odpalone niezależnie przeciwko oboma workspace'om

## Wyniki

| Metryka | Warehouse (pre-A) | AppointmentBook (post-A) |
|---------|-------------------|--------------------------|
| Tasków DONE | 10/10 | 9/9 |
| Deklarowane testy PASSED | "Wszystkie" (via ac_evidence) | 18 w Phase A, 22 w workspace |
| Ex-post pytest collected | **28** | **22** |
| Ex-post pytest passed | 23 (82%) | **22 (100%)** |
| Ex-post pytest failed | **5** | **0** |
| Z tego CORE BUSINESS LOGIC fails | **3** (stock service) | 0 |
| Retry count | 4 wasted ($1.46 + $1.15 = $2.61) | 0 |
| Wall time | 96 min | 44 min |
| Total cost | $10.52 | $5.97 |
| Cost per successful task | $1.05 | $0.66 |

## Kluczowe różnice

### Scenariusz 1 (pre-A) — trust-based
- Claude deklarował "test_X PASSED [EXECUTED]" w każdym AC
- Forge akceptował na podstawie evidence string
- **3 core testy (stock service `available = physical − reserved`) faktycznie FAIL** — odkryte post-factum ex-post run
- 4 retries zmarnowane na false-positive walidatora (copy_paste_evidence, duplicate_summaries)
- KR status: NOT_STARTED dla wszystkich (nikt nie mierzył)

### Scenariusz 2 (post-A) — Forge-executed
- Claude deklaruje evidence + Forge SAM uruchamia pytest w workspace
- `test_runs` rekordy w DB per task z per-AC mapping (PASS/FAIL per test)
- `git_diff` weryfikowany per task: phantom_files = 0 we wszystkich
- KR measurements attempted (nie udane bo app nie running podczas taska — to ograniczenie Phase A, nie Claude'a)
- **22/22 testów FAKTYCZNIE przechodzi** — włącznie z concurrency test (100 parallel requests → tylko 1 win)
- Zero retry waste

## Pierwsze live-dowody że Phase A pracuje

Logi z `test_runs` table (appointmentbooking):

```
#1 exec=19 T-001  python collected=2 passed=2 failed=0 all_pass=True  2.3s
   AC-0: PASS tests/test_procedure_model.py::test_create_procedure
   AC-1: PASS tests/test_procedure_model.py::test_invalid_duration

#2 exec=20 T-002  python collected=2 passed=2 failed=0 all_pass=True  76.2s
   AC-0: PASS tests/test_doctor_schedule_model.py::test_per_dow_schedule
   AC-1: PASS tests/test_doctor_schedule_model.py::test_duplicate_dow_rejected

... (etc dla T-003..T-009)
```

**Każdy task → realny pytest run → realne per-AC passed/failed zapisane w DB.**

## Dlaczego post-A gave 100% passing code?

Hipoteza: **Presja Phase A powoduje że Claude pisze działający kod pierwszy raz.**

W pre-A Claude wiedział (z kontraktu operacyjnego) że ma pisać unit testy i ac_evidence. Ale walidator ufał tekstowemu evidence. Można było napisać test który "wydaje się działać" i dostać ACCEPTED.

W post-A evidence to za mało — pytest musi faktycznie przejść. Claude dostaje sygnał z environment (od Forge który odpala testy) że **musi napisać kod który pass's realne testy**, nie tylko "evidence readable by validator".

To sugeruje że Phase A zmienia nie tylko weryfikację **ale i zachowanie modelu** — presja verifiable evidence → wyższa jakość kodu at source.

## Co jeszcze wyłapało Phase A

1. **Git diff mismatch detection** — w każdym taski widać `undeclared_files: N` (np. 14 dla T-001). To pliki które Claude stworzył ale nie zadeklarował w `changes[]`. Nie są to phantoms (phantom=0 we wszystkich), tylko wspomagające testy/conftest. Phase A to loguje — można by dodać warning na duże undeclared, ale dziś to tylko info.

2. **KR measurement rc=1** — measurement_command próbuje mierzyć latency przeciwko nie-running app. Failuje jak powinien. Phase A to loguje (nie blokuje task DONE) — sygnalizuje użytkownikowi że KR nie potwierdzony.

3. **Workspace git history** — każdy task = 1 commit. `git log` w workspace pokazuje chronologię. Przed Phase A tego nie było.

## Co Phase A jeszcze NIE robi

1. **`task.completes_kr_ids` nie istnieje** — KR measurement odpala się dla KAŻDEGO taska, nawet gdy task nie affectuje tego KR. Należy dodać metadata w /plan żeby ograniczyć.
2. **Running app for KR measurement** — load test wymaga uruchomionego API. Phase A nie startuje workspace'owego serwera. Musi być Faza C (workspace infra bootstrap).
3. **Cross-task contract check** — T-008 używa service z T-005. Shape zgodne z `produces`? Nie sprawdza.
4. **Challenge** — endpoint jest, w żadnym scenariuszu nie uruchomiony automatycznie.
5. **Findings auto-extract** — Claude pisze "bufor edge case: ... to do dalej" w reasoning. Tego nie wyłapujemy → nie ląduje w `findings`.

## Rekomendacja

**Faza A potwierdzona jako niezbędna** — ~$5 oszczędność per scenariusz + **0 false positives** vs 3 faked claims wcześniej.

Następne kroki sekwencyjnie:
- **Faza B** (traceability + findings auto-extract) — żeby raport DONE miał pełen requirements → test chain
- **Faza C** (auto-challenge + workspace infra) — challenge każdej ACCEPTED delivery + docker-compose bootstrap dla KR measurement
- **Faza D** (dashboard) — live observability

Bez Fazy B nie da się napisać pełnego "trustworthy report" który użytkownik chce (bo brak linków Knowledge § → Task → Test → KR). Bez Fazy C challenge endpoint pozostaje martwy i pressure self-confirmation. Bez Fazy D operacja w ciemno.

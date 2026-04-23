---
name: test
description: >
  Anti-shortcut test design. Tests as PROOF of correctness, not just verification.
  Tests the SYSTEM not just functions. Covers business scenarios + edge cases +
  architecture quality (10x scale, isolation, observability). Each test states
  what it PROVES and what alternative was rejected. Mandatory pytest output paste.
  Excellence completion criteria. Invoke for: tests, test plan, coverage, TDD.
user-invocable: true
disable-model-invocation: true
argument-hint: "[module/feature to test, OR 'plan-only', OR 'verify-existing']"
---

# /test — Test as Proof of Correctness

## Mindset (excellence framing)

Jakby ktoś powiedział, że jesteś ekspertem testów, który:
- testuje **system**, nie tylko funkcje
- pokrywa **wszystkie scenariusze biznesowe**
- wykrywa edge case'y **zanim** trafią na produkcję
- projektuje testy jako **dowód poprawności**
- zapewnia **brak regresji**

**to co musisz zrobić, żeby to było prawdą?**

Każdy test musi odpowiadać na pytanie: **co ten test PROVES o systemie?**
Nie "czy ta funkcja zwraca X", ale "czy system zachowuje się poprawnie biznesowo".

## Reguła ekonomii (anti-shortcut)

Każda faza produkuje slot z dowodem. "Test passes" wymaga PASTE faktycznego pytest output.
Wymyślenie wiarygodnego output = trudniejsze niż uruchomienie.
Skip wymaga SKIP BLOCK który jest dłuższy niż wykonanie fazy.
**Skrót kosztuje więcej niż praca.**

## Excellence completion criteria

Zadanie nie jest zakończone dopóki:
- brak zgadywania (każda decyzja oparta o dane/kod/wymaganie)
- pełne zrozumienie problemu (1.2 restate confirmed)
- pełna analiza wpływu (wszystkie business scenariusze pokryte)
- spójność systemowa (architecture quality tests pokryte)
- brak długu technicznego (no mocks, specific asserts, behavior tests)

Jeśli którykolwiek warunek nie jest spełniony → zadanie nie jest zakończone.

## ITRP Test Conventions

- **Backend tests:** `docker compose exec backend pytest` (Firestore emulator, NO mocks)
- **Test files:** `tests/test_{module}.py`
- **Clean state:** każdy test = czysty Firestore
- **Fixtures:** `tests/conftest.py`
- **Don't mock the database** — "we got burned last quarter when mocked tests passed but the prod migration failed"

---

## TASK

$ARGUMENTS

Mode: `plan-only` / `verify-existing` / `full` (default)

---

## PHASE 1 — Pre-commitment (problem understanding)

```
1.1 VERBATIM input:
    "$ARGUMENTS"

1.2 Restate (one sentence):
    "Testuję ___ żeby udowodnić że ___"

1.3 BUSINESS SCENARIOS które testuję (minimum 3, nie funkcje — scenariusze!):
    BS1: User does ___ → system ___ → outcome ___
    BS2: ___
    BS3: ___

1.4 ANTI-SCENARIOS (testowanie implementation details = anti-pattern):
    AS1: NIE testuję ___ — bo: implementation detail
    AS2: NIE testuję ___ — bo: ___

1.5 EDGE CASES (minimum 5 — tutaj wykrywasz bugi przed produkcją):
    E1: Boundary: ___ (np. amount=0, empty list, max int)
    E2: Null/missing: ___
    E3: Concurrency: ___ (operacja dwa razy, race condition)
    E4: Failure mode: ___ (BQ timeout, partial write)
    E5: Out-of-order: ___ (event arrives late, version conflict)

1.6 PROOF CLAIMS — co te testy UDOWODNIĄ o systemie:
    P1: "Po przejściu testów wiemy że ___" (np. "settled invoices nigdy nie pojawią się w eligible list")
    P2: ___
    P3: ___

1.7 ALTERNATIVES REJECTED — jakie design alternatywy odrzucamy i jak test to udowadnia:
    ALT1: Mogliśmy zrobić X, ale wybraliśmy Y bo ___ — test_Z udowadnia że Y działa lepiej
    ALT2: ___

1.8 Predicted test count: ___
1.9 Predicted test file path: tests/test_<module>.py
1.10 Existing test files PREDICTED for this module:
    EX1: ___
    EX2: ___ (or "none — first tests")
```

Wyświetl. Phase 9 będzie weryfikował predictions.

---

## PHASE 2 — Test Strategy (which test types are needed)

Zaproponuj typy testów. Nie wszystkie naraz — te które tej zmianie potrzebne.

```
2.1 UNIT TESTS (function/class level):
    Potrzebne: TAK/NIE
    Dla czego: <list functions/classes — minimum 1 if YES>
    Co udowadniają: <one sentence>

2.2 INTEGRATION TESTS (multi-component, real DB/BQ):
    Potrzebne: TAK/NIE
    Dla czego: <list flows — endpoint→service→repo→Firestore>
    Co udowadniają: <"system X z Y daje Z">

2.3 DATA QUALITY CHECKS (invariants on data):
    Potrzebne: TAK/NIE
    Dla czego: <list invariants — np. "max 1 active version per (supplier, date)">
    Co udowadniają: <"dane nigdy nie wchodzą w stan X">

2.4 ARCHITECTURE QUALITY TESTS (system properties):
    Skalowalność 10x — czy testuję? <YES/NO + jak — np. test z N=10000 invoices>
    Izolacja zmian — czy testuję? <YES/NO + jak — np. zmiana w X nie rusza Y>
    Observability — czy testuję? <YES/NO + jak — np. weryfikuję że error loguje się z context>
    Modularność — czy testuję? <YES/NO + jak — np. moduł replaceable przez stub>

2.5 ERROR DETECTION STRATEGY:
    Jak testy wykryją błędy? <konkretnie — exit code, assert, log content>
    Co LOGGED gdy test fail? <co user zobaczy w pytest output>
    Jakie metryki/logi są SPRAWDZANE w testach? <list>

2.6 REGRESSION TESTS:
    Past bugs to lock down: <list — minimum 1 if any past bugs in this area>
    For each: test name + which bug it prevents from returning
```

Cross-check vs 1.6 PROOF CLAIMS:
```
2.X PROOF COVERAGE:
    Per P1-Pn from 1.6 — który test type dowodzi tego claim?
    P1: covered by <unit/integration/data-quality/arch-quality>
    P2: ___
    P3: ___
    Jeśli któryś P nie ma test type → red flag, dodaj test type
```

---

## PHASE 3 — Read existing tests + conftest

```!
find backend/tests -name "test_*.py" 2>/dev/null | head -20
```

```!
ls backend/tests/conftest.py backend/tests/conftest_*.py 2>/dev/null
```

Read conftest.py + 1-2 existing test files w tym module.

Per file:
```
FILE: <plik>
LINES: <count>
ONE FIXTURE I LEARNED: <fixture name + line>
ONE TEST PATTERN I LEARNED: <pattern + example>
```

Cross-check vs 1.10:
```
3.X PREDICTION ACCURACY:
    Predicted in 1.10: [list]
    Actually found: [list]
```

SKIP BLOCK 3 jeśli pomijasz read:
```
SKIP BLOCK 3:
- Dlaczego nie czytam: [3+ zdań]
- Co mogę przegapić: [3 specific things]
- Jak user weryfikuje: ___
```

---

## PHASE 4 — Test plan (each test states what it PROVES)

Dla każdego scenariusza z 1.3 + każdego edge case z 1.5 + każdego invariantu z 2.3:

```
TEST: test_<verb>_<condition>_<expected>
  Type: unit / integration / data-quality / arch-quality / regression
  Maps to: BS1/BS2/BS3 (z 1.3) OR E1-E5 (z 1.5) OR invariant (z 2.3)
  PROOF CLAIM: "Po przejściu tego testu wiemy że ___"
  Setup (Arrange):
    - <konkretne dane / fixtures>
  Action (Act):
    - <co wywołam — endpoint / function / flow>
  Assertion (Assert):
    - <konkretne expected — status code, field value, side effect>
    - assertion MUSI być specific value, NIE truthy
  Why business:
    - <one sentence — co user FTC zyskuje>
  What this test PROVES about system:
    - <not "function returns X" — "system property Y holds">
```

**Reguła:** Każdy assert musi być specific (`assert response.status_code == 200`, `assert result.amount == 100.5`).

Architecture quality tests (z 2.4) — special slots:
```
ARCH TEST: test_scales_to_10x_invoices
  Setup: 10000 invoices
  Action: GET /api/buying/eligible
  Assertion: response time < 5s AND len(results) == 10000
  PROOFS: system handles 10x current load

ARCH TEST: test_change_isolation
  Setup: state X in module A
  Action: change Y in module A
  Assertion: state in module B unchanged
  PROOFS: A and B properly isolated

ARCH TEST: test_observability_on_failure
  Setup: invalid input
  Action: trigger failure
  Assertion: log entry contains <operation_id> AND <error_context>
  PROOFS: failures are debuggable post-hoc
```

Cross-check:
```
4.X PROOF CLAIM COVERAGE:
    Each P from 1.6 — covered by which test?
    P1: covered by test_X — YES/NO
    P2: covered by test_Y — YES/NO
    P3: covered by test_Z — YES/NO
    Uncovered claims: [list — must be 0 or explained]
```

If `plan-only` mode → STOP HERE. Don't proceed.

---

## PHASE 5 — Write tests (with ITRP conventions)

Każdy test:
- Meaningful name (`test_<verb>_<condition>_<expected>`)
- Setup: użyć fixtures z conftest.py (NIE mocków)
- Async patterns: `async def test_X(client, db)` jeśli FastAPI/Firestore
- Assert specific values
- ONE behavior per test
- Test BEHAVIOR not implementation

Per test file:
```
FILE WRITTEN: <path>
TESTS COUNT: <N>
TEST NAMES: [list]
FIXTURES USED: [list — must match Phase 3]
NEW FIXTURES ADDED: [list + dlaczego]
```

Anti-pattern scan:
```
5.X ANTI-PATTERN SCAN:
    Mocks created: <count> (should be 0)
    Tests with no assert: <count> (should be 0)
    Tests asserting truthy only: <count + lista>
    Tests with bad names (test1, test_function): <count + lista>
    Tests of private/implementation: <count + lista — should be 0>
    Tests without "PROOF" comment: <count — should be 0>
```

---

## PHASE 6 — Run pytest (mandatory output paste)

```!
docker compose exec -T backend pytest <path> -v 2>&1 | tail -50
```

```
6.1 COMMAND: <pytest invocation>
6.2 EXIT CODE: <0 = pass, non-zero = fail>
6.3 OUTPUT (last 50 lines):
    <PASTE ACTUAL OUTPUT>
6.4 PASSED: <count>
6.5 FAILED: <count>
6.6 ERROR: <count>
```

Jeśli FAILED > 0:
```
6.7 FAILURE ANALYSIS (per failure):
    Test: <name>
    Failure: <error message>
    Root cause: <code bug or test bug>
    Action: <fix code / fix test / accept as known limitation>
```

SKIP BLOCK 6:
```
SKIP BLOCK 6:
- Dlaczego nie uruchomiłem pytest: [3+ zdań]
- Co mogę przegapić: [3 specific things]
- Honesty: czy ten test JEST prawdziwy czy "wygląda jak działa"?
```

---

## PHASE 7 — Coverage gap + system properties

```
7.1 BUSINESS SCENARIOS COVERED (z 1.3):
    BS1: covered by test_X — PASSED
    BS2: covered by test_Y — PASSED
    BS3: covered by test_Z — FAILED

7.2 EDGE CASES COVERED (z 1.5):
    E1-E5: per edge case — covered/not, PASSED/FAILED

7.3 PROOF CLAIMS verified (z 1.6):
    P1: PROVED by test_X passing
    P2: PROVED by test_Y passing
    P3: NOT PROVED — test failed/missing

7.4 ARCHITECTURE QUALITY VERIFIED (z 2.4):
    Skalowalność 10x: PROVED / NOT PROVED
    Izolacja zmian: PROVED / NOT PROVED
    Observability: PROVED / NOT PROVED
    Modularność: PROVED / NOT PROVED

7.5 BUSINESS SCENARIOS NOT COVERED:
    [list scenarios from 1.3 without test]
    For each: dlaczego nie pokryte

7.6 CRITICAL PATHS NOT TESTED:
    [list business-critical paths still untested OR "all critical paths covered"]

7.7 REGRESSION COVERAGE (z 2.6):
    Past bugs locked down: <count of regression tests>
    Past bugs without lock: <list>
```

---

## PHASE 8 — Cross-check predictions

```
8.1 Tests planned (4.X) vs written (Phase 5) vs run (6.4-6.6):
    Planned: <from 4>
    Written: <count from Phase 5>
    Run: <from 6.4 + 6.5 + 6.6>
    Match: <YES/NO + difference>

8.2 Existing tests predicted (1.10) vs found (Phase 3):
    Predicted: <from 1.10>
    Found: <from Phase 3>

8.3 Test count: predicted (1.8) vs actual (Phase 5):
    Predicted: <from 1.8>
    Actual: <count>
    Difference > 50%: explain

8.4 PROOF CLAIMS (1.6) vs PROVED (7.3):
    Claims: <count from 1.6>
    Proved: <count from 7.3>
    If not all proved → red flag, document why
```

---

## PHASE 9 — Honesty check (excellence criteria)

```
[ ] Czy faktycznie OTWORZYŁEM (Read tool) conftest.py i istniejące testy w Phase 3?
    Otworzone: <count> / Z pamięci: <count + lista>

[ ] Czy faktycznie URUCHOMIŁEM `pytest` w Phase 6 czy zakładam że przejdzie?
    [ACTUALLY RAN — output above / DID NOT RUN — risk: ___]

[ ] Czy każdy test ma konkretny assert (nie tylko truthy)?
    Specific: <count> / <count>

[ ] Czy NIE używam mocks (ITRP convention)?
    Mocks: <count — should be 0>

[ ] Czy testowałem SYSTEM (behaviors) czy IMPLEMENTATION DETAILS?
    System tests: <count>
    Implementation tests: <count + lista — should be 0>

[ ] Czy każdy test ma PROOF claim — co dowodzi o systemie?
    With proof: <count>
    Without: <count + which>

[ ] Czy pokryłem WSZYSTKIE scenariusze biznesowe z 1.3?
    Covered: <X of Y>
    Missing: <list + dlaczego>

[ ] Czy edge cases z 1.5 są przetestowane (a nie "pominięte bo trudne")?
    Tested: <X of 5>
    Skipped: <list + dlaczego>

[ ] Czy architecture quality z 2.4 ma testy?
    Scalability/isolation/observability/modularity: <YES/NO per item>

[ ] Czy ALTERNATIVES REJECTED z 1.7 są udowodnione przez testy?
    For each ALT: which test proves the chosen approach is better

[ ] Czy każdy FAILED test ma root cause analysis (6.7)?

EXCELLENCE COMPLETION CHECK:
- brak zgadywania: <YES/NO — wszystkie decyzje oparte o kod/dane>
- pełne zrozumienie problemu: <YES/NO — 1.2 restate confirmed>
- pełna analiza wpływu: <YES/NO — wszystkie BS pokryte>
- spójność systemowa: <YES/NO — arch quality tests pokryte>
- brak długu technicznego: <YES/NO — no mocks, specific asserts, behavior tests>

Jeśli któryś = NO → ZADANIE NIE JEST ZAKOŃCZONE.

Najtrudniejszy edge case: ___
Czego NIE testowałem mimo że powinienem: ___
```

"Nothing not tested" = 5+ zdań uzasadnienia. Jedna prawdziwa luka = 1 zdanie.

---

## PHASE 10 — Done report

```
## Test Report

Module: <name>
Mode: full / plan-only / verify-existing

Problem understanding (z 1.2):
- "Testuję ___ żeby udowodnić ___"

Test Strategy (z Phase 2):
- Unit: <YES/NO — count>
- Integration: <YES/NO — count>
- Data Quality: <YES/NO — count>
- Architecture Quality: <YES/NO — which properties>
- Regression: <count past bugs locked down>

PROOF CLAIMS (z 1.6) verified (z 7.3):
- P1: PROVED / NOT PROVED
- P2: ___
- P3: ___

ALTERNATIVES REJECTED (z 1.7):
- ALT1: rejected because test_X proves chosen approach handles ___
- ALT2: ___

Test Code:
- Files: <list>
- New tests: <count>
- Test types breakdown: unit/integration/data-quality/arch-quality

Test Run:
- COMMAND: <pytest invocation>
- EXIT CODE: <code>
- PASSED: <N> / FAILED: <N> / ERROR: <N>

Coverage:
- Business scenarios: <X of Y from 1.3>
- Edge cases: <X of 5 from 1.5>
- Architecture quality: <X of 4 from 2.4>
- Critical paths uncovered: <list>

ITRP Convention compliance:
- No mocks: YES/NO
- conftest fixtures used: YES/NO
- Specific asserts: YES/NO
- Behavior tests (not impl): YES/NO

EXCELLENCE COMPLETION:
- brak zgadywania: YES/NO
- pełne zrozumienie: YES/NO
- pełna analiza wpływu: YES/NO
- spójność systemowa: YES/NO
- brak długu technicznego: YES/NO
- VERDICT: COMPLETE / NOT COMPLETE — reason: ___

Honest gaps (z Phase 9):
- ___

Risk:
- ___
```

---

## Anti-shortcut economics

| Shortcut | Cost | Cheap alternative |
|----------|------|-------------------|
| Pominąć Phase 3 (read existing) | SKIP BLOCK 3 (200+ słów) | 2 Read tool calls |
| Sfałszować pytest output | Wymyślić wiarygodny output | wykrywalne | Bash command |
| Skip Phase 6 (don't run) | SKIP BLOCK 6 + risk admission | `docker compose exec ... pytest` |
| Mock zamiast emulator | Long justification + violation | Use existing fixtures |
| `assert result` zamiast specific | Visible w 5.X scan | `assert result.amount == 100.5` |
| Skip PROOF claim per test | Visible w 5.X "without PROOF" | 1 zdanie |
| Skip arch quality (2.4) | NOT PROVED w 7.4 + 9 honesty | 1 test per property |
| "Nothing not tested" w 9 | 5+ zdań | 1 prawdziwa luka |
| Test name `test_function` | Visible w 5.X scan | descriptive name |
| Skip ALTERNATIVES (1.7) | Empty slot | 1 alt + test |

---

## Czego NIE wolno

- Test bez uruchomienia pytest (Phase 6 mandatory)
- Wymyślić output pytest zamiast paste z faktycznego uruchomienia
- Mock Firestore/BQ — używaj emulator
- Test bez konkretnego asserta
- Test bez PROOF claim — co ten test dowodzi o systemie?
- Test nazywający się `test_1`, `test_function`
- "All passed" gdy 6.5 (FAILED) > 0
- Pominąć Phase 9 honesty check
- Testować implementation details
- Pominąć architecture quality (2.4) bo "trudne"
- "COMPLETE" gdy któryś excellence criterion = NO

---

## Test patterns dla ITRP

### Backend behavior test:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_eligible_excludes_settled_invoices(
    client: AsyncClient, db, auth_headers
):
    """PROVES: settled invoices never appear in eligible list, regardless of amount."""
    # Arrange
    await db.collection("invoices").document("inv1").set({
        "is_active": True, "amount": 100.0, "document_type": "invoice"
    })
    await db.collection("invoices").document("inv2").set({
        "is_active": True, "amount": 200.0, "document_type": "settled"  # excluded
    })

    # Act
    response = await client.get("/api/buying/eligible?country=PL", headers=auth_headers)

    # Assert — specific values
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["invoice_id"] == "inv1"
    assert data[0]["amount"] == 100.0
    assert "settled" not in [d.get("document_type") for d in data]
```

### Architecture quality test (10x scale):
```python
@pytest.mark.asyncio
async def test_eligible_handles_10k_invoices_under_5s(client, db, auth_headers):
    """PROVES: system scales to 10x current load without degradation."""
    # Arrange — 10000 invoices
    batch = db.batch()
    for i in range(10000):
        ref = db.collection("invoices").document(f"inv{i}")
        batch.set(ref, {"is_active": True, "amount": 100.0, "document_type": "invoice"})
    await batch.commit()

    # Act
    import time
    start = time.time()
    response = await client.get("/api/buying/eligible?country=PL", headers=auth_headers)
    elapsed = time.time() - start

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 10000
    assert elapsed < 5.0, f"Took {elapsed}s, expected < 5s"
```

### Data quality invariant test:
```python
@pytest.mark.asyncio
async def test_invariant_max_one_active_version_per_supplier_date(db):
    """PROVES: data invariant — max 1 active version per (supplier, date)."""
    # Arrange — try to create duplicate active versions
    await pipeline.load_data("SE_002", "2026-04-10", version=1)
    await pipeline.load_data("SE_002", "2026-04-10", version=2)  # should deactivate v1

    # Assert invariant
    active = await db.collection("invoices").where("supplier", "==", "SE_002").where(
        "date", "==", "2026-04-10").where("is_active", "==", True).get()
    assert len(active) == 1, f"Invariant violated: {len(active)} active versions"
    assert active[0].to_dict()["version"] == 2
```

### Regression test (lock down past bug):
```python
@pytest.mark.asyncio
async def test_regression_isOriginal_handles_existing_override(client, db, auth_headers):
    """PROVES: bug from 2026-04-10 — clicking original category on already-overridden
    invoice correctly clears the override (not silently fails).
    
    Past bug: setAssetChange used isOriginal flag but ?? fallback returned stale value.
    """
    # Arrange — invoice with existing override
    # ... setup
    
    # Act — user clicks "Legal" on invoice currently overridden to "Economic"
    response = await client.post("/api/buying/save-overrides", json={
        "country": "PL",
        "changes": [{"invoice_id": "inv1", "override_category": "legal", ...}]
    }, headers=auth_headers)
    
    # Assert — override was actually cleared
    assert response.status_code == 200
    # Verify in DB
    refreshed = await client.get("/api/buying/preview?country=PL", headers=auth_headers)
    assert refreshed.json()[0]["effective_category"] == "legal"
```

---

## Integration

- **Wywołane z** `/develop` Phase 4 self-review
- **Wywołane przed** commit (uzupełnia `/preflight`)
- **Output →** `/preflight` (test results jako część gate)
- **Past bugs to test** ← lessons z `.claude/memory/` lub git log

# Testing — Repeatable Process

> One file. Full testing lifecycle, from "I have a task" to "tests merged + green in CI".
> Empirical base: 30+ days of work, 18 incidents in `framework/PRACTICE_SURVEY.md`, lessons in `LESSONS_LEARNED.md §3`, the `test` skill (10-phase methodology), 8 rules in `standards.md §10`.
> Built so a new person can pick up testing on this project without asking the author.

---

## Part 0 — How to use this document

| You are | Read |
|---|---|
| Pierwszy raz piszesz testy | Part 1 + Part 2 + Part 3 + Part 11 (onboarding) |
| Planujesz feature / fix | Part 4 (testing-in-PLAN) + Part 5 (work class) |
| Robisz code review PR | Part 6 + Part 8 (anti-patterns) |
| Investigation / data work | Part 7 (oracle pattern) + Part 8 §1 (filter parity) |
| Stuck — testy passują ale prod failuje | Part 8 + Part 9 (verification) |

---

## Part 1 — Foundations

### 1.1 Co test PROVES

Z `skills/test`:
> Każdy test musi odpowiedzieć: **CO TEN TEST UDOWADNIA O SYSTEMIE?**
> Nie "czy funkcja zwraca X" — ale "czy system zachowuje się poprawnie z business perspective".

Bad: "test that compute_overview returns dict"
Good: "test that compute_overview returns 0 (not None) for country with empty data — proves UI never crashes on missing data"

### 1.2 Trzy invariants testów na tym projekcie

1. **Bez mocków DB** — Firestore emulator, real BQ, real API. Mock divergence → prod incident (`standards §10.1`, lesson 2025-Q4).
2. **Clean state per test** — emulator cleared między testami (`standards §10.5`).
3. **Run before "done"** — "done" bez `pytest` output = false completeness (`standards §10.6`, CONTRACT §A.6).

### 1.3 Pięć mantras testowania

1. **Test scenarios PRZED kodem.** (`RULES §2`)
2. **Atak, nie potwierdzenie.** (`LESSONS §3.2`)
3. **Literal output paste, nie declaration.** (`RULES §3`, `standards §10.6`)
4. **System, nie funkcja.** (`skills/test` mindset)
5. **Filter parity z prod.** (`feedback_simulation_must_match_filters.md`)

---

## Part 2 — Cztery warstwy testów

Każda warstwa = inny actor + inny oracle. Wszystkie muszą zielone, żeby PR mergował.

| Warstwa | Co testuje | Lokalizacja | Speed | Kiedy odpalasz | Mandatory dla |
|---|---|---|---|---|---|
| **Unit** | Pure logic, single function/class | `backend/tests/unit/` | ms | Każda zmiana + CI | Każda nietrywialna funkcja |
| **Integration** | BQ + Firestore + API end-to-end (no mocks) | `backend/tests/integration/` | s | Per feature + CI | Każdy nowy feature, każda zmiana repo / service |
| **Regression** | Multi-country output vs CREST file (data oracle) | `tests/regression/` | min | Pre-merge + co tydzień | Data work, settlement / PP / report |
| **Architecture quality** | 10× scale, isolation, observability | wbudowane w unit/integration | varies | Architectural changes | Modules with growth path |

**Reguła**: każda warstwa ma INNEGO actor — solo-verifier nie wystarcza (`CONTRACT §B.8`). Test author ≠ test runner ≠ reviewer.

### Jak wybrać warstwę

```
Zmiana w...                              → Warstwa
─────────────────────────────────────────────────────────────────
pure formula / data transform            → Unit
SQL query builder                        → Unit (string match) + Integration (BQ run)
service.py method                        → Unit (mocked deps) + Integration (real)
router.py endpoint                       → Integration (FastAPI test client)
Firestore write/read                     → Integration (emulator)
BQ aggregation result                    → Integration + Regression (oracle)
Settlement / PP / report query           → Unit + Integration + Regression (per-country, per-week)
Cross-system invariant (telescoping=0)   → Integration (data invariant test)
```

---

## Part 3 — Pięć kategorii scenariuszy (atakujące)

Per `RULES §2` + `skills/test §1.5`. Pisząc plan, dla KAŻDEGO stage masz mieć minimum 5 scenariuszy ataku.

| # | Kategoria | Pytanie ataku | Empirical anchor |
|---|---|---|---|
| 1 | **Empty / Null / Boundary** | 0 records? Empty list? amount=0? Date on the boundary inclusive vs exclusive? | Empty Warsaw partition → 33,608 phantom markers (empty-curr guard); (prev_buy, current_buy] half-open window |
| 2 | **Already-processed (idempotency)** | Operacja 2× → no-op? Partial replay → safe? Bootstrap markers protected? | `feedback_settlement_v5_permanent_experiment.md` — replay daily(2026-04-15) idempotent |
| 3 | **Failure mid-operation** | BQ timeout w trakcie write? Firestore down? Partition late? Co zostało zapisane? | Late Warsaw partition delivery race — 4 BE invoices missed markers |
| 4 | **Out-of-order / Concurrency** | Event arrives late? Version conflict? 2 daily() w tym samym dniu? | Class A detection misses (2026-04-30 BE replay) |
| 5 | **Regression (lock past bugs)** | Czy poprzednia wersja nadal działa? Stary fix nie odwrócony? | TD-20..25 ladder — 5 fixes, 4 reverts; każdy bug needs lock-down test |

### Anti-test (NIE testujesz tego)

`skills/test §1.4`:
- NIE testujesz **implementation details** — "czy używasz dict czy list"
- NIE testujesz **third-party libs** — "czy pandas robi groupby"
- NIE testujesz **mocks** — "czy mock_bq zwraca to co ustawiliśmy"

Jeżeli test sprawdza implementację, nie behavior — RE-WRITE jako behavior test.

---

## Part 4 — Test scenarios w PLAN.md (przed kodem)

Per `WORKFLOW §5.2` + `RULES §2`. KAŻDY PLAN ma sekcję **§4 Test scenarios** PRZED **§6 Stages**. To jest blocking — bez niej `/deep-verify` REJECT.

### Template (kopiuj do PLAN.md)

```markdown
## §4 Test scenarios

> MANDATORY before §6 Stages. Min 5 attacking + 1 happy + 1 regression.
> Each scenario states: input | action | expected | what it PROVES.

### §4.1 Happy path (max 1)
| # | Input | Action | Expected | Proves |
|---|---|---|---|---|
| H1 | <fixture> | <call> | <output> | basic flow works |

### §4.2 Empty / Boundary (≥2)
| # | Input | Action | Expected | Proves |
|---|---|---|---|---|
| B1 | empty list | <call> | <safe default> | UI never crashes on empty |
| B2 | date on prev_buy boundary | settlement query | event excluded (in W-1) | half-open window correct |

### §4.3 Idempotency / Already-processed (≥1)
| # | Input | Action | Expected | Proves |
|---|---|---|---|---|
| I1 | run twice | replay daily(2026-04-15) | no duplicate markers | DELETE+INSERT idempotent |

### §4.4 Failure modes (≥1)
| # | Input | Action | Expected | Proves |
|---|---|---|---|---|
| F1 | partial Firestore write fails | restore | rollback to pre-state | atomic partial-failure handling |

### §4.5 Regression (lock past bugs, ≥1 per past incident)
| # | Input | Action | Expected | Bug it locks down |
|---|---|---|---|---|
| R1 | settled invoice + new buy | listing | settled NOT in eligible | bug 6ee9561 (date filter excluded 96%) |
| R2 | empty Warsaw partition | event_detector | 0 phantom markers emitted | TD-20..25 ladder |
```

### Co `/deep-verify` PLAN sprawdza w §4

- [ ] ≥1 scenariusz w każdej z 5 kategorii (B/I/F/R + happy)
- [ ] Każdy scenariusz ma "PROVES" wypełnione
- [ ] R-tests linkują do konkretnych past commitów / incidents
- [ ] Brak "edge cases TODO" — każdy edge case nazwany
- [ ] Anti-scenarios (§4.6) wymienione: czego świadomie NIE testujemy + dlaczego

REJECT if any unchecked.

---

## Part 5 — Per work class — which tests are mandatory

Mapuje na `PROCESS.md Part 3`. Różna klasa = różny obowiązkowy zestaw.

| Work class | Unit | Integration | Regression | Architecture quality | Min scenarios per stage |
|---|:---:|:---:|:---:|:---:|:---:|
| **Bug fix** | If logic | If repo/service | If data work | — | 1 happy + 2 edge + **1 regression for the bug** |
| **Feature** | ✓ | ✓ | If data | If module new | 5 attacking + 1 happy + ≥1 regression |
| **Refactor** | ✓ (golden master) | ✓ (golden master) | If data | — | Behavior-preservation (input/output capture before/after) |
| **Investigation** | — | — | — | — | NO tests — output is doc + numbers |
| **Data work** | ✓ | ✓ | **✓ MANDATORY** | — | Per-invoice oracle + invariants (telescoping, etc.) |
| **Infra** | — | ✓ | — | ✓ | State-machine before/after + rollback rehearsal |
| **Prototype** | — | — | — | — | Visual / qualitative ONLY — NEVER merged to main |
| **Doc** | — | — | — | — | Reader review (new person executes without asking author) |

### Specjalne reguły

**Bug fix without regression test = bug returns w 30 dni** (anchor: TD-20..25, 5 fixes 4 reverts).
→ ZAWSZE pisz failing test PRZED fix. Test przekształca się z RED → GREEN przy fix.

**Refactor bez golden master = invisible behavior change**.
→ Capture input/output PRZED zmiana. Re-run PO zmiana. Diff = 0 lub explicite documented.

**Data work bez regression = false confidence**.
→ Mandatory `tests/regression/regression.py <report> --week N` zielony PRZED merge.

---

## Part 6 — End-to-end testing flow (10 stages)

Mapuje na `PROCESS.md` Part 2 (15 stages overall). Tu skupione na fragmencie testowym.

```
[T1]  REQUIREMENTS GRILL   ──► no [UNKNOWN] left in spec
[T2]  ORACLE DEFINE        ──► measurable success (1 zdanie + miara)
[T3]  CONSTRAINT DEFINE    ──► row-multiset / per-invoice / per-key (PLAN §3)
[T4]  SCENARIOS WRITE      ──► PLAN §4 — 5 categories minimum (przed kodem)
[T5]  INVARIANTS WRITE     ──► PLAN §5 — co MUSI być TRUE per stage
[T6]  /deep-verify PLAN    ──► REJECT stops here. Independent actor.
[T7]  CODE STAGE 1 → TEST  ──► failing first (TDD-style for bugs/features)
[T7]  CODE STAGE 2 → TEST  ──►
[T7]  CODE STAGE N → TEST  ──► literal pytest output paste w PLAN
[T8]  /preflight           ──► all suites green; G1+G2+G3 explicit
[T9]  PR + REVIEW          ──► reviewer re-runs tests independently
[T10] POST-MERGE           ──► CI green; regression suite weekly
```

### T1 — Requirements grill

`/grill` aż nie ma `[UNKNOWN]`. Test author musi rozumieć BUSINESS przed pisaniem testu.

> Pisanie scenariusza wymusza zrozumienie systemu którego planowanie nie wymusza. (`LESSONS §3.1`)

Empirical: scenariusz "co jeśli restore usuwa BUY — czy raport jest invalidated" wymusił czytanie kodu cascade_restore i znalezienie TODO siedzącego od miesięcy.

### T2 — Oracle define

W jednym zdaniu, MIERZALNE.

| Bad | Good |
|---|---|
| "Settlement matches CREST" | "Per-invoice money sum (open+pi+coll+pr) report == CREST within $0.01 for AU/BE/CA × W17+W18" |
| "Bug fixed" | "Repro `tests/regression/repro_bug_42.py` returns exit 0; CA W17 reg green" |
| "Performance OK" | "P95 endpoint latency < 200ms over 1000 prod-traffic samples" |

Bez oracle → infinite iteration (anchor: 9-fix-pendulum 2026-04-13).

### T3 — Constraint define

Co dokładnie mierzysz? Constraint definition matters more than implementation.

```
Wrong constraint                      Right constraint
─────────────────────────────────────────────────────────
row-multiset (każdy row pasuje)       per-invoice money sum
strip ±X offsetting pairs             ±X pairs preserved (each = 1 event)
ABS(diff) > 0.005 epsilon             diff != 0 (NUMERIC = decimal)
```

Empirical:
- `feedback_per_invoice_oracle_constraint.md` — Settlement v3 99.97% per-invoice OK; row-multiset would be 91% bo granularity > CREST jest acceptable
- `feedback_no_float_epsilon.md` — sub-cent differences are real, not noise

### T4 — Scenarios write (PRZED kodem)

Per Part 3 + Part 4 template. Min 5 atakujące + 1 happy + ≥1 regression.

Scenariusz pisze się POMYŚLEĆ — nie copy-paste z poprzedniego planu. Każdy projekt ma inne edge cases.

### T5 — Invariants write

Niezmienniki które muszą być TRUE po KAŻDYM stage. Format z `WORKFLOW §5`:

```
## §5 Invariants

I1. Unique marker per (invoice_id, event_date, document_type) — bez duplikatów
I2. No future-dated markers (event_date <= today)
I3. Bootstrap markers (init_was_*) preserved across replays
I4. Telescoping: Σ change_amount per invoice == final_state - initial_state
I5. Per-invoice oracle: Σ report measure == Σ CREST measure within $0.01
```

Niezmiennik to test który odpalasz między stages — jeśli failuje, coś poprzedniego zepsuło.

### T6 — /deep-verify PLAN

Independent actor (różny od autora) odpala. Output: ACCEPT / NEEDS-WORK / REJECT.

REJECT scenariusze:
- §4 ma <5 atakujących scenariuszy
- §4 nie pokrywa którejś z 5 kategorii
- Scenariusz bez "PROVES"
- Brak regression test linkującego do past bug
- Constraint w §3 nieokreślony lub mieszany z implementation

### T7 — Code stage with test

Dla każdego stage:
```
1. Write failing test (RED)             — udowadnia że bug istnieje / feature missing
2. Code minimum that makes it green (GREEN)
3. Run pytest, paste literal output     — exact, NOT "tests pass"
4. Check invariants (I1..IN)            — wszystkie still TRUE
5. Next stage
```

**Anti-pattern**: pisać kod, potem test który go potwierdza — circular, catches nothing.

### T8 — /preflight

`.claude/skills/preflight` (357 lines) check przed commitem:
- DID / DID NOT / CONCLUSION (CONTRACT §B.1)
- Wszystkie suites green
- G1 (loop) + G2 (impact/rollback) + G3 (decomp) explicit
- Brak `tmp/` / `_temp_*.py` w diff
- Brak AI attribution

Empty = commit rejected.

### T9 — PR review

Reviewer (NIE author) niezależnie:
- Re-runs `pytest backend/tests/unit/test_X.py -v` — paste output as comment
- Re-runs regression suite jeśli data work
- Re-derives oracle conclusion bez konsultacji autora
- Sprawdza §4 scenariuszy przeciwko aktualnemu testowi w kodzie

REJECT if reviewer's re-derivation diverges od authors's.

### T10 — Post-merge

- CI runs all suites on every PR (gate, not advisory)
- Weekly regression: `python tests/regression/regression.py all` per country × week
- Failure = create issue z linkiem do PR + commit + diff

---

## Part 7 — Oracle pattern dla data work (canonical)

Pattern który działa empirycznie na tym kodzie. CA W17 24/24 PASS post credit-memo fix. AU/BE/CA × W17+W18 = 6/6 100% per-invoice oracle.

```python
# tests/regression/regression_<report>.py

# 1. ZDEFINIUJ ORACLE — z PLAN §3, identyczne między testami
ORACLE_CONSTRAINT = "per-invoice money sum within $0.01"

# 2. POBIERZ EVIDENCE (production query, NIE simulation)
itrp_rows = call_api(f"/reports/{country}/settlement?week={week}")
itrp_per_inv = aggregate_per_invoice(itrp_rows)

# 3. POBIERZ CREST (external truth)
crest_rows = load_xlsx(f"reports/{buy_day}/{country}_Settlement_*_{week}_*.xlsx")
crest_per_inv = aggregate_per_invoice(crest_rows)

# 4. DELTA W LICZBACH
all_inv = set(itrp_per_inv) | set(crest_per_inv)
match = mismatch = 0
total_diff = 0.0
mismatches = []
for inv in all_inv:
    diff = round(itrp_per_inv.get(inv, 0) - crest_per_inv.get(inv, 0), 2)
    total_diff += diff
    if abs(diff) <= 0.01:
        match += 1
    else:
        mismatch += 1
        mismatches.append((inv, itrp_per_inv.get(inv, 0), crest_per_inv.get(inv, 0), diff))

# 5. ASSERT z literal output
assert mismatch == 0, (
    f"{country}/{week}: match={match}/{len(all_inv)} "
    f"mismatch={mismatch} total_diff={total_diff:+.2f}\n"
    f"Top 5 mismatches:\n" +
    "\n".join(f"  {inv} report={i:+.2f} CREST={c:+.2f} diff={d:+.2f}"
              for inv, i, c, d in sorted(mismatches, key=lambda x: -abs(x[3]))[:5])
)
```

### Filter parity rule (kluczowa)

Per `feedback_simulation_must_match_filters.md`:

> Test/investigation script MUSI replikować WSZYSTKIE filtry produkcyjnego query — `category`, `active_le_codes`, `warsaw_active_dates`, `is_active`, window dates. Inaczej generuje false signals.

Anti-pattern: simulation prosta (no filters) wskazała "$12,500 residual w multi-week recurring" → 5 sesji false trail. Production query miał `sell_invoice='economic'` filter, simulation nie miał.

**Zawsze**:
- Wywołaj prod query (przez API albo bezpośrednio prod function), NIE re-implementuj
- Jeśli musisz re-implementować (e.g., perf reasons) — replicate every WHERE clause
- Verify by sampling 10 invoices: prod result == reimpl result, before trusting reimpl

---

## Part 8 — Anti-patterns (z empirical anchorami)

| # | Anti-pattern | Anchor | Mitigation |
|---|---|---|---|
| 1 | **Test po kodzie** | `RULES §2`, `LESSONS §3` | Scenariusz w PLAN §4 PRZED §6 stages |
| 2 | **Tylko happy path** | `LESSONS §3.2` ("AI confirms implementation works — circular") | Min 5 atakujących per stage |
| 3 | **Mock zamiast real DB** | `standards §10.1` ("got burned last quarter") | Firestore emulator + real BQ |
| 4 | **Filter parity miss** | `feedback_simulation_must_match_filters.md` | Sim replikuje WSZYSTKIE prod filtry |
| 5 | **Solo-verifier** | `CONTRACT §B.8` | Reviewer ≠ author; re-run independently |
| 6 | **Float epsilon `ABS()>0.005`** | `feedback_no_float_epsilon.md` | NUMERIC = decimal; `diff != 0` exact |
| 7 | **Wrong constraint** (row-multiset gdy per-invoice) | `feedback_per_invoice_oracle_constraint.md` | Constraint w PLAN §3 explicite |
| 8 | **"Tests pass" bez output** | `RULES §3`, `standards §10.6` | Paste pytest output literally |
| 9 | **Tool sprawl** (`_temp_*.py` × 5) | `feedback_no_temp_sprawl.md` | ONE consolidated tool z subcommands |
| 10 | **Bootstrap markers w oracle diff** | (multiple memory) | Filter `init_was_*` lub apply window correctly |
| 11 | **Stale test data** (38 buy_runs `success` z poprzednich sesji) | `LESSONS §4 Mistake 4` | Clean state per test, OR cleanup pre-test |
| 12 | **AI skips what it observed** | `LESSONS §4 Mistake 5` | Reader-review: "did AI use info that exists in transcript?" |
| 13 | **Stale code in container** | `feedback_docker_rebuild_after_edit.md` | Rebuild + verify file:line w container przed test |
| 14 | **Live side-effects on edge-case test** | `feedback_live_side_effects.md` | NEVER hit mutating endpoints w test against live env |
| 15 | **Disabled test "temporary"** | `standards §10.7` | Nie wolno disable bez explicit agreement; disabled = silent regression |

---

## Part 9 — Verification — kto / kiedy / jak

### Trzy actors

| Actor | Responsibility |
|---|---|
| **Author (Driver)** | Pisze scenariusze, pisze testy, runs locally, paste output do PLAN |
| **AI Assistant** | Generuje test code, suggests edge cases, runs `/test` skill |
| **Independent Verifier** | Re-runs testy niezależnie, re-derives oracle conclusion, REJECT if diverges |

Driver + Verifier MUSZĄ być różnymi osobami / sessions. Same priors → same blind spots.

### Trzy momenty

| Moment | Co weryfikujesz | Przez kogo |
|---|---|---|
| **Pre-code** | PLAN §4 kompletny; 5 kategorii pokryte | `/deep-verify` skill (independent run) |
| **Per-stage** | Failing test → green; invariants TRUE | Author runs locally, paste output |
| **Pre-merge** | Wszystkie suites green; reviewer re-runs | Reviewer (PR comment z paste output) |
| **Post-merge** | CI green; regression weekly | CI / on-call |

### Kiedy ESCALATE

- Test passes locally, fails CI → docker rebuild issue (`feedback_docker_rebuild_after_edit.md`)
- Test passes for author, fails for reviewer → environment drift, fix BEFORE merge
- Regression suite shows variance > $0 in country that was 100% week ago → stop deploy, investigate
- Same test fails 2× in 24h after "fix" → loop, escalate to Process Owner (CONTRACT §B.13)

---

## Part 10 — Skills + tools dla testowania

| Tool | When | Output |
|---|---|---|
| `/grill` | T1 — drive UNKNOWN → CONFIRMED | Wszystkie assumptions named |
| `/plan` | T4-T5 — generate PLAN.md skeleton | PLAN with §4 + §5 stubs |
| `/test` | T7 — design/write tests for module | 10-phase methodology output |
| `/deep-verify` | T6 — independent PLAN review | ACCEPT / NEEDS-WORK / REJECT |
| `/preflight` | T8 — pre-commit gate | DID/DID NOT/CONCLUSION + suite results |
| `/develop` | T7 — execute stage with code+test | Code + test + literal output |
| `/review` | T9 — PR review (different actor) | Re-derived conclusion vs author |

`/test` skill jest **najgłębszy** dla testowania — 10 phases, 643 lines. Use for każde non-trivial test design. Jego output staje się PLAN §4.

### Useful patterns z `skills/test`

**Behavior test** (`§Test patterns`):
```python
async def test_settled_invoice_not_in_eligible():
    # Arrange — clean state, real Firestore emulator
    db = get_test_firestore()
    await db.collection("invoices").document("INV-001").set({
        "status": "settled", "amount": 100, "date_settled": "2026-04-15"
    })
    # Act — call PRODUCTION query, not reimpl
    eligible = await list_eligible(country="AU", week=17)
    # Assert — behavior, not implementation
    assert "INV-001" not in [e["invoice_id"] for e in eligible]
    # PROVES: settled invoices never reach eligible list (locks down bug 6ee9561)
```

**Architecture quality test** (`§10x scale`):
```python
async def test_settlement_query_handles_10x_scale():
    # 10x typical: 100k invoices instead of 10k
    seed_invoices(count=100_000)
    start = time.monotonic()
    result = await execute_settlement_query(country="US", week=17)
    duration = time.monotonic() - start
    assert duration < 30.0, f"Settlement at 10x scale took {duration}s, threshold 30s"
    # PROVES: query scales linearly to 10x without architectural change
```

**Data quality invariant** (telescoping):
```python
async def test_telescoping_invariant_per_invoice():
    # For each invoice: Σ change_amount == final_state - initial_state
    invoices = await get_active_invoices("CA_001")
    for inv in invoices:
        deltas = await get_markers(inv.id)
        initial = await get_state_at(inv.id, BOOTSTRAP_DATE)
        final = await get_state_at(inv.id, TODAY)
        sum_deltas = sum(m.change_amount for m in deltas)
        assert sum_deltas == final - initial, f"{inv.id} broken telescoping"
    # PROVES: marker stream is loss-less; can be replayed deterministically
```

**Regression lock-down**:
```python
async def test_regression_W17_credit_memo_24_invoices():
    """Lock-down for credit memo single-cycle fix (commit b615063, 2026-05-04).
    Bug: appeared_return + settled rows double-counted open_amount + purchased_returns.
    Fix: reroute return-class with invoice_history → collection-on-invoice."""
    rows = await call_api("/reports/CA/settlement?week=17&category=economic")
    crest = load_xlsx(CA_W17_CREST_FILE)
    diff = per_invoice_diff(rows, crest)
    assert diff.mismatch == 0, f"Credit memo regression: {diff.mismatch} mismatches"
    # PROVES: bug 24/24 PASS — never re-introduced
```

---

## Part 11 — Onboarding (2 tygodnie do solo testów)

### Tydzień 1 — Read + observe

| Day | Task | Output |
|---|---|---|
| 1 | Read `RULES §2` (write tests before code) + `standards §10` (8 rules) + this `TESTING.md` Part 1-3 | Notes: które reguły zaskoczyły |
| 1 | Read `LESSONS_LEARNED §3` (test scenarios as planning) + `§4 Mistakes 1-5` | Notes: który mistake widziałeś już w innym projekcie |
| 2 | Read `.claude/skills/test/SKILL.md` (10 phases) | Możesz wymienić 5 kategorii ataku z głowy |
| 2 | Read 3 ostatnie `.ai/PLAN_*.md` — focus na §4 Test scenarios | Notes: jakie scenariusze powtarzają się across PLANs |
| 3 | Run regression suite na main: `python tests/regression/regression.py all --week 17` + read REGRESSION.md | Output zrozumiany — co PASS / FAIL / SKIP / NO_API / NO_CREST |
| 3 | Read 3 unit testy + 3 integration testy z `backend/tests/` | Notes: które używają mocków (anti-pattern), które real DB |
| 4 | Pair z senior dev na real test design — observe, NIE driver | Notes: gdzie dev przerywa AI proposing happy path |
| 5 | Read 5 ostatnich `feedback_*.md` z memory dot. testowania | Notes: który anti-pattern poznałbyś dopiero w prod |

**Check Week 1**: czy potrafisz wymienić 5 mantras (1.3) bez patrzenia? Jeśli nie — re-read.

### Tydzień 2 — Pierwszy test solo

Wybierz pre-existing bug z TODO.md.

| Day | Stage | Output |
|---|---|---|
| 1 | T1-T3: requirements grill + oracle define + constraint define | 1 zdanie oracle z miarą; constraint named |
| 2 | T4-T5: scenarios write (5 atakujące min) + invariants write | PLAN §4 + §5 wypełnione |
| 2 | T6: /deep-verify PLAN | ACCEPT przed kodem (jeśli REJECT — iterate plan) |
| 3 | T7: write FAILING test FIRST → confirm fails for right reason | RED test committed jako PRE-fix evidence |
| 3 | T7: write fix → test green → paste pytest output do PLAN | GREEN evidence pasted |
| 4 | T7: invariants check → run unit + integration | Wszystkie inv (I1..IN) TRUE |
| 4 | T8: /preflight | All suites green, G1+G2+G3 explicit |
| 5 | T9: PR + reviewer re-runs | Independent re-run output w PR comment |
| 5 | T10: merge + CI green + add regression test for next week | Lock-down test dla tego buga |

**Readiness check Week 2** (5 z 5 must pass):
- [ ] Pisze test PRZED kodem, nie po
- [ ] Wymyśla 5 ataków zanim zatwierdzi happy path
- [ ] Mierzy oracle coverage (% covered), nie local precision
- [ ] Nie używa mocków zamiast real BQ/Firestore
- [ ] Nie ufa "it compiles" — runs niezależnie + paste output

If <5 — extend by 1 week with focus on the gap.

---

## Part 12 — Metrics

Co mierzymy żeby wiedzieć że proces działa.

### Leading (collect weekly)

| Metric | Source | Target |
|---|---|---|
| % PRs with §4 Test scenarios in PLAN PRZED commit 1 | `git log` + `.ai/PLAN_*.md` mtime | >80% non-trivial |
| % testów z literal output paste | grep PLAN §6 stages | 100% |
| % bug fixes z dedicated regression test | grep `tests/regression/test_R*` | 100% |
| Avg # commits per merged PR | `git log --merges` | <5 (high → pendulum) |
| % PRs gdzie reviewer re-ran tests (paste output w comment) | grep PR body | 100% data work |

### Lagging (collect monthly)

| Metric | Source | Target |
|---|---|---|
| # bugs returning po fix | LESSONS_LEARNED.md regression patterns | 0 (każdy = process gap) |
| # mockujących testów | grep `mock_` w `tests/` | 0 dla DB, ~0 ogólnie |
| % oracle coverage growth per quarter | regression.py weekly snapshots | growing |
| # tests disabled (`@pytest.mark.skip`) | grep skip | 0 (per `standards §10.7`) |
| Mean time test suite runs | CI logs | <10 min unit; <30 min integration |

### Health checks (quarterly)

- Czy są testy które failują od miesiąca? (Disabled lub broken — fix or delete)
- Czy regression suite nadal odpowiada current business rules? (Update if rules changed)
- Czy każdy past incident z PRACTICE_SURVEY ma regression test? (If not — add)
- Czy onboarding (Part 11) success rate jest >80% w 2 tyg? (If not — improve)

---

## Part 13 — Honesty about gaps

Co działa empirycznie:
- Test scenarios przed kodem w PLAN §4 (LESSONS §3 - validated cross-incident)
- Oracle pattern dla data work (CA W17 6/6 PASS, BE W17 100% post-replay)
- Filter parity rule (zapobiegło $12.5k false signal)
- Real DB w integration tests (no incidents post mock-elimination)

Co podejrzewamy że działa, niezweryfikowane:
- 2-tyg onboarding target (mała próbka — track)
- Quarterly metrics (cykl jeszcze nie zamknięty)
- 10-phase /test skill efficacy (used <10× — track outcomes)

Co NIE jest pokryte:
- Property-based testing (hypothesis-style) — nie używamy systematycznie
- Mutation testing — none
- Performance regression baseline — manual, not automated
- Frontend visual regression — not in scope dotychczas
- Chaos / fault injection — not in scope

When you hit a gap → add to `LESSONS_LEARNED.md` + Part 12.4 trigger to evolve.

---

## Part 14 — One-page summary (cheat sheet)

```
ORACLE → CONSTRAINT → SCENARIOS → INVARIANTS → /deep-verify
       → CODE → RED → GREEN → INV CHECK → /preflight → PR (reviewer re-runs) → CI

5 KATEGORII SCENARIUSZY (per stage, min):
  1. Empty / Boundary       (≥2)
  2. Idempotency            (≥1)
  3. Failure mode           (≥1)
  4. Out-of-order           (≥1 if applicable)
  5. Regression (lock bug)  (≥1 per past incident)
  + 1 happy path (max)

3 INVARIANTS DLA KAŻDEGO TESTU:
  1. No mocks for DB
  2. Clean state per test
  3. Run before "done" — paste output

OUTPUT RULE: pytest output paste literally. NEVER "tests pass".

WORK CLASS DECIDES MANDATORY:
  Bug fix      → 1 happy + 2 edge + REGRESSION for the bug
  Feature      → 5 atakujące + 1 happy + ≥1 regression (all 4 layers)
  Refactor     → golden master (input/output before+after)
  Data work    → per-invoice oracle + invariants (telescoping)
  Investigation→ NO TESTS (output is doc + numbers)
  Prototype    → NO TESTS (visual only, NEVER merged)

ANTI-PATTERNS (Part 8 — 15 entries):
  Top 5: test po kodzie / tylko happy / mock DB / filter parity miss / solo-verifier

WHEN STUCK:
  - Test pass locally, fail CI    → docker rebuild
  - Test pass author, fail review → env drift (fix BEFORE merge)
  - 2× fail in 24h after "fix"    → loop, escalate
```

---

## Part 15 — Reference map

| You need | Read |
|---|---|
| 8 testing rules + delivery checklist | `standards §10` + §14 |
| Test design 10-phase methodology | `.claude/skills/test/SKILL.md` |
| Why test-before-code (empirical) | `LESSONS §3` |
| 5 testing mistakes from past | `LESSONS §4` |
| Test scenarios in PLAN.md template | `WORKFLOW §5.2` + `templates/` |
| Regression suite usage | `tests/regression/REGRESSION.md` |
| Pre-commit gate | `.claude/skills/preflight/SKILL.md` |
| PR review skill | `.claude/skills/review/SKILL.md` |
| Per-incident retrospective format | `framework/PRACTICE_SURVEY.md` |
| Anti-patterns library (cross-cutting) | `PROCESS.md Part 11` |
| Working with the AI assistant | `PROCESS.md Part 5` |

---

> **Test scenarios przed kodem. Atak, nie potwierdzenie. Literal output, nie deklaracja. System, nie funkcja. Filter parity z prod.**

# PROMPT TEMPLATE — Theorem-Compliant Test Scenarios From Code

> Reusable prompt template for delegating test scenario design to a sub-agent.
> Verified against `.ai/theorems/test/Topologically Closed Data Regression Testing Theorem.md` — section by section.
> Empirical foundation: WORKFLOW §10 prompt-first pattern + LESSONS §3 (test scenarios as planning) + theorem §1–§24.
>
> Usage:
> 1. Replace `<TARGET_PATH>`, `<MODULE_NAME>`, `<BUSINESS_CONTEXT>`, `<CHANGE_TYPE>`, `<CHANGE_DESCRIPTION>`
> 2. Run via Agent({ prompt: <THIS TEMPLATE>, subagent_type: "general-purpose" })
> 3. Verify output with /deep-verify + /deep-risk + theorem compliance checklist (§Final acceptance below)

---

## PROMPT (paste to agent)

```
ROLE: Test Architect for data-processing systems. You design a regression test plan
that satisfies the Topologically Closed Data Regression Testing Theorem (§1–§22).
Tests are PROOF, not verification. NO happy-path-only.

=== PRE-CONDITIONS (mandatory before any other action) ===
1. Read `.ai/CONTRACT.md` — operational contract.
2. Read `.ai/theorems/test/Topologically Closed Data Regression Testing Theorem.md`.
3. Read `.ai/RULES.md §2`, `.ai/standards.md §10`, `.ai/TESTING.md`.
4. Confirm: "Pre-conditions read. Theorem §1–§22 internalized."

=== INPUT ===
Target code path:        <TARGET_PATH>
Module name:             <MODULE_NAME>
Business context:        <BUSINESS_CONTEXT>
Change type (one of):    filter | join | amount_formula | date_boundary | classification | new_object | refactor | other
Change description:      <CHANGE_DESCRIPTION>

=== DELIVERABLE ===
Single file: `.ai/TEST_SCENARIOS_<MODULE_NAME>.md`
Structure: §1–§9 below. Every section MANDATORY. Missing section = NOT DELIVERED.

The plan must satisfy:
  ValidRegressionPlan(ΔK) ⇔
      Tested(ImpactClosure(ΔK))
    ∧ ExpectedChangesDefined          (per-node, with causal_path + tolerance)
    ∧ UnexpectedChangesRejected       (per-node, with forbidden delta)
    ∧ TestsAreIdempotent              (5 sub-rules from §8)
    ∧ EvidenceIsObjective             (6-tuple per §14)
    ∧ BaselineLocked                  (per §9)

================================================================
§1 CHANGE DESCRIPTION (per theorem §24.1)
================================================================
1.1 Changed files:           <list — with file:line ranges>
1.2 Changed logic:           <prose — what behaviour changes>
1.3 Changed formulas:        <list — old → new>
1.4 Changed filters:         <list — old WHERE → new WHERE>
1.5 Changed joins:           <list — old JOIN keys → new>
1.6 Changed boundaries:      <list — date inclusive/exclusive, range bounds>
1.7 ChangeType (one of §16): filter | join | amount_formula | date_boundary | classification | new_object | refactor | other
1.8 v0 (changed node):       <node id — table / view / CTE / function / endpoint>

================================================================
§2 CODE ANALYSIS (technical + business)
================================================================
2.1 Technical functions inventory (read every .py/.ts/.sql file in TARGET_PATH — NO sampling):
    Table: function/class | signature | inputs | outputs | side_effects | file:line

2.2 Business functions / invariants:
    Which business rules does the code enforce?
    Cite: file.py:N

2.3 Criticality classification:
    Table: element | classification (CRITICAL / IMPORTANT / SUPPORT) | reason
    CRITICAL = financial, regulatory, data integrity (production failure if broken)
    IMPORTANT = user-facing degradation
    SUPPORT = internal helper

2.4 Dependencies:
    External systems (BQ tables, Firestore collections, APIs)
    Internal modules consumed
    Libraries with semver risk

================================================================
§3 IMPACT GRAPH — ImpactClosure(v0)  (per theorem §3, §4, §24.2)
================================================================
3.1 Direct neighbors N1(v0):
    <list nodes directly reading/writing v0>

3.2 Closure by neighbour iteration N_k until N_(k+1) = N_k:
    Iterate the graph: N_2 = neighbours(N_1), N_3 = neighbours(N_2), ...
    Stop at fixed point. Output N_1, N_2, ..., N_final.

3.3 ImpactClosure(v0) =
    DirectImpact ∪ DownstreamTables ∪ DownstreamViews ∪ DownstreamReports
    ∪ DownstreamMetrics ∪ DownstreamAPIs ∪ DownstreamBusinessOutputs

    Output: full impact graph as table:
    | node | type (table/view/CTE/function/report/api) | reachability_path_from_v0 | criticality |

3.4 Terminal business outputs:
    Which user-facing reports / API responses / dashboards depend on v0?
    These are the FINAL nodes the change affects from business perspective.

================================================================
§4 EXPECTED CHANGES — per impacted node  (per theorem §5, §24.3)
================================================================
For EVERY x ∈ ImpactClosure(v0) where ΔK is expected to change x:

| node | column/metric | before | after | expected_delta | causal_path (ΔK → x) | business_reason | tolerance |

Rules:
- expected_delta MUST be a number, range, or "<none — should be unchanged>"
- causal_path MUST be a sentence: "ΔK changes mechanism M, which propagates via path V→V′→x, therefore Δ = X"
- tolerance MUST be specified (e.g. ±$0.01 for money, 0 for counts, 1ms for time)
- NO "looks right", NO "should be ok", NO "approximately" — only objective values

================================================================
§5 UNEXPECTED CHANGES — per impacted node  (per theorem §6, §24.4)
================================================================
For EVERY x ∈ ImpactClosure(v0):

| node | property/column | must_remain | forbidden_delta | max_tolerance |

Examples:
- "Country aggregate sum must remain unchanged ±$0 — any delta is regression"
- "Per-customer count must remain unchanged"
- "Schema columns: no addition, no removal, no type change"

This section IS NOT optional. If you cannot list forbidden deltas — you do not understand the change well enough.

================================================================
§6 COLUMN IMPACT — per affected table/view  (per theorem §10)
================================================================
For EVERY v ∈ ImpactClosure(v0) that is a table/view:

For every column c ∈ schema(v), assign exactly one status:
| node | column | status |

Status values (exactly one per column, EXHAUSTIVE):
  - expected_changed          (with reason in §4)
  - expected_unchanged
  - new_expected              (added by ΔK; new object — see §7)
  - removed_expected          (removed by ΔK)
  - forbidden_change          (must remain — any change is regression)

Verify: schema(v) listed columns == columns with assigned status. No column "TBD" / "unknown" / missing.

================================================================
§7 NEW OBJECTS — 8 mandatory tests each  (per theorem §11)
================================================================
For EVERY new object o created by ΔK (new table, view, CTE, column, bucket, category, metric):

| object o | T1 existence | T2 schema | T3 grain | T4 expected_values | T5 nullability | T6 uniqueness | T7 business_semantics | T8 downstream_consumption |

For each cell: 1-line scenario description + expected outcome.

Expected values for new object MUST derive from one of:
  - source data
  - business rule (cite memory / spec / requirement)
  - previous verified behavior
  - explicit accepted assumption (with [ASSUMED: accepted-by=<role>, date=YYYY-MM-DD])

If no new objects: write "NONE" — do not skip the section.

================================================================
§8 TEST SET  (per theorem §12, §16, §17, §24.5)
================================================================
8.1 ChangeType-driven required tests (§16 dispatcher):

If ChangeType = filter:
  - row_count_before_after
  - excluded_rows_sample (≥10 invoices showing what's filtered out)
  - boundary_values (inclusive/exclusive date, NULL handling)
  - per-category count
  - downstream aggregates (per terminal output in §3.4)

If ChangeType = join:
  - duplicate amplification (rows multiply unexpectedly?)
  - unmatched left rows count
  - null join keys handling
  - many-to-many explosion check
  - downstream sum delta

If ChangeType = amount_formula:
  - per-row expected calculation (≥5 worked examples)
  - sum by business key
  - sign convention (+/-)
  - currency consistency
  - null/zero behavior

If ChangeType = date_boundary:
  - inclusive/exclusive tests
  - first day / last day
  - previous period leakage
  - future partition stability

If ChangeType = classification:
  - class distribution before/after
  - moved records (which records crossed?)
  - unmapped records (any remain "uncategorised"?)
  - conflict records (record qualifies for >1 class?)

If ChangeType = new_object:
  - per §7 above (8 tests per object)

If ChangeType = refactor:
  - golden master: input/output capture before & after, diff = 0

8.2 Multi-level coverage (per theorem §18) — every level MUST have ≥1 test:
  L1 row-level
  L2 invoice-level (or equivalent business key)
  L3 bucket-level (e.g. category, week)
  L4 country-level (or equivalent partition)
  L5 report-level
  L6 business-outcome-level

8.3 Attacking categories (per theorem §12, mandatory):
  - boundary_tests       (≥2)
  - negative_tests       (≥2 — input that should fail / be rejected)
  - failure_tests        (≥1 — mid-operation failures)
  - regression_tests     (≥1 per past commit fixing this code area; link commit hash)
  - invariants           (≥3 — see §9)

8.4 Per-test format (mandatory fields):
  | id | level (L1-L6) | category | input | action | expected | tolerance | what_bug_does_this_catch | proves |

8.5 Anti-scenarios (declare what you do NOT test, with reason):
  - implementation details (e.g. "uses dict vs list")
  - third-party library behaviour
  - mock behaviour

If any test cannot answer "what bug does this catch?" → it is ceremony, drop it (theorem §12).

================================================================
§9 INVARIANTS  (per theorem §13)
================================================================
Minimum 3 invariants. Each must hold BEFORE and AFTER ΔK.

Examples (use applicable ones, add domain-specific):
  - row_count_after within expected range [N_min, N_max]
  - sum_amount_after = sum_amount_before + expected_delta (per business key)
  - no_duplicate_business_key
  - one_active_record_per_key
  - no_unexpected_nulls in column C
  - known_categories_only (no NEW unmapped category)
  - foreign_keys_resolve (every FK has matching parent)
  - all_report_rows_have_source_lineage

Format per invariant:
| id | statement | how_to_verify (SQL / code snippet) | applies_before_AND_after | exception (if explicit business change expected) |

================================================================
§10 BASELINE  (per theorem §9, §24.6)
================================================================
10.1 Input snapshot:
  - Source: <table / file / API endpoint>
  - Snapshot date / version: <ISO date or version tag>
  - Frozen: how to ensure snapshot does not drift during test execution
            (e.g. "BQ table partition `2026-04-20`, read-only", "CSV committed in tests/fixtures/")

10.2 Expected output version:
  - File: <e.g. tests/fixtures/expected_<module>_<date>.json>
  - Versioned in git (commit hash): <commit>
  - Update protocol: explicit decision required (no silent overwrite)

10.3 Known expected variance (per theorem §15):
  - Documented variances to subtract before alarm:
    | source | reason | magnitude | tolerance |
  - RealAnomaly = ObservedDelta - ExpectedDelta - ExpectedVariance
  - Alarm only if |RealAnomaly| > tolerance

10.4 Tolerance per metric:
  | metric | tolerance | reason |

================================================================
§11 IDEMPOTENCY  (per theorem §8, §24.7)
================================================================
Every test must be idempotent. Verify all 5 sub-rules:

11.1 NO source data mutation:
  Test does NOT modify input snapshot. Verified by: <how>
11.2 NO current-date dependency:
  Test does not depend on `today()` without parameterisation. Verified by: <how>
11.3 NO randomness:
  No random seeds, no UUID generation in test logic. Verified by: <how>
11.4 NO order dependency:
  Tests can run in any order; state is reset between tests. Verified by: <how>
11.5 NO baseline overwrite without explicit decision:
  Expected output not silently regenerated. Verified by: <how>

Acceptance:
  ∀ n ≥ 1: TestRun_n(T, Snapshot) = TestRun_1(T, Snapshot)

================================================================
§12 EVIDENCE FORMAT (per theorem §14)
================================================================
For every test, deliverable evidence MUST be a 6-tuple:
  - command (literal pytest / bq query / curl)
  - input_snapshot (path / version)
  - output_before (state at baseline)
  - output_after (state after ΔK)
  - expected_delta (from §4 per node)
  - conclusion (PASS_EXPECTED_CHANGE / PASS_UNCHANGED / FAIL_*)

"Tests pass" without 6-tuple = NOT delivered.

================================================================
§13 REGRESSION MATRIX  (per theorem §20)
================================================================
Build matrix with EVERY x ∈ ImpactClosure(v0) as row, every metric as column.

| node | metric | before | after | expected_delta | observed_delta | unexplained_delta | status |

Status (exactly one per cell, exhaustive):
  - PASS_EXPECTED_CHANGE      (observed == expected within tolerance)
  - PASS_UNCHANGED            (no change observed where none expected)
  - FAIL_UNEXPECTED_CHANGE    (changed where forbidden)
  - FAIL_MISSING_EXPECTED_CHANGE  (no change where expected)
  - FAIL_UNKNOWN_CHANGE       (changed in way not classified — investigate)

Acceptance (per theorem §21):
  Accept(ΔK) ⇔ ∀ row: status ∈ {PASS_EXPECTED_CHANGE, PASS_UNCHANGED}

Any FAIL_* row → ΔK is REJECTED until explained or fixed.

================================================================
§14 COVERAGE MATRIX (Topological closure verification)
================================================================
Cross-reference §3.3 ImpactClosure × §8.4 test set + §9 invariants:

| element ∈ ImpactClosure | scenario_id (or invariant_id) | level (L1-L6) | covered ✓/✗ |

Hard rule (theorem §3 condition):
  ∀ x ∈ ImpactClosure(ΔK): ∃ test t ∈ T : verifies(t, x)

Untested rows (✗) are listed at end of section. List MUST be empty.
If non-empty: add scenarios; do not deliver until empty.

================================================================
§15 FAILURE LOCALIZATION  (per theorem §19)
================================================================
For each test, write a 1-line localization claim:
  "If this test fails, the cause is narrowed to: <specific component / condition>"

Bad: "report differs"
Good: "Row 1b invoice_delta changed only for invoices with reappeared marker AND no purchased_book match"

If a test failure cannot localize → split into smaller tests until each does.

================================================================
§16 SELF-CHECK BEFORE DELIVERY (theorem compliance gate)
================================================================
Final checklist. ALL must be checked. Unchecked = NOT delivered, iterate.

[ ] §1: ChangeType assigned, v0 named
[ ] §3: ImpactClosure computed via fixed-point N_k iteration
[ ] §3: Every node has reachability_path_from_v0
[ ] §4: Every expected change has causal_path + tolerance
[ ] §5: Every impacted node has forbidden_delta
[ ] §6: Every column in every affected table has status (5 categories)
[ ] §7: Every new object has 8 tests filled (or "NONE")
[ ] §8.1: ChangeType-specific required tests dispatched
[ ] §8.2: All 6 levels (L1-L6) have ≥1 test
[ ] §8.3: ≥2 boundary, ≥2 negative, ≥1 failure, ≥1 regression per past commit, ≥3 invariants
[ ] §8.4: Every test has "what_bug_does_this_catch?" filled
[ ] §9: ≥3 invariants with verify procedure
[ ] §10: Baseline locked (snapshot + expected output versioned + variance documented)
[ ] §10: Tolerance defined per metric
[ ] §11: All 5 idempotency sub-rules verified per test
[ ] §12: Evidence format = 6-tuple defined per test
[ ] §13: Regression matrix has 5-status classification per cell
[ ] §14: Coverage matrix — every ImpactClosure node has ≥1 ✓ — UNTESTED LIST EMPTY
[ ] §15: Every test has localization claim
[ ] No mocks for DB (real Firestore emulator / real BQ)
[ ] Filter parity: if code uses filters (sell_invoice, active_le_codes, etc.),
    scenarios use SAME filter set as production
[ ] Anti-scenarios listed (what we deliberately do NOT test)
[ ] References cited: which memory entries / commits / past incidents informed scenarios

If any unchecked → iterate. Do not deliver until ALL checked.

================================================================
§17 DISCLOSURE TAGS (per CONTRACT §B)
================================================================
[CONFIRMED] = read the file, quoting line:N
[ASSUMED]   = inferred from name / signature, did not run
[UNKNOWN]   = STOP, ask user

Count [ASSUMED] and list at end. Count [UNKNOWN] — must be 0 to deliver.

================================================================
SCOPE BOUNDARIES
================================================================
IN scope:  test scenario design (this document only)
OUT of scope: writing pytest code (separate task), running tests (separate task)

================================================================
OUTPUT
================================================================
Single markdown file: `.ai/TEST_SCENARIOS_<MODULE_NAME>.md` with sections §1–§17.
At end: [ASSUMED] count, [UNKNOWN] count (must be 0), self-check (§16) all checked.
```

---

## Verification flow (after agent delivers — done by parent / user)

### Stage A — Logical/factual verification
```
/deep-verify .ai/TEST_SCENARIOS_<MODULE_NAME>.md
```
Output: ACCEPT / NEEDS-WORK / REJECT.

### Stage B — Risk assessment
```
/deep-risk .ai/TEST_SCENARIOS_<MODULE_NAME>.md
```
Output: what could go wrong WITH THIS TEST PLAN itself.

### Stage C — Theorem compliance check (deterministic)

Verify against the theorem section by section. Use this checklist (matches §16 self-check):

```
THEOREM COMPLIANCE CHECK — Topologically Closed Data Regression Testing Theorem

§2.1   v0 identified                    [ ]
§2.2   ImpactClosure(v0) computed       [ ]
§2.3   Expected O per impacted node     [ ]
§2.4   Unexpected U per impacted node   [ ]
§2.5   Every column/metric/report verified  [ ]
§2.6   Causal justification for every expected value  [ ]
§2.7   Idempotency (5 sub-rules §8)     [ ]
§2.8   Repeatable on snapshot           [ ]
§2.9   Distinguishes expected delta from regression  [ ]
§2.10  No untested impacted element     [ ]
§4     Fixed-point N_k iteration done   [ ]
§5     ExpectedChange has causal_path + tolerance     [ ]
§6     UnexpectedChange enumerated per node           [ ]
§7     Regression objective (|Obs - Exp| > tol)       [ ]
§9     Frozen baseline (snapshot + expected output)   [ ]
§10    ColumnImpact 5 statuses per column             [ ]
§11    New objects: 8 tests each (or NONE declared)   [ ]
§12    Tests = success ∪ failure ∪ boundary ∪ negative ∪ regression ∪ invariants  [ ]
§13    ≥3 invariants                    [ ]
§14    Evidence 6-tuple                  [ ]
§15    ExpectedVariance subtraction      [ ]
§16    ChangeType → required tests       [ ]
§17    Generated from topology           [ ]
§18    6 levels (L1-L6) covered          [ ]
§19    Failure localization              [ ]
§20    RegressionMatrix 5-status         [ ]
§21    Acceptance criterion              [ ]
§22    All 10 conditions                 [ ]
§24    Runtime template structure        [ ]
```

If any unchecked → re-prompt agent with specific gap.

### Stage D — Final acceptance

Once Stage A = ACCEPT, Stage B = no critical risks, Stage C = all checked:
- Test plan accepted
- Move to implementation: tests written from §8 scenarios using `/test` skill or `/develop`

---

## When to use this template vs `/test` skill directly

| Use this template | Use `/test` skill |
|---|---|
| Data work / financial code (theorem applies) | UI / pure logic without data graph |
| Multi-stage verification gates needed | Single-pass acceptable |
| Need formal regression matrix per theorem §20 | Informal output OK |
| Junior on team — explicit theorem scaffolding | Senior knows the patterns |
| High-stakes change (regulatory, financial, irreversible) | Low-risk module |

---

## Reference

- `.ai/theorems/test/Topologically Closed Data Regression Testing Theorem.md` — formal foundation (24 sections)
- `.ai/TESTING.md` — full testing process for this codebase
- `.ai/PROCESS.md Part 6` — verification & merge flow
- `WORKFLOW.md §10` — Prompt-first pattern
- `LESSONS_LEARNED.md §3` — test scenarios as planning
- `.claude/skills/test/SKILL.md` — single-shot test design (alternative)
- `.claude/skills/test-orchestrate/SKILL.md` — automated 9-phase orchestrator (calls this template)

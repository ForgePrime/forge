TOPOLOGICALLY CLOSED & RATIONAL DATA REGRESSION TESTING THEOREM

A data regression test suite is valid iff it is generated from the full topology
of the impacted data process, verifies every expected and forbidden change,
uses locked evidence, tests real data logic, rejects fake coverage, and reports
all untested or untestable areas explicitly.


1. DEFINITIONS

Let:

K      = existing code
ΔK     = code change
D      = data space
G      = data process graph
V      = process nodes
E      = dependency edges
T      = regression test suite
B      = baseline
S      = frozen input snapshot
O      = expected changes
U      = unexpected / forbidden changes
GAP    = untested or untestable space
INV    = invariants
RISK   = risk space

Where:

V = {
    source tables,
    intermediate tables,
    views,
    CTEs,
    functions,
    jobs,
    reports,
    metrics,
    endpoints,
    dashboards,
    business outputs
}

E = {
    reads_from,
    writes_to,
    depends_on,
    transforms,
    aggregates,
    joins,
    filters,
    exposes_to
}

G = (V, E)

A code change ΔK touches one or more nodes:

ChangedNodes(ΔK) = {v0, v1, ..., vn}


2. IMPACT CLOSURE

Every code change has a downstream impact topology.

ImpactClosure(ΔK) =
    ChangedNodes(ΔK)
    ∪ DownstreamTables(ΔK)
    ∪ DownstreamViews(ΔK)
    ∪ DownstreamCTEs(ΔK)
    ∪ DownstreamFunctions(ΔK)
    ∪ DownstreamReports(ΔK)
    ∪ DownstreamMetrics(ΔK)
    ∪ DownstreamAPIs(ΔK)
    ∪ DownstreamBusinessOutputs(ΔK)

Equivalently:

ImpactClosure(ΔK) = { v ∈ V : ∃ path(changed_node → v) in G }

The regression test scope is:

TestScope(ΔK) = ImpactClosure(ΔK)

Therefore:

∀ x ∈ ImpactClosure(ΔK):
    x must be tested
    OR x must have explicit GapRecord(x)


3. MAIN THEOREM

A regression test suite T is valid for a data-processing code change ΔK iff:

ValidRegressionPlan(ΔK, T) ⇔

    TopologicalCoverage(ΔK, T)
    ∧ ExpectedChangeModelComplete(ΔK)
    ∧ UnexpectedChangeModelComplete(ΔK)
    ∧ BaselineValid(B, S)
    ∧ TestsAreExecutable(T)
    ∧ TestsUseRealDataLogic(T)
    ∧ TestsHaveStrongOracles(T)
    ∧ TestsDetectRealFaults(T)
    ∧ TestsAreIdempotent(T)
    ∧ TestsAreRepeatable(T, S)
    ∧ TestsAreMeaningful(T)
    ∧ NoFakeCoverage(T)
    ∧ MultiLevelRegressionCoverage(T)
    ∧ AllNewObjectsValidated(ΔK, T)
    ∧ AllUntestedAreasReported(GAP)
    ∧ AcceptanceDecisionIsEvidenceBased(ΔK, T)


4. TOPOLOGICAL COVERAGE CONDITION

TopologicalCoverage(ΔK, T) ⇔

    ∀ x ∈ ImpactClosure(ΔK):
        ∃ t ∈ T:
            verifies(t, x)
        OR
        ∃ gap ∈ GAP:
            documents(gap, x)

If:

    ∃ x ∈ ImpactClosure(ΔK):
        ¬Tested(x)
        ∧ ¬DocumentedGap(x)

then:

    RegressionPlanInvalid


5. NEIGHBOR EXPANSION CONDITION

For every changed node v0:

N1(v0) = direct_downstream_neighbors(v0)

For k > 1:

Nk(v0) = direct_downstream_neighbors(Nk-1(v0))

The full impact scope is reached at fixed point:

N(k+1) = Nk

Then:

ImpactClosure(v0) = ⋃ Nk(v0) until fixed_point

Meaning:

test from the changed node through every downstream terminal output.


6. CHANGE TYPE TO TEST TYPE MAPPING

Tests are not chosen manually.
They are generated from the change type and topology.

T(ΔK) =
    GenerateTests(
        ChangeType(ΔK),
        ImpactClosure(ΔK),
        DataRisk(ImpactClosure),
        BusinessCriticality(ImpactClosure)
    )

Required mapping:

filter change →
    row_count_before_after
    excluded_rows_sample
    boundary_values
    per_category_count
    downstream_aggregate_delta
    forbidden_leakage_test

join change →
    duplicate_amplification_test
    unmatched_left_rows_test
    null_join_key_test
    many_to_many_explosion_test
    downstream_sum_delta_test
    grain_preservation_test

amount formula change →
    per_row_expected_calculation
    sum_by_business_key
    sign_convention_test
    currency_consistency_test
    null_zero_behavior_test
    rounding_tolerance_test

date boundary change →
    inclusive_exclusive_boundary_test
    first_day_last_day_test
    previous_period_leakage_test
    future_partition_stability_test
    timezone_cutoff_test

classification change →
    class_distribution_before_after
    moved_records_test
    unmapped_records_test
    conflict_records_test
    downstream_bucket_delta_test

schema change →
    existence_test
    column_type_test
    nullability_test
    backward_compatibility_test
    downstream_consumption_test

deduplication change →
    duplicate_key_count_test
    retained_record_selection_test
    tie_breaker_test
    idempotency_test
    downstream_count_stability_test

aggregation change →
    group_key_test
    aggregate_formula_test
    subtotal_total_reconciliation
    missing_group_test
    duplicate_group_test

permission / security filter change →
    allowed_records_test
    forbidden_records_test
    role_boundary_test
    no_data_leakage_test
    auditability_test

retry / reprocessing change →
    same_snapshot_same_output_test
    no_duplicate_write_test
    checkpoint_consistency_test
    watermark_boundary_test
    partial_failure_recovery_test


7. EXPECTED CHANGE MODEL

Every expected change must be defined before execution.

ExpectedChange(x) ⇔

    changed(x)
    ∧ causal_path(ΔK → x)
    ∧ changed_logic_identified(x)
    ∧ business_reason(x)
    ∧ expected_delta(x)
    ∧ expected_value_or_range(x)
    ∧ tolerance(x)
    ∧ evidence_source(x)

Forbidden:

    ExpectedDelta(x) = ObservedDelta(x) after execution
    without prior causal derivation

Expected change must be derived from:

    source data
    ∪ changed logic
    ∪ business rule
    ∪ accepted assumption
    ∪ previous verified behavior


8. UNEXPECTED CHANGE MODEL

For every impacted element x, forbidden changes must also be defined.

UnexpectedChange(x) ⇔

    changed(x)
    ∧ no_causal_path(ΔK → x)

OR:

    observed_delta(x) ∉ ExpectedChangeSet(x)

Condition:

    ∀ x ∈ ImpactClosure(ΔK):
        if changed(x) and not expected(x):
            FAIL


9. OBJECTIVE REGRESSION DEFINITION

A difference is not automatically a regression.

Regression(x) ⇔

    observed_delta(x) ≠ expected_delta(x)

More precisely:

ExpectedAfter(x) = Before(x) + ExpectedDelta(x)

Regression(x) ⇔

    abs(ObservedAfter(x) - ExpectedAfter(x)) > tolerance(x)

With expected variance:

RealAnomaly(x) =
    ObservedDelta(x)
    - ExpectedDelta(x)
    - ExpectedVariance(x)

Fail condition:

    abs(RealAnomaly(x)) > tolerance(x)


10. BASELINE VALIDITY CONDITION

Regression testing requires a locked reference point.

BaselineValid(B, S) ⇔

    input_snapshot_locked(S)
    ∧ expected_output_locked(B)
    ∧ expected_output_versioned(B)
    ∧ config_version_locked
    ∧ code_version_before_known
    ∧ code_version_after_known
    ∧ baseline_not_overwritten_without_decision
    ∧ known_variance_defined

Without this:

    cannot distinguish code change from data/config/test drift.


11. REAL DATA LOGIC CONDITION

A regression test is valid only if it executes the real transformation logic
or a contract-equivalent executable representation.

∀ t ∈ T:

    executes_real_data_logic(t)
    OR
    executes_contract_equivalent_logic(t)

Invalid tests:

    test only fixture shape
    test only mock output
    test only query success
    test only non-null existence
    test only count > 0
    test only dashboard loads


12. STRONG ORACLE CONDITION

Every test must have an objective oracle.

StrongOracle(t) ∈ {
    exact_expected_value,
    expected_delta,
    invariant,
    reconciliation,
    schema_contract,
    grain_contract,
    uniqueness_contract,
    nullability_contract,
    distribution_contract,
    golden_dataset,
    differential_comparison,
    property_based_assertion,
    business_rule_assertion
}

---

## Empirical anchors (2026)

| Anchor | What this theorem caught / would have caught |
|---|---|
| **CA W17 credit-memo single-cycle, 24/24 PASS** (commit `b615063`, 2026-05-04) | §6 ChangeType=amount_formula → required tests dispatched; per-invoice oracle constraint (theorem §3) confirmed match |
| **AU/BE/CA × W17+W18 = 6/6, $0.00 diff post-fix** | §3 ImpactClosure (settlement_queries → all country reports) covered by regression suite; matches §11 acceptance |
| **22 "multi-week recurring residual" was simulation artifact** (filter parity not preserved — `sell_invoice` filter missing in sim) | §7 ExpectedChange = causal_path required; missing filter = no causal path → falsifies the "residual" hypothesis |
| **Settlement v3 99.97% per-invoice match BE W17** (`project_v3_architecture_validated_be_w17.md`) | §10 BaselineValid (input snapshot locked); per-invoice constraint, not row-multiset (`feedback_per_invoice_oracle_constraint.md`) |

## Status (per `AUDIT.md` 2026-05-05)

ACCEPT — canonical for data regression testing. Operational template in `.ai/templates/PROMPT-test-scenarios-from-code.md`. Orchestrator skill: `.claude/skills/test-orchestrate/SKILL.md`. Process integration: `TESTING.md`.
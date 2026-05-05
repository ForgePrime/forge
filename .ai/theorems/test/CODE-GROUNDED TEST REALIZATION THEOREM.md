CODE-GROUNDED TEST REALIZATION THEOREM

A test suite is valid only if it is derived from executable code behavior,
mapped to Scope/SPEC intent, justified by risk or contract value,
able to fail under real defects, and able to prove success through explicit oracles.

Definitions:

SC   = Scope
SP   = Specification
C    = Codebase
CU   = code units: functions, classes, endpoints, jobs, pipelines, commands
CP   = executable code paths
BR   = branches
SE   = side effects
DEP  = external dependencies
ST   = state transitions
ERR  = error/failure branches
INV  = invariants
RISK = risk space
T    = tests
GAP  = untested / untestable / unjustified area

Derived from code:

CU = parse(C)

For each cu ∈ CU:

CodeProfile(cu) = {
    public_interface,
    inputs,
    outputs,
    return_types,
    exceptions,
    branches,
    side_effects,
    dependencies,
    state_mutations,
    data_contracts,
    security_constraints,
    concurrency_points,
    temporal_logic,
    retries,
    error_handling,
    logging_observability,
    business_rule_candidates
}

ExecutablePath(cu) = {
    happy_path,
    branch_paths,
    edge_paths,
    error_paths,
    dependency_failure_paths,
    state_transition_paths,
    retry_paths,
    rollback_paths,
    concurrency_paths,
    permission_paths,
    data_quality_paths
}

A test suite is correct iff:

CodeTestClosure(C, SC, SP, T, GAP) = true
1. CODE-GROUNDEDNESS CONDITION

No test may exist only as a conceptual scenario.

∀ t ∈ T :
    ∃ cu ∈ CU :
        calls_or_executes(t, cu) = true

If:

¬∃ cu : calls_or_executes(t, cu)

then:

t = invalid_conceptual_test
2. CODE PATH COVERAGE CONDITION

For every relevant executable path:

∀ cp ∈ CP :
    if must_test(cp) = true :
        ∃ t ∈ T :
            executes(t, cp)
            ∧ asserts_expected_result(t, cp)
            ∧ observes_failure_signal(t, cp)

If:

must_test(cp) = true
∧ ¬∃ t : executes(t, cp)

then:

untested_required_code_path(cp) = true
3. MUST-TEST DECISION FUNCTION

A code path must be tested if any condition is true:

must_test(cp) ⇔

    traced_to_scope(cp)
    ∨ traced_to_spec(cp)
    ∨ implements_business_rule(cp)
    ∨ changes_state(cp)
    ∨ writes_data(cp)
    ∨ deletes_data(cp)
    ∨ calls_external_dependency(cp)
    ∨ handles_error(cp)
    ∨ controls_permission(cp)
    ∨ affects_money_or_compliance(cp)
    ∨ transforms_data_contract(cp)
    ∨ has_branching_complexity(cp) ≥ threshold
    ∨ has_historical_bug(cp)
    ∨ is_public_interface(cp)
    ∨ is_integration_boundary(cp)
    ∨ is_retry_or_reprocessing_path(cp)
    ∨ is_security_sensitive(cp)
    ∨ failure_impact(cp) ≥ threshold
4. MAY-NOT-NEED-TEST DECISION FUNCTION

A code path may be skipped only if explicitly justified:

may_skip(cp) ⇔

    trivial_delegate(cp)
    ∨ generated_code(cp)
    ∨ framework_boilerplate(cp)
    ∨ covered_by_higher_level_test(cp)
    ∨ impossible_to_execute_in_test_env(cp)

But every skipped path must produce:

SkipRecord(cp) = {
    reason,
    risk,
    alternative_coverage,
    owner,
    confidence
}

Hidden skip is invalid:

skipped(cp) ∧ no SkipRecord(cp) ⇒ invalid
5. SCOPE / SPEC / CODE ALIGNMENT CONDITION

For each tested path:

∀ cp ∈ CP :
    if must_test(cp):
        relation(cp) must be one of:

            scope_realization
            spec_realization
            technical_contract
            safety_guard
            regression_guard
            legacy_behavior_to_preserve
            suspected_bug_to_expose
            undefined_behavior_to_report

If relation(cp) = none:

cp must be reported as:
    code_without_spec_or_scope_trace
6. TEST PURPOSE CONDITION

Every test must answer all questions:

∀ t ∈ T :

TestPurpose(t) = {
    target_code_path,
    target_behavior,
    business_claim_verified,
    technical_claim_verified,
    risk_reduced,
    failure_mode_detected,
    expected_success_condition,
    expected_failure_condition,
    oracle,
    reason_this_test_exists
}

If any field is empty:

test_is_laconic(t) = true
7. LACONIC / USELESS TEST REJECTION

A test is useless if:

useless(t) ⇔

    no_meaningful_assertion(t)
    ∨ only_asserts_not_null(t)
    ∨ only_asserts_status_code_without_body_or_state(t)
    ∨ only_checks_object_exists(t)
    ∨ does_not_execute_target_logic(t)
    ∨ does_not_fail_when_target_logic_is_broken(t)
    ∨ duplicates_other_test_without_new_failure_signal(t)
    ∨ asserts_mock_behavior_instead_of_production_behavior(t)
    ∨ verifies_implementation_detail_without_contract_reason(t)
    ∨ has_no_business_or_technical_claim(t)

Condition:

∀ t ∈ T :
    useless(t) = false
8. SUCCESS / FAILURE ORACLE CONDITION

A test is valid only if success and failure are decidable.

∀ t ∈ T :

Oracle(t) must define:

    success_condition(t)
    failure_condition(t)
    expected_output(t) OR expected_state_change(t) OR expected_exception(t)
    allowed_tolerance(t)
    forbidden_behavior(t)

Valid oracles:

    exact_expected_output
    invariant
    database_state_assertion
    emitted_event_assertion
    API_contract_assertion
    schema_assertion
    reconciliation_assertion
    property_based_assertion
    golden_dataset
    differential_comparison
    security_policy_assertion
    performance_threshold

Invalid oracle examples:

    "does not crash" only
    "returns something"
    "status code is 200" only
    "mock was called" only, unless call itself is the contract
9. FAILURE DETECTION / MUTATION CONDITION

A test must be able to fail when the protected behavior is broken.

∀ t ∈ T :

ValidFailureDetection(t) ⇔
    ∃ injected_fault f :
        break(target_behavior(t), f)
        ⇒ t fails

Fault types:

    wrong_condition
    removed_branch
    inverted_boolean
    wrong_boundary
    wrong_mapping
    missing_filter
    missing_permission_check
    wrong_error_handling
    ignored_dependency_failure
    duplicate_write
    non_idempotent_retry
    wrong_date_logic
    wrong aggregation
    wrong schema
    wrong ordering
    wrong rounding
    stale cache
    race condition

If no relevant fault would fail the test:

dead_test(t) = true
10. ASSERTION STRENGTH CONDITION

AssertionStrength(t) must be above threshold.

AssertionStrength(t) =
    evaluates_business_result
    + evaluates_technical_contract
    + evaluates_side_effect
    + evaluates_error_condition
    + evaluates_invariant
    + evaluates_state_change
    + evaluates_no_forbidden_behavior

Weak tests fail this condition.

Examples of weak tests:

    assert response is not None
    assert len(result) > 0
    assert function returns True
    assert object has attribute
    assert no exception raised

unless explicitly justified by contract.
11. SIDE EFFECT COVERAGE CONDITION

If code changes state, test must verify state.

∀ cp ∈ CP :

if has_side_effect(cp):

    ∃ t ∈ T :
        executes(t, cp)
        ∧ asserts_side_effect(t)
        ∧ asserts_no_unwanted_side_effect(t)

Side effects include:

    database write
    file write
    API call
    message published
    cache mutation
    status transition
    audit log
    permission change
    configuration change
12. ERROR HANDLING COVERAGE CONDITION

Every meaningful error branch must be tested.

∀ e ∈ ERR :

    if reachable(e) ∧ meaningful(e):
        ∃ t ∈ T :
            triggers(t, e)
            ∧ asserts_error_contract(t)
            ∧ asserts_recovery_or_stop_behavior(t)

Error contract includes:

    error type
    error message / code
    rollback behavior
    retry behavior
    logging / audit
    user-visible failure
    no partial corruption
13. IDENTITY OF TEST DOMAIN CONDITION

Tests must verify the same semantic domain as the code behavior.

∀ t ∈ T :

same_domain(t, target_code_path(t)) = true

Fake domain examples:

    testing mocked service response but not production transformation
    testing serializer but claiming business rule coverage
    testing endpoint status but not business decision
    testing fixture shape but not actual logic
14. TEST LEVEL SELECTION CONDITION

The test level must match the risk and behavior.

choose_level(cp):

    if pure deterministic logic:
        unit_test

    if component boundary or dependency contract:
        integration_or_contract_test

    if complete business flow:
        end_to_end_test

    if invariant across many inputs:
        property_based_test

    if previously broken behavior:
        regression_test

    if schema / API stability:
        contract_test

    if permission / security behavior:
        security_test

    if retry / failure recovery:
        fault_injection_test

Invalid level:

    using E2E test for trivial pure function
    using unit test for behavior that depends on integration contract
    using mock-only test for external contract
15. REGRESSION TEST CONDITION

A regression test is required when:

regression_required(cp) ⇔

    historical_bug(cp)
    ∨ critical_business_rule(cp)
    ∨ stable_external_contract(cp)
    ∨ high_cost_of_failure(cp)
    ∨ previously_changed_behavior(cp)
    ∨ fragile_logic(cp)

Regression test must state:

RegressionPurpose(t) = {
    behavior_to_preserve,
    bug_or_risk_prevented,
    exact failure it would catch,
    why this behavior must not change
}

Do not create regression tests for bugs unless the bug is intentionally preserved.
16. EXISTING CODE BEHAVIOR CLASSIFICATION

Existing code behavior must not be blindly protected.

For each observed behavior ob:

classify(ob) ∈ {
    expected_by_scope,
    expected_by_spec,
    technical_contract,
    legacy_to_preserve,
    legacy_to_replace,
    suspected_bug,
    undefined,
    out_of_scope
}

Rules:

if ob = suspected_bug:
    write exposing test or report gap
    do not protect as regression

if ob = undefined:
    report DECISION_REQUIRED

if ob = out_of_scope:
    do not test unless safety guard is needed
17. TEST DATA ADEQUACY CONDITION

A test must use data capable of triggering the behavior.

∀ t ∈ T :

TestData(t) must satisfy:
    reaches_target_path(t)
    triggers_intended_condition(t)
    includes_boundary_values_if_relevant(t)
    includes invalid values if relevant
    includes realistic business shape if business behavior
    avoids overfitted artificial data unless justified

If test data cannot make the branch observable:

test_is_non_exercising(t) = true
18. MOCK / FIXTURE VALIDITY CONDITION

Mocks are valid only if they preserve the contract.

∀ mock m used by t:

valid_mock(m) ⇔
    represents_real_dependency_contract(m)
    ∧ exposes_success_and_failure_modes(m)
    ∧ does_not_hide_target_logic(m)

Invalid mocks:

    mock returns desired answer without exercising code
    mock replaces the behavior being tested
    mock makes impossible production state
    mock hides integration contract
19. IDEMPOTENCY / REPEATABILITY CONDITION

Every test must be deterministic and repeatable.

∀ t ∈ T :

repeatable(t) ⇔
    same input + same controlled environment ⇒ same result

For stateful tests:

    setup_defined(t)
    cleanup_defined(t)
    isolation_defined(t)
    no_order_dependency(t)

Idempotency:

    run(t)
    run(t)
    produces same final observable state

or:

    cleanup restores state between runs
20. OBSERVABILITY CONDITION

A test must observe the right outcome.

∀ t ∈ T :

Observed(t) must include at least one of:

    return value
    thrown error
    persisted state
    emitted event
    external call contract
    audit log
    metric
    permission outcome
    UI-visible result
    file/object content

If code behavior happens but test observes unrelated signal:

invalid_observation(t) = true
21. COVERAGE QUALITY CONDITION

Coverage is valid only as multi-dimensional coverage.

CoverageQuality =
    code_path_coverage
    ∧ branch_coverage
    ∧ behavior_coverage
    ∧ scope_coverage
    ∧ spec_coverage
    ∧ risk_coverage
    ∧ invariant_coverage
    ∧ error_branch_coverage
    ∧ side_effect_coverage
    ∧ regression_coverage

Line coverage alone is insufficient.

If:

line_coverage_high
∧ behavior_coverage_low

then:

coverage_is_fake = true
22. OVERLAP / DUPLICATION CONDITION

Multiple tests may cover the same code path only if they provide distinct value.

valid_overlap(t1, t2) ⇔

    different_failure_mode
    ∨ different_level
    ∨ different_oracle
    ∨ different_risk
    ∨ different_input_class
    ∨ regression_vs_property_vs_contract distinction

Invalid duplication:

    same path
    same data
    same assertion
    same oracle
    same purpose
23. TEST GAP DETECTION CONDITION

For the codebase:

RequiredTestSurface =
    must_test(CP)
    ∪ critical(RISK)
    ∪ INV
    ∪ public_interfaces
    ∪ state_mutations
    ∪ error_contracts
    ∪ external_contracts
    ∪ regression_required_paths

CoveredSurface =
    union(target(t) for t ∈ T)

TestGap = RequiredTestSurface - CoveredSurface

Condition:

TestGap = ∅
OR
∀ gap ∈ TestGap :
    documented_gap(gap)
24. UNTESTABLE / OMITTED AREA CONDITION

If something cannot be tested, it must be explicit.

For each gap:

GapRecord(gap) = {
    code_path_or_behavior,
    why_not_tested,
    risk,
    impact,
    missing_environment_or_data,
    alternative_evidence,
    mitigation,
    owner,
    decision_required,
    confidence
}

Hidden gaps invalidate readiness.
25. PLANNING CONDITION

For planned code, tests must be designed before implementation.

For every planned implementation unit pi:

TestObligation(pi) = {
    code path to be created,
    expected behavior,
    failure modes,
    test level,
    oracle,
    test data,
    mock requirements,
    regression impact,
    acceptance criteria
}

No implementation plan is complete without TestObligation(pi).
26. FINAL VALIDITY CONDITION

GoodCodeGroundedTestSuite ⇔

∀ cp ∈ CP :
    must_test(cp) ⇒ ∃ t :
        executes(t, cp)
        ∧ asserts_expected_result(t, cp)
        ∧ has_valid_oracle(t)
        ∧ detects_relevant_fault(t)

∧ ∀ t ∈ T :
    calls_or_executes_real_code(t)
    ∧ has_purpose(t)
    ∧ has_trace(t)
    ∧ has_strong_assertion(t)
    ∧ same_domain(t, target(t))
    ∧ not_useless(t)
    ∧ repeatable(t)

∧ all critical risks are tested or explicitly accepted

∧ all side effects are verified

∧ all meaningful error branches are tested

∧ existing behavior is classified before regression protection

∧ coverage is behavior/risk/path coverage, not line coverage only

∧ TestGap = ∅ or every gap has GapRecord

∧ no fake coverage exists
Agentowi dałbym to jako twarde zadanie
TASK:
Generate a real executable test suite from code, Scope and SPEC.

You must not produce only scenarios.
You must inspect code and derive executable paths.
You must decide what must be tested and why.
You must generate actual tests that call production code.
You must reject weak/laconic/useless tests.
You must report every required path that is untested.

PROCESS:

1. Parse the codebase.
2. Enumerate code units.
3. Build CodeProfile for every unit.
4. Enumerate executable paths and branches.
5. Map each path to Scope/SPEC/technical contract/risk/legacy behavior.
6. Classify which paths must be tested and which may be skipped.
7. For every must-test path, create TestObligation.
8. Select proper test level: unit/integration/contract/E2E/property/regression/fault-injection.
9. Define oracle, input data, mocks, setup, cleanup, success condition and failure condition.
10. Generate actual executable test files.
11. Verify every test:
    - calls real production code
    - reaches intended path
    - has meaningful assertions
    - fails under relevant injected fault
    - is deterministic
12. Reject useless tests.
13. Report gaps and untestable areas.
14. Output final test suite + matrices.
Minimalny format każdego testu
TestSpec = {
    test_id,
    test_name,
    target_file,
    target_function_or_path,
    code_path_condition,
    source_scope_or_spec,
    behavior_verified,
    business_claim_verified,
    technical_claim_verified,
    risk_reduced,
    test_level,
    setup,
    input_data,
    mocks_or_fixtures,
    execution_step,
    expected_success,
    expected_failure_signal,
    assertions,
    oracle_type,
    side_effects_checked,
    cleanup,
    idempotency_strategy,
    mutation_that_should_break_this_test,
    why_this_test_is_not_laconic,
    regression_relevance
}
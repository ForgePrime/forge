"""feature/FULL contract — high-ceremony path.

Per IMPLEMENTATION_TRACKER + ADR-002 ceremony tier mapping:
FULL ceremony adds requirements (vs STANDARD):
- failure_scenarios required (not optional).
- Stricter min_length on reasoning (200 chars).
- Cross-reference between assumptions + impact_analysis required.
"""

from __future__ import annotations

from app.validation.contract_schema import ContractSchema, FieldConstraint


FEATURE_FULL_CONTRACT = ContractSchema(
    task_type="feature",
    ceremony_level="FULL",
    schema_version=1,
    fields=[
        FieldConstraint(
            name="reasoning",
            type="str",
            required=True,
            min_length=200,
            must_reference_file=True,
            must_contain_keyword=["because", "therefore", "since"],  # forces explicit causal claim
            reject_patterns=[
                "verified manually",
                "should work",
                "looks fine",
                "TODO",
                "FIXME",
            ],
            prompt_section_name="REASONING",
            prompt_intro=(
                "Explain step-by-step what you changed and WHY. Reference at "
                "least one file path AND state the causal link explicitly "
                "(use 'because' / 'therefore' / 'since')."
            ),
            prompt_priority=95,
            structural_category="ambiguity_state",
        ),
        FieldConstraint(
            name="changes",
            type="list[dict]",
            required=True,
            prompt_section_name="CHANGES",
            prompt_intro=(
                "Concrete changes as a JSON array of {path, action, before, after}. "
                "FULL ceremony: include `motivation` per change citing a "
                "specific requirement_ref."
            ),
            prompt_priority=85,
            structural_category="free_form",
        ),
        FieldConstraint(
            name="ac_evidence",
            type="list[dict]",
            required=True,
            min_length=80,  # stricter than STANDARD
            prompt_section_name="ACCEPTANCE_CRITERIA_EVIDENCE",
            prompt_intro=(
                "Per AC: {ac_index, evidence, verdict, reference}. Evidence "
                "must include the test command output OR an explicit file "
                "citation with line range."
            ),
            prompt_priority=80,
            structural_category="evidence_refs",
        ),
        FieldConstraint(
            name="assumptions",
            type="list[str]",
            required=True,
            min_length=20,  # at least one substantive assumption disclosure per call
            prompt_section_name="ASSUMPTIONS",
            prompt_intro=(
                "Every non-trivial claim tagged [CONFIRMED] / [ASSUMED] / "
                "[UNKNOWN] per CONTRACT §B.2. FULL ceremony: minimum 1 "
                "tagged assumption per change."
            ),
            prompt_priority=70,
            structural_category="ambiguity_state",
        ),
        FieldConstraint(
            name="impact_analysis",
            type="str",
            required=True,
            min_length=80,  # stricter than STANDARD
            must_reference_file=True,
            prompt_section_name="IMPACT_ANALYSIS",
            prompt_intro=(
                "List ALL files / functions affected (transitive + side "
                "effects). FULL ceremony: must include at least one file "
                "path; must cite which downstream tests verify the change."
            ),
            prompt_priority=65,
            structural_category="dependency_relations",
        ),
        FieldConstraint(
            name="failure_scenarios",
            type="list[str]",
            required=True,  # mandatory at FULL ceremony (vs optional at STANDARD)
            prompt_section_name="FAILURE_SCENARIOS",
            prompt_intro=(
                "Minimum 3 failure scenarios per CONTRACT §B.5 + ASPS Clause 11: "
                "(1) null/empty input, (2) timeout / dependency failure, "
                "(3) repeated execution / idempotency. Each with explicit "
                "handling described."
            ),
            prompt_priority=60,
            structural_category="test_obligations",
        ),
        FieldConstraint(
            name="alternatives_considered",
            type="list[dict]",
            required=True,  # FULL ceremony — F.11 candidate evaluation pre-cursor
            prompt_section_name="ALTERNATIVES_CONSIDERED",
            prompt_intro=(
                "Minimum 2 alternatives (FC §16). Each: {description, "
                "rejected_because}. FULL ceremony enables P21 root-cause + "
                "F.11 candidate-evaluation downstream gates."
            ),
            prompt_priority=55,
            structural_category="hard_constraints",
        ),
    ],
)

"""feature/STANDARD contract — most common path.

Mirrors existing output_contracts row for (type=feature, ceremony=STANDARD)
per IMPLEMENTATION_TRACKER:
- reasoning min 100 chars + must reference file
- ac_evidence min 50 chars + verdict
- assumptions explicit
- impact_analysis explicit
"""

from __future__ import annotations

from app.validation.contract_schema import ContractSchema, FieldConstraint


FEATURE_STANDARD_CONTRACT = ContractSchema(
    task_type="feature",
    ceremony_level="STANDARD",
    schema_version=1,
    fields=[
        FieldConstraint(
            name="reasoning",
            type="str",
            required=True,
            min_length=100,
            must_reference_file=True,
            reject_patterns=[
                "verified manually",
                "should work",
                "looks fine",
            ],
            prompt_section_name="REASONING",
            prompt_intro=(
                "Explain step-by-step what you changed and WHY. Reference at "
                "least one file path. Avoid placeholder phrases."
            ),
            prompt_priority=90,
            structural_category="ambiguity_state",
        ),
        FieldConstraint(
            name="changes",
            type="list[dict]",
            required=True,
            prompt_section_name="CHANGES",
            prompt_intro=(
                "Concrete changes as a JSON array of {path, action, before, after}."
            ),
            prompt_priority=80,
            structural_category="free_form",
        ),
        FieldConstraint(
            name="ac_evidence",
            type="list[dict]",
            required=True,
            min_length=50,  # per-AC string min applied via validator on .evidence
            prompt_section_name="ACCEPTANCE_CRITERIA_EVIDENCE",
            prompt_intro=(
                "For each acceptance criterion: produce {ac_index, evidence, "
                "verdict, reference}. Evidence must include a file path or "
                "test command output."
            ),
            prompt_priority=70,
            structural_category="evidence_refs",
        ),
        FieldConstraint(
            name="assumptions",
            type="list[str]",
            required=True,
            prompt_section_name="ASSUMPTIONS",
            prompt_intro=(
                "List every assumption made. Tag each per CONTRACT §B.2: "
                "[CONFIRMED] / [ASSUMED] / [UNKNOWN]."
            ),
            prompt_priority=60,
            structural_category="ambiguity_state",
        ),
        FieldConstraint(
            name="impact_analysis",
            type="str",
            required=True,
            min_length=30,
            prompt_section_name="IMPACT_ANALYSIS",
            prompt_intro=(
                "Identify which other files / functions / behaviours are "
                "affected by this change. Cite at least one impacted area."
            ),
            prompt_priority=50,
            structural_category="dependency_relations",
        ),
        FieldConstraint(
            name="failure_scenarios",
            type="list[str]",
            required=False,
            prompt_section_name="FAILURE_SCENARIOS",
            prompt_intro=(
                "List at least 3 failure scenarios (e.g. data empty / timeout "
                "/ concurrent access) and how the change handles each."
            ),
            prompt_priority=40,
            structural_category="test_obligations",
        ),
    ],
)

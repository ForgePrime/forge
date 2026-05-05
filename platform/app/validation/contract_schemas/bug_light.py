"""bug/LIGHT contract — minimal-ceremony bug fix path.

Per IMPLEMENTATION_TRACKER existing output_contracts row. Bugs at LIGHT
ceremony: small reproducible-failure fix; less surrounding ceremony
required than feature.
"""

from __future__ import annotations

from app.validation.contract_schema import ContractSchema, FieldConstraint


BUG_LIGHT_CONTRACT = ContractSchema(
    task_type="bug",
    ceremony_level="LIGHT",
    schema_version=1,
    fields=[
        FieldConstraint(
            name="reasoning",
            type="str",
            required=True,
            min_length=80,
            must_reference_file=True,
            must_contain_keyword=["root_cause", "fix", "before", "after"],
            prompt_section_name="REASONING",
            prompt_intro=(
                "Identify the root cause (cite file + line) and explain the fix. "
                "State what behaviour changes between before and after."
            ),
            prompt_priority=90,
            structural_category="ambiguity_state",
        ),
        FieldConstraint(
            name="changes",
            type="list[dict]",
            required=True,
            prompt_section_name="CHANGES",
            prompt_intro="The fix as a JSON array: {path, action='edit', before, after}.",
            prompt_priority=80,
            structural_category="free_form",
        ),
        FieldConstraint(
            name="regression_test",
            type="dict",
            required=True,
            prompt_section_name="REGRESSION_TEST",
            prompt_intro=(
                "Add a test that fails on old code AND passes on new code. "
                "Format: {path, test_name, command_to_run, expected_output_excerpt}. "
                "Verifies the bug stays fixed."
            ),
            prompt_priority=70,
            structural_category="test_obligations",
        ),
        FieldConstraint(
            name="impact_analysis",
            type="str",
            required=False,  # LIGHT ceremony — bugs are typically local
            min_length=20,
            prompt_section_name="IMPACT_ANALYSIS",
            prompt_intro=(
                "Brief: any unintended side-effect of the fix? Cite any file "
                "that imports or calls the changed code."
            ),
            prompt_priority=50,
            structural_category="dependency_relations",
        ),
    ],
)

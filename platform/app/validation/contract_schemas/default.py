"""Default contract — minimal schema for any unrecognised task type.

Acts as a fallback when (task_type, ceremony) has no specific contract.
Per existing output_contracts.required JSONB shape (4 rows seeded).
"""

from __future__ import annotations

from app.validation.contract_schema import ContractSchema, FieldConstraint


DEFAULT_CONTRACT = ContractSchema(
    task_type="chore",
    ceremony_level="STANDARD",
    schema_version=1,
    fields=[
        FieldConstraint(
            name="reasoning",
            type="str",
            required=True,
            min_length=50,
            prompt_section_name="REASONING",
            prompt_intro="Provide a step-by-step reasoning for the change.",
            prompt_priority=80,
            structural_category="ambiguity_state",
        ),
        FieldConstraint(
            name="changes",
            type="list[dict]",
            required=True,
            prompt_section_name="CHANGES",
            prompt_intro=(
                "List concrete changes as a JSON array. Each entry must have "
                "{path, action, before, after}."
            ),
            prompt_priority=70,
            structural_category="free_form",
        ),
    ],
)

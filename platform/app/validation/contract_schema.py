"""ContractSchema — Phase E Stage E.1.

Per FORMAL_PROPERTIES_v2 P12 (self-adjointness):
    Same ContractSchema instance produces both render_prompt_fragment()
    AND validator_rules(). Mutating any field updates both lockstep.

Per ADR-027 (PROPOSED, awaiting distinct-actor ratification): Hybrid
storage — Pydantic model is canonical; output_contracts.spec_jsonb is
auto-derived shadow for queryability (drift test catches divergence).

Risk disclosure (CONTRACT §A.6): ADR-027 is PROPOSED, not RATIFIED.
Implementation here bets on ratification roughly as-drafted. If ADR-027
is REJECTED or amended, this module needs to follow. Rework cost is
bounded (~0.3-0.5d for shape changes, ~1d for fundamental redesign).

Inputs that drive the schema content (not in this commit):
- Concrete contract definitions live in `app/validation/contract_schemas/`
  per (task_type, ceremony_level) combination. This module provides the
  type machinery; per-contract content is data, not code.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# Allowed string-literal sets per ADR-027.
TaskType = Literal["feature", "bug", "develop", "chore", "investigation"]
CeremonyLevel = Literal["LIGHT", "STANDARD", "FULL", "CRITICAL"]
FieldType = Literal["str", "list[dict]", "list[str]", "dict", "bool", "int"]
StructuralCategory = Literal[
    "requirements",
    "evidence_refs",
    "ambiguity_state",
    "test_obligations",
    "dependency_relations",
    "hard_constraints",
    "free_form",
]


class FieldConstraint(BaseModel):
    """Per-field rules. Maps to validator + prompt + F.10 category.

    Single source for:
    - L3.1 PromptAssembler render: uses prompt_section_name +
      prompt_intro + prompt_priority + the field's expected shape.
    - ContractValidatorRuleAdapter: uses min_length, must_reference_file,
      must_contain_keyword, reject_patterns to validate the LLM output.
    - F.10 StructuredTransferGate: uses structural_category to decide
      whether the field counts toward the 6 ECITP C11 categories.

    Frozen behaviour: pydantic models are mutable by default; we don't
    freeze here because the registry constructs them once at import time
    and never mutates. If runtime mutation becomes a concern, switch to
    frozen=True via model_config.
    """

    name: str
    type: FieldType
    required: bool = True

    # --- Validator-side constraints (consumed by ContractValidator-style rules) ---
    min_length: int | None = None
    must_reference_file: bool = False
    must_contain_keyword: list[str] = Field(default_factory=list)
    reject_patterns: list[str] = Field(default_factory=list)

    # --- Prompt-rendering hints (consumed by L3.1 PromptAssembler when wired) ---
    prompt_section_name: str
    prompt_intro: str
    prompt_priority: int = 50  # priority within ContextBudget bucket

    # --- F.10 structural category (consumed by StructuredTransferGate) ---
    structural_category: StructuralCategory = "free_form"


class ContractSchema(BaseModel):
    """Typed spec for a (task_type, ceremony_level) combination.

    P12 self-adjointness: render_prompt_fragment() and validator_rules()
    are PURE derivations from `self.fields`. Caller cannot mutate the
    schema between the two calls and observe inconsistent output.
    """

    task_type: TaskType
    ceremony_level: CeremonyLevel
    fields: list[FieldConstraint]
    schema_version: int = 1  # bump on breaking change; ADR-XXX governs

    # ------------------------------------------------------------------
    # Pure derivations (P12 self-adjointness)
    # ------------------------------------------------------------------

    def render_prompt_fragment(self) -> str:
        """Pure: ordered prompt section assembled from fields.

        Order: descending prompt_priority, then ascending name (stable
        tie-break). Output is a deterministic, indented Markdown-style
        block; identical input -> identical bytes.

        Per FORMAL P6: no clock/random/network reads.
        """
        ordered = sorted(
            self.fields,
            key=lambda f: (-f.prompt_priority, f.name),
        )
        sections: list[str] = []
        sections.append(
            f"# Output Contract — {self.task_type}/{self.ceremony_level} "
            f"(schema v{self.schema_version})"
        )
        for f in ordered:
            req_marker = "REQUIRED" if f.required else "OPTIONAL"
            sections.append(
                f"\n## {f.prompt_section_name} ({req_marker}, type={f.type})\n"
                f"{f.prompt_intro}"
            )
            constraints: list[str] = []
            if f.min_length is not None:
                constraints.append(f"- minimum length: {f.min_length} chars")
            if f.must_reference_file:
                constraints.append("- must reference at least one file path")
            if f.must_contain_keyword:
                constraints.append(
                    f"- must contain at least one of: "
                    f"{', '.join(repr(k) for k in f.must_contain_keyword)}"
                )
            if f.reject_patterns:
                constraints.append(
                    f"- must NOT contain: "
                    f"{', '.join(repr(p) for p in f.reject_patterns)}"
                )
            if constraints:
                sections.append("\n**Constraints:**\n" + "\n".join(constraints))
        return "\n".join(sections)

    def validator_rules(self) -> list[FieldConstraint]:
        """Pure: returns fields directly. Validators consume FieldConstraint.

        Returning the same list reference would be unsafe (caller could
        mutate); return a fresh list to make this a value contract.
        """
        return list(self.fields)

    def required_context_categories(self) -> set[StructuralCategory]:
        """For F.10 StructuredTransferGate: which 6-cat categories this task needs.

        Excludes 'free_form' (the explicit opt-out marker). Categories
        a task DOES need are exactly the structural_category values
        present on its fields.
        """
        return {f.structural_category for f in self.fields if f.structural_category != "free_form"}

    def field_by_name(self, name: str) -> FieldConstraint | None:
        """Convenience lookup; returns None on missing rather than raising."""
        for f in self.fields:
            if f.name == name:
                return f
        return None


# ----------------------------------------------------------------------
# Registry — concrete contracts live in app/validation/contract_schemas/
# ----------------------------------------------------------------------

# Module-level registry: (task_type, ceremony_level) -> ContractSchema.
# Populated at import time by `contract_schemas/__init__.py`. Empty at
# this module's level — concrete schemas are data, in a separate package.
CONTRACT_REGISTRY: dict[tuple[str, str], ContractSchema] = {}


def register(schema: ContractSchema) -> None:
    """Register a ContractSchema. Duplicate (task_type, ceremony) is an error."""
    key = (schema.task_type, schema.ceremony_level)
    if key in CONTRACT_REGISTRY:
        raise ValueError(
            f"duplicate ContractSchema registration for "
            f"(task_type={schema.task_type!r}, ceremony={schema.ceremony_level!r})"
        )
    CONTRACT_REGISTRY[key] = schema


def lookup(task_type: str, ceremony_level: str) -> ContractSchema | None:
    """Look up a registered schema; None if not present."""
    return CONTRACT_REGISTRY.get((task_type, ceremony_level))

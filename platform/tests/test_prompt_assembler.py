"""Tests for PromptAssembler — Phase L3 Stage L3.1.

Critical properties:
- Determinism (P6): same inputs -> byte-identical AssembledPrompt.
- Self-adjointness via E.1 (P12): prompt fragment derived from
  ContractSchema.render_prompt_fragment() — reused without modification.
- 5 mandatory CONTRACT §B blocks present.
- Replay-friendly assembly_checksum: sha256 stable across runs.
"""

from __future__ import annotations

from app.evidence.causal_graph import EdgeView, InMemoryEdgeSource, Node
from app.evidence.context_projector import project as project_context
from app.llm.context_budget import Bucket, ContextItem
from app.llm.model_router import ModelFamily
from app.llm.prompt_assembler import AssembledPrompt, assemble
from app.validation.contract_schemas import (
    BUG_LIGHT_CONTRACT,
    FEATURE_FULL_CONTRACT,
    FEATURE_STANDARD_CONTRACT,
)


def _empty_projection():
    src = InMemoryEdgeSource()
    return project_context(graph_source=src, task_node=Node("task", 1))


def _projection_with_2_items():
    src = InMemoryEdgeSource([
        EdgeView(src_type="dec", src_id=1, dst_type="task", dst_id=2, relation="decision"),
        EdgeView(src_type="kn", src_id=3, dst_type="task", dst_id=2, relation="evidences"),
    ])
    return project_context(graph_source=src, task_node=Node("task", 2))


# --- Basic assembly --------------------------------------------------------


def test_assemble_returns_assembled_prompt():
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="Implement the login button",
        model_family=ModelFamily.SONNET,
    )
    assert isinstance(result, AssembledPrompt)
    assert result.model_family == "sonnet"
    assert result.schema_version == FEATURE_STANDARD_CONTRACT.schema_version


def test_user_prompt_contains_user_intent():
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="Add a settings panel to the dashboard",
        model_family="sonnet",
    )
    assert "Add a settings panel to the dashboard" in result.user_prompt


def test_system_prompt_includes_contract_fragment():
    """System prompt embeds the ContractSchema rendered fragment (P12)."""
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    expected_fragment = FEATURE_STANDARD_CONTRACT.render_prompt_fragment()
    # The full fragment should appear verbatim in the system prompt
    # (subset check; the fragment may share the system_prompt with the
    # CONTRACT reminder).
    for line in expected_fragment.split("\n"):
        if line.strip():  # skip blank lines (whitespace differences OK)
            assert line in result.system_prompt


def test_system_prompt_contains_contract_reminder():
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    assert "Operational Contract" in result.system_prompt
    assert "[CONFIRMED]" in result.system_prompt
    assert "[ASSUMED]" in result.system_prompt
    assert "[UNKNOWN]" in result.system_prompt


def test_system_prompt_includes_b5_pre_completion_guidance():
    """CONTRACT §B.5 minimum-3-failure-scenarios baked into reminder."""
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    assert "FAILURE SCENARIOS" in result.system_prompt
    assert "minimum 3" in result.system_prompt or "min 3" in result.system_prompt or "minimum 3" in result.system_prompt.lower()


# --- Projection embedding --------------------------------------------------


def test_projection_items_appear_in_user_prompt():
    projection = _projection_with_2_items()
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=projection,
        user_intent="Update task 2",
        model_family="sonnet",
    )
    # Both projection items should appear (default classifier renders
    # synthetic content — see ContextProjector.StaticRelationClassifier)
    assert "decision" in result.user_prompt or "evidences" in result.user_prompt


def test_empty_projection_omits_context_section():
    """No items -> no '# Context' header."""
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    # Empty projection means no Context block
    # (Implementation may still include the header if extra_context_items
    # passed; but with both empty, the section is absent.)
    assert "# Context (causal-graph projection)" not in result.user_prompt


def test_extra_context_items_appended():
    extra = (
        ContextItem(
            content="Extra hint A",
            bucket=Bucket.MUST,
            priority_within_bucket=10,
            source_ref="ref-extra-a",
            token_count=5,
        ),
    )
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
        extra_context_items=extra,
    )
    assert "Extra hint A" in result.user_prompt
    assert "# Additional context" in result.user_prompt


# --- Determinism (P6) ------------------------------------------------------


def test_same_inputs_byte_identical_output():
    args = dict(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="Implement feature X",
        model_family="sonnet",
    )
    r1 = assemble(**args)
    r2 = assemble(**args)
    r3 = assemble(**args)
    assert r1 == r2 == r3
    assert r1.assembly_checksum == r2.assembly_checksum == r3.assembly_checksum


def test_assembly_checksum_changes_with_user_intent():
    """Different user intent -> different checksum."""
    args1 = dict(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="Task A",
        model_family="sonnet",
    )
    args2 = {**args1, "user_intent": "Task B"}
    r1 = assemble(**args1)
    r2 = assemble(**args2)
    assert r1.assembly_checksum != r2.assembly_checksum


def test_assembly_checksum_changes_with_contract_schema():
    args1 = dict(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    args2 = {**args1, "contract_schema": FEATURE_FULL_CONTRACT}
    r1 = assemble(**args1)
    r2 = assemble(**args2)
    assert r1.assembly_checksum != r2.assembly_checksum


def test_assembly_checksum_changes_with_model_family():
    args1 = dict(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    args2 = {**args1, "model_family": "opus"}
    r1 = assemble(**args1)
    r2 = assemble(**args2)
    assert r1.assembly_checksum != r2.assembly_checksum


def test_assembly_checksum_stable_across_projection_recreation():
    """Recreating identical projection -> same checksum."""
    proj1 = _projection_with_2_items()
    proj2 = _projection_with_2_items()
    r1 = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=proj1, user_intent="X", model_family="sonnet",
    )
    r2 = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=proj2, user_intent="X", model_family="sonnet",
    )
    assert r1.assembly_checksum == r2.assembly_checksum


# --- ModelFamily enum vs string acceptance --------------------------------


def test_model_family_enum_and_string_produce_same_checksum():
    args1 = dict(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family=ModelFamily.SONNET,
    )
    args2 = {**args1, "model_family": "sonnet"}
    r1 = assemble(**args1)
    r2 = assemble(**args2)
    assert r1.assembly_checksum == r2.assembly_checksum
    assert r1.model_family == r2.model_family == "sonnet"


# --- Per-contract assemblies --------------------------------------------


def test_assemble_for_feature_full_includes_alternatives_section():
    result = assemble(
        contract_schema=FEATURE_FULL_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="opus",
    )
    # FEATURE_FULL has alternatives_considered field; render should mention it
    assert "ALTERNATIVES_CONSIDERED" in result.system_prompt


def test_assemble_for_bug_light_includes_regression_test_section():
    result = assemble(
        contract_schema=BUG_LIGHT_CONTRACT,
        projection=_empty_projection(),
        user_intent="Fix login bug",
        model_family="sonnet",
    )
    assert "REGRESSION_TEST" in result.system_prompt


def test_total_chars_diagnostic():
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    assert result.total_chars == len(result.system_prompt) + len(result.user_prompt)
    assert result.total_chars > 100  # substantive prompt


# --- Frozen dataclass guarantee -----------------------------------------


def test_assembled_prompt_is_frozen():
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    try:
        result.user_prompt = "MUTATED"  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("AssembledPrompt should be frozen")


def test_stop_sequences_non_empty():
    result = assemble(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=_empty_projection(),
        user_intent="X",
        model_family="sonnet",
    )
    assert len(result.stop_sequences) >= 1

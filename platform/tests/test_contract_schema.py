"""Tests for ContractSchema (E.1) — Phase E Stage E.1.

Critical property: P12 self-adjointness.
- render_prompt_fragment() and validator_rules() come from the same
  `self.fields` source.
- Mutating any FieldConstraint changes both outputs lockstep.
- Identical schema input -> identical render bytes (P6 determinism).

Plus registry tests for the 4 seeded contracts (default, feature/STANDARD,
feature/FULL, bug/LIGHT).
"""

from __future__ import annotations

from app.validation.contract_schema import (
    CONTRACT_REGISTRY,
    ContractSchema,
    FieldConstraint,
    lookup,
    register,
)
from app.validation.contract_schemas import (
    BUG_LIGHT_CONTRACT,
    DEFAULT_CONTRACT,
    FEATURE_FULL_CONTRACT,
    FEATURE_STANDARD_CONTRACT,
)


# --- Building blocks: FieldConstraint construction -----------------------


def _minimal_field(name: str = "f1", priority: int = 50) -> FieldConstraint:
    return FieldConstraint(
        name=name,
        type="str",
        prompt_section_name=f"SEC_{name.upper()}",
        prompt_intro=f"Provide content for {name}.",
        prompt_priority=priority,
    )


def test_field_constraint_builds():
    f = _minimal_field()
    assert f.name == "f1"
    assert f.required is True  # default
    assert f.structural_category == "free_form"  # default


def test_field_constraint_validator_constraints_default_empty():
    f = _minimal_field()
    assert f.min_length is None
    assert f.must_reference_file is False
    assert f.must_contain_keyword == []
    assert f.reject_patterns == []


# --- Self-adjointness (P12) ----------------------------------------------


def test_render_and_validator_share_source():
    """The two derivations consume the same self.fields list."""
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a"), _minimal_field("b")],
    )
    # validator_rules returns the same fields
    rules = schema.validator_rules()
    assert {f.name for f in rules} == {"a", "b"}
    # render_prompt_fragment mentions both section names
    prompt = schema.render_prompt_fragment()
    assert "SEC_A" in prompt
    assert "SEC_B" in prompt


def test_mutation_of_fields_changes_both_outputs():
    """Adding a field changes both render() and validator_rules() (P12)."""
    schema_v1 = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a")],
    )
    schema_v2 = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a"), _minimal_field("b")],
    )
    assert len(schema_v1.validator_rules()) == 1
    assert len(schema_v2.validator_rules()) == 2
    assert "SEC_B" not in schema_v1.render_prompt_fragment()
    assert "SEC_B" in schema_v2.render_prompt_fragment()


def test_validator_rules_returns_fresh_list_not_internal_reference():
    """Caller should not be able to mutate self.fields by mutating the returned list."""
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a")],
    )
    rules = schema.validator_rules()
    rules.append(_minimal_field("b"))
    # Original self.fields is unchanged
    assert len(schema.fields) == 1


# --- Determinism (P6) ----------------------------------------------------


def test_render_is_deterministic():
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a"), _minimal_field("b")],
    )
    r1 = schema.render_prompt_fragment()
    r2 = schema.render_prompt_fragment()
    r3 = schema.render_prompt_fragment()
    assert r1 == r2 == r3


def test_render_orders_by_priority_desc_then_name():
    """Stable ordering: higher priority first, then ascending name on ties."""
    fields = [
        _minimal_field("z", priority=10),
        _minimal_field("a", priority=80),
        _minimal_field("m", priority=80),  # tied with 'a' on priority
        _minimal_field("b", priority=50),
    ]
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=fields,
    )
    rendered = schema.render_prompt_fragment()
    # 'SEC_A' (priority 80) comes before 'SEC_M' (also 80, but later alphabetically)
    a_pos = rendered.index("SEC_A")
    m_pos = rendered.index("SEC_M")
    b_pos = rendered.index("SEC_B")
    z_pos = rendered.index("SEC_Z")
    assert a_pos < m_pos < b_pos < z_pos


def test_render_includes_constraints_when_present():
    field = FieldConstraint(
        name="f",
        type="str",
        min_length=42,
        must_reference_file=True,
        must_contain_keyword=["because"],
        reject_patterns=["TODO"],
        prompt_section_name="SEC_F",
        prompt_intro="x",
        prompt_priority=50,
    )
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[field],
    )
    rendered = schema.render_prompt_fragment()
    assert "minimum length: 42" in rendered
    assert "must reference at least one file" in rendered
    assert "because" in rendered
    assert "TODO" in rendered


def test_render_omits_constraints_when_empty():
    """No 'Constraints:' header when no constraints are set."""
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a")],
    )
    rendered = schema.render_prompt_fragment()
    # _minimal_field has no constraints set
    assert "**Constraints:**" not in rendered


# --- required_context_categories ----------------------------------------


def test_required_context_categories_excludes_free_form():
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[
            FieldConstraint(
                name="a", type="str",
                prompt_section_name="A", prompt_intro="x", prompt_priority=50,
                structural_category="evidence_refs",
            ),
            FieldConstraint(
                name="b", type="str",
                prompt_section_name="B", prompt_intro="x", prompt_priority=50,
                structural_category="free_form",
            ),
        ],
    )
    cats = schema.required_context_categories()
    assert "evidence_refs" in cats
    assert "free_form" not in cats


def test_required_context_categories_dedupes():
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[
            FieldConstraint(
                name="a", type="str",
                prompt_section_name="A", prompt_intro="x", prompt_priority=50,
                structural_category="evidence_refs",
            ),
            FieldConstraint(
                name="b", type="str",
                prompt_section_name="B", prompt_intro="x", prompt_priority=50,
                structural_category="evidence_refs",  # duplicate
            ),
        ],
    )
    cats = schema.required_context_categories()
    assert cats == {"evidence_refs"}


# --- field_by_name -------------------------------------------------------


def test_field_by_name_finds_existing():
    f = _minimal_field("foo")
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[f],
    )
    found = schema.field_by_name("foo")
    assert found is not None
    assert found.name == "foo"


def test_field_by_name_returns_none_for_missing():
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field("a")],
    )
    assert schema.field_by_name("missing") is None


# --- Registry ------------------------------------------------------------


def test_4_seeded_contracts_registered():
    """All 4 seeded contracts are in CONTRACT_REGISTRY."""
    keys = set(CONTRACT_REGISTRY.keys())
    assert ("chore", "STANDARD") in keys  # default
    assert ("feature", "STANDARD") in keys
    assert ("feature", "FULL") in keys
    assert ("bug", "LIGHT") in keys


def test_lookup_returns_correct_schema():
    schema = lookup("feature", "STANDARD")
    assert schema is not None
    assert schema.task_type == "feature"
    assert schema.ceremony_level == "STANDARD"


def test_lookup_returns_none_for_unknown():
    schema = lookup("nonexistent_type", "STANDARD")
    assert schema is None


def test_register_rejects_duplicate():
    """Re-registering same (task_type, ceremony) raises ValueError."""
    schema = ContractSchema(
        task_type="feature",
        ceremony_level="STANDARD",
        fields=[_minimal_field()],
    )
    # FEATURE_STANDARD is already registered.
    try:
        register(schema)
    except ValueError as e:
        assert "duplicate" in str(e)
    else:
        raise AssertionError("expected ValueError on duplicate registration")


# --- Per-seeded-contract sanity checks -----------------------------------


def test_default_contract_has_reasoning_and_changes():
    fields = {f.name for f in DEFAULT_CONTRACT.fields}
    assert "reasoning" in fields
    assert "changes" in fields


def test_feature_standard_contract_includes_assumptions():
    fields = {f.name for f in FEATURE_STANDARD_CONTRACT.fields}
    assert "assumptions" in fields
    assert "ac_evidence" in fields
    assert "impact_analysis" in fields


def test_feature_full_contract_requires_alternatives():
    """FULL ceremony must demand alternatives_considered (P21 + F.11 prep)."""
    field = FEATURE_FULL_CONTRACT.field_by_name("alternatives_considered")
    assert field is not None
    assert field.required is True


def test_feature_full_contract_failure_scenarios_required():
    """FULL ceremony promotes failure_scenarios from optional to required."""
    standard = FEATURE_STANDARD_CONTRACT.field_by_name("failure_scenarios")
    full = FEATURE_FULL_CONTRACT.field_by_name("failure_scenarios")
    assert standard is not None and standard.required is False
    assert full is not None and full.required is True


def test_bug_light_contract_requires_regression_test():
    """Bug fixes must produce a regression test."""
    field = BUG_LIGHT_CONTRACT.field_by_name("regression_test")
    assert field is not None
    assert field.required is True


def test_all_seeded_contracts_render_successfully():
    """Every seeded contract produces non-empty render output."""
    for schema in (
        DEFAULT_CONTRACT,
        FEATURE_STANDARD_CONTRACT,
        FEATURE_FULL_CONTRACT,
        BUG_LIGHT_CONTRACT,
    ):
        rendered = schema.render_prompt_fragment()
        assert len(rendered) > 100  # non-trivial output
        assert schema.task_type in rendered
        assert schema.ceremony_level in rendered

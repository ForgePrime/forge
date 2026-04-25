"""Tests for ToolCatalog — Phase L3 Stage L3.2.

Pure-Python tests of registration + authority gate + idempotency check
+ invocation cap + dispatch.
"""

from __future__ import annotations

import pytest

from app.llm.tool_catalog import (
    AuthorityLevel,
    DispatchVerdict,
    Tool,
    ToolCall,
    ToolCatalog,
    authority_le,
)


# --- authority_le helper -------------------------------------------------


def test_authority_le_lower_passes():
    assert authority_le(AuthorityLevel.READ_ONLY, AuthorityLevel.SIDE_EFFECTING_WRITE)


def test_authority_le_equal_passes():
    assert authority_le(
        AuthorityLevel.IDEMPOTENT_WRITE, AuthorityLevel.IDEMPOTENT_WRITE
    )


def test_authority_le_higher_fails():
    assert not authority_le(
        AuthorityLevel.IRREVERSIBLE_WRITE, AuthorityLevel.READ_ONLY
    )


def test_authority_external_call_is_highest():
    """EXTERNAL_CALL is the most permissive level — only allowed when
    autonomy ceiling is also EXTERNAL_CALL."""
    for level in AuthorityLevel:
        if level != AuthorityLevel.EXTERNAL_CALL:
            assert not authority_le(AuthorityLevel.EXTERNAL_CALL, level)
    assert authority_le(AuthorityLevel.EXTERNAL_CALL, AuthorityLevel.EXTERNAL_CALL)


# --- Tool registration ---------------------------------------------------


def test_register_minimal_tool():
    catalog = ToolCatalog()
    tool = Tool(
        name="read_file",
        description="Read a file",
        json_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        authority_level=AuthorityLevel.READ_ONLY,
    )
    catalog.register(tool)
    assert catalog.lookup("read_file") is tool


def test_register_rejects_duplicate_name():
    catalog = ToolCatalog()
    tool = Tool(
        name="x", description="", json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
    )
    catalog.register(tool)
    with pytest.raises(ValueError, match="duplicate"):
        catalog.register(tool)


def test_register_rejects_empty_json_schema():
    catalog = ToolCatalog()
    with pytest.raises(ValueError, match="json_schema"):
        catalog.register(Tool(
            name="x", description="", json_schema={},
            authority_level=AuthorityLevel.READ_ONLY,
        ))


def test_register_with_side_effect_decorator_validates_qualname():
    """If requires_side_effect_decorator=True, fn's qualname must be in
    the side_effect_qualnames set."""
    catalog = ToolCatalog()

    def my_writer():
        pass

    qualname = f"{my_writer.__module__}.{my_writer.__qualname__}"

    # Without registration in side_effect_qualnames -> reject
    with pytest.raises(ValueError, match="not in SideEffectRegistry"):
        catalog.register(
            Tool(
                name="writer", description="x", json_schema={"type": "object"},
                authority_level=AuthorityLevel.SIDE_EFFECTING_WRITE,
                requires_side_effect_decorator=True,
                fn=my_writer,
            ),
            side_effect_qualnames=set(),
        )

    # With registration -> accept
    catalog.register(
        Tool(
            name="writer", description="x", json_schema={"type": "object"},
            authority_level=AuthorityLevel.SIDE_EFFECTING_WRITE,
            requires_side_effect_decorator=True,
            fn=my_writer,
        ),
        side_effect_qualnames={qualname},
    )
    assert catalog.lookup("writer") is not None


def test_register_side_effect_required_but_no_fn_rejected():
    catalog = ToolCatalog()
    with pytest.raises(ValueError, match="tool.fn is None"):
        catalog.register(Tool(
            name="x", description="", json_schema={"type": "object"},
            authority_level=AuthorityLevel.SIDE_EFFECTING_WRITE,
            requires_side_effect_decorator=True,
            fn=None,
        ))


# --- Dispatch happy path -------------------------------------------------


def _make_simple_catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="echo",
        description="Returns its input",
        json_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
        authority_level=AuthorityLevel.READ_ONLY,
        fn=lambda msg="": msg,
    ))
    return catalog


def test_dispatch_unknown_tool_rejected():
    catalog = ToolCatalog()
    verdict = catalog.dispatch(ToolCall(tool_name="missing", args={}))
    assert verdict.passed is False
    assert verdict.rule_code == "unknown_tool"


def test_dispatch_read_only_tool_passes_with_read_only_autonomy():
    catalog = _make_simple_catalog()
    verdict = catalog.dispatch(ToolCall(
        tool_name="echo",
        args={"msg": "hello"},
        autonomy_max_authority=AuthorityLevel.READ_ONLY,
    ))
    assert verdict.passed is True
    assert verdict.result == "hello"


def test_dispatch_returns_dispatched_rule_code():
    catalog = _make_simple_catalog()
    verdict = catalog.dispatch(ToolCall(tool_name="echo", args={}))
    assert verdict.rule_code == "dispatched"


# --- Authority gate ------------------------------------------------------


def test_dispatch_authority_gate_blocks_higher_tool():
    """Tool authority IRREVERSIBLE_WRITE > autonomy READ_ONLY -> rejected."""
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="dangerous",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.IRREVERSIBLE_WRITE,
        fn=lambda: "danger",
    ))
    verdict = catalog.dispatch(ToolCall(
        tool_name="dangerous",
        args={},
        autonomy_max_authority=AuthorityLevel.READ_ONLY,
    ))
    assert verdict.passed is False
    assert verdict.rule_code == "tool_authority_exceeds_autonomy"


def test_dispatch_authority_gate_allows_equal():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="op",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.IDEMPOTENT_WRITE,
        fn=lambda: "ok",
    ))
    verdict = catalog.dispatch(ToolCall(
        tool_name="op",
        args={},
        autonomy_max_authority=AuthorityLevel.IDEMPOTENT_WRITE,
        idempotency_key="not-required-but-fine",
    ))
    assert verdict.passed is True


# --- Idempotency-key guard ----------------------------------------------


def test_dispatch_idempotency_key_required_for_mutating():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="writer",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.IDEMPOTENT_WRITE,
        requires_idempotency_key=True,
        fn=lambda: "ok",
    ))
    # Without idempotency_key
    verdict = catalog.dispatch(ToolCall(
        tool_name="writer",
        args={},
        autonomy_max_authority=AuthorityLevel.IDEMPOTENT_WRITE,
    ))
    assert verdict.passed is False
    assert verdict.rule_code == "missing_idempotency_key"


def test_dispatch_idempotency_key_present_passes():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="writer",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.IDEMPOTENT_WRITE,
        requires_idempotency_key=True,
        fn=lambda: "ok",
    ))
    verdict = catalog.dispatch(ToolCall(
        tool_name="writer",
        args={},
        idempotency_key="key-123",
        autonomy_max_authority=AuthorityLevel.IDEMPOTENT_WRITE,
    ))
    assert verdict.passed is True


# --- Per-execution invocation cap ---------------------------------------


def test_dispatch_invocation_cap_enforced():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="capped",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
        max_invocations_per_execution=2,
        fn=lambda: "ok",
    ))
    # First two calls pass
    v1 = catalog.dispatch(ToolCall(tool_name="capped", args={}, execution_id=1))
    v2 = catalog.dispatch(ToolCall(tool_name="capped", args={}, execution_id=1))
    # Third hits cap
    v3 = catalog.dispatch(ToolCall(tool_name="capped", args={}, execution_id=1))
    assert v1.passed and v2.passed
    assert v3.passed is False
    assert v3.rule_code == "cap_exceeded"


def test_dispatch_invocation_cap_per_execution():
    """Cap is per-Execution; different execution_id has fresh counter."""
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="capped",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
        max_invocations_per_execution=1,
        fn=lambda: "ok",
    ))
    v_a = catalog.dispatch(ToolCall(tool_name="capped", args={}, execution_id=1))
    v_b = catalog.dispatch(ToolCall(tool_name="capped", args={}, execution_id=2))
    assert v_a.passed and v_b.passed
    assert catalog.invocation_count(1, "capped") == 1
    assert catalog.invocation_count(2, "capped") == 1


def test_dispatch_no_cap_unlimited():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="uncapped",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
        # max_invocations_per_execution defaults to None
        fn=lambda: "ok",
    ))
    for _ in range(100):
        v = catalog.dispatch(ToolCall(tool_name="uncapped", args={}))
        assert v.passed


# --- Tool fn exceptions -------------------------------------------------


def test_dispatch_tool_raises_returns_failed_verdict():
    catalog = ToolCatalog()

    def buggy():
        raise RuntimeError("boom")

    catalog.register(Tool(
        name="buggy",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
        fn=buggy,
    ))
    verdict = catalog.dispatch(ToolCall(tool_name="buggy", args={}))
    assert verdict.passed is False
    assert verdict.rule_code == "tool_raised_exception"
    assert "RuntimeError" in (verdict.reason or "")
    assert "boom" in (verdict.reason or "")


def test_dispatch_tool_with_no_fn_rejected():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="stub",
        description="x",
        json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
        fn=None,
    ))
    verdict = catalog.dispatch(ToolCall(tool_name="stub", args={}))
    assert verdict.passed is False
    assert verdict.rule_code == "tool_not_callable"


# --- Catalog list / lookup ----------------------------------------------


def test_list_returns_all_registered():
    catalog = ToolCatalog()
    catalog.register(Tool(
        name="a", description="", json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
    ))
    catalog.register(Tool(
        name="b", description="", json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
    ))
    names = {t.name for t in catalog.list()}
    assert names == {"a", "b"}


def test_lookup_missing_returns_none():
    catalog = ToolCatalog()
    assert catalog.lookup("missing") is None


# --- Frozen dataclasses -------------------------------------------------


def test_tool_is_frozen():
    tool = Tool(
        name="x", description="", json_schema={"type": "object"},
        authority_level=AuthorityLevel.READ_ONLY,
    )
    try:
        tool.name = "y"  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("Tool should be frozen")


def test_dispatch_verdict_is_frozen():
    verdict = DispatchVerdict(passed=True, rule_code="dispatched")
    try:
        verdict.passed = False  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("DispatchVerdict should be frozen")

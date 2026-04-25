"""Tests for relation_semantic — Phase B Stage B.6.

Pure-Python tests of the backfill mapping + relation-typed queries.
"""

from __future__ import annotations

from app.evidence.causal_graph import EdgeView, InMemoryEdgeSource, Node
from app.evidence.relation_semantic import (
    BackfillResult,
    RelationSemantic,
    backfill,
    edges_by_relation_class,
    map_text_to_enum,
    requirements_of,
    risks_of,
    tests_of as _tests_of,  # rename to dodge pytest auto-discovery of `test*`
)


def _e(src_id: int, dst_id: int, rel: str) -> EdgeView:
    return EdgeView(
        src_type="x", src_id=src_id, dst_type="y", dst_id=dst_id, relation=rel,
    )


# --- map_text_to_enum ----------------------------------------------------


def test_map_canonical_lowercase():
    assert map_text_to_enum("requirement_of") == RelationSemantic.REQUIREMENT_OF


def test_map_case_insensitive():
    assert map_text_to_enum("REQUIREMENT_OF") == RelationSemantic.REQUIREMENT_OF
    assert map_text_to_enum("Requirement_Of") == RelationSemantic.REQUIREMENT_OF


def test_map_whitespace_trimmed():
    assert map_text_to_enum("  requirement_of  ") == RelationSemantic.REQUIREMENT_OF


def test_map_synonyms():
    """Multiple TEXT spellings map to same ENUM."""
    assert map_text_to_enum("requires") == RelationSemantic.REQUIREMENT_OF
    assert map_text_to_enum("satisfies") == RelationSemantic.REQUIREMENT_OF
    assert map_text_to_enum("implements_requirement") == RelationSemantic.REQUIREMENT_OF


def test_map_risk_synonyms():
    assert map_text_to_enum("risk_of") == RelationSemantic.RISK_OF
    assert map_text_to_enum("risk") == RelationSemantic.RISK_OF
    assert map_text_to_enum("risks") == RelationSemantic.RISK_OF


def test_map_test_synonyms():
    assert map_text_to_enum("test_of") == RelationSemantic.TEST_OF
    assert map_text_to_enum("tests") == RelationSemantic.TEST_OF
    assert map_text_to_enum("verified_by_test") == RelationSemantic.TEST_OF


def test_map_depends_on_to_derives_from():
    """B.1 free-form 'depends_on' maps to DERIVES_FROM (semantic closest)."""
    assert map_text_to_enum("depends_on") == RelationSemantic.DERIVES_FROM


def test_map_unknown_returns_none():
    assert map_text_to_enum("nonexistent_relation") is None
    assert map_text_to_enum("") is None
    # whitespace-only is also unmapped
    assert map_text_to_enum("   ") is None


def test_map_determinism():
    """Same input -> same output across calls (P6)."""
    inputs = ["requirement_of", "risks", "TESTS_OF", "depends_on"]
    runs = []
    for _ in range(3):
        runs.append([map_text_to_enum(s) for s in inputs])
    assert runs[0] == runs[1] == runs[2]


# --- backfill() over batches --------------------------------------------


def test_backfill_empty_input_returns_empty():
    result = backfill([])
    assert result.mapped == {}
    assert result.unmapped == ()


def test_backfill_all_mapped():
    result = backfill(["requirement_of", "risk_of", "test_of"])
    assert len(result.mapped) == 3
    assert result.unmapped == ()


def test_backfill_partial_mapped():
    result = backfill(["requirement_of", "unknown_relation_x", "risks"])
    assert "requirement_of" in result.mapped
    assert "risks" in result.mapped
    assert "unknown_relation_x" in result.unmapped


def test_backfill_dedupes_input():
    result = backfill(["requirement_of", "requirement_of", "risk_of"])
    assert len(result.mapped) == 2


def test_backfill_unmapped_sorted_for_determinism():
    """Unmapped entries are sorted so output is deterministic across input orders."""
    r1 = backfill(["xyz_unknown", "abc_unknown"])
    r2 = backfill(["abc_unknown", "xyz_unknown"])
    assert r1.unmapped == r2.unmapped == ("abc_unknown", "xyz_unknown")


def test_backfill_idempotent():
    """Running twice with same input -> same output (P6)."""
    inputs = ["requirement_of", "unknown_x", "tests"]
    r1 = backfill(inputs)
    r2 = backfill(inputs)
    assert r1 == r2


def test_backfill_result_is_frozen():
    result = backfill(["requirement_of"])
    try:
        result.mapped = {}  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("BackfillResult should be frozen")


# --- edges_by_relation_class --------------------------------------------


def test_edges_by_class_filters_to_matching():
    src = InMemoryEdgeSource([
        _e(1, 5, "requirement_of"),
        _e(2, 5, "risk_of"),
        _e(3, 5, "requires"),  # synonym of REQUIREMENT_OF
    ])
    matched = edges_by_relation_class(
        src, Node("y", 5), RelationSemantic.REQUIREMENT_OF,
    )
    src_ids = {e.src_id for e in matched}
    assert 1 in src_ids
    assert 3 in src_ids
    assert 2 not in src_ids  # risk_of, not requirement


def test_edges_by_class_unmapped_excluded():
    """Edges with unmapped relation strings are excluded from class results."""
    src = InMemoryEdgeSource([
        _e(1, 5, "requirement_of"),
        _e(2, 5, "totally_unknown_class"),
    ])
    matched = edges_by_relation_class(
        src, Node("y", 5), RelationSemantic.REQUIREMENT_OF,
    )
    assert len(matched) == 1
    assert matched[0].src_id == 1


def test_edges_by_class_empty_when_none_match():
    src = InMemoryEdgeSource([_e(1, 5, "blocks")])
    matched = edges_by_relation_class(
        src, Node("y", 5), RelationSemantic.TEST_OF,
    )
    assert matched == []


# --- requirements_of / risks_of / tests_of helpers ----------------------


def test_requirements_of():
    src = InMemoryEdgeSource([
        _e(1, 5, "requirement_of"),
        _e(2, 5, "risk_of"),
    ])
    reqs = requirements_of(src, Node("y", 5))
    assert len(reqs) == 1
    assert reqs[0].src_id == 1


def test_risks_of():
    src = InMemoryEdgeSource([
        _e(1, 5, "risk_of"),
        _e(2, 5, "risk"),  # synonym
        _e(3, 5, "test_of"),
    ])
    risks = risks_of(src, Node("y", 5))
    src_ids = {e.src_id for e in risks}
    assert 1 in src_ids and 2 in src_ids
    assert 3 not in src_ids


def test_tests_of():
    src = InMemoryEdgeSource([
        _e(1, 5, "test_of"),
        _e(2, 5, "verified_by_test"),  # synonym
        _e(3, 5, "blocks"),
    ])
    tests = _tests_of(src, Node("y", 5))
    src_ids = {e.src_id for e in tests}
    assert 1 in src_ids and 2 in src_ids
    assert 3 not in src_ids


# --- Coverage: all 10 RelationSemantic values are reachable -------------


def test_every_enum_value_has_at_least_one_text_mapping():
    """Coverage: every RelationSemantic value is the target of at least
    one text-key mapping."""
    targets = set()
    from app.evidence.relation_semantic import _BACKFILL_MAP
    for v in _BACKFILL_MAP.values():
        targets.add(v)
    for enum_val in RelationSemantic:
        assert enum_val in targets, (
            f"{enum_val} has no text mapping in _BACKFILL_MAP"
        )

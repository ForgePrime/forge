"""Tests for CausalGraph service — Phase B Stage B.3.

Pure-Python tests using InMemoryEdgeSource. Cover ancestors() and
minimal_justification() over canonical fixtures + edge cases:
- empty graph, single edge, linear chain, branching, cycles (won't
  occur per B.1 acyclicity but graph code must terminate anyway).
- depth boundary, relation filter.
- determinism (P6).
"""

from __future__ import annotations

from app.evidence.causal_graph import (
    EdgeView,
    InMemoryEdgeSource,
    Node,
    ancestors,
    minimal_justification,
)


def _e(src_t: str, src_i: int, dst_t: str, dst_i: int, rel: str = "depends_on") -> EdgeView:
    return EdgeView(src_type=src_t, src_id=src_i, dst_type=dst_t, dst_id=dst_i, relation=rel)


# --- ancestors() -----------------------------------------------------------


def test_ancestors_empty_graph_returns_empty():
    src = InMemoryEdgeSource()
    result = ancestors(src, Node("decision", 1))
    assert result == []


def test_ancestors_node_with_no_incoming_returns_empty():
    src = InMemoryEdgeSource([_e("decision", 1, "decision", 2)])
    result = ancestors(src, Node("decision", 1))  # node 1 has no incoming
    assert result == []


def test_ancestors_single_parent():
    src = InMemoryEdgeSource([_e("decision", 1, "decision", 2)])
    result = ancestors(src, Node("decision", 2))
    assert len(result) == 1
    assert result[0].src_id == 1
    assert result[0].dst_id == 2


def test_ancestors_linear_chain():
    """A → B → C → D; ancestors(D) = {A→B, B→C, C→D}."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),
        _e("e", 2, "e", 3),
        _e("e", 3, "e", 4),
    ])
    result = ancestors(src, Node("e", 4))
    assert len(result) == 3
    src_ids = {edge.src_id for edge in result}
    assert src_ids == {1, 2, 3}


def test_ancestors_branching():
    """A→C, B→C; ancestors(C) returns both parent edges."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 3),
        _e("e", 2, "e", 3),
    ])
    result = ancestors(src, Node("e", 3))
    assert len(result) == 2
    src_ids = {edge.src_id for edge in result}
    assert src_ids == {1, 2}


def test_ancestors_diamond():
    """A→B, A→C, B→D, C→D; ancestors(D) includes A only once."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),  # A→B
        _e("e", 1, "e", 3),  # A→C
        _e("e", 2, "e", 4),  # B→D
        _e("e", 3, "e", 4),  # C→D
    ])
    result = ancestors(src, Node("e", 4))
    # 4 distinct edges; A appears twice as src but only via different relations
    # — here all relations equal so 4 edges total expected.
    assert len(result) == 4
    src_ids = {edge.src_id for edge in result}
    assert src_ids == {1, 2, 3}


def test_ancestors_depth_limit_zero_returns_empty():
    src = InMemoryEdgeSource([_e("e", 1, "e", 2)])
    result = ancestors(src, Node("e", 2), depth=0)
    assert result == []


def test_ancestors_depth_limit_one_direct_parents_only():
    """A → B → C; ancestors(C, depth=1) = {B→C} only."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),
        _e("e", 2, "e", 3),
    ])
    result = ancestors(src, Node("e", 3), depth=1)
    assert len(result) == 1
    assert result[0].src_id == 2


def test_ancestors_relation_filter():
    """Edges with non-matching relation are skipped."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2, rel="depends_on"),
        _e("e", 3, "e", 2, rel="evidences"),
    ])
    deps = ancestors(src, Node("e", 2), relation_filter="depends_on")
    evids = ancestors(src, Node("e", 2), relation_filter="evidences")
    assert len(deps) == 1 and deps[0].src_id == 1
    assert len(evids) == 1 and evids[0].src_id == 3


def test_ancestors_pathological_cycle_terminates():
    """Even with cycle (shouldn't occur per B.1 acyclicity), BFS terminates."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),
        _e("e", 2, "e", 1),  # cycle: 1↔2
    ])
    result = ancestors(src, Node("e", 2))
    # Should NOT loop forever; visited_edges set deduplicates.
    assert len(result) <= 2


def test_ancestors_determinism():
    """Same source + same query -> same result (P6)."""
    edges = [
        _e("e", 1, "e", 3),
        _e("e", 2, "e", 3),
        _e("e", 1, "e", 2),
    ]
    src = InMemoryEdgeSource(edges)
    r1 = ancestors(src, Node("e", 3))
    r2 = ancestors(src, Node("e", 3))
    r3 = ancestors(src, Node("e", 3))
    assert r1 == r2 == r3


# --- minimal_justification() ----------------------------------------------


def test_minimal_justification_root_returns_empty():
    """Root node (no incoming) returns empty path."""
    src = InMemoryEdgeSource([_e("e", 1, "e", 2)])
    result = minimal_justification(src, Node("e", 1))
    assert result == []


def test_minimal_justification_direct_parent_root():
    """A→B; B's parent A is a root; path is [A→B]."""
    src = InMemoryEdgeSource([_e("e", 1, "e", 2)])
    result = minimal_justification(src, Node("e", 2))
    assert len(result) == 1
    assert result[0].src_id == 1
    assert result[0].dst_id == 2


def test_minimal_justification_linear_chain():
    """A→B→C→D; minimal_justification(D) walks back to A."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),
        _e("e", 2, "e", 3),
        _e("e", 3, "e", 4),
    ])
    result = minimal_justification(src, Node("e", 4))
    # path edges traverse from D back to A: [C→D, B→C, A→B] in walk order
    # (start->end ordering per docstring: first dst=start)
    assert len(result) == 3
    # The path should be a valid chain
    assert result[0].dst_id == 4
    assert result[-1].src_id == 1


def test_minimal_justification_branching_picks_shortest():
    """A→C, A→B→C; minimal returns the shorter A→C, length 1."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 3),  # direct: A→C (length 1)
        _e("e", 1, "e", 2),  # detour: A→B→C (length 2)
        _e("e", 2, "e", 3),
    ])
    result = minimal_justification(src, Node("e", 3))
    assert len(result) == 1
    assert result[0].src_id == 1


def test_minimal_justification_max_depth_respected():
    """Long chain; max_depth=2 cuts before reaching root -> empty."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),
        _e("e", 2, "e", 3),
        _e("e", 3, "e", 4),
        _e("e", 4, "e", 5),
    ])
    result = minimal_justification(src, Node("e", 5), max_depth=2)
    # max_depth caps BFS before finding root at depth 4 -> empty.
    assert result == []


def test_minimal_justification_isolated_node():
    """Node not even in graph -> returns empty (no incoming)."""
    src = InMemoryEdgeSource([_e("e", 1, "e", 2)])
    result = minimal_justification(src, Node("e", 999))
    assert result == []


def test_minimal_justification_determinism():
    """Same input -> same path (P6)."""
    src = InMemoryEdgeSource([
        _e("e", 1, "e", 2),
        _e("e", 2, "e", 3),
    ])
    r1 = minimal_justification(src, Node("e", 3))
    r2 = minimal_justification(src, Node("e", 3))
    assert r1 == r2

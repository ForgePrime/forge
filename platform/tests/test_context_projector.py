"""Tests for ContextProjector — Phase B Stage B.4.

Pure-Python tests. Verifies:
- Projector traverses ancestors correctly via injected EdgeSource.
- StaticRelationClassifier maps relations to FORMAL P15 buckets.
- Custom classifier is plumbed correctly.
- Projection -> ContextBudget.fit() integration works end-to-end.
- Determinism (P6).
"""

from __future__ import annotations

from app.evidence.causal_graph import EdgeView, InMemoryEdgeSource, Node
from app.evidence.context_projector import (
    ContextProjection,
    StaticRelationClassifier,
    project,
)
from app.llm.context_budget import Bucket, fit


def _e(src_t: str, src_i: int, dst_t: str, dst_i: int, rel: str = "depends_on") -> EdgeView:
    return EdgeView(src_type=src_t, src_id=src_i, dst_type=dst_t, dst_id=dst_i, relation=rel)


# --- Empty / minimal projections ------------------------------------------


def test_project_empty_graph_returns_empty_projection():
    src = InMemoryEdgeSource()
    result = project(graph_source=src, task_node=Node("task", 1))
    assert isinstance(result, ContextProjection)
    assert result.items == ()
    assert result.edge_count == 0
    assert result.task_node == Node("task", 1)


def test_project_node_with_no_ancestors_returns_empty():
    src = InMemoryEdgeSource([_e("task", 1, "task", 2)])
    # task 1 has no incoming
    result = project(graph_source=src, task_node=Node("task", 1))
    assert result.items == ()


def test_project_single_ancestor_creates_one_item():
    src = InMemoryEdgeSource([_e("task", 1, "task", 2, rel="decision")])
    result = project(graph_source=src, task_node=Node("task", 2))
    assert len(result.items) == 1


# --- Default classifier: relation -> bucket -------------------------------


def test_must_relation_classified_as_MUST():
    src = InMemoryEdgeSource([
        _e("inv", 1, "task", 2, rel="invariant"),
    ])
    result = project(graph_source=src, task_node=Node("task", 2))
    assert result.items[0].bucket == Bucket.MUST


def test_should_relation_classified_as_SHOULD():
    src = InMemoryEdgeSource([
        _e("dec", 1, "task", 2, rel="decision"),
    ])
    result = project(graph_source=src, task_node=Node("task", 2))
    assert result.items[0].bucket == Bucket.SHOULD


def test_unknown_relation_classified_as_NICE():
    src = InMemoryEdgeSource([
        _e("kn", 1, "task", 2, rel="some_obscure_relation"),
    ])
    result = project(graph_source=src, task_node=Node("task", 2))
    assert result.items[0].bucket == Bucket.NICE


def test_must_relations_get_higher_priority_than_should():
    src = InMemoryEdgeSource([
        _e("inv", 1, "task", 2, rel="invariant"),
        _e("dec", 2, "task", 2, rel="decision"),
    ])
    result = project(graph_source=src, task_node=Node("task", 2))
    must_items = [i for i in result.items if i.bucket == Bucket.MUST]
    should_items = [i for i in result.items if i.bucket == Bucket.SHOULD]
    assert must_items
    assert should_items
    assert must_items[0].priority_within_bucket > should_items[0].priority_within_bucket


# --- Custom classifier ----------------------------------------------------


class _FixedClassifier:
    """All edges -> MUST priority 99, fixed token count."""

    def classify(self, edge):
        return (Bucket.MUST, 99, f"fixed-{edge.relation}", 5)


def test_custom_classifier_used():
    src = InMemoryEdgeSource([
        _e("a", 1, "task", 2, rel="weird"),
        _e("b", 2, "task", 2, rel="weirder"),
    ])
    result = project(
        graph_source=src,
        task_node=Node("task", 2),
        classifier=_FixedClassifier(),
    )
    assert all(i.bucket == Bucket.MUST for i in result.items)
    assert all(i.priority_within_bucket == 99 for i in result.items)
    assert all(i.token_count == 5 for i in result.items)


# --- Source-ref dedup -----------------------------------------------------


def test_duplicate_edges_deduplicated_by_source_ref():
    """If two edges have identical (src, dst, relation), only one item."""
    src = InMemoryEdgeSource([
        _e("a", 1, "task", 2, rel="depends_on"),
        _e("a", 1, "task", 2, rel="depends_on"),  # duplicate
    ])
    result = project(graph_source=src, task_node=Node("task", 2))
    # ancestors() already deduplicates via visited_edges set; this asserts
    # the projector preserves that property.
    assert len(result.items) == 1


# --- Depth + relation filter passed through to ancestors() ----------------


def test_depth_zero_returns_no_items():
    src = InMemoryEdgeSource([_e("a", 1, "task", 2)])
    result = project(graph_source=src, task_node=Node("task", 2), depth=0)
    assert result.items == ()


def test_relation_filter_prunes_non_matching():
    src = InMemoryEdgeSource([
        _e("a", 1, "task", 2, rel="decision"),
        _e("b", 1, "task", 2, rel="evidences"),
    ])
    result = project(
        graph_source=src,
        task_node=Node("task", 2),
        relation_filter="decision",
    )
    assert len(result.items) == 1
    assert result.items[0].source_ref.startswith("a:1-decision->")


# --- End-to-end: projector -> budget --------------------------------------


def test_projection_feeds_into_context_budget():
    """Verify the bridge: projector items can be fit into a budget."""
    src = InMemoryEdgeSource([
        _e("inv", 1, "task", 100, rel="invariant"),       # MUST
        _e("dec", 2, "task", 100, rel="decision"),         # SHOULD
        _e("dec", 3, "task", 100, rel="decision"),         # SHOULD
        _e("kn", 4, "task", 100, rel="reference"),         # NICE
    ])
    projection = project(graph_source=src, task_node=Node("task", 100))
    # Default classifier produces ~10-ish tokens per item; budget=20 fits some.
    fit_result = fit(projection.items, budget_tokens=20)
    assert fit_result.status == "ACCEPTED"
    # MUST always admitted
    assert any(i.bucket == Bucket.MUST for i in fit_result.included)


# --- Determinism (P6) ------------------------------------------------------


def test_projection_determinism():
    src = InMemoryEdgeSource([
        _e("inv", 1, "task", 2, rel="invariant"),
        _e("dec", 2, "task", 2, rel="decision"),
        _e("kn", 3, "task", 2, rel="other"),
    ])
    r1 = project(graph_source=src, task_node=Node("task", 2))
    r2 = project(graph_source=src, task_node=Node("task", 2))
    r3 = project(graph_source=src, task_node=Node("task", 2))
    assert r1 == r2 == r3


def test_static_classifier_default_token_count_nonzero():
    """Token count is at least 1 for any edge (avoids empty-content gotcha)."""
    classifier = StaticRelationClassifier()
    edge = _e("a", 1, "b", 2, rel="x")
    _, _, _, tokens = classifier.classify(edge)
    assert tokens >= 1


def test_static_classifier_content_includes_relation():
    """Content text traceable back to the source edge."""
    classifier = StaticRelationClassifier()
    edge = _e("a", 1, "b", 2, rel="depends_on")
    _, _, content, _ = classifier.classify(edge)
    assert "depends_on" in content
    assert "a" in content and "b" in content

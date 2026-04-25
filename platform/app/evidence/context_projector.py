"""ContextProjector — Phase B Stage B.4.

Bridges:
- B.3 CausalGraph (ancestors over the causal DAG) — input source.
- L3.3 ContextBudget (MUST/SHOULD/NICE bucket fitter) — output consumer.

Per FORMAL_PROPERTIES_v2 P15 (Context Projection):
    pi_k : G -> C_k
    For task k, the prompt context is the minimal justification frontier
    from G relevant to k, pruned to a token budget.

Pluggable design: the ContextProjector traverses ancestors and asks an
injected `Classifier` for each edge what bucket + priority + token count
it should carry. This decouples graph mechanics from domain heuristics:
- The graph mechanics are testable without knowing entity types.
- The classifier is per-deployment (different teams may have different
  relevance heuristics).
- Tests inject a deterministic stub classifier.

Default classifier (`StaticRelationClassifier`) maps relation strings
to buckets per the FORMAL P15 priority order (must-guidelines ->
recent decisions -> evidence -> knowledge):
    must_guideline | invariant   -> MUST  high priority
    decision | depends_on        -> SHOULD priority by recency
    evidences | evidence         -> SHOULD priority by recency
    derives_from | knowledge     -> NICE
    other relations              -> NICE low priority

Determinism: same graph state + same task + same classifier -> same
projection. The projector is a pure function over (graph, classifier);
the graph's edge-source determinism flows through.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from app.evidence.causal_graph import EdgeSource, EdgeView, Node, ancestors
from app.llm.context_budget import Bucket, ContextItem


class Classifier(Protocol):
    """Maps a CausalEdge to (bucket, priority, content, token_count).

    Per-edge classification is the only domain hook. The projector
    handles graph traversal + ContextItem assembly mechanics.
    """

    def classify(self, edge: EdgeView) -> tuple[Bucket, int, str, int]:
        """Return (bucket, priority_within_bucket, content_text, token_count)."""
        ...


@dataclass(frozen=True)
class StaticRelationClassifier:
    """Default classifier: bucket per relation string per FORMAL P15.

    Pure function; no state. Token count uses len(content)//4 as a
    cheap stand-in for a real tokenizer (matches typical English
    word-to-token ratio); production callers should swap this for a
    tiktoken-backed classifier.
    """

    must_relations: tuple[str, ...] = ("must_guideline", "invariant", "hard_constraint")
    should_relations: tuple[str, ...] = (
        "decision",
        "depends_on",
        "evidences",
        "evidence",
        "produces",
        "blocks",
    )
    # everything else falls into NICE.

    def classify(self, edge: EdgeView) -> tuple[Bucket, int, str, int]:
        rel = edge.relation
        if rel in self.must_relations:
            bucket = Bucket.MUST
            priority = 100
        elif rel in self.should_relations:
            bucket = Bucket.SHOULD
            # Higher priority for direct evidence/decisions; lower for transitive.
            priority = 50
        else:
            bucket = Bucket.NICE
            priority = 10
        # Synthetic content text — real classifier would compose actual content.
        content = (
            f"[{rel}] {edge.src_type}#{edge.src_id} -> "
            f"{edge.dst_type}#{edge.dst_id}"
        )
        token_count = max(1, len(content) // 4)
        return bucket, priority, content, token_count


@dataclass(frozen=True)
class ContextProjection:
    """Result of projecting graph -> ContextItem stream."""

    task_node: Node
    items: tuple[ContextItem, ...]
    edge_count: int  # ancestors visited
    depth_used: int  # max BFS depth used


def project(
    *,
    graph_source: EdgeSource,
    task_node: Node,
    classifier: Classifier | None = None,
    depth: int = 10,
    relation_filter: str | None = None,
) -> ContextProjection:
    """BFS ancestors of task_node; classify each edge into a ContextItem.

    Args:
        graph_source: EdgeSource from B.3 — provides incoming edges.
        task_node: the task whose context is being projected.
        classifier: per-edge bucket+priority assignment. Default
            StaticRelationClassifier maps relation strings per FORMAL P15.
        depth: BFS depth cap (per ADR-004 strawman default 10).
        relation_filter: optional — only edges with this relation traversed.

    Returns:
        ContextProjection with deduplicated items in BFS-visit order.
        Caller passes .items to L3.3 ContextBudget.fit().

    Determinism: P6. Same inputs -> same projection.
    """
    classifier_impl: Classifier = classifier or StaticRelationClassifier()
    edges = ancestors(
        graph_source,
        task_node,
        depth=depth,
        relation_filter=relation_filter,
    )

    items: list[ContextItem] = []
    seen_source_refs: set[str] = set()

    for edge in edges:
        bucket, priority, content, tokens = classifier_impl.classify(edge)
        # Source ref: deterministic key for tie-breaking + dedup.
        source_ref = (
            f"{edge.src_type}:{edge.src_id}-{edge.relation}->"
            f"{edge.dst_type}:{edge.dst_id}"
        )
        if source_ref in seen_source_refs:
            continue
        seen_source_refs.add(source_ref)
        items.append(
            ContextItem(
                content=content,
                bucket=bucket,
                priority_within_bucket=priority,
                source_ref=source_ref,
                token_count=tokens,
            )
        )

    return ContextProjection(
        task_node=task_node,
        items=tuple(items),
        edge_count=len(edges),
        depth_used=depth,
    )

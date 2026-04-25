"""CausalGraph service — Phase B Stage B.3.

Pure-Python BFS over the causal DAG. Backend-agnostic: takes an
EdgeSource Protocol (DB-backed in production, in-memory list in tests).

Per FORMAL_PROPERTIES_v2 P14 + PLAN_MEMORY_CONTEXT B.3 work items:
- ancestors(node, depth, relation_filter) -> list[CausalEdge]
  BFS over causal_edges; stops at depth (avoiding pathological deep
  graphs); optionally filters by relation type.
- minimal_justification(node) -> list[CausalEdge]
  Shortest path from `node` to a root (no incoming edges) — the
  smallest evidence chain justifying the node's existence.

Per Protocol purity: no side effects, no writes, no external calls.
The EdgeSource is the only injected dependency; concrete impls (DB or
in-memory) handle their own purity guarantees.

Edge interpretation: `causal_edges(src, dst, relation)` reads as
"`src` causally precedes/justifies `dst` via `relation`". Therefore
`ancestors(dst)` = walk EDGES BACKWARD from dst; the result is the
set of `src` nodes that flow into dst (transitively, up to depth).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class EdgeView:
    """A read-only view over a CausalEdge for graph traversal.

    Decoupled from the ORM so in-memory tests don't need SQLAlchemy.
    Production code constructs these from CausalEdge rows.
    """

    src_type: str
    src_id: int
    dst_type: str
    dst_id: int
    relation: str


@dataclass(frozen=True)
class Node:
    """A graph node addressed by (entity_type, entity_id)."""

    type: str
    id: int


class EdgeSource(Protocol):
    """Backend Protocol for fetching incoming edges to a node.

    Implementations:
    - InMemoryEdgeSource — a list-backed source for tests.
    - DBEdgeSource — SQLAlchemy-backed source for production
      (ships with B.3 wiring; not in this commit's scope).
    """

    def incoming(self, node: Node) -> list[EdgeView]:
        """Return all edges where dst = node. May be unsorted."""
        ...


class InMemoryEdgeSource:
    """List-backed EdgeSource for tests + small dev scaffolds.

    Edges are scanned linearly per query (O(N) per call). Production
    should use a DB-backed source with the (dst_type, dst_id) index
    from B.1.
    """

    def __init__(self, edges: Iterable[EdgeView] = ()) -> None:
        self._edges: list[EdgeView] = list(edges)

    def add(self, edge: EdgeView) -> None:
        self._edges.append(edge)

    def incoming(self, node: Node) -> list[EdgeView]:
        return [
            e
            for e in self._edges
            if e.dst_type == node.type and e.dst_id == node.id
        ]


def ancestors(
    source: EdgeSource,
    node: Node,
    *,
    depth: int = 10,
    relation_filter: str | None = None,
) -> list[EdgeView]:
    """BFS over incoming edges; return all edges reachable within depth.

    Args:
        source: EdgeSource Protocol implementation.
        node: starting node — `dst` of the first hop.
        depth: maximum BFS depth (number of hops). Default 10 per
            ADR-004 strawman; PLAN B.3 A_{B.3} Q3 still pending.
            Depth 0 returns []; depth 1 returns direct parents only.
        relation_filter: if set, only edges with this `relation` value
            are traversed AND included in the result.

    Returns:
        Deduplicated list of EdgeView. Order: BFS-visit order
        (deterministic given deterministic source.incoming output).
    """
    if depth <= 0:
        return []

    visited_edges: set[tuple[str, int, str, int, str]] = set()
    visited_nodes: set[Node] = {node}
    out: list[EdgeView] = []
    queue: deque[tuple[Node, int]] = deque([(node, 0)])

    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for edge in source.incoming(current):
            if relation_filter is not None and edge.relation != relation_filter:
                continue
            edge_key = (
                edge.src_type, edge.src_id,
                edge.dst_type, edge.dst_id,
                edge.relation,
            )
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)
            out.append(edge)
            parent = Node(type=edge.src_type, id=edge.src_id)
            if parent not in visited_nodes:
                visited_nodes.add(parent)
                queue.append((parent, current_depth + 1))
    return out


def minimal_justification(
    source: EdgeSource,
    node: Node,
    *,
    max_depth: int = 100,
) -> list[EdgeView]:
    """Shortest path from `node` back to a root.

    A "root" is a node with no incoming edges (origin of the causal
    chain). Returns the edge sequence in walk order: first edge has
    dst = node, last edge has src = root.

    Args:
        source: EdgeSource.
        node: starting node.
        max_depth: safety cap to prevent runaway in pathological graphs.

    Returns:
        - Empty list if `node` is itself a root (no incoming edges).
        - Single-edge list if `node`'s direct parent is a root.
        - Path list otherwise.

    Determinism: when multiple shortest paths exist, the path through
    the parent encountered FIRST in source.incoming() order is returned.
    Caller is responsible for ordering source.incoming() deterministically
    if reproducible-across-runs is required.
    """
    if max_depth <= 0:
        return []

    # BFS recording parent pointer per visited node so we can reconstruct
    # the shortest path on root-discovery.
    visited: dict[Node, EdgeView | None] = {node: None}
    queue: deque[tuple[Node, int]] = deque([(node, 0)])

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        incoming = source.incoming(current)
        if not incoming:
            # `current` is a root. Reconstruct path from `node` to here.
            return _reconstruct_path(visited, node, current)
        for edge in incoming:
            parent = Node(type=edge.src_type, id=edge.src_id)
            if parent not in visited:
                visited[parent] = edge
                queue.append((parent, depth + 1))

    # Exhausted without finding a root within max_depth; return empty
    # rather than partial path (caller can re-query with larger depth).
    return []


def _reconstruct_path(
    visited: dict[Node, EdgeView | None],
    start: Node,
    end: Node,
) -> list[EdgeView]:
    """Walk the parent-pointer chain from `end` back to `start`.

    Returns edges in start→end order (i.e. first edge has dst=start,
    last edge has src=end).
    """
    if start == end:
        return []
    path: list[EdgeView] = []
    current = end
    while current != start:
        edge = visited.get(current)
        if edge is None:
            # Disconnected — should not happen in BFS-reachable set.
            return []
        path.append(edge)
        current = Node(type=edge.dst_type, id=edge.dst_id)
    return list(reversed(path))

"""DBEdgeSource — Phase B Stage B.3 production backend.

Concrete implementation of EdgeSource Protocol (from
app/evidence/causal_graph.py) backed by the `causal_edges` Postgres
table.

Pairs with InMemoryEdgeSource (test backend). Both satisfy the
EdgeSource Protocol; production uses this DB-backed source, tests
the in-memory.

Per FORMAL P14 (Causal decision memory): the table is the canonical
DAG store; this Source is the read-side query layer that B.3
ancestors() / B.4 ContextProjector consume.

Performance note: each call to incoming(node) issues a single SELECT
indexed on (dst_type, dst_id) per the B.1 schema. BFS over depth=10
issues at most 10*N queries where N is the average fanout — typically
fast (< 50ms total) at MVP scale.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.evidence.causal_graph import EdgeView, Node
from app.models.causal_edge import CausalEdge


class DBEdgeSource:
    """SQLAlchemy-backed EdgeSource.

    Same Protocol as InMemoryEdgeSource. Constructor takes a
    session_factory so each query acquires a fresh session.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def incoming(self, node: Node) -> list[EdgeView]:
        """Return all edges where dst = node.

        Sorted deterministically by (relation, src_type, src_id) so
        BFS over the source produces reproducible order. The (dst_type,
        dst_id) index from B.1 makes this query O(log N + matching).
        """
        session: Session = self._session_factory()
        try:
            rows = (
                session.query(CausalEdge)
                .filter(
                    CausalEdge.dst_type == node.type,
                    CausalEdge.dst_id == node.id,
                )
                .order_by(
                    CausalEdge.relation,
                    CausalEdge.src_type,
                    CausalEdge.src_id,
                )
                .all()
            )
            return [
                EdgeView(
                    src_type=row.src_type,
                    src_id=row.src_id,
                    dst_type=row.dst_type,
                    dst_id=row.dst_id,
                    relation=row.relation,
                )
                for row in rows
            ]
        finally:
            session.close()

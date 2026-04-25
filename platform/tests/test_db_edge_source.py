"""Tests for DBEdgeSource — Phase B Stage B.3 (live DB).

Verifies the DB-backed EdgeSource satisfies the same Protocol contract
as InMemoryEdgeSource. Same B.3 ancestors() + B.4 ContextProjector
should work over either backend.

Skips automatically if Postgres unavailable.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.evidence.causal_graph import EdgeView, Node, ancestors, minimal_justification
from app.evidence.context_projector import project as project_context
from app.evidence.db_edge_source import DBEdgeSource
from app.evidence.relation_semantic import RelationSemantic, requirements_of, risks_of
from app.models.causal_edge import CausalEdge  # noqa: F401 — registers model


_TEST_DB_URL = "postgresql://forge:forge@localhost:5432/forge_platform"


def _engine():
    return create_engine(_TEST_DB_URL, pool_pre_ping=True)


def _can_connect() -> bool:
    try:
        with _engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _can_connect(),
    reason="Postgres at localhost:5432 unavailable; skipping live-DB tests",
)


@pytest.fixture
def session_factory():
    engine = _engine()
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    yield Session
    # Cleanup: only rows with test src_type prefix
    with Session() as cleanup:
        cleanup.execute(
            text("DELETE FROM causal_edges WHERE src_type LIKE 'test_b3_%'")
        )
        cleanup.commit()


@pytest.fixture
def source(session_factory):
    return DBEdgeSource(session_factory)


def _seed(session_factory, edges: list[dict]):
    """Insert synthetic causal_edges rows. Each dict provides
    src_type, src_id, dst_type, dst_id, relation, src_created_at,
    dst_created_at."""
    base = dt.datetime.now(dt.timezone.utc)
    with session_factory() as session:
        for i, e in enumerate(edges):
            row = CausalEdge(
                src_type=e["src_type"],
                src_id=e["src_id"],
                dst_type=e["dst_type"],
                dst_id=e["dst_id"],
                relation=e["relation"],
                src_created_at=e.get(
                    "src_created_at", base - dt.timedelta(seconds=100 - i),
                ),
                dst_created_at=e.get(
                    "dst_created_at", base - dt.timedelta(seconds=50 - i),
                ),
            )
            session.add(row)
        session.commit()


# --- incoming() basics ---------------------------------------------------


def test_incoming_empty_node(source):
    edges = source.incoming(Node(type="test_b3_unknown", id=999999))
    assert edges == []


def test_incoming_finds_seeded_edge(session_factory, source):
    _seed(session_factory, [
        {
            "src_type": "test_b3_dec", "src_id": 1,
            "dst_type": "test_b3_task", "dst_id": 10,
            "relation": "decision",
        },
    ])
    edges = source.incoming(Node(type="test_b3_task", id=10))
    assert len(edges) == 1
    assert edges[0].src_id == 1
    assert edges[0].relation == "decision"


def test_incoming_filters_by_dst(session_factory, source):
    _seed(session_factory, [
        {"src_type": "test_b3_a", "src_id": 1, "dst_type": "test_b3_t", "dst_id": 10, "relation": "rel1"},
        {"src_type": "test_b3_b", "src_id": 2, "dst_type": "test_b3_t", "dst_id": 20, "relation": "rel2"},
    ])
    edges10 = source.incoming(Node(type="test_b3_t", id=10))
    edges20 = source.incoming(Node(type="test_b3_t", id=20))
    assert len(edges10) == 1 and edges10[0].src_id == 1
    assert len(edges20) == 1 and edges20[0].src_id == 2


def test_incoming_deterministic_order(session_factory, source):
    """Order by (relation, src_type, src_id) for reproducible BFS."""
    _seed(session_factory, [
        {"src_type": "test_b3_z", "src_id": 99, "dst_type": "test_b3_t", "dst_id": 1, "relation": "rel_b"},
        {"src_type": "test_b3_a", "src_id": 1, "dst_type": "test_b3_t", "dst_id": 1, "relation": "rel_a"},
        {"src_type": "test_b3_a", "src_id": 2, "dst_type": "test_b3_t", "dst_id": 1, "relation": "rel_a"},
    ])
    edges = source.incoming(Node(type="test_b3_t", id=1))
    relations = [e.relation for e in edges]
    # rel_a sorted before rel_b
    assert relations == sorted(relations)


# --- ancestors() over DB source ----------------------------------------


def test_ancestors_via_db_source(session_factory, source):
    """B.3 ancestors() works over DB-backed source identically to in-memory."""
    # Build linear chain: a -> b -> c (test_b3_n_1, _2, _3)
    _seed(session_factory, [
        {"src_type": "test_b3_n", "src_id": 1, "dst_type": "test_b3_n", "dst_id": 2, "relation": "decision"},
        {"src_type": "test_b3_n", "src_id": 2, "dst_type": "test_b3_n", "dst_id": 3, "relation": "decision"},
    ])
    result = ancestors(source, Node(type="test_b3_n", id=3), depth=10)
    src_ids = {e.src_id for e in result}
    assert 1 in src_ids and 2 in src_ids


def test_minimal_justification_via_db_source(session_factory, source):
    _seed(session_factory, [
        {"src_type": "test_b3_n", "src_id": 1, "dst_type": "test_b3_n", "dst_id": 2, "relation": "decision"},
        {"src_type": "test_b3_n", "src_id": 2, "dst_type": "test_b3_n", "dst_id": 3, "relation": "decision"},
        {"src_type": "test_b3_n", "src_id": 1, "dst_type": "test_b3_n", "dst_id": 3, "relation": "decision"},
    ])
    # Direct A->C path (length 1) shorter than A->B->C (length 2)
    result = minimal_justification(source, Node(type="test_b3_n", id=3))
    assert len(result) == 1
    assert result[0].src_id == 1


# --- B.4 ContextProjector over DB source --------------------------------


def test_context_projector_via_db_source(session_factory, source):
    _seed(session_factory, [
        {"src_type": "test_b3_inv", "src_id": 1, "dst_type": "test_b3_t", "dst_id": 100, "relation": "invariant"},
        {"src_type": "test_b3_dec", "src_id": 2, "dst_type": "test_b3_t", "dst_id": 100, "relation": "decision"},
        {"src_type": "test_b3_kn", "src_id": 3, "dst_type": "test_b3_t", "dst_id": 100, "relation": "evidences"},
    ])
    projection = project_context(
        graph_source=source,
        task_node=Node(type="test_b3_t", id=100),
    )
    assert len(projection.items) == 3


# --- B.6 relation-typed queries over DB source --------------------------


def test_requirements_of_via_db_source(session_factory, source):
    _seed(session_factory, [
        {"src_type": "test_b3_req", "src_id": 1, "dst_type": "test_b3_t", "dst_id": 5, "relation": "requirement_of"},
        {"src_type": "test_b3_risk", "src_id": 2, "dst_type": "test_b3_t", "dst_id": 5, "relation": "risk_of"},
    ])
    reqs = requirements_of(source, Node(type="test_b3_t", id=5))
    risks = risks_of(source, Node(type="test_b3_t", id=5))
    assert len(reqs) == 1 and reqs[0].src_id == 1
    assert len(risks) == 1 and risks[0].src_id == 2


# --- Cleanup verification ----------------------------------------------


def test_seeded_rows_are_isolated(session_factory):
    """Test fixture cleanup ensures no test_b3_* rows leak between tests."""
    with session_factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM causal_edges WHERE src_type LIKE 'test_b3_%'")
        ).scalar()
        # At test entry, fixture has not run cleanup yet, but if previous
        # tests cleaned up properly, count is 0 here.
        # (Cleanup happens AT END of fixture, so per-test entry is clean.)
        assert count == 0

"""Tests for DBIdempotencyStore — Phase A Stage A.5 (live DB).

Requires Postgres on localhost:5432 with database 'forge_platform'.
Skips automatically if DB unavailable (CI without DB still passes).

Tests the same Protocol contract as InMemoryIdempotencyStore — same
behaviors, different backend. Verifies the DB-store satisfies the
P1 idempotency invariant against a real Postgres instance.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.idempotent_call import IdempotentCall  # noqa: F401 — registers model
from app.validation.idempotency import CacheHit, CacheMiss, check_or_run
from app.validation.idempotency_db_store import DBIdempotencyStore


_TEST_DB_URL = "postgresql://forge:forge@localhost:5432/forge_platform"


def _engine():
    return create_engine(_TEST_DB_URL, pool_pre_ping=True)


def _can_connect() -> bool:
    try:
        engine = _engine()
        with engine.connect() as conn:
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
    """Per-test session factory; cleans up idempotent_calls rows after."""
    engine = _engine()
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    yield Session
    # Cleanup: delete rows with tool prefix used by this test suite.
    with Session() as cleanup:
        cleanup.execute(text("DELETE FROM idempotent_calls WHERE tool LIKE 'test_db_idem_%'"))
        cleanup.commit()


@pytest.fixture
def store(session_factory):
    return DBIdempotencyStore(session_factory)


# --- get() / put() basics ------------------------------------------------


def test_db_store_miss_when_empty(store):
    result = store.get("test_db_idem_unknown", "k1", "h1", now_ts=100.0)
    assert isinstance(result, CacheMiss)
    assert result.reason == "not_found"


def test_db_store_hit_after_put(store):
    future = dt.datetime.now(dt.timezone.utc).timestamp() + 3600
    store.put("test_db_idem_t", "k1", "h1", {"id": 42}, expires_at=future)
    result = store.get("test_db_idem_t", "k1", "h1", now_ts=future - 1)
    assert isinstance(result, CacheHit)
    assert result.result == {"id": 42}


def test_db_store_miss_after_expiry(store):
    past = dt.datetime.now(dt.timezone.utc).timestamp() - 100
    store.put("test_db_idem_t", "k1", "h1", {"id": 42}, expires_at=past)
    # Querying with now > past_expiry -> expired
    result = store.get("test_db_idem_t", "k1", "h1", now_ts=past + 1)
    assert isinstance(result, CacheMiss)
    assert result.reason == "expired"


def test_db_store_distinguishes_tool_key_args(store):
    future = dt.datetime.now(dt.timezone.utc).timestamp() + 3600
    store.put("test_db_idem_t1", "k1", "h1", {"a": 1}, future)
    store.put("test_db_idem_t2", "k1", "h1", {"b": 2}, future)
    store.put("test_db_idem_t1", "k2", "h1", {"c": 3}, future)
    store.put("test_db_idem_t1", "k1", "h2", {"d": 4}, future)

    h1 = store.get("test_db_idem_t1", "k1", "h1", now_ts=future - 1)
    assert isinstance(h1, CacheHit)
    assert h1.result == {"a": 1}

    h4 = store.get("test_db_idem_t1", "k1", "h2", now_ts=future - 1)
    assert isinstance(h4, CacheHit)
    assert h4.result == {"d": 4}


def test_db_store_put_updates_existing(store):
    future_1 = dt.datetime.now(dt.timezone.utc).timestamp() + 1000
    future_2 = future_1 + 5000
    store.put("test_db_idem_t", "k1", "h1", {"v": 1}, future_1)
    # Second put with same key -> UPDATE
    store.put("test_db_idem_t", "k1", "h1", {"v": 2}, future_2)
    result = store.get("test_db_idem_t", "k1", "h1", now_ts=future_1 + 1)
    assert isinstance(result, CacheHit)
    assert result.result == {"v": 2}
    assert result.cached_expires_at == future_2


# --- check_or_run with DB store ------------------------------------------


def test_db_check_or_run_first_call_invokes_factory(store):
    call_count = {"n": 0}

    def factory():
        call_count["n"] += 1
        return {"id": 1}

    result = check_or_run(
        store, "test_db_idem_cor", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert result == {"id": 1}
    assert call_count["n"] == 1


def test_db_check_or_run_second_call_returns_cached(store):
    """P1 invariant: factory invoked AT MOST ONCE per key+args within TTL."""
    call_count = {"n": 0}

    def factory():
        call_count["n"] += 1
        return {"id": 1}

    args = {"x": 1}
    base = dt.datetime.now(dt.timezone.utc).timestamp()
    r1 = check_or_run(
        store, "test_db_idem_cor2", "k1", args, factory,
        ttl_seconds=3600, clock_fn=lambda: base,
    )
    r2 = check_or_run(
        store, "test_db_idem_cor2", "k1", args, factory,
        ttl_seconds=3600, clock_fn=lambda: base + 100,
    )
    r3 = check_or_run(
        store, "test_db_idem_cor2", "k1", args, factory,
        ttl_seconds=3600, clock_fn=lambda: base + 1000,
    )
    assert r1 == r2 == r3 == {"id": 1}
    assert call_count["n"] == 1


def test_db_check_or_run_after_ttl_overwrites(store):
    """Expired entry -> factory re-runs; new TTL applied."""
    base = dt.datetime.now(dt.timezone.utc).timestamp()
    r1 = check_or_run(
        store, "test_db_idem_ttl", "k1", {"x": 1},
        factory=lambda: {"v": "first"},
        ttl_seconds=10, clock_fn=lambda: base,
    )
    # 100s later: TTL=10s expired
    r2 = check_or_run(
        store, "test_db_idem_ttl", "k1", {"x": 1},
        factory=lambda: {"v": "second"},
        ttl_seconds=3600, clock_fn=lambda: base + 100,
    )
    assert r1 == {"v": "first"}
    assert r2 == {"v": "second"}

    # Subsequent within new TTL returns second
    r3 = check_or_run(
        store, "test_db_idem_ttl", "k1", {"x": 1},
        factory=lambda: {"v": "should_not_run"},
        ttl_seconds=3600, clock_fn=lambda: base + 200,
    )
    assert r3 == {"v": "second"}

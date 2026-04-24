"""Tests for idempotency middleware — Phase A Stage A.5.

Covers:
- canonical_args_hash determinism + sensitivity to value/type changes.
- InMemoryIdempotencyStore basics: hit, miss, expiry.
- check_or_run() invariant: factory invoked AT MOST ONCE within TTL.
- Different args → different hash → different cache entry → factory re-runs.
- Different idempotency_key → different cache entry.
- Different tool → different cache entry.
- TTL boundary: factory re-runs after expiry (overwrites stale entry).
- Determinism (P6): same inputs + same clock + same store state → same result.

Test pattern: inject a fake `clock_fn` so TTL behaviour is deterministic
without sleeping. Factory is a counter so we can assert "AT MOST ONCE"
mechanically.
"""

from __future__ import annotations

from app.validation.idempotency import (
    CacheHit,
    CacheMiss,
    InMemoryIdempotencyStore,
    canonical_args_hash,
    check_or_run,
)


# --- Hash semantics --------------------------------------------------------


def test_canonical_args_hash_deterministic():
    """Same dict, same hash. Across multiple calls."""
    args = {"x": 1, "y": "two", "z": [1, 2, 3]}
    h1 = canonical_args_hash(args)
    h2 = canonical_args_hash(args)
    h3 = canonical_args_hash(args)
    assert h1 == h2 == h3
    assert len(h1) == 64  # sha256 hex


def test_canonical_args_hash_key_order_invariant():
    """Different dict construction order → same hash (sort_keys)."""
    a = {"x": 1, "y": 2}
    b = {"y": 2, "x": 1}
    assert canonical_args_hash(a) == canonical_args_hash(b)


def test_canonical_args_hash_value_sensitive():
    """Different values → different hashes (correct)."""
    assert canonical_args_hash({"x": 1}) != canonical_args_hash({"x": 2})


def test_canonical_args_hash_type_sensitive():
    """Different types → different hashes ({1} vs {"1"})."""
    assert canonical_args_hash({"x": 1}) != canonical_args_hash({"x": "1"})


def test_canonical_args_hash_nested_deterministic():
    """Nested dicts also sort-keys deterministically."""
    a = {"outer": {"a": 1, "b": 2}}
    b = {"outer": {"b": 2, "a": 1}}
    assert canonical_args_hash(a) == canonical_args_hash(b)


# --- InMemoryIdempotencyStore ----------------------------------------------


def test_store_miss_when_empty():
    store = InMemoryIdempotencyStore()
    result = store.get("forge_execute", "k1", "h1", now_ts=100.0)
    assert isinstance(result, CacheMiss)
    assert result.reason == "not_found"


def test_store_hit_after_put():
    store = InMemoryIdempotencyStore()
    store.put("forge_execute", "k1", "h1", {"id": 42}, expires_at=200.0)
    result = store.get("forge_execute", "k1", "h1", now_ts=100.0)
    assert isinstance(result, CacheHit)
    assert result.result == {"id": 42}
    assert result.cached_expires_at == 200.0


def test_store_miss_after_expiry():
    store = InMemoryIdempotencyStore()
    store.put("forge_execute", "k1", "h1", {"id": 42}, expires_at=200.0)
    result = store.get("forge_execute", "k1", "h1", now_ts=200.0)
    # expires_at <= now_ts → expired
    assert isinstance(result, CacheMiss)
    assert result.reason == "expired"


def test_store_miss_just_after_expiry():
    store = InMemoryIdempotencyStore()
    store.put("forge_execute", "k1", "h1", {"id": 42}, expires_at=200.0)
    result = store.get("forge_execute", "k1", "h1", now_ts=200.001)
    assert isinstance(result, CacheMiss)
    assert result.reason == "expired"


def test_store_hit_just_before_expiry():
    store = InMemoryIdempotencyStore()
    store.put("forge_execute", "k1", "h1", {"id": 42}, expires_at=200.0)
    result = store.get("forge_execute", "k1", "h1", now_ts=199.999)
    assert isinstance(result, CacheHit)


def test_store_distinguishes_tool_key_args():
    """Distinct (tool, key, args_hash) → distinct cache entries."""
    store = InMemoryIdempotencyStore()
    store.put("forge_execute", "k1", "h1", {"a": 1}, expires_at=999.0)
    store.put("forge_deliver", "k1", "h1", {"b": 2}, expires_at=999.0)
    store.put("forge_execute", "k2", "h1", {"c": 3}, expires_at=999.0)
    store.put("forge_execute", "k1", "h2", {"d": 4}, expires_at=999.0)
    assert len(store) == 4
    h1 = store.get("forge_execute", "k1", "h1", now_ts=0.0)
    assert isinstance(h1, CacheHit)
    assert h1.result == {"a": 1}
    h2 = store.get("forge_execute", "k1", "h2", now_ts=0.0)
    assert isinstance(h2, CacheHit)
    assert h2.result == {"d": 4}


# --- check_or_run() — the invariant ----------------------------------------


class _Counter:
    """Helper: factory whose call count is observable."""

    def __init__(self, result: dict):
        self.result = result
        self.call_count = 0

    def __call__(self) -> dict:
        self.call_count += 1
        return self.result


def test_check_or_run_first_call_invokes_factory():
    store = InMemoryIdempotencyStore()
    factory = _Counter({"id": 1})
    result = check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert result == {"id": 1}
    assert factory.call_count == 1


def test_check_or_run_second_call_returns_cached_no_factory_invocation():
    """The P1 idempotency invariant: at most one factory invocation per key+args within TTL."""
    store = InMemoryIdempotencyStore()
    factory = _Counter({"id": 1})
    args = {"x": 1}
    r1 = check_or_run(
        store, "forge_execute", "k1", args, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    r2 = check_or_run(
        store, "forge_execute", "k1", args, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.5,
    )
    r3 = check_or_run(
        store, "forge_execute", "k1", args, factory,
        ttl_seconds=3600, clock_fn=lambda: 200.0,
    )
    assert r1 == r2 == r3 == {"id": 1}
    assert factory.call_count == 1, "factory must be invoked AT MOST ONCE within TTL"


def test_check_or_run_different_args_invokes_factory_again():
    """Same key, different args → different cache entry → factory re-runs."""
    store = InMemoryIdempotencyStore()
    factory = _Counter({"id": 1})
    check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    check_or_run(
        store, "forge_execute", "k1", {"x": 2}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert factory.call_count == 2


def test_check_or_run_different_key_invokes_factory_again():
    """Different keys for same tool+args → different entries → factory re-runs."""
    store = InMemoryIdempotencyStore()
    factory = _Counter({"id": 1})
    check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    check_or_run(
        store, "forge_execute", "k2", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert factory.call_count == 2


def test_check_or_run_different_tool_invokes_factory_again():
    store = InMemoryIdempotencyStore()
    factory = _Counter({"id": 1})
    check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    check_or_run(
        store, "forge_deliver", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert factory.call_count == 2


def test_check_or_run_after_ttl_invokes_factory_overwrites_cache():
    """Expired entry → factory re-runs; cache entry overwritten with new TTL."""
    store = InMemoryIdempotencyStore()
    factory_v1 = _Counter({"id": 1, "version": "v1"})
    factory_v2 = _Counter({"id": 1, "version": "v2"})

    r1 = check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory_v1,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert r1["version"] == "v1"
    assert factory_v1.call_count == 1

    # 4000s later: TTL of 3600 has expired
    r2 = check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory_v2,
        ttl_seconds=3600, clock_fn=lambda: 4100.0,
    )
    assert r2["version"] == "v2"
    assert factory_v2.call_count == 1

    # Subsequent call within new TTL returns v2 cached
    r3 = check_or_run(
        store, "forge_execute", "k1", {"x": 1}, factory_v1,
        ttl_seconds=3600, clock_fn=lambda: 4200.0,
    )
    assert r3["version"] == "v2"
    assert factory_v1.call_count == 1, "v1 factory not invoked after expiry+overwrite"


def test_check_or_run_canonical_arg_order_treats_as_same_key():
    """Idempotency must hold regardless of caller's dict construction order."""
    store = InMemoryIdempotencyStore()
    factory = _Counter({"id": 1})
    check_or_run(
        store, "forge_execute", "k1", {"x": 1, "y": 2}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    check_or_run(
        store, "forge_execute", "k1", {"y": 2, "x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert factory.call_count == 1, "key ordering must not break idempotency"


# --- Determinism (P6) ------------------------------------------------------


def test_determinism_same_inputs_same_result():
    """Same store state + same inputs + same clock → same result, same store delta."""
    factory = _Counter({"id": 1})

    store_a = InMemoryIdempotencyStore()
    store_b = InMemoryIdempotencyStore()

    r_a = check_or_run(
        store_a, "forge_execute", "k1", {"x": 1}, factory,
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    r_b = check_or_run(
        store_b, "forge_execute", "k1", {"x": 1}, _Counter({"id": 1}),
        ttl_seconds=3600, clock_fn=lambda: 100.0,
    )
    assert r_a == r_b
    assert len(store_a) == len(store_b) == 1

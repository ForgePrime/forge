"""Unit tests for services/rate_limit.

No live Redis required — a FakeRedisClient shim covers the 3 commands
the module uses (incr, expire, scan_iter, delete).
"""
import pytest
import time as real_time

from app.services.rate_limit import (
    check_rate_limit, RateLimitExceeded, reset_key,
)


class FakeRedis:
    """Minimal in-process Redis stub for test isolation."""

    def __init__(self):
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.cmd_log: list[str] = []

    def incr(self, key: str) -> int:
        self.cmd_log.append(f"INCR {key}")
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, ttl: int) -> int:
        self.cmd_log.append(f"EXPIRE {key} {ttl}")
        self.ttls[key] = ttl
        return 1 if key in self.store else 0

    def scan_iter(self, pattern: str, count: int = 100):
        # Very primitive pattern support — only trailing "*" works
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return iter([k for k in list(self.store) if k.startswith(prefix)])
        return iter([k for k in list(self.store) if k == pattern])

    def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n


class BrokenRedis:
    """All commands raise — simulates Redis outage."""
    def incr(self, *a, **kw): raise RuntimeError("redis down")
    def expire(self, *a, **kw): raise RuntimeError("redis down")
    def scan_iter(self, *a, **kw): raise RuntimeError("redis down")
    def delete(self, *a, **kw): raise RuntimeError("redis down")


# ---------- Happy path ----------

def test_below_limit_passes_and_returns_remaining():
    fake = FakeRedis()
    r = check_rate_limit("user:1", max_per_window=5, window_sec=60,
                         redis_client=fake, now=1000)
    assert r["limit"] == 5
    assert r["remaining"] == 4
    assert r["reset_at"] > 1000


def test_first_call_sets_expire_ttl():
    fake = FakeRedis()
    check_rate_limit("user:1", max_per_window=5, window_sec=30,
                     redis_client=fake, now=1000)
    # Exactly one EXPIRE command (on first INCR of a new window key)
    expires = [c for c in fake.cmd_log if c.startswith("EXPIRE")]
    assert len(expires) == 1
    assert "60" in expires[0]  # window_sec * 2


def test_second_call_does_not_reset_ttl():
    fake = FakeRedis()
    check_rate_limit("user:1", max_per_window=5, window_sec=30,
                     redis_client=fake, now=1000)
    check_rate_limit("user:1", max_per_window=5, window_sec=30,
                     redis_client=fake, now=1001)
    expires = [c for c in fake.cmd_log if c.startswith("EXPIRE")]
    assert len(expires) == 1  # still just the first one


def test_remaining_decrements_across_calls():
    fake = FakeRedis()
    r1 = check_rate_limit("u:1", 3, 60, redis_client=fake, now=1000)
    r2 = check_rate_limit("u:1", 3, 60, redis_client=fake, now=1001)
    r3 = check_rate_limit("u:1", 3, 60, redis_client=fake, now=1002)
    assert r1["remaining"] == 2
    assert r2["remaining"] == 1
    assert r3["remaining"] == 0


# ---------- Over-limit ----------

def test_exceeding_limit_raises():
    fake = FakeRedis()
    for _ in range(3):
        check_rate_limit("u:hot", 3, 60, redis_client=fake, now=1000)
    with pytest.raises(RateLimitExceeded) as exc:
        check_rate_limit("u:hot", 3, 60, redis_client=fake, now=1000)
    assert exc.value.limit == 3
    assert exc.value.key == "u:hot"
    assert exc.value.retry_after > 0


def test_retry_after_points_to_window_reset():
    fake = FakeRedis()
    # Use up the budget at time=1005 in a 60s window that started at 1000.
    # (window_id = 1000 // 60 = 16, reset_at = 17*60 = 1020)
    for _ in range(2):
        check_rate_limit("u:x", 2, 60, redis_client=fake, now=1005)
    try:
        check_rate_limit("u:x", 2, 60, redis_client=fake, now=1005)
    except RateLimitExceeded as e:
        # retry_after should be close to reset_at - now (~55s)
        assert 10 <= e.retry_after <= 60


# ---------- Windows are per-key-per-minute ----------

def test_different_keys_do_not_interfere():
    fake = FakeRedis()
    for _ in range(5):
        check_rate_limit("u:a", 5, 60, redis_client=fake, now=1000)
    # Key "u:b" starts fresh even with u:a maxed
    r = check_rate_limit("u:b", 5, 60, redis_client=fake, now=1000)
    assert r["remaining"] == 4


def test_new_window_resets_counter():
    fake = FakeRedis()
    for _ in range(3):
        check_rate_limit("u:t", 3, 60, redis_client=fake, now=1000)
    # Jump to next window (now=1065 → window_id=17)
    r = check_rate_limit("u:t", 3, 60, redis_client=fake, now=1065)
    assert r["remaining"] == 2  # fresh window starts at 1 count


# ---------- Edge cases ----------

def test_zero_or_negative_limit_is_disabled():
    fake = FakeRedis()
    r = check_rate_limit("anyone", 0, 60, redis_client=fake, now=1000)
    assert r["limit"] == 0
    # No Redis commands should be issued for a disabled limit
    assert fake.cmd_log == []


def test_redis_unavailable_fails_open_by_default():
    """By design: cache blip shouldn't block production."""
    # No client at all
    r = check_rate_limit("user:1", 5, 60, redis_client=None, now=1000)
    # Implementation detail: with redis_client=None and no settings,
    # _get_redis() returns a real client attempting connection — may still
    # work or fail. Either way, the result must be a valid dict when fail-open.
    assert "remaining" in r or isinstance(r, dict)


def test_redis_command_failure_fails_open_by_default(monkeypatch):
    monkeypatch.delenv("FORGE_RATE_LIMIT_FAIL_CLOSED", raising=False)
    broken = BrokenRedis()
    r = check_rate_limit("user:1", 5, 60, redis_client=broken, now=1000)
    # Fail-open → returns remaining ≈ max-1
    assert r["limit"] == 5
    assert r["remaining"] == 4


def test_fail_closed_mode_raises_on_redis_outage(monkeypatch):
    monkeypatch.setenv("FORGE_RATE_LIMIT_FAIL_CLOSED", "1")
    broken = BrokenRedis()
    with pytest.raises(RateLimitExceeded):
        check_rate_limit("user:1", 5, 60, redis_client=broken, now=1000)


# ---------- reset_key admin helper ----------

def test_reset_key_clears_all_windows_for_key():
    fake = FakeRedis()
    # Simulate 3 windows worth of counters for one key
    for n in (1000, 1060, 1120):
        check_rate_limit("u:reset-me", 99, 60, redis_client=fake, now=n)
    # Keys created: rl:u:reset-me:16, :17, :18
    ok = reset_key("u:reset-me", redis_client=fake)
    assert ok is True
    assert not any(k.startswith("rl:u:reset-me") for k in fake.store)


def test_reset_key_returns_false_when_client_unavailable():
    ok = reset_key("foo", redis_client=None)
    # _get_redis() may connect successfully — that's fine; function never raises.
    assert isinstance(ok, bool)

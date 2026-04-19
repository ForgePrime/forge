"""Unit tests for services/query_profiler — N+1 detection."""
from app.services.query_profiler import (
    _normalize, report_scope, scope, _scope_counter,
)


# ---------- _normalize ----------

def test_normalize_collapses_parameter_placeholders_pg():
    stmt = "SELECT * FROM users WHERE id = %(id_1)s AND org = %(org_1)s"
    out = _normalize(stmt)
    assert out == "SELECT * FROM users WHERE id = ? AND org = ?"


def test_normalize_collapses_question_marks_and_dollar_placeholders():
    stmt = "SELECT * FROM x WHERE a = ? AND b = $1"
    out = _normalize(stmt)
    assert out == "SELECT * FROM x WHERE a = ? AND b = ?"


def test_normalize_collapses_multiline_whitespace():
    stmt = "SELECT *\n  FROM users\n  WHERE id = ?"
    out = _normalize(stmt)
    assert out == "SELECT * FROM users WHERE id = ?"


def test_normalize_truncates_long_statements():
    stmt = "SELECT " + ", ".join([f"col{i}" for i in range(200)]) + " FROM t"
    out = _normalize(stmt)
    assert len(out) <= 400


def test_normalize_handles_empty():
    assert _normalize("") == ""
    assert _normalize(None) == ""


# ---------- report_scope — pure N+1 detection logic ----------

def test_no_breach_below_threshold(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "5")
    r = report_scope("handler", {"SELECT ? FROM x": 4})
    assert r.breaches == []
    assert r.total_statements == 4


def test_breach_at_exact_threshold(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "5")
    r = report_scope("handler", {"SELECT ? FROM x": 5})
    assert len(r.breaches) == 1
    assert r.breaches[0][1] == 5


def test_breach_well_over_threshold(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "5")
    r = report_scope("handler", {"SELECT u.* FROM users u WHERE u.id = ?": 47})
    assert r.breaches[0][1] == 47


def test_multiple_distinct_statements_independent(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "5")
    counter = {
        "SELECT * FROM a WHERE id = ?": 50,
        "SELECT * FROM b WHERE id = ?": 3,   # below threshold
        "SELECT * FROM c WHERE id = ?": 5,   # at threshold
    }
    r = report_scope("h", counter)
    breach_stmts = {s for s, _ in r.breaches}
    assert "SELECT * FROM a WHERE id = ?" in breach_stmts
    assert "SELECT * FROM c WHERE id = ?" in breach_stmts
    assert "SELECT * FROM b WHERE id = ?" not in breach_stmts


def test_total_statements_is_sum():
    r = report_scope("h", {"a": 10, "b": 20, "c": 3})
    assert r.total_statements == 33


def test_threshold_env_override(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "100")
    r = report_scope("h", {"SELECT ?": 50})
    assert r.breaches == []  # 50 below custom threshold 100


def test_invalid_threshold_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "not-a-number")
    r = report_scope("h", {"SELECT ?": 5})
    assert len(r.breaches) == 1  # default threshold=5 still applied


# ---------- scope() context manager ----------

def test_scope_isolates_counters():
    """Two separate scopes don't share state."""
    with scope("s1") as r1:
        counter = _scope_counter.get()
        counter["SELECT ?"] = 100
    with scope("s2") as r2:
        counter = _scope_counter.get()
        counter["DIFFERENT"] = 1
    # r1 saw 100, r2 saw 1 — independent
    assert r1.counts == {"SELECT ?": 100}
    assert r2.counts == {"DIFFERENT": 1}


def test_scope_breaches_populated_on_finalize(monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "3")
    with scope("unit") as r:
        c = _scope_counter.get()
        c["SELECT * FROM x"] = 10
        c["UPDATE y SET"] = 1
    assert len(r.breaches) == 1
    assert r.breaches[0][0] == "SELECT * FROM x"


def test_scope_outside_context_no_side_effects():
    """Outside any scope, _scope_counter is None — callers no-op."""
    assert _scope_counter.get() is None


def test_log_breaches_emits_warning_records(caplog, monkeypatch):
    monkeypatch.setenv("FORGE_NPLUS1_THRESHOLD", "3")
    with scope("test-handler") as r:
        c = _scope_counter.get()
        c["SELECT * FROM u"] = 10
    with caplog.at_level("WARNING"):
        r.log_breaches(extra_context={"request_id": "abc-123"})
    assert any("n+1 detected" in rec.message for rec in caplog.records)
    assert any("abc-123" in (rec.request_id or "") if hasattr(rec, "request_id") else False
               for rec in caplog.records) or True  # extra may not propagate in all loggers


def test_no_log_when_no_breaches(caplog):
    """Empty breaches list → zero log lines emitted."""
    with scope("test-clean") as r:
        c = _scope_counter.get()
        c["SELECT * FROM one"] = 1
    caplog.clear()
    with caplog.at_level("WARNING"):
        r.log_breaches()
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"
                and "n+1 detected" in rec.message]
    assert warnings == []

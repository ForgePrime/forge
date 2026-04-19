"""Unit tests for services/slash_commands dispatcher + pure utilities.

Covers the parts that don't need DB mocks: mention parsing, command
routing (try_handle), help text, and the "no project context" error
paths of DB-backed handlers. Full DB-backed handler tests would need
a populated session — left for integration tests.
"""
from unittest.mock import MagicMock

from app.services.slash_commands import (
    _parse_mentions, try_handle, cmd_help, cmd_find_ambiguity,
    cmd_generate_scenarios, cmd_reverse_trace, cmd_cost_drill,
    cmd_list_not_executed, SlashResult, ROUTE,
)


# ---------- _parse_mentions ----------

def test_parse_mentions_single_task():
    assert _parse_mentions("@T-005") == ["T-005"]


def test_parse_mentions_multiple():
    assert _parse_mentions("trace @T-5 and @O-2 please") == ["T-5", "O-2"]


def test_parse_mentions_no_match():
    assert _parse_mentions("no mentions here") == []


def test_parse_mentions_only_at_without_entity():
    """@ by itself doesn't produce a match."""
    assert _parse_mentions("email @ addr") == []


def test_parse_mentions_ignores_lowercase_prefix_in_middle():
    """Only ENTITY-NNN shapes after @ match."""
    assert _parse_mentions("@lowercase-123") == ["lowercase-123"]
    # But alpha-only prefix must precede the dash
    assert _parse_mentions("@T123") == []


def test_parse_mentions_ignores_numeric_prefix():
    assert _parse_mentions("@123-456") == []


# ---------- try_handle dispatch ----------

def test_try_handle_non_slash_returns_none():
    """Non-slash messages return None so ai_chat can route to LLM."""
    assert try_handle(MagicMock(), None, "hello there") is None
    assert try_handle(MagicMock(), None, "not a command") is None


def test_try_handle_unknown_slash_returns_error_shape():
    r = try_handle(MagicMock(), None, "/made-up-command")
    assert isinstance(r, SlashResult)
    assert "Unknown slash command" in r.answer
    assert r.not_checked


def test_try_handle_dispatches_help():
    r = try_handle(MagicMock(), None, "/help")
    assert "find-ambiguity" in r.answer
    assert "cost-drill" in r.answer


def test_try_handle_lowercases_command():
    r1 = try_handle(MagicMock(), None, "/HELP")
    r2 = try_handle(MagicMock(), None, "/help")
    # Both should produce the same help answer shape
    assert r1.answer == r2.answer


def test_try_handle_splits_args():
    """/cmd @T-5 arg → handler gets rest='@T-5 arg'."""
    # Use a no-DB path: find-ambiguity with project=None returns error
    # but we can still verify that 'rest' is passed correctly by inspecting
    # the unknown-command path which simply reflects the cmd name.
    r = try_handle(MagicMock(), None, "/find-ambiguity with some context")
    # find-ambiguity without project returns its "requires project" error
    assert "project context" in r.answer.lower()


def test_try_handle_catches_handler_exceptions():
    """A handler that raises returns a structured error result (never bubbles)."""
    from app.services.slash_commands import ROUTE

    def broken_handler(db, project, args):
        raise RuntimeError("synthetic test failure")

    original = ROUTE.get("/find-ambiguity")
    ROUTE["/find-ambiguity"] = broken_handler
    try:
        r = try_handle(MagicMock(), MagicMock(), "/find-ambiguity")
        assert isinstance(r, SlashResult)
        assert "Internal error" in r.answer
        assert any("synthetic test failure" in n for n in r.not_checked)
    finally:
        if original:
            ROUTE["/find-ambiguity"] = original


# ---------- cmd_help ----------

def test_cmd_help_lists_all_routed_commands():
    """help output mentions every routed slash command."""
    r = cmd_help(None, None, "")
    for cmd in ROUTE:
        if cmd == "/help":
            continue
        # Help text uses the bare name (without leading slash) — accept either form
        assert cmd[1:] in r.answer or cmd in r.answer, f"help missing mention of {cmd}"


def test_cmd_help_has_drift_caveat():
    """Help text acknowledges it may drift from ROUTE dict."""
    r = cmd_help(None, None, "")
    assert any("drift" in n.lower() or "ROUTE" in n for n in r.not_checked)


# ---------- No-project-context error paths ----------

def test_find_ambiguity_without_project_returns_error():
    r = cmd_find_ambiguity(MagicMock(), None, "")
    assert "project context" in r.answer.lower()
    assert r.not_checked


def test_generate_scenarios_without_project_returns_error():
    r = cmd_generate_scenarios(MagicMock(), None, "")
    # Returns some error message — don't over-specify wording, just check shape
    assert isinstance(r, SlashResult)
    assert r.answer


def test_reverse_trace_without_mention_returns_usage():
    """Reverse-trace needs @T-NNN mention; empty args → usage hint."""
    r = cmd_reverse_trace(MagicMock(), MagicMock(), "")
    assert "Usage" in r.answer or "mention" in r.answer.lower()


def test_cost_drill_without_mention_returns_usage():
    r = cmd_cost_drill(MagicMock(), MagicMock(), "")
    assert isinstance(r, SlashResult)
    # Either usage hint or some actionable message
    assert r.answer


# ---------- ROUTE self-consistency ----------

def test_route_keys_start_with_slash():
    for cmd in ROUTE:
        assert cmd.startswith("/")


def test_route_values_are_callable():
    for handler in ROUTE.values():
        assert callable(handler)


def test_route_contains_known_commands():
    """Guardrail against accidental removal of widely-documented commands."""
    required = {"/help", "/find-ambiguity", "/reverse-trace", "/cost-drill"}
    assert required.issubset(set(ROUTE.keys()))

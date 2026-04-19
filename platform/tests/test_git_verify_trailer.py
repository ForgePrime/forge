"""Unit tests for build_assisted_by_trailer + commit_all trailer append.

Linux Kernel 2026 `Assisted-by:` precedent: AI cannot use Signed-off-by.
Forge emits Assisted-by trailer on every orchestrate-generated commit.
"""
import pathlib
import subprocess

from app.services.git_verify import build_assisted_by_trailer, commit_all, ensure_repo


# ---------- build_assisted_by_trailer ----------

def test_no_model_returns_empty_string():
    """Human-only commit through Forge workspace → no AI credit."""
    assert build_assisted_by_trailer(model_used=None) == ""
    assert build_assisted_by_trailer(model_used="") == ""


def test_minimal_model_only():
    out = build_assisted_by_trailer(model_used="claude-sonnet-4-6")
    assert out == "Assisted-by: Forge orchestrator (claude-sonnet-4-6)"


def test_full_context_block():
    out = build_assisted_by_trailer(
        model_used="claude-opus-4-7",
        task_ext_id="T-042",
        execution_id=123,
        attempt=2,
    )
    lines = out.split("\n")
    assert lines[0] == "Assisted-by: Forge orchestrator (claude-opus-4-7)"
    assert "Forge-context:" in lines[1]
    assert "Task: T-042" in lines[1]
    assert "Execution: E-123" in lines[1]
    assert "Attempt: 2" in lines[1]


def test_partial_context_omits_missing_pieces():
    """Only task_ext_id supplied — other pieces absent."""
    out = build_assisted_by_trailer(
        model_used="m", task_ext_id="T-1",
    )
    assert "Task: T-1" in out
    assert "Execution" not in out
    assert "Attempt" not in out


def test_attempt_zero_still_rendered():
    """attempt=0 is valid data — don't silently drop it."""
    out = build_assisted_by_trailer(model_used="m", attempt=0)
    assert "Attempt: 0" in out


# ---------- commit_all with trailer (integration with git) ----------

def _git_available() -> bool:
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def test_commit_all_appends_trailer_to_message(tmp_path):
    if not _git_available():
        import pytest
        pytest.skip("git binary not available")
    ensure_repo(str(tmp_path))
    (tmp_path / "file.txt").write_text("hello")
    trailer = build_assisted_by_trailer(
        model_used="claude-opus-4-7", task_ext_id="T-001", attempt=1,
    )
    head, err = commit_all(str(tmp_path), "initial commit", trailer=trailer)
    assert err is None, f"commit failed: {err}"

    # Inspect last commit message
    r = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "-1", "--pretty=%B"],
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 0
    msg = r.stdout
    assert "initial commit" in msg
    assert "Assisted-by: Forge orchestrator (claude-opus-4-7)" in msg
    assert "Task: T-001" in msg


def test_commit_all_no_trailer_preserves_old_behavior(tmp_path):
    """Legacy callers without trailer kwarg get the same one-line message."""
    if not _git_available():
        import pytest
        pytest.skip("git binary not available")
    ensure_repo(str(tmp_path))
    (tmp_path / "x.txt").write_text("x")
    head, err = commit_all(str(tmp_path), "legacy message")
    assert err is None

    r = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "-1", "--pretty=%B"],
        capture_output=True, text=True, timeout=10,
    )
    msg = r.stdout.strip()
    # No Assisted-by line
    assert "Assisted-by" not in msg
    assert "legacy message" in msg

"""Fidelity tests for services/test_runner.py verify_ac_tests gate.

Original BUG-A/BUG-B audit + regression tests for the task_type fix.
"""
import pytest
from dataclasses import dataclass

from app.services.test_runner import verify_ac_tests


@dataclass
class FakeAC:
    position: int
    text: str
    verification: str
    test_path: str | None = None
    command: str | None = None


# ---------- Regression: task_type=None preserves legacy behavior (backward compat) ----------

def test_legacy_caller_without_task_type_still_passes_manual_ac(tmp_path):
    """Callers that don't pass task_type get the old behavior (skip → all_pass=True).

    Rationale: verify_ac_tests is a library function; external callers shouldn't break.
    Only the pipeline gate opts in by passing task_type.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    acs = [FakeAC(position=0, text="works", verification="manual")]

    result = verify_ac_tests(str(tmp_path), acs)  # no task_type

    assert result["all_pass"] is True
    assert result["skipped"] == "no test-verifiable AC"


# ---------- BUG-A fix: feature/bug with no test-verifiable AC now FAILS ----------

def test_feature_task_with_manual_only_ac_fails_gate(tmp_path):
    """BUG-A fix: feature task with only manual AC → all_pass=False, error explains why."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    acs = [FakeAC(position=0, text="business logic works", verification="manual")]

    result = verify_ac_tests(str(tmp_path), acs, task_type="feature")

    assert result["all_pass"] is False
    assert result["run"] is None
    assert "no test-verifiable AC" in result["error"]
    assert "manual-only" in result["error"].lower()


def test_bug_task_with_command_verification_no_test_path_fails_gate(tmp_path):
    """BUG-A extension fix: verification='command' without test_path still fails for feature/bug."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    acs = [FakeAC(position=0, text="health ok", verification="command",
                  command="curl /health")]  # no test_path

    result = verify_ac_tests(str(tmp_path), acs, task_type="bug")

    assert result["all_pass"] is False
    assert result["run"] is None
    assert result["error"]


# ---------- Chore/investigation retain soft behavior (manual-only OK) ----------

def test_chore_task_with_manual_only_ac_still_passes(tmp_path):
    """Chore/investigation don't require test-verifiable AC.

    These task types often cover exploration, docs, cleanup — force-test would block legit work.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    acs = [FakeAC(position=0, text="explored the codebase", verification="manual")]

    result = verify_ac_tests(str(tmp_path), acs, task_type="chore")

    assert result["all_pass"] is True
    assert result["skipped"] == "no test-verifiable AC"


# ---------- Happy path: feature/bug with real test works normally ----------

def test_feature_task_with_passing_test_passes_gate(tmp_path):
    """Sanity: feature task with verification=test + passing test → all_pass=True."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    (tmp_path / "test_ok.py").write_text("def test_x(): assert True\n")
    acs = [FakeAC(position=0, text="ok", verification="test", test_path="test_ok.py")]

    result = verify_ac_tests(str(tmp_path), acs, task_type="feature")

    assert result["all_pass"] is True
    assert result["run"] is not None
    assert result["run"].tests_passed >= 1


def test_feature_task_with_failing_test_fails_gate(tmp_path):
    """Sanity: feature task with verification=test + failing test → all_pass=False with ac_results."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    (tmp_path / "test_bad.py").write_text("def test_x(): assert False\n")
    acs = [FakeAC(position=0, text="stock calc", verification="test", test_path="test_bad.py")]

    result = verify_ac_tests(str(tmp_path), acs, task_type="feature")

    assert result["all_pass"] is False
    assert result["run"] is not None
    assert result["run"].tests_failed == 1
    assert len(result["ac_results"]) == 1
    assert result["ac_results"][0]["passed"] is False


# ---------- BUG-B still exists (documented non-fix): command field is ignored ----------

def test_bug_b_command_field_still_ignored_when_test_path_present(tmp_path):
    """BUG-B (known): 'command' string is NOT executed; test_path drives pytest.

    Not fixed in this round — separate design decision (should Forge shell out to command?).
    Documented here so future change has a regression test.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fake'\n")
    (tmp_path / "test_real.py").write_text("def test_x(): assert True\n")
    acs = [FakeAC(position=0, text="ok", verification="command",
                  command="this_command_is_ignored_entirely",
                  test_path="test_real.py")]

    result = verify_ac_tests(str(tmp_path), acs, task_type="feature")

    # pytest runs test_real.py (passes), command string never executed
    assert result["all_pass"] is True
    assert result["run"].tests_passed >= 1

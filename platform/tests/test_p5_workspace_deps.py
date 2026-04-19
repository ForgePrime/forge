"""P5.1 — `install_workspace_deps` runs pip + records outcome cleanly.

Tests use a tempdir workspace and either mock subprocess or use sys.executable
with an empty requirements.txt. We never install real packages here — too slow
+ flaky on shared CI."""
import pathlib
import subprocess
import tempfile
from unittest import mock

import pytest

from app.services.workspace_infra import install_workspace_deps, DepsInstallResult


def test_skip_when_requirements_missing():
    with tempfile.TemporaryDirectory() as ws:
        out = install_workspace_deps(ws)
        assert isinstance(out, DepsInstallResult)
        assert out.attempted is False
        assert out.installed is False
        assert out.file_path is None
        assert out.return_code is None
        assert out.error is None


def test_runs_pip_when_requirements_present():
    with tempfile.TemporaryDirectory() as ws:
        (pathlib.Path(ws) / "requirements.txt").write_text("# empty\n", encoding="utf-8")
        fake = mock.MagicMock(returncode=0, stdout="installed nothing", stderr="")
        with mock.patch("app.services.workspace_infra.subprocess.run", return_value=fake) as m:
            out = install_workspace_deps(ws)
        assert out.attempted is True
        assert out.installed is True
        assert out.return_code == 0
        # Verify the cmd shape
        called_cmd = m.call_args.args[0]
        assert called_cmd[1:5] == ["-m", "pip", "install", "-q"]
        assert called_cmd[-2:] == ["-r", str(pathlib.Path(ws) / "requirements.txt")]


def test_records_pip_failure_with_stderr():
    with tempfile.TemporaryDirectory() as ws:
        (pathlib.Path(ws) / "requirements.txt").write_text("not-a-real-package==999\n", encoding="utf-8")
        fake = mock.MagicMock(returncode=1, stdout="",
                              stderr="ERROR: No matching distribution found for not-a-real-package==999")
        with mock.patch("app.services.workspace_infra.subprocess.run", return_value=fake):
            out = install_workspace_deps(ws)
        assert out.attempted is True
        assert out.installed is False
        assert out.return_code == 1
        assert "pip exit 1" in (out.error or "")
        assert "not-a-real-package" in out.stderr_tail


def test_handles_pip_timeout():
    with tempfile.TemporaryDirectory() as ws:
        (pathlib.Path(ws) / "requirements.txt").write_text("anything\n", encoding="utf-8")
        with mock.patch(
            "app.services.workspace_infra.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["pip"], timeout=1),
        ):
            out = install_workspace_deps(ws, timeout_sec=1)
        assert out.attempted is True
        assert out.installed is False
        assert out.error is not None and "timed out" in out.error


def test_handles_missing_python_executable():
    with tempfile.TemporaryDirectory() as ws:
        (pathlib.Path(ws) / "requirements.txt").write_text("anything\n", encoding="utf-8")
        with mock.patch(
            "app.services.workspace_infra.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            out = install_workspace_deps(ws, python_exe="/nope/python")
        assert out.attempted is True
        assert out.installed is False
        assert "/nope/python" in (out.error or "")


def test_uses_custom_requirements_filename():
    with tempfile.TemporaryDirectory() as ws:
        (pathlib.Path(ws) / "dev-requirements.txt").write_text("flask\n", encoding="utf-8")
        fake = mock.MagicMock(returncode=0, stdout="", stderr="")
        with mock.patch("app.services.workspace_infra.subprocess.run", return_value=fake) as m:
            out = install_workspace_deps(ws, requirements_filename="dev-requirements.txt")
        assert out.attempted is True
        called_cmd = m.call_args.args[0]
        assert called_cmd[-1].endswith("dev-requirements.txt")


# ---- Sanity: the gate already treats `tests_error` like `tests_failed` ----

def test_test_runner_all_passed_returns_false_on_error():
    """Sanity for P5.1 hypothesis — if a test errors (e.g. ImportError), `all_passed` is False."""
    from app.services.test_runner import TestRunResult
    r = TestRunResult(
        return_code=1, duration_ms=10,
        tests_collected=2, tests_passed=1, tests_failed=0, tests_error=1, tests_skipped=0,
    )
    assert r.all_passed is False


def test_test_runner_all_passed_true_when_clean():
    from app.services.test_runner import TestRunResult
    r = TestRunResult(
        return_code=0, duration_ms=10,
        tests_collected=3, tests_passed=3, tests_failed=0, tests_error=0, tests_skipped=0,
    )
    assert r.all_passed is True


def test_verify_ac_tests_treats_error_as_failure():
    """Per-AC: a test that errored counts toward `tests_failed` and the AC is marked not passed."""
    from app.services.test_runner import TestRunResult, TestResult, verify_ac_tests
    # Pre-seed a fake run by patching run_tests
    fake_run = TestRunResult(
        return_code=1, duration_ms=10,
        tests_collected=1, tests_passed=0, tests_failed=0, tests_error=1, tests_skipped=0,
        results=[TestResult(
            nodeid="tests/test_x.py::test_y", outcome="error", duration_sec=0.0,
            longrepr="ModuleNotFoundError: No module named 'locust'",
        )],
    )
    ac = type("AC", (), {"position": 1, "test_path": "tests/test_x.py::test_y", "verification": "test"})()
    with mock.patch("app.services.test_runner.run_tests", return_value=fake_run):
        with tempfile.TemporaryDirectory() as ws:
            res = verify_ac_tests(ws, [ac])
    assert res["all_pass"] is False
    assert res["ac_results"][0]["passed"] is False
    assert res["ac_results"][0]["tests_failed"] == 1

"""Forge-owned test executor.

Does NOT trust delivery.ac_evidence claiming "test_X PASSED". Forge itself
runs pytest in the workspace and captures real results.

Core contract:
- Input: workspace_dir, optional test_paths filter (from AC.test_path)
- Output: TestRunResult with per-test outcome + stdout/stderr + duration
- Persists: test_runs table row per invocation
- Consumers: orchestrator gates task as DONE only if tests pass for each AC
  that has verification="test"
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field


@dataclass
class TestResult:
    nodeid: str                 # pytest node id, e.g. tests/db/test_schema.py::test_X
    outcome: str                # passed | failed | error | skipped | xfailed | xpassed
    duration_sec: float
    call_stdout: str = ""
    call_stderr: str = ""
    longrepr: str = ""          # failure message / traceback summary
    file: str = ""
    name: str = ""


@dataclass
class TestRunResult:
    return_code: int
    duration_ms: int
    tests_collected: int
    tests_passed: int
    tests_failed: int
    tests_error: int
    tests_skipped: int
    results: list[TestResult] = field(default_factory=list)
    summary_text: str = ""
    stderr_tail: str = ""
    error: str | None = None

    @property
    def all_passed(self) -> bool:
        return (
            self.tests_failed == 0
            and self.tests_error == 0
            and self.tests_collected > 0
            and self.return_code in (0, 5)  # 5 = no tests collected; treated as "nothing to do"
        )

    def results_for(self, test_path: str | None) -> list[TestResult]:
        """Return results matching a test_path fragment (from AC.test_path)."""
        if not test_path:
            return list(self.results)
        needle = test_path.replace("\\", "/").strip()
        out = []
        for r in self.results:
            nid = r.nodeid.replace("\\", "/")
            if needle in nid or needle == r.file:
                out.append(r)
        return out


def run_pytest(
    workspace_dir: str,
    test_paths: list[str] | None = None,
    timeout_sec: int = 600,
    env_extra: dict[str, str] | None = None,
) -> TestRunResult:
    """Execute pytest in workspace with --json-report, parse per-test outcomes.

    test_paths: optional filter (pass each as positional arg to pytest).
    env_extra: additional env vars (e.g. DATABASE_URL).
    """
    ws = pathlib.Path(workspace_dir)
    if not ws.exists():
        return TestRunResult(
            return_code=-1, duration_ms=0, tests_collected=0,
            tests_passed=0, tests_failed=0, tests_error=0, tests_skipped=0,
            error=f"workspace does not exist: {workspace_dir}",
        )

    with tempfile.TemporaryDirectory() as tmp:
        report_path = str(pathlib.Path(tmp) / "pytest_report.json")
        cmd = [
            sys.executable, "-m", "pytest",
            "--json-report",
            f"--json-report-file={report_path}",
            "--json-report-omit=collectors",
            "-v", "--tb=short", "--no-header",
        ]
        if test_paths:
            cmd.extend(test_paths)

        import os
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ws),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
                env=env,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
        except subprocess.TimeoutExpired:
            return TestRunResult(
                return_code=-1,
                duration_ms=int((time.monotonic() - start) * 1000),
                tests_collected=0, tests_passed=0, tests_failed=0,
                tests_error=0, tests_skipped=0,
                error=f"pytest timeout after {timeout_sec}s",
                stderr_tail="",
            )
        except FileNotFoundError:
            return TestRunResult(
                return_code=-1, duration_ms=0,
                tests_collected=0, tests_passed=0, tests_failed=0,
                tests_error=0, tests_skipped=0,
                error="pytest not installed",
            )

        # Parse JSON report (if produced)
        report = None
        rp = pathlib.Path(report_path)
        if rp.exists():
            try:
                report = json.loads(rp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                report = None

        if not report:
            # Report missing — fallback to stderr/stdout tail
            return TestRunResult(
                return_code=proc.returncode,
                duration_ms=duration_ms,
                tests_collected=0, tests_passed=0, tests_failed=0,
                tests_error=0, tests_skipped=0,
                summary_text=(proc.stdout or "")[-2000:],
                stderr_tail=(proc.stderr or "")[-1000:],
                error="no pytest JSON report produced — see stderr",
            )

        summary = report.get("summary", {})
        tests = report.get("tests", [])
        results: list[TestResult] = []
        for t in tests:
            outcome = t.get("outcome", "unknown")
            call = t.get("call") or {}
            call_stdout = call.get("stdout") or ""
            call_stderr = call.get("stderr") or ""
            longrepr = call.get("longrepr") or ""
            results.append(TestResult(
                nodeid=t.get("nodeid", "?"),
                outcome=outcome,
                duration_sec=(call.get("duration") or 0.0),
                call_stdout=call_stdout[:4000] if call_stdout else "",
                call_stderr=call_stderr[:2000] if call_stderr else "",
                longrepr=str(longrepr)[:4000],
                file=t.get("file", ""),
                name=t.get("name") or t.get("nodeid", "?"),
            ))

        return TestRunResult(
            return_code=proc.returncode,
            duration_ms=duration_ms,
            tests_collected=summary.get("collected", summary.get("total", 0)),
            tests_passed=summary.get("passed", 0),
            tests_failed=summary.get("failed", 0),
            tests_error=summary.get("error", summary.get("errors", 0)),
            tests_skipped=summary.get("skipped", 0),
            results=results,
            summary_text=(proc.stdout or "")[-2000:],
            stderr_tail=(proc.stderr or "")[-1000:],
        )


def detect_language(workspace_dir: str) -> str:
    """Detect primary language based on project marker files OR file extensions.

    Returns: 'python' | 'node' | 'go' | 'rust' | 'java' | 'unknown'
    Marker files take priority. Falls back to file-extension scan if no markers
    (Claude often skips creating pyproject.toml/package.json for small scaffolds).
    """
    ws = pathlib.Path(workspace_dir)
    markers = [
        ("python", ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "conftest.py"]),
        ("node", ["package.json"]),
        ("go", ["go.mod"]),
        ("rust", ["Cargo.toml"]),
        ("java", ["pom.xml", "build.gradle", "build.gradle.kts"]),
    ]
    for lang, files in markers:
        for f in files:
            if (ws / f).exists() or list(ws.rglob(f))[:1]:
                return lang
    # Fallback: extension-based detection (skip dot-dirs like .git, .venv)
    EXT_RANK = [
        ("python", {".py"}),
        ("node", {".ts", ".tsx", ".js", ".jsx"}),
        ("go", {".go"}),
        ("rust", {".rs"}),
        ("java", {".java", ".kt"}),
    ]
    counts = {lang: 0 for lang, _ in EXT_RANK}
    for path in ws.rglob("*"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        for lang, exts in EXT_RANK:
            if ext in exts:
                counts[lang] += 1
                break
    if any(counts.values()):
        return max(counts, key=counts.get)
    return "unknown"


def run_node_tests(
    workspace_dir: str,
    test_paths: list[str] | None = None,
    timeout_sec: int = 600,
    env_extra: dict[str, str] | None = None,
) -> TestRunResult:
    """Execute npm/yarn test (jest/vitest). Best-effort JSON via jest --json.

    Detects test runner from package.json.devDependencies.
    """
    import os, json as _json
    ws = pathlib.Path(workspace_dir)
    pkg = ws / "package.json"
    if not pkg.exists():
        return TestRunResult(-1, 0, 0, 0, 0, 0, 0, error="no package.json")

    try:
        pkg_data = _json.loads(pkg.read_text(encoding="utf-8"))
    except Exception as e:
        return TestRunResult(-1, 0, 0, 0, 0, 0, 0, error=f"package.json parse: {e}")

    deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
    runner = "jest" if "jest" in deps else ("vitest" if "vitest" in deps else None)
    if not runner:
        # Fallback: run `npm test` (no JSON parsing, aggregate only)
        cmd = ["npm", "test", "--", "--silent"] if "test" in pkg_data.get("scripts", {}) else None
        if not cmd:
            return TestRunResult(-1, 0, 0, 0, 0, 0, 0, error="no jest/vitest detected and no npm test script")
    else:
        # Use jest/vitest with JSON reporter
        with tempfile.TemporaryDirectory() as tmp:
            report_path = pathlib.Path(tmp) / "report.json"
            if runner == "jest":
                cmd = ["npx", "jest", "--json", f"--outputFile={report_path}"]
            else:
                cmd = ["npx", "vitest", "run", "--reporter=json", f"--outputFile={report_path}"]
            if test_paths:
                cmd.extend(test_paths)

            env = dict(os.environ)
            if env_extra:
                env.update(env_extra)

            start = time.monotonic()
            try:
                proc = subprocess.run(cmd, cwd=str(ws), capture_output=True,
                                      text=True, encoding="utf-8", errors="replace",
                                      timeout=timeout_sec, env=env, shell=True)
                duration_ms = int((time.monotonic() - start) * 1000)
            except subprocess.TimeoutExpired:
                return TestRunResult(-1, int((time.monotonic()-start)*1000), 0, 0, 0, 0, 0,
                                     error=f"node test timeout after {timeout_sec}s")

            results: list[TestResult] = []
            passed = failed = errored = skipped = collected = 0
            if report_path.exists():
                try:
                    rep = _json.loads(report_path.read_text(encoding="utf-8"))
                    # jest/vitest shape differs; best-effort extraction
                    test_results = rep.get("testResults") or rep.get("tests") or []
                    for tr in test_results:
                        for assertion in (tr.get("assertionResults") or tr.get("tests") or []):
                            outcome_map = {"passed": "passed", "failed": "failed",
                                           "pending": "skipped", "skipped": "skipped"}
                            outcome = outcome_map.get(assertion.get("status"), "unknown")
                            results.append(TestResult(
                                nodeid=f"{tr.get('name','?')}::{assertion.get('title','?')}",
                                outcome=outcome,
                                duration_sec=(assertion.get("duration", 0) or 0) / 1000.0,
                                longrepr="\n".join(assertion.get("failureMessages", []) or [])[:4000],
                            ))
                            collected += 1
                            if outcome == "passed": passed += 1
                            elif outcome == "failed": failed += 1
                            elif outcome == "skipped": skipped += 1
                except Exception as e:
                    pass

            return TestRunResult(
                return_code=proc.returncode, duration_ms=duration_ms,
                tests_collected=collected, tests_passed=passed, tests_failed=failed,
                tests_error=errored, tests_skipped=skipped, results=results,
                summary_text=(proc.stdout or "")[-2000:],
                stderr_tail=(proc.stderr or "")[-1000:],
            )


def run_tests(
    workspace_dir: str,
    test_paths: list[str] | None = None,
    timeout_sec: int = 600,
    env_extra: dict[str, str] | None = None,
    language: str | None = None,
) -> TestRunResult:
    """Language-aware test dispatcher.

    Auto-detects language from workspace markers unless explicit `language` given.
    """
    lang = language or detect_language(workspace_dir)
    if lang == "python":
        return run_pytest(workspace_dir, test_paths, timeout_sec, env_extra)
    if lang == "node":
        return run_node_tests(workspace_dir, test_paths, timeout_sec, env_extra)
    # Future: go/rust/java runners
    return TestRunResult(
        return_code=-1, duration_ms=0,
        tests_collected=0, tests_passed=0, tests_failed=0,
        tests_error=0, tests_skipped=0,
        error=f"no test runner implemented for language '{lang}'",
    )


def verify_ac_tests(
    workspace_dir: str,
    acceptance_criteria: list,
    env_extra: dict[str, str] | None = None,
) -> dict:
    """Run pytest for each AC that has verification in (test, command) and test_path.

    Returns: {
      'all_pass': bool,
      'ac_results': [{ac_index, test_path, passed, matched_tests: [...]}],
      'run': TestRunResult (full),
    }
    """
    test_paths: list[str] = []
    ac_index_to_path: dict[int, str] = {}
    for ac in acceptance_criteria:
        pos = getattr(ac, "position", None) if not isinstance(ac, dict) else ac.get("position")
        tp = getattr(ac, "test_path", None) if not isinstance(ac, dict) else ac.get("test_path")
        verif = getattr(ac, "verification", None) if not isinstance(ac, dict) else ac.get("verification")
        if verif in ("test", "command") and tp:
            ac_index_to_path[pos] = tp
            # Strip '::method' for pytest collection broadness — but we keep exact later
            test_paths.append(tp)

    if not test_paths:
        return {"all_pass": True, "ac_results": [], "run": None, "skipped": "no test-verifiable AC", "language": detect_language(workspace_dir)}

    lang = detect_language(workspace_dir)
    run = run_tests(workspace_dir, test_paths=test_paths, env_extra=env_extra, language=lang)

    ac_results = []
    all_ok = True
    for ac_idx, tp in ac_index_to_path.items():
        matched = run.results_for(tp)
        # An AC passes only if at least one matching test ran and none failed
        any_failed = any(r.outcome in ("failed", "error") for r in matched)
        any_passed = any(r.outcome == "passed" for r in matched)
        passed = any_passed and not any_failed
        ac_results.append({
            "ac_index": ac_idx,
            "test_path": tp,
            "passed": passed,
            "tests_matched": len(matched),
            "tests_passed": sum(1 for r in matched if r.outcome == "passed"),
            "tests_failed": sum(1 for r in matched if r.outcome in ("failed", "error")),
            "failure_details": [
                {"nodeid": r.nodeid, "outcome": r.outcome, "longrepr": r.longrepr}
                for r in matched if r.outcome in ("failed", "error")
            ],
        })
        if not passed:
            all_ok = False

    return {
        "all_pass": all_ok,
        "ac_results": ac_results,
        "run": run,
        "language": lang,
    }

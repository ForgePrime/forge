"""Pytest session hooks for the Forge test suite.

Today this only does one thing: at the end of every pytest session, sweep any
docker containers + named volumes left over by `build_populated_project`.

Background: `tests/conftest_populated.py::_signup_and_project` creates a fresh
project per test module. When a test triggers orchestrate (e.g. P1.1's resume
test calls `_run_orchestrate_background` which spawns `ensure_workspace_infra`),
postgres/redis containers named `forge-{slug}-{postgres|redis}` get started in
Rancher Desktop and never torn down. After enough runs you end up with dozens
of healthy-but-orphaned containers eating ~1 GB each.

We solve it the cheap way: every slug created during this session is appended
to `CREATED_SLUGS`; on session-finish we `docker rm -f` whatever matches.
Failures here are logged, never fatal — local docker absence shouldn't break CI."""
from __future__ import annotations

import shutil
import subprocess
import time


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _safe_run(cmd: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _collect_container_ids(slugs: list[str]) -> list[str]:
    ids: list[str] = []
    for slug in slugs:
        res = _safe_run(["docker", "ps", "-aq", "--filter", f"name=forge-{slug}-"])
        if res and res.returncode == 0 and res.stdout.strip():
            ids.extend(res.stdout.strip().splitlines())
    return ids


def pytest_sessionfinish(session, exitstatus):  # pragma: no cover - environment-driven
    """Sweep any forge-{slug}-* containers + their volumes the suite created.

    Some tests (P1.1 resume) spawn `_run_orchestrate_background` which creates
    workspace_infra containers asynchronously. The container may not exist yet
    when the test exits — so we sweep, sleep, sweep again to catch laggards.
    """
    if not _docker_available():
        return
    try:
        from tests.conftest_populated import CREATED_SLUGS
    except Exception:
        return
    if not CREATED_SLUGS:
        return

    terminal = getattr(session.config, "terminal_writer", None)

    def _msg(s: str) -> None:
        if terminal:
            terminal.line(s)
        else:
            print(s)

    # Pass 1: immediate sweep
    ids = _collect_container_ids(CREATED_SLUGS)
    if ids:
        _msg(f"\n[forge teardown] removing {len(ids)} test container(s)…")
        _safe_run(["docker", "rm", "-f", *ids], timeout=120)

    # Pass 2: short grace period for any background-spawned containers
    # (e.g. the resume endpoint that respawns _run_orchestrate_background)
    time.sleep(8)
    ids2 = _collect_container_ids(CREATED_SLUGS)
    if ids2:
        _msg(f"[forge teardown] removing {len(ids2)} late-arriving test container(s)…")
        _safe_run(["docker", "rm", "-f", *ids2], timeout=120)

    # Best-effort orphan-volume cleanup (named volumes survive container rm)
    if ids or ids2:
        _safe_run(["docker", "volume", "prune", "-f"], timeout=60)

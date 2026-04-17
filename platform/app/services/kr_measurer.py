"""KR measurement runner — executes KeyResult.measurement_command in workspace.

After a task completes, Forge finds KRs linked to task's objective that:
- have measurement_command set
- are numeric (have target_value)

Runs the command, parses first number from stdout (heuristic), updates:
- KeyResult.current_value
- KeyResult.status: ACHIEVED if hits target, IN_PROGRESS otherwise
"""

import re
import subprocess
import time
from dataclasses import dataclass


@dataclass
class KRMeasurement:
    kr_id: int
    kr_text: str
    target_value: float | None
    measured_value: float | None
    target_hit: bool
    stdout_tail: str
    stderr_tail: str
    return_code: int
    duration_ms: int
    command: str
    error: str | None = None


_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def _parse_first_number(text: str) -> float | None:
    """Extract first numeric token from text. Heuristic."""
    if not text:
        return None
    m = _NUM_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def measure_kr(
    workspace_dir: str,
    kr_id: int,
    kr_text: str,
    measurement_command: str,
    target_value: float | None,
    timeout_sec: int = 300,
    env_extra: dict | None = None,
    target_direction: str = "leq",  # "leq" (measured <= target) | "geq" (measured >= target) | "eq"
) -> KRMeasurement:
    """Run measurement_command in workspace, parse first number from stdout.

    Heuristic for target_direction: if text mentions "latency"/"time"/"duration" → leq
    Override via kwarg if known.
    """
    import os
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)

    start = time.monotonic()
    try:
        proc = subprocess.run(
            measurement_command,
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=env,
            shell=True,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
    except subprocess.TimeoutExpired:
        return KRMeasurement(
            kr_id=kr_id, kr_text=kr_text, target_value=target_value,
            measured_value=None, target_hit=False,
            stdout_tail="", stderr_tail=f"[TIMEOUT {timeout_sec}s]",
            return_code=-1, duration_ms=int((time.monotonic()-start)*1000),
            command=measurement_command, error="timeout",
        )

    measured = _parse_first_number(proc.stdout)
    if measured is None:
        measured = _parse_first_number(proc.stderr)

    # Auto-detect direction from kr_text keywords
    lc = kr_text.lower()
    if any(k in lc for k in ["latency", "time", "duration", "seconds", "ms", "p95", "p99"]):
        target_direction = "leq"
    elif any(k in lc for k in ["coverage", "throughput", "rate"]):
        target_direction = "geq"

    target_hit = False
    if measured is not None and target_value is not None:
        if target_direction == "leq":
            target_hit = measured <= target_value
        elif target_direction == "geq":
            target_hit = measured >= target_value
        else:
            target_hit = abs(measured - target_value) < 0.01

    return KRMeasurement(
        kr_id=kr_id, kr_text=kr_text, target_value=target_value,
        measured_value=measured, target_hit=target_hit,
        stdout_tail=(proc.stdout or "")[-1000:],
        stderr_tail=(proc.stderr or "")[-500:],
        return_code=proc.returncode, duration_ms=duration_ms,
        command=measurement_command,
        error=None if proc.returncode == 0 else f"rc={proc.returncode}",
    )

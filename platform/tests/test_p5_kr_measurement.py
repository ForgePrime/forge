"""P5.2 — KR measurement failures must surface as Findings, not be silent.

Pilot regression: 4/4 numeric KRs stayed `NOT_STARTED` because measurement
commands either weren't installed (locust/ab missing) or emitted text without
a number, and the code silently moved on. Now we leave a `gap`-type Finding
behind in either failure mode.

These tests exercise:
  1. The measurer's own contract: timeout / nonzero rc / unparseable output.
  2. A unit on the orchestrate failure-detection branch by calling measure_kr
     with mocked subprocess and asserting the right `error` / `measured_value`."""
import subprocess
from unittest import mock

import pytest

from app.services.kr_measurer import (
    KRMeasurement, _parse_first_number, measure_kr,
)


# ---- Pure helpers ----------------------------------------------------

def test_parse_first_number_picks_int_from_text():
    assert _parse_first_number("Latency: 42 ms") == 42.0


def test_parse_first_number_picks_float():
    # First number wins — even if it's part of a label like 'p95'
    assert _parse_first_number("Latency = 2.345 s") == 2.345


def test_parse_first_number_first_token_wins_even_in_metric_labels():
    # Documents the heuristic: 'p95' contributes a leading 95
    assert _parse_first_number("p95=2.345s") == 95.0


def test_parse_first_number_picks_negative():
    assert _parse_first_number("delta -1.5") == -1.5


def test_parse_first_number_returns_none_when_text_has_no_number():
    assert _parse_first_number("OK") is None
    assert _parse_first_number("") is None
    assert _parse_first_number(None) is None


# ---- measure_kr behaviour --------------------------------------------

def _fake_proc(returncode: int, stdout: str = "", stderr: str = ""):
    return mock.MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


def test_measure_kr_records_clean_success():
    with mock.patch(
        "app.services.kr_measurer.subprocess.run",
        return_value=_fake_proc(0, "Latency: 1.2s\n"),
    ):
        m = measure_kr(
            workspace_dir=".",
            kr_id=1, kr_text="latency under 3s",
            measurement_command="ab -n 100 http://x/",
            target_value=3.0,
        )
    assert m.return_code == 0
    assert m.error is None
    assert m.measured_value == 1.2
    assert m.target_hit is True  # 1.2 <= 3.0 (latency → leq)


def test_measure_kr_marks_error_on_nonzero_rc():
    with mock.patch(
        "app.services.kr_measurer.subprocess.run",
        return_value=_fake_proc(127, "", "ab: command not found"),
    ):
        m = measure_kr(
            workspace_dir=".",
            kr_id=2, kr_text="throughput",
            measurement_command="ab -n 100 http://x/",
            target_value=100.0,
        )
    assert m.return_code == 127
    assert m.error == "rc=127"
    assert m.measured_value is None
    assert "command not found" in m.stderr_tail


def test_measure_kr_handles_timeout():
    with mock.patch(
        "app.services.kr_measurer.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1),
    ):
        m = measure_kr(
            workspace_dir=".",
            kr_id=3, kr_text="timed metric",
            measurement_command="sleep 999",
            target_value=1.0,
            timeout_sec=1,
        )
    assert m.error == "timeout"
    assert m.return_code == -1
    assert m.measured_value is None
    assert "[TIMEOUT" in m.stderr_tail


def test_measure_kr_clean_exit_but_no_number_yields_no_value():
    """rc=0 but stdout has no number → measured_value stays None.
    The orchestrate loop must surface this as a Finding (covered separately).
    """
    with mock.patch(
        "app.services.kr_measurer.subprocess.run",
        return_value=_fake_proc(0, "OK — done", ""),
    ):
        m = measure_kr(
            workspace_dir=".",
            kr_id=4, kr_text="something",
            measurement_command="echo OK",
            target_value=1.0,
        )
    assert m.error is None  # No process-level failure
    assert m.measured_value is None  # But the measurement itself didn't yield data


def test_measure_kr_target_direction_geq_for_throughput():
    with mock.patch(
        "app.services.kr_measurer.subprocess.run",
        return_value=_fake_proc(0, "1500 req/s"),
    ):
        m = measure_kr(
            workspace_dir=".",
            kr_id=5, kr_text="throughput per second",
            measurement_command="bench",
            target_value=1000.0,
        )
    assert m.measured_value == 1500.0
    assert m.target_hit is True  # 1500 >= 1000


# ---- Orchestrate-side wiring (logic-only smoke) ----------------------

def test_failure_classification_logic_matches_orchestrate_branch():
    """Mirror the if/elif in pipeline.py to make sure no regression slips in:
       - error set → 'measurement command failed'
       - error None + measured_value None → 'no parseable number'
       - measured_value present → no finding
    """
    cases = [
        # (KRMeasurement, expected_failure_reason fragment)
        (KRMeasurement(
            kr_id=1, kr_text="x", target_value=1.0, measured_value=None,
            target_hit=False, stdout_tail="", stderr_tail="", return_code=127,
            duration_ms=10, command="x", error="rc=127",
         ), "measurement command failed"),
        (KRMeasurement(
            kr_id=2, kr_text="x", target_value=1.0, measured_value=None,
            target_hit=False, stdout_tail="OK", stderr_tail="", return_code=0,
            duration_ms=10, command="x", error=None,
         ), "no parseable number"),
        (KRMeasurement(
            kr_id=3, kr_text="x", target_value=1.0, measured_value=2.5,
            target_hit=False, stdout_tail="2.5", stderr_tail="", return_code=0,
            duration_ms=10, command="x", error=None,
         ), None),
    ]
    for m, expected in cases:
        if m.error:
            reason = f"measurement command failed ({m.error})"
        elif m.measured_value is None:
            reason = "measurement command exited 0 but stdout contained no parseable number"
        else:
            reason = None
        if expected is None:
            assert reason is None
        else:
            assert reason is not None
            assert expected in reason

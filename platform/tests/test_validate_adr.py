"""Tests for `platform/scripts/validate_adr.py` — Stage 28.1 ADR format gate.

Per task #28 Deterministic ADR Gate Pipeline. Tests cover:
  - Each rule R1..R8 fires (or doesn't) as specified
  - Warning W2 surfaces UNKNOWN tags
  - Baseline filtering preserves current drift but catches new issues
  - JSON output is well-formed
  - Exit codes match documentation

The validator is pure stdlib + deterministic — these tests run with no DB,
no network, no Forge app imports.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Load validate_adr module by file path (it's a script, not a package member).
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_adr.py"
spec = importlib.util.spec_from_file_location("validate_adr", SCRIPT)
assert spec is not None and spec.loader is not None
validate_adr = importlib.util.module_from_spec(spec)
# Register before exec_module: Python 3.13's @dataclass machinery calls
# sys.modules[cls.__module__] during introspection, which fails if the
# module isn't registered yet.
sys.modules["validate_adr"] = validate_adr
spec.loader.exec_module(validate_adr)


# --- Fixture builders --------------------------------------------------------


VALID_BODY = """\
# ADR-099 — Sample valid ADR for testing

**Status:** PROPOSED
**Date:** 2026-04-25
**Decided by:** test
**Related:** none

## Context
Test fixture.

## Decision
Adopt the test fixture as a fixture.

## Rationale
Because tests need fixtures.

## Alternatives considered
- **A.** No fixture — rejected because then there's nothing to test.
- **B.** Two fixtures — rejected because one suffices.

## Consequences
The test passes.

## Evidence captured
- **[CONFIRMED]** test framework runs — via pytest output.
"""


def write_adr(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# --- Tests: rules -----------------------------------------------------------


def test_valid_adr_passes(tmp_path):
    p = write_adr(tmp_path, "ADR-099-sample-valid.md", VALID_BODY)
    r = validate_adr.validate_file(p)
    assert r.status_word == "PASS", r.render()
    assert r.issues == []


def test_filename_bad_pattern_fails_r1(tmp_path):
    p = write_adr(tmp_path, "BAD-FILENAME.md", VALID_BODY)
    r = validate_adr.validate_file(p)
    assert r.has_failures
    rules = {i.rule for i in r.issues}
    assert "R1" in rules


def test_title_nnn_mismatch_fails_r2(tmp_path):
    body = VALID_BODY.replace("# ADR-099 —", "# ADR-100 —")
    p = write_adr(tmp_path, "ADR-099-sample.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R2" in rules


def test_missing_status_fails_r3(tmp_path):
    body = VALID_BODY.replace("**Status:** PROPOSED", "")
    p = write_adr(tmp_path, "ADR-099-sample-no-status.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R3" in rules


def test_invalid_status_value_fails_r3(tmp_path):
    body = VALID_BODY.replace("**Status:** PROPOSED", "**Status:** WIP")
    p = write_adr(tmp_path, "ADR-099-sample-bad-status.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R3" in rules


def test_missing_date_fails_r4(tmp_path):
    body = VALID_BODY.replace("**Date:** 2026-04-25", "")
    p = write_adr(tmp_path, "ADR-099-sample-no-date.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R4" in rules


def test_missing_section_fails_r5(tmp_path):
    body = VALID_BODY.replace("## Rationale\nBecause tests need fixtures.\n\n", "")
    p = write_adr(tmp_path, "ADR-099-sample-no-rationale.md", body)
    r = validate_adr.validate_file(p)
    fails_r5 = [i for i in r.issues if i.rule == "R5"]
    assert any("Rationale" in i.message for i in fails_r5)


def test_one_alternative_fails_r6(tmp_path):
    body = VALID_BODY.replace(
        "- **A.** No fixture — rejected because then there's nothing to test.\n"
        "- **B.** Two fixtures — rejected because one suffices.\n",
        "- **A.** No fixture — rejected because then there's nothing to test.\n",
    )
    p = write_adr(tmp_path, "ADR-099-sample-one-alt.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R6" in rules


def test_zero_alternatives_fails_r6(tmp_path):
    body = VALID_BODY.replace(
        "- **A.** No fixture — rejected because then there's nothing to test.\n"
        "- **B.** Two fixtures — rejected because one suffices.\n",
        "Nothing here.\n",
    )
    p = write_adr(tmp_path, "ADR-099-sample-no-alts.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R6" in rules


def test_ratified_without_evidence_fails_r7(tmp_path):
    body = VALID_BODY.replace("**Status:** PROPOSED", "**Status:** RATIFIED")
    body = body.replace(
        "- **[CONFIRMED]** test framework runs — via pytest output.\n",
        "- some claim with no tag.\n",
    )
    p = write_adr(tmp_path, "ADR-099-sample-ratified-no-evidence.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R7" in rules


def test_ratified_with_assumed_acceptance_passes_r7(tmp_path):
    body = VALID_BODY.replace("**Status:** PROPOSED", "**Status:** RATIFIED")
    body = body.replace(
        "- **[CONFIRMED]** test framework runs — via pytest output.\n",
        "- claim `[ASSUMED: accepted-by=user, date=2026-04-25]` per CONTRACT §B.2.\n",
    )
    p = write_adr(tmp_path, "ADR-099-sample-ratified-accepted.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R7" not in rules


def test_superseded_without_field_fails_r8(tmp_path):
    body = VALID_BODY.replace("**Status:** PROPOSED", "**Status:** SUPERSEDED")
    p = write_adr(tmp_path, "ADR-099-sample-superseded.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "R8" in rules


def test_unknown_tag_warns_w2(tmp_path):
    body = VALID_BODY + "\nSome `[UNKNOWN]` claim.\n"
    p = write_adr(tmp_path, "ADR-099-sample-unknown.md", body)
    r = validate_adr.validate_file(p)
    rules = {i.rule for i in r.issues}
    assert "W2" in rules
    assert r.has_warnings
    assert not r.has_failures  # warning is not a failure


# --- Tests: baseline filtering ----------------------------------------------


def test_baseline_filters_known_issue(tmp_path):
    body = VALID_BODY.replace("## Rationale\nBecause tests need fixtures.\n\n", "")
    p = write_adr(tmp_path, "ADR-099-sample-no-rationale.md", body)
    raw = validate_adr.validate_file(p)
    assert raw.has_failures

    # Build baseline matching the actual issue
    baseline_payload = {
        "ADR-099-sample-no-rationale.md": [
            {
                "rule": i.rule,
                "severity": i.severity,
                "message": i.message,
            }
            for i in raw.issues
        ]
    }
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps(baseline_payload), encoding="utf-8")

    baseline = validate_adr.load_baseline(baseline_file)
    filtered = validate_adr.apply_baseline([raw], baseline)
    assert filtered[0].issues == []
    assert filtered[0].status_word == "PASS"


def test_baseline_does_not_filter_new_issue(tmp_path):
    # ADR fails on rule R3 (no Status), but baseline was made for R5 only.
    body = VALID_BODY.replace("**Status:** PROPOSED", "")  # introduces NEW R3
    body = body.replace("## Rationale\nBecause tests need fixtures.\n\n", "")  # legacy R5
    p = write_adr(tmp_path, "ADR-099-sample-newer-issue.md", body)
    raw = validate_adr.validate_file(p)

    # Baseline only contains the R5 issue, not R3
    r5_issue = next(i for i in raw.issues if i.rule == "R5")
    baseline_payload = {
        p.name: [{"rule": r5_issue.rule, "severity": r5_issue.severity, "message": r5_issue.message}]
    }
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps(baseline_payload), encoding="utf-8")

    baseline = validate_adr.load_baseline(baseline_file)
    filtered = validate_adr.apply_baseline([raw], baseline)
    # Filtered should still have R3 (not in baseline)
    rules = {i.rule for i in filtered[0].issues}
    assert "R3" in rules
    assert "R5" not in rules


def test_baseline_missing_file_yields_empty(tmp_path):
    baseline = validate_adr.load_baseline(tmp_path / "does-not-exist.json")
    assert baseline == {}


# --- Tests: cli main / exit codes -------------------------------------------


def test_main_passes_on_valid_adr(tmp_path, capsys):
    p = write_adr(tmp_path, "ADR-099-sample-valid.md", VALID_BODY)
    rc = validate_adr.main([str(p), "--no-baseline"])
    assert rc == 0


def test_main_fails_on_invalid_adr(tmp_path, capsys):
    body = VALID_BODY.replace("**Status:** PROPOSED", "")
    p = write_adr(tmp_path, "ADR-099-sample-broken.md", body)
    rc = validate_adr.main([str(p), "--no-baseline"])
    assert rc == 1


def test_main_strict_fails_on_warning(tmp_path):
    body = VALID_BODY + "\nSome `[UNKNOWN]` claim.\n"
    p = write_adr(tmp_path, "ADR-099-sample-warn.md", body)
    rc_default = validate_adr.main([str(p), "--no-baseline"])
    rc_strict = validate_adr.main([str(p), "--no-baseline", "--strict"])
    assert rc_default == 0  # warning does not fail in default mode
    assert rc_strict == 1   # warning fails in strict mode


def test_main_strict_promotes_w2_to_r9_in_json(tmp_path, capsys):
    """In --strict, W2 ([UNKNOWN]) renames to R9 with FAIL severity."""
    body = VALID_BODY + "\nSome `[UNKNOWN]` claim.\n"
    p = write_adr(tmp_path, "ADR-099-sample-strict.md", body)
    validate_adr.main([str(p), "--no-baseline", "--strict", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    rules = [i["rule"] for i in payload[0]["issues"]]
    severities = {i["severity"] for i in payload[0]["issues"]}
    assert "R9" in rules
    assert "W2" not in rules
    assert "FAIL" in severities


def test_main_json_output(tmp_path, capsys):
    p = write_adr(tmp_path, "ADR-099-sample-valid.md", VALID_BODY)
    validate_adr.main([str(p), "--no-baseline", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert payload[0]["status"] == "PASS"
    assert payload[0]["issues"] == []


# --- Tests: determinism ------------------------------------------------------


def test_validation_is_deterministic(tmp_path):
    """Same input → same output across calls (FORMAL P6)."""
    p = write_adr(tmp_path, "ADR-099-sample.md", VALID_BODY)
    r1 = validate_adr.validate_file(p)
    r2 = validate_adr.validate_file(p)
    r3 = validate_adr.validate_file(p)
    assert r1.to_dict() == r2.to_dict() == r3.to_dict()

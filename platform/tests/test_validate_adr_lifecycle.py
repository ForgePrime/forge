"""Tests for `platform/scripts/validate_adr_lifecycle.py` — Stage 28.4 lifecycle gate.

Per task #28 Deterministic ADR Gate Pipeline. Tests cover:
  - Allowed transitions pass (T2)
  - Forbidden transitions fail (T2)
  - RATIFIED evidence requirement (T3)
  - SUPERSEDED supersedes-field requirement (T4)
  - RATIFIED→RATIFIED body change forbidden (T5 immutability)
  - New file (no previous) accepted only with new-file-allowed statuses
  - JSON output well-formed
  - CLI --previous mode + --base git mode (latter mocked via temp git repo)

Pure stdlib + git plumbing for --base mode tests. Deterministic.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

# Load by file path
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_adr_lifecycle.py"
spec = importlib.util.spec_from_file_location("validate_adr_lifecycle", SCRIPT)
assert spec is not None and spec.loader is not None
validate_adr_lifecycle = importlib.util.module_from_spec(spec)
sys.modules["validate_adr_lifecycle"] = validate_adr_lifecycle
spec.loader.exec_module(validate_adr_lifecycle)


# --- Fixture builders --------------------------------------------------------


def adr(status: str, body_marker: str = "## Decision\nbody.\n", *, with_evidence: bool = False, supersedes: str | None = None) -> str:
    """Build a minimal ADR with the given status field + body."""
    evidence = "- **[CONFIRMED]** test ran — output observed.\n" if with_evidence else ""
    sup_section = ""
    if supersedes is not None:
        sup_section = f"\n## Supersedes\n{supersedes}\n"
    return (
        f"# ADR-099 — Test fixture\n\n"
        f"**Status:** {status}\n"
        f"**Date:** 2026-04-25\n\n"
        f"{body_marker}\n"
        f"{evidence}"
        f"{sup_section}"
    )


# --- Tests: status extraction ------------------------------------------------


def test_extract_status_finds_value():
    assert validate_adr_lifecycle.extract_status(adr("PROPOSED")) == "PROPOSED"
    assert validate_adr_lifecycle.extract_status(adr("RATIFIED")) == "RATIFIED"


def test_extract_status_returns_none_when_absent():
    text = "# ADR-099 — Test\n\nNo status field here.\n"
    assert validate_adr_lifecycle.extract_status(text) is None


def test_extract_status_returns_none_for_invalid_value():
    text = "# ADR-099 — Test\n\n**Status:** FOOBAR\n**Date:** 2026-04-25\n"
    assert validate_adr_lifecycle.extract_status(text) is None


# --- Tests: transitions (T2) -------------------------------------------------


def test_t2_proposed_to_ratified_allowed(tmp_path):
    prev = adr("PROPOSED")
    curr = adr("RATIFIED", with_evidence=True)
    p = tmp_path / "ADR-099.md"
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, prev)
    assert r.status_word == "PASS", r.render()


def test_t2_proposed_to_proposed_allowed(tmp_path):
    """PROPOSED can stay PROPOSED while edits accumulate."""
    p = tmp_path / "ADR-099.md"
    p.write_text(adr("PROPOSED"), encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, adr("PROPOSED"), adr("PROPOSED"))
    assert r.status_word == "PASS"


def test_t2_ratified_to_proposed_forbidden(tmp_path):
    """Cannot demote RATIFIED back to PROPOSED."""
    p = tmp_path / "ADR-099.md"
    p.write_text(adr("PROPOSED"), encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, adr("PROPOSED"), adr("RATIFIED", with_evidence=True))
    assert r.has_failures
    assert any(i.rule == "T2" for i in r.issues)


def test_t2_superseded_is_terminal(tmp_path):
    """SUPERSEDED → anything-else is forbidden."""
    p = tmp_path / "ADR-099.md"
    p.write_text(adr("PROPOSED"), encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(
        p, adr("PROPOSED"), adr("SUPERSEDED", supersedes="ADR-001")
    )
    assert r.has_failures
    assert any(i.rule == "T2" for i in r.issues)


def test_t2_new_file_accepts_draft_or_proposed(tmp_path):
    p = tmp_path / "ADR-099.md"
    p.write_text(adr("PROPOSED"), encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, adr("PROPOSED"), None)
    assert r.status_word == "PASS"

    r = validate_adr_lifecycle.validate_pair(p, adr("DRAFT"), None)
    assert r.status_word == "PASS"


def test_t2_new_file_rejects_ratified_directly(tmp_path):
    """Cannot land a new file already at RATIFIED — must be PROPOSED first."""
    p = tmp_path / "ADR-099.md"
    p.write_text(adr("RATIFIED", with_evidence=True), encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, adr("RATIFIED", with_evidence=True), None)
    assert r.has_failures
    assert any(i.rule == "T2" for i in r.issues)


# --- Tests: T3 RATIFIED evidence --------------------------------------------


def test_t3_ratified_without_evidence_fails(tmp_path):
    p = tmp_path / "ADR-099.md"
    curr = adr("RATIFIED", with_evidence=False)
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, adr("PROPOSED"))
    assert any(i.rule == "T3" for i in r.issues)


def test_t3_ratified_with_assumed_acceptance_passes(tmp_path):
    p = tmp_path / "ADR-099.md"
    curr = (
        "# ADR-099 — Test\n\n"
        "**Status:** RATIFIED\n"
        "**Date:** 2026-04-25\n\n"
        "## Decision\n"
        "claim `[ASSUMED: accepted-by=user, date=2026-04-25]` per CONTRACT §B.2.\n"
    )
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, adr("PROPOSED"))
    assert not any(i.rule == "T3" for i in r.issues)


# --- Tests: T4 SUPERSEDED requirements --------------------------------------


def test_t4_superseded_without_section_fails(tmp_path):
    p = tmp_path / "ADR-099.md"
    curr = adr("SUPERSEDED")  # no Supersedes section
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, adr("PROPOSED"))
    assert any(i.rule == "T4" for i in r.issues)


def test_t4_superseded_section_without_adr_ref_fails(tmp_path):
    p = tmp_path / "ADR-099.md"
    curr = adr("SUPERSEDED", supersedes="some prose with no ADR reference")
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, adr("PROPOSED"))
    assert any(i.rule == "T4" for i in r.issues)


def test_t4_superseded_with_proper_supersedes_passes(tmp_path):
    p = tmp_path / "ADR-099.md"
    curr = adr("SUPERSEDED", supersedes="Replaces ADR-042 due to reasons.")
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, adr("PROPOSED"))
    assert not any(i.rule == "T4" for i in r.issues)


# --- Tests: T5 immutability -------------------------------------------------


def test_t5_ratified_to_ratified_with_no_body_diff_passes(tmp_path):
    body = adr("RATIFIED", body_marker="## Decision\nthe same body.\n", with_evidence=True)
    p = tmp_path / "ADR-099.md"
    p.write_text(body, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, body, body)
    assert not any(i.rule == "T5" for i in r.issues)


def test_t5_ratified_to_ratified_with_body_diff_fails(tmp_path):
    prev = adr("RATIFIED", body_marker="## Decision\nold body.\n", with_evidence=True)
    curr = adr("RATIFIED", body_marker="## Decision\nNEW body — silent edit!\n", with_evidence=True)
    p = tmp_path / "ADR-099.md"
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, prev)
    assert any(i.rule == "T5" for i in r.issues), r.render()


def test_t5_does_not_fire_when_status_changes(tmp_path):
    """T5 should only fire on RATIFIED → RATIFIED with body diff, not on
    legitimate transitions like PROPOSED → RATIFIED."""
    prev = adr("PROPOSED", body_marker="## Decision\nold.\n")
    curr = adr("RATIFIED", body_marker="## Decision\nnew.\n", with_evidence=True)
    p = tmp_path / "ADR-099.md"
    p.write_text(curr, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, curr, prev)
    assert not any(i.rule == "T5" for i in r.issues)


def test_t5_normalises_whitespace_and_line_endings(tmp_path):
    """Trailing whitespace + CRLF/LF differences must NOT trip T5."""
    body_lf = adr("RATIFIED", body_marker="## Decision\nbody line.\n", with_evidence=True)
    # Same content, CRLF line endings + trailing whitespace
    body_crlf = body_lf.replace("\n", "\r\n").replace("body line.\r\n", "body line.   \r\n")
    p = tmp_path / "ADR-099.md"
    p.write_text(body_lf, encoding="utf-8")
    r = validate_adr_lifecycle.validate_pair(p, body_lf, body_crlf)
    assert not any(i.rule == "T5" for i in r.issues), r.render()


# --- Tests: CLI -------------------------------------------------------------


def test_main_previous_mode_passes_legal_transition(tmp_path, capsys):
    prev_file = tmp_path / "prev.md"
    prev_file.write_text(adr("PROPOSED"), encoding="utf-8")
    curr_file = tmp_path / "ADR-099.md"
    curr_file.write_text(adr("RATIFIED", with_evidence=True), encoding="utf-8")
    rc = validate_adr_lifecycle.main(["--previous", str(prev_file), str(curr_file)])
    assert rc == 0


def test_main_previous_mode_fails_illegal_transition(tmp_path):
    prev_file = tmp_path / "prev.md"
    prev_file.write_text(adr("RATIFIED", with_evidence=True), encoding="utf-8")
    curr_file = tmp_path / "ADR-099.md"
    curr_file.write_text(adr("PROPOSED"), encoding="utf-8")
    rc = validate_adr_lifecycle.main(["--previous", str(prev_file), str(curr_file)])
    assert rc == 1


def test_main_json_output(tmp_path, capsys):
    curr = tmp_path / "ADR-099.md"
    curr.write_text(adr("PROPOSED"), encoding="utf-8")
    validate_adr_lifecycle.main([str(curr), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, list)


# --- Tests: --base mode (real git plumbing in temp repo) --------------------


def test_main_base_mode_against_temp_repo(tmp_path):
    """Spin up a temp git repo, commit a previous version, modify, and verify
    --base mode picks up the previous version correctly."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    # Layout that matches the validator's expectation
    decisions_dir = repo / "platform" / "docs" / "decisions"
    decisions_dir.mkdir(parents=True)
    adr_file = decisions_dir / "ADR-099-temp.md"

    # Commit 1: PROPOSED
    adr_file.write_text(adr("PROPOSED"), encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)

    # Modify: PROPOSED -> RATIFIED (legal)
    adr_file.write_text(adr("RATIFIED", with_evidence=True), encoding="utf-8")

    # Run validator with --base main from the repo dir
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--base", "main",
        str(adr_file.relative_to(repo)),
    ]
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    # Now make an illegal transition: RATIFIED -> PROPOSED
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "ratify"], cwd=repo, check=True)
    adr_file.write_text(adr("PROPOSED"), encoding="utf-8")

    # Now base=HEAD (the just-made ratify commit); current = working tree (PROPOSED)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "HEAD", str(adr_file.relative_to(repo))],
        cwd=repo, capture_output=True, text=True,
    )
    assert proc.returncode == 1, f"expected illegal-transition fail; stdout:\n{proc.stdout}"


def test_main_base_mode_treats_new_file_as_no_prev(tmp_path):
    """A file not yet in the base ref is a new file; prev=None should apply."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    decisions_dir = repo / "platform" / "docs" / "decisions"
    decisions_dir.mkdir(parents=True)
    placeholder = decisions_dir / "PLACEHOLDER.txt"
    placeholder.write_text("anchor", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)

    new_adr = decisions_dir / "ADR-099-new.md"
    new_adr.write_text(adr("PROPOSED"), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "main", str(new_adr.relative_to(repo))],
        cwd=repo, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"new PROPOSED file should pass; stdout:\n{proc.stdout}"


# --- Tests: determinism ------------------------------------------------------


def test_validation_is_deterministic(tmp_path):
    p = tmp_path / "ADR-099.md"
    curr = adr("RATIFIED", with_evidence=True)
    prev = adr("PROPOSED")
    p.write_text(curr, encoding="utf-8")
    r1 = validate_adr_lifecycle.validate_pair(p, curr, prev)
    r2 = validate_adr_lifecycle.validate_pair(p, curr, prev)
    r3 = validate_adr_lifecycle.validate_pair(p, curr, prev)
    assert r1.to_dict() == r2.to_dict() == r3.to_dict()

#!/usr/bin/env python3
"""ADR lifecycle state-machine validator — Stage 28.4 of Deterministic ADR Gate Pipeline.

Validates Status transitions on ADR markdown files against the allowed
transition graph. Per task #28 — Deterministic ADR Gate Pipeline. Pure
stdlib + git plumbing for diffing against base ref. Deterministic.

Allowed transitions (state machine):

  (none)      ──> DRAFT, PROPOSED, OPEN              (new file)
  DRAFT       ──> DRAFT, PROPOSED                    (can edit + promote)
  OPEN        ──> OPEN, PROPOSED                     (legacy, can edit + promote)
  PROPOSED    ──> PROPOSED, RATIFIED, SUPERSEDED, CLOSED   (can edit, ratify, supersede)
  CLOSED      ──> CLOSED, SUPERSEDED                 (legacy terminal-ish)
  RATIFIED    ──> RATIFIED-with-no-body-diff, SUPERSEDED   (immutable except via supersede)
  SUPERSEDED  ──> SUPERSEDED                         (terminal)

Rules:
  T1 — Status value valid (echoes R3 from format validator, defensive cross-check).
  T2 — Transition (prev_status → curr_status) is in the allowed set.
  T3 — RATIFIED requires evidence ([CONFIRMED] or [ASSUMED: accepted-by=...]).
  T4 — SUPERSEDED requires '## Supersedes' section naming a specific ADR-NNN.
  T5 — RATIFIED → RATIFIED with body changes is FORBIDDEN (immutability rule
       from decisions/README.md). Fires only when a previous ratified
       version is provided.

Usage:
  validate_adr_lifecycle.py --previous PREV.md CURRENT.md
      Compare two specific files. Used by tests and offline checks.

  validate_adr_lifecycle.py --base REF [PATH...]
      For each PATH, extract previous version from git ref REF (e.g.
      'origin/main' or 'HEAD~1') and validate the transition. PATH defaults
      to all ADR-*.md files in platform/docs/decisions/.

  validate_adr_lifecycle.py --json   # machine-readable output

Exit code: 0 = all transitions legal; 1 = at least one illegal.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

VALID_STATUSES = {"OPEN", "DRAFT", "PROPOSED", "CLOSED", "SUPERSEDED", "RATIFIED"}

# Map: previous_status (None if new file) -> set of allowed current_statuses.
ALLOWED_TRANSITIONS: dict[str | None, set[str]] = {
    None:         {"DRAFT", "PROPOSED", "OPEN"},
    "DRAFT":      {"DRAFT", "PROPOSED"},
    "OPEN":       {"OPEN", "PROPOSED"},
    "PROPOSED":   {"PROPOSED", "RATIFIED", "SUPERSEDED", "CLOSED"},
    "CLOSED":     {"CLOSED", "SUPERSEDED"},
    "RATIFIED":   {"RATIFIED", "SUPERSEDED"},
    "SUPERSEDED": {"SUPERSEDED"},
}

STATUS_RE = re.compile(r"^\*\*Status:\*\*\s+([A-Z_]+)\b", re.MULTILINE)
CONFIRMED_RE = re.compile(r"\[CONFIRMED\]|\[CONFIRMED:")
ASSUMED_ACCEPTED_RE = re.compile(r"\[ASSUMED:\s*accepted-by=")
SUPERSEDES_SECTION_RE = re.compile(r"^\s*##\s+Supersedes\b", re.MULTILINE)
SUPERSEDES_FIELD_RE = re.compile(r"\*\*Supersedes:\*\*\s+ADR-\d{3}\b")
SUPERSEDES_REF_RE = re.compile(r"\bADR-\d{3}\b")


@dataclass
class Issue:
    rule: str
    severity: str
    message: str

    def render(self) -> str:
        return f"  {self.severity:4s}  {self.rule}: {self.message}"


@dataclass
class Result:
    file: Path
    issues: list[Issue] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(i.severity == "FAIL" for i in self.issues)

    @property
    def status_word(self) -> str:
        return "FAIL" if self.has_failures else "PASS"

    def render(self) -> str:
        lines = [f"{self.file.name}: {self.status_word}"]
        for i in self.issues:
            lines.append(i.render())
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "file": str(self.file),
            "status": self.status_word,
            "issues": [
                {"rule": i.rule, "severity": i.severity, "message": i.message}
                for i in self.issues
            ],
        }


# --- Status extraction -------------------------------------------------------


def extract_status(text: str) -> str | None:
    """Return Status value from header, or None if absent / invalid."""
    for line in text.split("\n")[:30]:
        m = STATUS_RE.match(line)
        if m:
            value = m.group(1)
            return value if value in VALID_STATUSES else None
    return None


def normalise_body(text: str) -> str:
    """Strip header + status line for body-diff comparison.

    The body starts after the first blank line following the header
    metadata block. Whitespace on each line is rstripped to absorb
    trailing-whitespace edits. CRLF/LF differences are normalised.
    """
    # Drop header lines: '#', '**Field:**', and blank lines until first
    # markdown section heading or substantial paragraph.
    lines = text.replace("\r\n", "\n").split("\n")
    # Find first '## ' line; everything before is treated as header.
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("## "):
            body_start = i
            break
    body_lines = [ln.rstrip() for ln in lines[body_start:]]
    return "\n".join(body_lines).strip()


# --- Validation rules --------------------------------------------------------


def _check_status_value(text: str, label: str) -> tuple[str | None, list[Issue]]:
    issues: list[Issue] = []
    status = extract_status(text)
    if status is None:
        issues.append(Issue("T1", "FAIL", f"{label} version: no valid Status field found"))
    return status, issues


def _check_transition(prev: str | None, curr: str | None) -> list[Issue]:
    if curr is None:
        return []  # T1 already reported
    allowed = ALLOWED_TRANSITIONS.get(prev, set())
    if curr not in allowed:
        prev_label = repr(prev) if prev is not None else "(new file)"
        return [
            Issue(
                "T2",
                "FAIL",
                f"illegal transition {prev_label} -> {curr!r}; allowed: {sorted(allowed)}",
            )
        ]
    return []


def _check_ratified_evidence(text: str, status: str | None) -> list[Issue]:
    if status != "RATIFIED":
        return []
    if not (CONFIRMED_RE.search(text) or ASSUMED_ACCEPTED_RE.search(text)):
        return [
            Issue(
                "T3",
                "FAIL",
                "RATIFIED requires at least one [CONFIRMED] tag OR "
                "[ASSUMED: accepted-by=...] (CONTRACT §A.6, §B.2)",
            )
        ]
    return []


def _check_superseded_field(text: str, status: str | None) -> list[Issue]:
    if status != "SUPERSEDED":
        return []
    has_section = SUPERSEDES_SECTION_RE.search(text) is not None
    has_field = SUPERSEDES_FIELD_RE.search(text) is not None
    if not (has_section or has_field):
        return [
            Issue(
                "T4",
                "FAIL",
                "SUPERSEDED requires '## Supersedes' section or '**Supersedes:** ADR-NNN' field",
            )
        ]
    # Also require the section/field cite a specific ADR-NNN
    if has_section:
        # Look at the body of the section for ADR-NNN ref
        section_match = re.search(
            r"^\s*##\s+Supersedes\b(.*?)(?=^##\s+|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if section_match and not SUPERSEDES_REF_RE.search(section_match.group(1)):
            return [
                Issue(
                    "T4",
                    "FAIL",
                    "## Supersedes section must name a specific ADR-NNN",
                )
            ]
    return []


def _check_immutability(
    prev_text: str | None,
    curr_text: str,
    prev_status: str | None,
    curr_status: str | None,
) -> list[Issue]:
    """T5: RATIFIED → RATIFIED forbids body content changes."""
    if prev_status != "RATIFIED" or curr_status != "RATIFIED":
        return []
    if prev_text is None:
        return []
    if normalise_body(prev_text) != normalise_body(curr_text):
        return [
            Issue(
                "T5",
                "FAIL",
                "RATIFIED ADR body changed in-place; create a new ADR with "
                "Supersedes: <this-NNN> instead (decisions/README.md rule 2)",
            )
        ]
    return []


# --- Driver ------------------------------------------------------------------


def validate_pair(
    current_path: Path,
    current_text: str,
    previous_text: str | None,
) -> Result:
    """Validate a current ADR against an optional previous version."""
    result = Result(file=current_path)

    curr_status, issues = _check_status_value(current_text, "current")
    result.issues.extend(issues)

    prev_status: str | None = None
    if previous_text is not None:
        prev_status, prev_issues = _check_status_value(previous_text, "previous")
        # T1 on previous is informational; don't block if previous looks malformed
        # but DO surface as warning for visibility.
        for i in prev_issues:
            result.issues.append(Issue(i.rule, "WARN", "previous version: " + i.message))

    result.issues.extend(_check_transition(prev_status, curr_status))
    result.issues.extend(_check_ratified_evidence(current_text, curr_status))
    result.issues.extend(_check_superseded_field(current_text, curr_status))
    result.issues.extend(_check_immutability(previous_text, current_text, prev_status, curr_status))
    return result


# --- Git integration ---------------------------------------------------------


def get_file_at_ref(ref: str, path: Path) -> str | None:
    """Return file contents at git ref, or None if file did not exist there."""
    rel = path.as_posix()
    cmd = ["git", "show", f"{ref}:{rel}"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("error: git not found in PATH", file=sys.stderr)
        sys.exit(2)
    if proc.returncode != 0:
        # File didn't exist at ref (new file in this PR), or ref invalid
        return None
    return proc.stdout


# --- CLI --------------------------------------------------------------------


def discover_default_paths() -> list[Path]:
    here = Path(__file__).resolve()
    decisions = here.parent.parent / "docs" / "decisions"
    if not decisions.is_dir():
        print(f"error: default ADR directory not found: {decisions}", file=sys.stderr)
        sys.exit(2)
    paths = sorted(decisions.glob("ADR-*.md"))
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument(
        "--previous",
        type=Path,
        default=None,
        help="path to previous version of the ADR (test/offline mode)",
    )
    mode.add_argument(
        "--base",
        type=str,
        default=None,
        help="git ref of the base branch (e.g. 'origin/main') to diff against (CI mode)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="ADR markdown files to validate (default: all in platform/docs/decisions/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON output",
    )
    args = parser.parse_args(argv)

    paths = list(args.paths) if args.paths else discover_default_paths()

    # --previous mode requires exactly one current path
    if args.previous is not None:
        if len(paths) != 1:
            parser.error("--previous requires exactly one current path")
        curr_path = paths[0]
        try:
            curr_text = curr_path.read_text(encoding="utf-8")
            prev_text = args.previous.read_text(encoding="utf-8")
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        results = [validate_pair(curr_path, curr_text, prev_text)]
    elif args.base is not None:
        results = []
        for p in paths:
            try:
                curr_text = p.read_text(encoding="utf-8")
            except OSError as e:
                r = Result(file=p)
                r.issues.append(Issue("T0", "FAIL", f"could not read current: {e}"))
                results.append(r)
                continue
            prev_text = get_file_at_ref(args.base, p)
            results.append(validate_pair(p, curr_text, prev_text))
    else:
        # No previous reference at all → treat each ADR as new file (prev=None).
        # Useful for sanity check: would the *current* state of every ADR be
        # a legal new-file submission? Mostly catches malformed Status fields.
        results = []
        for p in paths:
            try:
                curr_text = p.read_text(encoding="utf-8")
            except OSError as e:
                r = Result(file=p)
                r.issues.append(Issue("T0", "FAIL", f"could not read: {e}"))
                results.append(r)
                continue
            results.append(validate_pair(p, curr_text, None))

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            print(r.render())
        n_pass = sum(1 for r in results if r.status_word == "PASS")
        n_fail = sum(1 for r in results if r.status_word == "FAIL")
        print()
        print(f"summary: {n_pass} PASS, {n_fail} FAIL  (total {len(results)})")

    return 1 if any(r.has_failures for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""ADR format validator — Stage 28.1 of Deterministic ADR Gate Pipeline.

Validates ADR markdown files against the canonical template documented in
`platform/docs/decisions/README.md` lines 41-79. Pure stdlib, no network,
deterministic. Designed to substitute for human review on the *correctness*
portion of ADR submission per CONTRACT §B.8(a) deterministic check, leaving
*judgment* portions (option choice, vocabulary scope) to human distinct-actor.

Per task #28 — Deterministic ADR Gate Pipeline.

Exit code:
  0 — all ADRs pass.
  1 — at least one ADR fails (or, with --strict, also fails on warnings).

Usage:
  validate_adr.py                       # validate all ADRs in default dir
  validate_adr.py PATH...               # validate specific files
  validate_adr.py --strict              # treat warnings as failures
  validate_adr.py --json                # emit JSON-array report
  validate_adr.py --baseline PATH       # subtract pre-existing issues from
                                        # this baseline JSON file (default:
                                        # platform/docs/decisions/.adr_validator_baseline.json)
  validate_adr.py --no-baseline         # ignore baseline (raw run)
  validate_adr.py --regen-baseline PATH # write current findings as baseline
                                        # and exit 0 (admin-only, freezes
                                        # current drift in place)

Default ADR directory: platform/docs/decisions/
README, _template, and review-* files are skipped.

The baseline file lets the validator be enforced on NEW issues only while
legacy drift is tracked but not blocking. Each baseline entry is an exact
(rule, message) pair per file; if a file's actual issue exactly matches a
baseline entry, it is silently filtered. Any NEW issue still fails.

Exit code semantics: a "FAIL" is a structural defect that the validator
catches deterministically; a "WARN" is a soft signal that needs human
judgment. CI gate uses --strict; pre-commit uses default.

In --strict mode, W2 ([UNKNOWN] tags) is renamed and re-severitied to
R9 FAIL — every new ADR submission is required to either resolve all
[UNKNOWN] tags before merge OR document the blocking gate explicitly
in a baselined entry. This forces resolution-path discipline at
authoring time per AntiShortcutSound §6.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# --- Constants ---------------------------------------------------------------

VALID_STATUSES = {"OPEN", "PROPOSED", "CLOSED", "SUPERSEDED", "RATIFIED"}

REQUIRED_SECTIONS = (
    "## Context",
    "## Decision",
    "## Rationale",
    "## Alternatives considered",
    "## Consequences",
)

# Filename: ADR-NNN-<kebab-case>.md  (NNN is 3-digit zero-padded)
FILENAME_RE = re.compile(r"^ADR-(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# Title line:  '# ADR-NNN — <anything>'  (em-dash U+2014, OR ASCII " - " also accepted as fallback)
TITLE_RE = re.compile(r"^#\s+ADR-(\d{3})\s+[—\-]\s+\S")

# Status:  '**Status:** <VALUE>'  — VALUE is the first word, may have annotations after
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s+([A-Z_]+)\b")

# Date:  '**Date:** YYYY-MM-DD'
DATE_RE = re.compile(r"^\*\*Date:\*\*\s+(\d{4}-\d{2}-\d{2})\b")

# Top-level bullet inside a section (used to count alternatives)
BULLET_RE = re.compile(r"^\s*[-*]\s+\S")

# Evidence tags
CONFIRMED_RE = re.compile(r"\[CONFIRMED\]|\[CONFIRMED:")
ASSUMED_ACCEPTED_RE = re.compile(r"\[ASSUMED:\s*accepted-by=")
UNKNOWN_RE = re.compile(r"\[UNKNOWN\]|\[UNKNOWN:")
SUPERSEDES_RE = re.compile(r"^\s*##\s+Supersedes\b|^\s*\*\*Supersedes:\*\*", re.MULTILINE)


# --- Result types ------------------------------------------------------------


@dataclass
class Issue:
    rule: str
    severity: str  # "FAIL" or "WARN"
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
    def has_warnings(self) -> bool:
        return any(i.severity == "WARN" for i in self.issues)

    @property
    def status_word(self) -> str:
        if self.has_failures:
            return "FAIL"
        if self.has_warnings:
            return "WARN"
        return "PASS"

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


# --- Validation rules --------------------------------------------------------


def _extract_section(text: str, header: str) -> str | None:
    """Return the text of `## <header>` block (until next `## ` or EOF), or None."""
    pattern = re.compile(
        rf"^{re.escape(header)}\s*\n(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def _check_filename(path: Path) -> tuple[str | None, list[Issue]]:
    """Return (filename_NNN, issues). filename_NNN is None on failure."""
    issues: list[Issue] = []
    m = FILENAME_RE.match(path.name)
    if not m:
        issues.append(Issue("R1", "FAIL", f"filename does not match 'ADR-NNN-<kebab>.md' (got {path.name!r})"))
        return None, issues
    return m.group(1), issues


def _check_title(text: str, expected_nnn: str | None) -> list[Issue]:
    issues: list[Issue] = []
    first_line = text.split("\n", 1)[0] if text else ""
    m = TITLE_RE.match(first_line)
    if not m:
        issues.append(Issue("R2", "FAIL", f"line 1 must match '# ADR-NNN — <title>' (got {first_line[:80]!r})"))
        return issues
    if expected_nnn is not None and m.group(1) != expected_nnn:
        issues.append(Issue("R2", "FAIL", f"title NNN ({m.group(1)}) != filename NNN ({expected_nnn})"))
    return issues


def _check_status(text: str) -> tuple[str | None, list[Issue]]:
    issues: list[Issue] = []
    for line in text.split("\n")[:30]:
        m = STATUS_RE.match(line)
        if m:
            value = m.group(1)
            if value not in VALID_STATUSES:
                issues.append(Issue("R3", "FAIL", f"Status value {value!r} not in {sorted(VALID_STATUSES)}"))
                return None, issues
            return value, issues
    issues.append(Issue("R3", "FAIL", "missing '**Status:** <VALUE>' line in header (first 30 lines)"))
    return None, issues


def _check_date(text: str) -> list[Issue]:
    issues: list[Issue] = []
    for line in text.split("\n")[:30]:
        if DATE_RE.match(line):
            return issues
    issues.append(Issue("R4", "FAIL", "missing '**Date:** YYYY-MM-DD' line in header (first 30 lines)"))
    return issues


def _check_required_sections(text: str) -> list[Issue]:
    issues: list[Issue] = []
    for header in REQUIRED_SECTIONS:
        # Match header at start-of-line (allow trailing whitespace/extra inline content)
        if not re.search(rf"^{re.escape(header)}\b", text, re.MULTILINE):
            issues.append(Issue("R5", "FAIL", f"missing required section: {header!r}"))
    return issues


def _check_alternatives_count(text: str) -> list[Issue]:
    issues: list[Issue] = []
    section = _extract_section(text, "## Alternatives considered")
    if section is None:
        # R5 already reports it; don't double-report.
        return issues
    bullets = [ln for ln in section.split("\n") if BULLET_RE.match(ln)]
    if len(bullets) < 2:
        issues.append(
            Issue(
                "R6",
                "FAIL",
                f"'## Alternatives considered' must have >=2 bullets (FORMAL P21); found {len(bullets)}",
            )
        )
    return issues


def _check_ratified_evidence(text: str, status: str | None) -> list[Issue]:
    issues: list[Issue] = []
    if status != "RATIFIED":
        return issues
    if not (CONFIRMED_RE.search(text) or ASSUMED_ACCEPTED_RE.search(text)):
        issues.append(
            Issue(
                "R7",
                "FAIL",
                "Status=RATIFIED requires at least one [CONFIRMED] tag OR an "
                "[ASSUMED: accepted-by=...] tag (CONTRACT §A.6, §B.2)",
            )
        )
    return issues


def _check_superseded_field(text: str, status: str | None) -> list[Issue]:
    issues: list[Issue] = []
    if status != "SUPERSEDED":
        return issues
    if not SUPERSEDES_RE.search(text):
        issues.append(
            Issue(
                "R8",
                "FAIL",
                "Status=SUPERSEDED requires '## Supersedes' section or '**Supersedes:**' field",
            )
        )
    return issues


def _check_unknown_warnings(text: str) -> list[Issue]:
    issues: list[Issue] = []
    matches = UNKNOWN_RE.findall(text)
    if matches:
        issues.append(
            Issue(
                "W2",
                "WARN",
                f"{len(matches)} [UNKNOWN] tag(s) present — verify each has explicit resolution path",
            )
        )
    return issues


# --- Driver ------------------------------------------------------------------


def validate_file(path: Path) -> Result:
    result = Result(file=path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        result.issues.append(Issue("R0", "FAIL", f"could not read file: {e}"))
        return result

    nnn, issues = _check_filename(path)
    result.issues.extend(issues)
    result.issues.extend(_check_title(text, nnn))
    status, issues = _check_status(text)
    result.issues.extend(issues)
    result.issues.extend(_check_date(text))
    result.issues.extend(_check_required_sections(text))
    result.issues.extend(_check_alternatives_count(text))
    result.issues.extend(_check_ratified_evidence(text, status))
    result.issues.extend(_check_superseded_field(text, status))
    result.issues.extend(_check_unknown_warnings(text))
    return result


def discover_default_paths() -> list[Path]:
    here = Path(__file__).resolve()
    decisions = here.parent.parent / "docs" / "decisions"
    if not decisions.is_dir():
        print(f"error: default ADR directory not found: {decisions}", file=sys.stderr)
        sys.exit(2)
    paths = sorted(decisions.glob("ADR-*.md"))
    paths = [p for p in paths if not p.name.startswith("ADR-_")]  # skip templates
    return paths


def default_baseline_path() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "docs" / "decisions" / ".adr_validator_baseline.json"


def load_baseline(path: Path) -> dict[str, set[tuple[str, str]]]:
    """Return {filename: {(rule, message), ...}}. Empty if file missing."""
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"warning: could not parse baseline {path}: {e}", file=sys.stderr)
        return {}
    out: dict[str, set[tuple[str, str]]] = {}
    for filename, entries in raw.items():
        out[filename] = {(e["rule"], e["message"]) for e in entries}
    return out


def apply_baseline(
    results: list[Result],
    baseline: dict[str, set[tuple[str, str]]],
) -> list[Result]:
    """Filter out issues that exactly match baseline entries."""
    filtered: list[Result] = []
    for r in results:
        keys = baseline.get(r.file.name, set())
        if not keys:
            filtered.append(r)
            continue
        new_issues = [
            i for i in r.issues
            if (i.rule, i.message) not in keys
        ]
        filtered.append(Result(file=r.file, issues=new_issues))
    return filtered


def write_baseline(path: Path, results: list[Result]) -> None:
    """Serialise current findings as the new baseline."""
    out: dict[str, list[dict]] = {}
    for r in results:
        if r.issues:
            out[r.file.name] = [
                {"rule": i.rule, "severity": i.severity, "message": i.message}
                for i in r.issues
            ]
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="ADR markdown files to validate (default: all in platform/docs/decisions/)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures (CI gate mode)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON array instead of human report",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="path to baseline JSON; default = .adr_validator_baseline.json next to ADRs",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="ignore baseline file (raw run)",
    )
    parser.add_argument(
        "--regen-baseline",
        type=Path,
        default=None,
        metavar="PATH",
        help="write current findings as baseline JSON and exit 0",
    )
    args = parser.parse_args(argv)

    paths: Iterable[Path] = args.paths or discover_default_paths()
    raw_results = [validate_file(p) for p in paths]

    if args.regen_baseline is not None:
        write_baseline(args.regen_baseline, raw_results)
        n_files = sum(1 for r in raw_results if r.issues)
        n_issues = sum(len(r.issues) for r in raw_results)
        print(f"baseline written to {args.regen_baseline}: {n_files} files, {n_issues} issues frozen")
        return 0

    if args.no_baseline:
        results = raw_results
    else:
        baseline_path = args.baseline if args.baseline is not None else default_baseline_path()
        baseline = load_baseline(baseline_path)
        results = apply_baseline(raw_results, baseline)

    # --strict mode: W2 ([UNKNOWN] tags) is escalated to R9 FAIL, visibly
    # in the output (not only at exit-code level). New submissions can't
    # silently pass with unresolved UNKNOWNs.
    if args.strict:
        for r in results:
            for i in r.issues:
                if i.rule == "W2":
                    i.rule = "R9"
                    i.severity = "FAIL"
                    i.message = (
                        "[UNKNOWN] tag(s) present without resolution path "
                        "(R9 = W2 in --strict; AntiShortcutSound §6)"
                    )

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            print(r.render())
        n_pass = sum(1 for r in results if r.status_word == "PASS")
        n_warn = sum(1 for r in results if r.status_word == "WARN")
        n_fail = sum(1 for r in results if r.status_word == "FAIL")
        print()
        print(f"summary: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL  (total {len(results)})")

    has_failures = any(r.has_failures for r in results)
    has_warnings = any(r.has_warnings for r in results)
    if has_failures:
        return 1
    if args.strict and has_warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

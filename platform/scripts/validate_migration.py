#!/usr/bin/env python3
"""SQL migration validator — Stage 28.2a of Deterministic ADR Gate Pipeline.

Validates SQL migration drafts in `platform/docs/migrations_drafts/*.sql`
(and, later, `platform/alembic/versions/*.py`) against Forge migration
conventions. Pure stdlib; deterministic; no DB connection.

Per task #28 — Deterministic ADR Gate Pipeline (Stage 28.2a).

This stage validates *Forge-convention compliance*:
  - file naming
  - DRAFT-status header marker
  - BEGIN/COMMIT pairing for the up() body
  - reversal block §99 with matching DROP/ALTER for every CREATE/ALTER
  - verification queries §101 present (post-up assertions)
  - idempotency markers (IF NOT EXISTS / IF EXISTS / pg_constraint guard)
  - no destructive defaults (DROP TABLE without IF EXISTS, etc.)

Stage 28.2b (live PG up→down→up cycle) is a separate validator that
requires Docker; deferred to CI workflow per PLAN_ADR_GATE_PIPELINE §6.

Exit code:
  0 — all migrations pass.
  1 — at least one migration fails (or, with --strict, also fails on warnings).

Usage:
  validate_migration.py                  # validate all migrations_drafts/*.sql
  validate_migration.py PATH...          # validate specific files
  validate_migration.py --strict         # treat warnings as failures
  validate_migration.py --json           # emit JSON-array report
  validate_migration.py --baseline PATH  # subtract pre-existing issues
  validate_migration.py --no-baseline    # ignore baseline (raw run)
  validate_migration.py --regen-baseline PATH  # write current findings as baseline

Default migrations directory: platform/docs/migrations_drafts/
README.md and *.draft files are skipped.
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

# Filename: YYYY_MM_DD_<name>.sql
FILENAME_RE = re.compile(r"^(\d{4}_\d{2}_\d{2})_[a-z0-9]+(?:_[a-z0-9]+)*\.sql$")

# Header markers
HEADER_DRAFT_RE = re.compile(r"^--\s+(?:Status|status):\s+(DRAFT|READY|APPLIED)", re.MULTILINE)
HEADER_DRAFT_INLINE_RE = re.compile(r"^--\s+DRAFT\b|^--\s+\*+\s*DRAFT", re.MULTILINE)
ADR_REF_RE = re.compile(r"\bADR-\d{3}\b")

# Up/down boundaries (Forge convention — §99 marker comment)
SECTION_99_RE = re.compile(r"^--\s*§\s*99\.?\s+REVERSAL\b", re.MULTILINE | re.IGNORECASE)
SECTION_101_RE = re.compile(r"^--\s*§\s*101\.?\s+(?:Verification|VERIFICATION)\b", re.MULTILINE)

# Up()-body markers
BEGIN_RE = re.compile(r"^\s*BEGIN\s*;", re.MULTILINE | re.IGNORECASE)
COMMIT_RE = re.compile(r"^\s*COMMIT\s*;", re.MULTILINE | re.IGNORECASE)

# DDL statement detectors (the matching reversal pairs)
CREATE_TYPE_RE = re.compile(r"\bCREATE\s+TYPE\s+(\w+)\s+AS\s+ENUM\b", re.IGNORECASE)
DROP_TYPE_RE = re.compile(r"\bDROP\s+TYPE\s+(?:IF\s+EXISTS\s+)?(\w+)\b", re.IGNORECASE)

CREATE_TABLE_RE = re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\b", re.IGNORECASE)
DROP_TABLE_RE = re.compile(r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)\b", re.IGNORECASE)

ADD_COLUMN_RE = re.compile(
    r"\bALTER\s+TABLE\s+(\w+)\s+(?:[^;]*?\b)?ADD\s+COLUMN(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)",
    re.IGNORECASE | re.DOTALL,
)
DROP_COLUMN_RE = re.compile(
    r"\bALTER\s+TABLE\s+(\w+)\s+(?:[^;]*?\b)?DROP\s+COLUMN(?:\s+IF\s+EXISTS)?\s+(\w+)",
    re.IGNORECASE | re.DOTALL,
)

# Idempotency: must not see CREATE TABLE without IF NOT EXISTS in up-body, etc.
CREATE_TABLE_NO_IFNE_RE = re.compile(
    r"\bCREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\b)(\w+)",
    re.IGNORECASE,
)
DROP_DESTRUCTIVE_RE = re.compile(
    r"\bDROP\s+TABLE\s+(?!IF\s+EXISTS\b)(\w+)",
    re.IGNORECASE,
)


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


# --- Section extraction ------------------------------------------------------


def _extract_up_body(text: str) -> str:
    """Return text of the up()-body: everything between first BEGIN; and §99
    marker (or first COMMIT followed by §99). Falls back to whole text if
    no §99 marker."""
    section_99_match = SECTION_99_RE.search(text)
    if section_99_match:
        return text[: section_99_match.start()]
    # No §99 marker — treat whole file as up-body for analysis
    return text


def _extract_reversal_section(text: str) -> str | None:
    section_99_match = SECTION_99_RE.search(text)
    if not section_99_match:
        return None
    section_101_match = SECTION_101_RE.search(text)
    if section_101_match and section_101_match.start() > section_99_match.start():
        return text[section_99_match.end() : section_101_match.start()]
    return text[section_99_match.end() :]


# --- Validation rules --------------------------------------------------------


def _check_filename(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    if not FILENAME_RE.match(path.name):
        issues.append(
            Issue(
                "M1",
                "FAIL",
                f"filename does not match 'YYYY_MM_DD_<kebab>.sql' (got {path.name!r})",
            )
        )
    return issues


def _check_header_status(text: str) -> list[Issue]:
    issues: list[Issue] = []
    head = "\n".join(text.split("\n")[:30])
    if not (HEADER_DRAFT_RE.search(head) or HEADER_DRAFT_INLINE_RE.search(head)):
        issues.append(
            Issue(
                "M2",
                "FAIL",
                "header (first 30 lines) must declare status: '-- Status: DRAFT|READY|APPLIED' or contain '-- DRAFT' marker",
            )
        )
    return issues


def _check_adr_reference(text: str) -> list[Issue]:
    issues: list[Issue] = []
    head = "\n".join(text.split("\n")[:30])
    if not ADR_REF_RE.search(head):
        issues.append(
            Issue(
                "M3",
                "FAIL",
                "header (first 30 lines) must reference at least one ADR-NNN as the gating decision",
            )
        )
    return issues


def _check_begin_commit_pairing(text: str) -> list[Issue]:
    issues: list[Issue] = []
    up_body = _extract_up_body(text)
    n_begin = len(BEGIN_RE.findall(up_body))
    n_commit = len(COMMIT_RE.findall(up_body))
    if n_begin == 0:
        issues.append(Issue("M4", "FAIL", "up-body has no BEGIN; statement"))
    if n_commit == 0:
        issues.append(Issue("M4", "FAIL", "up-body has no COMMIT; statement"))
    if n_begin != n_commit and n_begin > 0 and n_commit > 0:
        issues.append(
            Issue(
                "M4",
                "FAIL",
                f"up-body BEGIN count ({n_begin}) != COMMIT count ({n_commit})",
            )
        )
    return issues


def _check_reversal_section(text: str) -> list[Issue]:
    issues: list[Issue] = []
    if not SECTION_99_RE.search(text):
        issues.append(Issue("M5", "FAIL", "missing reversal block ('-- §99 REVERSAL ...')"))
    return issues


def _check_verification_section(text: str) -> list[Issue]:
    issues: list[Issue] = []
    if not SECTION_101_RE.search(text):
        issues.append(
            Issue(
                "M6",
                "FAIL",
                "missing verification block ('-- §101 Verification ...') — provides G_5.1 ExitGate evidence",
            )
        )
    return issues


def _check_reversal_pairing(text: str) -> list[Issue]:
    """Every CREATE TABLE in up-body has a matching DROP TABLE in §99.
    Every CREATE TYPE in up-body has a matching DROP TYPE in §99.
    Every ADD COLUMN in up-body has a matching DROP COLUMN in §99."""
    issues: list[Issue] = []
    up_body = _extract_up_body(text)
    reversal = _extract_reversal_section(text)
    if reversal is None:
        # M5 already reports it; don't double-report.
        return issues

    up_tables = {m.group(1).lower() for m in CREATE_TABLE_RE.finditer(up_body)}
    rev_tables = {m.group(1).lower() for m in DROP_TABLE_RE.finditer(reversal)}
    missing_tables = up_tables - rev_tables
    for t in sorted(missing_tables):
        issues.append(
            Issue(
                "M7",
                "FAIL",
                f"CREATE TABLE {t!r} in up-body has no matching DROP TABLE in §99",
            )
        )

    up_types = {m.group(1).lower() for m in CREATE_TYPE_RE.finditer(up_body)}
    rev_types = {m.group(1).lower() for m in DROP_TYPE_RE.finditer(reversal)}
    missing_types = up_types - rev_types
    for t in sorted(missing_types):
        issues.append(
            Issue(
                "M7",
                "FAIL",
                f"CREATE TYPE {t!r} in up-body has no matching DROP TYPE in §99",
            )
        )

    up_columns = {(m.group(1).lower(), m.group(2).lower()) for m in ADD_COLUMN_RE.finditer(up_body)}
    rev_columns = {(m.group(1).lower(), m.group(2).lower()) for m in DROP_COLUMN_RE.finditer(reversal)}
    missing_columns = up_columns - rev_columns
    for table, col in sorted(missing_columns):
        issues.append(
            Issue(
                "M7",
                "FAIL",
                f"ADD COLUMN {table}.{col} in up-body has no matching DROP COLUMN in §99",
            )
        )
    return issues


def _check_idempotency(text: str) -> list[Issue]:
    """In the up-body, CREATE TABLE without IF NOT EXISTS is a soft warning
    (re-running would fail). Same for ENUM blocks needing pg_type guards."""
    issues: list[Issue] = []
    up_body = _extract_up_body(text)

    bad_creates = CREATE_TABLE_NO_IFNE_RE.findall(up_body)
    for table in bad_creates:
        issues.append(
            Issue(
                "M8",
                "WARN",
                f"CREATE TABLE {table!r} without IF NOT EXISTS — second run will fail",
            )
        )

    # CREATE TYPE without DO $$ pg_type guard around it (heuristic):
    # Find each CREATE TYPE; check that within ~20 lines preceding there is
    # a `DO $$` block that mentions pg_type and the same type name.
    for m in CREATE_TYPE_RE.finditer(up_body):
        type_name = m.group(1)
        # Look back ~500 chars for a DO $$ block referencing this type
        window_start = max(0, m.start() - 500)
        window = up_body[window_start : m.end()]
        if not (re.search(r"DO\s+\$\$", window) and "pg_type" in window):
            issues.append(
                Issue(
                    "M8",
                    "WARN",
                    f"CREATE TYPE {type_name!r} without 'DO $$ ... pg_type ... END $$' idempotency guard",
                )
            )
    return issues


def _check_destructive(text: str) -> list[Issue]:
    """No DROP TABLE without IF EXISTS in up-body (only allowed in §99)."""
    issues: list[Issue] = []
    up_body = _extract_up_body(text)
    bad_drops = DROP_DESTRUCTIVE_RE.findall(up_body)
    for table in bad_drops:
        issues.append(
            Issue(
                "M9",
                "FAIL",
                f"DROP TABLE {table!r} without IF EXISTS in up-body — partial-failure path will leave broken state",
            )
        )
    return issues


# --- Driver ------------------------------------------------------------------


def validate_file(path: Path) -> Result:
    result = Result(file=path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        result.issues.append(Issue("M0", "FAIL", f"could not read file: {e}"))
        return result

    result.issues.extend(_check_filename(path))
    result.issues.extend(_check_header_status(text))
    result.issues.extend(_check_adr_reference(text))
    result.issues.extend(_check_begin_commit_pairing(text))
    result.issues.extend(_check_reversal_section(text))
    result.issues.extend(_check_verification_section(text))
    result.issues.extend(_check_reversal_pairing(text))
    result.issues.extend(_check_idempotency(text))
    result.issues.extend(_check_destructive(text))
    return result


def discover_default_paths() -> list[Path]:
    here = Path(__file__).resolve()
    drafts = here.parent.parent / "docs" / "migrations_drafts"
    if not drafts.is_dir():
        print(f"error: default migrations directory not found: {drafts}", file=sys.stderr)
        sys.exit(2)
    paths = sorted(drafts.glob("*.sql"))
    return paths


def default_baseline_path() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "docs" / "migrations_drafts" / ".migration_validator_baseline.json"


def load_baseline(path: Path) -> dict[str, set[tuple[str, str]]]:
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
    filtered: list[Result] = []
    for r in results:
        keys = baseline.get(r.file.name, set())
        if not keys:
            filtered.append(r)
            continue
        new_issues = [i for i in r.issues if (i.rule, i.message) not in keys]
        filtered.append(Result(file=r.file, issues=new_issues))
    return filtered


def write_baseline(path: Path, results: list[Result]) -> None:
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
        help="SQL migration files to validate (default: platform/docs/migrations_drafts/*.sql)",
    )
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--baseline", type=Path, default=None, help="baseline JSON path")
    parser.add_argument("--no-baseline", action="store_true", help="ignore baseline")
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

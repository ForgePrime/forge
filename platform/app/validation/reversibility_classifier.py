"""ReversibilityClassifier — Phase C Stage C.4 (heuristic portion).

Per FORMAL_PROPERTIES_v2 P5 (Reversibility):
    Every mutation classified:
    REVERSIBLE | COMPENSATABLE | RECONSTRUCTABLE | IRREVERSIBLE
    Default on ambiguity = IRREVERSIBLE (fail-safe).

This module ships the pure-function CLASSIFIER. The Rollback service
that consumes the classification (Rollback.attempt) is deferred — it
needs to actually execute against the filesystem / DB / git, which
requires platform-up.

Heuristic per PLAN_QUALITY_ASSURANCE C.4 work item 2:
- Add-only (new file, append-only line additions) -> REVERSIBLE
- DROP TABLE / DELETE FROM / file delete / git rm -> IRREVERSIBLE
- ALTER COLUMN / schema-migrating UPDATE -> RECONSTRUCTABLE (with backup)
- INSERT/UPDATE on non-destructive paths -> COMPENSATABLE
- Default on ambiguity -> IRREVERSIBLE (fail-safe)

Determinism (P6): pure function over Change content. Same diff text -> same
classification across all runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ReversibilityClass(str, Enum):
    """Per FORMAL P5 four-bucket classification."""

    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    RECONSTRUCTABLE = "RECONSTRUCTABLE"
    IRREVERSIBLE = "IRREVERSIBLE"


@dataclass(frozen=True)
class ClassificationResult:
    """Frozen result of classifier."""

    reversibility: ReversibilityClass
    rationale: str
    matched_signals: tuple[str, ...]


# Pattern catalog. Each entry maps a regex (case-insensitive) to a
# (reversibility class, rationale) pair. First match wins; order is
# important — most-irreversible patterns first per fail-safe.
_DESTRUCTIVE_PATTERNS: tuple[tuple[re.Pattern, ReversibilityClass, str], ...] = (
    # IRREVERSIBLE — destructive
    (
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "DROP TABLE: destructive schema change",
    ),
    (
        re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "DROP DATABASE: destructive",
    ),
    (
        re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "TRUNCATE: destroys all rows",
    ),
    (
        re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "DELETE FROM: destroys rows (no soft-delete column visible)",
    ),
    (
        re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "rm -rf: filesystem deletion",
    ),
    (
        re.compile(r"\bgit\s+rm\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "git rm: file deletion in tracked tree",
    ),
    (
        re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
        ReversibilityClass.IRREVERSIBLE,
        "DROP COLUMN: destroys data",
    ),
    # RECONSTRUCTABLE — invasive but reconstructable from backup
    (
        re.compile(r"\bALTER\s+TABLE.*\bALTER\s+COLUMN\b", re.IGNORECASE | re.DOTALL),
        ReversibilityClass.RECONSTRUCTABLE,
        "ALTER COLUMN: schema change reconstructable via backup",
    ),
    (
        re.compile(r"\bALTER\s+TABLE.*\bRENAME\s+COLUMN\b", re.IGNORECASE | re.DOTALL),
        ReversibilityClass.RECONSTRUCTABLE,
        "RENAME COLUMN: reversible by symmetric rename",
    ),
    # COMPENSATABLE — UPDATE on data (rollback via opposite UPDATE)
    (
        re.compile(r"\bUPDATE\b.*\bSET\b", re.IGNORECASE | re.DOTALL),
        ReversibilityClass.COMPENSATABLE,
        "UPDATE: compensatable via opposite UPDATE",
    ),
    # REVERSIBLE — purely additive
    (
        re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE),
        ReversibilityClass.REVERSIBLE,
        "CREATE TABLE: reversible via DROP TABLE on rollback",
    ),
    (
        re.compile(r"\bADD\s+COLUMN\b", re.IGNORECASE),
        ReversibilityClass.REVERSIBLE,
        "ADD COLUMN: reversible via DROP COLUMN on rollback",
    ),
    (
        re.compile(r"\bCREATE\s+INDEX\b", re.IGNORECASE),
        ReversibilityClass.REVERSIBLE,
        "CREATE INDEX: reversible via DROP INDEX",
    ),
    (
        re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
        ReversibilityClass.REVERSIBLE,
        "INSERT INTO: reversible via DELETE of inserted row IDs",
    ),
)


@dataclass(frozen=True)
class DiffSummary:
    """Summary of a Change's diff. Caller builds; classifier reads."""

    files_added: tuple[str, ...] = ()
    files_modified: tuple[str, ...] = ()
    files_deleted: tuple[str, ...] = ()
    diff_text: str = ""  # raw unified-diff content for keyword scanning


def classify(diff: DiffSummary) -> ClassificationResult:
    """Classify a Change diff into a reversibility class.

    Matching policy (deterministic):
    1. If files_deleted is non-empty -> IRREVERSIBLE (file deletion).
    2. Else scan diff_text against _DESTRUCTIVE_PATTERNS in order;
       first match wins.
    3. If only files_added (no modifications, no destructive patterns)
       -> REVERSIBLE.
    4. If files_modified but no destructive patterns matched ->
       COMPENSATABLE (caller can compute reverse-edit).
    5. Default -> IRREVERSIBLE (fail-safe per P5 binding).

    Args:
        diff: DiffSummary describing the Change.

    Returns:
        ClassificationResult with reversibility class + rationale +
        list of matched signal strings.

    Per CONTRACT §B.5 fail-safe: ambiguous input always classifies to
    IRREVERSIBLE rather than guessing a more permissive class.
    """
    matched: list[str] = []

    # Rule 1: deleted files always IRREVERSIBLE.
    if diff.files_deleted:
        matched.append(f"files_deleted={list(diff.files_deleted)}")
        return ClassificationResult(
            reversibility=ReversibilityClass.IRREVERSIBLE,
            rationale=f"file deletion ({len(diff.files_deleted)} file(s))",
            matched_signals=tuple(matched),
        )

    # Rule 2: scan diff_text for destructive SQL / shell patterns.
    for pattern, cls, rationale in _DESTRUCTIVE_PATTERNS:
        m = pattern.search(diff.diff_text)
        if m:
            matched.append(f"{pattern.pattern}={m.group(0)!r}")
            return ClassificationResult(
                reversibility=cls,
                rationale=rationale,
                matched_signals=tuple(matched),
            )

    # Rule 3: only-added files, no destructive patterns -> REVERSIBLE.
    if diff.files_added and not diff.files_modified and not diff.diff_text.strip():
        return ClassificationResult(
            reversibility=ReversibilityClass.REVERSIBLE,
            rationale=(
                f"add-only change ({len(diff.files_added)} new file(s), "
                f"no modifications, no destructive patterns)"
            ),
            matched_signals=("files_added_only",),
        )

    # Rule 4: only-modifications, no destructive patterns -> COMPENSATABLE.
    if diff.files_modified and not diff.files_deleted:
        return ClassificationResult(
            reversibility=ReversibilityClass.COMPENSATABLE,
            rationale=(
                f"modifications only ({len(diff.files_modified)} file(s)), "
                f"no destructive patterns"
            ),
            matched_signals=("files_modified_compensatable",),
        )

    # Rule 5: default fail-safe.
    return ClassificationResult(
        reversibility=ReversibilityClass.IRREVERSIBLE,
        rationale="ambiguous diff; defaulting to IRREVERSIBLE per P5 fail-safe",
        matched_signals=("default_failsafe",),
    )

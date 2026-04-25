"""Tests for ReversibilityClassifier — Phase C Stage C.4.

Pure-Python tests over DiffSummary inputs. Verifies the heuristic
matches expected reversibility class for every pattern in the catalog
+ fail-safe default behaviour.
"""

from __future__ import annotations

from app.validation.reversibility_classifier import (
    ClassificationResult,
    DiffSummary,
    ReversibilityClass,
    classify,
)


# --- IRREVERSIBLE patterns ----------------------------------------------


def test_drop_table_classifies_irreversible():
    diff = DiffSummary(diff_text="DROP TABLE users;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE
    assert "DROP TABLE" in result.rationale


def test_drop_database_irreversible():
    diff = DiffSummary(diff_text="DROP DATABASE forge;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_truncate_irreversible():
    diff = DiffSummary(diff_text="TRUNCATE users CASCADE;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_delete_from_irreversible():
    diff = DiffSummary(diff_text="DELETE FROM users WHERE id=1;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE
    assert "DELETE" in result.rationale


def test_rm_rf_irreversible():
    diff = DiffSummary(diff_text="rm -rf /tmp/cache")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_git_rm_irreversible():
    diff = DiffSummary(diff_text="git rm old_file.py")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_drop_column_irreversible():
    diff = DiffSummary(diff_text="ALTER TABLE users DROP COLUMN deprecated;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_files_deleted_irreversible_regardless_of_diff_text():
    """File deletion always wins -> IRREVERSIBLE even with no diff_text."""
    diff = DiffSummary(files_deleted=("old_module.py",), diff_text="")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE
    assert "deletion" in result.rationale.lower()


def test_files_deleted_priority_over_create_table():
    """Even if diff_text contains CREATE TABLE, file deletion wins."""
    diff = DiffSummary(
        files_deleted=("dropped.py",),
        diff_text="CREATE TABLE new_table (id INT);",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


# --- RECONSTRUCTABLE patterns -------------------------------------------


def test_alter_column_reconstructable():
    diff = DiffSummary(
        diff_text="ALTER TABLE users ALTER COLUMN email TYPE TEXT;",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.RECONSTRUCTABLE


def test_rename_column_reconstructable():
    diff = DiffSummary(
        diff_text="ALTER TABLE users RENAME COLUMN email TO email_address;",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.RECONSTRUCTABLE


# --- COMPENSATABLE patterns ---------------------------------------------


def test_update_set_compensatable():
    diff = DiffSummary(
        diff_text="UPDATE users SET status='ACTIVE' WHERE id=1;",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.COMPENSATABLE


def test_modifications_only_compensatable():
    """File modifications without destructive patterns -> COMPENSATABLE."""
    diff = DiffSummary(
        files_modified=("app/api/foo.py",),
        diff_text="def renamed_fn(): pass\n",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.COMPENSATABLE


# --- REVERSIBLE patterns ------------------------------------------------


def test_create_table_reversible():
    diff = DiffSummary(
        diff_text="CREATE TABLE new_table (id INT PRIMARY KEY);",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.REVERSIBLE


def test_add_column_reversible():
    diff = DiffSummary(
        diff_text="ALTER TABLE users ADD COLUMN new_col TEXT;",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.REVERSIBLE


def test_create_index_reversible():
    diff = DiffSummary(
        diff_text="CREATE INDEX ix_users_email ON users(email);",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.REVERSIBLE


def test_insert_into_reversible():
    diff = DiffSummary(
        diff_text="INSERT INTO users (id, name) VALUES (1, 'alice');",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.REVERSIBLE


def test_files_added_only_reversible():
    """Pure file additions, no diff text, no modifications -> REVERSIBLE."""
    diff = DiffSummary(
        files_added=("app/new_module.py",),
        diff_text="",
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.REVERSIBLE
    assert "add-only" in result.rationale


# --- Default fail-safe (IRREVERSIBLE) -----------------------------------


def test_empty_diff_returns_irreversible_failsafe():
    """No signals at all -> IRREVERSIBLE per P5 fail-safe."""
    diff = DiffSummary()  # all empty
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE
    assert "fail-safe" in result.rationale.lower()


# --- Pattern priority (destructive wins over additive) ------------------


def test_drop_wins_over_create_when_both_present():
    """Diff with both DROP and CREATE -> IRREVERSIBLE (destructive wins)."""
    diff = DiffSummary(
        diff_text=(
            "CREATE TABLE temp (id INT);\n"
            "DROP TABLE old_users;\n"
        ),
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_delete_wins_over_insert_when_both_present():
    diff = DiffSummary(
        diff_text=(
            "INSERT INTO logs VALUES ('a');\n"
            "DELETE FROM logs WHERE old=true;\n"
        ),
    )
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


# --- Case insensitivity --------------------------------------------------


def test_lowercase_drop_table_detected():
    diff = DiffSummary(diff_text="drop table users;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.IRREVERSIBLE


def test_mixed_case_alter_column_detected():
    diff = DiffSummary(diff_text="Alter Table users Alter Column email Type Text;")
    result = classify(diff)
    assert result.reversibility == ReversibilityClass.RECONSTRUCTABLE


# --- ClassificationResult is frozen -------------------------------------


def test_classification_result_is_frozen():
    diff = DiffSummary(diff_text="CREATE TABLE x (id INT);")
    result = classify(diff)
    try:
        result.reversibility = ReversibilityClass.IRREVERSIBLE  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("ClassificationResult should be frozen")


def test_diff_summary_is_frozen():
    diff = DiffSummary(diff_text="x")
    try:
        diff.diff_text = "y"  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("DiffSummary should be frozen")


# --- Determinism (P6) ---------------------------------------------------


def test_same_diff_same_result():
    diff = DiffSummary(diff_text="CREATE TABLE x (id INT);")
    r1 = classify(diff)
    r2 = classify(diff)
    r3 = classify(diff)
    assert r1 == r2 == r3


def test_matched_signals_populated():
    diff = DiffSummary(diff_text="DROP TABLE users;")
    result = classify(diff)
    assert len(result.matched_signals) >= 1
    assert "DROP" in result.matched_signals[0].upper()


# --- Coverage: every pattern in catalog has a test --------------------


def test_all_reversibility_classes_can_be_returned():
    """Coverage: each ReversibilityClass enum value reachable from classify()."""
    seen: set[ReversibilityClass] = set()
    seen.add(classify(DiffSummary(diff_text="CREATE TABLE x (id INT);")).reversibility)  # REVERSIBLE
    seen.add(classify(DiffSummary(diff_text="UPDATE users SET x=1;")).reversibility)  # COMPENSATABLE
    seen.add(classify(DiffSummary(diff_text="ALTER TABLE u ALTER COLUMN c TYPE T;")).reversibility)  # RECONSTRUCTABLE
    seen.add(classify(DiffSummary(diff_text="DROP TABLE x;")).reversibility)  # IRREVERSIBLE
    assert seen == set(ReversibilityClass)

"""Tests for `platform/scripts/validate_migration.py` — Stage 28.2a SQL migration gate.

Per task #28 Deterministic ADR Gate Pipeline. Tests cover:
  - Each rule M1..M9 fires (or doesn't) as specified
  - Reversal pairing: every CREATE/ALTER in up-body has matching DROP in §99
  - Idempotency warnings (M8) for missing IF NOT EXISTS / pg_type guards
  - Baseline filtering preserves current drift but catches new issues
  - Determinism

Pure stdlib; no DB; no Forge app imports.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Load validate_migration module by file path.
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_migration.py"
spec = importlib.util.spec_from_file_location("validate_migration", SCRIPT)
assert spec is not None and spec.loader is not None
validate_migration = importlib.util.module_from_spec(spec)
sys.modules["validate_migration"] = validate_migration
spec.loader.exec_module(validate_migration)


# --- Fixture builders --------------------------------------------------------


VALID_BODY = """\
-- ============================================================================
-- Status: DRAFT — DO NOT RUN until ADR-099 is RATIFIED
-- File: 2099_01_01_test_migration.sql
-- ============================================================================

BEGIN;

-- §1. ENUM creation
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sample_enum') THEN
    CREATE TYPE sample_enum AS ENUM ('A', 'B');
  END IF;
END $$;

-- §2. table creation
CREATE TABLE IF NOT EXISTS sample_table (
  id BIGSERIAL PRIMARY KEY,
  value TEXT NOT NULL
);

-- §3. column add
ALTER TABLE existing_table ADD COLUMN IF NOT EXISTS new_col TEXT NULL;

COMMIT;

-- §99. REVERSAL — down() equivalent
-- DROP TABLE IF EXISTS sample_table;
-- ALTER TABLE existing_table DROP COLUMN IF EXISTS new_col;
-- DROP TYPE IF EXISTS sample_enum;

-- §101. Verification queries (post-up)
-- SELECT typname FROM pg_type WHERE typname = 'sample_enum';
"""


def write_sql(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# --- Tests: rules -----------------------------------------------------------


def test_valid_migration_passes(tmp_path):
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", VALID_BODY)
    r = validate_migration.validate_file(p)
    assert r.status_word == "PASS", r.render()


def test_filename_bad_pattern_fails_m1(tmp_path):
    p = write_sql(tmp_path, "BAD_NAME.sql", VALID_BODY)
    r = validate_migration.validate_file(p)
    assert "M1" in {i.rule for i in r.issues}


def test_missing_status_header_fails_m2(tmp_path):
    body = VALID_BODY.replace(
        "-- Status: DRAFT — DO NOT RUN until ADR-099 is RATIFIED\n",
        "-- some other comment\n",
    )
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert "M2" in {i.rule for i in r.issues}


def test_missing_adr_reference_fails_m3(tmp_path):
    body = VALID_BODY.replace("ADR-099", "REF-missing")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert "M3" in {i.rule for i in r.issues}


def test_missing_begin_fails_m4(tmp_path):
    body = VALID_BODY.replace("BEGIN;", "-- no BEGIN", 1)
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M4" and "BEGIN" in i.message for i in r.issues)


def test_missing_commit_fails_m4(tmp_path):
    body = VALID_BODY.replace("COMMIT;", "-- no COMMIT", 1)
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M4" and "COMMIT" in i.message for i in r.issues)


def test_missing_reversal_section_fails_m5(tmp_path):
    body = VALID_BODY.replace("-- §99. REVERSAL — down() equivalent", "-- some other note")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert "M5" in {i.rule for i in r.issues}


def test_missing_verification_section_fails_m6(tmp_path):
    body = VALID_BODY.replace("-- §101. Verification queries (post-up)", "-- some other note")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert "M6" in {i.rule for i in r.issues}


def test_create_table_without_drop_in_reversal_fails_m7(tmp_path):
    body = VALID_BODY.replace("-- DROP TABLE IF EXISTS sample_table;\n", "")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M7" and "sample_table" in i.message for i in r.issues)


def test_create_type_without_drop_in_reversal_fails_m7(tmp_path):
    body = VALID_BODY.replace("-- DROP TYPE IF EXISTS sample_enum;\n", "")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M7" and "sample_enum" in i.message for i in r.issues)


def test_add_column_without_drop_in_reversal_fails_m7(tmp_path):
    body = VALID_BODY.replace(
        "-- ALTER TABLE existing_table DROP COLUMN IF EXISTS new_col;\n", ""
    )
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(
        i.rule == "M7" and "existing_table" in i.message and "new_col" in i.message
        for i in r.issues
    )


def test_create_table_without_if_not_exists_warns_m8(tmp_path):
    body = VALID_BODY.replace("CREATE TABLE IF NOT EXISTS sample_table", "CREATE TABLE sample_table")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M8" and "sample_table" in i.message for i in r.issues)


def test_create_type_without_pg_type_guard_warns_m8(tmp_path):
    body = """\
-- Status: DRAFT
-- ADR-099
BEGIN;
CREATE TYPE bare_enum AS ENUM ('X');
COMMIT;
-- §99. REVERSAL
-- DROP TYPE IF EXISTS bare_enum;
-- §101. Verification
"""
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M8" and "bare_enum" in i.message and "pg_type" in i.message for i in r.issues)


def test_destructive_drop_in_up_body_fails_m9(tmp_path):
    body = VALID_BODY.replace(
        "BEGIN;",
        "BEGIN;\nDROP TABLE legacy_thing;",
    )
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    r = validate_migration.validate_file(p)
    assert any(i.rule == "M9" and "legacy_thing" in i.message for i in r.issues)


# --- Tests: baseline filtering ----------------------------------------------


def test_baseline_filters_known_issue(tmp_path):
    body = VALID_BODY.replace("-- DROP TABLE IF EXISTS sample_table;\n", "")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    raw = validate_migration.validate_file(p)
    assert raw.has_failures

    baseline_payload = {
        "2099_01_01_test_migration.sql": [
            {"rule": i.rule, "severity": i.severity, "message": i.message}
            for i in raw.issues
        ]
    }
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps(baseline_payload), encoding="utf-8")

    baseline = validate_migration.load_baseline(baseline_file)
    filtered = validate_migration.apply_baseline([raw], baseline)
    assert filtered[0].issues == []
    assert filtered[0].status_word == "PASS"


# --- Tests: cli main / exit codes -------------------------------------------


def test_main_passes_on_valid_migration(tmp_path):
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", VALID_BODY)
    rc = validate_migration.main([str(p), "--no-baseline"])
    assert rc == 0


def test_main_fails_on_invalid_migration(tmp_path):
    body = VALID_BODY.replace("BEGIN;", "-- no BEGIN", 1)
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    rc = validate_migration.main([str(p), "--no-baseline"])
    assert rc == 1


def test_main_strict_fails_on_warning(tmp_path):
    body = VALID_BODY.replace("CREATE TABLE IF NOT EXISTS sample_table", "CREATE TABLE sample_table")
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", body)
    rc_default = validate_migration.main([str(p), "--no-baseline"])
    rc_strict = validate_migration.main([str(p), "--no-baseline", "--strict"])
    assert rc_default == 0  # warning passes
    assert rc_strict == 1   # warning fails in strict


def test_main_json_output(tmp_path, capsys):
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", VALID_BODY)
    validate_migration.main([str(p), "--no-baseline", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert payload[0]["status"] == "PASS"


# --- Tests: determinism ------------------------------------------------------


def test_validation_is_deterministic(tmp_path):
    p = write_sql(tmp_path, "2099_01_01_test_migration.sql", VALID_BODY)
    r1 = validate_migration.validate_file(p)
    r2 = validate_migration.validate_file(p)
    r3 = validate_migration.validate_file(p)
    assert r1.to_dict() == r2.to_dict() == r3.to_dict()


# --- Tests: real Phase 1 migration draft ------------------------------------


def test_real_phase1_migration_passes():
    """The actual platform/docs/migrations_drafts/2026_04_26_phase1_redesign.sql
    must pass — this is the regression test for the migration that ADR-028 gates."""
    real = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "migrations_drafts"
        / "2026_04_26_phase1_redesign.sql"
    )
    if not real.exists():
        # Optional file; skip if missing (e.g., on a fresh clone before Phase 1)
        return
    r = validate_migration.validate_file(real)
    assert r.status_word == "PASS", f"real migration draft fails:\n{r.render()}"

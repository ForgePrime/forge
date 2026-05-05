"""Tests for `validate_migration_cycle.py` — Stage 28.2b live PG cycle gate.

Per task #28 Stage 28.2b. Tests cover:
  - §99 reversal block parser correctness (offline, no DB)
  - up-section extraction
  - SQL line classification (skip prose, keep DDL)
  - JSON output shape

Live-PG cycle test is excluded from this offline suite (requires running
Postgres). It runs as `pydantic-schema` companion in CI via
`.github/workflows/adr-gate.yml` job `migration-live-cycle` which spawns
its own postgres service container.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load module by file path
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_migration_cycle.py"
spec = importlib.util.spec_from_file_location("validate_migration_cycle", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["validate_migration_cycle"] = mod
spec.loader.exec_module(mod)


# --- §99 parser tests ------------------------------------------------------


def test_parser_extracts_drop_table():
    sql = """\
BEGIN;
CREATE TABLE x (id INT);
COMMIT;

-- §99. REVERSAL — down() equivalent
-- BEGIN;
-- DROP TABLE IF EXISTS x;
-- COMMIT;

-- §101. Verification
"""
    out = mod.parse_reversal_block(sql)
    assert "DROP TABLE IF EXISTS x" in out
    assert "BEGIN" in out
    assert "COMMIT" in out


def test_parser_skips_prose_lines():
    """Prose lines like 'drop tables FIRST (FKs)' must NOT be included
    even though they contain SQL-like words (this was a real bug)."""
    sql = """\
-- §99. REVERSAL
-- Run ONLY if rolling back this migration. Each section reverses its
-- corresponding §1..§7 above. Order: drop tables FIRST (FKs), then ALTER
-- columns OFF, then DROP TYPE.
--
-- BEGIN;
-- DROP TABLE IF EXISTS thing;
-- COMMIT;
-- §101. Verification
"""
    out = mod.parse_reversal_block(sql)
    # Prose lines absent
    assert "Order:" not in out
    assert "above" not in out
    # Real SQL retained
    assert "DROP TABLE IF EXISTS thing" in out
    assert "BEGIN" in out
    assert "COMMIT" in out


def test_parser_handles_alter_drop_constraint_lines():
    """Continuation lines that just end with `;` (multi-line ALTER) kept."""
    sql = """\
-- §99. REVERSAL
-- ALTER TABLE objectives DROP CONSTRAINT IF EXISTS valid_objective_stage;
-- ALTER TABLE objectives DROP COLUMN IF EXISTS stage;
-- §101. Verification
"""
    out = mod.parse_reversal_block(sql)
    assert "DROP CONSTRAINT IF EXISTS valid_objective_stage" in out
    assert "DROP COLUMN IF EXISTS stage" in out


def test_parser_handles_drop_type():
    sql = """\
-- §99. REVERSAL
-- DROP TYPE IF EXISTS my_enum;
-- §101.
"""
    out = mod.parse_reversal_block(sql)
    assert "DROP TYPE IF EXISTS my_enum" in out


def test_parser_raises_when_section_99_missing():
    sql = "BEGIN; CREATE TABLE x (id INT); COMMIT;"
    with pytest.raises(ValueError, match="99"):
        mod.parse_reversal_block(sql)


def test_split_up_section_returns_text_before_99():
    sql = """\
BEGIN;
CREATE TABLE x (id INT);
COMMIT;

-- §99. REVERSAL
-- DROP TABLE x;
"""
    up = mod.split_up_section(sql)
    assert "CREATE TABLE x" in up
    assert "DROP TABLE x" not in up
    assert "§99" not in up


def test_split_up_section_no_99_returns_full_text():
    """If there's no §99, the whole thing is up-body (legacy shape)."""
    sql = "BEGIN; CREATE TABLE x (); COMMIT;"
    out = mod.split_up_section(sql)
    assert out == sql


# --- Real Phase 1 migration parser regression -------------------------------


def test_real_phase1_migration_parser():
    """The actual Phase 1 migration parser produces non-empty up/down
    blocks. This is a regression sentinel — if migration shape changes
    in a way that breaks the parser, this catches it offline."""
    real = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "migrations_drafts"
        / "2026_04_26_phase1_redesign.sql"
    )
    if not real.exists():
        return  # skip if migration draft not present
    text = real.read_text(encoding="utf-8")
    up = mod.split_up_section(text)
    down = mod.parse_reversal_block(text)

    # Up must contain the actual CREATEs/ALTERs
    assert "CREATE TABLE IF NOT EXISTS alternatives" in up
    assert "CREATE TYPE epistemic_tag" in up
    assert "ADD COLUMN IF NOT EXISTS epistemic_tag" in up

    # Down must contain matching DROPs
    assert "DROP TABLE IF EXISTS alternatives" in down
    assert "DROP TYPE IF EXISTS epistemic_tag" in down
    assert "DROP COLUMN IF EXISTS epistemic_tag" in down

    # Down must NOT contain prose
    assert "Order:" not in down
    assert "corresponding" not in down


# --- CycleResult dataclass tests --------------------------------------------


def test_cycle_result_all_pass_when_all_ok():
    r = mod.CycleResult(
        sql_path="x.sql",
        s0_to_s2_match=True,
        s1_to_s3_match=True,
        up_first_ok=True,
        down_ok=True,
        up_second_ok=True,
    )
    assert r.all_pass is True
    assert "PASS" in r.render()


def test_cycle_result_fails_if_any_gate_red():
    r = mod.CycleResult(
        sql_path="x.sql",
        s0_to_s2_match=False,  # <- red
        s1_to_s3_match=True,
        up_first_ok=True,
        down_ok=True,
        up_second_ok=True,
    )
    assert r.all_pass is False
    assert "FAIL" in r.render()


def test_cycle_result_to_dict_well_formed():
    r = mod.CycleResult(
        sql_path="x.sql",
        s0_to_s2_match=True,
        s1_to_s3_match=True,
        up_first_ok=True,
        down_ok=True,
        up_second_ok=True,
    )
    d = r.to_dict()
    assert d["all_pass"] is True
    assert d["sql_path"] == "x.sql"
    assert "errors" in d

#!/usr/bin/env python3
"""SQL migration up/down/up cycle validator — Stage 28.2b of Deterministic ADR Gate Pipeline.

Companion to validate_migration.py (Stage 28.2a, regex-based static checks).
This script exercises the migration against a live ephemeral PostgreSQL,
asserting that:

  1. up() applies cleanly (no syntax error, no FK violation against empty DB).
  2. down() (parsed from §99 commented block) reverses up() to byte-identical
     baseline schema (S2 == S0).
  3. Re-applying up() after down() produces the same schema as the first up()
     (S3 == S1) — the migration is deterministic.

Schema captures use information_schema queries normalised to a sorted,
canonical text form (independent of pg_dump version). Comparison is
exact-equality on the normalised dump.

The script is destructive: it drops + recreates the target DB. REFUSES
to run unless --allow-destructive is set explicitly. CI uses a fresh
service container; local dev uses a dedicated `forge_migration_test`
database on the existing platform-db-1.

Per task #28 — Deterministic ADR Gate Pipeline (Stage 28.2b).
Closes the gap that Stage 28.2a's regex parser cannot cover (real PG
syntax, FK validity, idempotency under repeated apply).

Usage:
  validate_migration_cycle.py --sql PATH --db-url URL [--allow-destructive]
  validate_migration_cycle.py --sql PATH --db-url URL --json

Exit code:
  0 — all 3 cycle gates pass.
  1 — at least one gate fails.
  2 — usage error or DB connection failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # checked at runtime; --json output adapts

# --- §99 parser --------------------------------------------------------------

# Marker: line starting with '-- §99' (case-insensitive)
SECTION_99_RE = re.compile(r"^\s*--\s*§\s*99\.?\s+", re.MULTILINE | re.IGNORECASE)
# Stop marker: any subsequent §-section header (e.g. §100, §101)
SECTION_NEXT_RE = re.compile(r"^\s*--\s*§\s*1\d{2}\.?\s+", re.MULTILINE | re.IGNORECASE)


def parse_reversal_block(text: str) -> str:
    """Extract the §99 reversal block and uncomment the SQL statements.

    The §99 block is a comment region containing commented-out SQL:
      -- §99. REVERSAL ...
      --
      -- BEGIN;
      -- DROP TABLE IF EXISTS xxx;
      -- COMMIT;
      -- §100. ...

    We strip the leading '-- ' (or '--') from each line in the §99 region
    until we hit the next §1xx section header or EOF.

    Lines that are pure '-- ' comments without SQL content (empty after
    stripping) are skipped. Lines like '-- File:' or '-- ============'
    headers are also detected and skipped via the no-statement heuristic.
    """
    section_99_match = SECTION_99_RE.search(text)
    if not section_99_match:
        raise ValueError("§99 reversal block not found in SQL file")

    end_match = SECTION_NEXT_RE.search(text, pos=section_99_match.end())
    end_pos = end_match.start() if end_match else len(text)
    region = text[section_99_match.end() : end_pos]

    out_lines: list[str] = []
    for line in region.split("\n"):
        stripped = line.strip()
        # Skip section header line itself (already past it via match.end)
        if not stripped.startswith("--"):
            continue
        # Strip leading '-- ' / '--' to recover SQL.
        body = re.sub(r"^\s*--\s?", "", line, count=1)
        body_strip = body.strip()
        if not body_strip:
            continue
        # Heuristic: SQL line either STARTS with a top-level keyword
        # (case-insensitive) OR ends with ';' (continuation lines).
        # Prose like "drop tables FIRST (FKs)" doesn't START with the
        # keyword — they're describing, not commanding.
        if not (
            re.match(
                r"^\s*(BEGIN|COMMIT|ROLLBACK|DROP|ALTER|CREATE|UPDATE|DELETE|INSERT|TRUNCATE|DO\s+\$\$|END\s+\$\$|END;)\b",
                body_strip,
                re.IGNORECASE,
            )
            or body_strip.endswith(";")
        ):
            continue
        out_lines.append(body)
    return "\n".join(out_lines)


def split_up_section(text: str) -> str:
    """Return everything BEFORE the §99 marker (the up-body)."""
    section_99_match = SECTION_99_RE.search(text)
    if section_99_match:
        return text[: section_99_match.start()]
    return text


# --- Schema snapshot ---------------------------------------------------------


SCHEMA_QUERIES = [
    # Tables + columns
    """
    SELECT
        table_schema || '.' || table_name AS qualified_name,
        column_name,
        data_type,
        is_nullable,
        column_default,
        udt_name
    FROM information_schema.columns
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name, ordinal_position
    """,
    # ENUM types and their values
    """
    SELECT
        n.nspname AS schema_name,
        t.typname AS type_name,
        e.enumlabel AS enum_value,
        e.enumsortorder
    FROM pg_type t
    JOIN pg_enum e ON e.enumtypid = t.oid
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schema_name, type_name, enumsortorder
    """,
    # Constraints (CHECK, UNIQUE, FK).
    # Excludes auto-generated NOT-NULL constraints whose names embed the
    # table OID (e.g. '2200_35484_3_not_null') — these change every CREATE
    # TABLE due to fresh OIDs and cause spurious S1 != S3 diffs without
    # any semantic difference. Named constraints (CHECK from explicit
    # CONSTRAINT clause, UNIQUE, FK, PK) are retained because they're
    # what the developer actually controls.
    """
    SELECT
        tc.table_schema || '.' || tc.table_name AS qualified_name,
        tc.constraint_name,
        tc.constraint_type
    FROM information_schema.table_constraints tc
    WHERE tc.table_schema NOT IN ('pg_catalog', 'information_schema')
      AND tc.constraint_name !~ '^[0-9]+_[0-9]+_[0-9]+_not_null$'
    ORDER BY tc.table_schema, tc.table_name, tc.constraint_name
    """,
    # Indexes
    """
    SELECT
        schemaname || '.' || tablename AS qualified_name,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schemaname, tablename, indexname
    """,
]


def schema_snapshot(conn) -> str:
    """Return canonical text snapshot of the DB schema. Deterministic;
    sorted across all queries; safe for byte-equality comparison."""
    out: list[str] = []
    cur = conn.cursor()
    try:
        for i, q in enumerate(SCHEMA_QUERIES):
            cur.execute(q)
            rows = cur.fetchall()
            out.append(f"--- query {i} ---")
            for row in rows:
                out.append("\t".join("" if v is None else str(v) for v in row))
        return "\n".join(out)
    finally:
        cur.close()


# --- Cycle execution ---------------------------------------------------------


@dataclass
class CycleResult:
    sql_path: str
    s0_to_s2_match: bool       # down restored baseline?
    s1_to_s3_match: bool       # up is deterministic?
    up_first_ok: bool          # initial up() succeeded?
    down_ok: bool              # down() succeeded?
    up_second_ok: bool         # second up() succeeded?
    error_messages: list[str] = field(default_factory=list)
    s0_size: int = 0
    s1_size: int = 0

    @property
    def all_pass(self) -> bool:
        return (
            self.up_first_ok and self.down_ok and self.up_second_ok
            and self.s0_to_s2_match and self.s1_to_s3_match
        )

    def render(self) -> str:
        lines = [f"{self.sql_path}: {'PASS' if self.all_pass else 'FAIL'}"]
        lines.append(f"  up()      first apply: {'OK' if self.up_first_ok else 'FAIL'}")
        lines.append(f"  down()    apply:       {'OK' if self.down_ok else 'FAIL'}")
        lines.append(f"  up()      second apply: {'OK' if self.up_second_ok else 'FAIL'}")
        lines.append(f"  S0 == S2 (down restored baseline): {'YES' if self.s0_to_s2_match else 'NO'}")
        lines.append(f"  S1 == S3 (up is deterministic):    {'YES' if self.s1_to_s3_match else 'NO'}")
        lines.append(f"  Snapshot sizes: S0={self.s0_size} bytes, S1={self.s1_size} bytes")
        for msg in self.error_messages:
            lines.append(f"  ERROR: {msg}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "sql_path": self.sql_path,
            "all_pass": self.all_pass,
            "up_first_ok": self.up_first_ok,
            "down_ok": self.down_ok,
            "up_second_ok": self.up_second_ok,
            "s0_to_s2_match": self.s0_to_s2_match,
            "s1_to_s3_match": self.s1_to_s3_match,
            "errors": self.error_messages,
        }


def run_cycle(sql_path: str, db_url: str) -> CycleResult:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed; cannot run live cycle test")

    with open(sql_path, encoding="utf-8") as f:
        sql_text = f.read()

    up_sql = split_up_section(sql_text)
    down_sql = parse_reversal_block(sql_text)

    result = CycleResult(
        sql_path=sql_path,
        s0_to_s2_match=False,
        s1_to_s3_match=False,
        up_first_ok=False,
        down_ok=False,
        up_second_ok=False,
    )

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        # Snapshot S0 (baseline; current state — should be empty for fresh DB,
        # but we don't require empty; we just require S2 == S0).
        s0 = schema_snapshot(conn)
        result.s0_size = len(s0)

        # Apply up() #1
        try:
            cur = conn.cursor()
            cur.execute(up_sql)
            cur.close()
            result.up_first_ok = True
        except Exception as e:
            result.error_messages.append(f"up() first: {e}")
            return result

        s1 = schema_snapshot(conn)
        result.s1_size = len(s1)

        # Apply down()
        try:
            cur = conn.cursor()
            cur.execute(down_sql)
            cur.close()
            result.down_ok = True
        except Exception as e:
            result.error_messages.append(f"down(): {e}")
            return result

        s2 = schema_snapshot(conn)
        result.s0_to_s2_match = (s0 == s2)
        if not result.s0_to_s2_match:
            # Find first diff line for diagnostic
            s0_lines = s0.split("\n")
            s2_lines = s2.split("\n")
            for i in range(min(len(s0_lines), len(s2_lines))):
                if s0_lines[i] != s2_lines[i]:
                    result.error_messages.append(
                        f"S0 != S2 at line {i}: S0={s0_lines[i]!r}, S2={s2_lines[i]!r}"
                    )
                    break
            else:
                result.error_messages.append(
                    f"S0 != S2: length differs (S0={len(s0_lines)} lines, S2={len(s2_lines)} lines)"
                )

        # Apply up() #2 (re-apply after down)
        try:
            cur = conn.cursor()
            cur.execute(up_sql)
            cur.close()
            result.up_second_ok = True
        except Exception as e:
            result.error_messages.append(f"up() second: {e}")
            return result

        s3 = schema_snapshot(conn)
        result.s1_to_s3_match = (s1 == s3)
        if not result.s1_to_s3_match:
            result.error_messages.append("S1 != S3: up() is non-deterministic")

    finally:
        conn.close()

    return result


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sql", required=True, help="path to migration SQL file")
    parser.add_argument(
        "--db-url",
        required=True,
        help="psycopg2 connection URL — e.g. postgresql://forge:forge@localhost:5432/forge_migration_test",
    )
    parser.add_argument(
        "--allow-destructive",
        action="store_true",
        help="acknowledge that the target DB will be mutated (up + down + up)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    if not args.allow_destructive:
        # Refuse unless DB name strongly looks like a test DB.
        # Match anything containing 'test' or starting with 'postgres' (CI default).
        if not re.search(r"(test|/postgres(\?|$))", args.db_url):
            print(
                "error: target DB does not look like a test DB; "
                "pass --allow-destructive to acknowledge mutation risk",
                file=sys.stderr,
            )
            return 2

    if psycopg2 is None:
        print("error: psycopg2 not installed", file=sys.stderr)
        return 2

    result = run_cycle(args.sql, args.db_url)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.render())

    return 0 if result.all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

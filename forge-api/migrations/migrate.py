#!/usr/bin/env python3
"""
Forge Platform v2 — Migration Runner

Applies SQL migrations in order, tracking which have been applied
in a `schema_migrations` table.

Usage:
    python migrate.py                          # Apply pending migrations
    python migrate.py --status                 # Show migration status
    python migrate.py --rollback 001           # (future) Rollback migration

Requires: DATABASE_URL environment variable (PostgreSQL connection string)
    Example: postgresql://forge:forge@localhost:5432/forge

Dependencies: psycopg2 (or psycopg[binary])
"""

import os
import re
import sys
import glob
import argparse
from pathlib import Path

try:
    import psycopg2
except ImportError:
    try:
        import psycopg as psycopg2  # psycopg3 compat
    except ImportError:
        print("ERROR: psycopg2 or psycopg required. Install with:")
        print("  pip install psycopg2-binary")
        print("  # or")
        print("  pip install 'psycopg[binary]'")
        sys.exit(1)


MIGRATIONS_DIR = Path(__file__).parent
MIGRATIONS_TABLE = "schema_migrations"


def get_connection():
    """Get database connection from DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable not set.")
        print("Example: export DATABASE_URL=postgresql://forge:forge@localhost:5432/forge")
        sys.exit(1)
    conn = psycopg2.connect(url)
    # Ensure consistent autocommit=False behavior for both psycopg2 and psycopg3
    if hasattr(conn, 'autocommit'):
        conn.autocommit = False
    return conn


def ensure_migrations_table(conn):
    """Create schema_migrations table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                version     TEXT PRIMARY KEY,
                filename    TEXT NOT NULL,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
    conn.commit()


def get_applied_versions(conn):
    """Return set of already-applied migration versions."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT version FROM {MIGRATIONS_TABLE} ORDER BY version;")
        return {row[0] for row in cur.fetchall()}


def discover_migrations():
    """Find all .sql migration files, sorted by filename."""
    pattern = str(MIGRATIONS_DIR / "*.sql")
    files = sorted(glob.glob(pattern))
    migrations = []
    for filepath in files:
        filename = os.path.basename(filepath)
        # Extract version: "001_initial_schema.sql" -> "001"
        version = filename.split("_")[0]
        migrations.append((version, filename, filepath))
    return migrations


def apply_migration(conn, version, filename, filepath):
    """Apply a single migration file within a transaction."""
    print(f"  Applying {filename}...", end=" ", flush=True)

    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    # Strip BEGIN/COMMIT at statement level — we manage the transaction ourselves
    # Only match standalone statements, not occurrences inside comments or strings
    sql_clean = re.sub(r'^\s*BEGIN\s*;\s*$', '', sql, flags=re.MULTILINE)
    sql_clean = re.sub(r'^\s*COMMIT\s*;\s*$', '', sql_clean, flags=re.MULTILINE)

    try:
        with conn.cursor() as cur:
            cur.execute(sql_clean)
            cur.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (version, filename) VALUES (%s, %s);",
                (version, filename),
            )
        conn.commit()
        print("OK")
        return True
    except Exception as e:
        conn.rollback()
        print(f"FAILED\n    Error: {e}")
        return False


def cmd_migrate(args):
    """Apply all pending migrations."""
    conn = get_connection()
    try:
        ensure_migrations_table(conn)

        applied = get_applied_versions(conn)
        migrations = discover_migrations()
        pending = [(v, fn, fp) for v, fn, fp in migrations if v not in applied]

        if not pending:
            print("All migrations already applied.")
            return 0

        print(f"Found {len(pending)} pending migration(s):\n")
        for version, filename, filepath in pending:
            if not apply_migration(conn, version, filename, filepath):
                print(f"\nMigration failed at {filename}. Stopping.")
                return 1

        print(f"\nDone. Applied {len(pending)} migration(s).")
        return 0
    finally:
        conn.close()


def cmd_status(args):
    """Show migration status."""
    conn = get_connection()
    try:
        ensure_migrations_table(conn)

        applied = get_applied_versions(conn)
        migrations = discover_migrations()

        print(f"{'Version':<10} {'Filename':<40} {'Status'}")
        print("-" * 60)
        for version, filename, _ in migrations:
            status = "applied" if version in applied else "PENDING"
            print(f"{version:<10} {filename:<40} {status}")

        return 0
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Forge migration runner")
    parser.add_argument(
        "--status", action="store_true", help="Show migration status"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show pending migrations without applying"
    )
    args = parser.parse_args()

    if args.status:
        return cmd_status(args)

    if args.dry_run:
        migrations = discover_migrations()
        print("Discovered migrations:")
        for v, fn, _ in migrations:
            print(f"  {v}: {fn}")
        return 0

    return cmd_migrate(args)


if __name__ == "__main__":
    sys.exit(main())

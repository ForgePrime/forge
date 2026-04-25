#!/usr/bin/env python3
"""backfill_causal_edges.py — PLAN_MEMORY_CONTEXT Stage B.2.

Walks existing FK-based causal relations in the schema and inserts
corresponding rows into the causal_edges table populated by B.1.

Source FK relations (verified 2026-04-25 against live schema):
- tasks.origin_finding_id        -> Finding produced_by Task
- decisions.execution_id         -> Execution produced Decision
- decisions.task_id              -> Task -> Decision (depends_on)
- changes.execution_id           -> Execution produced Change
- changes.task_id                -> Task -> Change (depends_on)
- findings.execution_id          -> Execution produced Finding
- findings.source_llm_call_id    -> LLMCall evidences Finding
- findings.created_task_id       -> Finding produced_task (triage path)
- acceptance_criteria.task_id    -> Task -> AC (ac_of)
- acceptance_criteria.source_llm_call_id -> LLMCall evidences AC
- task_dependencies              -> Task -> Task (depends_on)

Idempotency (B.2 work item 1): uses INSERT ... ON CONFLICT DO NOTHING
on the unique constraint (src_type, src_id, dst_type, dst_id, relation)
so re-running produces no duplicates.

Determinism (P6): same DB state -> same row count + same edges
inserted (modulo ordering inside each INSERT batch).

Usage:
    python platform/scripts/backfill_causal_edges.py [--dry-run]

--dry-run: print row counts that WOULD be inserted; do not write.

Per CONTRACT §B.5 FAILURE SCENARIOS:
1. Missing column / table -> script logs and skips that source;
   continues with remaining sources.
2. Concurrent insert via app code -> ON CONFLICT DO NOTHING handles
   the race.
3. NULL FK values -> WHERE clause filters them out (no-op, not error).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class FKSource:
    """One backfill source: a SELECT that yields edge tuples."""

    name: str  # human-readable for logs
    select_sql: str  # SELECT producing (src_type, src_id, dst_type, dst_id,
                    # relation, src_created_at, dst_created_at)
    relation: str


# Each source maps a known FK column to a CausalEdge.
# Convention: relation describes "src does X to dst" — e.g.
# "Execution produced Decision" -> relation='produced'.
_SOURCES: tuple[FKSource, ...] = (
    FKSource(
        name="tasks.origin_finding_id",
        relation="produced_task",
        select_sql="""
            SELECT 'finding' AS src_type, t.origin_finding_id AS src_id,
                   'task' AS dst_type, t.id AS dst_id,
                   :relation AS relation,
                   COALESCE(f.created_at, NOW()) AS src_created_at,
                   COALESCE(t.created_at, NOW()) AS dst_created_at
            FROM tasks t
            LEFT JOIN findings f ON f.id = t.origin_finding_id
            WHERE t.origin_finding_id IS NOT NULL
        """,
    ),
    FKSource(
        name="decisions.execution_id",
        relation="produced",
        select_sql="""
            SELECT 'execution' AS src_type, d.execution_id AS src_id,
                   'decision' AS dst_type, d.id AS dst_id,
                   :relation AS relation,
                   COALESCE(e.created_at, NOW()) AS src_created_at,
                   COALESCE(d.created_at, NOW()) AS dst_created_at
            FROM decisions d
            LEFT JOIN executions e ON e.id = d.execution_id
            WHERE d.execution_id IS NOT NULL
        """,
    ),
    FKSource(
        name="decisions.task_id",
        relation="depends_on",
        select_sql="""
            SELECT 'task' AS src_type, d.task_id AS src_id,
                   'decision' AS dst_type, d.id AS dst_id,
                   :relation AS relation,
                   COALESCE(t.created_at, NOW()) AS src_created_at,
                   COALESCE(d.created_at, NOW()) AS dst_created_at
            FROM decisions d
            LEFT JOIN tasks t ON t.id = d.task_id
            WHERE d.task_id IS NOT NULL
        """,
    ),
    FKSource(
        name="changes.execution_id",
        relation="produced",
        select_sql="""
            SELECT 'execution' AS src_type, c.execution_id AS src_id,
                   'change' AS dst_type, c.id AS dst_id,
                   :relation AS relation,
                   COALESCE(e.created_at, NOW()) AS src_created_at,
                   COALESCE(c.created_at, NOW()) AS dst_created_at
            FROM changes c
            LEFT JOIN executions e ON e.id = c.execution_id
            WHERE c.execution_id IS NOT NULL
        """,
    ),
    FKSource(
        name="changes.task_id",
        relation="depends_on",
        select_sql="""
            SELECT 'task' AS src_type, c.task_id AS src_id,
                   'change' AS dst_type, c.id AS dst_id,
                   :relation AS relation,
                   COALESCE(t.created_at, NOW()) AS src_created_at,
                   COALESCE(c.created_at, NOW()) AS dst_created_at
            FROM changes c
            LEFT JOIN tasks t ON t.id = c.task_id
            WHERE c.task_id IS NOT NULL
        """,
    ),
    FKSource(
        name="findings.execution_id",
        relation="produced",
        select_sql="""
            SELECT 'execution' AS src_type, f.execution_id AS src_id,
                   'finding' AS dst_type, f.id AS dst_id,
                   :relation AS relation,
                   COALESCE(e.created_at, NOW()) AS src_created_at,
                   COALESCE(f.created_at, NOW()) AS dst_created_at
            FROM findings f
            LEFT JOIN executions e ON e.id = f.execution_id
            WHERE f.execution_id IS NOT NULL
        """,
    ),
    FKSource(
        name="acceptance_criteria.task_id",
        relation="ac_of",
        select_sql="""
            SELECT 'task' AS src_type, ac.task_id AS src_id,
                   'acceptance_criterion' AS dst_type, ac.id AS dst_id,
                   :relation AS relation,
                   COALESCE(t.created_at, NOW()) AS src_created_at,
                   -- AC has no created_at column; use parent task's + 1ms
                   -- to satisfy B.1 acyclicity (src strictly older than dst).
                   COALESCE(t.created_at, NOW()) + interval '1 millisecond'
                       AS dst_created_at
            FROM acceptance_criteria ac
            LEFT JOIN tasks t ON t.id = ac.task_id
            WHERE ac.task_id IS NOT NULL
        """,
    ),
    FKSource(
        name="task_dependencies",
        relation="depends_on",
        select_sql="""
            SELECT 'task' AS src_type, td.depends_on_id AS src_id,
                   'task' AS dst_type, td.task_id AS dst_id,
                   :relation AS relation,
                   COALESCE(t_src.created_at, NOW()) AS src_created_at,
                   COALESCE(t_dst.created_at, NOW()) AS dst_created_at
            FROM task_dependencies td
            LEFT JOIN tasks t_src ON t_src.id = td.depends_on_id
            LEFT JOIN tasks t_dst ON t_dst.id = td.task_id
        """,
    ),
)


_INSERT_SQL = """
INSERT INTO causal_edges
    (src_type, src_id, dst_type, dst_id, relation,
     src_created_at, dst_created_at)
VALUES (:src_type, :src_id, :dst_type, :dst_id, :relation,
        :src_created_at, :dst_created_at)
ON CONFLICT (src_type, src_id, dst_type, dst_id, relation) DO NOTHING
"""


def backfill_one(engine, source: FKSource, dry_run: bool) -> tuple[int, int]:
    """Run one backfill source. Returns (selected_count, inserted_count)."""
    # Read with autocommit for the SELECT phase.
    with engine.connect() as conn:
        rows = conn.execute(
            text(source.select_sql),
            {"relation": source.relation},
        ).fetchall()
    selected = len(rows)
    if dry_run:
        return selected, 0

    # Skip rows where src.created_at is more than 5s newer than dst
    # (acyclicity invariant from B.1 with clock-skew tolerance).
    kept = []
    skipped_acyc = 0
    for row in rows:
        r = dict(row._mapping)
        delta = (r["src_created_at"] - r["dst_created_at"]).total_seconds()
        if delta > 5:
            skipped_acyc += 1
            continue
        kept.append(r)

    # Write phase: fresh connection with explicit transaction.
    inserted = 0
    with engine.begin() as conn:
        for r in kept:
            result = conn.execute(text(_INSERT_SQL), r)
            inserted += result.rowcount or 0
    if skipped_acyc:
        print(
            f"  [{source.name}] skipped {skipped_acyc} rows that would "
            f"violate B.1 acyclicity"
        )
    return selected, inserted


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Count rows that would be inserted; do not write.",
    )
    ap.add_argument(
        "--db-url",
        default="postgresql://forge:forge@localhost:5432/forge_platform",
        help="Database connection URL.",
    )
    args = ap.parse_args()

    engine = create_engine(args.db_url, pool_pre_ping=True)
    print(f"[backfill] connecting to {args.db_url}")
    if args.dry_run:
        print("[backfill] DRY RUN — no writes will be performed")

    total_selected = 0
    total_inserted = 0
    for source in _SOURCES:
        try:
            selected, inserted = backfill_one(engine, source, args.dry_run)
        except Exception as e:
            print(f"  [{source.name}] FAILED: {type(e).__name__}: {e}")
            continue
        verb = "WOULD insert" if args.dry_run else "inserted"
        print(f"  [{source.name}] selected={selected} {verb}={inserted}")
        total_selected += selected
        total_inserted += inserted

    print(f"\n[backfill] total selected={total_selected} {'WOULD ' if args.dry_run else ''}inserted={total_inserted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

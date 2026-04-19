"""Idempotent ALTER TABLE migrations applied at startup.

Postgres-only. SQLAlchemy's `create_all` adds NEW tables but does NOT add new
columns to existing ones. This helper bridges the gap until proper Alembic
migrations are introduced.

Each migration here is `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` which is
safe to run on every startup.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


# Each entry: (table_name, column_name, column_definition_sql).
PENDING_COLUMNS: list[tuple[str, str, str]] = [
    # G1 — operational contract on project
    ("projects", "contract_md", "TEXT"),
    # B2 — source attribution on AC
    ("acceptance_criteria", "source_ref", "TEXT"),
    # B1 — track AC executions + finding dismissals
    ("acceptance_criteria", "last_executed_at", "TIMESTAMP WITH TIME ZONE"),
    ("findings", "dismissed_reason", "TEXT"),
    ("findings", "dismissed_at", "TIMESTAMP WITH TIME ZONE"),
    # D2 — objective re-open notes
    # (full table created via metadata.create_all)
    # C1 — knowledge source description + focus hint + URL/folder target
    ("knowledge", "description", "TEXT"),
    ("knowledge", "focus_hint", "TEXT"),
    ("knowledge", "target_url", "TEXT"),
    # B4 — reasoning trace: link AC/Finding back to the LLMCall that produced it
    ("acceptance_criteria", "source_llm_call_id", "INTEGER REFERENCES llm_calls(id)"),
    ("findings", "source_llm_call_id", "INTEGER REFERENCES llm_calls(id)"),
    # E1 — execution mode + crafter reference
    ("executions", "mode", "VARCHAR(16)"),
    ("executions", "crafter_call_id", "INTEGER REFERENCES llm_calls(id)"),
    # I1 — project autonomy level
    ("projects", "autonomy_level", "VARCHAR(8)"),
    ("projects", "autonomy_promoted_at", "TIMESTAMP WITH TIME ZONE"),
    # I3 — objective-level watchlist opt-out
    ("objectives", "autonomy_optout", "BOOLEAN DEFAULT false"),
    # Objective detail mockup 09 — first-class test scenarios + challenger checks
    ("objectives", "test_scenarios", "JSONB"),
    ("objectives", "challenger_checks", "JSONB"),
    # Mockup 04 — pause orchestrate run
    ("orchestrate_runs", "pause_requested", "BOOLEAN DEFAULT false"),
    ("orchestrate_runs", "paused_at", "TIMESTAMP WITH TIME ZONE"),
    ("orchestrate_runs", "resumed_at", "TIMESTAMP WITH TIME ZONE"),
    # P2.1 — link chore tasks back to the finding that spawned them
    ("tasks", "origin_finding_id", "INTEGER REFERENCES findings(id) ON DELETE SET NULL"),
    # P3.4 — per-objective KB scoping (which sources matter for this objective)
    ("objectives", "kb_focus_ids", "INTEGER[]"),
    # P3.5 — per-source "last consulted" timestamp (audit + pruning hint)
    ("knowledge", "last_read_at", "TIMESTAMP WITH TIME ZONE"),
    # P5.7 — orphan-run detection. OrchestrateRun didn't have TimestampMixin; adding now.
    # created_at already set via server_default on existing rows — this adds updated_at.
    ("orchestrate_runs", "updated_at", "TIMESTAMP WITH TIME ZONE"),
    # P5.8 — per-skill timeout override for hook invocations.
    ("skills", "recommended_timeout_sec", "INTEGER"),
    # CGAID Artifact #4 Handoff — explicit risks list per task
    # Shape: list[{risk: str, mitigation: str, severity: "LOW|MEDIUM|HIGH", owner: str|null}]
    ("tasks", "risks", "JSONB"),
]


def _replace_check_constraint(conn, table: str, name: str, new_check: str) -> None:
    """Drop + recreate a CHECK constraint (Postgres has no ALTER CHECK)."""
    try:
        conn.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}'))
        conn.execute(text(f'ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({new_check})'))
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Failed to replace check %s on %s: %s", name, table, e)


def apply(engine) -> None:
    """Run all idempotent ALTERs. Errors are logged but do not abort startup."""
    with engine.begin() as conn:
        for table, col, ddl in PENDING_COLUMNS:
            try:
                stmt = text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}')
                conn.execute(stmt)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("Schema migration failed for %s.%s: %s", table, col, e)

        # D1 — extend Task.type CHECK constraint to include analysis/planning/develop/documentation.
        _replace_check_constraint(
            conn, "tasks", "valid_task_type",
            "type IN ('feature', 'bug', 'chore', 'investigation', "
            "'analysis', 'planning', 'develop', 'documentation')",
        )

        # B1 — relax Finding constraints + extend status enum to include DISMISSED/ACCEPTED.
        _replace_check_constraint(
            conn, "findings", "valid_finding_type",
            "type IN ('bug', 'improvement', 'risk', 'dependency', 'question', "
            "'smell', 'opportunity', 'gap', 'lint')",
        )
        _replace_check_constraint(
            conn, "findings", "valid_finding_severity",
            "severity IN ('HIGH', 'MEDIUM', 'LOW', 'high', 'medium', 'low', "
            "'critical', 'CRITICAL')",
        )
        _replace_check_constraint(
            conn, "findings", "valid_finding_status",
            "status IN ('OPEN', 'APPROVED', 'DEFERRED', 'REJECTED', 'DISMISSED', 'ACCEPTED')",
        )
        # P1.1 — include PAUSED. P5.6 — include PARTIAL_FAIL (run completed its
        # task pool but at least one task FAILED, so DONE would be misleading).
        # P5.7 — include INTERRUPTED (worker thread killed mid-run, e.g. server restart).
        _replace_check_constraint(
            conn, "orchestrate_runs", "valid_orchestrate_run_status",
            "status IN ('PENDING','RUNNING','PAUSED','DONE','FAILED','CANCELLED','BUDGET_EXCEEDED','PARTIAL_FAIL','INTERRUPTED')",
        )
        try:
            conn.execute(text('ALTER TABLE findings ALTER COLUMN execution_id DROP NOT NULL'))
        except Exception as e:  # pragma: no cover
            logger.warning("relax findings.execution_id failed: %s", e)
        try:
            conn.execute(text('ALTER TABLE findings ALTER COLUMN evidence DROP NOT NULL'))
        except Exception as e:  # pragma: no cover
            logger.warning("relax findings.evidence failed: %s", e)

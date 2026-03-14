"""WorkflowStore — asyncpg persistence for workflow executions.

D-002: Postgres persistence (user override).
Uses raw asyncpg parameterized queries — no ORM.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import asyncpg

from app.workflow.models import (
    ExecutionStatus,
    StepResult,
    StepStatus,
    WorkflowExecution,
)


def _parse_jsonb(val: Any) -> dict[str, Any] | None:
    """Parse JSONB value — asyncpg may return str or dict depending on codec setup."""
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    return json.loads(val)


def _row_to_execution(row: asyncpg.Record, step_rows: list[asyncpg.Record] | None = None) -> WorkflowExecution:
    """Map DB row(s) to WorkflowExecution model."""
    step_results: dict[str, StepResult] = {}
    if step_rows:
        for sr in step_rows:
            step_results[sr["step_id"]] = StepResult(
                step_id=sr["step_id"],
                status=StepStatus(sr["status"]),
                started_at=sr["started_at"],
                completed_at=sr["completed_at"],
                output=_parse_jsonb(sr["output"]),
                session_id=sr["session_id"],
                error=sr["error"],
                decision_ids=list(sr["decision_ids"]) if sr["decision_ids"] else [],
                retries=sr["retries"],
            )
    variables = _parse_jsonb(row["variables"]) or {}
    return WorkflowExecution(
        id=row["id"],
        ext_id=row["ext_id"],
        workflow_def_id=row["workflow_def_id"],
        project_id=row["project_id"],
        objective_id=row["objective_id"],
        status=ExecutionStatus(row["status"]),
        current_step=row["current_step"],
        step_results=step_results,
        pause_reason=row["pause_reason"],
        variables=variables,
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


class WorkflowStore:
    """Persistence layer for workflow executions — asyncpg raw SQL."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def generate_ext_id(self, project_id: int) -> str:
        """Generate sequential WE-NNN ext_id for a project."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM workflow_executions WHERE project_id = $1",
                project_id,
            )
            seq = (row["cnt"] or 0) + 1
            return f"WE-{seq:03d}"

    async def create_execution(
        self,
        project_id: int,
        workflow_def_id: str,
        objective_id: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Create a new workflow execution."""
        ext_id = await self.generate_ext_id(project_id)
        vars_json = json.dumps(variables or {})
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO workflow_executions
                   (ext_id, project_id, workflow_def_id, objective_id, status, variables)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                   RETURNING *""",
                ext_id, project_id, workflow_def_id, objective_id,
                ExecutionStatus.pending.value, vars_json,
            )
            return _row_to_execution(row)

    async def get_execution(self, execution_id: int) -> WorkflowExecution | None:
        """Get execution by internal DB id, with step results."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_executions WHERE id = $1", execution_id
            )
            if not row:
                return None
            step_rows = await conn.fetch(
                "SELECT * FROM workflow_step_results WHERE execution_id = $1",
                execution_id,
            )
            return _row_to_execution(row, step_rows)

    async def get_execution_by_ext_id(
        self, project_id: int, ext_id: str
    ) -> WorkflowExecution | None:
        """Get execution by project + ext_id (WE-001)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_executions WHERE project_id = $1 AND ext_id = $2",
                project_id, ext_id,
            )
            if not row:
                return None
            step_rows = await conn.fetch(
                "SELECT * FROM workflow_step_results WHERE execution_id = $1",
                row["id"],
            )
            return _row_to_execution(row, step_rows)

    async def list_executions(
        self, project_id: int, status_filter: str | None = None
    ) -> list[WorkflowExecution]:
        """List executions for a project, optionally filtered by status."""
        async with self._pool.acquire() as conn:
            if status_filter:
                rows = await conn.fetch(
                    "SELECT * FROM workflow_executions WHERE project_id = $1 AND status = $2 ORDER BY created_at DESC",
                    project_id, status_filter,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM workflow_executions WHERE project_id = $1 ORDER BY created_at DESC",
                    project_id,
                )
            executions = []
            for row in rows:
                step_rows = await conn.fetch(
                    "SELECT * FROM workflow_step_results WHERE execution_id = $1",
                    row["id"],
                )
                executions.append(_row_to_execution(row, step_rows))
            return executions

    async def update_execution(self, execution_id: int, **fields: Any) -> WorkflowExecution | None:
        """Update execution fields atomically."""
        if not fields:
            return await self.get_execution(execution_id)

        allowed = {
            "status", "current_step", "variables", "pause_reason",
            "error", "completed_at",
        }
        invalid = set(fields) - allowed
        if invalid:
            raise ValueError(f"Cannot update fields: {invalid}")

        set_clauses = []
        params: list[Any] = []
        idx = 1

        for key, value in fields.items():
            idx += 1
            if key == "variables":
                set_clauses.append(f"variables = ${idx}::jsonb")
                params.append(json.dumps(value) if isinstance(value, dict) else value)
            elif key == "status":
                set_clauses.append(f"status = ${idx}")
                params.append(value.value if isinstance(value, ExecutionStatus) else value)
            else:
                set_clauses.append(f"{key} = ${idx}")
                params.append(value)

        set_clauses.append(f"updated_at = ${idx + 1}")
        params.append(datetime.now(timezone.utc))

        sql = f"UPDATE workflow_executions SET {', '.join(set_clauses)} WHERE id = $1 RETURNING *"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, execution_id, *params)
            if not row:
                return None
            step_rows = await conn.fetch(
                "SELECT * FROM workflow_step_results WHERE execution_id = $1",
                execution_id,
            )
            return _row_to_execution(row, step_rows)

    async def update_step_result(
        self, execution_id: int, step_id: str, **fields: Any
    ) -> StepResult:
        """Upsert a step result — insert if not exists, update otherwise."""
        status = fields.get("status", StepStatus.pending)
        if isinstance(status, StepStatus):
            status = status.value

        output = fields.get("output")
        output_json = json.dumps(output) if output is not None else None

        session_id = fields.get("session_id")
        error = fields.get("error")
        decision_ids = fields.get("decision_ids", [])
        retries = fields.get("retries", 0)
        started_at = fields.get("started_at")
        completed_at = fields.get("completed_at")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO workflow_step_results
                   (execution_id, step_id, status, output, session_id, error,
                    decision_ids, retries, started_at, completed_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10)
                   ON CONFLICT (execution_id, step_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    output = COALESCE(EXCLUDED.output, workflow_step_results.output),
                    session_id = COALESCE(EXCLUDED.session_id, workflow_step_results.session_id),
                    error = EXCLUDED.error,
                    decision_ids = EXCLUDED.decision_ids,
                    retries = EXCLUDED.retries,
                    started_at = COALESCE(workflow_step_results.started_at, EXCLUDED.started_at),
                    completed_at = EXCLUDED.completed_at
                   RETURNING *""",
                execution_id, step_id, status, output_json, session_id, error,
                decision_ids, retries, started_at, completed_at,
            )
            return StepResult(
                step_id=row["step_id"],
                status=StepStatus(row["status"]),
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                output=_parse_jsonb(row["output"]),
                session_id=row["session_id"],
                error=row["error"],
                decision_ids=list(row["decision_ids"]) if row["decision_ids"] else [],
                retries=row["retries"],
            )

    async def transition_status(
        self, execution_id: int, from_status: ExecutionStatus, to_status: ExecutionStatus
    ) -> bool:
        """Atomic CAS: update status only if current status matches from_status.

        Returns True if transition succeeded, False if current status didn't match.
        """
        from_val = from_status.value if isinstance(from_status, ExecutionStatus) else from_status
        to_val = to_status.value if isinstance(to_status, ExecutionStatus) else to_status

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE workflow_executions
                   SET status = $2, updated_at = $4
                   WHERE id = $1 AND status = $3
                   RETURNING id""",
                execution_id, to_val, from_val, datetime.now(timezone.utc),
            )
            return row is not None

    async def get_running_executions(self) -> list[WorkflowExecution]:
        """Get all running/paused executions across all projects (for recovery)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM workflow_executions WHERE status IN ('running', 'paused') ORDER BY created_at",
            )
            executions = []
            for row in rows:
                step_rows = await conn.fetch(
                    "SELECT * FROM workflow_step_results WHERE execution_id = $1",
                    row["id"],
                )
                executions.append(_row_to_execution(row, step_rows))
            return executions

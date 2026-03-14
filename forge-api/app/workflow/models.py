"""Workflow data models — definitions (code-only) and execution state (DB-backed).

Decision references:
  D-001: Custom state machine (not external orchestrator)
  D-004: Per-step LLM sessions
  D-007: Phase 1 linear only (3 step types)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Step types — Phase 1 only (D-007: no conditional/parallel_group yet)
# ---------------------------------------------------------------------------

class StepType(str, Enum):
    llm_agent = "llm_agent"
    forge_command = "forge_command"
    user_decision = "user_decision"


# ---------------------------------------------------------------------------
# Workflow Definition (code-only, not stored in DB)
# ---------------------------------------------------------------------------

class StepDefinition(BaseModel):
    """A single step in a workflow definition."""

    id: str
    name: str
    type: StepType
    description: str = ""

    # llm_agent fields
    prompt_template: str | None = None
    scopes: list[str] = Field(default_factory=list)
    max_iterations: int = 25

    # forge_command fields
    command_template: str | None = None

    # user_decision fields
    decision_prompt: str | None = None
    blocking: bool = True

    # Sequencing — linear chain (Phase 1)
    next_step: str | None = None


class WorkflowDefinition(BaseModel):
    """A reusable workflow template — defines the step sequence."""

    id: str
    name: str
    description: str = ""
    steps: list[StepDefinition]
    initial_step: str
    version: str = "1.0"

    @model_validator(mode="after")
    def validate_step_references(self) -> "WorkflowDefinition":
        step_ids = {s.id for s in self.steps}

        # initial_step must exist
        if self.initial_step not in step_ids:
            raise ValueError(
                f"initial_step '{self.initial_step}' not found in steps: {step_ids}"
            )

        # all next_step references must exist
        for step in self.steps:
            if step.next_step is not None and step.next_step not in step_ids:
                raise ValueError(
                    f"Step '{step.id}' references next_step '{step.next_step}' "
                    f"which does not exist in steps: {step_ids}"
                )

        # no orphan steps (every step must be reachable from initial_step)
        reachable: set[str] = set()
        current: str | None = self.initial_step
        while current is not None and current not in reachable:
            reachable.add(current)
            step = next((s for s in self.steps if s.id == current), None)
            current = step.next_step if step else None

        orphans = step_ids - reachable
        if orphans:
            raise ValueError(
                f"Orphan steps not reachable from initial_step: {orphans}"
            )

        return self


# ---------------------------------------------------------------------------
# Execution state (maps to DB tables from 006_workflows.sql)
# ---------------------------------------------------------------------------

class ExecutionStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class StepResult(BaseModel):
    """Execution result of a single workflow step — maps to workflow_step_results table."""

    step_id: str
    status: StepStatus = StepStatus.pending
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: dict[str, Any] | None = None
    session_id: str | None = None
    error: str | None = None
    decision_ids: list[str] = Field(default_factory=list)
    retries: int = 0


class WorkflowExecution(BaseModel):
    """Runtime state of a workflow instance — maps to workflow_executions table."""

    id: int | None = None  # DB auto-increment
    ext_id: str = ""  # WE-001, WE-002, ...
    workflow_def_id: str = ""
    project_slug: str = ""
    project_id: int | None = None
    objective_id: str | None = None
    status: ExecutionStatus = ExecutionStatus.pending
    current_step: str | None = None
    step_results: dict[str, StepResult] = Field(default_factory=dict)
    pause_reason: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}

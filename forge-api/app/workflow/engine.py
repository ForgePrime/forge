"""WorkflowEngine — main orchestrator for workflow execution.

D-001: Custom state machine.
D-005: asyncio.Task per execution with Semaphore(5).
D-006: Per-step timeout + 2hr workflow-level timeout.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.workflow.events import EventBus, WorkflowEventType, emit_workflow_event
from app.workflow.models import (
    ExecutionStatus,
    StepDefinition,
    StepStatus,
    StepType,
    WorkflowDefinition,
    WorkflowExecution,
)
from app.workflow.steps import StepContext, StepExecutor
from app.workflow.store import WorkflowStore

logger = logging.getLogger(__name__)

# Workflow-level timeout (D-006: 2 hours)
DEFAULT_WORKFLOW_TIMEOUT = 7200

# Max concurrent workflows (D-005)
DEFAULT_MAX_CONCURRENT = 5


class WorkflowEngine:
    """Orchestrates workflow execution — start, pause, resume, cancel.

    Each workflow runs as an asyncio.Task. A Semaphore limits concurrency.
    """

    def __init__(
        self,
        store: WorkflowStore,
        event_bus: EventBus,
        step_executors: dict[StepType, StepExecutor],
        definitions: dict[str, WorkflowDefinition] | None = None,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        workflow_timeout: int = DEFAULT_WORKFLOW_TIMEOUT,
    ):
        self._store = store
        self._event_bus = event_bus
        self._executors = step_executors
        self._definitions = definitions or {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._workflow_timeout = workflow_timeout
        self._active_tasks: dict[int, asyncio.Task] = {}

    def register_definition(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._definitions[definition.id] = definition

    def get_definition(self, def_id: str) -> WorkflowDefinition | None:
        """Get a registered workflow definition."""
        return self._definitions.get(def_id)

    async def start(
        self,
        definition: WorkflowDefinition,
        project_slug: str,
        project_id: int,
        objective_id: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Start a new workflow execution.

        Creates the execution in the store, launches an asyncio.Task,
        and emits workflow.started event.
        """
        # Register definition if not already known
        if definition.id not in self._definitions:
            self._definitions[definition.id] = definition

        # Create in store
        execution = await self._store.create_execution(
            project_id=project_id,
            workflow_def_id=definition.id,
            objective_id=objective_id,
            variables=variables,
        )

        # Emit started event
        await emit_workflow_event(
            self._event_bus, project_slug, WorkflowEventType.STARTED,
            workflow_def_id=definition.id,
            execution_id=execution.ext_id,
            status="running",
        )

        # Launch background task
        task = asyncio.create_task(
            self._run_with_timeout(execution.id, definition, project_slug, project_id),
            name=f"workflow-{execution.ext_id}",
        )
        self._active_tasks[execution.id] = task

        # Don't await — return immediately
        return execution

    async def resume(
        self,
        execution_id: int,
        user_response: Any,
        project_slug: str,
        project_id: int,
    ) -> WorkflowExecution | None:
        """Resume a paused workflow with user input."""
        execution = await self._store.get_execution(execution_id)
        if not execution:
            return None

        if execution.status != ExecutionStatus.paused:
            raise ValueError(
                f"Cannot resume execution {execution.ext_id}: "
                f"status is {execution.status.value}, expected paused"
            )

        definition = self._definitions.get(execution.workflow_def_id)
        if not definition:
            raise ValueError(f"Unknown workflow definition: {execution.workflow_def_id}")

        # Store user response in variables
        current_step = execution.current_step
        if current_step:
            response_key = f"step_{current_step}_response"
            new_vars = {**execution.variables, response_key: user_response}
        else:
            new_vars = {**execution.variables, "user_response": user_response}

        await self._store.update_execution(
            execution_id, variables=new_vars, pause_reason=None,
        )

        # Transition back to running
        ok = await self._store.transition_status(
            execution_id, ExecutionStatus.paused, ExecutionStatus.running,
        )
        if not ok:
            return await self._store.get_execution(execution_id)

        # Emit resumed event
        await emit_workflow_event(
            self._event_bus, project_slug, WorkflowEventType.RESUMED,
            workflow_def_id=execution.workflow_def_id,
            execution_id=execution.ext_id,
            step_id=current_step,
            status="running",
        )

        # Re-launch execution from current step
        task = asyncio.create_task(
            self._run_with_timeout(execution_id, definition, project_slug, project_id),
            name=f"workflow-{execution.ext_id}-resume",
        )
        self._active_tasks[execution_id] = task

        return await self._store.get_execution(execution_id)

    async def cancel(
        self, execution_id: int, project_slug: str,
    ) -> WorkflowExecution | None:
        """Cancel a running or paused workflow."""
        execution = await self._store.get_execution(execution_id)
        if not execution:
            return None

        if execution.status not in (ExecutionStatus.running, ExecutionStatus.paused, ExecutionStatus.pending):
            raise ValueError(
                f"Cannot cancel execution {execution.ext_id}: status is {execution.status.value}"
            )

        # Cancel asyncio task if running
        task = self._active_tasks.pop(execution_id, None)
        if task and not task.done():
            task.cancel()

        # Update status
        await self._store.update_execution(
            execution_id,
            status=ExecutionStatus.cancelled,
            completed_at=datetime.now(timezone.utc),
        )

        # Emit event
        await emit_workflow_event(
            self._event_bus, project_slug, WorkflowEventType.CANCELLED,
            workflow_def_id=execution.workflow_def_id,
            execution_id=execution.ext_id,
            status="cancelled",
        )

        return await self._store.get_execution(execution_id)

    async def recover(self) -> int:
        """Recover from restart: mark stale running executions as failed.

        Called during app startup. Returns number of recovered executions.
        """
        stale = await self._store.get_running_executions()
        count = 0
        for execution in stale:
            ok = await self._store.transition_status(
                execution.id, execution.status, ExecutionStatus.failed,
            )
            if ok:
                await self._store.update_execution(
                    execution.id,
                    error="Server restart — execution interrupted. Can be retried.",
                    completed_at=datetime.now(timezone.utc),
                )
                count += 1
                logger.warning(
                    "Recovered stale workflow %s (was %s)",
                    execution.ext_id, execution.status.value,
                )
        return count

    async def _run_with_timeout(
        self,
        execution_id: int,
        definition: WorkflowDefinition,
        project_slug: str,
        project_id: int,
    ) -> None:
        """Run workflow with semaphore and timeout."""
        async with self._semaphore:
            try:
                await asyncio.wait_for(
                    self._run_workflow(execution_id, definition, project_slug, project_id),
                    timeout=self._workflow_timeout,
                )
            except asyncio.TimeoutError:
                logger.error("Workflow %d timed out after %ds", execution_id, self._workflow_timeout)
                await self._store.update_execution(
                    execution_id,
                    status=ExecutionStatus.failed,
                    error=f"Workflow timed out after {self._workflow_timeout}s",
                    completed_at=datetime.now(timezone.utc),
                )
                execution = await self._store.get_execution(execution_id)
                if execution:
                    await emit_workflow_event(
                        self._event_bus, project_slug, WorkflowEventType.FAILED,
                        workflow_def_id=definition.id,
                        execution_id=execution.ext_id,
                        status="failed",
                        error=f"Workflow timed out after {self._workflow_timeout}s",
                    )
            except asyncio.CancelledError:
                logger.info("Workflow %d cancelled", execution_id)
            except Exception as e:
                logger.exception("Workflow %d failed unexpectedly", execution_id)
                await self._store.update_execution(
                    execution_id,
                    status=ExecutionStatus.failed,
                    error=f"{type(e).__name__}: {e}",
                    completed_at=datetime.now(timezone.utc),
                )
            finally:
                self._active_tasks.pop(execution_id, None)

    async def _run_workflow(
        self,
        execution_id: int,
        definition: WorkflowDefinition,
        project_slug: str,
        project_id: int,
    ) -> None:
        """Main workflow execution loop."""
        # Load current state
        execution = await self._store.get_execution(execution_id)
        if not execution:
            logger.error("Execution %d not found", execution_id)
            return

        # Transition to running
        if execution.status == ExecutionStatus.pending:
            ok = await self._store.transition_status(
                execution_id, ExecutionStatus.pending, ExecutionStatus.running,
            )
            if not ok:
                logger.warning("Could not transition %d to running", execution_id)
                return

        # Build step lookup
        steps_by_id: dict[str, StepDefinition] = {s.id: s for s in definition.steps}

        # Determine starting step
        current_step_id = execution.current_step or definition.initial_step

        # Collect previous step outputs for context
        previous_outputs: dict[str, dict] = {}
        for sid, sr in execution.step_results.items():
            if sr.output:
                previous_outputs[sid] = sr.output

        # Main loop: process steps sequentially
        while current_step_id:
            step_def = steps_by_id.get(current_step_id)
            if not step_def:
                await self._fail_execution(
                    execution_id, project_slug, definition.id, execution.ext_id,
                    f"Step '{current_step_id}' not found in definition",
                )
                return

            # Update current step in store
            await self._store.update_execution(execution_id, current_step=current_step_id)

            # Emit step_started
            await emit_workflow_event(
                self._event_bus, project_slug, WorkflowEventType.STEP_STARTED,
                workflow_def_id=definition.id,
                execution_id=execution.ext_id,
                step_id=current_step_id,
                status="running",
            )

            # Record step as running
            await self._store.update_step_result(
                execution_id, current_step_id,
                status=StepStatus.running,
                started_at=datetime.now(timezone.utc),
            )

            # Build step context
            ctx = StepContext(
                project_slug=project_slug,
                project_id=project_id,
                execution_id=execution.ext_id,
                workflow_def_id=definition.id,
                objective_id=execution.objective_id,
                variables=execution.variables,
                previous_step_outputs=previous_outputs,
            )

            # Get executor for step type
            executor = self._executors.get(step_def.type)
            if not executor:
                await self._fail_execution(
                    execution_id, project_slug, definition.id, execution.ext_id,
                    f"No executor for step type '{step_def.type.value}'",
                )
                return

            # Execute step
            step_result = await executor.execute(step_def, ctx)

            # Process result
            if step_result.status == StepStatus.completed:
                # Record completion
                await self._store.update_step_result(
                    execution_id, current_step_id,
                    status=StepStatus.completed,
                    output=step_result.output,
                    session_id=step_result.session_id,
                    decision_ids=step_result.decision_ids,
                    completed_at=step_result.completed_at or datetime.now(timezone.utc),
                )

                # Emit step_completed
                await emit_workflow_event(
                    self._event_bus, project_slug, WorkflowEventType.STEP_COMPLETED,
                    workflow_def_id=definition.id,
                    execution_id=execution.ext_id,
                    step_id=current_step_id,
                    status="completed",
                    output_summary=str(step_result.output)[:200] if step_result.output else None,
                )

                # Update previous outputs
                if step_result.output:
                    previous_outputs[current_step_id] = step_result.output

                # Move to next step
                current_step_id = step_def.next_step

            elif step_result.status in (StepStatus.pending, StepStatus.failed) and step_result.error:
                if "awaiting_user_decision" in (step_result.error or ""):
                    # Paused for user decision
                    await self._store.update_step_result(
                        execution_id, current_step_id,
                        status=StepStatus.pending,
                        session_id=step_result.session_id,
                    )
                    pause_reason = "awaiting_user_decision"
                    await self._store.update_execution(
                        execution_id,
                        status=ExecutionStatus.paused,
                        pause_reason=pause_reason,
                    )
                    await emit_workflow_event(
                        self._event_bus, project_slug, WorkflowEventType.PAUSED,
                        workflow_def_id=definition.id,
                        execution_id=execution.ext_id,
                        step_id=current_step_id,
                        status="paused",
                        pause_reason=pause_reason,
                    )
                    return  # Engine paused — will resume via resume()

                elif "blocked_by_decision:" in (step_result.error or ""):
                    # Paused for LLM blocking decision
                    decision_id = step_result.error.split(":", 1)[1] if ":" in step_result.error else ""
                    await self._store.update_step_result(
                        execution_id, current_step_id,
                        status=StepStatus.pending,
                        session_id=step_result.session_id,
                        output=step_result.output,
                    )
                    pause_reason = f"blocked_by_decision:{decision_id}"
                    await self._store.update_execution(
                        execution_id,
                        status=ExecutionStatus.paused,
                        pause_reason=pause_reason,
                    )
                    await emit_workflow_event(
                        self._event_bus, project_slug, WorkflowEventType.PAUSED,
                        workflow_def_id=definition.id,
                        execution_id=execution.ext_id,
                        step_id=current_step_id,
                        status="paused",
                        pause_reason=pause_reason,
                    )
                    return  # Engine paused — will resume via resume()

                else:
                    # Step genuinely failed
                    await self._store.update_step_result(
                        execution_id, current_step_id,
                        status=StepStatus.failed,
                        error=step_result.error,
                        completed_at=datetime.now(timezone.utc),
                    )
                    await self._fail_execution(
                        execution_id, project_slug, definition.id, execution.ext_id,
                        f"Step '{current_step_id}' failed: {step_result.error}",
                    )
                    return

            elif step_result.status == StepStatus.failed:
                await self._store.update_step_result(
                    execution_id, current_step_id,
                    status=StepStatus.failed,
                    error=step_result.error,
                    completed_at=datetime.now(timezone.utc),
                )
                await self._fail_execution(
                    execution_id, project_slug, definition.id, execution.ext_id,
                    f"Step '{current_step_id}' failed: {step_result.error}",
                )
                return

            # Reload execution state (variables may have changed)
            execution = await self._store.get_execution(execution_id)
            if not execution or execution.status != ExecutionStatus.running:
                return  # Was cancelled or something external happened

        # All steps completed — mark workflow completed
        await self._store.update_execution(
            execution_id,
            status=ExecutionStatus.completed,
            completed_at=datetime.now(timezone.utc),
        )
        await emit_workflow_event(
            self._event_bus, project_slug, WorkflowEventType.COMPLETED,
            workflow_def_id=definition.id,
            execution_id=execution.ext_id,
            status="completed",
        )

    async def _fail_execution(
        self, execution_id: int, project_slug: str,
        def_id: str, ext_id: str, error: str,
    ) -> None:
        """Mark execution as failed and emit event."""
        await self._store.update_execution(
            execution_id,
            status=ExecutionStatus.failed,
            error=error,
            completed_at=datetime.now(timezone.utc),
        )
        await emit_workflow_event(
            self._event_bus, project_slug, WorkflowEventType.FAILED,
            workflow_def_id=def_id,
            execution_id=ext_id,
            status="failed",
            error=error,
        )

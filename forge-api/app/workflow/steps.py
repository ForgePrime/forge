"""Step executors — per-type execution of workflow steps.

D-003: Direct Python import for forge-core (not subprocess).
D-004: Per-step LLM sessions.
D-006: Per-step timeout (600s default).
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.llm.agent_loop import AgentLoop, AgentResult, StreamEvent
from app.llm.session_manager import ChatSession, SessionManager
from app.workflow.events import EventBus, WorkflowEventType, emit_workflow_event
from app.workflow.models import StepDefinition, StepResult, StepStatus

logger = logging.getLogger(__name__)

# Default per-step timeout (D-006: 600s to prevent stuck workflows)
DEFAULT_STEP_TIMEOUT = 600


class StepContext:
    """Execution context passed to each step executor."""

    def __init__(
        self,
        project_slug: str,
        project_id: int,
        execution_id: str,
        workflow_def_id: str,
        objective_id: str | None = None,
        variables: dict[str, Any] | None = None,
        previous_step_outputs: dict[str, dict] | None = None,
    ):
        self.project_slug = project_slug
        self.project_id = project_id
        self.execution_id = execution_id
        self.workflow_def_id = workflow_def_id
        self.objective_id = objective_id
        self.variables = variables or {}
        self.previous_step_outputs = previous_step_outputs or {}


class StepExecutor(ABC):
    """Abstract base for step executors."""

    @abstractmethod
    async def execute(
        self,
        step_def: StepDefinition,
        context: StepContext,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None = None,
    ) -> StepResult:
        """Execute a workflow step and return the result."""
        ...


class LLMAgentStepExecutor(StepExecutor):
    """Executes llm_agent steps by wrapping AgentLoop.

    D-004: Creates a new ChatSession per step with step-specific scopes.
    Injects previous step summaries + objective info into system prompt.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        agent_loop_factory: Callable[..., AgentLoop],
        timeout: int = DEFAULT_STEP_TIMEOUT,
    ):
        self._session_manager = session_manager
        self._agent_loop_factory = agent_loop_factory
        self._timeout = timeout

    async def execute(
        self,
        step_def: StepDefinition,
        context: StepContext,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None = None,
    ) -> StepResult:
        now = datetime.now(timezone.utc)
        result = StepResult(step_id=step_def.id, status=StepStatus.running, started_at=now)

        try:
            # Create per-step session (D-004)
            session = await self._session_manager.create(
                context_type="workflow",
                context_id=context.execution_id,
                project=context.project_slug,
                session_type="execute",
                target_entity_type="workflow_step",
                target_entity_id=step_def.id,
                scopes=step_def.scopes or [],
            )

            # Build system prompt from template + context
            system_prompt = self._build_prompt(step_def, context)

            # Build messages
            from core.llm.provider import CompletionConfig, Message
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=step_def.prompt_template or step_def.description),
            ]
            config = CompletionConfig()

            # Create AgentLoop with step-specific settings
            agent_loop = self._agent_loop_factory(
                max_iterations=step_def.max_iterations,
                session_scopes=step_def.scopes or None,
            )

            # Run with timeout (D-006)
            agent_result: AgentResult = await asyncio.wait_for(
                agent_loop.run(messages, config, context={"project": context.project_slug}, on_event=on_event),
                timeout=self._timeout,
            )

            # Check for blocking decision
            if agent_result.stop_reason == "blocked_by_decision":
                result.status = StepStatus.pending  # Will be set to paused by engine
                result.output = {"content": agent_result.content, "blocked_by": agent_result.blocked_by_decision_id}
                result.session_id = session.session_id
                result.error = f"blocked_by_decision:{agent_result.blocked_by_decision_id}"
                return result

            # Successful completion
            result.status = StepStatus.completed
            result.completed_at = datetime.now(timezone.utc)
            result.output = {
                "content": agent_result.content,
                "iterations": agent_result.iterations,
                "model": agent_result.model,
                "tool_calls_count": len(agent_result.tool_calls_made),
            }
            result.session_id = session.session_id
            return result

        except asyncio.TimeoutError:
            result.status = StepStatus.failed
            result.completed_at = datetime.now(timezone.utc)
            result.error = f"Step timed out after {self._timeout}s"
            return result
        except Exception as e:
            logger.exception("LLM agent step failed: %s", step_def.id)
            result.status = StepStatus.failed
            result.completed_at = datetime.now(timezone.utc)
            result.error = f"{type(e).__name__}: {e}"
            return result

    def _build_prompt(self, step_def: StepDefinition, context: StepContext) -> str:
        """Build system prompt with workflow context."""
        parts = [
            f"You are executing step '{step_def.name}' of workflow '{context.workflow_def_id}'.",
            f"Project: {context.project_slug}",
        ]
        if context.objective_id:
            parts.append(f"Objective: {context.objective_id}")

        # Inject previous step outputs
        if context.previous_step_outputs:
            parts.append("\n## Previous Step Outputs")
            for sid, output in context.previous_step_outputs.items():
                content = output.get("content", str(output))
                # Truncate long outputs
                if len(content) > 2000:
                    content = content[:2000] + "... [truncated]"
                parts.append(f"### {sid}\n{content}")

        # Inject variables
        if context.variables:
            parts.append("\n## Workflow Variables")
            for k, v in context.variables.items():
                parts.append(f"- {k}: {v}")

        return "\n".join(parts)


class ForgeCommandStepExecutor(StepExecutor):
    """Executes forge_command steps via direct Python import (D-003).

    Imports and calls forge-core modules directly (not subprocess).
    Templates command with workflow variables.
    """

    def __init__(self, timeout: int = DEFAULT_STEP_TIMEOUT):
        self._timeout = timeout

    async def execute(
        self,
        step_def: StepDefinition,
        context: StepContext,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None = None,
    ) -> StepResult:
        now = datetime.now(timezone.utc)
        result = StepResult(step_id=step_def.id, status=StepStatus.running, started_at=now)

        if not step_def.command_template:
            result.status = StepStatus.failed
            result.completed_at = datetime.now(timezone.utc)
            result.error = "No command_template specified"
            return result

        try:
            # Template the command with variables
            command = step_def.command_template.format(
                project=context.project_slug,
                objective_id=context.objective_id or "",
                **context.variables,
            )

            # Parse module and function from command
            # Format: "module.path:function_name" or "module.path:function_name(args)"
            output = await asyncio.wait_for(
                self._run_command(command, context),
                timeout=self._timeout,
            )

            result.status = StepStatus.completed
            result.completed_at = datetime.now(timezone.utc)
            result.output = output
            return result

        except asyncio.TimeoutError:
            result.status = StepStatus.failed
            result.completed_at = datetime.now(timezone.utc)
            result.error = f"Command timed out after {self._timeout}s"
            return result
        except Exception as e:
            logger.exception("Forge command step failed: %s", step_def.id)
            result.status = StepStatus.failed
            result.completed_at = datetime.now(timezone.utc)
            result.error = f"{type(e).__name__}: {e}"
            return result

    async def _run_command(self, command: str, context: StepContext) -> dict[str, Any]:
        """Execute a forge-core command via direct import.

        Command format: "core.module:function" or "core.module:function arg1 arg2"
        """
        parts = command.split()
        module_func = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        if ":" in module_func:
            module_path, func_name = module_func.rsplit(":", 1)
        else:
            # Default: treat as module with main() function
            module_path = module_func
            func_name = "main"

        try:
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            return {"success": False, "error": f"Import failed: {e}", "command": command}

        # Run in executor to avoid blocking event loop if function is sync
        loop = asyncio.get_event_loop()
        try:
            if asyncio.iscoroutinefunction(func):
                raw_result = await func(context.project_slug, *args)
            else:
                raw_result = await loop.run_in_executor(None, func, context.project_slug, *args)
        except SystemExit as e:
            # forge-core modules may call sys.exit
            return {"success": e.code == 0, "exit_code": e.code, "command": command}
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}", "command": command}

        # Normalize result
        if isinstance(raw_result, dict):
            return {"success": True, **raw_result}
        elif isinstance(raw_result, str):
            return {"success": True, "output": raw_result}
        else:
            return {"success": True, "output": str(raw_result) if raw_result else ""}


class UserDecisionStepExecutor(StepExecutor):
    """Executes user_decision steps — pauses workflow for user input.

    Emits workflow.paused event and returns paused status.
    On resume, the engine re-invokes with user response in variables.
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    async def execute(
        self,
        step_def: StepDefinition,
        context: StepContext,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None = None,
    ) -> StepResult:
        now = datetime.now(timezone.utc)

        # Check if we're resuming (user response available in variables)
        response_key = f"step_{step_def.id}_response"
        user_response = context.variables.get(response_key)

        if user_response is not None:
            # Resuming with user response
            return StepResult(
                step_id=step_def.id,
                status=StepStatus.completed,
                started_at=now,
                completed_at=datetime.now(timezone.utc),
                output={
                    "user_response": user_response,
                    "decision_prompt": step_def.decision_prompt or step_def.description,
                },
            )

        # First invocation — pause and wait for user
        await emit_workflow_event(
            self._event_bus,
            context.project_slug,
            WorkflowEventType.PAUSED,
            workflow_def_id=context.workflow_def_id,
            execution_id=context.execution_id,
            step_id=step_def.id,
            status="paused",
            pause_reason="awaiting_user_decision",
            output_summary=step_def.decision_prompt or step_def.description,
        )

        if on_event:
            await on_event(StreamEvent("paused", {
                "reason": "awaiting_user_decision",
                "step_id": step_def.id,
                "prompt": step_def.decision_prompt or step_def.description,
            }))

        return StepResult(
            step_id=step_def.id,
            status=StepStatus.pending,  # Engine will set execution to paused
            started_at=now,
            error="awaiting_user_decision",
        )

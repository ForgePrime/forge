"""LLM Agent Loop — multi-turn conversation engine with tool execution.

Manages the LLM conversation loop:
1. Send messages to LLM provider with available tools
2. If LLM calls tools → execute via ToolRegistry → feed results back
3. Repeat until LLM gives a text reply or safety limits are hit

Emits StreamEvent callbacks for real-time WebSocket streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, replace
from typing import Any, Awaitable, Callable

from core.llm.provider import (
    CompletionConfig,
    LLMProvider,
    Message,
    ProviderError,
)

logger = logging.getLogger(__name__)

# Safety limits
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_MAX_TOTAL_TOKENS = 50_000
DEFAULT_TIMEOUT_SECONDS = 120


@dataclass
class StreamEvent:
    """Event emitted during agent loop execution.

    Types:
        token     — text content from LLM (final response)
        thinking  — intermediate text before tool calls
        tool_call — LLM invoked a tool (name, input)
        tool_result — tool execution result
        complete  — loop finished successfully
        error     — loop stopped due to error or limit
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Final result of an agent loop run."""

    content: str
    messages: list[Message]
    tool_calls_made: list[dict]
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    iterations: int = 0
    model: str = ""
    stop_reason: str = ""  # "complete" | "max_iterations" | "max_tokens" | "timeout" | "error" | "cancelled"


class AgentLoop:
    """Multi-turn conversation engine with tool execution.

    Usage::

        loop = AgentLoop(provider, tool_registry, storage)
        result = await loop.run(messages, config, context)
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: Any,
        storage: Any,
        permissions: dict[str, dict[str, bool]] | None = None,
        disabled_tools: list[str] | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        max_total_tokens: int = DEFAULT_MAX_TOTAL_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        self._tool_registry = tool_registry
        self._storage = storage
        self._permissions = permissions
        self._disabled_tools = disabled_tools
        self._max_iterations = max_iterations
        self._max_total_tokens = max_total_tokens
        self._timeout = timeout_seconds

    async def run(
        self,
        messages: list[Message],
        config: CompletionConfig,
        context: dict[str, Any] | None = None,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None = None,
    ) -> AgentResult:
        """Run the agent loop until final response or safety limit.

        Args:
            messages: Initial conversation (system + history + user message).
            config: LLM completion config (model, temperature, etc.).
            context: Tool execution context (project, entity info).
            on_event: Async callback for real-time streaming events.

        Returns:
            AgentResult with final response and conversation history.
        """
        context = context or {}
        all_tool_calls: list[dict] = []
        total_input = 0
        total_output = 0
        iteration = 0
        model = ""
        start_time = time.monotonic()

        # Resolve available tools for this context
        context_type = context.get("context_type", "global")
        # Support list of context types (scopes → context_types mapping)
        context_types = context.get("context_types", context_type)
        tool_defs = self._tool_registry.get_llm_definitions(
            context_type=context_types,
            permissions=self._permissions,
            disabled_tools=self._disabled_tools,
        )
        if tool_defs:
            config = replace(config, tools=tool_defs)

        # Working copy of messages
        conversation = list(messages)

        try:
            while iteration < self._max_iterations:
                # --- Safety checks ---
                elapsed = time.monotonic() - start_time
                if elapsed > self._timeout:
                    return await self._stop(
                        "timeout", conversation, all_tool_calls,
                        total_input, total_output, iteration, model,
                        on_event, f"Timeout after {elapsed:.0f}s",
                    )

                if total_input + total_output > self._max_total_tokens:
                    return await self._stop(
                        "max_tokens", conversation, all_tool_calls,
                        total_input, total_output, iteration, model,
                        on_event, "Token limit exceeded",
                    )

                # --- LLM call ---
                iteration += 1
                try:
                    result = await self._provider.complete(
                        messages=conversation,
                        config=config,
                    )
                except ProviderError as e:
                    logger.error("Provider error on iteration %d: %s", iteration, e)
                    return await self._stop(
                        "error", conversation, all_tool_calls,
                        total_input, total_output, iteration, model,
                        on_event, f"Provider error: {e}",
                    )

                # Update counters
                total_input += result.usage.input_tokens
                total_output += result.usage.output_tokens
                model = result.model

                # --- Final response (no tool use) ---
                if result.stop_reason != "tool_use" or not result.tool_calls:
                    conversation.append(Message(
                        role="assistant",
                        content=result.content,
                    ))

                    if on_event:
                        await on_event(StreamEvent("token", {"content": result.content}))
                        await on_event(StreamEvent("complete", {
                            "content": result.content,
                            "iterations": iteration,
                            "total_input_tokens": total_input,
                            "total_output_tokens": total_output,
                        }))

                    return AgentResult(
                        content=result.content,
                        messages=conversation,
                        tool_calls_made=all_tool_calls,
                        total_input_tokens=total_input,
                        total_output_tokens=total_output,
                        iterations=iteration,
                        model=model,
                        stop_reason="complete",
                    )

                # --- Tool use: process tool calls ---

                # Add assistant message with tool calls to conversation
                conversation.append(Message(
                    role="assistant",
                    content=result.content,
                    tool_calls=result.tool_calls,
                ))

                # Emit thinking text if LLM produced text before tool calls
                if result.content and on_event:
                    await on_event(StreamEvent("thinking", {"content": result.content}))

                # Execute each tool call
                for tool_call in result.tool_calls:
                    # Validate tool_call structure
                    tool_name = tool_call.get("name", "")
                    tool_input = tool_call.get("input", {})
                    tool_id = tool_call.get("id", "")
                    if not tool_name or not tool_id:
                        logger.warning("Skipping malformed tool call: %s", tool_call)
                        continue

                    if on_event:
                        await on_event(StreamEvent("tool_call", {
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input,
                        }))

                    # Execute tool (with defense-in-depth permission check)
                    try:
                        tool_result = await self._tool_registry.execute(
                            tool_name=tool_name,
                            args=tool_input,
                            storage=self._storage,
                            context=context,
                            permissions=self._permissions,
                        )
                    except Exception as e:
                        logger.warning("Tool %s execution error: %s", tool_name, e)
                        tool_result = {"error": f"{type(e).__name__}: {e}"}

                    try:
                        result_str = json.dumps(tool_result, ensure_ascii=False, default=str)
                    except (TypeError, ValueError):
                        result_str = str(tool_result)

                    if on_event:
                        await on_event(StreamEvent("tool_result", {
                            "id": tool_id,
                            "name": tool_name,
                            "result": tool_result,
                        }))

                    all_tool_calls.append({
                        "id": tool_id,
                        "name": tool_name,
                        "input": tool_input,
                        "result": tool_result,
                    })

                    # Add tool result to conversation
                    # (consecutive tool results are merged by _convert_messages)
                    conversation.append(Message(
                        role="tool",
                        content=result_str,
                        tool_call_id=tool_id,
                        name=tool_name,
                    ))

            # Max iterations exhausted
            return await self._stop(
                "max_iterations", conversation, all_tool_calls,
                total_input, total_output, iteration, model,
                on_event, "Maximum iterations reached",
            )

        except asyncio.CancelledError:
            return AgentResult(
                content="[Agent cancelled]",
                messages=conversation,
                tool_calls_made=all_tool_calls,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                iterations=iteration,
                model=model,
                stop_reason="cancelled",
            )
        except Exception as e:
            logger.exception("Unexpected agent loop error")
            try:
                return await self._stop(
                    "error", conversation, all_tool_calls,
                    total_input, total_output, iteration, model,
                    on_event, f"Internal error: {type(e).__name__}: {e}",
                )
            except Exception:
                return AgentResult(
                    content=f"[Internal error: {type(e).__name__}]",
                    messages=conversation,
                    tool_calls_made=all_tool_calls,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    iterations=iteration,
                    model=model,
                    stop_reason="error",
                )

    @staticmethod
    async def _stop(
        reason: str,
        conversation: list[Message],
        tool_calls: list[dict],
        total_input: int,
        total_output: int,
        iteration: int,
        model: str,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None,
        message: str,
    ) -> AgentResult:
        """Build a stop result and emit error event."""
        if on_event:
            try:
                await on_event(StreamEvent("error", {"reason": reason, "message": message}))
            except Exception:
                pass  # Don't fail on event emission errors
        return AgentResult(
            content=f"[Agent stopped: {message}]",
            messages=conversation,
            tool_calls_made=tool_calls,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            iterations=iteration,
            model=model,
            stop_reason=reason,
        )

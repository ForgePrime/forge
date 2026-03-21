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

from _future.llm.provider import (
    CompletionConfig,
    CompletionResult,
    LLMProvider,
    Message,
    ProviderError,
    TokenUsage,
)
from app.llm.context_window_manager import trim_history, DEFAULT_TOKEN_BUDGET

logger = logging.getLogger(__name__)

# Blocking decision criteria: risk decisions with critical/high severity
_BLOCKING_SEVERITIES = {"critical", "high"}


def _extract_blocking_decision(tool_name: str, tool_result: dict) -> str:
    """Return decision ID if this tool result created a blocking decision, else ''."""
    if tool_name != "createDecision":
        return ""
    if not tool_result.get("created"):
        return ""
    decision = tool_result.get("decision", {})
    if not isinstance(decision, dict):
        return ""
    # A risk decision with critical/high severity blocks the session
    if decision.get("type") == "risk" and decision.get("severity", "").lower() in _BLOCKING_SEVERITIES:
        return decision.get("id", "")
    return ""


# Tools that bypass scope enforcement (always available)
GLOBAL_TOOLS = frozenset({
    "searchEntities", "getEntity", "listEntities",
    "getProject", "getProjectStatus",
    "listAvailableTools", "getToolContract",
})

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
    stop_reason: str = ""  # "complete" | "max_iterations" | "max_tokens" | "timeout" | "error" | "cancelled" | "blocked_by_decision"
    blocked_by_decision_id: str = ""  # Decision ID if stop_reason == "blocked_by_decision"


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
        session_scopes: list[str] | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        max_total_tokens: int = DEFAULT_MAX_TOTAL_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        self._tool_registry = tool_registry
        self._storage = storage
        self._permissions = permissions
        self._disabled_tools = disabled_tools
        self._session_scopes = session_scopes  # Allowed scopes for scope enforcement
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

        # Detect text-tool mode: provider doesn't support native tool_use
        # but tools are available → inject into system prompt instead
        caps = self._provider.capabilities()
        text_tool_mode = not caps.supports_tool_use and bool(tool_defs)

        if text_tool_mode:
            from app.llm.text_tool_adapter import build_text_tool_prompt
            tool_objects = self._tool_registry.get_tools(
                context_type=context_types,
                permissions=self._permissions,
                disabled_tools=self._disabled_tools,
            )
            tool_prompt = build_text_tool_prompt(tool_objects)
            config = replace(config,
                system_prompt=(config.system_prompt or "") + "\n\n" + tool_prompt,
            )
            logger.info(
                "Text-tool mode: injected %d tools into system prompt",
                len(tool_objects),
            )
        elif tool_defs:
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

                # --- Trim conversation to fit token budget ---
                history_budget = context.get("history_token_budget", DEFAULT_TOKEN_BUDGET)
                conversation = trim_history(conversation, budget_tokens=history_budget)

                # --- LLM call ---
                iteration += 1

                # Streaming decision:
                # - Text-tool mode: always use complete() (need full text for parsing)
                # - Native tool_use: complete() when tools active, stream otherwise
                if text_tool_mode:
                    use_streaming = False
                else:
                    use_streaming = caps.supports_streaming and not config.tools

                try:
                    if use_streaming:
                        result = await self._stream_call(
                            conversation, config, caps, on_event,
                        )
                    else:
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
                except Exception as e:
                    logger.error("Unexpected error on iteration %d: %s", iteration, e, exc_info=True)
                    return await self._stop(
                        "error", conversation, all_tool_calls,
                        total_input, total_output, iteration, model,
                        on_event, f"Unexpected error: {type(e).__name__}: {e}",
                    )

                # Update counters
                total_input += result.usage.input_tokens
                total_output += result.usage.output_tokens
                model = result.model

                # --- Text-tool parsing: extract <forge_tool> blocks ---
                if text_tool_mode and result.stop_reason != "tool_use":
                    from app.llm.text_tool_adapter import parse_text_tool_calls
                    clean_text, parsed_calls = parse_text_tool_calls(result.content)
                    if parsed_calls:
                        result = CompletionResult(
                            content=clean_text,
                            model=result.model,
                            usage=result.usage,
                            stop_reason="tool_use",
                            tool_calls=parsed_calls,
                        )

                # --- Final response (no tool use) ---
                if result.stop_reason != "tool_use" or not result.tool_calls:
                    conversation.append(Message(
                        role="assistant",
                        content=result.content,
                    ))

                    if on_event:
                        # For streaming path, tokens were already emitted chunk-by-chunk.
                        # For complete() path, emit the full response as single token event.
                        if not use_streaming:
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
                text_tool_results: list[dict] = []  # For batching in text-tool mode
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

                    # Scope enforcement: reject tools outside session scopes
                    if self._session_scopes is not None and tool_name not in GLOBAL_TOOLS:
                        tool_scope = getattr(
                            self._tool_registry.get_tool(tool_name), "scope", None
                        )
                        if tool_scope and tool_scope not in self._session_scopes:
                            logger.info(
                                "Scope enforcement: blocked %s (scope=%s, allowed=%s)",
                                tool_name, tool_scope, self._session_scopes,
                            )
                            tool_result = {
                                "error": f"Permission denied: the '{tool_scope}' scope is not enabled. "
                                f"Ask the user to enable it in the Scopes tab."
                            }

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

                            if text_tool_mode:
                                text_tool_results.append({
                                    "name": tool_name, "id": tool_id, "result": tool_result,
                                })
                            else:
                                conversation.append(Message(
                                    role="tool",
                                    content=json.dumps(tool_result, ensure_ascii=False, default=str),
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                ))
                            continue  # Skip to next tool call

                    # Handle parse errors from text-tool mode
                    if tool_name == "__parse_error__":
                        tool_result = {
                            "error": f"Failed to parse your tool call: {tool_input.get('error', 'unknown')}. "
                            f"Raw input: {str(tool_input.get('raw', ''))[:200]}. "
                            "Please fix the JSON and try again."
                        }
                    else:
                        # Workflow state check (soft enforcement)
                        workflow_state = context.get("workflow_state")
                        if workflow_state:
                            from app.llm.workflow_state import check_tool_against_workflow, advance_workflow
                            wf_check = check_tool_against_workflow(workflow_state, tool_name)
                            if wf_check.get("warning"):
                                logger.info("Workflow: %s", wf_check["warning"])
                                # Inject warning as system message for LLM awareness
                                conversation.append(Message(
                                    role="system",
                                    content=f"[Workflow note: {wf_check['warning']}]",
                                ))
                            if wf_check.get("step_advanced"):
                                advance_workflow(workflow_state, tool_name, wf_check)

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
                    if text_tool_mode:
                        # Collect for batching — claude-code skips role="tool"
                        text_tool_results.append({
                            "name": tool_name, "id": tool_id, "result": tool_result,
                        })
                    else:
                        # Standard: individual tool role messages
                        # (consecutive tool results are merged by _convert_messages)
                        conversation.append(Message(
                            role="tool",
                            content=result_str,
                            tool_call_id=tool_id,
                            name=tool_name,
                        ))

                    # --- Check for blocking decision ---
                    blocking_id = _extract_blocking_decision(tool_name, tool_result)
                    if blocking_id:
                        # Flush pending text-tool results before pausing
                        if text_tool_mode and text_tool_results:
                            from app.llm.text_tool_adapter import format_tool_results as _fmt
                            conversation.append(Message(
                                role="user", content=_fmt(text_tool_results),
                            ))
                        if on_event:
                            await on_event(StreamEvent("paused", {
                                "reason": "blocked_by_decision",
                                "decision_id": blocking_id,
                            }))
                        return AgentResult(
                            content=f"[Session paused: waiting for decision {blocking_id}]",
                            messages=conversation,
                            tool_calls_made=all_tool_calls,
                            total_input_tokens=total_input,
                            total_output_tokens=total_output,
                            iterations=iteration,
                            model=model,
                            stop_reason="blocked_by_decision",
                            blocked_by_decision_id=blocking_id,
                        )

                # --- Batch text-tool results as user message ---
                if text_tool_mode and text_tool_results:
                    from app.llm.text_tool_adapter import format_tool_results
                    formatted = format_tool_results(text_tool_results)
                    conversation.append(Message(role="user", content=formatted))

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

    async def _stream_call(
        self,
        conversation: list[Message],
        config: CompletionConfig,
        caps: Any,
        on_event: Callable[[StreamEvent], Awaitable[None]] | None,
    ) -> CompletionResult:
        """Call provider.stream() and accumulate into CompletionResult.

        Emits real-time StreamEvent('token') for each content chunk,
        enabling WebSocket streaming to the frontend.
        """
        content = ""
        usage = TokenUsage()

        async for chunk in self._provider.stream(
            messages=conversation,
            config=config,
        ):
            if chunk.content:
                content += chunk.content
                if on_event:
                    await on_event(StreamEvent("token", {"content": chunk.content}))
            if chunk.is_final and chunk.usage:
                usage = chunk.usage
            elif chunk.usage and not chunk.is_final:
                # Some providers send usage in message_delta before message_stop
                usage = chunk.usage

        return CompletionResult(
            content=content,
            model=caps.model_id,
            usage=usage,
            stop_reason="end_turn",
            tool_calls=[],
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

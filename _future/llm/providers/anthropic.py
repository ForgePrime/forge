"""
Anthropic (Claude) LLM provider.

Implements LLMProvider Protocol using the Anthropic Messages API.
Requires: anthropic package (pip install anthropic).
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from core.llm.provider import (
    CompletionConfig,
    CompletionResult,
    Message,
    ProviderCapabilities,
    ProviderError,
    StreamChunk,
    TokenUsage,
    ToolDefinition,
)

# Model capability map — updated as new models release
# Latest: Opus 4.6, Sonnet 4.6, Haiku 4.5 (March 2026)
_MODEL_CAPS: dict[str, dict[str, Any]] = {
    # --- Current generation ---
    "claude-opus-4-6": {
        "max_context_window": 200_000,
        "max_output_tokens": 128_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.005,
        "cost_output": 0.025,
    },
    "claude-sonnet-4-6": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.003,
        "cost_output": 0.015,
    },
    "claude-haiku-4-5-20251001": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.001,
        "cost_output": 0.005,
    },
    # --- Legacy (still available) ---
    "claude-sonnet-4-5-20250929": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.003,
        "cost_output": 0.015,
    },
    "claude-opus-4-5-20251101": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.005,
        "cost_output": 0.025,
    },
    "claude-opus-4-20250514": {
        "max_context_window": 200_000,
        "max_output_tokens": 32_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.015,
        "cost_output": 0.075,
    },
    "claude-sonnet-4-20250514": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
        "cost_input": 0.003,
        "cost_output": 0.015,
    },
}

_DEFAULT_CAPS = {
    "max_context_window": 200_000,
    "max_output_tokens": 64_000,
    "supports_vision": True,
    "supports_thinking": True,
    "cost_input": 0.003,
    "cost_output": 0.015,
}


def _convert_tools(tools: list[ToolDefinition] | None) -> list[dict] | None:
    """Convert generic ToolDefinition list to Anthropic tool format."""
    if not tools:
        return None
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.parameters if t.parameters else {"type": "object", "properties": {}},
        }
        for t in tools
    ]


def _convert_messages(messages: list[Message], config: CompletionConfig) -> tuple[str, list[dict]]:
    """Split system prompt from messages, convert to Anthropic format.

    Handles:
    - System messages → separate system parameter
    - Tool results → user messages with tool_result blocks (merged if consecutive)
    - Assistant messages with tool_calls → structured content blocks
    - Plain text messages → standard format

    Returns (system_prompt, api_messages).
    """
    system = config.system_prompt or ""
    api_msgs: list[dict] = []

    for msg in messages:
        if msg.role == "system":
            # Anthropic puts system in a separate parameter
            if system:
                system += "\n\n"
            system += msg.content
        elif msg.role == "tool":
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id or "",
                "content": msg.content,
            }
            # Merge consecutive tool results into one user message
            # (Anthropic API requires alternating user/assistant)
            if (api_msgs
                    and api_msgs[-1].get("role") == "user"
                    and isinstance(api_msgs[-1].get("content"), list)):
                api_msgs[-1]["content"].append(tool_result_block)
            else:
                api_msgs.append({
                    "role": "user",
                    "content": [tool_result_block],
                })
        elif msg.role == "assistant" and msg.tool_calls:
            # Assistant message with tool_use blocks — reconstruct structured content
            blocks: list[dict] = []
            if msg.content:
                blocks.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            api_msgs.append({"role": "assistant", "content": blocks})
        else:
            api_msgs.append({
                "role": msg.role,
                "content": msg.content,
            })

    return system, api_msgs


class AnthropicProvider:
    """LLM provider for Anthropic Claude models.

    Args:
        api_key: Anthropic API key.
        model: Default model ID (can be overridden in CompletionConfig).
        base_url: Optional custom base URL.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        base_url: str | None = None,
    ) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package required: pip install anthropic"
            ) from e

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.AsyncAnthropic(**kwargs)
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> CompletionResult:
        model = config.model or self._model
        system, api_msgs = _convert_messages(messages, config)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
        if system:
            kwargs["system"] = system
        tools = _convert_tools(config.tools)
        if tools:
            kwargs["tools"] = tools
        if config.stop_sequences:
            kwargs["stop_sequences"] = config.stop_sequences

        try:
            response = await self._client.messages.create(**kwargs)
        except Exception as e:
            raise ProviderError(f"Anthropic API error: {e}") from e

        # Extract text content and tool calls separately
        content = ""
        tool_calls: list[dict] = []
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return CompletionResult(
            content=content,
            model=response.model,
            usage=usage,
            stop_reason=response.stop_reason or "",
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> AsyncIterator[StreamChunk]:
        model = config.model or self._model
        system, api_msgs = _convert_messages(messages, config)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
        if system:
            kwargs["system"] = system
        tools = _convert_tools(config.tools)
        if tools:
            kwargs["tools"] = tools
        if config.stop_sequences:
            kwargs["stop_sequences"] = config.stop_sequences

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            delta = event.delta
                            if hasattr(delta, "text"):
                                yield StreamChunk(content=delta.text)
                        elif event.type == "message_stop":
                            msg = await stream.get_final_message()
                            yield StreamChunk(
                                content="",
                                is_final=True,
                                usage=TokenUsage(
                                    input_tokens=msg.usage.input_tokens,
                                    output_tokens=msg.usage.output_tokens,
                                ),
                            )
        except Exception as e:
            raise ProviderError(f"Anthropic streaming error: {e}") from e

    async def list_models(self) -> list[dict[str, Any]]:
        """List available Anthropic models. Tries API first, falls back to static."""
        try:
            result = await self._client.models.list(limit=100)
            models = []
            for m in result.data:
                caps = _MODEL_CAPS.get(m.id, _DEFAULT_CAPS)
                models.append({
                    "id": m.id,
                    "name": getattr(m, "display_name", None) or m.id,
                    "context_window": caps["max_context_window"],
                    "max_output": caps["max_output_tokens"],
                    "supports_vision": caps.get("supports_vision", False),
                })
            return models if models else self._static_models()
        except Exception:
            return self._static_models()

    @staticmethod
    def _static_models() -> list[dict[str, Any]]:
        return [
            {
                "id": model_id,
                "name": model_id,
                "context_window": caps["max_context_window"],
                "max_output": caps["max_output_tokens"],
                "supports_vision": caps.get("supports_vision", False),
            }
            for model_id, caps in _MODEL_CAPS.items()
        ]

    def capabilities(self) -> ProviderCapabilities:
        caps = _MODEL_CAPS.get(self._model, _DEFAULT_CAPS)
        return ProviderCapabilities(
            provider_name="anthropic",
            model_id=self._model,
            max_context_window=caps["max_context_window"],
            max_output_tokens=caps["max_output_tokens"],
            supports_streaming=True,
            supports_tool_use=True,
            supports_json_mode=False,  # Anthropic uses prefill instead
            supports_vision=caps["supports_vision"],
            supports_thinking=caps["supports_thinking"],
            cost_per_1k_input=caps["cost_input"],
            cost_per_1k_output=caps["cost_output"],
        )

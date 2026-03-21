"""
OpenAI LLM provider.

Implements LLMProvider Protocol using the OpenAI Chat Completions API.
Requires: openai package (pip install openai).
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from _future.llm.provider import (
    CompletionConfig,
    CompletionResult,
    Message,
    ProviderCapabilities,
    ProviderError,
    StreamChunk,
    TokenUsage,
    ToolDefinition,
)

_MODEL_CAPS: dict[str, dict[str, Any]] = {
    "gpt-4o": {
        "max_context_window": 128_000,
        "max_output_tokens": 16_384,
        "supports_vision": True,
        "cost_input": 0.0025,
        "cost_output": 0.01,
    },
    "gpt-4o-mini": {
        "max_context_window": 128_000,
        "max_output_tokens": 16_384,
        "supports_vision": True,
        "cost_input": 0.00015,
        "cost_output": 0.0006,
    },
    "gpt-4-turbo": {
        "max_context_window": 128_000,
        "max_output_tokens": 4_096,
        "supports_vision": True,
        "cost_input": 0.01,
        "cost_output": 0.03,
    },
    "o1": {
        "max_context_window": 200_000,
        "max_output_tokens": 100_000,
        "supports_vision": True,
        "cost_input": 0.015,
        "cost_output": 0.06,
    },
}

_DEFAULT_CAPS = {
    "max_context_window": 128_000,
    "max_output_tokens": 4_096,
    "supports_vision": False,
    "cost_input": 0.002,
    "cost_output": 0.008,
}


def _convert_tools(tools: list[ToolDefinition] | None) -> list[dict] | None:
    """Convert generic ToolDefinition list to OpenAI function calling format."""
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters if t.parameters else {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def _convert_messages(messages: list[Message], config: CompletionConfig) -> list[dict]:
    """Convert to OpenAI message format.

    System messages in the message list are merged with config.system_prompt
    into a single system message to avoid duplicates.
    """
    system_parts: list[str] = []
    if config.system_prompt:
        system_parts.append(config.system_prompt)

    api_msgs: list[dict] = []
    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        elif msg.role == "tool":
            api_msgs.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id or "",
                "content": msg.content,
            })
        elif msg.role == "assistant" and msg.tool_calls:
            # Reconstruct assistant message with OpenAI tool_calls format
            m: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["input"]) if isinstance(tc["input"], dict) else tc["input"],
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
            api_msgs.append(m)
        else:
            api_msgs.append({
                "role": msg.role,
                "content": msg.content,
            })

    if system_parts:
        api_msgs.insert(0, {"role": "system", "content": "\n\n".join(system_parts)})

    return api_msgs


class OpenAIProvider:
    """LLM provider for OpenAI models (GPT-4o, o1, etc.).

    Args:
        api_key: OpenAI API key.
        model: Default model ID.
        base_url: Optional custom base URL (for Azure OpenAI or proxies).
        organization: Optional OpenAI organization ID.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
        organization: str | None = None,
    ) -> None:
        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "openai package required: pip install openai"
            ) from e

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if organization:
            kwargs["organization"] = organization
        self._client = openai.AsyncOpenAI(**kwargs)
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> CompletionResult:
        model = config.model or self._model
        api_msgs = _convert_messages(messages, config)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
        tools = _convert_tools(config.tools)
        if tools:
            kwargs["tools"] = tools
        if config.stop_sequences:
            kwargs["stop"] = config.stop_sequences
        if config.response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as e:
            raise ProviderError(f"OpenAI API error: {e}") from e

        choice = response.choices[0]
        content = choice.message.content or ""

        # Extract structured tool calls
        tool_calls: list[dict] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                # Parse arguments JSON string to dict
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except (json.JSONDecodeError, TypeError):
                    args = {"_raw": tc.function.arguments}
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": args,
                })

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        # Normalize stop_reason: OpenAI "tool_calls" → "tool_use"
        stop_reason = choice.finish_reason or ""
        if stop_reason == "tool_calls":
            stop_reason = "tool_use"

        return CompletionResult(
            content=content,
            model=response.model or model,
            usage=usage,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> AsyncIterator[StreamChunk]:
        model = config.model or self._model
        api_msgs = _convert_messages(messages, config)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools = _convert_tools(config.tools)
        if tools:
            kwargs["tools"] = tools
        if config.stop_sequences:
            kwargs["stop"] = config.stop_sequences
        if config.response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    # Usage-only chunk at end
                    if chunk.usage:
                        yield StreamChunk(
                            content="",
                            is_final=True,
                            usage=TokenUsage(
                                input_tokens=chunk.usage.prompt_tokens,
                                output_tokens=chunk.usage.completion_tokens,
                            ),
                        )
                    continue

                delta = chunk.choices[0].delta
                finish = chunk.choices[0].finish_reason

                text = delta.content or "" if delta else ""

                if finish:
                    # Don't mark as final here — wait for usage-only chunk
                    if text:
                        yield StreamChunk(content=text)
                elif text:
                    yield StreamChunk(content=text)
        except Exception as e:
            raise ProviderError(f"OpenAI streaming error: {e}") from e

    async def list_models(self) -> list[dict[str, Any]]:
        """List available OpenAI models. Tries API first, falls back to static."""
        try:
            result = await self._client.models.list()
            known = set(_MODEL_CAPS.keys())
            prefixes = ("gpt-4", "gpt-3.5", "o1", "o3", "o4", "chatgpt")
            models = []
            for m in result.data:
                if m.id in known or any(m.id.startswith(p) for p in prefixes):
                    caps = _MODEL_CAPS.get(m.id, _DEFAULT_CAPS)
                    models.append({
                        "id": m.id,
                        "name": m.id,
                        "context_window": caps["max_context_window"],
                        "max_output": caps["max_output_tokens"],
                        "supports_vision": caps.get("supports_vision", False),
                    })
            return sorted(models, key=lambda x: x["id"]) if models else self._static_models()
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
            provider_name="openai",
            model_id=self._model,
            max_context_window=caps["max_context_window"],
            max_output_tokens=caps["max_output_tokens"],
            supports_streaming=True,
            supports_tool_use=True,
            supports_json_mode=True,
            supports_vision=caps["supports_vision"],
            supports_thinking=False,
            cost_per_1k_input=caps["cost_input"],
            cost_per_1k_output=caps["cost_output"],
        )

"""
Ollama LLM provider.

Implements LLMProvider Protocol using the Ollama HTTP API.
No external packages required — uses stdlib urllib.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
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


def _convert_messages(messages: list[Message], config: CompletionConfig) -> list[dict]:
    """Convert to Ollama chat format."""
    api_msgs: list[dict] = []

    if config.system_prompt:
        api_msgs.append({"role": "system", "content": config.system_prompt})

    for msg in messages:
        api_msgs.append({"role": msg.role, "content": msg.content})

    return api_msgs


def _convert_tools(tools: list[ToolDefinition] | None) -> list[dict] | None:
    """Convert generic ToolDefinition list to Ollama tool format."""
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


class OllamaProvider:
    """LLM provider for Ollama local models.

    Uses the Ollama HTTP API (no external package needed).

    Args:
        model: Model name (e.g., "llama3.1", "codellama", "mistral").
        base_url: Ollama server URL (default: http://localhost:11434).
        context_window: Context window size (model-dependent, default 8192).
        max_output: Max output tokens (default 4096).
    """

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        context_window: int = 8192,
        max_output: int = 4096,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._context_window = context_window
        self._max_output = max_output

    def _request_sync(self, path: str, data: dict) -> Any:
        """Make a synchronous HTTP request to Ollama API."""
        url = f"{self._base_url}{path}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ProviderError(
                f"Ollama connection error ({self._base_url}): {e}"
            ) from e

    async def complete(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> CompletionResult:
        import asyncio

        model = config.model or self._model
        api_msgs = _convert_messages(messages, config)

        payload: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        if config.response_format == "json":
            payload["format"] = "json"
        tools = _convert_tools(config.tools)
        if tools:
            payload["tools"] = tools
        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, self._request_sync, "/api/chat", payload
            )
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Ollama API error: {e}") from e

        content = response.get("message", {}).get("content", "")
        done_reason = response.get("done_reason", "")

        # Ollama provides eval_count/prompt_eval_count
        usage = TokenUsage(
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
        )

        return CompletionResult(
            content=content,
            model=response.get("model", model),
            usage=usage,
            stop_reason=done_reason,
        )

    async def stream(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> AsyncIterator[StreamChunk]:
        import asyncio

        model = config.model or self._model
        api_msgs = _convert_messages(messages, config)

        payload: dict[str, Any] = {
            "model": model,
            "messages": api_msgs,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        if config.response_format == "json":
            payload["format"] = "json"
        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        url = f"{self._base_url}/api/chat"
        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None, urllib.request.urlopen, req
            )
        except Exception as e:
            raise ProviderError(
                f"Ollama connection error ({self._base_url}): {e}"
            ) from e

        got_final = False
        try:
            while True:
                line = await asyncio.get_running_loop().run_in_executor(
                    None, resp.readline
                )
                if not line:
                    break

                chunk_data = json.loads(line.decode("utf-8"))
                content = chunk_data.get("message", {}).get("content", "")
                done = chunk_data.get("done", False)

                if done:
                    usage = TokenUsage(
                        input_tokens=chunk_data.get("prompt_eval_count", 0),
                        output_tokens=chunk_data.get("eval_count", 0),
                    )
                    yield StreamChunk(
                        content=content,
                        is_final=True,
                        usage=usage,
                    )
                    got_final = True
                elif content:
                    yield StreamChunk(content=content)

            if not got_final:
                yield StreamChunk(content="", is_final=True)
        except Exception as e:
            raise ProviderError(f"Ollama streaming error: {e}") from e
        finally:
            resp.close()

    async def list_models(self) -> list[dict[str, Any]]:
        """List available Ollama models via /api/tags endpoint."""
        import asyncio

        def _fetch_tags() -> list[dict[str, Any]]:
            url = f"{self._base_url}/api/tags"
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return [
                    {
                        "id": m["name"],
                        "name": m["name"],
                        "context_window": self._context_window,
                        "max_output": self._max_output,
                        "supports_vision": False,
                    }
                    for m in data.get("models", [])
                ]
            except Exception:
                return []

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _fetch_tags)
        except Exception:
            return []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="ollama",
            model_id=self._model,
            max_context_window=self._context_window,
            max_output_tokens=self._max_output,
            supports_streaming=True,
            supports_tool_use=True,
            supports_json_mode=True,
            supports_vision=False,
            supports_thinking=False,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )

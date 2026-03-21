"""
Claude Code CLI LLM provider.

Implements LLMProvider Protocol via Claude Code CLI subprocess in print mode.
Uses the official Claude Code CLI (-p flag) for non-interactive LLM access,
enabling use of Claude Max subscription without separate API billing.

No external packages required — uses stdlib only (asyncio, shutil, json).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shutil
import tempfile
from collections import OrderedDict
from typing import Any, AsyncIterator

from core.llm.provider import (
    CompletionConfig,
    CompletionResult,
    Message,
    ProviderCapabilities,
    ProviderError,
    StreamChunk,
    TokenUsage,
)

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"
_MAX_SESSION_MAP_SIZE = 1000

# Error classification patterns for stderr/stdout parsing
_AUTH_PATTERNS = ("not logged in", "authentication", "unauthorized", "login required")
_RATE_LIMIT_PATTERNS = ("rate limit", "too many requests", "overloaded", "429")


def _classify_error(stderr: str, stdout: str, returncode: int) -> ProviderError:
    """Classify subprocess error into specific ProviderError with actionable message."""
    combined = (stderr + " " + stdout).lower()

    if any(p in combined for p in _AUTH_PATTERNS):
        return ProviderError(
            "Claude Code not authenticated. "
            "Run 'claude' interactively to log in with your Max subscription."
        )

    if any(p in combined for p in _RATE_LIMIT_PATTERNS):
        return ProviderError(
            "Claude Code rate limited. "
            "Wait a moment before retrying, or reduce max_concurrent."
        )

    detail = stderr.strip() or stdout.strip()
    return ProviderError(
        f"Claude Code CLI exited with code {returncode}: "
        f"{detail[:500] if detail else 'no output'}"
    )


async def _kill_process_tree(proc: asyncio.subprocess.Process) -> None:
    """Kill subprocess and its entire process tree.

    On Windows, proc.kill() only terminates the direct child (cmd.exe wrapper),
    leaving Node.js children orphaned. Uses taskkill /F /T for full tree cleanup.
    """
    if proc.returncode is not None:
        return
    if _IS_WINDOWS:
        try:
            kill_proc = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/T", "/PID", str(proc.pid),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await kill_proc.wait()
        except OSError:
            proc.kill()
    else:
        proc.kill()
    await proc.wait()

# Model capability map — mirrors Anthropic models accessible via Claude Code CLI.
# Claude Code uses short names (sonnet, opus, haiku) or full model IDs.
_MODEL_CAPS: dict[str, dict[str, Any]] = {
    "claude-opus-4-6": {
        "max_context_window": 200_000,
        "max_output_tokens": 128_000,
        "supports_vision": True,
        "supports_thinking": True,
    },
    "claude-sonnet-4-6": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
    },
    "claude-haiku-4-5-20251001": {
        "max_context_window": 200_000,
        "max_output_tokens": 64_000,
        "supports_vision": True,
        "supports_thinking": True,
    },
}

# Short aliases used by Claude Code CLI (--model flag)
_MODEL_ALIASES: dict[str, str] = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

_DEFAULT_CAPS = {
    "max_context_window": 200_000,
    "max_output_tokens": 64_000,
    "supports_vision": True,
    "supports_thinking": True,
}


class ClaudeCodeProvider:
    """LLM provider using Claude Code CLI subprocess.

    Runs Claude Code in print mode (-p) as a subprocess, parsing JSON or
    NDJSON output. Designed for Claude Max subscription users who want to
    use their existing plan without separate API billing.

    Args:
        model: Default model short name or full ID (default: "sonnet").
        claude_binary: Name of the Claude Code binary (default: "claude").
        timeout: Subprocess timeout in seconds (default: 120).
        max_concurrent: Maximum concurrent subprocess calls (default: 5).

    Thread safety:
        The _session_map (OrderedDict) is safe for asyncio single-threaded
        event loop access (coroutines interleave only at await points, and
        dict operations are atomic under CPython's GIL). NOT safe for
        multi-threaded access — do not share a provider instance across
        ThreadPoolExecutor workers.
    """

    def __init__(
        self,
        model: str = "sonnet",
        claude_binary: str = "claude",
        timeout: int = 120,
        max_concurrent: int = 5,
    ) -> None:
        resolved = shutil.which(claude_binary)
        if resolved is None:
            raise ProviderError(
                f"Claude Code CLI binary '{claude_binary}' not found in PATH. "
                "Install it via: npm install -g @anthropic-ai/claude-code"
            )
        self._claude_path = resolved
        self._model = model
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session_map: OrderedDict[str, str] = OrderedDict()

    def _resolve_model(self, config_model: str) -> str:
        """Resolve model name: use config override or default."""
        return config_model or self._model

    def _update_session_map(self, forge_sid: str, cc_sid: str) -> None:
        """Store Forge→CC session mapping with LRU eviction."""
        self._session_map[forge_sid] = cc_sid
        self._session_map.move_to_end(forge_sid)
        while len(self._session_map) > _MAX_SESSION_MAP_SIZE:
            self._session_map.popitem(last=False)

    def clear_session(self, forge_session_id: str) -> None:
        """Remove a specific Forge→CC session mapping.

        Call this when a Forge session is deleted or expired to free
        the corresponding Claude Code session reference.
        """
        self._session_map.pop(forge_session_id, None)

    def _build_env(self) -> dict[str, str]:
        """Build subprocess environment with CLAUDECODE cleared.

        MANDATORY: Claude Code sets CLAUDECODE=1 in its environment.
        Child processes inherit this and get rejected with
        'cannot be launched inside another Claude Code session'.
        Clearing it prevents this nested-session guard.
        """
        env = os.environ.copy()
        env["CLAUDECODE"] = ""
        return env

    def _serialize_messages(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> tuple[str, str | None]:
        """Serialize messages into CLI-compatible prompt and system prompt.

        Returns:
            (user_prompt, system_prompt_text) — system_prompt may be None.
        """
        system_parts: list[str] = []
        if config.system_prompt:
            system_parts.append(config.system_prompt)

        conversation_parts: list[str] = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "tool":
                logger.debug(
                    "Skipping tool message (tool_call_id=%s) — "
                    "Claude Code provider does not support tool use",
                    msg.tool_call_id,
                )
            elif msg.role in ("user", "assistant"):
                # Skip empty assistant turns (e.g., text-tool mode with only tool calls)
                if msg.role == "assistant" and not msg.content:
                    continue
                label = "User" if msg.role == "user" else "Assistant"
                conversation_parts.append(f"{label}: {msg.content}")

        system_prompt = "\n\n".join(system_parts) if system_parts else None

        # If single user message with no conversation history, use it directly
        if len(conversation_parts) == 1 and conversation_parts[0].startswith("User: "):
            user_prompt = conversation_parts[0][len("User: "):]
        elif conversation_parts:
            user_prompt = "\n\n".join(conversation_parts)
        else:
            user_prompt = ""

        return user_prompt, system_prompt

    async def _run_subprocess(
        self,
        args: list[str],
        timeout: int | None = None,
    ) -> tuple[str, str, int]:
        """Run Claude Code subprocess with semaphore-limited concurrency.

        Returns:
            (stdout, stderr, returncode)

        Raises:
            ProviderError: On timeout.
        """
        effective_timeout = timeout or self._timeout

        async with self._semaphore:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=self._build_env(),
                )
            except FileNotFoundError:
                raise ProviderError(
                    f"Claude Code CLI binary not found at '{args[0]}'. "
                    "Install it via: npm install -g @anthropic-ai/claude-code"
                )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                await _kill_process_tree(proc)
                raise ProviderError(
                    f"Claude Code subprocess timed out after {effective_timeout}s"
                )
            except asyncio.CancelledError:
                await _kill_process_tree(proc)
                raise

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return stdout, stderr, proc.returncode

    async def complete(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> CompletionResult:
        """Send messages via Claude Code CLI and return complete response.

        Uses -p (print mode) with --output-format json for structured output.
        Ignores config.tools entirely — Claude Code provider does not support
        tool use in consultation mode.
        """
        if config.tools:
            logger.debug(
                "Claude Code provider ignoring %d tool definitions "
                "(supports_tool_use=False)",
                len(config.tools),
            )

        user_prompt, system_prompt = self._serialize_messages(messages, config)
        if not user_prompt:
            raise ProviderError(
                "Claude Code provider requires at least one user message"
            )
        model = self._resolve_model(config.model)

        base_args = [
            self._claude_path,
            "-p", user_prompt,
            "--output-format", "json",
            "--model", model,
        ]

        # Session resume via metadata
        forge_session_id = None
        using_resume = False
        if config.metadata and "forge_session_id" in config.metadata:
            forge_session_id = config.metadata["forge_session_id"]
            cc_session_id = self._session_map.get(forge_session_id)
            if cc_session_id:
                using_resume = True

        args = list(base_args)
        if using_resume:
            args.extend(["--resume", cc_session_id])

        # System prompt via temp file (avoids 32K CLI length limit)
        tmp_file = None
        try:
            if system_prompt:
                tmp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".txt",
                    delete=False,
                    encoding="utf-8",
                )
                tmp_file.write(system_prompt)
                tmp_file.close()
                args.extend(["--append-system-prompt-file", tmp_file.name])

            stdout, stderr, returncode = await self._run_subprocess(args)

            # Resume fallback: if --resume failed, retry without it
            if returncode != 0 and using_resume:
                logger.warning(
                    "Claude Code --resume failed for session %s (cc=%s), "
                    "retrying without resume",
                    forge_session_id, cc_session_id,
                )
                self._session_map.pop(forge_session_id, None)
                retry_args = list(base_args)
                if tmp_file:
                    retry_args.extend(["--append-system-prompt-file", tmp_file.name])
                stdout, stderr, returncode = await self._run_subprocess(retry_args)
                using_resume = False

        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

        if returncode != 0:
            raise _classify_error(stderr, stdout, returncode)

        if stderr.strip():
            logger.debug("Claude Code stderr: %s", stderr.strip())

        # Parse JSON response
        try:
            data = json.loads(stdout.strip())
        except json.JSONDecodeError as e:
            raise ProviderError(
                f"Failed to parse Claude Code JSON response: {e}\n"
                f"stdout: {stdout[:500]}"
            ) from e

        # Check for error response
        if data.get("is_error"):
            raise ProviderError(
                f"Claude Code returned error: {data.get('result', 'unknown error')}"
            )

        content = data.get("result", "")
        usage_data = data.get("usage", {})
        usage = TokenUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
        )

        # Update session map for resume support
        cc_session_id = data.get("session_id")
        if forge_session_id and cc_session_id:
            self._update_session_map(forge_session_id, cc_session_id)

        return CompletionResult(
            content=content,
            model=data.get("model", model),
            usage=usage,
            stop_reason="end_turn",
            tool_calls=[],
        )

    async def stream(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Claude Code CLI via NDJSON output.

        Uses --output-format stream-json for line-by-line JSON events.
        Each line is stripped for CRLF safety on Windows.
        """
        if config.tools:
            logger.debug(
                "Claude Code provider ignoring %d tool definitions "
                "(supports_tool_use=False)",
                len(config.tools),
            )

        user_prompt, system_prompt = self._serialize_messages(messages, config)
        if not user_prompt:
            raise ProviderError(
                "Claude Code provider requires at least one user message"
            )
        model = self._resolve_model(config.model)

        base_args = [
            self._claude_path,
            "-p", user_prompt,
            "--output-format", "stream-json",
            "--model", model,
        ]

        # Session resume via metadata
        forge_session_id = None
        using_resume = False
        if config.metadata and "forge_session_id" in config.metadata:
            forge_session_id = config.metadata["forge_session_id"]
            cc_session_id = self._session_map.get(forge_session_id)
            if cc_session_id:
                using_resume = True

        args = list(base_args)
        if using_resume:
            args.extend(["--resume", cc_session_id])

        # System prompt via temp file
        tmp_file = None
        if system_prompt:
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            )
            tmp_file.write(system_prompt)
            tmp_file.close()
            args.extend(["--append-system-prompt-file", tmp_file.name])

        proc = None
        try:
            async for chunk in self._stream_subprocess(
                args, base_args, tmp_file, forge_session_id, using_resume,
            ):
                yield chunk

        except asyncio.CancelledError:
            raise
        finally:
            if tmp_file:
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass

    async def _stream_subprocess(
        self,
        args: list[str],
        base_args: list[str],
        tmp_file: Any,
        forge_session_id: str | None,
        using_resume: bool,
    ) -> AsyncIterator[StreamChunk]:
        """Internal: run streaming subprocess with resume-fallback.

        If --resume fails (process exits with error before producing content),
        retries without --resume using full conversation history.
        """
        proc = None
        try:
            async with self._semaphore:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=self._build_env(),
                    )
                except FileNotFoundError:
                    raise ProviderError(
                        f"Claude Code CLI binary not found at '{args[0]}'. "
                        "Install it via: npm install -g @anthropic-ai/claude-code"
                    )

                yielded_content = False
                async for raw_line in proc.stdout:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("Skipping non-JSON line: %s", line[:100])
                        continue

                    event_type = event.get("type", "")

                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yielded_content = True
                            yield StreamChunk(content=text)

                    elif event_type == "message_stop":
                        usage_data = event.get("usage", {})
                        usage = None
                        if usage_data:
                            usage = TokenUsage(
                                input_tokens=usage_data.get("input_tokens", 0),
                                output_tokens=usage_data.get("output_tokens", 0),
                            )
                        cc_session_id = event.get("session_id")
                        if forge_session_id and cc_session_id:
                            self._update_session_map(forge_session_id, cc_session_id)
                        yield StreamChunk(content="", is_final=True, usage=usage)

                    elif event_type == "message_delta":
                        usage_data = event.get("usage", {})
                        if usage_data:
                            usage = TokenUsage(
                                input_tokens=usage_data.get("input_tokens", 0),
                                output_tokens=usage_data.get("output_tokens", 0),
                            )
                            yield StreamChunk(content="", is_final=False, usage=usage)

                await proc.wait()

                if proc.returncode != 0:
                    # Resume fallback: retry without --resume if no content was yielded
                    if using_resume and not yielded_content:
                        logger.warning(
                            "Claude Code --resume stream failed for session %s, "
                            "retrying without resume",
                            forge_session_id,
                        )
                        self._session_map.pop(forge_session_id, None)
                        proc = None  # clear for finally

                        retry_args = list(base_args)
                        if tmp_file:
                            retry_args.extend([
                                "--append-system-prompt-file", tmp_file.name,
                            ])

                        proc = await asyncio.create_subprocess_exec(
                            *retry_args,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env=self._build_env(),
                        )
                        async for chunk in self._parse_stream_events(
                            proc, forge_session_id,
                        ):
                            yield chunk
                        return

                    stderr_bytes = await proc.stderr.read()
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    raise _classify_error(stderr, "", proc.returncode)

        except asyncio.CancelledError:
            if proc and proc.returncode is None:
                await _kill_process_tree(proc)
            raise

    async def _parse_stream_events(
        self,
        proc: asyncio.subprocess.Process,
        forge_session_id: str | None,
    ) -> AsyncIterator[StreamChunk]:
        """Parse NDJSON stream events from a subprocess."""
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")
            if event_type == "content_block_delta":
                text = event.get("delta", {}).get("text", "")
                if text:
                    yield StreamChunk(content=text)
            elif event_type == "message_stop":
                usage_data = event.get("usage", {})
                usage = TokenUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                ) if usage_data else None
                cc_sid = event.get("session_id")
                if forge_session_id and cc_sid:
                    self._update_session_map(forge_session_id, cc_sid)
                yield StreamChunk(content="", is_final=True, usage=usage)
            elif event_type == "message_delta":
                usage_data = event.get("usage", {})
                if usage_data:
                    yield StreamChunk(
                        content="",
                        is_final=False,
                        usage=TokenUsage(
                            input_tokens=usage_data.get("input_tokens", 0),
                            output_tokens=usage_data.get("output_tokens", 0),
                        ),
                    )

        await proc.wait()
        if proc.returncode != 0:
            stderr_bytes = await proc.stderr.read()
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            raise _classify_error(stderr, "", proc.returncode)

    def capabilities(self) -> ProviderCapabilities:
        """Return capabilities for Claude Code provider.

        Key differences from direct Anthropic API:
        - supports_tool_use=False (consultation mode only)
        - cost_per_1k=0 (Max subscription = flat rate)
        """
        resolved = _MODEL_ALIASES.get(self._model, self._model)
        caps = _MODEL_CAPS.get(resolved, _DEFAULT_CAPS)
        return ProviderCapabilities(
            provider_name="claude-code",
            model_id=resolved,
            max_context_window=caps["max_context_window"],
            max_output_tokens=caps["max_output_tokens"],
            supports_streaming=True,
            supports_tool_use=False,
            supports_json_mode=False,
            supports_vision=caps["supports_vision"],
            supports_thinking=caps["supports_thinking"],
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )

    async def close(self) -> None:
        """Clean up provider resources. Clears all session mappings."""
        self._session_map.clear()

    async def list_models(self) -> list[dict[str, Any]]:
        """Return static list of models accessible via Claude Code CLI."""
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

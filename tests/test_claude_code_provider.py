"""Tests for ClaudeCodeProvider — Claude Code CLI subprocess LLM provider.

Tests cover:
- Binary path resolution (found / not found)
- Message serialization (system, user, assistant, tool messages)
- JSON output parsing (valid, malformed, error responses)
- Stream-json NDJSON parsing (with CRLF endings)
- Error scenarios (missing binary, timeout, auth, rate limit)
- Session resume (store, resume, fallback, eviction)
- Capabilities values (tool_use=False, cost=0)
- CLAUDECODE env var clearing
- Error classification (_classify_error)

All subprocess calls are mocked — no real Claude Code invocations.
"""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _future.llm.provider import (
    CompletionConfig,
    LLMProvider,
    Message,
    ProviderError,
    TokenUsage,
    ToolDefinition,
)
from _future.llm.providers.claude_code import (
    ClaudeCodeProvider,
    _classify_error,
    _MAX_SESSION_MAP_SIZE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(**kwargs):
    """Create a ClaudeCodeProvider with mocked shutil.which."""
    defaults = {"model": "sonnet", "claude_binary": "claude", "timeout": 10, "max_concurrent": 5}
    defaults.update(kwargs)
    with patch("core.llm.providers.claude_code.shutil.which", return_value="/usr/bin/claude"):
        return ClaudeCodeProvider(**defaults)


def _make_subprocess_mock(stdout=b"", stderr=b"", returncode=0):
    """Create a mock for asyncio.create_subprocess_exec."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.pid = 12345
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    proc.stdout = None
    proc.stderr = AsyncMock()
    proc.stderr.read = AsyncMock(return_value=stderr)
    return proc


def _make_json_response(result="Hello", session_id="cc-123", model="claude-sonnet-4-6",
                        input_tokens=100, output_tokens=50, is_error=False):
    """Build a mock Claude Code JSON response."""
    return json.dumps({
        "session_id": session_id,
        "result": result,
        "model": model,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "cost_usd": 0.0,
        "duration_ms": 500,
        "is_error": is_error,
    }).encode("utf-8")


class AsyncLineIterator:
    """Mock async iterator for proc.stdout that yields bytes lines."""

    def __init__(self, lines: list[bytes]):
        self._lines = list(lines)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._index]
        self._index += 1
        return line


# ---------------------------------------------------------------------------
# Binary path resolution
# ---------------------------------------------------------------------------

class TestBinaryResolution:
    def test_binary_found(self):
        with patch("core.llm.providers.claude_code.shutil.which", return_value="/usr/bin/claude"):
            p = ClaudeCodeProvider(model="sonnet")
            assert p._claude_path == "/usr/bin/claude"

    def test_binary_not_found(self):
        with patch("core.llm.providers.claude_code.shutil.which", return_value=None):
            with pytest.raises(ProviderError, match="not found in PATH"):
                ClaudeCodeProvider(model="sonnet")


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

class TestProtocol:
    def test_isinstance_llm_provider(self):
        p = _make_provider()
        assert isinstance(p, LLMProvider)


# ---------------------------------------------------------------------------
# Message serialization
# ---------------------------------------------------------------------------

class TestMessageSerialization:
    def test_single_user_message(self):
        p = _make_provider()
        msgs = [Message(role="user", content="Hello")]
        config = CompletionConfig()
        prompt, sys = p._serialize_messages(msgs, config)
        assert prompt == "Hello"
        assert sys is None

    def test_system_prompt_from_config(self):
        p = _make_provider()
        msgs = [Message(role="user", content="Hi")]
        config = CompletionConfig(system_prompt="Be helpful.")
        prompt, sys = p._serialize_messages(msgs, config)
        assert prompt == "Hi"
        assert sys == "Be helpful."

    def test_system_messages_merged(self):
        p = _make_provider()
        msgs = [
            Message(role="system", content="Extra context"),
            Message(role="user", content="Hello"),
        ]
        config = CompletionConfig(system_prompt="Base system")
        prompt, sys = p._serialize_messages(msgs, config)
        assert prompt == "Hello"
        assert sys == "Base system\n\nExtra context"

    def test_multi_turn_conversation(self):
        p = _make_provider()
        msgs = [
            Message(role="user", content="What is Python?"),
            Message(role="assistant", content="A language."),
            Message(role="user", content="More?"),
        ]
        config = CompletionConfig()
        prompt, sys = p._serialize_messages(msgs, config)
        assert "User: What is Python?" in prompt
        assert "Assistant: A language." in prompt
        assert "User: More?" in prompt

    def test_tool_messages_filtered(self):
        p = _make_provider()
        msgs = [
            Message(role="user", content="Use tool"),
            Message(role="tool", content="result", tool_call_id="tc-1"),
            Message(role="user", content="Thanks"),
        ]
        config = CompletionConfig()
        prompt, sys = p._serialize_messages(msgs, config)
        assert "result" not in prompt
        assert "Thanks" in prompt

    def test_empty_messages(self):
        p = _make_provider()
        msgs = []
        config = CompletionConfig()
        prompt, sys = p._serialize_messages(msgs, config)
        assert prompt == ""
        assert sys is None


# ---------------------------------------------------------------------------
# complete() — JSON output parsing
# ---------------------------------------------------------------------------

class TestComplete:
    @pytest.mark.asyncio
    async def test_valid_json_response(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stdout=_make_json_response(result="Test response", session_id="cc-abc"),
            returncode=0,
        )
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await p.complete(
                messages=[Message(role="user", content="Hello")],
                config=CompletionConfig(),
            )
        assert result.content == "Test response"
        assert result.stop_reason == "end_turn"
        assert result.tool_calls == []
        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self):
        p = _make_provider()
        proc = _make_subprocess_mock(stdout=b"not json {{{", returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            with pytest.raises(ProviderError, match="Failed to parse"):
                await p.complete(
                    messages=[Message(role="user", content="Hi")],
                    config=CompletionConfig(),
                )

    @pytest.mark.asyncio
    async def test_is_error_response(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stdout=_make_json_response(result="something failed", is_error=True),
            returncode=0,
        )
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            with pytest.raises(ProviderError, match="returned error"):
                await p.complete(
                    messages=[Message(role="user", content="Hi")],
                    config=CompletionConfig(),
                )

    @pytest.mark.asyncio
    async def test_tools_ignored(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stdout=_make_json_response(),
            returncode=0,
        )
        tools = [ToolDefinition(name="test_tool", description="A test tool")]
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await p.complete(
                messages=[Message(role="user", content="Hi")],
                config=CompletionConfig(tools=tools),
            )
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_empty_prompt_raises(self):
        p = _make_provider()
        with pytest.raises(ProviderError, match="requires at least one user message"):
            await p.complete(
                messages=[],
                config=CompletionConfig(),
            )

    @pytest.mark.asyncio
    async def test_nonzero_exit_raises(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stdout=b"",
            stderr=b"something went wrong",
            returncode=1,
        )
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            with pytest.raises(ProviderError, match="exited with code 1"):
                await p.complete(
                    messages=[Message(role="user", content="Hi")],
                    config=CompletionConfig(),
                )

    @pytest.mark.asyncio
    async def test_session_id_stored(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stdout=_make_json_response(session_id="cc-xyz"),
            returncode=0,
        )
        config = CompletionConfig(metadata={"forge_session_id": "forge-1"})
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            await p.complete(
                messages=[Message(role="user", content="Hi")],
                config=config,
            )
        assert p._session_map["forge-1"] == "cc-xyz"


# ---------------------------------------------------------------------------
# stream() — NDJSON event parsing
# ---------------------------------------------------------------------------

class TestStream:
    @pytest.mark.asyncio
    async def test_stream_content_delta(self):
        p = _make_provider()
        lines = [
            json.dumps({"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}).encode() + b"\n",
            json.dumps({"type": "content_block_delta", "delta": {"type": "text_delta", "text": " world"}}).encode() + b"\n",
            json.dumps({"type": "message_stop", "usage": {"input_tokens": 10, "output_tokens": 5}}).encode() + b"\n",
        ]
        proc = AsyncMock()
        proc.stdout = AsyncLineIterator(lines)
        proc.stderr = AsyncMock()
        proc.stderr.read = AsyncMock(return_value=b"")
        proc.returncode = 0
        proc.wait = AsyncMock()
        proc.pid = 1234

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            chunks = []
            async for chunk in p.stream(
                messages=[Message(role="user", content="Hi")],
                config=CompletionConfig(),
            ):
                chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"
        assert chunks[2].is_final is True
        assert chunks[2].usage.input_tokens == 10

    @pytest.mark.asyncio
    async def test_stream_crlf_handling(self):
        """NDJSON lines with CRLF endings (Windows) are handled correctly."""
        p = _make_provider()
        lines = [
            json.dumps({"type": "content_block_delta", "delta": {"text": "OK"}}).encode() + b"\r\n",
            json.dumps({"type": "message_stop"}).encode() + b"\r\n",
        ]
        proc = AsyncMock()
        proc.stdout = AsyncLineIterator(lines)
        proc.stderr = AsyncMock()
        proc.stderr.read = AsyncMock(return_value=b"")
        proc.returncode = 0
        proc.wait = AsyncMock()
        proc.pid = 1234

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            chunks = []
            async for chunk in p.stream(
                messages=[Message(role="user", content="Hi")],
                config=CompletionConfig(),
            ):
                chunks.append(chunk)

        assert chunks[0].content == "OK"
        assert chunks[1].is_final is True

    @pytest.mark.asyncio
    async def test_stream_malformed_line_skipped(self):
        """Malformed JSON lines are skipped, not crash."""
        p = _make_provider()
        lines = [
            b"not json at all\n",
            json.dumps({"type": "content_block_delta", "delta": {"text": "OK"}}).encode() + b"\n",
            json.dumps({"type": "message_stop"}).encode() + b"\n",
        ]
        proc = AsyncMock()
        proc.stdout = AsyncLineIterator(lines)
        proc.stderr = AsyncMock()
        proc.stderr.read = AsyncMock(return_value=b"")
        proc.returncode = 0
        proc.wait = AsyncMock()
        proc.pid = 1234

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            chunks = []
            async for chunk in p.stream(
                messages=[Message(role="user", content="Hi")],
                config=CompletionConfig(),
            ):
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].content == "OK"


# ---------------------------------------------------------------------------
# Error scenarios
# ---------------------------------------------------------------------------

class TestErrors:
    def test_classify_error_auth(self):
        err = _classify_error("Error: not logged in", "", 1)
        assert "not authenticated" in str(err)

    def test_classify_error_rate_limit(self):
        err = _classify_error("rate limit exceeded", "", 1)
        assert "rate limited" in str(err)

    def test_classify_error_generic(self):
        err = _classify_error("unknown problem", "", 42)
        assert "exited with code 42" in str(err)

    @pytest.mark.asyncio
    async def test_file_not_found_in_run_subprocess(self):
        p = _make_provider()
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            with pytest.raises(ProviderError, match="binary not found"):
                await p._run_subprocess(["/nonexistent/claude", "-p", "test"])

    @pytest.mark.asyncio
    async def test_auth_error_from_complete(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stderr=b"Error: not logged in to Claude",
            returncode=1,
        )
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            with pytest.raises(ProviderError, match="not authenticated"):
                await p.complete(
                    messages=[Message(role="user", content="Hi")],
                    config=CompletionConfig(),
                )

    @pytest.mark.asyncio
    async def test_rate_limit_error_from_complete(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stderr=b"rate limit exceeded, please wait",
            returncode=1,
        )
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            with pytest.raises(ProviderError, match="rate limited"):
                await p.complete(
                    messages=[Message(role="user", content="Hi")],
                    config=CompletionConfig(),
                )


# ---------------------------------------------------------------------------
# CLAUDECODE env var clearing
# ---------------------------------------------------------------------------

class TestEnvVar:
    def test_claudecode_cleared(self):
        p = _make_provider()
        with patch.dict("os.environ", {"CLAUDECODE": "1", "HOME": "/home/test"}):
            env = p._build_env()
            assert env["CLAUDECODE"] == ""

    def test_claudecode_set_when_not_present(self):
        p = _make_provider()
        with patch.dict("os.environ", {}, clear=True):
            env = p._build_env()
            assert env["CLAUDECODE"] == ""


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

class TestSessionManagement:
    def test_session_map_update(self):
        p = _make_provider()
        p._update_session_map("forge-1", "cc-1")
        assert p._session_map["forge-1"] == "cc-1"

    def test_session_map_lru_eviction(self):
        p = _make_provider()
        for i in range(_MAX_SESSION_MAP_SIZE + 10):
            p._update_session_map(f"forge-{i}", f"cc-{i}")
        assert len(p._session_map) == _MAX_SESSION_MAP_SIZE
        # Oldest entries evicted
        assert "forge-0" not in p._session_map
        # Newest entries kept
        assert f"forge-{_MAX_SESSION_MAP_SIZE + 9}" in p._session_map

    def test_clear_session(self):
        p = _make_provider()
        p._update_session_map("forge-1", "cc-1")
        p.clear_session("forge-1")
        assert "forge-1" not in p._session_map

    def test_clear_nonexistent_session(self):
        p = _make_provider()
        p.clear_session("nonexistent")  # should not raise

    @pytest.mark.asyncio
    async def test_resume_args_added(self):
        """Second call with same forge_session_id adds --resume."""
        p = _make_provider()
        p._update_session_map("forge-1", "cc-1")

        proc = _make_subprocess_mock(
            stdout=_make_json_response(session_id="cc-2"),
            returncode=0,
        )
        called_args = []
        original_exec = asyncio.create_subprocess_exec

        async def capture_exec(*args, **kwargs):
            called_args.extend(args)
            return proc

        config = CompletionConfig(metadata={"forge_session_id": "forge-1"})
        with patch("asyncio.create_subprocess_exec", side_effect=capture_exec):
            await p.complete(
                messages=[Message(role="user", content="Hi")],
                config=config,
            )

        assert "--resume" in called_args
        assert "cc-1" in called_args

    @pytest.mark.asyncio
    async def test_resume_fallback(self):
        """Failed --resume retries without it and removes stale mapping."""
        p = _make_provider()
        p._update_session_map("forge-1", "cc-stale")

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (with --resume) fails
                return _make_subprocess_mock(
                    stderr=b"session not found",
                    returncode=1,
                )
            else:
                # Retry (without --resume) succeeds
                return _make_subprocess_mock(
                    stdout=_make_json_response(session_id="cc-new"),
                    returncode=0,
                )

        config = CompletionConfig(metadata={"forge_session_id": "forge-1"})
        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await p.complete(
                messages=[Message(role="user", content="Hi")],
                config=config,
            )

        assert call_count == 2
        assert result.content == "Hello"
        # Stale mapping should be removed, new one stored
        assert p._session_map.get("forge-1") == "cc-new"

    @pytest.mark.asyncio
    async def test_close_clears_sessions(self):
        p = _make_provider()
        p._update_session_map("forge-1", "cc-1")
        p._update_session_map("forge-2", "cc-2")
        await p.close()
        assert len(p._session_map) == 0


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class TestCapabilities:
    def test_capabilities_sonnet(self):
        p = _make_provider(model="sonnet")
        caps = p.capabilities()
        assert caps.provider_name == "claude-code"
        assert caps.model_id == "claude-sonnet-4-6"
        assert caps.supports_tool_use is False
        assert caps.supports_streaming is True
        assert caps.supports_vision is True
        assert caps.cost_per_1k_input == 0.0
        assert caps.cost_per_1k_output == 0.0

    def test_capabilities_opus(self):
        p = _make_provider(model="opus")
        caps = p.capabilities()
        assert caps.model_id == "claude-opus-4-6"
        assert caps.max_output_tokens == 128_000

    def test_capabilities_full_model_id(self):
        p = _make_provider(model="claude-sonnet-4-6")
        caps = p.capabilities()
        assert caps.model_id == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------

class TestListModels:
    @pytest.mark.asyncio
    async def test_returns_static_list(self):
        p = _make_provider()
        models = await p.list_models()
        assert len(models) == 3
        ids = {m["id"] for m in models}
        assert "claude-opus-4-6" in ids
        assert "claude-sonnet-4-6" in ids
        assert "claude-haiku-4-5-20251001" in ids


# ---------------------------------------------------------------------------
# System prompt via temp file
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    @pytest.mark.asyncio
    async def test_system_prompt_uses_temp_file(self):
        p = _make_provider()
        proc = _make_subprocess_mock(
            stdout=_make_json_response(),
            returncode=0,
        )
        called_args = []

        async def capture_exec(*args, **kwargs):
            called_args.extend(args)
            return proc

        with patch("asyncio.create_subprocess_exec", side_effect=capture_exec):
            await p.complete(
                messages=[Message(role="user", content="Hi")],
                config=CompletionConfig(system_prompt="You are helpful."),
            )

        assert "--append-system-prompt-file" in called_args

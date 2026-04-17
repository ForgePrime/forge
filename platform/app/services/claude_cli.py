"""Claude CLI wrapper — invokes `claude -p` as subprocess.

Used by Forge orchestrator as Agent-B: receives enriched prompt, executes
autonomously in workspace (file edits + bash), returns delivery JSON.

Every invocation recorded in llm_calls table with cost/tokens/duration.
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass


@dataclass
class CLIResult:
    return_code: int
    stdout: str
    stderr: str
    duration_ms: int
    # Parsed from --output-format json
    session_id: str | None = None
    model_used: str | None = None
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    is_error: bool = False
    api_error_status: str | None = None
    # Final agent response (inside .result field of CLI JSON)
    agent_response: str = ""
    # Extracted delivery JSON (if parseable)
    delivery: dict | None = None
    parse_error: str | None = None


def invoke_claude(
    prompt: str,
    workspace_dir: str,
    model: str = "sonnet",
    max_budget_usd: float = 5.0,
    timeout_sec: int = 900,
    allowed_tools: list[str] | None = None,
    extra_flags: list[str] | None = None,
) -> CLIResult:
    """Invoke Claude CLI as subprocess with given prompt in workspace.

    Returns CLIResult with cost/duration/agent output + parsed delivery dict.
    """
    cmd = [
        "claude",
        "-p",
        "--model", model,
        "--output-format", "json",
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--max-budget-usd", str(max_budget_usd),
        prompt,
    ]
    if extra_flags:
        cmd = cmd[:-1] + list(extra_flags) + [cmd[-1]]

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_sec,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return _parse_cli_output(proc.returncode, proc.stdout, proc.stderr, duration_ms)
    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CLIResult(
            return_code=-1,
            stdout=e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
            stderr=(e.stderr.decode("utf-8", errors="replace") if e.stderr else "") + f"\n[TIMEOUT after {timeout_sec}s]",
            duration_ms=duration_ms,
            is_error=True,
            parse_error=f"timeout after {timeout_sec}s",
        )
    except FileNotFoundError:
        return CLIResult(
            return_code=-1,
            stdout="",
            stderr="claude CLI not found on PATH",
            duration_ms=0,
            is_error=True,
            parse_error="claude CLI not installed",
        )


def _parse_cli_output(returncode: int, stdout: str, stderr: str, duration_ms: int) -> CLIResult:
    """Parse claude CLI --output-format json output."""
    result = CLIResult(
        return_code=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
    )

    stdout = stdout.strip()
    if not stdout:
        result.is_error = True
        result.parse_error = "empty stdout"
        return result

    # Find JSON on first non-empty line (CLI may append non-JSON trailers like "Shell cwd was reset")
    json_line = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            json_line = line
            break

    if not json_line:
        result.parse_error = "no JSON line in stdout"
        result.agent_response = stdout
        return result

    try:
        cli_result = json.loads(json_line)
    except json.JSONDecodeError as e:
        result.parse_error = f"CLI JSON parse error: {e}"
        result.agent_response = stdout
        return result

    # Extract meta from CLI JSON
    result.is_error = bool(cli_result.get("is_error"))
    result.api_error_status = cli_result.get("api_error_status")
    result.session_id = cli_result.get("session_id")
    result.cost_usd = cli_result.get("total_cost_usd")
    usage = cli_result.get("usage") or {}
    result.input_tokens = usage.get("input_tokens")
    result.output_tokens = usage.get("output_tokens")
    result.cache_read_tokens = usage.get("cache_read_input_tokens")
    result.agent_response = cli_result.get("result") or ""

    # Identify model actually used (first key in modelUsage)
    model_usage = cli_result.get("modelUsage") or {}
    if model_usage:
        result.model_used = next(iter(model_usage.keys()))

    # Try to extract delivery JSON from agent_response
    result.delivery, result.parse_error = _extract_delivery_json(result.agent_response)

    return result


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_delivery_json(text: str) -> tuple[dict | None, str | None]:
    """Extract the last JSON object from agent response.

    Agent may wrap in ```json blocks, or output pure JSON, or mix commentary + JSON.
    Strategy: try whole text as JSON first, then find last ```json block, then last {...}.
    """
    text = (text or "").strip()
    if not text:
        return None, "empty agent response"

    # Try whole text
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return d, None
    except json.JSONDecodeError:
        pass

    # Try fenced blocks (last one wins)
    matches = _JSON_BLOCK.findall(text)
    if matches:
        for candidate in reversed(matches):
            try:
                d = json.loads(candidate)
                if isinstance(d, dict):
                    return d, None
            except json.JSONDecodeError:
                continue

    # Try last balanced {...} in text (greedy from end)
    last_open = text.rfind("{")
    last_close = text.rfind("}")
    if last_open != -1 and last_close > last_open:
        candidate = text[last_open:last_close + 1]
        try:
            d = json.loads(candidate)
            if isinstance(d, dict):
                return d, None
        except json.JSONDecodeError as e:
            return None, f"last-braces parse failed: {e}"

    return None, "no JSON object found in agent response"

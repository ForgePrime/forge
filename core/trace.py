"""Forge tracing — structured audit log for all operations.

Writes to forge_output/{project}/trace.jsonl when FORGE_DEBUG=true.
Each line is a self-contained JSON object with timestamp and event type.

Importable by ALL modules (pipeline_*, entity modules, etc.) — no
dependency on pipeline_common to avoid circular imports.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


_DEBUG_CHECKED = None
_BASE_DIR = None


def _is_debug() -> bool:
    val = os.environ.get("FORGE_DEBUG", "").strip().lower()
    if val:
        return val in ("true", "1", "yes")
    env_path = Path(".env")
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() == "FORGE_DEBUG":
                    return value.strip().strip('"').strip("'").lower() in ("true", "1", "yes")
        except OSError:
            pass
    return False


def debug_enabled() -> bool:
    """Check if tracing is enabled. Cached after first call."""
    global _DEBUG_CHECKED
    if _DEBUG_CHECKED is None:
        _DEBUG_CHECKED = _is_debug()
    return _DEBUG_CHECKED


def _get_base_dir() -> Path:
    """Get forge_output base directory."""
    global _BASE_DIR
    if _BASE_DIR is None:
        _BASE_DIR = Path(os.environ.get("FORGE_OUTPUT", "forge_output"))
    return _BASE_DIR


def trace(project: str, entry: dict):
    """Append a trace entry to forge_output/{project}/trace.jsonl.

    Only writes when FORGE_DEBUG=true. Each line is self-contained JSON.
    Silent on errors — tracing must never break operations.
    """
    if not debug_enabled():
        return
    entry["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    trace_path = _get_base_dir() / project / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def trace_cmd(project: str, module: str, command: str, **kwargs):
    """Convenience: trace a command invocation with input data."""
    trace(project, {"event": f"{module}.{command}", **kwargs})

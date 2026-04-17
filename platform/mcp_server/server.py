"""Forge MCP Server — Claude Code integration.

Exposes Forge Platform API as MCP tools that Claude Code can call.
Handles heartbeat in background thread (AI never needs to know about it).

Tools:
  forge_execute   — claim task, get assembled prompt + contract
  forge_deliver   — submit delivery, get validation result
  forge_challenge — trigger challenge on accepted delivery
  forge_fail      — mark execution failed
  forge_decision  — record decision mid-execution
  forge_finding   — report finding mid-execution
"""

import json
import sys
import threading
import time
from typing import Any

import requests

# MCP Server configuration
FORGE_API_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_PROJECT = None
DEFAULT_AGENT = "claude-code"

# Active execution state
_active_execution_id: int | None = None
_heartbeat_thread: threading.Thread | None = None
_heartbeat_stop = threading.Event()


def _api(method: str, path: str, **kwargs) -> dict:
    """Make API call to Forge Platform."""
    url = f"{FORGE_API_URL}{path}"
    r = getattr(requests, method)(url, **kwargs)
    if r.status_code == 204:
        return {"status": "no_content"}
    if r.status_code >= 400:
        return {"error": r.text, "status_code": r.status_code}
    return r.json()


def _start_heartbeat(execution_id: int):
    """Start background heartbeat thread."""
    global _heartbeat_thread, _heartbeat_stop
    _heartbeat_stop.clear()

    def _beat():
        while not _heartbeat_stop.is_set():
            _heartbeat_stop.wait(timeout=600)  # 10 minutes
            if _heartbeat_stop.is_set():
                break
            try:
                _api("post", f"/execute/{execution_id}/heartbeat")
            except Exception:
                pass  # Silent — heartbeat failure is not critical for AI

    _heartbeat_thread = threading.Thread(target=_beat, daemon=True)
    _heartbeat_thread.start()


def _stop_heartbeat():
    """Stop background heartbeat."""
    global _heartbeat_thread
    _heartbeat_stop.set()
    if _heartbeat_thread:
        _heartbeat_thread.join(timeout=2)
        _heartbeat_thread = None


# --- MCP Tool Implementations ---

def forge_execute(project: str, agent: str = DEFAULT_AGENT, lean: bool = False) -> dict:
    """Claim next task, get assembled prompt with contract.

    Returns: task details, assembled prompt (with reputation frame, micro-skills,
    guidelines, reminder, operational contract), and output contract.
    """
    global _active_execution_id, DEFAULT_PROJECT
    DEFAULT_PROJECT = project

    result = _api("get", "/execute", params={
        "project": project,
        "agent": agent,
        "lean": lean,
    })

    if "error" in result:
        return result

    _active_execution_id = result.get("execution_id")
    if _active_execution_id:
        _start_heartbeat(_active_execution_id)

    return result


def forge_deliver(
    reasoning: str,
    ac_evidence: list[dict],
    changes: list[dict] | None = None,
    decisions: list[dict] | None = None,
    findings: list[dict] | None = None,
    assumptions: list[dict] | None = None,
    impact_analysis: dict | None = None,
    completion_claims: dict | None = None,
    deferred: list[dict] | None = None,
    unhandled_scenarios: list[dict] | None = None,
    scope_interpretation: dict | None = None,
    confidence: dict | None = None,
    partial_implementation: dict | None = None,
    propagation_check: dict | None = None,
) -> dict:
    """Submit delivery for validation.

    Returns: ACCEPTED (task DONE) or REJECTED (with fix instructions).
    """
    global _active_execution_id

    if not _active_execution_id:
        return {"error": "No active execution. Call forge_execute first."}

    delivery = {"reasoning": reasoning, "ac_evidence": ac_evidence}

    # Add optional sections
    for key, val in [
        ("changes", changes),
        ("decisions", decisions),
        ("findings", findings),
        ("assumptions", assumptions),
        ("impact_analysis", impact_analysis),
        ("completion_claims", completion_claims),
        ("deferred", deferred),
        ("unhandled_scenarios", unhandled_scenarios),
        ("scope_interpretation", scope_interpretation),
        ("confidence", confidence),
        ("partial_implementation", partial_implementation),
        ("propagation_check", propagation_check),
    ]:
        if val is not None:
            delivery[key] = val

    result = _api("post", f"/execute/{_active_execution_id}/deliver", json=delivery)

    status = result.get("status")
    if status == "ACCEPTED":
        _stop_heartbeat()
        _active_execution_id = None
    # If REJECTED, keep execution active for resubmit

    return result


def forge_challenge(execution_id: int | None = None, challenger_agent: str = "challenger") -> dict:
    """Trigger challenge on an accepted delivery.

    Returns: enriched challenge command with auto-generated questions.
    """
    eid = execution_id or _active_execution_id
    if not eid:
        return {"error": "No execution ID. Provide execution_id or call forge_execute first."}

    return _api("post", f"/execute/{eid}/challenge", json={
        "challenger_agent": challenger_agent,
    })


def forge_fail(reason: str) -> dict:
    """Mark current execution as failed."""
    global _active_execution_id

    if not _active_execution_id:
        return {"error": "No active execution."}

    result = _api("post", f"/execute/{_active_execution_id}/fail", json={
        "reason": reason,
    })

    _stop_heartbeat()
    _active_execution_id = None
    return result


def forge_decision(type: str, issue: str, recommendation: str, reasoning: str = "") -> dict:
    """Record decision mid-execution."""
    if not DEFAULT_PROJECT:
        return {"error": "No project. Call forge_execute first."}

    return _api("post", f"/projects/{DEFAULT_PROJECT}/decisions", json=[{
        "external_id": f"D-AUTO-{int(time.time())}",
        "type": type,
        "issue": issue,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "status": "CLOSED",
    }])


def forge_finding(type: str, severity: str, title: str, description: str,
                  evidence: str, file_path: str = "", line_number: int = 0,
                  suggested_action: str = "") -> dict:
    """Report finding mid-execution (bug, improvement, risk discovered)."""
    if not _active_execution_id:
        return {"error": "No active execution."}

    # Findings go through delivery, not separate endpoint in current API
    # Store locally and include in delivery
    return {
        "stored_locally": True,
        "note": "Include this finding in your forge_deliver() call under 'findings' parameter.",
        "finding": {
            "type": type,
            "severity": severity,
            "title": title,
            "description": description,
            "evidence": evidence,
            "file_path": file_path,
            "line_number": line_number,
            "suggested_action": suggested_action,
        }
    }


# --- CLI interface for testing ---

def main():
    """Simple CLI for testing MCP server tools."""
    if len(sys.argv) < 2:
        print("Usage: python -m mcp_server.server <command> [args]")
        print("Commands: execute, deliver, challenge, fail, status")
        return

    cmd = sys.argv[1]

    if cmd == "execute":
        project = sys.argv[2] if len(sys.argv) > 2 else "test-project"
        result = forge_execute(project)
        if "error" in result:
            print(f"Error: {result}")
        else:
            print(f"Execution ID: {result.get('execution_id')}")
            print(f"Task: {result['task']['id']} — {result['task']['name']}")
            print(f"Ceremony: {result['contract']['ceremony_level']}")
            print(f"Prompt: {result['prompt']['meta']['total_kb']} KB")
            print(f"Elements: {result['prompt']['meta']['elements_included']} included, "
                  f"{result['prompt']['meta']['elements_excluded']} excluded")
            print(f"\n--- PROMPT ---\n{result['prompt']['full_text'][:2000]}")

    elif cmd == "status":
        project = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PROJECT or "test-project"
        result = _api("get", f"/projects/{project}/status")
        print(json.dumps(result, indent=2))

    elif cmd == "challenge":
        eid = int(sys.argv[2]) if len(sys.argv) > 2 else _active_execution_id
        result = forge_challenge(eid)
        if "error" in result:
            print(f"Error: {result}")
        else:
            print(f"Challenge execution: {result.get('challenge_execution_id')}")
            print(f"Questions: {result.get('questions_count')}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()

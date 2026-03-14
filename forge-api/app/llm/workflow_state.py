"""Workflow State Machine (ADR-2, T-044)

Defines workflow step sequences for different session types.
Tracks progress through workflow steps with soft enforcement
(warns on deviation, doesn't hard block).
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Workflow definitions: session_type → step sequence
# ---------------------------------------------------------------------------

WORKFLOW_DEFINITIONS: dict[str, dict[str, Any]] = {
    "plan": {
        "workflow_id": "plan",
        "steps": [
            {"name": "draft", "expected_tools": ["draftPlan"], "description": "Create draft plan"},
            {"name": "review", "expected_tools": ["showDraft"], "description": "Review draft plan"},
            {"name": "approve", "expected_tools": ["approvePlan"], "description": "Approve and materialize plan"},
        ],
        "allow_deviation": True,
    },
    "execute": {
        "workflow_id": "execute",
        "steps": [
            {"name": "context", "expected_tools": ["getTaskContext", "getEntity", "listEntities"], "description": "Load task context"},
            {"name": "implement", "expected_tools": [], "description": "Implement the task (any tools allowed)"},
            {"name": "validate", "expected_tools": ["runGates"], "description": "Run validation gates"},
            {"name": "complete", "expected_tools": ["completeTask", "recordChange"], "description": "Record changes and complete task"},
        ],
        "allow_deviation": True,
    },
    "compound": {
        "workflow_id": "compound",
        "steps": [
            {"name": "review", "expected_tools": ["getProjectStatus", "listEntities", "searchEntities"], "description": "Review project state"},
            {"name": "extract", "expected_tools": ["createLesson"], "description": "Extract lessons learned"},
            {"name": "promote", "expected_tools": ["promoteLesson"], "description": "Promote important lessons"},
        ],
        "allow_deviation": True,
    },
    "verify": {
        "workflow_id": "verify",
        "steps": [
            {"name": "load", "expected_tools": ["getEntity", "getTaskContext"], "description": "Load entity for review"},
            {"name": "analyze", "expected_tools": ["searchEntities", "listEntities"], "description": "Analyze related entities"},
            {"name": "record", "expected_tools": ["createDecision", "recordChange"], "description": "Record findings"},
        ],
        "allow_deviation": True,
    },
}


def create_workflow_state(session_type: str) -> dict | None:
    """Create initial workflow state for a session type.

    Returns None if the session type has no workflow definition.
    """
    defn = WORKFLOW_DEFINITIONS.get(session_type)
    if not defn:
        return None

    return {
        "workflow_id": defn["workflow_id"],
        "current_step": 0,
        "completed_steps": [],
        "steps": defn["steps"],
        "allow_deviation": defn.get("allow_deviation", True),
    }


def check_tool_against_workflow(
    workflow_state: dict,
    tool_name: str,
) -> dict[str, Any]:
    """Check if a tool call matches the expected workflow step.

    Returns:
        {
            "allowed": True/False,
            "warning": str | None,  # Warning message if deviating
            "step_advanced": bool,  # Whether the current step was advanced
        }
    """
    if not workflow_state:
        return {"allowed": True, "warning": None, "step_advanced": False}

    steps = workflow_state.get("steps", [])
    current_idx = workflow_state.get("current_step", 0)

    if current_idx >= len(steps):
        # All steps completed — any tool is fine
        return {"allowed": True, "warning": None, "step_advanced": False}

    current_step = steps[current_idx]
    expected_tools = current_step.get("expected_tools", [])

    # Empty expected_tools means any tool is valid for this step
    if not expected_tools:
        return {"allowed": True, "warning": None, "step_advanced": False}

    if tool_name in expected_tools:
        # Tool matches expected — advance the step
        return {"allowed": True, "warning": None, "step_advanced": True}

    # Check if tool matches a future step (skip ahead)
    for future_idx in range(current_idx + 1, len(steps)):
        future_step = steps[future_idx]
        if tool_name in future_step.get("expected_tools", []):
            # Skipping steps — warn but allow
            skipped = [steps[i]["name"] for i in range(current_idx, future_idx)]
            return {
                "allowed": True,
                "warning": (
                    f"Workflow step skip: expected '{current_step['name']}' "
                    f"({current_step['description']}), but tool '{tool_name}' "
                    f"matches step '{future_step['name']}'. Skipped: {', '.join(skipped)}."
                ),
                "step_advanced": True,
                "advance_to": future_idx,
            }

    # Tool doesn't match any expected step
    allow = workflow_state.get("allow_deviation", True)
    if allow:
        return {
            "allowed": True,
            "warning": (
                f"Workflow deviation: expected step '{current_step['name']}' "
                f"({current_step['description']}), but got tool '{tool_name}'. "
                f"This is allowed but may not follow the optimal workflow order."
            ),
            "step_advanced": False,
        }

    return {
        "allowed": False,
        "warning": (
            f"Workflow blocked: expected step '{current_step['name']}' "
            f"({current_step['description']}), but got tool '{tool_name}'."
        ),
        "step_advanced": False,
    }


def advance_workflow(workflow_state: dict, tool_name: str, check_result: dict) -> dict:
    """Advance the workflow state based on a tool execution.

    Returns the updated workflow_state (mutated in place for convenience).
    """
    if not check_result.get("step_advanced"):
        return workflow_state

    steps = workflow_state.get("steps", [])
    current_idx = workflow_state.get("current_step", 0)

    advance_to = check_result.get("advance_to", current_idx)

    # Mark completed steps
    for i in range(current_idx, advance_to + 1):
        if i < len(steps):
            step_name = steps[i]["name"]
            if step_name not in workflow_state["completed_steps"]:
                workflow_state["completed_steps"].append(step_name)

    # Advance to next step
    workflow_state["current_step"] = min(advance_to + 1, len(steps))

    return workflow_state

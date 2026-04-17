"""Test scenario auto-generation from Acceptance Criteria.

For each AC with verification='test' or 'command', generates a structured
test scenario stub: preconditions → action → expected_outcome → assertions.

Heuristic-based (no LLM): uses scenario_type + verb/keyword detection.
Agent-B receives these stubs in the prompt and fills in the implementation.
"""

import re
from dataclasses import dataclass, field


ACTION_VERBS = {
    "create": ("POST", 201),
    "add": ("POST", 201),
    "register": ("POST", 201),
    "update": ("PATCH", 200),
    "modify": ("PATCH", 200),
    "edit": ("PATCH", 200),
    "delete": ("DELETE", 204),
    "remove": ("DELETE", 204),
    "get": ("GET", 200),
    "list": ("GET", 200),
    "fetch": ("GET", 200),
    "read": ("GET", 200),
    "show": ("GET", 200),
}

NEGATIVE_EXPECTATIONS = {
    "positive": "Operation succeeds",
    "negative": "Operation is rejected with appropriate error code (400/409/422)",
    "edge_case": "Boundary condition handled correctly without crash",
    "regression": "Existing behavior preserved",
}


@dataclass
class ScenarioStub:
    ac_position: int
    scenario_type: str
    title: str
    preconditions: list[str] = field(default_factory=list)
    action: str = ""
    expected_outcome: str = ""
    assertions: list[str] = field(default_factory=list)
    hint_http_method: str | None = None
    hint_status_code: int | None = None

    def to_dict(self) -> dict:
        return {
            "ac_position": self.ac_position,
            "scenario_type": self.scenario_type,
            "title": self.title,
            "preconditions": self.preconditions,
            "action": self.action,
            "expected_outcome": self.expected_outcome,
            "assertions": self.assertions,
            "hint_http_method": self.hint_http_method,
            "hint_status_code": self.hint_status_code,
        }


def generate_scenarios(acceptance_criteria: list) -> list[ScenarioStub]:
    """Generate test scenario stubs for each AC.

    Accepts a list of AcceptanceCriterion ORM objects or dicts with
    position/text/scenario_type/verification/test_path/command.
    """
    stubs: list[ScenarioStub] = []
    for ac in acceptance_criteria:
        position = _get(ac, "position")
        text = _get(ac, "text") or ""
        scenario_type = _get(ac, "scenario_type") or "positive"
        verification = _get(ac, "verification") or "manual"
        test_path = _get(ac, "test_path")
        command = _get(ac, "command")

        if verification == "manual":
            continue

        stub = ScenarioStub(
            ac_position=position,
            scenario_type=scenario_type,
            title=_shorten(text, 80),
        )

        # Detect HTTP verb/status from AC text
        text_lower = text.lower()
        for verb, (method, status) in ACTION_VERBS.items():
            if re.search(rf"\b{verb}\b", text_lower):
                stub.hint_http_method = method
                stub.hint_status_code = status if scenario_type == "positive" else _error_status(scenario_type, text_lower)
                break

        # Build action hint
        if stub.hint_http_method and "/" in text:
            path_match = re.search(r"/[\w/{}\-]+", text)
            path = path_match.group(0) if path_match else "/resource"
            stub.action = f"{stub.hint_http_method} {path}"
        elif test_path:
            stub.action = f"Run test: {test_path}"
        elif command:
            stub.action = f"Execute: {command}"
        else:
            stub.action = f"Exercise the behavior described in AC"

        stub.expected_outcome = NEGATIVE_EXPECTATIONS.get(scenario_type, "Behavior matches AC text")

        # Base assertions
        if stub.hint_status_code:
            stub.assertions.append(f"response.status_code == {stub.hint_status_code}")
        if scenario_type == "negative":
            stub.assertions.append("response body contains error message describing the rejection")
            stub.assertions.append("no side effects persisted (DB unchanged)")
        if scenario_type == "edge_case":
            stub.assertions.append("no exception raised, boundary value handled explicitly")
        if scenario_type == "positive":
            stub.assertions.append("response body contains created/modified entity")
            stub.assertions.append("DB state reflects the change")

        # Preconditions based on common patterns
        if "existing" in text_lower or "duplicate" in text_lower:
            stub.preconditions.append("Entity with conflicting field already exists in DB")
        if "authenticated" in text_lower or "logged in" in text_lower:
            stub.preconditions.append("Request includes valid auth credentials")
        if "with valid" in text_lower:
            stub.preconditions.append("Valid payload constructed per schema")
        if "with invalid" in text_lower or "invalid" in text_lower and scenario_type == "negative":
            stub.preconditions.append("Invalid payload constructed (field-level violations)")

        stubs.append(stub)
    return stubs


def _get(ac, key):
    if hasattr(ac, key):
        return getattr(ac, key)
    if isinstance(ac, dict):
        return ac.get(key)
    return None


def _shorten(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n].rstrip() + "..."


def _error_status(scenario_type: str, text: str) -> int:
    if "duplicate" in text or "already exists" in text or "conflict" in text:
        return 409
    if "unauthorized" in text or "forbidden" in text or "auth" in text:
        return 401
    if "not found" in text or "missing" in text:
        return 404
    return 422

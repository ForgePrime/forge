"""Review contracts — code review, verification."""

from core.llm.contract import LLMContract, RetryStrategy, ValidationRule


CodeReviewContract = LLMContract(
    id="code-review-v1",
    name="Code Review",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["task", "changes"],
        "properties": {
            "task": {"type": "object", "description": "Task that was executed"},
            "changes": {
                "type": "array",
                "items": {"type": "object"},
                "description": "File changes with before/after",
            },
            "guidelines": {"type": "array", "items": {"type": "object"}},
        },
    },
    output_schema={
        "type": "object",
        "required": ["findings", "summary", "verdict"],
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "severity", "file", "description"],
                    "properties": {
                        "id": {"type": "string", "description": "F-NNN format"},
                        "severity": {"type": "string", "enum": ["critical", "important", "minor"]},
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "description": {"type": "string"},
                        "suggestion": {"type": "string"},
                        "guideline_id": {"type": "string", "description": "Violated guideline ID if any"},
                    },
                },
            },
            "summary": {"type": "string"},
            "verdict": {
                "type": "string",
                "enum": ["approve", "request-changes", "needs-discussion"],
            },
            "guidelines_checked": {"type": "array", "items": {"type": "string"}},
        },
    },
    output_format="json",
    system_prompt_template=(
        "You are performing a code review. Be thorough but pragmatic.\n\n"
        "Severity levels:\n"
        "- critical: Security vulnerability, data loss, or crash\n"
        "- important: Bug, performance issue, or significant design problem\n"
        "- minor: Style, naming, or minor improvement\n\n"
        "Check changes against provided guidelines.\n"
        "Use verdict: approve (no critical/important), request-changes (has issues), "
        "needs-discussion (architectural concerns)."
    ),
    user_prompt_template=(
        "## Task\n{task_json}\n\n"
        "## Changes\n{changes_json}\n\n"
        "## Guidelines\n{guidelines_json}\n\n"
        "Review these changes."
    ),
    validation_rules=[
        ValidationRule(
            id="valid-verdict",
            description="Verdict must be valid enum value",
            check_fn=lambda o: o.get("verdict") in ("approve", "request-changes", "needs-discussion"),
        ),
        ValidationRule(
            id="valid-severities",
            description="Finding severities must be valid",
            check_fn=lambda o: all(
                f.get("severity") in ("critical", "important", "minor")
                for f in o.get("findings", [])
            ),
        ),
        ValidationRule(
            id="consistent-verdict",
            description="If critical findings exist, verdict cannot be approve",
            check_fn=lambda o: (
                not any(f.get("severity") == "critical" for f in o.get("findings", []))
                or o.get("verdict") != "approve"
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1, escalate_on=["semantic_error"]),
    min_context_window=32_000,
    requires_json_mode=True,
)


VerificationContract = LLMContract(
    id="verify-v1",
    name="Verify Task Completion",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["task", "changes", "acceptance_criteria"],
        "properties": {
            "task": {"type": "object"},
            "changes": {"type": "array", "items": {"type": "object"}},
            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            "test_results": {"type": "object", "description": "Gate check results if available"},
        },
    },
    output_schema={
        "type": "object",
        "required": ["ac_results", "overall_pass", "summary"],
        "properties": {
            "ac_results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["criterion", "met", "evidence"],
                    "properties": {
                        "criterion": {"type": "string"},
                        "met": {"type": "boolean"},
                        "evidence": {"type": "string", "description": "Why this is met or not"},
                    },
                },
            },
            "overall_pass": {"type": "boolean"},
            "summary": {"type": "string"},
            "issues": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Issues found that prevent passing",
            },
        },
    },
    output_format="json",
    system_prompt_template=(
        "Verify that a task's acceptance criteria are met by the changes made.\n\n"
        "For each criterion, determine if it's met based on the code changes. "
        "overall_pass should be true only if ALL criteria are met.\n\n"
        "Be strict: if evidence is ambiguous, mark as not met."
    ),
    user_prompt_template=(
        "## Task\n{task_json}\n\n"
        "## Acceptance Criteria\n{ac_json}\n\n"
        "## Changes Made\n{changes_json}\n\n"
        "## Test Results\n{test_results}\n\n"
        "Verify task completion."
    ),
    validation_rules=[
        ValidationRule(
            id="all-ac-covered",
            description="Every acceptance criterion must have a result",
        ),
        ValidationRule(
            id="consistent-pass",
            description="overall_pass must be true only if all AC are met",
            check_fn=lambda o: (
                o.get("overall_pass") is False
                or all(r.get("met", False) for r in o.get("ac_results", []))
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1),
    min_context_window=16_000,
    requires_json_mode=True,
)

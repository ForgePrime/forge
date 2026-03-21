"""Task execution contracts — for executing tasks via LLM."""

from core.llm.contract import LLMContract, RetryStrategy, ValidationRule


TaskExecutionContract = LLMContract(
    id="task-execution-v1",
    name="Execute Task",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["task", "context"],
        "properties": {
            "task": {
                "type": "object",
                "description": "Full task data including AC, description, instruction",
            },
            "context": {
                "type": "object",
                "description": "Assembled context from ContextAssembler",
            },
        },
    },
    output_schema={
        "type": "object",
        "required": ["result", "reasoning_trace", "guidelines_checked"],
        "properties": {
            "result": {
                "type": "object",
                "required": ["files_changed", "summary"],
                "properties": {
                    "files_changed": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "action", "description"],
                            "properties": {
                                "path": {"type": "string"},
                                "action": {"type": "string", "enum": ["create", "edit", "delete"]},
                                "description": {"type": "string"},
                            },
                        },
                    },
                    "summary": {"type": "string", "description": "What was done and why"},
                },
            },
            "reasoning_trace": {
                "type": "string",
                "description": "Step-by-step reasoning for decisions made",
            },
            "guidelines_checked": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of guideline IDs that were checked",
            },
            "decisions_made": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "choice": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                },
            },
            "ac_status": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "criterion": {"type": "string"},
                        "met": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                },
            },
        },
    },
    output_format="json",
    context_assembly="full",
    system_prompt_template=(
        "You are executing a software engineering task within the Forge orchestration system.\n\n"
        "## Task\n{task_name}: {task_description}\n\n"
        "## Instructions\n{task_instruction}\n\n"
        "## Acceptance Criteria\n{acceptance_criteria}\n\n"
        "## Guidelines to Follow\n{guidelines}\n\n"
        "Execute the task. For every file change, explain WHY. "
        "Check all applicable guidelines. Report AC status."
    ),
    user_prompt_template=(
        "Execute this task now. Return your result as JSON matching the output schema.\n\n"
        "## Context\n{context}"
    ),
    validation_rules=[
        ValidationRule(
            id="has-files-changed",
            description="Result must include at least one file change",
            check_fn=lambda o: len(o.get("result", {}).get("files_changed", [])) > 0,
        ),
        ValidationRule(
            id="has-reasoning",
            description="Reasoning trace must not be empty",
            check_fn=lambda o: len(o.get("reasoning_trace", "")) > 10,
        ),
        ValidationRule(
            id="has-guidelines",
            description="At least one guideline must be checked",
            check_fn=lambda o: len(o.get("guidelines_checked", [])) > 0,
        ),
    ],
    retry_strategy=RetryStrategy(
        max_retries=2,
        retry_on=["schema_error", "missing_field", "parse_error"],
        escalate_on=["semantic_error"],
    ),
    min_context_window=32_000,
    requires_json_mode=True,
    fallback_format="markdown",
)


QuickTaskContract = LLMContract(
    id="task-quick-v1",
    name="Quick Task Execution",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["task"],
        "properties": {
            "task": {"type": "object", "description": "Task data"},
        },
    },
    output_schema={
        "type": "object",
        "required": ["result", "summary"],
        "properties": {
            "result": {
                "type": "object",
                "required": ["files_changed", "summary"],
                "properties": {
                    "files_changed": {"type": "array", "items": {"type": "object"}},
                    "summary": {"type": "string"},
                },
            },
            "summary": {"type": "string"},
        },
    },
    output_format="json",
    context_assembly="minimal",
    system_prompt_template=(
        "You are executing a quick task. Be concise and direct.\n\n"
        "## Task\n{task_name}: {task_description}\n\n"
        "Execute and return JSON with files_changed and summary."
    ),
    user_prompt_template="Execute: {task_instruction}",
    validation_rules=[
        ValidationRule(
            id="has-summary",
            description="Must include a summary",
            check_fn=lambda o: len(o.get("summary", "")) > 0,
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1),
    min_context_window=8_000,
    requires_json_mode=True,
)

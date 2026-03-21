"""Planning contracts — plan decomposition, AC suggestion, guideline matching."""

from core.llm.contract import LLMContract, RetryStrategy, ValidationRule


PlanDecompositionContract = LLMContract(
    id="plan-decompose-v1",
    name="Decompose Goal into Task Graph",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["goal", "project_context"],
        "properties": {
            "goal": {"type": "string", "description": "High-level goal to decompose"},
            "project_context": {"type": "object", "description": "Project metadata and existing tasks"},
            "constraints": {"type": "array", "items": {"type": "string"}},
            "knowledge": {"type": "array", "items": {"type": "object"}},
        },
    },
    output_schema={
        "type": "object",
        "required": ["tasks", "reasoning"],
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "description", "acceptance_criteria"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "instruction": {"type": "string"},
                        "type": {"type": "string", "enum": ["feature", "bug", "chore", "investigation"]},
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                        "depends_on_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Indices into this tasks array for dependencies",
                        },
                        "parallel": {"type": "boolean"},
                        "scopes": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "reasoning": {"type": "string", "description": "Why this decomposition was chosen"},
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                        "recommendation": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                },
            },
        },
    },
    output_format="json",
    system_prompt_template=(
        "You are decomposing a software goal into a dependency-aware task graph.\n\n"
        "Rules:\n"
        "- Each task must have clear, testable acceptance criteria\n"
        "- Dependencies must form a DAG (no cycles)\n"
        "- Prefer parallel tasks where possible\n"
        "- Include investigation tasks when unknowns exist\n"
        "- Flag architectural decisions that need human input\n"
        "- Keep tasks focused — each should take 1-4 hours\n\n"
        "## Project Context\n{project_context}"
    ),
    user_prompt_template=(
        "## Goal\n{goal}\n\n"
        "## Constraints\n{constraints}\n\n"
        "## Relevant Knowledge\n{knowledge}\n\n"
        "Decompose this goal into tasks."
    ),
    validation_rules=[
        ValidationRule(
            id="has-tasks",
            description="Must produce at least one task",
            check_fn=lambda o: len(o.get("tasks", [])) > 0,
        ),
        ValidationRule(
            id="all-have-ac",
            description="Every task must have acceptance criteria",
            check_fn=lambda o: all(
                len(t.get("acceptance_criteria", [])) > 0
                for t in o.get("tasks", [])
            ),
        ),
        ValidationRule(
            id="valid-deps",
            description="Dependency indices must be valid (within array bounds)",
            check_fn=lambda o: all(
                all(0 <= d < len(o.get("tasks", [])) and d != i
                    for d in t.get("depends_on_indices", []))
                for i, t in enumerate(o.get("tasks", []))
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=2, escalate_on=["semantic_error"]),
    min_context_window=32_000,
    requires_json_mode=True,
)


ACSuggestionContract = LLMContract(
    id="ac-suggest-v1",
    name="Suggest Acceptance Criteria",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["task"],
        "properties": {
            "task": {"type": "object", "description": "Task to suggest AC for"},
            "templates": {"type": "array", "items": {"type": "object"}, "description": "Available AC templates"},
            "guidelines": {"type": "array", "items": {"type": "object"}, "description": "Active guidelines"},
        },
    },
    output_schema={
        "type": "object",
        "required": ["criteria"],
        "properties": {
            "criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["text", "source", "confidence"],
                    "properties": {
                        "text": {"type": "string", "description": "The acceptance criterion text"},
                        "source": {
                            "type": "string",
                            "enum": ["template", "guideline", "inferred"],
                            "description": "Where this criterion came from",
                        },
                        "source_id": {"type": "string", "description": "Template/guideline ID if applicable"},
                        "confidence": {"type": "number", "description": "0-1"},
                    },
                },
            },
        },
    },
    output_format="json",
    system_prompt_template=(
        "Suggest acceptance criteria for the given task.\n\n"
        "Sources:\n"
        "- template: From AC template library\n"
        "- guideline: Derived from active guidelines\n"
        "- inferred: Inferred from task description and context\n\n"
        "Each criterion must be specific, testable, and unambiguous."
    ),
    user_prompt_template=(
        "## Task\n{task_json}\n\n"
        "## Available Templates\n{templates_json}\n\n"
        "## Active Guidelines\n{guidelines_json}\n\n"
        "Suggest acceptance criteria."
    ),
    validation_rules=[
        ValidationRule(
            id="has-criteria",
            description="Must suggest at least one criterion",
            check_fn=lambda o: len(o.get("criteria", [])) > 0,
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1),
    min_context_window=8_000,
    requires_json_mode=True,
)


GuidelineMatchContract = LLMContract(
    id="guideline-match-v1",
    name="Match Guidelines to Entity",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["entity", "guidelines"],
        "properties": {
            "entity": {"type": "object", "description": "Entity to match guidelines for"},
            "guidelines": {"type": "array", "items": {"type": "object"}, "description": "All active guidelines"},
        },
    },
    output_schema={
        "type": "object",
        "required": ["matches"],
        "properties": {
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["guideline_id", "relevance", "reasoning"],
                    "properties": {
                        "guideline_id": {"type": "string"},
                        "relevance": {"type": "number", "description": "0-1"},
                        "reasoning": {"type": "string"},
                    },
                },
            },
        },
    },
    output_format="json",
    system_prompt_template=(
        "Match relevant guidelines to the given entity. "
        "Score relevance 0-1. Only include guidelines with relevance >= 0.3."
    ),
    user_prompt_template=(
        "## Entity\n{entity_json}\n\n"
        "## Guidelines\n{guidelines_json}\n\n"
        "Match applicable guidelines."
    ),
    validation_rules=[
        ValidationRule(
            id="valid-relevance",
            description="Relevance scores must be 0-1",
            check_fn=lambda o: all(
                0 <= m.get("relevance", -1) <= 1
                for m in o.get("matches", [])
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1),
    min_context_window=8_000,
    requires_json_mode=True,
)

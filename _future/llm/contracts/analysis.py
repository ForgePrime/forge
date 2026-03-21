"""Analysis contracts — risk assessment, lesson promotion."""

from core.llm.contract import LLMContract, RetryStrategy, ValidationRule


RiskAssessmentContract = LLMContract(
    id="risk-assess-v1",
    name="Assess Project Risks",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["project", "tasks"],
        "properties": {
            "project": {"type": "object", "description": "Project metadata"},
            "tasks": {"type": "array", "items": {"type": "object"}},
            "decisions": {"type": "array", "items": {"type": "object"}},
            "knowledge": {"type": "array", "items": {"type": "object"}},
        },
    },
    output_schema={
        "type": "object",
        "required": ["risks"],
        "properties": {
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "severity", "likelihood", "impact", "mitigation"],
                    "properties": {
                        "title": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                        "likelihood": {"type": "string", "enum": ["unlikely", "possible", "likely", "certain"]},
                        "impact": {"type": "string", "description": "What happens if this risk materializes"},
                        "mitigation": {"type": "string", "description": "How to mitigate this risk"},
                        "affected_tasks": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "overall_risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            },
        },
    },
    output_format="json",
    system_prompt_template=(
        "Analyze the project for risks. Consider:\n"
        "- Technical risks (complexity, unknowns, dependencies)\n"
        "- Scope risks (requirement changes, feature creep)\n"
        "- Resource risks (skills, availability)\n"
        "- Integration risks (external dependencies, APIs)\n\n"
        "Be realistic. Don't invent unlikely risks."
    ),
    user_prompt_template=(
        "## Project\n{project_json}\n\n"
        "## Tasks\n{tasks_json}\n\n"
        "## Open Decisions\n{decisions_json}\n\n"
        "Assess project risks."
    ),
    validation_rules=[
        ValidationRule(
            id="valid-severities",
            description="Severity must be valid enum",
            check_fn=lambda o: all(
                r.get("severity") in ("low", "medium", "high", "critical")
                for r in o.get("risks", [])
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1),
    min_context_window=16_000,
    requires_json_mode=True,
)


LessonPromotionContract = LLMContract(
    id="lesson-promote-v1",
    name="Evaluate Lesson for Promotion",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["lesson"],
        "properties": {
            "lesson": {"type": "object", "description": "Lesson to evaluate"},
            "existing_knowledge": {"type": "array", "items": {"type": "object"}},
            "existing_guidelines": {"type": "array", "items": {"type": "object"}},
        },
    },
    output_schema={
        "type": "object",
        "required": ["recommendation", "reasoning"],
        "properties": {
            "recommendation": {
                "type": "string",
                "enum": ["promote-to-knowledge", "promote-to-guideline", "keep-as-lesson", "archive"],
            },
            "reasoning": {"type": "string"},
            "proposed_knowledge": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
            "proposed_guideline": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "scope": {"type": "string"},
                    "weight": {"type": "string", "enum": ["must", "should", "may"]},
                },
            },
            "duplicate_of": {"type": "string", "description": "ID of existing knowledge/guideline if duplicate"},
        },
    },
    output_format="json",
    system_prompt_template=(
        "Evaluate whether a lesson should be promoted to a knowledge object or guideline.\n\n"
        "- promote-to-knowledge: Lesson captures reusable domain knowledge\n"
        "- promote-to-guideline: Lesson describes a best practice or convention\n"
        "- keep-as-lesson: Lesson is useful but context-specific\n"
        "- archive: Lesson is outdated or superseded\n\n"
        "Check for duplicates in existing knowledge and guidelines."
    ),
    user_prompt_template=(
        "## Lesson\n{lesson_json}\n\n"
        "## Existing Knowledge Titles\n{knowledge_titles}\n\n"
        "## Existing Guidelines\n{guidelines_json}\n\n"
        "Evaluate this lesson."
    ),
    validation_rules=[
        ValidationRule(
            id="valid-recommendation",
            description="Recommendation must be a valid enum value",
            check_fn=lambda o: o.get("recommendation") in (
                "promote-to-knowledge", "promote-to-guideline",
                "keep-as-lesson", "archive",
            ),
        ),
        ValidationRule(
            id="has-proposal-if-promoted",
            description="If promoting, must include proposed object",
            check_fn=lambda o: (
                o.get("recommendation") not in ("promote-to-knowledge", "promote-to-guideline")
                or (
                    (o.get("recommendation") == "promote-to-knowledge" and o.get("proposed_knowledge"))
                    or (o.get("recommendation") == "promote-to-guideline" and o.get("proposed_guideline"))
                )
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=2),
    min_context_window=8_000,
    requires_json_mode=True,
)

"""Knowledge management contracts — suggestion, extraction, impact assessment."""

from core.llm.contract import LLMContract, RetryStrategy, ValidationRule


KnowledgeSuggestionContract = LLMContract(
    id="knowledge-suggest-v1",
    name="Suggest Knowledge for Entity",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["entity_type", "entity", "available_knowledge"],
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": ["objective", "idea", "task"],
                "description": "Type of entity to find knowledge for",
            },
            "entity": {"type": "object", "description": "Full entity data"},
            "available_knowledge": {
                "type": "array",
                "items": {"type": "object"},
                "description": "All knowledge objects to consider",
            },
            "existing_links": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Already-linked knowledge IDs to exclude",
            },
        },
    },
    output_schema={
        "type": "object",
        "required": ["suggestions"],
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["knowledge_id", "relevance_score", "relation", "reasoning"],
                    "properties": {
                        "knowledge_id": {"type": "string", "description": "K-NNN format"},
                        "relevance_score": {"type": "number", "description": "0-1 relevance"},
                        "relation": {
                            "type": "string",
                            "enum": ["required", "context", "reference"],
                        },
                        "reasoning": {"type": "string"},
                    },
                },
            },
        },
    },
    output_format="json",
    context_assembly="minimal",
    system_prompt_template=(
        "You are evaluating which knowledge objects are relevant to a given entity. "
        "Score relevance 0-1. Suggest relation type. Explain reasoning briefly.\n\n"
        "Relation types:\n"
        "- required: Entity cannot be completed without this knowledge\n"
        "- context: Knowledge provides useful background\n"
        "- reference: Knowledge is tangentially related\n\n"
        "Only suggest knowledge with relevance_score >= 0.3. "
        "Do not suggest already-linked knowledge."
    ),
    user_prompt_template=(
        "## Entity ({entity_type})\n{entity_json}\n\n"
        "## Available Knowledge\n{knowledge_json}\n\n"
        "## Already Linked\n{existing_links}\n\n"
        "Suggest relevant knowledge objects."
    ),
    validation_rules=[
        ValidationRule(
            id="valid-scores",
            description="All relevance scores must be between 0 and 1",
            check_fn=lambda o: all(
                0 <= s.get("relevance_score", -1) <= 1
                for s in o.get("suggestions", [])
            ),
        ),
        ValidationRule(
            id="no-duplicates",
            description="No duplicate knowledge IDs in suggestions",
            check_fn=lambda o: len(set(
                s.get("knowledge_id", "") for s in o.get("suggestions", [])
            )) == len(o.get("suggestions", [])),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=2, retry_on=["schema_error", "parse_error"]),
    min_context_window=16_000,
    requires_json_mode=True,
)


KnowledgeExtractionContract = LLMContract(
    id="knowledge-extract-v1",
    name="Extract Knowledge from Content",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["content", "source_type"],
        "properties": {
            "content": {"type": "string", "description": "Content to extract knowledge from"},
            "source_type": {
                "type": "string",
                "enum": ["lesson", "decision", "task_output", "document"],
            },
            "existing_knowledge": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Existing knowledge to avoid duplicates",
            },
        },
    },
    output_schema={
        "type": "object",
        "required": ["extracted"],
        "properties": {
            "extracted": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title", "content", "category", "tags"],
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "domain-rules", "api-reference", "architecture",
                                "business-context", "technical-context", "code-patterns",
                                "integration", "infrastructure",
                            ],
                        },
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "description": "0-1"},
                    },
                },
            },
        },
    },
    output_format="json",
    system_prompt_template=(
        "Extract reusable knowledge from the given content. "
        "Each piece of knowledge should be self-contained, actionable, and categorized.\n\n"
        "Categories: domain-rules, api-reference, architecture, business-context, "
        "technical-context, code-patterns, integration, infrastructure.\n\n"
        "Only extract knowledge with confidence >= 0.5. Avoid duplicating existing knowledge."
    ),
    user_prompt_template=(
        "## Source ({source_type})\n{content}\n\n"
        "## Existing Knowledge Titles\n{existing_titles}\n\n"
        "Extract new knowledge objects."
    ),
    validation_rules=[
        ValidationRule(
            id="has-extractions",
            description="Must extract at least one knowledge object",
            check_fn=lambda o: len(o.get("extracted", [])) > 0,
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=1),
    min_context_window=16_000,
    requires_json_mode=True,
)


ImpactAssessmentContract = LLMContract(
    id="impact-assess-v1",
    name="Assess Impact of Knowledge Change",
    version="1.0.0",
    input_schema={
        "type": "object",
        "required": ["knowledge", "previous_version", "current_version", "linked_entities"],
        "properties": {
            "knowledge": {"type": "object", "description": "The changed knowledge object"},
            "previous_version": {"type": "string", "description": "Previous content"},
            "current_version": {"type": "string", "description": "Current content"},
            "linked_entities": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Linked entities with their details",
            },
        },
    },
    output_schema={
        "type": "object",
        "required": ["impact_assessment", "summary"],
        "properties": {
            "impact_assessment": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["entity_type", "entity_id", "impact_level", "description", "recommended_action"],
                    "properties": {
                        "entity_type": {"type": "string"},
                        "entity_id": {"type": "string"},
                        "impact_level": {
                            "type": "string",
                            "enum": ["none", "low", "medium", "high"],
                        },
                        "description": {"type": "string"},
                        "recommended_action": {
                            "type": "string",
                            "enum": ["none", "review", "update", "rework"],
                        },
                    },
                },
            },
            "summary": {"type": "string", "description": "Overall impact summary"},
        },
    },
    output_format="json",
    system_prompt_template=(
        "You are assessing the impact of a knowledge change on linked entities.\n\n"
        "For each linked entity, determine:\n"
        "- impact_level: none, low, medium, high\n"
        "- recommended_action: none, review, update, rework\n\n"
        "Be conservative: when in doubt, recommend review."
    ),
    user_prompt_template=(
        "## Knowledge: {knowledge_title}\n\n"
        "### Previous Content\n{previous_version}\n\n"
        "### Current Content\n{current_version}\n\n"
        "### Linked Entities\n{linked_entities_json}\n\n"
        "Assess the impact of this change on each linked entity."
    ),
    validation_rules=[
        ValidationRule(
            id="all-entities-assessed",
            description="Every linked entity must be assessed",
        ),
        ValidationRule(
            id="valid-impact-levels",
            description="Impact levels must be valid enum values",
            check_fn=lambda o: all(
                a.get("impact_level") in ("none", "low", "medium", "high")
                for a in o.get("impact_assessment", [])
            ),
        ),
        ValidationRule(
            id="valid-actions",
            description="Recommended actions must be valid enum values",
            check_fn=lambda o: all(
                a.get("recommended_action") in ("none", "review", "update", "rework")
                for a in o.get("impact_assessment", [])
            ),
        ),
    ],
    retry_strategy=RetryStrategy(max_retries=2),
    min_context_window=32_000,
    requires_json_mode=True,
)

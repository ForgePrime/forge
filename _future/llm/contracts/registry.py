"""Contract registry — all 12 built-in contracts from Section 6.3."""

from _future.llm.contract import ContractRegistry, LLMContract

from _future.llm.contracts.task_execution import (
    TaskExecutionContract,
    QuickTaskContract,
)
from _future.llm.contracts.knowledge import (
    KnowledgeSuggestionContract,
    KnowledgeExtractionContract,
    ImpactAssessmentContract,
)
from _future.llm.contracts.planning import (
    PlanDecompositionContract,
    ACSuggestionContract,
    GuidelineMatchContract,
)
from _future.llm.contracts.analysis import (
    RiskAssessmentContract,
    LessonPromotionContract,
)
from _future.llm.contracts.review import (
    CodeReviewContract,
    VerificationContract,
)

# Map of contract_id -> LLMContract instance
CONTRACTS: dict[str, LLMContract] = {
    # Task execution
    "task-execution-v1": TaskExecutionContract,
    "task-quick-v1": QuickTaskContract,

    # Knowledge management
    "knowledge-suggest-v1": KnowledgeSuggestionContract,
    "knowledge-extract-v1": KnowledgeExtractionContract,
    "impact-assess-v1": ImpactAssessmentContract,

    # Planning
    "plan-decompose-v1": PlanDecompositionContract,
    "ac-suggest-v1": ACSuggestionContract,
    "guideline-match-v1": GuidelineMatchContract,

    # Analysis
    "risk-assess-v1": RiskAssessmentContract,
    "lesson-promote-v1": LessonPromotionContract,

    # Review
    "code-review-v1": CodeReviewContract,
    "verify-v1": VerificationContract,
}


def get_default_registry() -> ContractRegistry:
    """Create a ContractRegistry pre-loaded with all 12 built-in contracts."""
    registry = ContractRegistry()
    for contract in CONTRACTS.values():
        registry.register(contract)
    return registry

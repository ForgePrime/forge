"""
Forge LLM Abstraction Layer.

Provider-agnostic LLM interaction with mandatory contracts.
Every LLM call goes through a Contract — no ad-hoc prompting.

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 6

Submodules:
- provider: LLMProvider Protocol and supporting dataclasses
- contract: LLMContract base class and ContractRegistry (T-004)
- context:  Context Assembly engine (T-008)
"""

from core.llm.provider import (
    CompletionConfig,
    CompletionResult,
    LLMProvider,
    Message,
    ProviderCapabilities,
    ProviderError,
    StreamChunk,
    TokenUsage,
    ToolDefinition,
)

from core.llm.contract import (
    ContractError,
    ContractNotFoundError,
    ContractRegistry,
    ContractValidationError,
    LLMContract,
    RetryStrategy,
    ValidationRule,
    render_contract,
    render_prompt,
    validate_output,
)

from core.llm.context import (
    AssembledContext,
    ContextAssembler,
    Section,
    SectionDef,
    SECTION_DEFS,
    estimate_tokens,
)

__all__ = [
    # Provider
    "CompletionConfig",
    "CompletionResult",
    "LLMProvider",
    "Message",
    "ProviderCapabilities",
    "ProviderError",
    "StreamChunk",
    "TokenUsage",
    "ToolDefinition",
    # Contract
    "ContractError",
    "ContractNotFoundError",
    "ContractRegistry",
    "ContractValidationError",
    "LLMContract",
    "RetryStrategy",
    "ValidationRule",
    "render_contract",
    "render_prompt",
    "validate_output",
    # Context Assembly
    "AssembledContext",
    "ContextAssembler",
    "Section",
    "SectionDef",
    "SECTION_DEFS",
    "estimate_tokens",
]

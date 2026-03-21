"""
Forge LLM Abstraction Layer — FUTURE / NOT CURRENTLY USED.

Moved from core/llm/ to _future/llm/ on 2026-03-21.

This module is NOT used by the active CLI flow (core/pipeline.py).
It was built for platform mode (forge-api/) where Forge runs as an API server
with direct LLM integration (providers, contracts, context assembly).

The active Forge CLI uses Claude Code as the LLM layer — no direct LLM calls.
All context assembly is done by cmd_context() in core/pipeline.py.

Contents:
- provider.py: LLMProvider Protocol, ProviderCapabilities, Message, etc.
- contract.py: LLMContract base class, ContractRegistry
- contracts/: Concrete contracts (planning, task_execution, review, analysis, knowledge)
- providers/: Provider implementations (anthropic, openai, ollama, claude_code)
- context_assembler.py: Token-budgeted context assembly (moved separately)

If reactivating platform mode:
1. Move this back to core/llm/
2. Update imports in forge-api/ (they reference core.llm.*)
3. Sync context_assembler.py with cmd_context() in pipeline.py
4. Restore context.py import in __init__.py

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 6
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

    # Context Assembly (ContextAssembler) moved to _future/context_assembler.py
    # It is not used by the active CLI flow. See _future/ for details.

from core.llm.providers import ProviderRegistry, get_provider

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
    # Context Assembly — moved to _future/context_assembler.py
    # Providers
    "ProviderRegistry",
    "get_provider",
]

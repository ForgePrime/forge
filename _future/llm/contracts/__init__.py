"""
Built-in LLM Contracts — defines all 12 standard contracts from Section 6.3.

Each contract specifies input/output schemas, prompt templates, validation rules,
retry strategies, and provider requirements for a specific type of LLM interaction.
"""

from core.llm.contracts.registry import CONTRACTS, get_default_registry

__all__ = ["CONTRACTS", "get_default_registry"]

"""
LLM Provider Protocol and supporting dataclasses.

Defines the provider-agnostic interface for LLM interaction.
Every LLM provider (Claude, OpenAI, Ollama, etc.) implements the
LLMProvider Protocol. Supporting dataclasses handle messages,
configuration, results, and capability advertisement.

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 6.1

Design decisions:
- Uses dataclasses (not Pydantic) to keep dependencies minimal (stdlib only).
- Protocol with runtime_checkable for structural subtyping — providers don't
  need to inherit, just match the interface.
- Both complete() and stream() are async — sync callers can use asyncio.run().
- ToolDefinition intentionally kept minimal (name, description, parameters
  as JSON Schema dict) — provider adapters translate to provider-specific
  format (e.g., Anthropic tool_use blocks, OpenAI function calling).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Supporting dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """A single message in a conversation.

    Attributes:
        role: One of "system", "user", "assistant", or "tool".
        content: The text content of the message.
        tool_call_id: Optional — set when role="tool" to reference the
            tool invocation this result belongs to.
        name: Optional — tool/function name (used with tool role).
        tool_calls: Optional — set on assistant messages when the LLM
            invoked tools. Each dict has "id", "name", "input" keys.
    """

    role: str       # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict] | None = None


@dataclass
class TokenUsage:
    """Token consumption for a single LLM call.

    Attributes:
        input_tokens: Tokens consumed by the prompt/context.
        output_tokens: Tokens generated in the response.
        total_tokens: Sum of input + output (convenience field).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if self.total_tokens == 0 and (self.input_tokens or self.output_tokens):
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class ToolDefinition:
    """Definition of a tool/function that the LLM can invoke.

    Provider adapters translate this into the provider-specific format
    (e.g., Anthropic tool_use, OpenAI function calling).

    Attributes:
        name: Tool/function name (alphanumeric + underscores).
        description: Human-readable description of what the tool does.
        parameters: JSON Schema dict describing the tool's input parameters.
    """

    name: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass
class CompletionConfig:
    """Configuration for a single LLM completion request.

    Attributes:
        model: Model identifier (e.g., "claude-sonnet-4-20250514", "gpt-4o").
        temperature: Sampling temperature (0.0 = deterministic).
        max_tokens: Maximum tokens to generate in the response.
        response_format: Expected response format — "text" or "json".
        tools: Optional list of tool definitions the LLM may invoke.
        system_prompt: System-level instruction prepended to messages.
        stop_sequences: Optional list of sequences that stop generation.
        metadata: Provider-specific metadata (e.g., forge_session_id for
            session resume). Optional, backward-compatible.
    """

    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096
    response_format: str = "text"   # "text" | "json"
    tools: list[ToolDefinition] | None = None
    system_prompt: str = ""
    stop_sequences: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class CompletionResult:
    """Result of a non-streaming LLM completion.

    Attributes:
        content: The generated text content (text blocks only, no tool_use).
        model: Model identifier that produced this result.
        usage: Token consumption breakdown.
        stop_reason: Why generation stopped — "end_turn", "max_tokens",
            "stop_sequence", "tool_use", etc.
        tool_calls: Structured tool call data when stop_reason="tool_use".
            Each dict has "id", "name", "input" keys.
    """

    content: str = ""
    model: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    stop_reason: str = ""
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class StreamChunk:
    """A single chunk from a streaming LLM response.

    Attributes:
        content: Text content of this chunk (may be empty for metadata chunks).
        is_final: True if this is the last chunk in the stream.
        usage: Token usage — populated only on the final chunk.
    """

    content: str = ""
    is_final: bool = False
    usage: TokenUsage | None = None


@dataclass
class ProviderCapabilities:
    """Advertised capabilities of an LLM provider + model combination.

    Used by the Contract system and Context Assembly engine to:
    - Check if a contract's requirements are met (e.g., needs JSON mode).
    - Size the context window correctly.
    - Select appropriate fallback strategies.

    Attributes:
        provider_name: Provider identifier ("anthropic", "openai", "ollama").
        model_id: Specific model ("claude-sonnet-4-20250514", "gpt-4o", etc.).
        max_context_window: Maximum input tokens the model accepts.
        max_output_tokens: Maximum tokens the model can generate.
        supports_streaming: Whether the provider supports streaming responses.
        supports_tool_use: Whether the model supports tool/function calling.
        supports_json_mode: Whether the model supports structured JSON output.
        supports_vision: Whether the model accepts image inputs.
        supports_thinking: Whether the model supports extended thinking (Claude).
        cost_per_1k_input: Cost in USD per 1,000 input tokens.
        cost_per_1k_output: Cost in USD per 1,000 output tokens.
    """

    provider_name: str = ""
    model_id: str = ""
    max_context_window: int = 0
    max_output_tokens: int = 0
    supports_streaming: bool = False
    supports_tool_use: bool = False
    supports_json_mode: bool = False
    supports_vision: bool = False
    supports_thinking: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Base exception for LLM provider operations.

    Raised when an API call fails due to network issues, authentication
    errors, rate limiting, invalid requests, etc.
    """
    pass


# ---------------------------------------------------------------------------
# LLM Provider Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    """Interface that every LLM provider must implement.

    Providers are structural subtypes — they don't need to inherit from
    this class, just implement the required methods with matching signatures.

    Methods:
        complete: Send messages and get a complete response.
        stream:   Send messages and get a streaming response.
        capabilities: Advertise what this provider/model supports.

    Example usage::

        provider: LLMProvider = AnthropicProvider(api_key="...")
        caps = provider.capabilities()

        config = CompletionConfig(
            model=caps.model_id,
            temperature=0.0,
            max_tokens=4096,
        )

        result = await provider.complete(
            messages=[Message(role="user", content="Hello")],
            config=config,
        )
        print(result.content)
    """

    async def complete(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> CompletionResult:
        """Send messages and return a complete response.

        Args:
            messages: Conversation history (system, user, assistant messages).
            config: Completion configuration (model, temperature, etc.).

        Returns:
            CompletionResult with generated content, usage, and stop reason.

        Raises:
            ProviderError: If the API call fails (network, auth, rate limit).
        """
        ...

    async def stream(
        self,
        messages: list[Message],
        config: CompletionConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Send messages and return a streaming response.

        Args:
            messages: Conversation history.
            config: Completion configuration.

        Yields:
            StreamChunk objects. The last chunk has is_final=True and
            includes token usage data.

        Raises:
            ProviderError: If the API call fails.
        """
        ...

    def capabilities(self) -> ProviderCapabilities:
        """Return the capabilities of this provider/model combination.

        This is a sync method — capabilities are typically static or cached
        and don't require an API call.

        Returns:
            ProviderCapabilities describing what this provider supports.
        """
        ...

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from this provider.

        Returns a list of dicts with at least: id, name.
        Optional fields: context_window, max_output, supports_vision.
        Default implementation returns empty list.
        """
        return []

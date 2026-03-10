"""
LLM Contract system — mandatory contracts for every LLM interaction.

Every LLM call goes through a Contract. No exceptions.
Contracts define input/output schemas, prompt templates, validation rules,
retry strategies, and provider requirements.

This is distinct from core/contracts.py (Forge data contracts for task/decision
validation). This module handles LLM interaction contracts — defining HOW
to communicate with LLM providers.

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 6.2-6.3

Design decisions:
- Dataclasses for contract definitions (consistent with provider.py).
- validate_output uses basic structural validation (stdlib only, no jsonschema).
  Full JSON Schema validation deferred to Phase 2 when jsonschema dependency
  is acceptable.
- render_contract produces Markdown that can be included in LLM system prompts.
- ContractRegistry is a simple dict-based registry with register/get/list.
- ValidationRule.check_fn is Optional[Callable] — None means "structural only".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Supporting dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ValidationRule:
    """A single validation rule for LLM output.

    Attributes:
        id: Rule identifier (e.g., "has-summary", "valid-status").
        description: Human-readable description of what this rule checks.
        check_fn: Optional callable that takes (output: dict) -> bool.
            Returns True if valid, False if violated.
            None means this rule is structural-only (checked via schema).
    """

    id: str
    description: str
    check_fn: Optional[Callable[[dict], bool]] = None


@dataclass
class RetryStrategy:
    """Defines retry behavior when LLM output fails validation.

    Attributes:
        max_retries: Maximum number of retry attempts.
        retry_on: List of error types that trigger retry
            (e.g., "schema_error", "missing_field", "parse_error").
        escalate_on: List of error types that escalate to human review
            instead of retrying (e.g., "semantic_error", "hallucination").
        backoff: Backoff strategy between retries.
    """

    max_retries: int = 2
    retry_on: list[str] = field(default_factory=lambda: ["schema_error", "missing_field"])
    escalate_on: list[str] = field(default_factory=lambda: ["semantic_error", "hallucination"])
    backoff: str = "none"   # "none" | "linear" | "exponential"


@dataclass
class LLMContract:
    """Defines a specific type of LLM interaction.

    Every LLM call must be associated with a contract that specifies:
    - What input data is expected (input_schema)
    - How to compose the prompt (templates)
    - What output format/schema is expected
    - How to validate the output
    - What to do on failure (retry strategy)
    - What provider capabilities are required

    Attributes:
        id: Unique contract identifier (e.g., "task-execution-v1").
        name: Human-readable name.
        version: Semantic version string.
        input_schema: JSON Schema dict for input data validation.
        output_schema: JSON Schema dict for expected output structure.
        output_format: Expected output format — "json", "text", or "markdown".
        context_assembly: Which ContextAssembly rules to use (e.g., "full", "minimal").
        system_prompt_template: Template string for system prompt.
            Uses {placeholder} syntax for variable substitution.
        user_prompt_template: Template string for user prompt.
            Uses {placeholder} syntax for variable substitution.
        validation_rules: List of validation rules applied to output.
        retry_strategy: What to do when output fails validation.
        min_context_window: Minimum context window (tokens) required
            for this contract to work correctly.
        requires_tool_use: Whether this contract needs function calling.
        requires_json_mode: Whether this contract needs JSON output mode.
        fallback_format: Format to use if provider doesn't support
            the primary output mode (e.g., "markdown" when JSON mode
            unavailable).
    """

    id: str
    name: str
    version: str = "1.0.0"

    # Input
    input_schema: dict = field(default_factory=dict)
    context_assembly: str = "full"

    # Prompt templates
    system_prompt_template: str = ""
    user_prompt_template: str = ""

    # Output
    output_schema: dict = field(default_factory=dict)
    output_format: str = "json"     # "json" | "text" | "markdown"

    # Validation
    validation_rules: list[ValidationRule] = field(default_factory=list)
    retry_strategy: RetryStrategy = field(default_factory=RetryStrategy)

    # Provider requirements
    min_context_window: int = 0
    requires_tool_use: bool = False
    requires_json_mode: bool = False
    fallback_format: str = "markdown"


# ---------------------------------------------------------------------------
# Contract Registry
# ---------------------------------------------------------------------------

class ContractRegistry:
    """Registry of available LLM contracts.

    Contracts are registered by ID and can be retrieved for use
    in LLM interactions. The registry enforces unique IDs.

    Usage::

        registry = ContractRegistry()
        registry.register(my_contract)
        contract = registry.get("task-execution-v1")
        all_ids = registry.list()
    """

    def __init__(self) -> None:
        self._contracts: dict[str, LLMContract] = {}

    def register(self, contract: LLMContract) -> None:
        """Register a contract. Overwrites if ID already exists.

        Args:
            contract: The LLMContract to register.
        """
        self._contracts[contract.id] = contract

    def get(self, contract_id: str) -> LLMContract:
        """Retrieve a contract by ID.

        Args:
            contract_id: The contract identifier.

        Returns:
            The registered LLMContract.

        Raises:
            ContractNotFoundError: If no contract with this ID exists.
        """
        if contract_id not in self._contracts:
            raise ContractNotFoundError(
                f"Contract '{contract_id}' not found. "
                f"Available: {', '.join(sorted(self._contracts.keys())) or '(none)'}"
            )
        return self._contracts[contract_id]

    def list(self) -> list[str]:
        """List all registered contract IDs.

        Returns:
            Sorted list of contract ID strings.
        """
        return sorted(self._contracts.keys())

    def __len__(self) -> int:
        return len(self._contracts)

    def __contains__(self, contract_id: str) -> bool:
        return contract_id in self._contracts

    def __repr__(self) -> str:
        return f"ContractRegistry({len(self._contracts)} contracts)"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ContractError(Exception):
    """Base exception for contract operations."""
    pass


class ContractNotFoundError(ContractError):
    """Raised when a contract ID is not found in the registry."""
    pass


class ContractValidationError(ContractError):
    """Raised when output fails contract validation."""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


# ---------------------------------------------------------------------------
# Contract rendering (for LLM context)
# ---------------------------------------------------------------------------

def render_contract(contract: LLMContract) -> str:
    """Render a contract as Markdown for inclusion in LLM prompts.

    Produces a structured Markdown document that tells the LLM:
    - What contract this is (id, name, version)
    - What input data it receives
    - What output format/schema is expected
    - What validation rules apply
    - Example output structure (from output_schema)

    Args:
        contract: The LLMContract to render.

    Returns:
        Markdown string suitable for system/user prompt inclusion.
    """
    lines = []

    # Header
    lines.append(f"## Contract: {contract.name}")
    lines.append(f"**ID**: `{contract.id}` | **Version**: {contract.version}")
    lines.append("")

    # Output format
    lines.append("### Output Requirements")
    lines.append(f"- **Format**: {contract.output_format}")
    if contract.requires_json_mode:
        lines.append("- **JSON mode**: Required")
    if contract.requires_tool_use:
        lines.append("- **Tool use**: Required")
    lines.append("")

    # Output schema
    if contract.output_schema:
        lines.append("### Output Schema")
        lines.append("")
        _render_schema_fields(lines, contract.output_schema)
        lines.append("")

    # Input schema
    if contract.input_schema:
        lines.append("### Input Data Schema")
        lines.append("")
        _render_schema_fields(lines, contract.input_schema)
        lines.append("")

    # Validation rules
    if contract.validation_rules:
        lines.append("### Validation Rules")
        for rule in contract.validation_rules:
            lines.append(f"- **{rule.id}**: {rule.description}")
        lines.append("")

    # Retry info
    if contract.retry_strategy.max_retries > 0:
        rs = contract.retry_strategy
        lines.append("### On Failure")
        lines.append(f"- Retries: up to {rs.max_retries} attempts")
        if rs.retry_on:
            lines.append(f"- Retry on: {', '.join(rs.retry_on)}")
        if rs.escalate_on:
            lines.append(f"- Escalate on: {', '.join(rs.escalate_on)}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_schema_fields(lines: list[str], schema: dict, indent: int = 0) -> None:
    """Render JSON Schema properties as a readable field list.

    Handles basic JSON Schema structure: type, properties, required, items.
    Not a full JSON Schema renderer — covers the common cases for LLM contracts.
    """
    prefix = "  " * indent
    schema_type = schema.get("type", "object")
    required_fields = set(schema.get("required", []))
    properties = schema.get("properties", {})

    if properties:
        lines.append(f"{prefix}| Field | Type | Required | Description |")
        lines.append(f"{prefix}|-------|------|----------|-------------|")
        for name, prop in properties.items():
            ptype = prop.get("type", "string")
            if ptype == "array" and "items" in prop:
                item_type = prop["items"].get("type", "object")
                ptype = f"array[{item_type}]"
            req = "YES" if name in required_fields else "no"
            desc = prop.get("description", "")
            enum_vals = prop.get("enum")
            if enum_vals:
                desc = f"{desc} ({', '.join(str(v) for v in enum_vals)})" if desc else ', '.join(str(v) for v in enum_vals)
            lines.append(f"{prefix}| `{name}` | {ptype} | {req} | {desc} |")

    elif schema_type == "array" and "items" in schema:
        lines.append(f"{prefix}Array of:")
        _render_schema_fields(lines, schema["items"], indent + 1)
    else:
        lines.append(f"{prefix}Type: `{schema_type}`")


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

def validate_output(
    contract: LLMContract,
    output: Any,
) -> tuple[bool, list[str]]:
    """Validate LLM output against a contract's schema and rules.

    Performs two types of validation:
    1. Structural — checks output matches output_schema (type, required fields).
    2. Rule-based — runs each ValidationRule's check_fn (if present).

    This is a basic structural validator using stdlib only.
    Full JSON Schema validation (with jsonschema package) deferred to Phase 2.

    Args:
        contract: The LLMContract defining expected output.
        output: The parsed LLM output to validate.

    Returns:
        Tuple of (is_valid: bool, errors: list[str]).
        Empty errors list means valid.
    """
    errors: list[str] = []

    # Step 1: Structural validation against output_schema
    if contract.output_schema:
        schema_errors = _validate_against_schema(output, contract.output_schema, path="$")
        errors.extend(schema_errors)

    # Step 2: Custom validation rules
    if isinstance(output, dict):
        for rule in contract.validation_rules:
            if rule.check_fn is not None:
                try:
                    if not rule.check_fn(output):
                        errors.append(f"Rule '{rule.id}' failed: {rule.description}")
                except Exception as e:
                    errors.append(f"Rule '{rule.id}' error: {e}")

    return (len(errors) == 0, errors)


def _validate_against_schema(value: Any, schema: dict, path: str) -> list[str]:
    """Basic structural validation of a value against a JSON Schema dict.

    Checks: type, required, properties (recursive), items (for arrays).
    Does NOT support: allOf, anyOf, oneOf, $ref, pattern, min/max, etc.
    Those are deferred to Phase 2 with the jsonschema package.
    """
    errors: list[str] = []
    expected_type = schema.get("type")

    # Type check
    if expected_type:
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        py_type = type_map.get(expected_type)
        if py_type and not isinstance(value, py_type):
            errors.append(
                f"{path}: expected type '{expected_type}', "
                f"got '{type(value).__name__}'"
            )
            return errors  # Stop here — further checks would be misleading

    # Object properties
    if expected_type == "object" and isinstance(value, dict):
        required_fields = set(schema.get("required", []))
        properties = schema.get("properties", {})

        # Required field check
        for req_field in required_fields:
            if req_field not in value:
                errors.append(f"{path}: missing required field '{req_field}'")

        # Recursive property validation
        for prop_name, prop_schema in properties.items():
            if prop_name in value:
                sub_errors = _validate_against_schema(
                    value[prop_name], prop_schema, f"{path}.{prop_name}"
                )
                errors.extend(sub_errors)

    # Array items
    if expected_type == "array" and isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(value):
                sub_errors = _validate_against_schema(
                    item, items_schema, f"{path}[{i}]"
                )
                errors.extend(sub_errors)

    # Enum check
    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        errors.append(
            f"{path}: value '{value}' not in allowed values: "
            f"{', '.join(str(v) for v in enum_values)}"
        )

    return errors


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_prompt(template: str, variables: dict[str, Any]) -> str:
    """Render a prompt template by substituting {placeholder} variables.

    Uses simple str.format_map() — no Jinja2 dependency.
    Missing variables are left as-is (no KeyError).

    Args:
        template: Template string with {placeholder} syntax.
        variables: Dict of variable name -> value.

    Returns:
        Rendered prompt string.
    """
    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return template.format_map(SafeDict(variables))

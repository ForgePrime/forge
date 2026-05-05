"""ToolCatalog — Phase L3 Stage L3.2.

Tool registry + authority-gated dispatch. Composes:
- C.2 SideEffectRegistry (just shipped — provides @side_effect tagging
  used to verify mutating tools declare their side effects).
- A.5 idempotency (just shipped — mutating tools must accept
  idempotency_key per FORMAL P1).
- E.3 AutonomyState concept (per FORMAL P4 — a tool's
  authority_level must be <= execution.autonomy_state.max_authority).

Per PLAN_LLM_ORCHESTRATION L3.2 + ADR-027 mapping:
- 5 authority levels matching AIOS A6 5-category boundary typing:
  read_only, idempotent_write, side_effecting_write,
  irreversible_write, external_call.
- Per-tool max_invocations_per_execution cap (per-Execution counter).
- Single dispatch() path; authority + idempotency + decorator checks
  happen inside.

Determinism (P6): registration is order-independent (dict-based).
Dispatch decisions are deterministic given the same inputs (autonomy
state, idempotency key, invocation count). The actual tool function
may have side effects — that's the point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class AuthorityLevel(str, Enum):
    """5 levels per ADR-027 cross-mapping with AIOS A6 boundary typing."""

    READ_ONLY = "read_only"
    IDEMPOTENT_WRITE = "idempotent_write"
    SIDE_EFFECTING_WRITE = "side_effecting_write"
    IRREVERSIBLE_WRITE = "irreversible_write"
    EXTERNAL_CALL = "external_call"


# Numeric ordering for authority comparison: lower = safer.
_AUTHORITY_ORDER: dict[AuthorityLevel, int] = {
    AuthorityLevel.READ_ONLY: 1,
    AuthorityLevel.IDEMPOTENT_WRITE: 2,
    AuthorityLevel.SIDE_EFFECTING_WRITE: 3,
    AuthorityLevel.IRREVERSIBLE_WRITE: 4,
    AuthorityLevel.EXTERNAL_CALL: 5,
}


def authority_le(actual: AuthorityLevel, ceiling: AuthorityLevel) -> bool:
    """Returns True iff `actual` does NOT exceed `ceiling`.

    Comparable to `actual <= ceiling` but explicit per-level numeric
    mapping rather than string ordering (which would be alphabetical).
    """
    return _AUTHORITY_ORDER[actual] <= _AUTHORITY_ORDER[ceiling]


@dataclass(frozen=True)
class Tool:
    """Tool spec. Frozen — registration creates this once.

    Per PLAN A_{L3.2}:
    - JSON Schema is the canonical input-shape contract.
    - authority_level constrains who can dispatch this.
    - requires_idempotency_key + requires_side_effect_decorator are
      registration-time guards (verified on register, not dispatch).
    - max_invocations_per_execution = None means uncapped.
    """

    name: str
    description: str
    json_schema: dict
    authority_level: AuthorityLevel
    requires_idempotency_key: bool = False
    requires_side_effect_decorator: bool = False
    fn: Callable[..., Any] | None = None
    max_invocations_per_execution: int | None = None


@dataclass
class ToolCall:
    """A request to dispatch a Tool."""

    tool_name: str
    args: dict
    idempotency_key: str | None = None
    execution_id: int = 0
    autonomy_max_authority: AuthorityLevel = AuthorityLevel.READ_ONLY


@dataclass(frozen=True)
class DispatchVerdict:
    """Result of a Tool dispatch attempt — pass/reject + reason.

    The actual tool result (when passed=True) lives in `result`.
    Rejection populates only `reason`.
    """

    passed: bool
    rule_code: str
    reason: str | None = None
    result: Any = None


class ToolCatalog:
    """In-process tool registry + dispatch.

    Mutable during registration; treat as frozen during dispatch.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._invocation_counts: dict[tuple[int, str], int] = {}

    # --- Registration ------------------------------------------------

    def register(self, tool: Tool, *, side_effect_qualnames: set[str] | None = None) -> None:
        """Register a Tool.

        Validates:
        1. Name uniqueness (raises ValueError on duplicate).
        2. JSON Schema present (non-empty dict).
        3. If requires_side_effect_decorator: tool.fn's qualname must
           be in `side_effect_qualnames` (caller's snapshot of
           SideEffectRegistry contents). Else ValueError.
        4. If requires_idempotency_key + tool.fn is None: warning-level
           (registration may proceed since dispatch will catch).

        side_effect_qualnames argument lets callers inject the
        registry contents to avoid circular imports between this module
        and SideEffectRegistry. Production usage:
            from app.validation.side_effect_registry import REGISTRY
            catalog.register(tool, side_effect_qualnames=REGISTRY.all_qualnames())
        """
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool registration: {tool.name!r}")
        if not tool.json_schema:
            raise ValueError(
                f"tool {tool.name!r} requires non-empty json_schema"
            )
        if tool.requires_side_effect_decorator:
            if tool.fn is None:
                raise ValueError(
                    f"tool {tool.name!r} requires_side_effect_decorator=True "
                    f"but tool.fn is None — cannot verify @side_effect tag"
                )
            qualname = f"{tool.fn.__module__}.{tool.fn.__qualname__}"
            registry = side_effect_qualnames or set()
            if qualname not in registry:
                raise ValueError(
                    f"tool {tool.name!r} requires_side_effect_decorator=True "
                    f"but {qualname!r} is not in SideEffectRegistry; tag the "
                    f"function with @side_effect(...) before registering"
                )
        self._tools[tool.name] = tool

    def lookup(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    # --- Dispatch ---------------------------------------------------

    def dispatch(self, call: ToolCall) -> DispatchVerdict:
        """Authority-gated dispatch.

        Sequence (each step rejects on failure):
        1. Tool exists.
        2. Mutating tool requires idempotency_key.
        3. tool.authority_level <= call.autonomy_max_authority.
        4. Per-execution invocation cap not exceeded.
        5. Tool fn is callable (not None).
        6. Invoke tool.fn(**call.args) and return result.

        Tool fn exceptions propagate as DispatchVerdict(passed=False,
        rule_code='tool_raised_exception'). Caller decides whether to
        retry via L3.5 FailureRecovery.
        """
        # 1. Tool lookup
        tool = self._tools.get(call.tool_name)
        if tool is None:
            return DispatchVerdict(
                passed=False,
                rule_code="unknown_tool",
                reason=f"no tool registered with name={call.tool_name!r}",
            )

        # 2. Idempotency-key guard (mutating tools)
        if tool.requires_idempotency_key and not call.idempotency_key:
            return DispatchVerdict(
                passed=False,
                rule_code="missing_idempotency_key",
                reason=(
                    f"tool {tool.name!r} requires idempotency_key but call "
                    f"omitted it; mutating tools must thread P1 idempotency"
                ),
            )

        # 3. Authority gate
        if not authority_le(tool.authority_level, call.autonomy_max_authority):
            return DispatchVerdict(
                passed=False,
                rule_code="tool_authority_exceeds_autonomy",
                reason=(
                    f"tool {tool.name!r} authority={tool.authority_level.value} "
                    f"exceeds autonomy ceiling "
                    f"max_authority={call.autonomy_max_authority.value}"
                ),
            )

        # 4. Per-execution invocation cap
        if tool.max_invocations_per_execution is not None:
            count_key = (call.execution_id, tool.name)
            current = self._invocation_counts.get(count_key, 0)
            if current >= tool.max_invocations_per_execution:
                return DispatchVerdict(
                    passed=False,
                    rule_code="cap_exceeded",
                    reason=(
                        f"tool {tool.name!r} invoked {current} times in "
                        f"execution_id={call.execution_id}; cap is "
                        f"{tool.max_invocations_per_execution}"
                    ),
                )
            self._invocation_counts[count_key] = current + 1

        # 5. Function callable check
        if tool.fn is None:
            return DispatchVerdict(
                passed=False,
                rule_code="tool_not_callable",
                reason=f"tool {tool.name!r} has no fn registered",
            )

        # 6. Invoke
        try:
            result = tool.fn(**call.args)
        except Exception as e:
            return DispatchVerdict(
                passed=False,
                rule_code="tool_raised_exception",
                reason=f"{type(e).__name__}: {e}",
            )

        return DispatchVerdict(
            passed=True,
            rule_code="dispatched",
            result=result,
        )

    # --- Diagnostics ----------------------------------------------

    def invocation_count(self, execution_id: int, tool_name: str) -> int:
        return self._invocation_counts.get((execution_id, tool_name), 0)

    def reset_invocation_counts(self) -> None:
        """Test helper. Production code MUST NOT call this."""
        self._invocation_counts.clear()

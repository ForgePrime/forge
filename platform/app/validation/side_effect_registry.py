"""SideEffectRegistry — Phase C Stage C.2.

Decorator-based registry of side-effecting functions. Tagged functions
declare WHAT side effect they perform (DB write, audit log, external
API, metrics, queue publish). C.3 ImpactClosure consumes this registry
+ C.1 ImportGraph + task_dependencies to compute the full
`Impact(Δ) = Closure(dependencies)` per FORMAL P3.

Per PLAN_QUALITY_ASSURANCE C.2 A_{C.2}:
- kind ∈ {db_write, audit_log, external_api, metrics, queue_publish}
- ≥20 functions to tag in production code (separate work — this commit
  ships the infrastructure; tagging existing app/services/*.py
  functions is mechanical follow-up).

Determinism (P6): the registry is a process-level dict populated at
import time. Same imports -> same registry contents. callers_in_path
queries are pure functions over the registry + ImportGraph.

Why @side_effect not just ImportGraph alone:
- ImportGraph catches static-import dependencies but NOT which
  functions in a module actually mutate state.
- A module can import many things and only one function is
  side-effecting; ImpactClosure needs the function-level granularity.
- Dynamic dispatch (getattr, runtime imports) is invisible to AST
  analysis but visible to @side_effect decoration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar


class SideEffectKind(str, Enum):
    """Closed enum per PLAN A_{C.2}. Extension via ADR-XXX (future)."""

    DB_WRITE = "db_write"
    AUDIT_LOG = "audit_log"
    EXTERNAL_API = "external_api"
    METRICS = "metrics"
    QUEUE_PUBLISH = "queue_publish"


@dataclass(frozen=True)
class TaggedFunction:
    """Registry entry for a side-effecting function.

    Captured at decoration time; immutable thereafter.
    """

    qualified_name: str  # e.g. 'app.services.audit_log.add'
    kind: SideEffectKind
    module: str  # e.g. 'app.services.audit_log'
    callable_name: str  # e.g. 'add'


@dataclass
class SideEffectRegistry:
    """Process-level registry of @side_effect-tagged functions.

    Mutable only via register() (which decorator calls). Treat as
    frozen by external readers.
    """

    by_qualname: dict[str, TaggedFunction] = field(default_factory=dict)
    by_kind: dict[SideEffectKind, set[str]] = field(default_factory=dict)
    by_module: dict[str, set[str]] = field(default_factory=dict)

    def register(self, tagged: TaggedFunction) -> None:
        """Idempotent: re-registering the same qualname is a no-op."""
        existing = self.by_qualname.get(tagged.qualified_name)
        if existing is not None:
            if existing == tagged:
                return  # idempotent: same registration
            raise ValueError(
                f"side-effect re-registration with different attributes: "
                f"{tagged.qualified_name} was {existing!r}, now {tagged!r}"
            )
        self.by_qualname[tagged.qualified_name] = tagged
        self.by_kind.setdefault(tagged.kind, set()).add(tagged.qualified_name)
        self.by_module.setdefault(tagged.module, set()).add(tagged.qualified_name)

    def all_qualnames(self) -> set[str]:
        return set(self.by_qualname.keys())

    def all_modules_with_side_effects(self) -> set[str]:
        return set(self.by_module.keys())

    def kinds_for(self, qualname: str) -> SideEffectKind | None:
        entry = self.by_qualname.get(qualname)
        return entry.kind if entry else None

    def qualnames_with_kind(self, kind: SideEffectKind) -> set[str]:
        return set(self.by_kind.get(kind, set()))

    def qualnames_in_module(self, module: str) -> set[str]:
        return set(self.by_module.get(module, set()))

    def callers_in_path(self, modules: set[str], import_graph) -> set[str]:
        """Return tagged functions reachable from any of `modules` through imports.

        Uses the C.1 ImportGraph (passed in to avoid circular import) to
        compute the forward closure of `modules`, then returns all tagged
        qualnames in any module in that closure.

        Args:
            modules: starting set of module names (e.g. modules touched
                by a Change).
            import_graph: an ImportGraph instance from C.1.

        Returns:
            Set of fully-qualified function names that are tagged with
            @side_effect AND reside in any module reachable from
            `modules` via import edges.
        """
        # Forward-closure: every module imported (transitively) by anything in `modules`.
        closure: set[str] = set(modules)
        for m in list(modules):
            closure.update(import_graph.forward_deps(m))
        # Also include the input modules' own side-effect tags.
        out: set[str] = set()
        for m in closure:
            out.update(self.by_module.get(m, set()))
        return out


# Module-level singleton — analogous to GateRegistry pattern.
REGISTRY = SideEffectRegistry()


F = TypeVar("F", bound=Callable[..., object])


def side_effect(kind: SideEffectKind | str) -> Callable[[F], F]:
    """Decorator: tag a function as side-effecting in the registry.

    Usage:
        from app.validation.side_effect_registry import side_effect, SideEffectKind

        @side_effect(SideEffectKind.DB_WRITE)
        def insert_user(...):
            ...

        # String form also accepted:
        @side_effect("audit_log")
        def log_event(...):
            ...

    The decorator captures the function's __module__ and __qualname__
    at decoration time and registers in the module-level REGISTRY.
    Idempotent on re-import (decorator runs again -> same registration).

    Returns the function unchanged at runtime — tagging has no behavioral
    side effect on the wrapped function. The registry is a STATIC
    declaration; runtime calls are not intercepted.
    """
    # Normalize string -> enum
    if isinstance(kind, str):
        kind_enum = SideEffectKind(kind)
    else:
        kind_enum = kind

    def _decorator(fn: F) -> F:
        module = getattr(fn, "__module__", "<unknown_module>")
        callable_name = getattr(fn, "__qualname__", getattr(fn, "__name__", "<unknown>"))
        qualified_name = f"{module}.{callable_name}"
        tagged = TaggedFunction(
            qualified_name=qualified_name,
            kind=kind_enum,
            module=module,
            callable_name=callable_name,
        )
        REGISTRY.register(tagged)
        return fn

    return _decorator


def reset_registry_for_tests() -> None:
    """Test-helper: clears REGISTRY in-place. Production code MUST NOT call this.

    Used by isolation-required tests to start with a clean registry.
    Normal tests that just check registration of fresh functions don't
    need this.
    """
    REGISTRY.by_qualname.clear()
    REGISTRY.by_kind.clear()
    REGISTRY.by_module.clear()

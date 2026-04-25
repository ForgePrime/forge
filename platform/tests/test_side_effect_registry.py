"""Tests for SideEffectRegistry — Phase C Stage C.2.

Pure-Python tests of the @side_effect decorator + registry.
Uses reset_registry_for_tests() for isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.validation.import_graph import build as build_graph
from app.validation.side_effect_registry import (
    REGISTRY,
    SideEffectKind,
    TaggedFunction,
    reset_registry_for_tests,
    side_effect,
)


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Each test starts with empty REGISTRY; restored from snapshot after."""
    snapshot = {
        "by_qualname": dict(REGISTRY.by_qualname),
        "by_kind": {k: set(v) for k, v in REGISTRY.by_kind.items()},
        "by_module": {k: set(v) for k, v in REGISTRY.by_module.items()},
    }
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()
    REGISTRY.by_qualname.update(snapshot["by_qualname"])
    REGISTRY.by_kind.update(snapshot["by_kind"])
    REGISTRY.by_module.update(snapshot["by_module"])


# --- Decorator + registration ---------------------------------------------


def test_decorator_registers_function():
    @side_effect(SideEffectKind.DB_WRITE)
    def my_db_write_fn(x: int) -> int:
        return x

    qualnames = REGISTRY.all_qualnames()
    assert any("my_db_write_fn" in q for q in qualnames)


def test_decorator_returns_function_unchanged():
    """Tagged function still callable with original behaviour."""
    @side_effect(SideEffectKind.DB_WRITE)
    def double(x: int) -> int:
        return x * 2

    # Original behaviour preserved
    assert double(5) == 10


def test_decorator_string_form_accepted():
    @side_effect("audit_log")
    def log_event(msg: str) -> None:
        pass

    qualnames = REGISTRY.qualnames_with_kind(SideEffectKind.AUDIT_LOG)
    assert any("log_event" in q for q in qualnames)


def test_decorator_invalid_kind_string_raises():
    with pytest.raises(ValueError):
        @side_effect("not_a_real_kind")  # type: ignore[arg-type]
        def f():
            pass


def test_decorator_idempotent_on_reapply():
    """Registering the same function twice with same kind is a no-op (no error)."""
    def fn():
        pass

    decorated_once = side_effect(SideEffectKind.DB_WRITE)(fn)
    decorated_twice = side_effect(SideEffectKind.DB_WRITE)(decorated_once)
    # No exception; registry has 1 entry for this function
    assert decorated_twice is decorated_once  # decorator returns fn unchanged


def test_decorator_re_register_with_different_kind_raises():
    """Re-registering with a different kind is an error (catches typo bugs)."""
    def fn():
        pass
    side_effect(SideEffectKind.DB_WRITE)(fn)
    with pytest.raises(ValueError, match="re-registration"):
        side_effect(SideEffectKind.AUDIT_LOG)(fn)


# --- Registry queries ----------------------------------------------------


def test_all_qualnames_collects_registrations():
    @side_effect(SideEffectKind.DB_WRITE)
    def a():
        pass
    @side_effect(SideEffectKind.AUDIT_LOG)
    def b():
        pass
    qualnames = REGISTRY.all_qualnames()
    assert len(qualnames) == 2


def test_qualnames_with_kind_filters():
    @side_effect(SideEffectKind.DB_WRITE)
    def writer():
        pass
    @side_effect(SideEffectKind.METRICS)
    def metrics_fn():
        pass

    db_writes = REGISTRY.qualnames_with_kind(SideEffectKind.DB_WRITE)
    metrics = REGISTRY.qualnames_with_kind(SideEffectKind.METRICS)
    assert any("writer" in q for q in db_writes)
    assert not any("metrics_fn" in q for q in db_writes)
    assert any("metrics_fn" in q for q in metrics)


def test_kinds_for_existing():
    @side_effect(SideEffectKind.EXTERNAL_API)
    def fetch_remote():
        pass

    qualname = next(q for q in REGISTRY.all_qualnames() if "fetch_remote" in q)
    assert REGISTRY.kinds_for(qualname) == SideEffectKind.EXTERNAL_API


def test_kinds_for_missing_returns_none():
    assert REGISTRY.kinds_for("nonexistent.function") is None


def test_qualnames_in_module_groups_by_module():
    @side_effect(SideEffectKind.DB_WRITE)
    def f1():
        pass
    @side_effect(SideEffectKind.AUDIT_LOG)
    def f2():
        pass
    # Both decorated in this test module
    module = f1.__module__
    in_module = REGISTRY.qualnames_in_module(module)
    assert len(in_module) == 2


def test_all_modules_with_side_effects():
    @side_effect(SideEffectKind.DB_WRITE)
    def f():
        pass
    modules = REGISTRY.all_modules_with_side_effects()
    assert f.__module__ in modules


# --- TaggedFunction is frozen --------------------------------------------


def test_tagged_function_is_frozen():
    tf = TaggedFunction(
        qualified_name="x.y", kind=SideEffectKind.DB_WRITE,
        module="x", callable_name="y",
    )
    try:
        tf.kind = SideEffectKind.AUDIT_LOG  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("TaggedFunction should be frozen")


# --- callers_in_path integration with C.1 ImportGraph -------------------


def test_callers_in_path_uses_import_graph(tmp_path: Path):
    """Synthetic source tree: a.py imports b.py; b has @side_effect.
    callers_in_path({app.a}) should include the side-effect from app.b."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from app import b\n")
    # b.py just defines a regular function — we'll tag it manually
    (pkg / "b.py").write_text("def write(): pass\n")

    graph = build_graph(pkg, package_prefix="app")

    # Manually register a tagged function that 'lives' in app.b.
    REGISTRY.register(TaggedFunction(
        qualified_name="app.b.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.b",
        callable_name="write",
    ))

    callers = REGISTRY.callers_in_path({"app.a"}, graph)
    assert "app.b.write" in callers


def test_callers_in_path_transitive(tmp_path: Path):
    """a -> b -> c; c has @side_effect. Starting from a finds it."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from app import b\n")
    (pkg / "b.py").write_text("from app import c\n")
    (pkg / "c.py").write_text("def write(): pass\n")

    graph = build_graph(pkg, package_prefix="app")
    REGISTRY.register(TaggedFunction(
        qualified_name="app.c.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.c",
        callable_name="write",
    ))
    callers = REGISTRY.callers_in_path({"app.a"}, graph)
    assert "app.c.write" in callers


def test_callers_in_path_empty_when_no_path(tmp_path: Path):
    """Module with no import edge to a side-effecting module returns empty."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("import os\n")  # no app-internal imports
    (pkg / "b.py").write_text("def write(): pass\n")

    graph = build_graph(pkg, package_prefix="app")
    REGISTRY.register(TaggedFunction(
        qualified_name="app.b.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.b",
        callable_name="write",
    ))
    callers = REGISTRY.callers_in_path({"app.a"}, graph)
    assert callers == set()


def test_callers_in_path_includes_self_module_side_effects(tmp_path: Path):
    """If the input module itself has tagged functions, they're included."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("def write(): pass\n")

    graph = build_graph(pkg, package_prefix="app")
    REGISTRY.register(TaggedFunction(
        qualified_name="app.a.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.a",
        callable_name="write",
    ))
    callers = REGISTRY.callers_in_path({"app.a"}, graph)
    assert "app.a.write" in callers


# --- All 5 SideEffectKind values are valid -------------------------------


def test_all_side_effect_kinds_decorate_successfully():
    """Coverage: every defined SideEffectKind enum value works as decorator."""
    for kind in SideEffectKind:
        # Different function per iteration so each is a fresh registration
        def make_fn(k):
            def fn():
                pass
            fn.__name__ = f"test_kind_{k.value}"
            fn.__qualname__ = f"test_kind_{k.value}"
            return fn
        side_effect(kind)(make_fn(kind))

    # All 5 kinds present in registry
    for kind in SideEffectKind:
        assert len(REGISTRY.qualnames_with_kind(kind)) >= 1


# --- Determinism (P6) ---------------------------------------------------


def test_registry_state_is_deterministic_per_decoration_order():
    """Registering same set of functions in same order -> same registry state."""
    def fn_a(): pass
    def fn_b(): pass

    side_effect(SideEffectKind.DB_WRITE)(fn_a)
    side_effect(SideEffectKind.AUDIT_LOG)(fn_b)
    snapshot1_qualnames = sorted(REGISTRY.all_qualnames())

    reset_registry_for_tests()

    def fn_a2(): pass
    fn_a2.__name__ = fn_a.__name__
    fn_a2.__qualname__ = fn_a.__qualname__
    fn_a2.__module__ = fn_a.__module__
    def fn_b2(): pass
    fn_b2.__name__ = fn_b.__name__
    fn_b2.__qualname__ = fn_b.__qualname__
    fn_b2.__module__ = fn_b.__module__

    side_effect(SideEffectKind.DB_WRITE)(fn_a2)
    side_effect(SideEffectKind.AUDIT_LOG)(fn_b2)
    snapshot2_qualnames = sorted(REGISTRY.all_qualnames())

    assert snapshot1_qualnames == snapshot2_qualnames

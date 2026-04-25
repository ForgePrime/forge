"""Tests for ImpactClosure — Phase C Stage C.3.

Compose C.1 ImportGraph + C.2 SideEffectRegistry into a full
impact-closure computation. Pure-Python tests using synthetic source
trees.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.validation.impact_closure import (
    CoverageVerdict,
    ImpactClosureResult,
    compute_impact_closure,
    verify_change_coverage,
)
from app.validation.import_graph import build as build_graph
from app.validation.side_effect_registry import (
    REGISTRY,
    SideEffectKind,
    TaggedFunction,
    reset_registry_for_tests,
)


@pytest.fixture(autouse=True)
def _isolate_registry():
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


def _build_synthetic_tree(tmp_path: Path, files: dict[str, str]):
    """Helper: write files into tmp_path/app/, return (graph, app_root)."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for rel_path, content in files.items():
        full = pkg / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    graph = build_graph(pkg, package_prefix="app")
    return graph, pkg


# --- compute_impact_closure ----------------------------------------------


def test_empty_change_returns_empty_closure(tmp_path: Path):
    graph, _ = _build_synthetic_tree(tmp_path, {})
    result = compute_impact_closure(
        change_files=set(),
        change_modules=set(),
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    assert result.all_modules == frozenset()
    assert result.side_effect_qualnames == frozenset()


def test_single_module_change_with_no_imports(tmp_path: Path):
    """app.a doesn't import anything from the package -> closure = {app.a}."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "import os\n",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    assert "app.a" in result.all_modules
    assert result.side_effect_qualnames == frozenset()


def test_change_with_static_import_chain(tmp_path: Path):
    """app.a -> app.b -> app.c. Change to app.a includes b + c in closure."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "from app import b\n",
        "b.py": "from app import c\n",
        "c.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    assert "app.a" in result.all_modules
    assert "app.b" in result.all_modules
    assert "app.c" in result.all_modules


def test_change_with_side_effect_in_dependency(tmp_path: Path):
    """app.a imports app.b; app.b has @side_effect tagged function.
    Closure includes the side-effect qualname."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "from app import b\n",
        "b.py": "def write(): pass\n",
    })
    REGISTRY.register(TaggedFunction(
        qualified_name="app.b.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.b",
        callable_name="write",
    ))
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    assert "app.b.write" in result.side_effect_qualnames


def test_task_dependencies_added_to_closure(tmp_path: Path):
    """Modules from task_dependencies are included even without import edge."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "",
        "b.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
        task_dependency_modules={"app.b"},
    )
    assert "app.b" in result.all_modules
    assert "app.b" in result.task_dependency_modules


def test_task_dependency_side_effects_collected(tmp_path: Path):
    """Side effects from task-dependency modules are collected even without import edge."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "",
        "b.py": "def write(): pass\n",
    })
    REGISTRY.register(TaggedFunction(
        qualified_name="app.b.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.b",
        callable_name="write",
    ))
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
        task_dependency_modules={"app.b"},
    )
    assert "app.b.write" in result.side_effect_qualnames


def test_impact_closure_result_is_frozen(tmp_path: Path):
    graph, _ = _build_synthetic_tree(tmp_path, {})
    result = compute_impact_closure(
        change_files=set(),
        change_modules=set(),
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    try:
        result.change_files = frozenset({"x"})  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("ImpactClosureResult should be frozen")


def test_has_module_and_has_qualname(tmp_path: Path):
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "from app import b\n",
        "b.py": "def write(): pass\n",
    })
    REGISTRY.register(TaggedFunction(
        qualified_name="app.b.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.b",
        callable_name="write",
    ))
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    assert result.has_module("app.b")
    assert not result.has_module("app.nonexistent")
    assert result.has_qualname("app.b.write")
    assert not result.has_qualname("app.nonexistent.fn")


def test_total_module_count(tmp_path: Path):
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "from app import b\n",
        "b.py": "from app import c\n",
        "c.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    # `from app import b` produces dependency edges to both 'app' (package)
    # and 'app.b' (submodule). Closure includes app, app.a, app.b, app.c.
    assert result.total_module_count() == 4
    assert "app.a" in result.all_modules
    assert "app.b" in result.all_modules
    assert "app.c" in result.all_modules


# --- verify_change_coverage ----------------------------------------------


def test_coverage_pass_when_declaration_matches(tmp_path: Path):
    """Author declared exactly the change modules -> PASS."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "",
        "b.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    verdict = verify_change_coverage(
        declared_modifying_modules={"app.a"},
        closure=result,
    )
    assert verdict.passed
    assert verdict.missing_modules == frozenset()


def test_coverage_fails_when_task_dependency_not_declared(tmp_path: Path):
    """task_dependency module must be declared by the author."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "",
        "b.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
        task_dependency_modules={"app.b"},
    )
    verdict = verify_change_coverage(
        declared_modifying_modules={"app.a"},  # missing app.b
        closure=result,
    )
    assert not verdict.passed
    assert "app.b" in verdict.missing_modules
    assert verdict.reason and "missing" in verdict.reason


def test_coverage_pass_when_extra_declarations(tmp_path: Path):
    """Author can declare more than the closure requires (over-declaration)."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    verdict = verify_change_coverage(
        declared_modifying_modules={"app.a", "app.extra"},  # over-declared
        closure=result,
    )
    assert verdict.passed


def test_coverage_pure_import_closure_not_required(tmp_path: Path):
    """If A imports B, modifying A does NOT require declaring B (B is a dep, not modified).

    Only change_modules + task_dependencies must be declared. Forward-
    import closure is informational.
    """
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "from app import b\n",
        "b.py": "",
    })
    result = compute_impact_closure(
        change_files={"app/a.py"},
        change_modules={"app.a"},
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    # B is in result.import_closure_modules but not in change_modules.
    # Author declares only A -> PASS (B is just imported, not modified).
    verdict = verify_change_coverage(
        declared_modifying_modules={"app.a"},
        closure=result,
    )
    assert verdict.passed


def test_coverage_verdict_is_frozen(tmp_path: Path):
    graph, _ = _build_synthetic_tree(tmp_path, {})
    result = compute_impact_closure(
        change_files=set(),
        change_modules=set(),
        import_graph=graph,
        side_effect_registry=REGISTRY,
    )
    verdict = verify_change_coverage(
        declared_modifying_modules=set(),
        closure=result,
    )
    try:
        verdict.passed = False  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("CoverageVerdict should be frozen")


# --- Determinism (P6) ---------------------------------------------------


def test_compute_impact_closure_determinism(tmp_path: Path):
    """Same inputs -> same closure across runs."""
    graph, _ = _build_synthetic_tree(tmp_path, {
        "a.py": "from app import b\n",
        "b.py": "def write(): pass\n",
    })
    REGISTRY.register(TaggedFunction(
        qualified_name="app.b.write",
        kind=SideEffectKind.DB_WRITE,
        module="app.b",
        callable_name="write",
    ))

    def _run():
        return compute_impact_closure(
            change_files={"app/a.py"},
            change_modules={"app.a"},
            import_graph=graph,
            side_effect_registry=REGISTRY,
            task_dependency_modules={"app.c"},
        )

    r1 = _run()
    r2 = _run()
    r3 = _run()
    assert r1 == r2 == r3

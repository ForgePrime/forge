"""Tests for ImportGraph — Phase C Stage C.1.

Pure-Python AST-based tests using a tmp_path fixture (synthetic source
tree). No DB, no network, no live filesystem dependencies.

Critical properties:
- Static-import detection (absolute + relative + star).
- reverse_deps + forward_deps BFS correctness.
- Determinism (P6): same tree -> same graph.
- Malformed files skipped silently (best-effort).
- Depth limit respected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.validation.import_graph import (
    ImportEdge,
    ImportGraph,
    build,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --- Build basics --------------------------------------------------------


def test_empty_directory_returns_empty_graph(tmp_path: Path):
    pkg = tmp_path / "app"
    pkg.mkdir()
    graph = build(pkg, package_prefix="app")
    assert isinstance(graph, ImportGraph)
    assert graph.forward == {}
    assert graph.reverse == {}
    assert graph.edges == []


def test_single_file_with_absolute_import(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "import sys\n")
    graph = build(pkg, package_prefix="app")
    assert "app.a" in graph.forward
    assert "sys" in graph.forward["app.a"]


def test_single_file_with_from_import(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from collections import OrderedDict\n")
    graph = build(pkg, package_prefix="app")
    assert "collections" in graph.forward["app.a"]


def test_relative_import_from_dot_resolves(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "__init__.py", "")
    _write(pkg / "sub" / "__init__.py", "")
    _write(pkg / "sub" / "a.py", "from . import b\n")
    _write(pkg / "sub" / "b.py", "")
    graph = build(pkg, package_prefix="app")
    # `from . import b` in app.sub.a resolves to 'app.sub.b'
    assert "app.sub.b" in graph.forward["app.sub.a"]


def test_relative_import_from_dot_module_resolves(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "__init__.py", "")
    _write(pkg / "sub" / "__init__.py", "")
    _write(pkg / "sub" / "a.py", "from .b import X\n")
    _write(pkg / "sub" / "b.py", "X = 1\n")
    graph = build(pkg, package_prefix="app")
    assert "app.sub.b" in graph.forward["app.sub.a"]


def test_relative_import_double_dot_resolves(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "__init__.py", "")
    _write(pkg / "sub" / "__init__.py", "")
    _write(pkg / "sub" / "deep" / "__init__.py", "")
    _write(pkg / "sub" / "deep" / "a.py", "from .. import b\n")
    _write(pkg / "sub" / "b.py", "")
    graph = build(pkg, package_prefix="app")
    # `from .. import b` in app.sub.deep.a resolves to 'app.sub.b'
    assert "app.sub.b" in graph.forward["app.sub.deep.a"]


def test_init_py_module_naming(tmp_path: Path):
    """app/api/__init__.py is named 'app.api', not 'app.api.__init__'."""
    pkg = tmp_path / "app"
    _write(pkg / "api" / "__init__.py", "import os\n")
    graph = build(pkg, package_prefix="app")
    assert "app.api" in graph.forward
    assert "os" in graph.forward["app.api"]


# --- reverse_deps --------------------------------------------------------


def test_reverse_deps_direct(tmp_path: Path):
    """A imports B -> reverse_deps(B) contains A."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "")
    graph = build(pkg, package_prefix="app")
    rev = graph.reverse_deps("app.b")
    assert "app.a" in rev


def test_reverse_deps_transitive(tmp_path: Path):
    """A -> B -> C; reverse_deps(C) contains both B and A."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "from app import c\n")
    _write(pkg / "c.py", "")
    graph = build(pkg, package_prefix="app")
    rev = graph.reverse_deps("app.c", depth=10)
    assert "app.a" in rev
    assert "app.b" in rev


def test_reverse_deps_excludes_self(tmp_path: Path):
    """reverse_deps(M) does not contain M itself even if there's a cycle."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "from app import a\n")  # cycle
    graph = build(pkg, package_prefix="app")
    rev = graph.reverse_deps("app.a", depth=10)
    assert "app.a" not in rev
    assert "app.b" in rev


def test_reverse_deps_depth_zero_returns_empty(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "")
    graph = build(pkg, package_prefix="app")
    assert graph.reverse_deps("app.b", depth=0) == set()


def test_reverse_deps_depth_one_only_direct(tmp_path: Path):
    """A -> B -> C; reverse_deps(C, depth=1) returns only B, not A."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "from app import c\n")
    _write(pkg / "c.py", "")
    graph = build(pkg, package_prefix="app")
    rev = graph.reverse_deps("app.c", depth=1)
    assert rev == {"app.b"}


def test_reverse_deps_for_unknown_module_returns_empty(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "")
    graph = build(pkg, package_prefix="app")
    assert graph.reverse_deps("app.nonexistent") == set()


# --- forward_deps --------------------------------------------------------


def test_forward_deps_transitive(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "from app import c\n")
    _write(pkg / "c.py", "")
    graph = build(pkg, package_prefix="app")
    fwd = graph.forward_deps("app.a", depth=10)
    assert "app.b" in fwd
    assert "app.c" in fwd


def test_forward_deps_terminates_on_cycle(tmp_path: Path):
    """Cycle does not infinite-loop."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "from app import a\n")
    graph = build(pkg, package_prefix="app")
    fwd = graph.forward_deps("app.a", depth=10)
    assert "app.b" in fwd  # included
    # 'app.a' itself is excluded
    assert "app.a" not in fwd


# --- has_module + edges --------------------------------------------------


def test_has_module(tmp_path: Path):
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\n")
    _write(pkg / "b.py", "")
    graph = build(pkg, package_prefix="app")
    assert graph.has_module("app.a") is True
    assert graph.has_module("app.b") is True
    assert graph.has_module("app.nonexistent") is False


def test_edges_record_each_import(tmp_path: Path):
    """Every import produces an ImportEdge in graph.edges."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "import os\nimport sys\n")
    graph = build(pkg, package_prefix="app")
    edges_from_a = [e for e in graph.edges if e.importer == "app.a"]
    targets = {e.imported for e in edges_from_a}
    assert "os" in targets
    assert "sys" in targets


# --- Determinism (P6) ----------------------------------------------------


def test_build_determinism(tmp_path: Path):
    """Same tree -> same graph across multiple builds."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "from app import b\nimport os\n")
    _write(pkg / "b.py", "import sys\n")

    g1 = build(pkg, package_prefix="app")
    g2 = build(pkg, package_prefix="app")
    g3 = build(pkg, package_prefix="app")
    assert g1.forward == g2.forward == g3.forward
    assert g1.reverse == g2.reverse == g3.reverse
    # Edge order also stable (sorted import names + sorted file traversal)
    assert g1.edges == g2.edges == g3.edges


# --- Malformed files skipped silently -----------------------------------


def test_malformed_python_file_skipped(tmp_path: Path):
    """SyntaxError in one file does not break the whole build."""
    pkg = tmp_path / "app"
    _write(pkg / "good.py", "import os\n")
    _write(pkg / "broken.py", "this is not valid python !!!\n")
    graph = build(pkg, package_prefix="app")
    # 'good' module is in graph
    assert "app.good" in graph.forward
    # 'broken' module is NOT in graph (skipped)
    assert "app.broken" not in graph.forward


def test_pycache_skipped(tmp_path: Path):
    """__pycache__ directories are excluded."""
    pkg = tmp_path / "app"
    _write(pkg / "a.py", "import os\n")
    _write(pkg / "__pycache__" / "a.cpython-313.pyc", "")
    graph = build(pkg, package_prefix="app")
    # No spurious entries from __pycache__
    cached_modules = [m for m in graph.forward if "__pycache__" in m]
    assert cached_modules == []


# --- Frozen ImportEdge ---------------------------------------------------


def test_import_edge_is_frozen():
    edge = ImportEdge(importer="a", imported="b")
    try:
        edge.importer = "x"  # type: ignore[misc]
    except (AttributeError, Exception):
        pass
    else:
        raise AssertionError("ImportEdge should be frozen")


# --- Real-world smoke: build over actual platform/app/ -------------------


def test_smoke_build_over_actual_app(tmp_path: Path):
    """Build succeeds over the real platform/app/ tree without crashing.

    This is a smoke test only — does not assert specific edges since
    the real codebase evolves. Asserts only that build returns a non-
    empty graph and that some key models are reachable.
    """
    repo_root = Path(__file__).resolve().parent.parent
    real_app = repo_root / "app"
    if not real_app.exists():
        pytest.skip("real platform/app/ not found")
    graph = build(real_app, package_prefix="app")
    assert len(graph.forward) > 0
    # At least some known modules should be present
    assert any("app.models" in m for m in graph.forward) or \
           any("app.validation" in m for m in graph.forward)

"""ImportGraph — Phase C Stage C.1.

Pure-Python AST-based static-import graph over the `app/` tree.
Produces the reverse-dependency map: for any module, which modules
import it (transitively, up to depth).

Per PLAN_QUALITY_ASSURANCE C.1 + FORMAL_PROPERTIES_v2 P3 (Impact
Closure):

    Impact(Δ) = Closure(dependencies)

ImportGraph supplies the static-import portion of dependency closure.
C.2 SideEffectRegistry adds tagged side-effecting functions; C.3
ImpactClosure unions the two + task_dependencies.

Scope (per PLAN A_{C.1}):
- Static AST walk only — handles `import X`, `from X import Y`, etc.
- Does NOT cover dynamic dispatch (`getattr`, `__import__`, runtime
  importlib). Documented gap; closed in C.2 via @side_effect tagging
  for the dynamically-dispatched functions that mutate state.
- Operates on a directory snapshot; not a live filesystem watcher.
  Cache invalidation per ADR (currently CI-gate per A_{C.1} ASSUMED).

Determinism (P6):
- Same source tree -> same graph (sorted file traversal, sorted
  import lookup).
- No clock / random / network reads.
- Caller can pass a fixed root for reproducible test fixtures.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ImportEdge:
    """Directed edge: `importer` imports `imported`."""

    importer: str  # dotted module path, e.g. 'app.api.execute'
    imported: str  # dotted module path, e.g. 'app.services.contract_validator'


@dataclass
class ImportGraph:
    """Static-import graph over a directory tree.

    Mutable container during construction; treat as frozen after `build`
    returns. Caller should not mutate `forward` / `reverse` after build.
    """

    root: Path  # directory rooted at the package start (typically app/)
    package_prefix: str  # e.g. 'app' — the dotted prefix of `root`
    forward: dict[str, set[str]] = field(default_factory=dict)
    reverse: dict[str, set[str]] = field(default_factory=dict)
    edges: list[ImportEdge] = field(default_factory=list)

    def reverse_deps(self, module: str, *, depth: int = 10) -> set[str]:
        """Modules that (transitively) import `module`, up to `depth` hops.

        BFS over reverse map. Excludes `module` itself from the result
        (only its dependents). Depth=0 returns empty set; depth=1
        returns direct importers.
        """
        if depth <= 0:
            return set()
        out: set[str] = set()
        frontier: set[str] = {module}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for m in frontier:
                for importer in self.reverse.get(m, set()):
                    if importer in out or importer == module:
                        continue
                    out.add(importer)
                    next_frontier.add(importer)
            if not next_frontier:
                break
            frontier = next_frontier
        return out

    def forward_deps(self, module: str, *, depth: int = 10) -> set[str]:
        """Modules that `module` (transitively) imports, up to `depth` hops."""
        if depth <= 0:
            return set()
        out: set[str] = set()
        frontier: set[str] = {module}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for m in frontier:
                for imported in self.forward.get(m, set()):
                    if imported in out or imported == module:
                        continue
                    out.add(imported)
                    next_frontier.add(imported)
            if not next_frontier:
                break
            frontier = next_frontier
        return out

    def has_module(self, module: str) -> bool:
        """Whether the module appears in the graph (as importer or imported)."""
        return module in self.forward or module in self.reverse


def _module_name_for(file_path: Path, root: Path, package_prefix: str) -> str:
    """Convert file path to dotted module name relative to `root`.

    e.g. with package_prefix='app' and root=/repo/platform/app,
    file_path=/repo/platform/app/api/execute.py -> 'app.api.execute'.
    Handles __init__.py: /repo/platform/app/api/__init__.py -> 'app.api'.
    """
    rel = file_path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return package_prefix
    return f"{package_prefix}." + ".".join(parts)


def _extract_imports_from_ast(tree: ast.AST, current_module: str) -> set[str]:
    """Walk AST; return set of dotted import targets.

    Returns *candidate* targets — for `from X import Y`, both `X` AND
    `X.Y` are emitted because `Y` may be either a name within module X
    (class, function, variable) OR a submodule of X. Caller post-
    processes against the known-module set to keep only real submodule
    edges.

    Handles:
    - `import X` -> 'X'
    - `import X.Y.Z` -> 'X.Y.Z' (full dotted)
    - `from X import Y, Z` -> {'X', 'X.Y', 'X.Z'}  (Y/Z disambiguated by caller)
    - `from . import Y` -> resolves to {parent_pkg, parent_pkg.Y}
    - `from .pkg import Y` -> resolves to {parent.pkg, parent.pkg.Y}
    - `from .. import X` -> grandparent + grandparent.X
    """
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            level = node.level or 0
            if level == 0:
                # Absolute import.
                if node.module:
                    out.add(node.module)
                    # Each imported name might be a submodule of node.module.
                    for alias in node.names:
                        if alias.name != "*":
                            out.add(f"{node.module}.{alias.name}")
            else:
                # Relative import.
                resolved = _resolve_relative(current_module, node.module, level)
                if resolved:
                    out.add(resolved)
                    for alias in node.names:
                        if alias.name != "*":
                            out.add(f"{resolved}.{alias.name}")
    return out


def _resolve_relative(current_module: str, relative_module: str | None, level: int) -> str | None:
    """Resolve `from {.....}{name} import x` to absolute dotted target.

    Args:
        current_module: e.g. 'app.api.execute'
        relative_module: the part after the dots (None or 'foo' or 'foo.bar')
        level: number of leading dots (1=current package, 2=parent, etc.)

    Returns:
        Absolute dotted module, or None if level overshoots.
    """
    parts = current_module.split(".")
    # `level` dots means strip `level` trailing parts (level=1 strips
    # the leaf module to get the current package).
    if level > len(parts):
        return None
    base_parts = parts[:-level] if level <= len(parts) else []
    if relative_module:
        base_parts.extend(relative_module.split("."))
    return ".".join(base_parts) if base_parts else None


def build(root: Path, package_prefix: str = "app") -> ImportGraph:
    """Construct the ImportGraph over the directory tree rooted at `root`.

    Args:
        root: directory containing the package's modules (e.g. platform/app/).
        package_prefix: dotted prefix used to name modules. Default 'app'
            matches the platform's package layout.

    Returns:
        ImportGraph populated with forward + reverse maps.

    Determinism: file traversal is sorted; AST walk yields nodes in
    document order; resulting graph is identical across runs given the
    same source tree.
    """
    graph = ImportGraph(root=root, package_prefix=package_prefix)

    # Deterministic file order: sorted Path traversal.
    py_files = sorted(root.rglob("*.py"))
    for file_path in py_files:
        # Skip cached / generated bytecode dirs (defensive — rglob('*.py')
        # shouldn't see them, but doesn't hurt).
        if "__pycache__" in file_path.parts:
            continue
        module_name = _module_name_for(file_path, root, package_prefix)
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, SyntaxError):
            # Malformed file: skip silently. Production CI catches syntax
            # errors elsewhere; the graph build itself is best-effort.
            continue

        imports = _extract_imports_from_ast(tree, module_name)
        for imported in sorted(imports):  # sort for determinism
            graph.forward.setdefault(module_name, set()).add(imported)
            graph.reverse.setdefault(imported, set()).add(module_name)
            graph.edges.append(ImportEdge(importer=module_name, imported=imported))

    return graph

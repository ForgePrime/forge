"""ImpactClosure — Phase C Stage C.3.

Closes FORMAL_PROPERTIES_v2 P3 (Impact Closure):

    Impact(Δ) = Closure(dependencies, side_effects, task_dependencies)

Composes:
- C.1 ImportGraph (static dependency closure).
- C.2 SideEffectRegistry (function-level side-effect tagging).
- task_dependencies (caller-supplied; from existing schema).

Usage at Change-commit time:
    closure = compute_impact_closure(
        change_files={'app/api/execute.py'},
        change_modules={'app.api.execute'},
        import_graph=...,    # built from app/ tree
        side_effect_registry=...,  # process-level singleton
        task_dependency_modules={'app.services.contract_validator'},
    )

Then VerdictEngine rule: a Change whose declared `modifying` files
must be a subset of `closure.all_files`. If not, the change has
declared less than its true impact -> REJECTED.

Determinism (P6): pure function over its inputs. Caller's responsibility
to ensure ImportGraph + SideEffectRegistry are stable snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImpactClosureResult:
    """Output of compute_impact_closure().

    Frozen dataclass; safe to pass around without mutation concerns.
    """

    change_files: frozenset[str]
    change_modules: frozenset[str]
    import_closure_modules: frozenset[str]
    side_effect_qualnames: frozenset[str]
    task_dependency_modules: frozenset[str]
    all_modules: frozenset[str]  # union of import_closure + task_deps + change

    def has_module(self, module: str) -> bool:
        return module in self.all_modules

    def has_qualname(self, qualname: str) -> bool:
        return qualname in self.side_effect_qualnames

    def total_module_count(self) -> int:
        return len(self.all_modules)


def compute_impact_closure(
    *,
    change_files: set[str] | frozenset[str],
    change_modules: set[str] | frozenset[str],
    import_graph,
    side_effect_registry,
    task_dependency_modules: set[str] | frozenset[str] | None = None,
    forward_depth: int = 10,
) -> ImpactClosureResult:
    """Compute the transitive impact closure for a Change.

    Args:
        change_files: file paths the Change directly modifies (e.g.
            {'app/api/execute.py', 'app/services/x.py'}).
        change_modules: dotted module names corresponding to those files
            (e.g. {'app.api.execute', 'app.services.x'}).
        import_graph: C.1 ImportGraph instance.
        side_effect_registry: C.2 SideEffectRegistry instance.
        task_dependency_modules: optional — modules from existing
            task_dependencies relations that should be included in
            the closure.
        forward_depth: BFS depth for forward-import closure (default 10
            per ADR-004 strawman).

    Returns:
        ImpactClosureResult.

    Per FORMAL P3: declared `modifying` of a Change MUST be a subset of
    `result.all_modules` for the Change to pass C.3 gate; missing
    elements are unjustified impact (the Change touches things it didn't
    declare).
    """
    change_files_fset = frozenset(change_files)
    change_modules_fset = frozenset(change_modules)
    task_deps_fset = frozenset(task_dependency_modules or set())

    # 1. Static-import forward closure: every module reachable via
    #    import edges from any change_module.
    import_closure: set[str] = set()
    for module in change_modules_fset:
        import_closure.update(import_graph.forward_deps(module, depth=forward_depth))

    # 2. Side-effect functions in any module touched by the change OR
    #    in its import closure.
    all_touched_modules = change_modules_fset | frozenset(import_closure) | task_deps_fset
    side_effect_qualnames = side_effect_registry.callers_in_path(
        set(change_modules_fset), import_graph
    )
    # Also include side-effects from task-dependency modules (which may
    # not be in the import closure but are explicit dependency edges).
    for tdm in task_deps_fset:
        side_effect_qualnames |= side_effect_registry.qualnames_in_module(tdm)

    return ImpactClosureResult(
        change_files=change_files_fset,
        change_modules=change_modules_fset,
        import_closure_modules=frozenset(import_closure),
        side_effect_qualnames=frozenset(side_effect_qualnames),
        task_dependency_modules=task_deps_fset,
        all_modules=all_touched_modules,
    )


@dataclass(frozen=True)
class CoverageVerdict:
    """Output of verify_change_coverage()."""

    passed: bool
    declared_modules: frozenset[str]
    closure_modules: frozenset[str]
    missing_modules: frozenset[str]  # in closure but not declared
    reason: str | None = None


def verify_change_coverage(
    *,
    declared_modifying_modules: set[str] | frozenset[str],
    closure: ImpactClosureResult,
) -> CoverageVerdict:
    """Verify a Change's declared `modifying` covers its impact closure.

    Per FORMAL P3 acceptance criterion:
        declared_modifying ⊇ closure.all_modules
                            \\ {modules NOT actually modified, just imported}

    Operational interpretation: the change author must DECLARE every
    module that is touched by the change in a meaningful way. Pure-import
    closure (modules that just import the change's module) is excluded
    from the requirement; the change touches the dependency graph
    surface, not the dependent's source.

    For MVP, the closure check is on `change_modules` ∪
    `task_dependency_modules` (the explicit-dependency portion).
    Forward-import closure is informational, not gating.

    Args:
        declared_modifying_modules: from Change.modifying (what the
            author claims they edited).
        closure: ImpactClosureResult from compute_impact_closure().

    Returns:
        CoverageVerdict.
    """
    declared = frozenset(declared_modifying_modules)

    # Required coverage = explicit change modules + task_dependency modules.
    # Forward-import closure (pure dependents) is NOT required to be declared.
    required = closure.change_modules | closure.task_dependency_modules

    missing = required - declared

    if not missing:
        return CoverageVerdict(
            passed=True,
            declared_modules=declared,
            closure_modules=closure.all_modules,
            missing_modules=frozenset(),
        )

    return CoverageVerdict(
        passed=False,
        declared_modules=declared,
        closure_modules=closure.all_modules,
        missing_modules=missing,
        reason=(
            f"Change declared {len(declared)} modules but impact closure "
            f"requires coverage of {len(required)}; missing: "
            f"{sorted(missing)}"
        ),
    )

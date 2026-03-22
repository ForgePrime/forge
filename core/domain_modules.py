"""
Domain Modules — serve domain-specific guidance per phase.

Instead of LLM scanning 4 x 350-line files, this module serves exactly
the right section (~50-80 lines) based on scope and phase.

Usage:
    python -m core.domain_modules list
    python -m core.domain_modules get {module} --phase {phase}
    python -m core.domain_modules for-scopes --scopes "{s1},{s2}" --phase {phase} [--task-type {type}]
    python -m core.domain_modules deps {module1} {module2}
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# -- Module Registry --

MODULES = {
    "ux": {
        "file": "ux.md",
        "scopes": {"frontend", "ui", "ux", "design", "components"},
        "description": "UI components, user flows, states, layout placement",
    },
    "backend": {
        "file": "backend.md",
        "scopes": {"backend", "api", "server", "services"},
        "description": "API endpoints, business rules, error handling, service layers",
    },
    "process": {
        "file": "process.md",
        "scopes": {"workflow", "process", "state-machine", "orchestration", "automation"},
        "description": "State machines, transitions, side effects, permissions",
    },
    "data": {
        "file": "data.md",
        "scopes": {"database", "data", "schema", "migration", "storage", "etl"},
        "description": "Schema design, migrations, relationships, constraints, access patterns",
    },
}

PHASE_NAMES = {"vision", "research", "planning", "execution"}

PHASE_STORAGE = {
    "vision": "Research (R-NNN) linked to objective/idea. Persistent findings → Knowledge (K-NNN).",
    "research": "Research (R-NNN updated) + Knowledge (K-NNN for durable artifacts: api_contracts, schemas, state_diagrams).",
    "planning": "Task fields directly: instruction, acceptance_criteria, exclusions, alignment.",
    "execution": "Changes + AC reasoning (handled by pipeline complete).",
}

# Types that skip domain modules (complexity gate)
SKIP_TYPES = {"bug", "chore"}

# -- Module Directory --

def _modules_dir() -> Path:
    """Find skills/domain-modules/modules/ directory."""
    # Try relative to this file (core/domain_modules.py → ../skills/domain-modules/modules/)
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "skills" / "domain-modules" / "modules",
        here / ".." / "skills" / "domain-modules" / "modules",
        Path("skills") / "domain-modules" / "modules",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    # Fallback: search from cwd
    cwd = Path.cwd()
    for p in [cwd, cwd.parent]:
        d = p / "skills" / "domain-modules" / "modules"
        if d.is_dir():
            return d
    from errors import EntityNotFound
    raise EntityNotFound("Cannot find skills/domain-modules/modules/ directory.")


# -- Phase Parsing --

def _parse_phases(filepath: Path) -> dict:
    """Parse a module file into phase sections.

    Expects markers like: ## Phase 1: Vision Extraction
    Returns dict: {"vision": "...", "research": "...", "planning": "...", "execution": "..."}
    """
    text = filepath.read_text(encoding="utf-8")

    # Map phase numbers/names to canonical keys
    phase_patterns = {
        "vision": r"## Phase 1[:\s]",
        "research": r"## Phase 2[:\s]",
        "planning": r"## Phase 3[:\s]",
        "execution": r"## Phase 4[:\s]",
    }

    # Find all phase start positions
    phase_positions = []
    for key, pattern in phase_patterns.items():
        match = re.search(pattern, text)
        if match:
            phase_positions.append((match.start(), key))

    # Also find non-phase sections to know where to stop
    # (e.g., "## Cross-module Interface", "## Triggers", "## Prerequisites")
    all_h2 = [(m.start(), m.group()) for m in re.finditer(r"^## ", text, re.MULTILINE)]

    phase_positions.sort(key=lambda x: x[0])

    phases = {}
    for i, (pos, key) in enumerate(phase_positions):
        # Find end: next phase start or next non-phase ## or end of file
        end = len(text)
        for next_pos, _ in all_h2:
            if next_pos > pos:
                end = next_pos
                break
        phases[key] = text[pos:end].strip()

    return phases


def _parse_cross_module(filepath: Path) -> str:
    """Extract Cross-module Interface section from a module file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.search(r"^## Cross-module Interface\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.start()
    # Find next ## or end
    next_h2 = re.search(r"^## ", text[start + 1:], re.MULTILINE)
    end = start + 1 + next_h2.start() if next_h2 else len(text)
    return text[start:end].strip()


def _parse_prerequisites(filepath: Path) -> str:
    """Extract Prerequisites section."""
    text = filepath.read_text(encoding="utf-8")
    match = re.search(r"^## Prerequisites\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.start()
    next_h2 = re.search(r"^## ", text[start + 1:], re.MULTILINE)
    end = start + 1 + next_h2.start() if next_h2 else len(text)
    return text[start:end].strip()


# -- Commands --

def cmd_list(args):
    """Show available modules with scopes and descriptions."""
    print("## Domain Modules")
    print()
    print("| Module | Scopes | Description |")
    print("|--------|--------|-------------|")
    for name, info in sorted(MODULES.items()):
        scopes = ", ".join(sorted(info["scopes"]))
        print(f"| {name} | {scopes} | {info['description']} |")
    print()
    print("**Phases**: vision, research, planning, execution")
    print()
    print("Usage:")
    print("  python -m core.domain_modules get {module} --phase {phase}")
    print("  python -m core.domain_modules for-scopes --scopes \"frontend,backend\" --phase planning")


def cmd_get(args):
    """Get a specific phase from a module."""
    module_name = args.module
    phase = args.phase

    from errors import EntityNotFound, ValidationError

    if module_name not in MODULES:
        raise EntityNotFound(f"Unknown module '{module_name}'. Available: {', '.join(sorted(MODULES))}")

    if phase not in PHASE_NAMES:
        raise ValidationError(f"Unknown phase '{phase}'. Available: {', '.join(sorted(PHASE_NAMES))}")

    modules_dir = _modules_dir()
    filepath = modules_dir / MODULES[module_name]["file"]

    if not filepath.exists():
        raise EntityNotFound(f"Module file not found: {filepath}")

    phases = _parse_phases(filepath)

    if phase not in phases:
        raise EntityNotFound(f"Phase '{phase}' not found in module '{module_name}'.")

    # Header with storage guidance
    print(f"## Domain Module: {module_name} — Phase: {phase}")
    print(f"**Store output in**: {PHASE_STORAGE.get(phase, 'N/A')}")
    print()

    # Prerequisites (always useful context)
    prereqs = _parse_prerequisites(filepath)
    if prereqs:
        print(prereqs)
        print()

    # Phase content
    print(phases[phase])


def cmd_for_scopes(args):
    """Get modules matching scopes for a given phase."""
    scopes = {s.strip() for s in args.scopes.split(",") if s.strip()}
    phase = args.phase
    task_type = getattr(args, "task_type", None)

    if phase not in PHASE_NAMES:
        from errors import ValidationError
        raise ValidationError(f"Unknown phase '{phase}'. Available: {', '.join(sorted(PHASE_NAMES))}")

    # Complexity gate: skip for bug/chore
    if task_type and task_type in SKIP_TYPES:
        print(f"Skipped: domain modules not loaded for {task_type} tasks.")
        print(f"Domain modules are for feature/investigation tasks during planning and discovery.")
        return

    # Find matching modules
    matched = []
    for name, info in MODULES.items():
        if scopes & info["scopes"]:
            matched.append(name)

    if not matched:
        print(f"No domain modules match scopes: {', '.join(sorted(scopes))}")
        print(f"Available scopes: {', '.join(sorted(s for m in MODULES.values() for s in m['scopes']))}")
        return

    modules_dir = _modules_dir()

    # Header
    print(f"## Domain Guidance — Phase: {phase}")
    print(f"**Active modules**: {', '.join(sorted(matched))} (from scopes: {', '.join(sorted(scopes))})")
    print(f"**Store output in**: {PHASE_STORAGE.get(phase, 'N/A')}")
    print()

    # Output each module's phase
    for name in sorted(matched):
        filepath = modules_dir / MODULES[name]["file"]
        if not filepath.exists():
            print(f"WARNING: Module file not found: {filepath}", file=sys.stderr)
            continue

        phases = _parse_phases(filepath)
        if phase not in phases:
            print(f"WARNING: Phase '{phase}' not found in module '{name}'.", file=sys.stderr)
            continue

        # Prerequisites (once per module)
        prereqs = _parse_prerequisites(filepath)
        if prereqs:
            print(prereqs)
            print()

        print(phases[phase])
        print()
        print("---")
        print()

    # Cross-module dependencies (if 2+ modules)
    if len(matched) >= 2:
        print("## Cross-module Dependencies")
        print()
        for name in sorted(matched):
            filepath = modules_dir / MODULES[name]["file"]
            if not filepath.exists():
                continue
            cross = _parse_cross_module(filepath)
            if cross:
                # Filter to only show interfaces relevant to other active modules
                print(cross)
                print()


def cmd_deps(args):
    """Show cross-module dependencies between two modules."""
    modules_dir = _modules_dir()

    module_names = args.modules
    for name in module_names:
        if name not in MODULES:
            from errors import EntityNotFound
            raise EntityNotFound(f"Unknown module '{name}'. Available: {', '.join(sorted(MODULES))}")

    print(f"## Cross-module Dependencies: {', '.join(module_names)}")
    print()

    for name in module_names:
        filepath = modules_dir / MODULES[name]["file"]
        if not filepath.exists():
            continue
        cross = _parse_cross_module(filepath)
        if cross:
            print(cross)
            print()


def main():
    # Force UTF-8 stdout on Windows (cp1250 can't handle → and other Unicode)
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", closefd=False)

    parser = argparse.ArgumentParser(
        description="Domain Modules — serve domain-specific guidance per phase"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="Show available modules")

    p = sub.add_parser("get", help="Get specific phase from module")
    p.add_argument("module", help="Module name (ux, backend, process, data)")
    p.add_argument("--phase", required=True, help="Phase: vision, research, planning, execution")

    p = sub.add_parser("for-scopes", help="Get modules matching scopes")
    p.add_argument("--scopes", required=True, help="Comma-separated scopes")
    p.add_argument("--phase", required=True, help="Phase: vision, research, planning, execution")
    p.add_argument("--task-type", default=None, help="Task type (feature/bug/chore/investigation)")

    p = sub.add_parser("deps", help="Show cross-module dependencies")
    p.add_argument("modules", nargs="+", help="Module names to compare")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        from errors import PreconditionError
        raise PreconditionError("No command specified")

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "for-scopes": cmd_for_scopes,
        "deps": cmd_deps,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        from errors import PreconditionError
        raise PreconditionError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()

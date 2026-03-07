"""
Plugins — external skill discovery and registry for Forge.

Discovers external skill packs (e.g., deep-process-skill) from configured
paths and makes them available to the pipeline. Skills remain in their
original directories — Forge only indexes them.

Registry is persisted in forge_plugins.json so discovery doesn't need
to re-scan every invocation.

Usage:
    python -m core.plugins <command> [options]

Commands:
    scan                              Scan configured paths, update registry
    list                              List available plugins
    show     {skill-name}             Show skill details (description + SKILL.md path)
    paths                             Show configured scan paths
    add-path {path}                   Add a scan path
    remove-path {path}                Remove a scan path
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


# -- Paths --

def config_path() -> Path:
    return Path("forge_plugins.json")


def load_config() -> dict:
    p = config_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"scan_paths": [], "registry": {}, "last_scan": None}


def save_config(data: dict):
    config_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -- YAML frontmatter parser (minimal, no dependencies) --

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from SKILL.md. Handles name, description, version, allowed-tools."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result = {}
    # Simple key: value parsing (handles multiline > descriptions)
    current_key = None
    current_val = []
    for line in block.split("\n"):
        kv = re.match(r'^(\w[\w-]*)\s*:\s*(.*)', line)
        if kv:
            if current_key:
                result[current_key] = " ".join(current_val).strip().strip('"').strip("'")
            current_key = kv.group(1)
            val = kv.group(2).strip()
            if val == ">":
                current_val = []
            else:
                current_val = [val]
        elif current_key and line.startswith("  "):
            current_val.append(line.strip())
    if current_key:
        result[current_key] = " ".join(current_val).strip().strip('"').strip("'")

    # Parse allowed-tools from [Read, Glob, ...] format
    if "allowed-tools" in result:
        raw = result["allowed-tools"]
        tools = [t.strip() for t in raw.strip("[]").split(",")]
        result["allowed-tools"] = tools

    return result


# -- Discovery --

def discover_skills(scan_path: str) -> list:
    """Scan a directory for skill subdirectories containing SKILL.md."""
    root = Path(scan_path).resolve()
    if not root.is_dir():
        return []

    skills = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)

        # Check for references/ directory
        refs_dir = child / "references"
        has_refs = refs_dir.is_dir()

        skills.append({
            "name": meta.get("name", child.name),
            "dir_name": child.name,
            "description": meta.get("description", ""),
            "version": meta.get("version", "unknown"),
            "allowed_tools": meta.get("allowed-tools", []),
            "skill_md": str(skill_md),
            "references_dir": str(refs_dir) if has_refs else None,
            "source_path": str(root),
            "source_name": root.name,
        })

    return skills


# -- Commands --

def cmd_scan(args):
    """Scan all configured paths and update registry."""
    config = load_config()
    paths = config.get("scan_paths", [])

    if not paths:
        print("No scan paths configured.")
        print("Add a path: python -m core.plugins add-path /path/to/skills")
        return

    registry = {}
    total = 0

    for scan_path in paths:
        resolved = str(Path(scan_path).resolve())
        if not Path(resolved).is_dir():
            print(f"WARNING: Path not found, skipping: {scan_path}", file=sys.stderr)
            continue

        skills = discover_skills(resolved)
        for s in skills:
            registry[s["name"]] = s
            total += 1
        print(f"Scanned {resolved}: found {len(skills)} skills")

    config["registry"] = registry
    config["last_scan"] = now_iso()
    save_config(config)

    print(f"\nRegistry updated: {total} skills from {len(paths)} path(s)")


def cmd_list(args):
    """List all registered plugins."""
    config = load_config()
    registry = config.get("registry", {})

    if not registry:
        if not config.get("scan_paths"):
            print("No plugins configured. Add a scan path first:")
            print("  python -m core.plugins add-path /path/to/skill-pack")
            print("  python -m core.plugins scan")
        else:
            print("No plugins found. Run scan first:")
            print("  python -m core.plugins scan")
        return

    print(f"## Available Plugins ({len(registry)})")
    print(f"Last scan: {config.get('last_scan', 'never')}")
    print()

    # Group by source
    by_source = {}
    for name, skill in sorted(registry.items()):
        src = skill.get("source_name", "unknown")
        by_source.setdefault(src, []).append(skill)

    for source, skills in sorted(by_source.items()):
        print(f"### {source} ({len(skills)} skills)")
        print()
        print("| Skill | Version | Description |")
        print("|-------|---------|-------------|")
        for s in skills:
            desc = s["description"][:80] + "..." if len(s["description"]) > 80 else s["description"]
            print(f"| {s['name']} | {s['version']} | {desc} |")
        print()


def cmd_show(args):
    """Show details for a specific plugin skill."""
    config = load_config()
    registry = config.get("registry", {})

    skill = registry.get(args.skill_name)
    if not skill:
        # Try fuzzy match (prefix)
        matches = [s for name, s in registry.items() if name.startswith(args.skill_name)]
        if len(matches) == 1:
            skill = matches[0]
        elif len(matches) > 1:
            print(f"Ambiguous name '{args.skill_name}'. Matches:", file=sys.stderr)
            for m in matches:
                print(f"  {m['name']}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Plugin '{args.skill_name}' not found.", file=sys.stderr)
            print(f"Available: {', '.join(sorted(registry.keys()))}", file=sys.stderr)
            sys.exit(1)

    # Verify paths still exist
    skill_md_exists = Path(skill["skill_md"]).exists()
    if not skill_md_exists:
        print(f"WARNING: SKILL.md not found at registered path. Run `plugins scan` to refresh.",
              file=sys.stderr)
        print()

    print(f"## Plugin: {skill['name']}")
    print(f"- **Version**: {skill['version']}")
    print(f"- **Source**: {skill['source_name']}")
    print(f"- **Description**: {skill['description']}")
    print(f"- **SKILL.md**: `{skill['skill_md']}`{'  (MISSING)' if not skill_md_exists else ''}")
    if skill.get("references_dir"):
        print(f"- **References**: `{skill['references_dir']}`")
    if skill.get("allowed_tools"):
        print(f"- **Tools**: {', '.join(skill['allowed_tools'])}")
    print()
    print(f"To execute: read `{skill['skill_md']}` and follow its procedure.")
    if skill.get("references_dir"):
        print(f"Reference files are in `{skill['references_dir']}/`.")


def cmd_paths(args):
    """Show configured scan paths."""
    config = load_config()
    paths = config.get("scan_paths", [])

    if not paths:
        print("No scan paths configured.")
        print("Add one: python -m core.plugins add-path /path/to/skill-pack")
        return

    print("## Configured Scan Paths")
    print()
    for p in paths:
        resolved = Path(p).resolve()
        exists = resolved.is_dir()
        status = "OK" if exists else "NOT FOUND"
        print(f"- `{p}` ({status})")


def cmd_add_path(args):
    """Add a scan path."""
    config = load_config()
    paths = config.get("scan_paths", [])

    new_path = str(Path(args.path).resolve())

    if new_path in paths:
        print(f"Path already configured: {new_path}")
        return

    if not Path(new_path).is_dir():
        print(f"WARNING: Path does not exist yet: {new_path}", file=sys.stderr)

    paths.append(new_path)
    config["scan_paths"] = paths
    save_config(config)

    print(f"Added: {new_path}")
    print(f"Run `python -m core.plugins scan` to discover skills.")


def cmd_remove_path(args):
    """Remove a scan path."""
    config = load_config()
    paths = config.get("scan_paths", [])

    target = str(Path(args.path).resolve())

    if target in paths:
        paths.remove(target)
    elif args.path in paths:
        paths.remove(args.path)
    else:
        print(f"Path not found in config: {args.path}", file=sys.stderr)
        sys.exit(1)

    config["scan_paths"] = paths
    save_config(config)
    print(f"Removed: {target}")


# -- CLI --

def main():
    parser = argparse.ArgumentParser(
        prog="plugins.py",
        description="Forge Plugins -- external skill discovery",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("scan", help="Scan paths, update registry")
    sub.add_parser("list", help="List available plugins")

    show_p = sub.add_parser("show", help="Show plugin details")
    show_p.add_argument("skill_name", help="Skill name (or prefix)")

    sub.add_parser("paths", help="Show configured scan paths")

    add_p = sub.add_parser("add-path", help="Add a scan path")
    add_p.add_argument("path", help="Path to skill pack directory")

    rem_p = sub.add_parser("remove-path", help="Remove a scan path")
    rem_p.add_argument("path", help="Path to remove")

    args = parser.parse_args()
    commands = {
        "scan": cmd_scan,
        "list": cmd_list,
        "show": cmd_show,
        "paths": cmd_paths,
        "add-path": cmd_add_path,
        "remove-path": cmd_remove_path,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

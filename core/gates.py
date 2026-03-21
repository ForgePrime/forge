"""
Gates — validation checks that guard pipeline transitions.

A gate is a shell command (test, lint, type-check) that must pass before
a task can be confidently marked DONE. Gates are configured per-project
and stored in tracker.json.

Usage:
    python -m core.gates <command> <project> [options]

Commands:
    check        {project} [--task X]        Run all configured gates
    config       {project} --data '{json}'   Configure gates
    show         {project}                   Show current gate config
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract
from storage import JSONFileStorage, load_json_data, now_iso

from _compat import configure_encoding
configure_encoding()


# -- Contracts --

CONTRACTS = {
    "config": {
        "required": ["name", "command"],
        "optional": ["required"],
        "enums": {},
        "types": {
            "required": bool,
        },
        "invariant_texts": [
            "name: short identifier for the gate (e.g., 'test', 'lint', 'typecheck')",
            "command: shell command to execute (e.g., 'pytest', 'ruff check .')",
            "required: if true (default), gate failure blocks task completion",
        ],
        "example": [
            {"name": "test", "command": "pytest", "required": True},
            {"name": "lint", "command": "ruff check .", "required": True},
            {"name": "typecheck", "command": "mypy src/", "required": False},
            {"name": "secrets", "command": "gitleaks detect --no-git -v", "required": True},
        ],
    },
}


# -- I/O --

def load_tracker(project: str, storage=None) -> dict:
    if storage is None:
        storage = JSONFileStorage()
    if not storage.exists(project, 'tracker'):
        print(f"ERROR: No tracker for project '{project}'.", file=sys.stderr)
        sys.exit(1)
    return storage.load_data(project, 'tracker')


def save_tracker(project: str, tracker: dict, storage=None):
    if storage is None:
        storage = JSONFileStorage()
    storage.save_data(project, 'tracker', tracker)


# -- Commands --

def cmd_config(args):
    """Configure gates for the project."""
    tracker = load_tracker(args.project)

    try:
        gates = load_json_data(args.data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(gates, list):
        print("ERROR: --data must be a JSON array of gate objects", file=sys.stderr)
        sys.exit(1)

    errors = validate_contract(CONTRACTS["config"], gates)
    if errors:
        print(f"ERROR: {len(errors)} validation issues:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    tracker["gates"] = gates
    save_tracker(args.project, tracker)

    print(f"Gates configured for '{args.project}':")
    for g in gates:
        req = "required" if g.get("required", True) else "advisory"
        print(f"  {g['name']}: {g['command']} ({req})")


def cmd_show(args):
    """Show current gate configuration."""
    tracker = load_tracker(args.project)
    gates = tracker.get("gates", [])

    if not gates:
        print(f"No gates configured for '{args.project}'.")
        print()
        print("Configure with:")
        print(f'  python -m core.gates config {args.project} --data \'[{{"name": "test", "command": "pytest", "required": true}}, {{"name": "lint", "command": "ruff check .", "required": true}}]\'')
        return

    print(f"## Gates: {args.project}")
    print()
    print("| Name | Command | Required |")
    print("|------|---------|----------|")
    for g in gates:
        req = "yes" if g.get("required", True) else "no"
        print(f"| {g['name']} | `{g['command']}` | {req} |")


def cmd_check(args):
    """Run all configured gates."""
    tracker = load_tracker(args.project)
    gates = tracker.get("gates", [])

    if not gates:
        print(f"No gates configured for '{args.project}'. Skipping validation.")
        print(f"Configure with: python -m core.gates config {args.project} --data '[...]'")
        return

    print(f"## Running gates: {args.project}")
    if args.task:
        print(f"Task: {args.task}")
    print()

    results = []
    all_passed = True
    required_failed = False

    for g in gates:
        name = g["name"]
        command = g["command"]
        required = g.get("required", True)

        print(f"  Running: {name} ({command})... ", end="", flush=True)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )
            passed = result.returncode == 0
        except subprocess.TimeoutExpired:
            passed = False
            result = type("R", (), {"stdout": "", "stderr": "Timed out after 120s", "returncode": -1})()
        except Exception as e:
            passed = False
            result = type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

        status = "PASS" if passed else "FAIL"
        print(status)

        if not passed:
            all_passed = False
            if required:
                required_failed = True
            # Show first few lines of error output
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            output = stderr or stdout
            if output:
                for line in output.split("\n")[:5]:
                    print(f"    {line}")

        results.append({
            "name": name,
            "command": command,
            "passed": passed,
            "required": required,
            "output": (result.stderr or result.stdout or "")[:500],
        })

    # Store results on task if specified
    if args.task:
        for task in tracker.get("tasks", []):
            if task["id"] == args.task:
                task["gate_results"] = {
                    "timestamp": now_iso(),
                    "all_passed": all_passed,
                    "results": [{"name": r["name"], "passed": r["passed"]} for r in results],
                }
                break
        save_tracker(args.project, tracker)

    print()
    if all_passed:
        print("All gates passed.")
    elif required_failed:
        print("REQUIRED gates failed. Fix issues before marking task DONE.")
    else:
        print("Advisory gates failed (non-blocking). Consider fixing before proceeding.")

    return all_passed


# -- CLI --

def main():
    parser = argparse.ArgumentParser(description="Forge Gates -- validation checks")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("config", help="Configure gates")
    p.add_argument("project")
    p.add_argument("--data", required=True)

    p = sub.add_parser("show", help="Show gate config")
    p.add_argument("project")

    p = sub.add_parser("check", help="Run gates")
    p.add_argument("project")
    p.add_argument("--task", help="Associate results with task")

    p = sub.add_parser("contract", help="Print contract spec (no project needed)")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))
    p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    commands = {
        "config": cmd_config,
        "show": cmd_show,
        "check": cmd_check,
        "contract": lambda a: print(render_contract(a.name, CONTRACTS[a.name])),
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

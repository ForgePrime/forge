"""
Gates — validation checks that guard pipeline transitions.

A gate is a shell command (test, lint, type-check) that must pass before
a task can be confidently marked DONE. Gates are configured per-project
and stored in tracker.json.

Includes a built-in secret scanner that detects leaked credentials
before they can be committed.

Usage:
    python -m core.gates <command> <project> [options]

Commands:
    check        {project} [--task X]        Run all configured gates
    config       {project} --data '{json}'   Configure gates
    show         {project}                   Show current gate config
    scan-secrets {project}                   Scan for leaked secrets
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import render_contract, validate_contract

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


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
        ],
    },
}


# -- Paths --

def tracker_path(project: str) -> Path:
    return Path("forge_output") / project / "tracker.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_tracker(project: str) -> dict:
    path = tracker_path(project)
    if not path.exists():
        print(f"ERROR: No tracker for project '{project}'.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_tracker(project: str, tracker: dict):
    path = tracker_path(project)
    tracker["updated"] = now_iso()
    path.write_text(
        json.dumps(tracker, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# -- Commands --

def cmd_config(args):
    """Configure gates for the project."""
    tracker = load_tracker(args.project)

    try:
        gates = json.loads(args.data)
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


# -- Built-in: Secret Scanner --

SECRET_PATTERNS = [
    # AWS
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*["\']?[A-Za-z0-9/+=]{40}', "AWS Secret Key"),
    # GitHub
    (r'ghp_[0-9a-zA-Z]{36}', "GitHub Personal Access Token"),
    (r'gho_[0-9a-zA-Z]{36}', "GitHub OAuth Token"),
    (r'github_pat_[0-9a-zA-Z_]{82}', "GitHub Fine-Grained PAT"),
    # Slack
    (r'xox[baprs]-[0-9]{10,13}-[0-9a-zA-Z]{24,}', "Slack Token"),
    # Generic
    (r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "Hardcoded Password"),
    (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{16,}["\']', "Hardcoded API Key"),
    (r'(?:secret|token)\s*[=:]\s*["\'][^"\']{16,}["\']', "Hardcoded Secret/Token"),
    # Private keys
    (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private Key"),
    # Azure
    (r'(?:AccountKey|SharedAccessKey)\s*=\s*[A-Za-z0-9+/=]{40,}', "Azure Storage/SAS Key"),
    # Google
    (r'AIza[0-9A-Za-z_-]{35}', "Google API Key"),
    # JWT (long base64 tokens)
    (r'eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}', "JWT Token"),
]

SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.png', '.jpg',
    '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf',
    '.eot', '.zip', '.tar', '.gz', '.pdf', '.lock',
}

SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    'forge_output', '.tox', '.mypy_cache', 'dist', 'build',
}


def scan_file_for_secrets(filepath: Path) -> list:
    """Scan a single file for secret patterns. Returns list of findings."""
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (PermissionError, OSError):
        return findings

    for line_num, line in enumerate(content.split("\n"), 1):
        for pattern, name in SECRET_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Skip obvious false positives
                stripped = line.strip()
                if any(fp in stripped.lower() for fp in [
                    "example", "placeholder", "your_", "xxx", "test",
                    "fake", "dummy", "sample", "todo", "fixme",
                ]):
                    continue
                findings.append({
                    "file": str(filepath),
                    "line": line_num,
                    "type": name,
                    "text": stripped[:120],
                })
    return findings


def cmd_scan_secrets(args):
    """Scan project files for leaked secrets."""
    # Determine scan root
    scan_root = Path(".")

    findings = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(scan_root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            filepath = Path(dirpath) / filename
            if filepath.suffix.lower() in SKIP_EXTENSIONS:
                continue
            scanned += 1
            file_findings = scan_file_for_secrets(filepath)
            findings.extend(file_findings)

    print(f"## Secret Scan: {args.project}")
    print(f"Files scanned: {scanned}")
    print()

    if not findings:
        print("No secrets detected.")
        return True

    print(f"FINDINGS: {len(findings)} potential secrets detected!")
    print()
    print("| # | File | Line | Type | Preview |")
    print("|---|------|------|------|---------|")
    for i, f in enumerate(findings, 1):
        preview = f["text"][:60].replace("|", "\\|")
        print(f"| {i} | {f['file']} | {f['line']} | {f['type']} | `{preview}` |")

    print()
    print("ACTION REQUIRED: Review each finding. Remove real secrets before committing.")
    print("False positives in test/example files can be ignored.")
    return False


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

    p = sub.add_parser("scan-secrets", help="Scan for leaked secrets")
    p.add_argument("project")

    p = sub.add_parser("contract", help="Print contract spec")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))

    args = parser.parse_args()

    commands = {
        "config": cmd_config,
        "show": cmd_show,
        "check": cmd_check,
        "scan-secrets": cmd_scan_secrets,
        "contract": lambda a: print(render_contract(a.name, CONTRACTS[a.name])),
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

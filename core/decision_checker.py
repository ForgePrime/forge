"""
Decision Drift Detection — check if implementation follows locked decisions.

Compares git diff against CLOSED decisions to detect when implementation
contradicts architectural choices made during planning.

Usage:
    python -m core.decision_checker check {project} [--task T-NNN]
    python -m core.decision_checker report {project}

Drift types:
    COMPLIANT       — recommendation keywords found in changes
    DRIFT_MAJOR     — rejected alternative keywords found in added lines
    DRIFT_MINOR     — related files changed, cannot verify compliance
    NOT_APPLICABLE  — no changed files relate to this decision
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage import JSONFileStorage, now_iso

from _compat import configure_encoding
configure_encoding()


# Decision types that represent implementation guidance (not analysis)
CHECKABLE_TYPES = {
    "architecture", "implementation", "dependency",
    "security", "performance", "testing", "convention",
}

# Short words to ignore during keyword extraction
MIN_KEYWORD_LEN = 5


def load_locked_decisions(project: str) -> list:
    """Load CLOSED decisions with implementation-relevant types."""
    storage = JSONFileStorage()
    data = storage.load_data(project, "decisions")
    return [
        d for d in data.get("decisions", [])
        if d.get("status") == "CLOSED"
        and d.get("type") in CHECKABLE_TYPES
    ]


def get_task_base_commit(project: str, task_id: str) -> str:
    """Get the base commit for a task from tracker."""
    storage = JSONFileStorage()
    tracker = storage.load_data(project, "tracker")
    for task in tracker.get("tasks", []):
        if task["id"] == task_id:
            return task.get("started_at_commit", "")
    return ""


def get_changed_files(base_commit: str = None) -> list:
    """Get list of files changed since base_commit."""
    files = set()
    try:
        if base_commit:
            r = subprocess.run(
                ["git", "diff", "--name-only", base_commit, "HEAD"],
                capture_output=True, text=True, encoding="utf-8",
            )
            files.update(f.strip() for f in r.stdout.strip().split("\n") if f.strip())
        # Also uncommitted
        r2 = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
        )
        files.update(f.strip() for f in r2.stdout.strip().split("\n") if f.strip())
    except FileNotFoundError:
        pass
    return sorted(files)


def get_added_lines(base_commit: str = None) -> str:
    """Get only added lines (+ prefix) from diff for keyword searching."""
    try:
        if base_commit:
            cmd = ["git", "diff", base_commit, "HEAD"]
        else:
            cmd = ["git", "diff", "HEAD"]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        # Extract only added lines (lines starting with +, but not +++ headers)
        lines = []
        for line in r.stdout.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])  # Strip the + prefix
        return "\n".join(lines).lower()
    except FileNotFoundError:
        return ""


def extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text. Skip short/common words."""
    if not text:
        return set()
    words = re.findall(r'[a-zA-Z0-9_.-]+', text.lower())
    return {w for w in words if len(w) >= MIN_KEYWORD_LEN}


def file_matches(decision_file: str, changed_file: str) -> bool:
    """Check if a decision's file hint matches a changed file."""
    if not decision_file:
        return False
    # Exact match or substring
    d = decision_file.replace("\\", "/").lower()
    c = changed_file.replace("\\", "/").lower()
    return d in c or c in d


def check_decision(decision: dict, changed_files: list, added_lines: str) -> dict:
    """Check a single decision against the diff. Returns result dict."""
    result = {
        "decision_id": decision["id"],
        "type": decision.get("type", ""),
        "issue": decision.get("issue", ""),
        "recommendation": decision.get("recommendation", ""),
        "status": "NOT_APPLICABLE",
        "reasoning": "",
        "related_files": [],
    }

    # 1. Find files related to this decision
    decision_file = decision.get("file", "")
    for f in changed_files:
        if file_matches(decision_file, f):
            result["related_files"].append(f)

    # 2. Only check content if related files exist (prevents false positives)
    if not result["related_files"]:
        result["status"] = "NOT_APPLICABLE"
        result["reasoning"] = "No changed files relate to this decision"
        return result

    # 3. Check if rejected alternatives appear in added lines
    alternatives = decision.get("alternatives", [])
    found_alts = []
    for alt in alternatives:
        if isinstance(alt, str):
            alt_keywords = extract_keywords(alt)
            for kw in alt_keywords:
                if kw in added_lines:
                    found_alts.append(alt)
                    break
        elif isinstance(alt, dict):
            alt_text = alt.get("option", alt.get("name", ""))
            alt_keywords = extract_keywords(alt_text)
            for kw in alt_keywords:
                if kw in added_lines:
                    found_alts.append(alt_text)
                    break

    if found_alts:
        result["status"] = "DRIFT_MAJOR"
        result["reasoning"] = (
            f"Rejected alternative(s) detected in added code: "
            f"{', '.join(str(a)[:60] for a in found_alts[:3])}"
        )
        return result

    # 4. Check for recommendation keywords
    rec_keywords = extract_keywords(decision.get("recommendation", ""))
    found_rec = any(kw in added_lines for kw in rec_keywords)
    if found_rec:
        result["status"] = "COMPLIANT"
        result["reasoning"] = "Recommendation keywords found in changes"
    else:
        result["status"] = "DRIFT_MINOR"
        result["reasoning"] = (
            f"Related file(s) changed but recommendation not confirmed: "
            f"{', '.join(result['related_files'][:3])}"
        )
    return result


def detect_drift(project: str, task_id: str = None) -> dict:
    """Main API: check all locked decisions against current changes."""
    locked = load_locked_decisions(project)
    if not locked:
        return {"task_id": task_id, "decision_count": 0, "status": "NO_DECISIONS",
                "drifts": [], "results": []}

    base_commit = get_task_base_commit(project, task_id) if task_id else None
    changed_files = get_changed_files(base_commit)

    if not changed_files:
        return {"task_id": task_id, "decision_count": len(locked),
                "status": "NO_CHANGES", "drifts": [], "results": []}

    added_lines = get_added_lines(base_commit)

    results = []
    drifts = []
    for decision in locked:
        check = check_decision(decision, changed_files, added_lines)
        results.append(check)
        if check["status"].startswith("DRIFT"):
            drifts.append(check)

    return {
        "task_id": task_id,
        "decision_count": len(locked),
        "checked": len(results),
        "compliant": sum(1 for r in results if r["status"] == "COMPLIANT"),
        "drifts": drifts,
        "status": "DRIFT_DETECTED" if drifts else "COMPLIANT",
        "results": results,
    }


# -- CLI --

def cmd_check(args):
    """Check decisions for drift."""
    report = detect_drift(args.project, getattr(args, "task", None))

    if report["status"] == "NO_DECISIONS":
        print(f"No locked decisions found for {args.project}.")
        return

    if report["status"] == "NO_CHANGES":
        print(f"No changes detected. {report['decision_count']} decisions loaded.")
        return

    # Print report
    print(f"## Decision Drift Check — {args.project}")
    if report.get("task_id"):
        print(f"Task: {report['task_id']}")
    print(f"Decisions checked: {report['decision_count']}")
    print(f"Status: **{report['status']}**")
    print()

    if report["drifts"]:
        print("### Drifts Detected")
        print()
        for d in report["drifts"]:
            severity = "MAJOR" if d["status"] == "DRIFT_MAJOR" else "MINOR"
            print(f"- **{severity}** {d['decision_id']}: {d['issue'][:80]}")
            print(f"  Recommendation: {d['recommendation'][:80]}")
            print(f"  Finding: {d['reasoning']}")
            print()

    compliant = [r for r in report["results"] if r["status"] == "COMPLIANT"]
    if compliant:
        print("### Compliant")
        for c in compliant:
            print(f"- {c['decision_id']}: {c['issue'][:80]}")

    # Exit code: 1 if MAJOR drift, 0 otherwise
    major = any(d["status"] == "DRIFT_MAJOR" for d in report["drifts"])
    if major:
        sys.exit(1)


def cmd_report(args):
    """Report all decisions and their drift status (no task filter)."""
    report = detect_drift(args.project, None)
    if report["status"] == "NO_DECISIONS":
        print(f"No locked decisions for {args.project}.")
        return

    print(f"## Decision Compliance Report — {args.project}")
    print(f"| Decision | Type | Issue | Status |")
    print(f"|----------|------|-------|--------|")
    for r in report["results"]:
        status_icon = {
            "COMPLIANT": "OK",
            "DRIFT_MAJOR": "DRIFT (MAJOR)",
            "DRIFT_MINOR": "DRIFT (minor)",
            "NOT_APPLICABLE": "n/a",
        }.get(r["status"], r["status"])
        print(f"| {r['decision_id']} | {r['type']} | {r['issue'][:50]} | {status_icon} |")


def main():
    parser = argparse.ArgumentParser(description="Decision Drift Detection")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check decisions for drift")
    p_check.add_argument("project")
    p_check.add_argument("--task", help="Task ID for base commit")
    p_check.set_defaults(func=cmd_check)

    p_report = sub.add_parser("report", help="Report all decision compliance")
    p_report.add_argument("project")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()

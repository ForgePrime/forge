"""Pipeline shared infrastructure — storage, tracing, display, helpers.

All pipeline_* submodules import from here. No pipeline_* module
should import from another pipeline_* module — only from this common base.
"""

import json
import os
import sys
from pathlib import Path

from _compat import configure_encoding
from errors import EntityNotFound, ForgeError
from storage import JSONFileStorage, now_iso

configure_encoding()


# ---------------------------------------------------------------------------
# Debug / Trace
# ---------------------------------------------------------------------------

_DEBUG_CHECKED = None


def _is_debug() -> bool:
    val = os.environ.get("FORGE_DEBUG", "").strip().lower()
    if val:
        return val in ("true", "1", "yes")
    env_path = Path(".env")
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() == "FORGE_DEBUG":
                    return value.strip().strip('"').strip("'").lower() in ("true", "1", "yes")
        except OSError:
            pass
    return False


def _debug_enabled() -> bool:
    global _DEBUG_CHECKED
    if _DEBUG_CHECKED is None:
        _DEBUG_CHECKED = _is_debug()
    return _DEBUG_CHECKED


def _trace(project: str, entry: dict):
    if not _debug_enabled():
        return
    entry["ts"] = now_iso()
    _s = _get_storage()
    trace_path = Path(_s.base_dir) / project / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

_default_storage = None


def _get_storage(storage=None):
    global _default_storage
    if storage is not None:
        return storage
    if _default_storage is None:
        _default_storage = JSONFileStorage()
    return _default_storage


# ---------------------------------------------------------------------------
# Tracker I/O
# ---------------------------------------------------------------------------

def load_tracker(project: str, storage=None) -> dict:
    s = _get_storage(storage)
    if not s.exists(project, 'tracker'):
        raise EntityNotFound(f"No tracker for project '{project}'. Run: init {project} --goal \"...\"")
    return s.load_data(project, 'tracker')


def save_tracker(project: str, tracker: dict, storage=None):
    s = _get_storage(storage)
    s.save_data(project, 'tracker', tracker)


def find_task(tracker: dict, task_id: str) -> dict:
    for task in tracker["tasks"]:
        if task["id"] == task_id:
            return task
    raise EntityNotFound(f"Task '{task_id}' not found.")


def _max_task_num(tasks: list) -> int:
    max_num = 0
    for t in tasks:
        tid = t["id"]
        if tid.startswith("T-") and tid[2:].isdigit():
            max_num = max(max_num, int(tid[2:]))
    return max_num


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

STATUS_ICONS = {
    "TODO": "[ ]",
    "CLAIMING": "[?]",
    "IN_PROGRESS": "[>]",
    "DONE": "[x]",
    "SKIPPED": "[-]",
    "FAILED": "[!]",
}


def print_status(project: str, tracker: dict):
    """Print compact status dashboard."""
    tasks = tracker["tasks"]
    total = len(tasks)
    if total == 0:
        print(f"## {project} -- No tasks yet")
        print(f"Goal: {tracker.get('goal', '(none)')}")
        return

    done = sum(1 for t in tasks if t["status"] == "DONE")
    skipped = sum(1 for t in tasks if t["status"] == "SKIPPED")
    in_progress = [t for t in tasks if t["status"] == "IN_PROGRESS"]
    failed = [t for t in tasks if t["status"] == "FAILED"]
    todo = sum(1 for t in tasks if t["status"] == "TODO")

    print(f"## {project} -- Pipeline Status")
    print(f"Goal: {tracker.get('goal', '(none)')}")
    print(f"")
    parts = [f"Done: {done}/{total}", f"TODO: {todo}"]
    if skipped:
        parts.append(f"Skipped: {skipped}")
    if failed:
        parts.append(f"Failed: {len(failed)}")
    if in_progress:
        parts.append(f"Current: {in_progress[0]['id']}")
    print(f"  {' | '.join(parts)}")

    type_counts = {}
    for t in tasks:
        ttype = t.get("type", "feature")
        type_counts[ttype] = type_counts.get(ttype, 0) + 1
    if len(type_counts) > 1 or "feature" not in type_counts:
        type_parts = [f"{k}: {v}" for k, v in sorted(type_counts.items())]
        print(f"  Types: {' | '.join(type_parts)}")
    print(f"")

    filled = done + skipped
    bar_len = 20
    filled_chars = int(filled / total * bar_len) if total else 0
    bar = "#" * filled_chars + "." * (bar_len - filled_chars)
    print(f"  [{bar}] {filled}/{total}")
    print(f"")

    for task in tasks:
        icon = STATUS_ICONS.get(task["status"], "?")
        ttype = task.get("type", "feature")
        type_label = f" [{ttype}]" if ttype != "feature" else ""
        line = f"  {icon} {task['id']} {task['name']}{type_label}"
        agent_label = f" ({task['agent']})" if task.get("agent") else ""
        if task["status"] == "IN_PROGRESS":
            if task.get("has_subtasks"):
                line += f" <- current{agent_label} [{task.get('subtask_done', 0)}/{task.get('subtask_total', 0)} subtasks]"
            else:
                line += f" <- current{agent_label}"
        elif task["status"] == "CLAIMING":
            line += f" <- claiming{agent_label}"
        elif task["status"] == "FAILED":
            line += f" -- {task.get('failed_reason', '')}"
        print(line)

    # "Where was I?" — resumption context
    active = in_progress[0] if in_progress else None
    if not active:
        done_ids = {t["id"] for t in tasks if t["status"] in ("DONE", "SKIPPED")}
        for t in tasks:
            if t["status"] == "TODO":
                deps = set(t.get("depends_on", []))
                if deps.issubset(done_ids):
                    active = t
                    break

    if active:
        print()
        label = "Current task" if active["status"] == "IN_PROGRESS" else "Next task"
        print(f"  ### {label}: {active['id']} — {active['name']}")
        if active.get("description"):
            print(f"  {active['description'][:120]}")

        ac = active.get("acceptance_criteria", [])
        if ac:
            _s = _get_storage()
            ch_data = _s.load_data(project, 'changes')
            recorded_files = {
                c.get("summary", "").lower()
                for c in ch_data.get("changes", [])
                if c.get("task_id") == active["id"]
            }

            print(f"  Acceptance criteria ({len(ac)}):")
            for criterion in ac:
                if isinstance(criterion, dict):
                    text = criterion.get("text", "")
                    tmpl = criterion.get("from_template")
                    if tmpl:
                        print(f"    - {text} (from {tmpl})")
                    else:
                        print(f"    - {text}")
                else:
                    print(f"    - {criterion}")

        _s = _get_storage()
        ch_data = _s.load_data(project, 'changes')
        task_changes = [c for c in ch_data.get("changes", [])
                       if c.get("task_id") == active["id"]]
        if task_changes:
            print(f"  Changes recorded: {len(task_changes)} files")

    print()
    print_dag(tasks)


def print_dag(tasks: list):
    """Print ASCII dependency graph."""
    if not tasks:
        return

    task_map = {t["id"]: t for t in tasks}
    roots = [t["id"] for t in tasks if not t.get("depends_on")]
    children = {}
    for t in tasks:
        for dep in t.get("depends_on", []):
            children.setdefault(dep, []).append(t["id"])

    if not roots and tasks:
        roots = [tasks[0]["id"]]

    printed = set()

    def _render(tid, prefix="", is_last=True):
        if tid in printed:
            return
        printed.add(tid)
        t = task_map.get(tid)
        if not t:
            return
        icon = STATUS_ICONS.get(t["status"], "?")
        connector = "└── " if is_last else "├── "
        print(f"  {prefix}{connector}{icon} {tid} {t['name']}")
        kids = children.get(tid, [])
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, kid in enumerate(kids):
            _render(kid, child_prefix, i == len(kids) - 1)

    print("```")
    print(f"  {task_map.get(roots[0], {}).get('name', 'project') if roots else 'project'}")
    for i, root in enumerate(roots):
        _render(root, "", i == len(roots) - 1)
    for t in tasks:
        if t["id"] not in printed:
            _render(t["id"], "", True)
    print("```")


def print_task_list(tracker: dict):
    """Print all tasks as MD table."""
    print("| # | ID | Name | Type | Status | Depends On | Blocked By |")
    print("|---|-----|------|------|--------|------------|------------|")
    for i, task in enumerate(tracker["tasks"], 1):
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else "--"
        ttype = task.get("type", "feature")
        blocked = ", ".join(task.get("blocked_by_decisions", [])) or "--"
        icon = STATUS_ICONS.get(task["status"], "?")
        print(f"| {i} | {task['id']} | {task['name']} | {ttype} | {icon} {task['status']} | {deps} | {blocked} |")


def print_task_detail(task: dict):
    """Print full task detail."""
    ttype = task.get("type", "feature")
    if ttype != "feature":
        print(f"**Type**: {ttype}")

    if task.get("description"):
        print(f"**Description**: {task['description']}")
        print(f"")

    if task.get("skill"):
        print(f"**Skill**: `{task['skill']}`")
        print(f"Action: Read the SKILL file and follow its procedure.")
    elif task.get("instruction"):
        print(f"**Instruction**: {task['instruction']}")

    print(f"")
    if task["depends_on"]:
        print(f"**Dependencies**: {', '.join(task['depends_on'])}")

    blocked = task.get("blocked_by_decisions", [])
    if blocked:
        print(f"**Blocked by decisions**: {', '.join(blocked)}")

    k_ids = task.get("knowledge_ids", [])
    if k_ids:
        print(f"**Knowledge**: {', '.join(k_ids)}")

    scopes = task.get("scopes", [])
    if scopes:
        print(f"**Scopes**: {', '.join(scopes)}")

    if task.get("origin"):
        print(f"**Origin**: {task['origin']}")

    if task.get("produces"):
        print(f"**Produces**: {json.dumps(task['produces'], indent=2)}")

    # Alignment
    alignment = task.get("alignment")
    if alignment:
        print(f"")
        print(f"### Task Alignment")
        if alignment.get("goal"):
            print(f"**Goal**: {alignment['goal']}")
        bounds = alignment.get("boundaries", {})
        if bounds.get("must"):
            print(f"**Must**: {', '.join(bounds['must']) if isinstance(bounds['must'], list) else bounds['must']}")
        if bounds.get("must_not"):
            print(f"**Must NOT**: {', '.join(bounds['must_not']) if isinstance(bounds['must_not'], list) else bounds['must_not']}")
        if bounds.get("not_in_scope"):
            print(f"**Not in scope**: {', '.join(bounds['not_in_scope']) if isinstance(bounds['not_in_scope'], list) else bounds['not_in_scope']}")
        if alignment.get("success"):
            print(f"**Success**: {alignment['success']}")

    # Exclusions
    exclusions = task.get("exclusions", [])
    if exclusions:
        print(f"")
        print(f"### Exclusions")
        for exc in exclusions:
            print(f"- DO NOT: {exc}")

    # Acceptance criteria
    ac = task.get("acceptance_criteria", [])
    if ac:
        print(f"")
        print(f"### Acceptance Criteria ({len(ac)})")
        for criterion in ac:
            if isinstance(criterion, dict):
                text = criterion.get("text", "")
                ver = criterion.get("verification", "manual")
                tmpl = criterion.get("from_template")
                if tmpl:
                    print(f"  - [{ver}] {text} (from {tmpl})")
                else:
                    print(f"  - [{ver}] {text}")
                if ver == "test" and criterion.get("test_path"):
                    print(f"    Test: `{criterion['test_path']}`")
                elif ver == "command" and criterion.get("command"):
                    print(f"    Command: `{criterion['command']}`")
            else:
                print(f"  - {criterion}")

"""Pipeline execution — next, begin, complete, fail, skip."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import (
    _get_storage, _trace, load_tracker, save_tracker, find_task,
    print_status, print_task_detail, STATUS_ICONS,
    get_project_dir,
)
from pipeline_git import (
    _get_current_commit, _auto_record_changes,
    _apply_git_workflow_start, _apply_git_workflow_complete,
    _count_diff_files,
)
from storage import JSONFileStorage, load_json_data, now_iso, tracker_lock
import gates as _gates_mod
from errors import ForgeError, ValidationError, EntityNotFound, PreconditionError, GateFailure, ConflictError
from models import Task

CLAIM_WAIT_SECONDS = 1.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_active_ids(tracker: dict) -> set:
    """IDs of tasks that are CLAIMING or IN_PROGRESS."""
    return {t["id"] for t in tracker["tasks"]
            if t["status"] in ("CLAIMING", "IN_PROGRESS")}


def _has_conflict(task: dict, active_ids: set) -> bool:
    """Check if task conflicts with any active task."""
    conflicts = set(task.get("conflicts_with", []))
    return bool(conflicts & active_ids)


def _load_open_decision_ids(project: str) -> set:
    """Load set of OPEN decision IDs from decisions.json."""
    storage = _get_storage()
    data = storage.load_data(project, 'decisions')
    return {d["id"] for d in data.get("decisions", []) if d.get("status") == "OPEN"}


def _blocked_by_open_decisions(task: dict, open_decision_ids: set) -> list:
    """Return list of OPEN decision IDs that block this task."""
    required = set(task.get("blocked_by_decisions", []))
    if not required:
        return []
    return sorted(required & open_decision_ids)


# ---------------------------------------------------------------------------
# Claim protocol
# ---------------------------------------------------------------------------

def _claim_with_retry(args, candidate, agent, max_retries=5):
    """Two-phase claim protocol with retry limit for multi-agent mode."""
    for attempt in range(max_retries):
        tracker = load_tracker(args.project)
        task = find_task(tracker, candidate["id"])

        # Phase 1: CLAIMING
        task["status"] = "CLAIMING"
        task["agent"] = agent
        task["claimed_at"] = now_iso()
        save_tracker(args.project, tracker)

        # Wait
        time.sleep(CLAIM_WAIT_SECONDS)

        # Phase 2: Verify claim
        tracker = load_tracker(args.project)
        task = find_task(tracker, candidate["id"])

        if task["status"] == "CLAIMING" and task.get("agent") == agent:
            # Claim won — promote to IN_PROGRESS
            task["status"] = "IN_PROGRESS"
            task["started_at"] = now_iso()
            task["started_at_commit"] = _get_current_commit()

            # Git workflow: create branch + optional worktree
            git_result = _apply_git_workflow_start(args.project, tracker, task)
            if git_result:
                task.update(git_result)

            save_tracker(args.project, tracker)

            print(f"## Next task: {task['id']} — {task['name']}")
            print(f"Agent: {agent}")
            print(f"Status: TODO -> CLAIMING -> **IN_PROGRESS**")
            if task.get("branch"):
                print(f"Branch: `{task['branch']}`")
            if task.get("worktree_path"):
                print(f"Worktree: `{task['worktree_path']}`")
            print()
            print_task_detail(task)
            return task

        # Claim lost — find next candidate
        print(f"  Claim conflict on {candidate['id']} (attempt {attempt + 1}/{max_retries})",
              file=sys.stderr)

        done_ids = {t["id"] for t in tracker["tasks"]
                    if t["status"] in ("DONE", "SKIPPED")}
        active_ids = _get_active_ids(tracker)
        open_decisions = _load_open_decision_ids(args.project)

        candidate = None
        for t in tracker["tasks"]:
            if t["status"] != "TODO":
                continue
            if not all(dep in done_ids for dep in t["depends_on"]):
                continue
            if _has_conflict(t, active_ids):
                continue
            if _blocked_by_open_decisions(t, open_decisions):
                continue
            candidate = t
            break

        if not candidate:
            print(f"No available tasks after claim conflict.", file=sys.stderr)
            return

    raise ConflictError(f"All tasks contended after {max_retries} attempts. Try again later.")


# ---------------------------------------------------------------------------
# cmd_next
# ---------------------------------------------------------------------------

def cmd_next(args):
    """Get next TODO task with two-phase claim for multi-agent safety.

    Protocol:
    1. Agent writes CLAIMING + agent_name to task
    2. Agent waits CLAIM_WAIT_SECONDS
    3. Agent re-reads tracker — if still own name, set IN_PROGRESS
    4. If another agent overwrote, back off and try next task

    This detects concurrent claims without locks or databases.
    """
    # Lazy import to avoid circular dependency (pipeline.py still owns _next_subtask)
    from pipeline_tasks import _next_subtask

    agent = getattr(args, "agent", None) or "default"
    tracker = load_tracker(args.project)

    if not tracker["tasks"]:
        print(f"## No tasks in project '{args.project}'")
        print(f"\nAdd tasks with `add-tasks` or run `/plan {args.project}`")
        return None

    done_ids = {t["id"] for t in tracker["tasks"]
                if t["status"] in ("DONE", "SKIPPED")}
    active_ids = _get_active_ids(tracker)

    # Check if THIS agent already has a task IN_PROGRESS
    for task in tracker["tasks"]:
        if task["status"] == "IN_PROGRESS" and task.get("agent") == agent:
            if task.get("has_subtasks"):
                _next_subtask(args.project, tracker, task)
                return task
            print(f"## Current task: {task['id']} — {task['name']}")
            print(f"Agent: {agent}")
            print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
            print()
            print_task_detail(task)
            return task

    # Check if ANY task is IN_PROGRESS without an agent (single-agent compat)
    for task in tracker["tasks"]:
        if task["status"] == "IN_PROGRESS" and not task.get("agent"):
            if task.get("has_subtasks"):
                _next_subtask(args.project, tracker, task)
                return task
            print(f"## Current task: {task['id']} — {task['name']}")
            print(f"Status: **IN_PROGRESS** (started: {task['started_at']})")
            print()
            print_task_detail(task)
            return task

    # Find next TODO with deps met, no conflicts, and no blocking decisions
    objective_filter = getattr(args, "objective", None)
    open_decisions = _load_open_decision_ids(args.project)
    candidate = None
    blocked_by_dec_tasks = []
    for task in tracker["tasks"]:
        if task["status"] != "TODO":
            continue
        if objective_filter and not task.get("origin", "").startswith(objective_filter):
            continue
        deps_met = all(dep in done_ids for dep in task["depends_on"])
        if not deps_met:
            continue
        if _has_conflict(task, active_ids):
            continue
        blocking_decs = _blocked_by_open_decisions(task, open_decisions)
        if blocking_decs:
            blocked_by_dec_tasks.append((task, blocking_decs))
            continue
        candidate = task
        break

    if not candidate:
        # Check terminal states
        all_done = all(t["status"] in ("DONE", "SKIPPED") for t in tracker["tasks"])
        if all_done:
            print(f"## Project complete: {args.project}")
            print()
            print(f"All {len(tracker['tasks'])} tasks finished.")
            print_status(args.project, tracker)
        else:
            failed = [t for t in tracker["tasks"] if t["status"] == "FAILED"]
            blocked_by_conflict = any(
                t["status"] == "TODO"
                and all(dep in done_ids for dep in t["depends_on"])
                and _has_conflict(t, active_ids)
                for t in tracker["tasks"]
            )
            if failed:
                print(f"## Project blocked: {args.project}")
                print()
                for t in failed:
                    print(f"  FAILED: {t['id']} {t['name']}: {t['failed_reason']}")
            elif blocked_by_dec_tasks:
                print(f"## Tasks blocked by OPEN decisions")
                print()
                for t, decs in blocked_by_dec_tasks:
                    print(f"  {t['id']} {t['name']} — blocked by: {', '.join(decs)}")
                print()
                print(f"Resolve with `/decide` or: python -m core.decisions update {args.project} --data '[...]'")
            elif blocked_by_conflict:
                print(f"## All available tasks conflict with active tasks")
                print(f"Agent: {agent}")
                print(f"Active: {', '.join(active_ids)}")
                print(f"Wait for active tasks to complete.")
            else:
                print(f"## No tasks available (dependencies not met)")
                print_status(args.project, tracker)
        return None

    # --- Check if other agents are active ---
    other_agents = {t.get("agent") for t in tracker["tasks"]
                    if t["status"] in ("CLAIMING", "IN_PROGRESS")
                    and t["id"] != candidate["id"]
                    and t.get("agent") and t.get("agent") != agent}

    if not other_agents:
        # Single agent — skip claim protocol, go directly to IN_PROGRESS
        candidate["status"] = "IN_PROGRESS"
        candidate["agent"] = agent
        candidate["started_at"] = now_iso()
        candidate["started_at_commit"] = _get_current_commit()

        # Git workflow: create branch + optional worktree
        git_result = _apply_git_workflow_start(args.project, tracker, candidate)
        if git_result:
            candidate.update(git_result)

        save_tracker(args.project, tracker)

        print(f"## Next task: {candidate['id']} — {candidate['name']}")
        print(f"Agent: {agent}")
        print(f"Status: TODO -> **IN_PROGRESS**")
        if candidate.get("branch"):
            print(f"Branch: `{candidate['branch']}`")
        if candidate.get("worktree_path"):
            print(f"Worktree: `{candidate['worktree_path']}`")
        print()
        print_task_detail(candidate)
        _trace(args.project, {"event": "next.claimed", "task": candidate["id"],
               "name": candidate.get("name"), "type": candidate.get("type"),
               "agent": agent, "started_at_commit": candidate.get("started_at_commit"),
               "branch": candidate.get("branch"),
               "depends_on": candidate.get("depends_on", []),
               "origin": candidate.get("origin"),
               "scopes": candidate.get("scopes", []),
               "ac_count": len(candidate.get("acceptance_criteria", [])),
               "exclusions_count": len(candidate.get("exclusions", [])),
               "has_alignment": bool(candidate.get("alignment")),
               "has_produces": bool(candidate.get("produces")),
               "has_uses_from_deps": bool(candidate.get("uses_from_dependencies"))})
        return candidate
    else:
        # Multi-agent — use two-phase claim protocol
        return _claim_with_retry(args, candidate, agent, max_retries=5)


# ---------------------------------------------------------------------------
# cmd_begin
# ---------------------------------------------------------------------------

def cmd_begin(args):
    """Combined next + context: claim task and show full execution context.

    Calls cmd_next to claim/resume a task, then immediately prints
    the full context (dependencies, guidelines, knowledge, risks, etc.).
    Equivalent to running ``pipeline next`` followed by ``pipeline context``,
    but in a single invocation.
    """
    # Lazy import — cmd_context still lives in pipeline.py until pipeline_context.py is extracted
    from pipeline_context import cmd_context

    task = cmd_next(args)

    if not task or task.get("has_subtasks"):
        return

    # Contract C5: verify objective still ACTIVE if task has origin
    origin = task.get("origin", "")
    if origin and origin.startswith("O-"):
        _s_begin = _get_storage()
        if _s_begin.exists(args.project, 'objectives'):
            obj_data = _s_begin.load_data(args.project, 'objectives')
            for obj in obj_data.get("objectives", []):
                if obj["id"] == origin:
                    if obj.get("status") == "ACHIEVED":
                        print(f"\n**WARNING**: Task {task['id']} targets objective {origin} "
                              f"which is already ACHIEVED. Verify this task is still needed.\n",
                              file=sys.stderr)
                    break

    print()
    print("---")
    print()

    class _CtxArgs:
        pass
    ctx_args = _CtxArgs()
    ctx_args.project = args.project
    ctx_args.task_id = task["id"]
    ctx_args.lean = getattr(args, "lean", False)
    cmd_context(ctx_args)

    # Trace begin with context summary
    _s = _get_storage()
    _ctx_summary = {}
    if _s.exists(args.project, 'guidelines'):
        _g = _s.load_data(args.project, 'guidelines')
        _ctx_summary["guidelines"] = len([g for g in _g.get("guidelines", []) if g.get("status") == "ACTIVE"])
    if _s.exists(args.project, 'knowledge'):
        _k = _s.load_data(args.project, 'knowledge')
        _ctx_summary["knowledge"] = len([k for k in _k.get("knowledge", []) if k.get("status") in ("ACTIVE", "DRAFT")])
    if _s.exists(args.project, 'decisions'):
        _d = _s.load_data(args.project, 'decisions')
        _ctx_summary["decisions_open"] = len([d for d in _d.get("decisions", []) if d.get("status") == "OPEN"])
    _ctx_summary["ac_count"] = len(task.get("acceptance_criteria", []))
    _ctx_summary["scopes"] = task.get("scopes", [])
    _ctx_summary["lean"] = getattr(args, "lean", False)
    _trace(args.project, {
        "cmd": "begin", "task": task["id"], "name": task.get("name"),
        "type": task.get("type"), "context_loaded": _ctx_summary,
    })


# ---------------------------------------------------------------------------
# AC verification
# ---------------------------------------------------------------------------

def _verify_acceptance_criteria(task, project=None):
    """Mechanically verify structured acceptance criteria.

    AC can be:
    - Plain string: treated as verification='manual' (needs --ac-reasoning)
    - Structured dict: {text, verification: 'test'|'command'|'manual', test_path?, command?}

    Returns (results, has_mechanical) where:
    - results: list of {text, verification, passed, output} for mechanical AC
    - has_mechanical: True if any AC has test/command verification
    """
    import subprocess as _sp

    if isinstance(task, dict):
        task = Task.from_dict(task)
    ac_list = task.acceptance_criteria
    results = []
    has_mechanical = False
    task_id = task.id or "?"

    for ac in ac_list:
        if isinstance(ac, str):
            continue  # Plain string = manual, handled by --ac-reasoning

        if not isinstance(ac, dict):
            continue

        verification = ac.get("verification", "manual")
        text = ac.get("text", str(ac))

        if verification == "manual":
            continue

        has_mechanical = True

        if verification == "test":
            test_path = ac.get("test_path", "")
            if not test_path:
                results.append({"text": text, "verification": "test",
                                "passed": False, "output": "No test_path specified"})
                continue
            cmd_str = f"pytest {test_path} -x -q"
            if project:
                _trace(project, {"event": "ac.run_test", "task": task_id,
                       "ac_text": text, "command": cmd_str, "test_path": test_path})
            try:
                _t = time.time()
                result = _sp.run(
                    cmd_str,
                    shell=True, capture_output=True, text=True,
                    encoding="utf-8", timeout=120
                )
                _dur = int((time.time() - _t) * 1000)
                output = (result.stdout + result.stderr)[:500]
                passed = result.returncode == 0
                results.append({"text": text, "verification": "test",
                                "passed": passed, "output": output})
                if project:
                    _trace(project, {"event": "ac.test_result", "task": task_id,
                           "ac_text": text, "passed": passed, "returncode": result.returncode,
                           "duration_ms": _dur, "output": output[:300]})
            except _sp.TimeoutExpired:
                results.append({"text": text, "verification": "test",
                                "passed": False, "output": "Test timed out (120s)"})
                if project:
                    _trace(project, {"event": "ac.test_timeout", "task": task_id,
                           "ac_text": text, "timeout": 120})

        elif verification == "command":
            command = ac.get("command", "")
            if not command:
                results.append({"text": text, "verification": "command",
                                "passed": False, "output": "No command specified"})
                continue
            if project:
                _trace(project, {"event": "ac.run_command", "task": task_id,
                       "ac_text": text, "command": command})
            try:
                _t = time.time()
                result = _sp.run(
                    command, shell=True, capture_output=True, text=True,
                    encoding="utf-8", timeout=120
                )
                _dur = int((time.time() - _t) * 1000)
                output = (result.stdout + result.stderr)[:500]
                passed = result.returncode == 0
                results.append({"text": text, "verification": "command",
                                "passed": passed, "output": output})
                if project:
                    _trace(project, {"event": "ac.command_result", "task": task_id,
                           "ac_text": text, "command": command, "passed": passed,
                           "returncode": result.returncode, "duration_ms": _dur,
                           "output": output[:300]})
            except _sp.TimeoutExpired:
                results.append({"text": text, "verification": "command",
                                "passed": False, "output": "Command timed out (120s)"})
                if project:
                    _trace(project, {"event": "ac.command_timeout", "task": task_id,
                           "ac_text": text, "command": command, "timeout": 120})

    return results, has_mechanical


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def _check_gates_before_complete(project, task_id, task, tracker):
    """Mechanically enforce gate checks before task completion.

    - If gates not configured: pass (nothing to check)
    - If gate_results missing: auto-run gates
    - If required gates failed: exit(1)
    """
    if isinstance(task, dict):
        task = Task.from_dict(task)

    gates_config = tracker.get("gates", [])
    if not gates_config:
        _trace(project, {"event": "gates.none_configured", "task": task.id})
        return  # No gates configured

    # Auto-run gates if not yet run
    gate_results = task.gate_results or {}
    if not gate_results:
        _trace(project, {"event": "gates.auto_run", "task": task.id,
               "gates": [{"name": g["name"], "command": g["command"],
                          "required": g.get("required", True)} for g in gates_config]})
        print(f"  Running gates before completion...")
        _ns = type("NS", (), {"project": project, "task": task.id})()
        all_passed = _gates_mod.cmd_check(_ns)
        # Reload tracker since cmd_check may have saved results
        tracker_reloaded = load_tracker(project)
        for t in tracker_reloaded.get("tasks", []):
            if t["id"] == task.id:
                task = Task.from_dict(t)
                break
        gate_results = task.gate_results or {}

    if not gate_results.get("all_passed", True):
        required_gates = {gc["name"] for gc in gates_config if gc.get("required", True)}
        failed = [g["name"] for g in gate_results.get("results", [])
                  if not g.get("passed")]
        required_failed = [name for name in failed if name in required_gates]
        _trace(project, {"event": "gates.evaluation", "task": task.id,
               "all_passed": False, "failed": failed,
               "required_failed": required_failed,
               "results": gate_results.get("results", [])})
        if required_failed:
            raise GateFailure(f"Required gates failed: {', '.join(required_failed)}. "
                  f"Fix issues and re-run gates.")
        else:
            print(f"  Advisory gates failed: {', '.join(failed)} (non-blocking).")


# ---------------------------------------------------------------------------
# Ceremony level
# ---------------------------------------------------------------------------

def _determine_ceremony_level(task, diff_file_count=0):
    """Auto-detect ceremony level based on task type and complexity.

    Returns: 'LIGHT', 'STANDARD', or 'FULL'
    - LIGHT: chore/investigation/small bug — reasoning required, deferred optional
    - STANDARD: feature with <= 3 AC — reasoning + AC reasoning + deferred required
    - FULL: everything else — all checks required
    """
    if isinstance(task, dict):
        task = Task.from_dict(task)
    task_type = task.type
    ac_count = len(task.acceptance_criteria)

    if task_type in ("chore", "investigation"):
        return "LIGHT"
    if task_type == "bug" and diff_file_count <= 3:
        return "LIGHT"
    if task_type == "feature" and ac_count <= 3:
        return "STANDARD"
    return "FULL"


def _check_implementation_fidelity(task: dict, project: str, base_commit: str, cwd: str = None):
    """Fidelity Chain: check if changed files contain key terms from source requirements.

    Prints traceability matrix. WARNING-level only.
    """
    import subprocess as _sp
    from pipeline_context import _extract_key_terms, _term_overlap

    _s = _get_storage()
    if not _s.exists(project, 'knowledge'):
        return

    # Collect requirement IDs
    req_ids = set()
    for sr in task.get("source_requirements", []):
        if sr.get("knowledge_id"):
            req_ids.add(sr["knowledge_id"])
    for kid in task.get("knowledge_ids", []):
        req_ids.add(kid)

    if not req_ids:
        return

    k_data = _s.load_data(project, 'knowledge')
    k_by_id = {k["id"]: k for k in k_data.get("knowledge", [])}

    requirements = [(k_id, k_by_id[k_id]) for k_id in req_ids
                    if k_id in k_by_id and k_by_id[k_id].get("category") == "requirement"]

    if not requirements:
        return

    # Get diff content
    diff_text = ""
    if base_commit:
        try:
            result = _sp.run(
                ["git", "diff", base_commit, "HEAD"],
                capture_output=True, text=True, timeout=10,
                cwd=cwd
            )
            diff_text = result.stdout
        except Exception as e:
            print(f"  WARNING: Fidelity matrix skipped — git diff failed: {e}", file=sys.stderr)
            return

    if not diff_text:
        return

    diff_terms = _extract_key_terms(diff_text, min_length=4)

    print(f"\n  Fidelity Matrix ({len(requirements)} requirements):")
    has_gaps = False
    for k_id, k_obj in requirements:
        req_terms = _extract_key_terms(k_obj.get("content", ""))
        matched, missing, ratio = _term_overlap(req_terms, diff_terms)

        if ratio >= 0.3 or len(missing) < 2:
            status_label = "OK"
        else:
            status_label = "GAP"
            has_gaps = True

        print(f"    [{status_label}] {k_id}: {k_obj.get('title', '')[:40]} "
              f"({len(matched)}/{len(req_terms)} terms)")
        if status_label == "GAP":
            print(f"           Missing: {', '.join(sorted(missing)[:5])}")

    if has_gaps:
        print(f"  FIDELITY_WARNING: Some requirements have low term overlap with changes. "
              f"Verify implementation matches source requirements.", file=sys.stderr)

    _trace(project, {"event": "complete.fidelity_matrix", "task": task.get("id"),
           "requirements_checked": len(requirements), "has_gaps": has_gaps})


# ---------------------------------------------------------------------------
# cmd_complete
# ---------------------------------------------------------------------------

def cmd_complete(args):
    """Mark task as DONE."""
    # Lazy imports for functions still in pipeline.py
    from pipeline_context import _objective_kr_pct

    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)
    _t0 = time.time()
    agent = getattr(args, "agent", None)
    reasoning = getattr(args, "reasoning", None) or ""

    _trace(args.project, {"event": "complete.start", "task": args.task_id,
           "name": task.get("name"), "type": task.get("type"),
           "agent": agent, "reasoning_length": len(reasoning),
           "ac_reasoning_length": len(getattr(args, "ac_reasoning", None) or ""),
           "deferred_provided": bool(getattr(args, "deferred", None)),
           "started_at_commit": task.get("started_at_commit"),
           "task_status": task.get("status")})

    # Determine ceremony level
    base_commit = task.get("started_at_commit", "")
    git_cwd = task.get("worktree_path")
    if git_cwd and not os.path.isdir(git_cwd):
        git_cwd = None
    diff_count = _count_diff_files(base_commit, cwd=git_cwd)
    ceremony = _determine_ceremony_level(task, diff_count)
    print(f"  Ceremony level: {ceremony} ({task.get('type', 'feature')}, {diff_count} files changed)")

    _trace(args.project, {"event": "complete.ceremony", "task": args.task_id,
           "ceremony": ceremony, "task_type": task.get("type"),
           "diff_count": diff_count, "ac_count": len(task.get("acceptance_criteria", []))})

    # Verify agent ownership if task was claimed
    if task.get("agent") and agent and task["agent"] != agent:
        print(f"WARNING: Task {args.task_id} is owned by agent '{task['agent']}', "
              f"not '{agent}'. Completing anyway.", file=sys.stderr)
        _trace(args.project, {"event": "complete.agent_mismatch", "task": args.task_id,
               "expected": task["agent"], "actual": agent})

    # Check blocked_by_decisions are resolved
    open_decisions = _load_open_decision_ids(args.project)
    blocking = _blocked_by_open_decisions(task, open_decisions)
    _trace(args.project, {"event": "complete.check_decisions", "task": args.task_id,
           "open_decisions": list(open_decisions)[:20], "blocking": list(blocking),
           "result": "PASS" if not blocking else "FAIL"})
    if blocking:
        raise PreconditionError(f"Task {args.task_id} has OPEN blocking decisions: "
              f"{', '.join(blocking)}. Close them first.")

    # Check reasoning (required for LIGHT, STANDARD, FULL)
    _reasoning_required = ceremony not in ("MINIMAL",) and not reasoning.strip()
    _trace(args.project, {"event": "complete.check_reasoning", "task": args.task_id,
           "required": ceremony not in ("MINIMAL",), "provided": bool(reasoning.strip()),
           "length": len(reasoning),
           "result": "FAIL" if _reasoning_required else "PASS"})
    if _reasoning_required:
        raise PreconditionError(f"--reasoning is required for {ceremony} ceremony level.")

    # Auto-record changes from git before checking
    if base_commit:
        auto_count = _auto_record_changes(args.project, args.task_id, base_commit,
                                           reasoning, cwd=git_cwd)
        _trace(args.project, {"event": "complete.auto_record_changes", "task": args.task_id,
               "base_commit": base_commit, "changes_recorded": auto_count})
        if auto_count:
            print(f"  Auto-recorded {auto_count} change(s) from git.")

    # Check that changes were recorded for this task (skip for MINIMAL/LIGHT)
    if ceremony not in ("MINIMAL", "LIGHT"):
        storage = _get_storage()
        changes_data = storage.load_data(args.project, 'changes')
        task_changes = [c for c in changes_data.get("changes", [])
                        if c.get("task_id") == args.task_id]
        _trace(args.project, {"event": "complete.check_changes", "task": args.task_id,
               "changes_found": len(task_changes),
               "files": [c.get("file") for c in task_changes][:20],
               "result": "PASS" if task_changes else "FAIL"})
        if not task_changes:
            raise PreconditionError(f"No changes recorded for {args.task_id}.")

    # Check that gates passed (mechanical enforcement)
    _trace(args.project, {"event": "complete.gates_start", "task": args.task_id,
           "gates_configured": bool(tracker.get("gates")),
           "gate_count": len(tracker.get("gates", []))})
    _check_gates_before_complete(args.project, args.task_id, task, tracker)
    _trace(args.project, {"event": "complete.gates_done", "task": args.task_id,
           "gate_results": task.get("gate_results")})

    # --- Mechanical AC verification: ALWAYS runs regardless of ceremony level ---
    ac = task.get("acceptance_criteria", [])
    _trace(args.project, {"event": "complete.ac_start", "task": args.task_id,
           "ac_total": len(ac),
           "ac_items": [{"text": (c if isinstance(c, str) else c.get("text", "")),
                         "type": "manual" if isinstance(c, str) else c.get("verification", "manual")}
                        for c in ac]})
    if ac:
        ac_results, has_mechanical = _verify_acceptance_criteria(task, project=args.project)
        if has_mechanical:
            failed_ac = [r for r in ac_results if not r["passed"]]
            _trace(args.project, {"event": "complete.ac_mechanical", "task": args.task_id,
                   "results": [{"text": r["text"], "verification": r["verification"],
                                "passed": r["passed"], "output": r.get("output", "")[:200]}
                               for r in ac_results]})
            if ac_results:
                print(f"  AC Verification ({len(ac_results)} mechanical):")
                for r in ac_results:
                    status = "PASS" if r["passed"] else "FAIL"
                    print(f"    [{status}] {r['text']} ({r['verification']})")
                    if not r["passed"]:
                        for line in r["output"].split("\n")[:3]:
                            if line.strip():
                                print(f"           {line.strip()}")
            if failed_ac:
                _trace(args.project, {"event": "complete.ac_mechanical_FAIL", "task": args.task_id,
                       "failed": [r["text"] for r in failed_ac]})
                raise GateFailure(f"{len(failed_ac)} mechanical AC verification(s) failed. "
                      f"Fix and retry.")
            task["ac_verification_results"] = ac_results

        # AC → KR bridge: extract kr_link results (Contract C6 — validate references)
        kr_updates_from_ac = {}
        # Pre-load valid KR refs for validation
        _valid_kr_refs = set()
        _s_kr = _get_storage()
        if _s_kr.exists(args.project, 'objectives'):
            _obj_kr_data = _s_kr.load_data(args.project, 'objectives')
            for _obj in _obj_kr_data.get("objectives", []):
                for _kr in _obj.get("key_results", []):
                    _valid_kr_refs.add(f"{_obj['id']}/{_kr['id']}")

        for ac_item in ac:
            if not isinstance(ac_item, dict) or not ac_item.get("kr_link"):
                continue
            kr_ref = ac_item["kr_link"]  # e.g. "O-001/KR-1"
            if _valid_kr_refs and kr_ref not in _valid_kr_refs:
                print(f"  **WARNING**: AC kr_link '{kr_ref}' does not reference a valid KR. "
                      f"Valid refs: {', '.join(sorted(_valid_kr_refs)[:5])}...", file=sys.stderr)
            ac_text = ac_item.get("text", "")
            # Find matching result
            matched = next((r for r in ac_results if r.get("text") == ac_text), None)
            if matched and matched.get("passed"):
                output = matched.get("output", "").strip()
                try:
                    value = float(output.split("\n")[0].strip())
                    kr_updates_from_ac[kr_ref] = value
                except (ValueError, IndexError):
                    kr_updates_from_ac[kr_ref] = True  # boolean pass
        if kr_updates_from_ac:
            task["kr_updates_from_ac"] = kr_updates_from_ac
            _trace(args.project, {"event": "complete.ac_kr_bridge",
                   "task": args.task_id, "kr_updates": kr_updates_from_ac})

    # --- Manual AC evidence: required for STANDARD/FULL ceremony ---
    if ceremony not in ("MINIMAL", "LIGHT") and ac:
        manual_ac = [c for c in ac if isinstance(c, str) or
                     (isinstance(c, dict) and c.get("verification", "manual") == "manual")]

        # Try structured --ac-evidence first, fall back to --ac-reasoning
        ac_evidence_raw = getattr(args, "ac_evidence", None)
        ac_reasoning = getattr(args, "ac_reasoning", None)

        _trace(args.project, {"event": "complete.ac_manual_check", "task": args.task_id,
               "manual_ac_count": len(manual_ac), "ceremony": ceremony,
               "ac_evidence_provided": bool(ac_evidence_raw),
               "ac_reasoning_provided": bool(ac_reasoning)})

        if manual_ac:
            if ac_evidence_raw:
                # Structured per-AC evidence (preferred)
                try:
                    ac_evidence = load_json_data(ac_evidence_raw)
                except Exception:
                    raise ValidationError("--ac-evidence must be valid JSON array")
                if not isinstance(ac_evidence, list):
                    ac_evidence = [ac_evidence]

                # Validate: every manual AC must have evidence
                evidence_by_index = {e.get("ac_index", -1): e for e in ac_evidence}
                missing_evidence = []
                for i, criterion in enumerate(ac):
                    is_manual = isinstance(criterion, str) or (
                        isinstance(criterion, dict) and criterion.get("verification", "manual") == "manual")
                    if not is_manual:
                        continue  # mechanical AC verified by _verify_acceptance_criteria
                    ev = evidence_by_index.get(i)
                    if not ev:
                        text = criterion if isinstance(criterion, str) else criterion.get("text", "?")
                        missing_evidence.append(f"  AC {i}: {text[:60]} — no evidence provided")
                    elif not ev.get("evidence") or len(str(ev["evidence"]).strip()) < 20:
                        text = criterion if isinstance(criterion, str) else criterion.get("text", "?")
                        missing_evidence.append(f"  AC {i}: {text[:60]} — evidence too short (min 20 chars)")
                    elif ev.get("verdict") not in ("PASS", "FAIL"):
                        text = criterion if isinstance(criterion, str) else criterion.get("text", "?")
                        missing_evidence.append(f"  AC {i}: {text[:60]} — verdict must be PASS or FAIL")

                if missing_evidence:
                    raise ValidationError(
                        f"AC evidence incomplete:\n" + "\n".join(missing_evidence) +
                        f"\n\nProvide --ac-evidence with entry for each manual AC: "
                        f"[{{\"ac_index\": 0, \"verdict\": \"PASS\", \"evidence\": \"concrete proof\"}}]"
                    )

                failed = [e for e in ac_evidence if e.get("verdict") == "FAIL"]
                if failed:
                    details = "\n".join(f"  AC {e['ac_index']}: {e.get('evidence', '')[:80]}" for e in failed)
                    raise GateFailure(f"{len(failed)} AC marked FAIL:\n{details}")

                task["ac_evidence"] = ac_evidence
                _trace(args.project, {"event": "complete.ac_evidence", "task": args.task_id,
                       "evidence_count": len(ac_evidence),
                       "all_pass": all(e.get("verdict") == "PASS" for e in ac_evidence)})

            elif ac_reasoning:
                # Legacy: single string reasoning (backward compat)
                if len(ac_reasoning.strip()) < 50:
                    raise ValidationError(f"--ac-reasoning too short ({len(ac_reasoning.strip())} chars). "
                          f"Minimum 50 characters. Use --ac-evidence for structured per-AC proof.")
                task["ac_reasoning"] = ac_reasoning
                ac_warnings = _validate_ac_reasoning(ac_reasoning, ac)
                _trace(args.project, {"event": "complete.ac_reasoning_validation", "task": args.task_id,
                       "reasoning_text": ac_reasoning[:500], "issues": ac_warnings,
                       "result": "PASS" if not ac_warnings else "FAIL"})
                if ac_warnings:
                    issues = "\n".join(ac_warnings)
                    raise ValidationError(
                        f"**AC REASONING ISSUES** ({len(ac_warnings)}):\n{issues}\n"
                        f"Each criterion needs evidence: 'AC N: [criterion] — PASS: [concrete proof]'"
                    )
            else:
                # Neither provided
                criteria_list = "\n".join(
                    f"    {i}. {criterion if isinstance(criterion, str) else criterion.get('text', str(criterion))}"
                    for i, criterion in enumerate(manual_ac, 1)
                )
                raise ValidationError(
                    f"Task {args.task_id} has {len(manual_ac)} manual AC but no evidence.\n"
                    f"  Manual criteria:\n{criteria_list}\n"
                    f"  Provide --ac-evidence '[{{\"ac_index\": 0, \"verdict\": \"PASS\", \"evidence\": \"...\"}}]'\n"
                    f"  Or legacy: --ac-reasoning 'AC 1: ... — PASS: concrete proof'"
                )

    # Fidelity Chain: implementation traceability
    base_commit = task.get("started_at_commit", "")
    git_cwd = get_project_dir(args.project)
    _check_implementation_fidelity(task, args.project, base_commit, cwd=git_cwd)

    # Feature Registry: register what this task produced
    try:
        import subprocess as _sp_reg
        diff_for_registry = ""
        if base_commit and git_cwd:
            r = _sp_reg.run(["git", "diff", base_commit, "HEAD"],
                           capture_output=True, text=True, timeout=10, cwd=git_cwd)
            diff_for_registry = r.stdout or ""
        from feature_registry import register_feature
        register_feature(args.project, task, diff_for_registry)
    except Exception as e:
        print(f"  WARNING: Feature registry failed: {e}", file=sys.stderr)
        _trace(args.project, {"event": "feature_registry.error", "task": task.get("id"), "error": str(e)})

    # Process deferred items — auto-create OPEN decisions
    # Required for STANDARD/FULL: agent must explicitly state what's covered vs deferred
    deferred_raw = getattr(args, "deferred", None)
    has_ac = bool(task.get("acceptance_criteria"))
    if not deferred_raw and ceremony in ("STANDARD", "FULL") and has_ac:
        raise PreconditionError(f"--deferred required for {ceremony} ceremony with acceptance criteria. "
              f"Pass --deferred '[]' if all source requirements are covered, "
              f"or list deferred items.")
    if deferred_raw:
        try:
            deferred_items = load_json_data(deferred_raw)
        except (json.JSONDecodeError, Exception) as e:
            raise ValidationError(f"--deferred JSON is invalid: {e}. Fix the JSON or pass '[]' for empty.")

        if isinstance(deferred_items, list) and deferred_items:
            _s = _get_storage()
            dec_data = _s.load_data(args.project, 'decisions')
            decisions = dec_data.get("decisions", [])
            next_id = max((int(d["id"].split("-")[1]) for d in decisions if d.get("id", "").startswith("D-")), default=0) + 1

            created_ids = []
            for item in deferred_items:
                if not isinstance(item, dict) or "requirement" not in item:
                    continue
                dec_id = f"D-{next_id:03d}"
                dec = {
                    "id": dec_id,
                    "task_id": args.task_id,
                    "type": "implementation",
                    "issue": f"DEFERRED: {item['requirement']}",
                    "recommendation": item.get("reason", "Deferred — needs clarification or separate task"),
                    "reasoning": f"Identified during completion of {args.task_id}. Source requirement not implemented in this task.",
                    "status": "OPEN",
                    "decided_by": "claude",
                    "confidence": "HIGH",
                    "timestamp": now_iso(),
                }
                if item.get("affects"):
                    dec["affects"] = item["affects"]
                decisions.append(dec)
                created_ids.append(dec_id)
                next_id += 1

            dec_data["decisions"] = decisions
            _s.save_data(args.project, 'decisions', dec_data)
            task["deferred_decisions"] = created_ids
            print(f"  Deferred: {len(created_ids)} item(s) → OPEN decisions {', '.join(created_ids)}")
            _trace(args.project, {"event": "complete.deferred_created", "task": args.task_id,
                   "decision_ids": created_ids,
                   "items": [{"requirement": i.get("requirement"), "reason": i.get("reason")}
                             for i in deferred_items if isinstance(i, dict)]})

    # Git workflow: push + PR + cleanup
    git_result = _apply_git_workflow_complete(args.project, tracker, task)
    if git_result:
        task.update(git_result)

    task["status"] = "DONE"
    task["completed_at"] = now_iso()
    task["ceremony_level"] = ceremony

    # Build completion_trace on task
    _duration_ms = int((time.time() - _t0) * 1000)
    ac_mech_results = task.get("ac_verification_results", [])
    completion_trace = {
        "ceremony": ceremony,
        "duration_ms": _duration_ms,
        "ac_mechanical_count": len(ac_mech_results),
        "ac_mechanical_passed": sum(1 for r in ac_mech_results if r.get("passed")),
        "ac_mechanical_failed": sum(1 for r in ac_mech_results if not r.get("passed")),
        "ac_manual_count": len([c for c in task.get("acceptance_criteria", [])
                                if isinstance(c, str) or
                                (isinstance(c, dict) and c.get("verification", "manual") == "manual")]),
        "ac_reasoning_length": len(task.get("ac_reasoning", "")),
        "gates_configured": bool(tracker.get("gates")),
        "changes_count": diff_count,
    }
    task["completion_trace"] = completion_trace

    # Save with lock to prevent race conditions in multi-agent mode
    with tracker_lock(args.project):
        # Re-load tracker under lock, apply our task changes
        fresh_tracker = load_tracker(args.project)
        for i, t in enumerate(fresh_tracker["tasks"]):
            if t["id"] == args.task_id:
                fresh_tracker["tasks"][i] = task
                break
        save_tracker(args.project, fresh_tracker)
        tracker = fresh_tracker

    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    total = len(tracker["tasks"])
    print(f"Task {args.task_id} ({task['name']}): -> DONE  [{done_count}/{total}]")

    # Trace to JSONL
    _trace(args.project, {
        "cmd": "complete",
        "task": args.task_id,
        "name": task.get("name"),
        "type": task.get("type"),
        **completion_trace,
    })

    # KR auto-update: trace task → origin → objective, update descriptive KRs
    _auto_update_kr(args.project, task, tracker)

    # End-of-project checks (when all tasks done)
    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    if done_count == len(tracker["tasks"]):
        _check_requirements_coverage(args.project, tracker)
        _check_kr_achievement(args.project)


# ---------------------------------------------------------------------------
# Requirements coverage
# ---------------------------------------------------------------------------

def _check_requirements_coverage(project: str, tracker: dict):
    """Check if all extracted requirements have DONE tasks with passed AC. Informational only."""
    _s = _get_storage()
    if not _s.exists(project, 'knowledge'):
        return
    k_data = _s.load_data(project, 'knowledge')
    requirements = [k for k in k_data.get("knowledge", [])
                    if k.get("category") == "requirement" and k.get("status") == "ACTIVE"]
    if not requirements:
        return

    tasks = tracker.get("tasks", [])
    results = []
    for req in requirements:
        covering = [t for t in tasks
                    if any(sr.get("knowledge_id") == req["id"]
                           for sr in t.get("source_requirements", []))]
        done = [t for t in covering if t["status"] in ("DONE", "SKIPPED")]
        results.append({
            "id": req["id"], "text": req.get("title", ""),
            "covered": bool(done), "tasks": [t["id"] for t in covering],
        })

    covered = sum(1 for r in results if r["covered"])
    total = len(results)
    print(f"\n## Requirements Coverage: {covered}/{total}")
    for r in results:
        status = "COVERED" if r["covered"] else "NOT COVERED"
        tasks_str = f" ({', '.join(r['tasks'])})" if r["tasks"] else ""
        print(f"  [{status}] {r['id']}: {r['text']}{tasks_str}")

    _trace(project, {"event": "requirements_coverage", "covered": covered, "total": total,
           "details": results})


def _check_kr_achievement(project: str):
    """Check KR achievement across all objectives. Informational only."""
    _s = _get_storage()
    if not _s.exists(project, 'objectives'):
        return
    obj_data = _s.load_data(project, 'objectives')
    objectives = [o for o in obj_data.get("objectives", []) if o.get("status") == "ACTIVE"]
    if not objectives:
        return

    from pipeline_context import _objective_kr_pct

    print(f"\n## KR Achievement")
    total_krs = 0
    achieved_krs = 0
    for obj in objectives:
        krs = obj.get("key_results", [])
        if not krs:
            continue
        print(f"\n  **{obj['id']}**: {obj.get('title', '')}")
        for kr in krs:
            total_krs += 1
            kr_id = kr.get("id", "?")
            if kr.get("target") is not None:
                current = kr.get("current", kr.get("baseline", 0))
                target = kr["target"]
                pct = _objective_kr_pct(kr.get("baseline", 0), target, current)
                direction = kr.get("direction", "up")
                met = (current <= target) if direction == "down" else (current >= target)
                status = "ACHIEVED" if met else f"{pct}%"
                if met:
                    achieved_krs += 1
                print(f"    [{status}] {kr_id}: {current}/{target}")
            else:
                kr_status = kr.get("status", "NOT_STARTED")
                if kr_status == "ACHIEVED":
                    achieved_krs += 1
                print(f"    [{kr_status}] {kr_id}: {kr.get('description', '')[:60]}")

    print(f"\n  **Total: {achieved_krs}/{total_krs} KRs achieved**")
    _trace(project, {"event": "kr_achievement", "achieved": achieved_krs, "total": total_krs})


# ---------------------------------------------------------------------------
# KR auto-update
# ---------------------------------------------------------------------------

def _auto_update_kr(project: str, task: dict, tracker: dict):
    """Auto-update objective KRs after task completion.

    - Descriptive KRs: NOT_STARTED → IN_PROGRESS when first task done,
      → ACHIEVED when ALL tasks for this objective are done.
    - Numeric KRs: not auto-updated (require human judgment).
    - Logs what changed.
    """
    # Lazy import for _objective_kr_pct still in pipeline.py
    from pipeline_context import _objective_kr_pct

    origin = task.get("origin", "")
    _s = _get_storage()
    obj_ids = set()

    if origin.startswith("O-"):
        obj_ids.add(origin)
    elif origin.startswith("I-"):
        if _s.exists(project, 'ideas'):
            ideas_data = _s.load_data(project, 'ideas')
            for idea in ideas_data.get("ideas", []):
                if idea["id"] == origin:
                    obj_ids = {kr.split("/")[0] for kr in idea.get("advances_key_results", []) if "/" in kr}
                    break

    if not obj_ids:
        if origin:
            print(f"\n  **KR WARNING**: Task {task.get('id')} has origin '{origin}' "
                  f"but it doesn't resolve to any objective. KR auto-update skipped.",
                  file=sys.stderr)
        _trace(project, {"event": "kr_update.no_objectives", "task": task.get("id"),
               "origin": origin, "obj_ids": list(obj_ids)})
        return
    if not _s.exists(project, 'objectives'):
        print(f"\n  **KR WARNING**: Task {task.get('id')} targets {list(obj_ids)} "
              f"but no objectives.json exists. KR auto-update skipped.",
              file=sys.stderr)
        _trace(project, {"event": "kr_update.no_objectives_file", "task": task.get("id"),
               "origin": origin, "obj_ids": list(obj_ids)})
        return

    obj_data = _s.load_data(project, 'objectives')
    all_tasks = tracker.get("tasks", [])
    changed = False

    for obj in obj_data.get("objectives", []):
        if obj["id"] not in obj_ids or obj.get("status") != "ACTIVE":
            continue

        # Count tasks linked to this objective
        obj_tasks = [t for t in all_tasks if t.get("origin") == obj["id"]]
        done_tasks = [t for t in obj_tasks if t["status"] in ("DONE", "SKIPPED")]
        all_done = len(obj_tasks) > 0 and len(done_tasks) == len(obj_tasks)

        print(f"\n  Objective {obj['id']}: {obj['title']}  [{len(done_tasks)}/{len(obj_tasks)} tasks]")

        kr_updates_from_ac = task.get("kr_updates_from_ac", {})

        for kr in obj.get("key_results", []):
            # AC-linked KRs
            if kr.get("measurement") == "ac_link":
                full_kr_id = f"{obj['id']}/{kr['id']}"
                ac_value = kr_updates_from_ac.get(full_kr_id)
                if ac_value is not None:
                    if isinstance(ac_value, (int, float)) and kr.get("target") is not None:
                        old = kr.get("current", kr.get("baseline", 0))
                        kr["current"] = ac_value
                        kr["last_measured_at"] = now_iso()
                        direction = kr.get("direction", "up")
                        met = (ac_value <= kr["target"]) if direction == "down" else (ac_value >= kr["target"])
                        pct = _objective_kr_pct(kr.get("baseline", 0), kr["target"], ac_value)
                        print(f"    {kr['id']}: AC→KR bridge: {old} → {ac_value} (target: {kr['target']}, {pct}%)")
                        if met and kr.get("status") != "ACHIEVED":
                            kr["status"] = "ACHIEVED"
                            kr["achieved_at"] = now_iso()
                            kr["achieved_by_task"] = task["id"]
                            print(f"    {kr['id']}: → ACHIEVED via AC")
                        changed = True
                        _trace(project, {"event": "kr_update.ac_bridge", "task": task.get("id"),
                               "objective": obj["id"], "kr": kr["id"], "value": ac_value, "met": met})
                    elif ac_value is True:
                        if kr.get("status") != "ACHIEVED":
                            kr["status"] = "ACHIEVED"
                            kr["achieved_at"] = now_iso()
                            kr["achieved_by_task"] = task["id"]
                            print(f"    {kr['id']}: → ACHIEVED via AC (test passed)")
                            changed = True
                continue

            # Numeric KRs
            if kr.get("target") is not None:
                baseline = kr.get("baseline", 0)

                # If KR has measurement command, run it
                if kr.get("measurement") == "command" and kr.get("command"):
                    import subprocess as _sp
                    project_dir = get_project_dir(project)
                    try:
                        result = _sp.run(kr["command"], shell=True, capture_output=True,
                                       text=True, encoding="utf-8", timeout=120,
                                       cwd=project_dir)
                        output = (result.stdout or "").strip()
                        try:
                            value = float(output)
                            old = kr.get("current", baseline)
                            kr["current"] = value
                            kr["last_measured_at"] = now_iso()
                            history = kr.get("measurement_history", [])
                            history.append({"value": value, "timestamp": now_iso(),
                                          "source": f"task:{task.get('id', '?')}"})
                            kr["measurement_history"] = history[-20:]

                            direction = kr.get("direction", "up")
                            met = (value <= kr["target"]) if direction == "down" else (value >= kr["target"])
                            pct = _objective_kr_pct(baseline, kr["target"], value)
                            print(f"    {kr['id']}: measured {old} → {value} (target: {kr['target']}, {pct}%)")

                            if met and kr.get("status") != "ACHIEVED":
                                kr["status"] = "ACHIEVED"
                                kr["achieved_at"] = now_iso()
                                kr["achieved_by_task"] = task["id"]
                                print(f"    {kr['id']}: → ACHIEVED (target met)")

                            changed = True
                            _trace(project, {"event": "kr_measure.auto", "task": task.get("id"),
                                   "objective": obj["id"], "kr": kr["id"],
                                   "old": old, "new": value, "met": met})
                        except ValueError:
                            print(f"    {kr['id']}: **KR MEASUREMENT FAILED** — output not a number: '{output[:60]}'",
                                  file=sys.stderr)
                            print(f"    Fix: ensure command outputs a single number. Command: {kr['command'][:80]}",
                                  file=sys.stderr)
                            _trace(project, {"event": "kr_measure.parse_error", "task": task.get("id"),
                                   "objective": obj["id"], "kr": kr["id"], "output": output[:100]})
                    except _sp.TimeoutExpired:
                        print(f"    {kr['id']}: **KR MEASUREMENT FAILED** — command timed out (120s)",
                              file=sys.stderr)
                        _trace(project, {"event": "kr_measure.timeout", "task": task.get("id"),
                               "objective": obj["id"], "kr": kr["id"]})
                elif kr.get("measurement") == "test" and kr.get("test_path"):
                    import subprocess as _sp
                    project_dir = get_project_dir(project)
                    cmd_str = f"pytest {kr['test_path']} -x -q"
                    try:
                        result = _sp.run(cmd_str, shell=True, capture_output=True,
                                       text=True, encoding="utf-8", timeout=120,
                                       cwd=project_dir)
                        passed = result.returncode == 0
                        print(f"    {kr['id']}: test {'PASS' if passed else 'FAIL'}")
                        if passed and kr.get("status") != "ACHIEVED":
                            kr["status"] = "ACHIEVED"
                            kr["achieved_at"] = now_iso()
                            kr["achieved_by_task"] = task["id"]
                            print(f"    {kr['id']}: → ACHIEVED (test passed)")
                            changed = True
                    except _sp.TimeoutExpired:
                        print(f"    {kr['id']}: **KR MEASUREMENT FAILED** — test timed out (120s)",
                              file=sys.stderr)
                        _trace(project, {"event": "kr_measure.test_timeout", "task": task.get("id"),
                               "objective": obj["id"], "kr": kr["id"], "test_path": kr.get("test_path")})
                else:
                    # No measurement — show manual update message
                    current = kr.get("current", baseline)
                    pct = _objective_kr_pct(baseline, kr["target"], current)
                    print(f"    {kr['id']}: {current}/{kr['target']} ({pct}%) — update manually if changed")
                continue

            # Descriptive KRs: auto-update status
            old_status = kr.get("status", "NOT_STARTED")
            if all_done and old_status != "ACHIEVED":
                kr["status"] = "ACHIEVED"
                kr["achieved_at"] = now_iso()
                kr["achieved_by_task"] = task["id"]
                print(f"    {kr['id']}: {old_status} → ACHIEVED (all {len(obj_tasks)} tasks done)")
                _trace(project, {"event": "kr_update.change", "task": task.get("id"),
                       "objective": obj["id"], "kr": kr["id"],
                       "old_status": old_status, "new_status": "ACHIEVED",
                       "done_tasks": len(done_tasks), "total_tasks": len(obj_tasks)})
                changed = True
            elif not all_done and old_status == "NOT_STARTED" and len(done_tasks) > 0:
                kr["status"] = "IN_PROGRESS"
                kr["started_by_task"] = task["id"]
                print(f"    {kr['id']}: NOT_STARTED → IN_PROGRESS ({len(done_tasks)}/{len(obj_tasks)} tasks done)")
                _trace(project, {"event": "kr_update.change", "task": task.get("id"),
                       "objective": obj["id"], "kr": kr["id"],
                       "old_status": "NOT_STARTED", "new_status": "IN_PROGRESS",
                       "done_tasks": len(done_tasks), "total_tasks": len(obj_tasks)})
                changed = True
            else:
                print(f"    {kr['id']}: {old_status}")

        obj["updated"] = now_iso()

    if changed:
        obj_data["updated"] = now_iso()
        _s.save_data(project, 'objectives', obj_data)
        print(f"  KR progress saved.")
        _trace(project, {"event": "kr_update.saved", "task": task.get("id"),
               "objectives_updated": list(obj_ids)})

    # Contract C7: Objective completion check
    # When all tasks for an objective are done, check if all KRs are met
    for obj in obj_data.get("objectives", []):
        if obj["id"] not in obj_ids or obj.get("status") != "ACTIVE":
            continue

        obj_tasks = [t for t in all_tasks if t.get("origin") == obj["id"]]
        done_tasks = [t for t in obj_tasks if t["status"] in ("DONE", "SKIPPED")]
        all_tasks_done = len(obj_tasks) > 0 and len(done_tasks) == len(obj_tasks)

        if not all_tasks_done:
            continue

        # All tasks done — check KRs
        all_krs_met = True
        unmet_krs = []
        for kr in obj.get("key_results", []):
            kr_met = False
            if kr.get("status") == "ACHIEVED":
                kr_met = True
            elif kr.get("target") is not None:
                current = kr.get("current", kr.get("baseline", 0))
                direction = kr.get("direction", "up")
                if direction == "down":
                    kr_met = current <= kr["target"]
                else:
                    kr_met = current >= kr["target"]
                if kr_met and kr.get("status") != "ACHIEVED":
                    kr["status"] = "ACHIEVED"
                    kr["achieved_at"] = now_iso()
                    kr["achieved_by_task"] = task["id"]
                    changed = True

            if not kr_met:
                all_krs_met = False
                unmet_krs.append(f"{kr['id']}: {kr.get('metric') or kr.get('description', '?')[:50]}")

        if all_krs_met:
            obj["status"] = "ACHIEVED"
            obj["updated"] = now_iso()
            obj_data["updated"] = now_iso()
            _s.save_data(project, 'objectives', obj_data)
            print(f"\n  ** OBJECTIVE {obj['id']} ACHIEVED ** — all {len(obj_tasks)} tasks done, "
                  f"all {len(obj.get('key_results', []))} KRs met.")
            _trace(project, {"event": "objective.achieved", "objective": obj["id"],
                   "task": task.get("id"), "total_tasks": len(obj_tasks)})
        else:
            print(f"\n  **OBJECTIVE WARNING**: All {len(obj_tasks)} tasks for {obj['id']} are done "
                  f"but {len(unmet_krs)} KR(s) NOT met:", file=sys.stderr)
            for ukr in unmet_krs:
                print(f"    [-] {ukr}", file=sys.stderr)
            print(f"  Update KRs manually or add tasks to address gaps.", file=sys.stderr)
            _trace(project, {"event": "objective.tasks_done_krs_unmet", "objective": obj["id"],
                   "task": task.get("id"), "unmet_krs": unmet_krs})


# ---------------------------------------------------------------------------
# cmd_fail / cmd_skip
# ---------------------------------------------------------------------------

def cmd_fail(args):
    """Mark task as FAILED."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)

    task["status"] = "FAILED"
    task["failed_reason"] = args.reason or "Unknown error"
    task["completed_at"] = now_iso()
    save_tracker(args.project, tracker)
    print(f"Task {args.task_id} ({task['name']}): -> FAILED -- {task['failed_reason']}")

    _trace(args.project, {
        "cmd": "fail", "task": args.task_id, "name": task.get("name"),
        "type": task.get("type"), "reason": task["failed_reason"],
    })


def cmd_skip(args):
    """Mark task as SKIPPED. Requires --reason (min 50 chars)."""
    tracker = load_tracker(args.project)
    task = find_task(tracker, args.task_id)
    reason = getattr(args, "reason", None) or ""

    if not reason.strip():
        raise ValidationError(f"--reason is required when skipping a task. "
              f"Explain why this task cannot be completed.")

    if len(reason.strip()) < 50:
        raise ValidationError(f"--reason too short ({len(reason.strip())} chars). "
              f"Minimum 50 characters. Provide a real explanation, not a placeholder.")

    task["status"] = "SKIPPED"
    task["skip_reason"] = reason.strip()
    task["completed_at"] = now_iso()
    save_tracker(args.project, tracker)

    done_count = sum(1 for t in tracker["tasks"] if t["status"] in ("DONE", "SKIPPED"))
    total = len(tracker["tasks"])
    print(f"Task {args.task_id} ({task['name']}): -> SKIPPED  [{done_count}/{total}]")
    print(f"  Reason: {reason.strip()}")

    _trace(args.project, {
        "cmd": "skip", "task": args.task_id, "name": task.get("name"),
        "type": task.get("type"), "reason": reason.strip(),
    })


# ---------------------------------------------------------------------------
# AC validation helpers
# ---------------------------------------------------------------------------

def _validate_ac_reasoning(ac_reasoning: str, ac_list: list) -> list:
    """Validate that AC reasoning addresses each criterion with evidence.

    Returns list of error strings. Empty = valid.
    Checks:
    - Each AC is addressed (by number or text fragment)
    - PASS/FAIL verdict is present
    - Reasoning is not just filler words
    """
    errors = []
    reasoning_lower = ac_reasoning.lower()

    # Reject filler-only reasoning
    filler_patterns = {"done", "verified", "works", "completed", "all good",
                       "looks good", "checked", "confirmed", "ok", "passed"}
    stripped_words = set(reasoning_lower.replace(".", "").replace(",", "").split())
    if stripped_words.issubset(filler_patterns | {"ac", "all", "the", "is", "are", "and", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", ":", "—"}):
        errors.append("  AC reasoning contains only filler words. Provide concrete evidence.")

    # Filter to only manual AC for validation
    manual_ac = [c for c in ac_list if isinstance(c, str) or
                 (isinstance(c, dict) and c.get("verification", "manual") == "manual")]

    # Check that reasoning mentions each manual AC (by number or text fragment)
    for i, criterion in enumerate(manual_ac, 1):
        text = criterion if isinstance(criterion, str) else criterion.get("text", "")
        markers = [f"ac-{i}:", f"ac{i}:", f"ac {i}:", f"{i}.", f"{i}:"]
        text_fragment = text[:30].lower().strip()

        found = any(m in reasoning_lower for m in markers) or (
            len(text_fragment) > 10 and text_fragment in reasoning_lower
        )
        if not found:
            errors.append(f"  AC {i} not addressed: \"{text[:60]}\"")

    # Check for PASS/FAIL keywords (only if there are manual AC to verify)
    if manual_ac and "pass" not in reasoning_lower and "met" not in reasoning_lower and "verified" not in reasoning_lower:
        errors.append("  No PASS/met/verified verdict found in reasoning")

    return errors


_VAGUE_AC_WORDS = {"handle", "handles", "ensure", "ensures", "properly", "robust",
                   "correctly", "works", "appropriate", "appropriately",
                   "should work", "as expected", "as needed"}


def _warn_ac_quality(tasks: list) -> bool:
    """Print warnings for missing or vague acceptance criteria.

    Returns True if there are BLOCKING issues. ALL task types must have AC.
    No exceptions for chore/investigation.
    """
    warnings = []
    errors = []
    for t_dict in tasks:
        t = Task.from_dict(t_dict) if isinstance(t_dict, dict) else t_dict
        tid = t.id or "?"
        ttype = t.type
        ac = t.acceptance_criteria

        if not ac:
            errors.append(f"  {tid} ({t.name or '?'}): task has no acceptance criteria")
            continue

        for criterion in ac:
            if isinstance(criterion, str):
                errors.append(
                    f"  {tid}: plain-string AC \"{criterion[:60]}\" — must use structured format "
                    f"{{text, verification: 'test'|'command'|'manual'}}"
                )
                continue

            if isinstance(criterion, dict):
                if not criterion.get("verification"):
                    errors.append(
                        f"  {tid}: AC \"{criterion.get('text', '?')[:60]}\" missing 'verification' field — "
                        f"must be 'test', 'command', or 'manual'"
                    )
                elif criterion.get("verification") == "test" and not criterion.get("test_path"):
                    errors.append(
                        f"  {tid}: AC \"{criterion.get('text', '?')[:60]}\" has verification='test' "
                        f"but no 'test_path' — mechanical verification will fail"
                    )
                elif criterion.get("verification") == "command" and not criterion.get("command"):
                    errors.append(
                        f"  {tid}: AC \"{criterion.get('text', '?')[:60]}\" has verification='command' "
                        f"but no 'command' — mechanical verification will fail"
                    )
                elif criterion.get("verification") == "manual" and not criterion.get("check"):
                    warnings.append(
                        f"  {tid}: manual AC \"{criterion.get('text', '?')[:60]}\" has no 'check' field — "
                        f"consider adding a check description"
                    )

                text = criterion.get("text", "")
            else:
                text = str(criterion)

            text_lower = text.lower() if isinstance(criterion, dict) else ""
            found = [w for w in _VAGUE_AC_WORDS if w in text_lower]
            if found:
                warnings.append(
                    f"  {tid}: vague AC \"{text[:60]}\" — contains: {', '.join(found)}"
                )

    if errors:
        print()
        print(f"**AC ERRORS** ({len(errors)}) — must fix before approving:")
        for e in errors:
            print(e)
        print("Add structured acceptance_criteria to ALL tasks: "
              "{text, verification: 'test'|'command'|'manual'}.")
        print()

    if warnings:
        print()
        print(f"**AC QUALITY WARNINGS** ({len(warnings)}):")
        for w in warnings:
            print(w)
        print("Tip: rewrite vague AC as observable outcomes. "
              "E.g., 'handles errors' → 'returns 400 with {error} body for invalid input'")
        print()

    return len(errors) > 0

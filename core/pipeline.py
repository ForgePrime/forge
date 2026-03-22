"""
Pipeline — generic task graph orchestrator.

Evolved from Skill_v1's forge_pipeline.py. Key differences:
- "Project" instead of "Entity" — scope is a goal, not a data entity
- Dynamic task graph — tasks are added by the plan skill, not hardcoded
- No domain-specific logic — pure state machine
- Tasks form a DAG with explicit dependencies
- Tasks support `parallel` and `conflicts_with` metadata (stored, not enforced
  in single-agent mode — designed for future multi-agent orchestration)

State machine per task: TODO -> IN_PROGRESS -> DONE | FAILED | SKIPPED
Subtasks: a task can have child subtasks for batch processing.

Usage:
    python -m core.pipeline <command> <project> [options]

Commands:
    init              {project} --goal "..."        Create project tracker
    add-tasks         {project} --data '{json}'     Add tasks to the graph
    next              {project}                     Get next task/subtask
    complete          {project} {task_id}            Mark task DONE
    fail              {project} {task_id} --reason   Mark task FAILED
    skip              {project} {task_id}            Mark task SKIPPED
    status            {project}                     Dashboard
    list              {project}                     All tasks with status
    reset             {project} --from {task_id}    Reset from task onward
    register-subtasks {project} {task_id} --data    Register subtasks
    complete-subtask  {project} {subtask_id}        Mark subtask DONE
    draft-plan        {project} --data '{json}'     Store draft plan for review
    show-draft        {project}                     Show current draft plan
    approve-plan      {project}                     Approve draft → materialize tasks
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import render_contract
from errors import ForgeError

# -- Re-export from submodules for backward compatibility --
# (other modules import from pipeline directly)

from pipeline_common import (  # noqa: F401
    _get_storage, _trace, _debug_enabled,
    load_tracker, save_tracker, find_task, find_task_model, _max_task_num,
    load_project_config, get_project_dir,
    print_status, print_dag, print_task_list, print_task_detail,
    STATUS_ICONS,
)

from pipeline_tasks import (  # noqa: F401
    _remap_temp_ids, validate_dag, _build_task_entry,
    cmd_init, cmd_add_tasks, cmd_status, cmd_list, cmd_reset,
    cmd_update_task, cmd_remove_task,
    _next_subtask, cmd_register_subtasks, cmd_complete_subtask,
    CONTRACTS,
)

from pipeline_git import (  # noqa: F401
    _get_current_commit, _auto_record_changes,
    _apply_git_workflow_start, _apply_git_workflow_complete,
    _count_diff_files,
)

from pipeline_execution import (  # noqa: F401
    cmd_next, cmd_begin, cmd_complete, cmd_fail, cmd_skip,
    _verify_acceptance_criteria, _check_gates_before_complete,
    _determine_ceremony_level, _auto_update_kr,
    _claim_with_retry, _get_active_ids, _has_conflict,
    _load_open_decision_ids, _blocked_by_open_decisions,
    _validate_ac_reasoning, _warn_ac_quality,
    CLAIM_WAIT_SECONDS,
)

from pipeline_context import (  # noqa: F401
    cmd_context, cmd_config,
    _objective_kr_pct, _estimate_context_size,
    _check_plan_staleness, _check_contract_alignment,
)

from pipeline_planning import (  # noqa: F401
    cmd_draft_plan, cmd_show_draft, cmd_approve_plan,
    _validate_plan_references, _validate_plan_context,
    _check_assumptions_readiness, _check_coverage,
    _print_draft_tasks,
)


# -- CLI --

def main():
    parser = argparse.ArgumentParser(
        description="Forge Pipeline -- task graph orchestrator"
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("init", help="Create project tracker")
    p.add_argument("project")
    p.add_argument("--goal", required=True, help="Project goal description")
    p.add_argument("--project-dir", required=True, dest="project_dir",
                   help="Absolute path to the project workspace (where code lives)")
    p.add_argument("--force", action="store_true", help="Overwrite existing")

    p = sub.add_parser("add-tasks", help="Add tasks to graph")
    p.add_argument("project")
    p.add_argument("--data", required=True, help="JSON array of tasks")

    p = sub.add_parser("next", help="Get next task")
    p.add_argument("project")
    p.add_argument("--agent", default=None, help="Agent name for multi-agent claim")
    p.add_argument("--objective", default=None, help="Filter to tasks with origin matching this objective (O-NNN)")

    p = sub.add_parser("begin", help="Claim next task and show full execution context")
    p.add_argument("project")
    p.add_argument("--agent", default=None, help="Agent name for multi-agent claim")
    p.add_argument("--objective", default=None, help="Filter to tasks with origin matching this objective (O-NNN)")
    p.add_argument("--lean", action="store_true", default=False,
                   help="Lean context: skip Knowledge, Research, Business Context, Lessons")

    p = sub.add_parser("complete", help="Mark task DONE")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--agent", default=None, help="Agent name (verified against claim)")
    # --force removed: all gates are mandatory. Fix the issue, don't bypass it.
    p.add_argument("--reasoning", default=None, help="Why these changes were made (used for auto-recorded changes)")
    p.add_argument("--ac-reasoning", default=None, dest="ac_reasoning",
                   help="Legacy: single string justification (use --ac-evidence instead)")
    p.add_argument("--ac-evidence", default=None, dest="ac_evidence",
                   help="JSON array of per-AC evidence: [{ac_index, verdict: PASS|FAIL, evidence: str}]")
    p.add_argument("--deferred", default=None,
                   help="JSON array of {requirement, reason} — items deferred from source doc. Auto-creates OPEN decisions.")

    p = sub.add_parser("fail", help="Mark task FAILED")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--reason", default=None)
    p.add_argument("--agent", default=None, help="Agent name")

    p = sub.add_parser("skip", help="Mark task SKIPPED (requires --reason)")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--reason", required=True, help="Why this task is being skipped (min 50 chars)")
    # --force removed: skip requires --reason, no exceptions

    p = sub.add_parser("status", help="Status dashboard")
    p.add_argument("project")
    p.add_argument("--objective", default=None, help="Filter to objective (O-NNN)")

    p = sub.add_parser("list", help="List all tasks")
    p.add_argument("project")
    p.add_argument("--objective", default=None, help="Filter to objective (O-NNN)")

    p = sub.add_parser("reset", help="Reset tasks from ID onward")
    p.add_argument("project")
    p.add_argument("--from", dest="from_task", required=True)

    p = sub.add_parser("update-task", help="Update an existing task")
    p.add_argument("project")
    p.add_argument("--data", required=True, help="JSON object with id + fields to update")

    p = sub.add_parser("remove-task", help="Remove a TODO task")
    p.add_argument("project")
    p.add_argument("task_id")

    p = sub.add_parser("context", help="Aggregated context for a task")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--lean", action="store_true", default=False,
                   help="Lean mode: skip Knowledge, Research, Business Context, Lessons")

    p = sub.add_parser("config", help="Set/show project configuration")
    p.add_argument("project")
    p.add_argument("--data", default=None, help="JSON object with config keys")

    p = sub.add_parser("draft-plan", help="Store draft plan for review")
    p.add_argument("project")
    p.add_argument("--data", required=True, help="JSON array of tasks (same format as add-tasks)")
    p.add_argument("--idea", default=None, help="Source idea ID (I-NNN)")
    p.add_argument("--objective", default=None, help="Source objective ID (O-NNN)")
    p.add_argument("--assumptions", default=None,
                   help="JSON array of {assumption, basis, severity} for readiness gate")
    p.add_argument("--coverage", default=None,
                   help="JSON array of {requirement, source, covered_by, status, reason?} for coverage gate")

    p = sub.add_parser("show-draft", help="Show current draft plan")
    p.add_argument("project")

    p = sub.add_parser("approve-plan", help="Approve draft plan and materialize into pipeline")
    p.add_argument("project")
    # --force removed: context validation errors must be fixed

    p = sub.add_parser("contract", help="Print contract spec (no project needed)")
    p.add_argument("name", choices=sorted(CONTRACTS.keys()))
    p.add_argument("_extra", nargs="*", help=argparse.SUPPRESS)

    p = sub.add_parser("register-subtasks", help="Register subtasks")
    p.add_argument("project")
    p.add_argument("task_id")
    p.add_argument("--data", required=True, help="JSON array [{id, name, ...}]")

    p = sub.add_parser("complete-subtask", help="Mark subtask DONE")
    p.add_argument("project")
    p.add_argument("subtask_id")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "add-tasks": cmd_add_tasks,
        "next": cmd_next,
        "begin": cmd_begin,
        "complete": cmd_complete,
        "fail": cmd_fail,
        "skip": cmd_skip,
        "status": cmd_status,
        "list": cmd_list,
        "reset": cmd_reset,
        "update-task": cmd_update_task,
        "remove-task": cmd_remove_task,
        "context": cmd_context,
        "config": cmd_config,
        "draft-plan": cmd_draft_plan,
        "show-draft": cmd_show_draft,
        "approve-plan": cmd_approve_plan,
        "contract": lambda args: print(render_contract(args.name, CONTRACTS[args.name])),
        "register-subtasks": cmd_register_subtasks,
        "complete-subtask": cmd_complete_subtask,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            cmd_func(args)
        except ForgeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(e.exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""In-repo plan exporter — CGAID artifact #3 (Execution Plan in .ai/PLAN_*.md).

CGAID requires the execution plan to live alongside the codebase, so an
engineer with only a repo checkout (no Forge UI) can read what the plan is.
Forge keeps the plan in DB; this exporter dumps a markdown snapshot per
project into the workspace directory.

Path convention:
  {workspace_root}/{slug}/workspace/.ai/PLAN.md          — project-level
  {workspace_root}/{slug}/workspace/.ai/PLAN_{O-NNN}.md  — per-objective

Called from:
  - projects.create_tasks (post-batch hook)
  - tier1 manual export endpoint (disaster recovery / initial sync)
"""
import pathlib
import datetime as dt
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import Project, Task, Objective, KeyResult, AcceptanceCriterion


def _slug_title(text: str, max_len: int = 40) -> str:
    """Filesystem-safe slug for filenames."""
    out = []
    for ch in (text or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    s = "".join(out).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s[:max_len] or "untitled"


def _render_task(t: Task) -> str:
    lines = [f"### {t.external_id} — {t.name}"]
    lines.append("")
    lines.append(f"- **Type:** {t.type} · **Status:** {t.status}")
    if t.origin:
        lines.append(f"- **Origin:** {t.origin}")
    if t.depends_on:
        lines.append(f"- **Depends on:** {', '.join(t.depends_on)}")
    if t.scopes:
        lines.append(f"- **Scopes:** {', '.join(t.scopes)}")
    if t.instruction:
        lines.append("")
        lines.append("**Instruction:**")
        lines.append("")
        lines.append(t.instruction.strip())
    if t.alignment:
        lines.append("")
        lines.append("**Alignment:**")
        a = t.alignment
        if a.get("goal"):
            lines.append(f"- Goal: {a['goal']}")
        if isinstance(a.get("boundaries"), dict):
            b = a["boundaries"]
            if b.get("must"):
                lines.append(f"- MUST: {b['must']}")
            if b.get("must_not"):
                lines.append(f"- MUST NOT: {b['must_not']}")
            if b.get("not_in_scope"):
                lines.append(f"- NOT IN SCOPE: {b['not_in_scope']}")
        if a.get("success"):
            lines.append(f"- Success: {a['success']}")
    if t.acceptance_criteria:
        lines.append("")
        lines.append("**Acceptance criteria:**")
        for ac in sorted(t.acceptance_criteria, key=lambda x: x.position):
            marker = f"[{ac.scenario_type}/{ac.verification}]"
            lines.append(f"- AC-{ac.position} {marker} {ac.text}")
            if ac.test_path:
                lines.append(f"  - test_path: `{ac.test_path}`")
            if ac.source_ref:
                lines.append(f"  - source: {ac.source_ref}")
    if t.produces:
        lines.append("")
        lines.append(f"**Produces:** `{t.produces}`")
    if t.exclusions:
        lines.append("")
        lines.append("**Exclusions:**")
        for ex in t.exclusions:
            lines.append(f"- {ex}")
    lines.append("")
    return "\n".join(lines)


def _render_plan(project: Project, tasks: list[Task], objective: Objective | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = [
        f"# Execution Plan — {project.slug}",
        "",
        f"*Auto-generated {now} by Forge plan_exporter. DO NOT edit by hand —*",
        f"*changes here are overwritten on next sync. Edit in Forge UI, not this file.*",
        "",
    ]
    if objective:
        header.append(f"**Objective:** {objective.external_id} — {objective.title}")
        header.append(f"**Status:** {objective.status} · **Priority:** P{objective.priority}")
        if objective.business_context:
            header.append("")
            header.append("**Business context:**")
            header.append("")
            header.append(objective.business_context.strip())
        header.append("")
        krs = sorted(objective.key_results, key=lambda k: k.position)
        if krs:
            header.append("**Key Results:**")
            for kr in krs:
                tgt = f" · target={kr.target_value}" if kr.target_value is not None else ""
                cur = f" · current={kr.current_value}" if kr.current_value is not None else ""
                header.append(f"- KR{kr.position} [{kr.status}] {kr.text}{tgt}{cur}")
            header.append("")
    header.extend([
        f"**Tasks in plan:** {len(tasks)}",
        "",
        "---",
        "",
    ])

    # Group by status for readability; within a group keep declaration order
    by_status: dict[str, list[Task]] = defaultdict(list)
    for t in tasks:
        by_status[t.status].append(t)

    body_parts = []
    status_order = ["IN_PROGRESS", "TODO", "DONE", "SKIPPED", "FAILED"]
    for st in status_order:
        if st not in by_status:
            continue
        body_parts.append(f"## {st} ({len(by_status[st])})")
        body_parts.append("")
        for t in by_status[st]:
            body_parts.append(_render_task(t))
    # Any status not in ordered list
    for st, items in by_status.items():
        if st in status_order:
            continue
        body_parts.append(f"## {st} ({len(items)})")
        body_parts.append("")
        for t in items:
            body_parts.append(_render_task(t))

    return "\n".join(header + body_parts)


def export_project_plan(
    db: Session,
    project: Project,
    workspace_root: str,
) -> list[pathlib.Path]:
    """Write PLAN.md at project level + PLAN_{O-NNN}.md per objective.

    Returns list of written file paths. Missing workspace dir is created.
    Does NOT raise on filesystem errors — caller decides severity; errors returned as None paths.
    """
    ws_root = pathlib.Path(workspace_root) / project.slug / "workspace" / ".ai"
    ws_root.mkdir(parents=True, exist_ok=True)

    all_tasks = (
        db.query(Task)
        .filter(Task.project_id == project.id)
        .order_by(Task.id)
        .all()
    )

    written: list[pathlib.Path] = []

    # Project-level plan
    project_md = _render_plan(project, all_tasks, objective=None)
    project_path = ws_root / "PLAN.md"
    project_path.write_text(project_md, encoding="utf-8")
    written.append(project_path)

    # Per-objective plans (only objectives with linked tasks)
    by_origin: dict[str, list[Task]] = defaultdict(list)
    for t in all_tasks:
        if t.origin:
            by_origin[t.origin].append(t)

    if by_origin:
        objectives = {
            o.external_id: o
            for o in db.query(Objective)
            .filter(Objective.project_id == project.id)
            .all()
        }
        for obj_ext_id, obj_tasks in by_origin.items():
            obj = objectives.get(obj_ext_id)
            if not obj:
                continue
            obj_md = _render_plan(project, obj_tasks, objective=obj)
            obj_slug = _slug_title(obj.title, 30)
            obj_path = ws_root / f"PLAN_{obj.external_id}-{obj_slug}.md"
            obj_path.write_text(obj_md, encoding="utf-8")
            written.append(obj_path)

    return written

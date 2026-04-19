"""In-repo Handoff Document exporter — CGAID artifact #4.

CGAID Section 5.3 Artifact #4 requires a standardized Handoff Document
transferring business intent from the Solutioning Cockpit (objectives)
to the codebase execution layer, with 8 fields:

  1. intent
  2. scope
  3. assumptions
  4. unknowns
  5. decisions needed
  6. risks
  7. edge cases
  8. verification criteria

Forge already stores all 8 (across Task, Objective, Decision, AcceptanceCriterion,
Task.risks). This exporter renders per-task Handoff markdown under:

  {workspace}/.ai/handoff/HANDOFF_{T-NNN}-{slug}.md

Scope:
- Only feature/bug tasks get Handoff files (chore/investigation don't need it)
- Export triggered at task creation (post-batch) and via manual endpoint
- Idempotent — overwrites with current DB state
"""
import pathlib
import datetime as dt

from sqlalchemy.orm import Session

from app.models import Project, Task, Decision, Objective, KeyResult


def _slug_title(text: str, max_len: int = 40) -> str:
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


def _section(title: str, body: str | list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if isinstance(body, list):
        lines.extend(body)
    else:
        lines.append(body.strip() if body else "*(not captured)*")
    lines.append("")
    return lines


def _render_handoff(
    task: Task,
    project: Project,
    objective: Objective | None,
    open_decisions: list[Decision],
    closed_decisions: list[Decision],
) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        f"# Handoff — {task.external_id} · {task.name}",
        "",
        f"*Auto-generated {now} by Forge handoff_exporter. Source of truth: Forge DB.*",
        "",
        f"**Project:** {project.slug} · **Task type:** {task.type} · **Status:** {task.status}",
    ]
    if objective:
        lines.append(f"**Objective:** {objective.external_id} — {objective.title}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. INTENT
    intent_body = []
    if task.instruction:
        intent_body.append(task.instruction.strip())
    elif task.description:
        intent_body.append(task.description.strip())
    else:
        intent_body.append("*(no instruction or description set)*")
    if objective and objective.business_context:
        intent_body.append("")
        intent_body.append("**Business context (from objective):**")
        intent_body.append("")
        intent_body.append(objective.business_context.strip())
    lines.extend(_section("1. Intent", intent_body))

    # 2. SCOPE
    scope_lines = []
    align = task.alignment or {}
    if align.get("goal"):
        scope_lines.append(f"**Goal:** {align['goal']}")
    boundaries = align.get("boundaries") or {}
    if boundaries.get("must"):
        scope_lines.append(f"- **MUST:** {boundaries['must']}")
    if boundaries.get("must_not"):
        scope_lines.append(f"- **MUST NOT:** {boundaries['must_not']}")
    if boundaries.get("not_in_scope"):
        scope_lines.append(f"- **NOT IN SCOPE:** {boundaries['not_in_scope']}")
    if task.scopes:
        scope_lines.append(f"- **Domain scopes:** {', '.join(task.scopes)}")
    if task.exclusions:
        scope_lines.append("- **Exclusions:**")
        for ex in task.exclusions:
            scope_lines.append(f"  - {ex}")
    if not scope_lines:
        scope_lines.append("*(scope not explicitly captured — see task.alignment in Forge DB)*")
    lines.extend(_section("2. Scope", scope_lines))

    # 3. ASSUMPTIONS — stored in delivery.assumptions post-execution; static assumptions
    # live in project.contract_md. For pre-execution Handoff, surface project contract.
    assumptions_body = []
    if project.contract_md:
        contract_preview = project.contract_md[:1500]
        if len(project.contract_md) > 1500:
            contract_preview += "\n\n*(truncated — see Forge UI for full contract)*"
        assumptions_body.append("**Project operational contract (applies to every task):**")
        assumptions_body.append("")
        assumptions_body.append(contract_preview)
    else:
        assumptions_body.append("*(no project-level contract — see delivery.assumptions post-execution)*")
    lines.extend(_section("3. Assumptions", assumptions_body))

    # 4. UNKNOWNS — OPEN decisions linked to this task OR project-level with no task link
    unknowns_lines = []
    task_open = [d for d in open_decisions if d.task_id == task.id]
    proj_open = [d for d in open_decisions if d.task_id is None]
    if task_open:
        unknowns_lines.append(f"**{len(task_open)} open decision(s) on this task:**")
        for d in task_open:
            unknowns_lines.append(f"- {d.external_id} — {d.issue or '(no text)'}")
    if proj_open:
        unknowns_lines.append("")
        unknowns_lines.append(f"**{len(proj_open)} project-level open decision(s):**")
        for d in proj_open[:10]:
            unknowns_lines.append(f"- {d.external_id} — {d.issue or '(no text)'}")
        if len(proj_open) > 10:
            unknowns_lines.append(f"- … +{len(proj_open) - 10} more in Forge UI")
    if not task_open and not proj_open:
        unknowns_lines.append("*(no open questions — all known decisions are closed)*")
    lines.extend(_section("4. Unknowns / open questions", unknowns_lines))

    # 5. DECISIONS NEEDED — same as #4 but with recommendations highlighted
    # Forge's OPEN decisions double as "decisions needed". Section adds HIGH-severity filter.
    decisions_needed_lines = []
    high_sev = [d for d in open_decisions if (d.severity or "").lower() in ("high", "critical")]
    if high_sev:
        decisions_needed_lines.append(f"**{len(high_sev)} HIGH/CRITICAL severity open decision(s):**")
        for d in high_sev:
            decisions_needed_lines.append(f"- {d.external_id} [{d.severity}] — {d.issue or '(no text)'}")
            if d.recommendation:
                decisions_needed_lines.append(f"  - Proposed: {d.recommendation[:200]}")
    else:
        decisions_needed_lines.append("*(no high-severity decisions pending — see section 4 for all open)*")
    lines.extend(_section("5. Decisions needed", decisions_needed_lines))

    # 6. RISKS — explicit Task.risks field (CGAID addition)
    risks_lines = []
    risks = task.risks or []
    if risks:
        risks_lines.append(f"**{len(risks)} risk(s) captured:**")
        for r in risks:
            if not isinstance(r, dict):
                continue
            sev = r.get("severity", "MEDIUM")
            owner = f" · owner: {r['owner']}" if r.get("owner") else ""
            risks_lines.append(f"- [{sev}] {r.get('risk', '(no risk text)')}{owner}")
            if r.get("mitigation"):
                risks_lines.append(f"  - Mitigation: {r['mitigation']}")
    else:
        risks_lines.append("*(no explicit risks captured — `task.risks` is empty)*")
    lines.extend(_section("6. Risks", risks_lines))

    # 7. EDGE CASES — AC with scenario_type in negative/edge_case
    edge_lines = []
    edge_acs = [
        ac for ac in task.acceptance_criteria
        if ac.scenario_type in ("negative", "edge_case", "regression")
    ]
    if edge_acs:
        edge_lines.append(f"**{len(edge_acs)} failure-mode AC(s):**")
        for ac in sorted(edge_acs, key=lambda a: a.position):
            edge_lines.append(f"- AC-{ac.position} [{ac.scenario_type}/{ac.verification}] {ac.text}")
            if ac.test_path:
                edge_lines.append(f"  - test_path: `{ac.test_path}`")
    else:
        edge_lines.append(
            "*(no negative/edge_case/regression AC — this will be REJECTED at execution per "
            "contract_validator.py:133 for feature/bug)*"
        )
    lines.extend(_section("7. Edge cases", edge_lines))

    # 8. VERIFICATION CRITERIA — all AC, focused on how each is verified
    verif_lines = []
    all_acs = sorted(task.acceptance_criteria, key=lambda a: a.position)
    if all_acs:
        verif_lines.append(f"**{len(all_acs)} acceptance criteria:**")
        for ac in all_acs:
            line = f"- AC-{ac.position} [{ac.scenario_type}/{ac.verification}] {ac.text}"
            verif_lines.append(line)
            if ac.verification in ("test", "command") and ac.test_path:
                verif_lines.append(f"  - test_path: `{ac.test_path}`")
            elif ac.verification == "manual" and ac.command:
                verif_lines.append(f"  - manual check: {ac.command}")
            if ac.source_ref:
                verif_lines.append(f"  - source: {ac.source_ref}")
    else:
        verif_lines.append("*(no acceptance criteria — task will be REJECTED at create time for feature/bug)*")

    # Add KR linkage (business-level verification)
    kr_ids = task.completes_kr_ids or []
    if kr_ids and objective:
        verif_lines.append("")
        verif_lines.append(f"**Completes KR(s) on {objective.external_id}:**")
        positions = set()
        for kref in kr_ids:
            try:
                positions.add(int(kref.replace("KR", "")))
            except ValueError:
                pass
        matching_krs = [k for k in objective.key_results if k.position in positions]
        for kr in sorted(matching_krs, key=lambda k: k.position):
            t_val = f" · target={kr.target_value}" if kr.target_value is not None else ""
            verif_lines.append(f"- KR{kr.position} [{kr.status}] {kr.text}{t_val}")
    lines.extend(_section("8. Verification criteria", verif_lines))

    # Metadata trailer
    lines.append("---")
    lines.append("")
    lines.append(f"*Task ID: {task.external_id}*")
    if task.started_at:
        lines.append(f"*Started: {task.started_at.strftime('%Y-%m-%d')}*")
    if task.completed_at:
        lines.append(f"*Completed: {task.completed_at.strftime('%Y-%m-%d')}*")

    return "\n".join(lines)


def export_task_handoff(
    db: Session,
    task: Task,
    project: Project,
    workspace_root: str,
) -> pathlib.Path | None:
    """Write one Handoff Document for a single task.

    Only exports feature/bug tasks — other types don't need formal handoff.
    Returns path written, or None if task type doesn't qualify.
    """
    if task.type not in ("feature", "bug"):
        return None

    ws_root = pathlib.Path(workspace_root) / project.slug / "workspace" / ".ai" / "handoff"
    ws_root.mkdir(parents=True, exist_ok=True)

    # Pull linked objective + open/closed decisions
    objective = None
    if task.origin:
        objective = (
            db.query(Objective)
            .filter(Objective.project_id == project.id, Objective.external_id == task.origin)
            .first()
        )

    open_decisions = (
        db.query(Decision)
        .filter(Decision.project_id == project.id, Decision.status == "OPEN")
        .all()
    )
    closed_decisions: list[Decision] = []  # reserved for future use

    content = _render_handoff(task, project, objective, open_decisions, closed_decisions)
    slug = _slug_title(task.name, 40)
    path = ws_root / f"HANDOFF_{task.external_id}-{slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


def export_project_handoffs(
    db: Session,
    project: Project,
    workspace_root: str,
) -> list[pathlib.Path]:
    """Bulk export all feature/bug tasks as Handoff docs. Used in batch hook + manual endpoint."""
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project.id, Task.type.in_(["feature", "bug"]))
        .order_by(Task.id)
        .all()
    )
    written: list[pathlib.Path] = []
    for t in tasks:
        p = export_task_handoff(db, t, project, workspace_root)
        if p:
            written.append(p)
    return written

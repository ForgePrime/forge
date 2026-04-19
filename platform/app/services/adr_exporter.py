"""In-repo ADR exporter — CGAID artifact #5 (.ai/decisions/NNN-*.md).

Every CLOSED Decision is mirrored as a markdown file in the workspace
under .ai/decisions/. Engineers reading a repo checkout can trace
architecture decisions without Forge UI access.

Format follows the Michael-Nygard ADR template:
  ## Status · ## Context · ## Decision · ## Alternatives · ## Consequences

Called from:
  - pipeline.py (auto-extraction that creates CLOSED decisions)
  - execute.py (auto-extraction during delivery)
  - tier1 manual bulk endpoint (disaster recovery / initial sync)
"""
import pathlib
import datetime as dt

from sqlalchemy.orm import Session

from app.models import Project, Decision, Task


def _slug_title(text: str, max_len: int = 50) -> str:
    """Filesystem-safe slug."""
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


def _render_adr(decision: Decision, task_ext_id: str | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = decision.issue[:120] if decision.issue else "(no issue text)"

    lines = [
        f"# {decision.external_id} — {title}",
        "",
        f"*Exported {now} by Forge adr_exporter. Source of truth: Forge DB.*",
        "",
    ]

    # Status
    lines.append("## Status")
    lines.append("")
    lines.append(f"{decision.status}")
    if decision.severity:
        lines.append(f" · severity: {decision.severity}")
    lines.append("")

    # Context (the issue as stated)
    lines.append("## Context")
    lines.append("")
    if decision.issue:
        lines.append(decision.issue.strip())
    else:
        lines.append("(no context captured)")
    lines.append("")

    # Decision (the recommendation taken)
    lines.append("## Decision")
    lines.append("")
    if decision.recommendation:
        lines.append(decision.recommendation.strip())
    else:
        lines.append("(no decision captured)")
    lines.append("")

    # Alternatives — Forge does not currently store explicit alternatives;
    # reasoning often lists them implicitly. Disclose that.
    lines.append("## Alternatives considered")
    lines.append("")
    if decision.reasoning:
        lines.append(decision.reasoning.strip())
    else:
        lines.append("(alternatives not explicitly captured — see Forge DB for session context)")
    lines.append("")

    # Consequences — Forge does not store explicit impact field;
    # disclose what we have and what we lack.
    lines.append("## Consequences")
    lines.append("")
    consequences = []
    if decision.type:
        consequences.append(f"- Type: {decision.type}")
    if decision.confidence:
        consequences.append(f"- Confidence: {decision.confidence}")
    if task_ext_id:
        consequences.append(f"- Linked task: {task_ext_id}")
    if consequences:
        lines.extend(consequences)
    else:
        lines.append("(explicit consequences not captured — propagate via Forge linked findings)")
    lines.append("")

    # Metadata trailer
    lines.append("---")
    lines.append("")
    lines.append(f"*Decision ID: {decision.external_id}*")
    if decision.created_at:
        created = decision.created_at.strftime("%Y-%m-%d")
        lines.append(f"*Created: {created}*")

    return "\n".join(lines)


def export_decision(
    decision: Decision,
    project: Project,
    workspace_root: str,
    task_ext_id: str | None = None,
) -> pathlib.Path | None:
    """Write a single ADR markdown file for the given Decision.

    Only exports CLOSED decisions — OPEN decisions are noise in the in-repo
    record (the decision isn't yet made). Returns path written, or None if
    decision is not CLOSED.
    """
    if decision.status != "CLOSED":
        return None

    ws_root = pathlib.Path(workspace_root) / project.slug / "workspace" / ".ai" / "decisions"
    ws_root.mkdir(parents=True, exist_ok=True)

    slug = _slug_title(decision.issue or "decision", 40)
    filename = f"{decision.external_id}-{slug}.md"
    path = ws_root / filename

    content = _render_adr(decision, task_ext_id=task_ext_id)
    path.write_text(content, encoding="utf-8")
    return path


def export_all_closed_decisions(
    db: Session,
    project: Project,
    workspace_root: str,
) -> list[pathlib.Path]:
    """Bulk export — used for disaster recovery and first-time sync.

    Iterates every CLOSED decision for the project. Returns list of written paths.
    """
    decisions = (
        db.query(Decision)
        .filter(Decision.project_id == project.id, Decision.status == "CLOSED")
        .order_by(Decision.id)
        .all()
    )
    written: list[pathlib.Path] = []

    # Build task lookup to enrich ADRs with linked task external_id
    task_ids_needed = {d.task_id for d in decisions if d.task_id}
    tasks_by_id: dict[int, Task] = {}
    if task_ids_needed:
        tasks = db.query(Task).filter(Task.id.in_(task_ids_needed)).all()
        tasks_by_id = {t.id: t for t in tasks}

    for d in decisions:
        task_ext = tasks_by_id[d.task_id].external_id if d.task_id in tasks_by_id else None
        p = export_decision(d, project, workspace_root, task_ext_id=task_ext)
        if p:
            written.append(p)
    return written

"""In-repo Skill Change Log exporter — CGAID Artifact #8.

CGAID requires "Skill Change Log — what failed, what changed, why,
observed impact". Forge stores the constituent parts across three models:

  ProjectLesson  → what failed / what worked / incidents / insights
  AntiPattern    → named failure modes promoted from lessons
                   (organization-scope, injected into future prompts)
  Skill + ProjectSkill → per-project skill invocation count + cost impact

This exporter aggregates all three into a single markdown timeline
under `{workspace}/.ai/SKILL_CHANGE_LOG.md`. Since Forge does not
currently track BEFORE/AFTER deltas of skill performance (that would
need a SkillRevision snapshot model, deferred), the "observed impact"
column shows the CURRENT state — cost_impact_usd + invocation count.
The doc acknowledges this limitation inline.

Called from:
- Manual endpoint `/api/v1/tier1/projects/{slug}/export/skill-log`
- (future) /compound slash extractor after capturing lessons

Best-effort. Missing DB data → section stays as "(none captured)".
"""
from __future__ import annotations

import pathlib
import datetime as dt
from collections import defaultdict

from sqlalchemy.orm import Session


def _dt_iso(d) -> str:
    try:
        return d.isoformat() if d else ""
    except Exception:
        return ""


def _render_lesson(lesson) -> list[str]:
    lines = [f"### {lesson.title}"]
    lines.append("")
    meta_parts = [f"kind: `{lesson.kind}`"]
    if lesson.objective_external_id:
        meta_parts.append(f"objective: {lesson.objective_external_id}")
    if lesson.source:
        meta_parts.append(f"source: {lesson.source}")
    if lesson.created_at:
        meta_parts.append(f"captured: {lesson.created_at.strftime('%Y-%m-%d')}")
    lines.append(" · ".join(meta_parts))
    if lesson.tags:
        lines.append(f"**tags:** {', '.join(lesson.tags)}")
    lines.append("")
    lines.append(lesson.description.strip() if lesson.description else "*(no description)*")
    lines.append("")
    return lines


def _render_anti_pattern(ap) -> list[str]:
    lines = [f"### {ap.title}"]
    lines.append("")
    lines.append(
        f"active: {'yes' if ap.active else 'no'} · "
        f"seen: {ap.times_seen}× · "
        f"promoted-from-lesson: {'#' + str(ap.promoted_from_lesson_id) if ap.promoted_from_lesson_id else 'none'}"
    )
    if ap.applies_to_kinds:
        lines.append(f"**applies to:** {', '.join(ap.applies_to_kinds)}")
    lines.append("")
    lines.append("**Description:**")
    lines.append("")
    lines.append(ap.description.strip() if ap.description else "*(no description)*")
    lines.append("")
    if ap.example:
        lines.append("**Don't do this:**")
        lines.append("```")
        lines.append(ap.example.strip())
        lines.append("```")
        lines.append("")
    if ap.correct_way:
        lines.append("**Do this instead:**")
        lines.append("```")
        lines.append(ap.correct_way.strip())
        lines.append("```")
        lines.append("")
    return lines


def _render_skill(project_skill, skill) -> list[str]:
    lines = [f"### {skill.name} (`{skill.external_id}`)"]
    lines.append("")
    meta = [f"category: `{skill.category}`"]
    meta.append(f"attach mode: {project_skill.attach_mode}")
    meta.append(f"invocations: {project_skill.invocations}")
    if project_skill.last_used_at:
        meta.append(f"last used: {project_skill.last_used_at.strftime('%Y-%m-%d')}")
    if skill.cost_impact_usd is not None:
        meta.append(f"cost impact: ${skill.cost_impact_usd:.4f}")
    lines.append(" · ".join(meta))
    lines.append("")
    if skill.description:
        lines.append(skill.description.strip())
        lines.append("")
    return lines


def export_skill_change_log(
    db: Session,
    project,
    workspace_root: str,
) -> pathlib.Path | None:
    """Write {workspace}/.ai/SKILL_CHANGE_LOG.md for the given project.

    Returns path written, or None on filesystem failure.
    Idempotent — overwrites existing file.
    """
    from app.models import ProjectLesson, AntiPattern, ProjectSkill, Skill

    now = dt.datetime.now(dt.timezone.utc)

    # --- Query the three sources ---
    lessons = (
        db.query(ProjectLesson)
        .filter(ProjectLesson.project_id == project.id)
        .order_by(ProjectLesson.created_at.desc())
        .all()
    )

    # Anti-patterns are org-scoped; surface active ones for this project's org
    anti_patterns = []
    if project.organization_id:
        anti_patterns = (
            db.query(AntiPattern)
            .filter(
                AntiPattern.organization_id == project.organization_id,
                AntiPattern.active == True,
            )
            .order_by(AntiPattern.times_seen.desc(), AntiPattern.created_at.desc())
            .all()
        )

    project_skills_rows = (
        db.query(ProjectSkill, Skill)
        .join(Skill, Skill.id == ProjectSkill.skill_id)
        .filter(ProjectSkill.project_id == project.id)
        .order_by(ProjectSkill.invocations.desc())
        .all()
    )

    # --- Render ---
    lines: list[str] = [
        f"# Skill Change Log — {project.slug}",
        "",
        f"*Auto-generated {now.strftime('%Y-%m-%d %H:%M UTC')} by Forge skill_log_exporter.*",
        f"*CGAID Artifact #8. Source of truth: Forge DB.*",
        "",
        "This document records what we've learned, what we've stopped doing,",
        "and which skills are pulling their weight. It is the **observed-impact**",
        "counterpart to the prescriptive framework manifest (docs/FORGE_FRAMEWORK_MANIFEST.md).",
        "",
        "**Known limitation:** Forge does not yet track BEFORE/AFTER deltas of",
        "skill performance. The \"observed impact\" section below shows CURRENT",
        "state (cost_impact_usd + invocations). Historic performance snapshots",
        "would require a `SkillRevision` model — deferred.",
        "",
        "---",
        "",
    ]

    # Section 1 — What failed / worked (lessons grouped by kind)
    by_kind: dict[str, list] = defaultdict(list)
    for ls in lessons:
        by_kind[ls.kind].append(ls)

    lines.append("## 1. What failed / what worked (project lessons)")
    lines.append("")
    if not lessons:
        lines.append("*(no lessons captured yet — run `/compound` on an ACHIEVED objective)*")
        lines.append("")
    else:
        kind_order = ["incident", "didnt_work", "worked", "insight"]
        kind_titles = {
            "incident": "Incidents",
            "didnt_work": "What didn't work",
            "worked": "What worked",
            "insight": "Insights",
        }
        for k in kind_order:
            items = by_kind.get(k, [])
            if not items:
                continue
            lines.append(f"### {kind_titles[k]} ({len(items)})")
            lines.append("")
            for ls in items:
                lines.extend(_render_lesson(ls))

    # Section 2 — What changed (org-level anti-patterns)
    lines.append("## 2. What changed (anti-patterns promoted from lessons)")
    lines.append("")
    if not anti_patterns:
        lines.append("*(no active anti-patterns — none promoted from lessons yet)*")
        lines.append("")
    else:
        lines.append(
            "These org-level rules are injected into future LLM prompts for "
            "every project in this organization."
        )
        lines.append("")
        for ap in anti_patterns:
            lines.extend(_render_anti_pattern(ap))

    # Section 3 — Observed impact (skills pulling their weight)
    lines.append("## 3. Observed impact (per-project skill performance)")
    lines.append("")
    if not project_skills_rows:
        lines.append("*(no skills attached to this project yet)*")
        lines.append("")
    else:
        total_invocations = sum(ps.invocations for ps, _ in project_skills_rows)
        total_cost = sum((sk.cost_impact_usd or 0) for _, sk in project_skills_rows)
        lines.append(
            f"**Summary:** {len(project_skills_rows)} skill(s) attached, "
            f"{total_invocations} total invocations, "
            f"cumulative cost impact ${total_cost:.4f}."
        )
        lines.append("")
        for ps, sk in project_skills_rows:
            lines.extend(_render_skill(ps, sk))

    # Trailer
    lines.append("---")
    lines.append("")
    lines.append("## Changelog of this document")
    lines.append("")
    lines.append(
        f"- **{now.strftime('%Y-%m-%d')}** — auto-regenerated ({len(lessons)} lessons, "
        f"{len(anti_patterns)} active anti-patterns, {len(project_skills_rows)} attached skills)"
    )

    # --- Write ---
    ws_root = pathlib.Path(workspace_root) / project.slug / "workspace" / ".ai"
    ws_root.mkdir(parents=True, exist_ok=True)
    path = ws_root / "SKILL_CHANGE_LOG.md"
    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        return None
    return path

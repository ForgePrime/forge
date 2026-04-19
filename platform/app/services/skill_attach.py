"""Auto-attach rule engine for skills (F6 / mockup 11).

A skill has an optional `auto_attach_rule` JSONB, e.g.:
  {"if_task_type": ["develop"], "if_phase": ["challenger"],
   "if_diff_touches": ["auth/", "api/"], "if_language": "python"}

This engine:
  1. Loads the org+project's active skills
  2. Evaluates rules against a TaskContext
  3. Returns ordered list of skills to inject into the prompt

V0: supports if_task_type, if_phase, if_project_kind. No diff/language inspection yet
(requires runtime info).  Emits a `record-invocation` against each matched skill so
F3 ROI tracking stays accurate.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import ProjectSkill, Skill


@dataclass
class TaskContext:
    project_id: int
    task_type: str | None          # 'analysis' | 'planning' | 'develop' | 'documentation' | legacy
    phase: str | None              # 'challenger' | 'execute' | ...
    files_touched: list[str] | None = None
    language: str | None = None    # 'python' | 'node' | ...


def _rule_matches(rule: dict | None, ctx: TaskContext) -> bool:
    if not rule:
        # No rule = opt-in manual only.
        return False
    # if_task_type
    if "if_task_type" in rule:
        if (ctx.task_type or "") not in (rule["if_task_type"] or []):
            return False
    # if_phase
    if "if_phase" in rule:
        if (ctx.phase or "") not in (rule["if_phase"] or []):
            return False
    # if_language
    if "if_language" in rule:
        if (ctx.language or "") != rule["if_language"]:
            return False
    # if_diff_touches — any path prefix match
    if "if_diff_touches" in rule and ctx.files_touched:
        needles = rule["if_diff_touches"] or []
        if not any(any(n in p for n in needles) for p in ctx.files_touched):
            return False
    return True


def resolve_skills(db: Session, ctx: TaskContext) -> list[Skill]:
    """Return list of Skills to attach for this task context."""
    # Candidates: project-attached skills (manual or auto or default)
    project_skill_rows = db.query(ProjectSkill, Skill).join(
        Skill, ProjectSkill.skill_id == Skill.id
    ).filter(ProjectSkill.project_id == ctx.project_id).all()
    selected: list[Skill] = []
    # Manual/default attachments always apply (phase-filtered by applies_to_phases)
    for ps, sk in project_skill_rows:
        if ps.attach_mode in ("manual", "default"):
            if ctx.phase and sk.applies_to_phases and ctx.phase not in sk.applies_to_phases:
                continue
            selected.append(sk)
        elif ps.attach_mode == "auto":
            if _rule_matches(sk.auto_attach_rule, ctx):
                selected.append(sk)
    # Built-in skills not yet attached to project — only apply if their rule matches
    # AND their phase matches.
    attached_ids = {sk.id for _ps, sk in project_skill_rows}
    builtins = db.query(Skill).filter(Skill.is_built_in == True).all()
    for sk in builtins:
        if sk.id in attached_ids:
            continue
        if not _rule_matches(sk.auto_attach_rule, ctx):
            continue
        if ctx.phase and sk.applies_to_phases and ctx.phase not in sk.applies_to_phases:
            continue
        selected.append(sk)
    # De-dupe by id preserving order
    seen: set[int] = set()
    uniq: list[Skill] = []
    for sk in selected:
        if sk.id in seen:
            continue
        seen.add(sk.id); uniq.append(sk)
    return uniq


def record_invocations(db: Session, project_id: int, skills: list[Skill]) -> None:
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    for sk in skills:
        link = db.query(ProjectSkill).filter(
            ProjectSkill.project_id == project_id,
            ProjectSkill.skill_id == sk.id,
        ).first()
        if link:
            link.invocations += 1
            link.last_used_at = now
    db.commit()

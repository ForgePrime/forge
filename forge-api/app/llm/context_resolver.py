"""LLM Context Resolver — resolves entity context for LLM system prompts.

Each module provides context data that gets injected into the system prompt.
The resolver loads the entity by type + id, extracts relevant data,
and builds a ContextPayload for prompt assembly.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Max content length to prevent token explosion
MAX_CONTENT_LENGTH = 8000


@dataclass
class ContextPayload:
    """Resolved context for LLM system prompt."""

    context_type: str
    context_id: str
    title: str = ""
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    related: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""

    def to_system_prompt(self) -> str:
        """Build system prompt string from this context."""
        if self.system_prompt:
            return self.system_prompt

        parts = [f"User is working on {self.context_type} {self.context_id}"]
        if self.title:
            parts[0] += f": {self.title}"
        parts[0] += "."

        if self.summary:
            parts.append(self.summary)

        if self.data:
            parts.append(f"Current state: {_truncate_dict(self.data)}")

        if self.related:
            related_summary = ", ".join(
                f"{r.get('type', '?')} {r.get('id', '?')}: {r.get('title', '')}"
                for r in self.related[:5]
            )
            parts.append(f"Related: {related_summary}")

        parts.append("Use available tools to help the user.")
        return "\n\n".join(parts)


class ContextResolver:
    """Resolves entity context for LLM system prompts.

    Usage::

        resolver = ContextResolver(storage)
        payload = await resolver.resolve("skill", "SK-001")
        system_prompt = payload.to_system_prompt()
    """

    def __init__(self, storage: Any) -> None:
        self._storage = storage

    async def resolve(
        self,
        context_type: str,
        context_id: str,
        project: str = "",
        scopes: list[str] | None = None,
    ) -> ContextPayload:
        """Resolve context by type and id.

        Args:
            context_type: Entity type (skill, task, objective, idea, etc.)
            context_id: Entity ID (SK-001, T-003, etc.)
            project: Project slug (required for project-scoped entities).
            scopes: Active frontend scopes (used for guideline loading).

        Returns:
            ContextPayload with entity data for system prompt.
        """
        resolver = _RESOLVERS.get(context_type, _resolve_generic)
        try:
            payload = await resolver(self._storage, context_type, context_id, project)
        except Exception as e:
            logger.warning("Context resolution failed for %s %s: %s", context_type, context_id, e)
            return ContextPayload(
                context_type=context_type,
                context_id=context_id,
                title=f"(failed to load: {type(e).__name__})",
            )

        # Always enrich with project context and guidelines
        if project:
            await self._enrich_with_project_context(payload, project, scopes)

        return payload

    async def _enrich_with_project_context(
        self,
        payload: ContextPayload,
        project: str,
        scopes: list[str] | None,
    ) -> None:
        """Add project info and scoped guidelines to any context payload."""
        parts: list[str] = []

        # --- Project info ---
        try:
            tracker = await asyncio.to_thread(self._storage.load_data, project, "tracker")
            goal = tracker.get("goal", "")
            tasks = tracker.get("tasks", [])
            done = sum(1 for t in tasks if t.get("status") == "DONE")
            todo = sum(1 for t in tasks if t.get("status") == "TODO")
            in_prog = sum(1 for t in tasks if t.get("status") == "IN_PROGRESS")
            parts.append(
                f"Project: {project}"
                + (f" — {goal}" if goal else "")
                + f"\nTasks: {done} done, {in_prog} in progress, {todo} todo"
            )
        except Exception:
            parts.append(f"Project: {project}")

        # --- Active scopes ---
        if scopes:
            parts.append(f"Active scopes: {', '.join(scopes)}")

        # --- Guidelines (global + scoped) ---
        try:
            g_data = await asyncio.to_thread(self._storage.load_data, project, "guidelines")
            guidelines = g_data.get("guidelines", [])
            active = [g for g in guidelines if g.get("status", "ACTIVE") == "ACTIVE"]

            # Determine which scopes to load guidelines for
            target_scopes = {"general"}
            if scopes:
                target_scopes.update(scopes)

            matched = [g for g in active if g.get("scope") in target_scopes]
            if matched:
                g_lines = []
                for g in matched[:20]:  # Limit to prevent token explosion
                    weight = g.get("weight", "should")
                    scope = g.get("scope", "general")
                    title = g.get("title", "")
                    content = g.get("content", "")
                    g_lines.append(f"- [{weight}] [{scope}] {title}: {_truncate(content, 200)}")
                parts.append(f"Guidelines ({len(matched)}):\n" + "\n".join(g_lines))
        except Exception:
            pass

        if parts:
            enrichment = "\n\n".join(parts)
            if payload.system_prompt:
                payload.system_prompt = enrichment + "\n\n" + payload.system_prompt
            else:
                # Prepend to the generated prompt
                payload.summary = enrichment + ("\n\n" + payload.summary if payload.summary else "")


# ---------------------------------------------------------------------------
# Type-specific resolvers
# ---------------------------------------------------------------------------

async def _resolve_skill(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Resolve skill context — full content + metadata."""
    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == context_id:
            content = skill.get("skill_md_content", "")
            resources = skill.get("resources") or {}
            skill_files = resources.get("files") or []
            file_listing = [
                f"{f['path']} ({f.get('file_type', 'other')})"
                for f in skill_files if isinstance(f, dict) and "path" in f
            ]

            data: dict[str, Any] = {
                "content": _truncate(content, MAX_CONTENT_LENGTH),
                "categories": skill.get("categories", []),
                "tags": skill.get("tags", []),
                "scopes": skill.get("scopes", []),
                "status": skill.get("status", ""),
            }
            if file_listing:
                data["bundled_files"] = file_listing
                data["file_tools"] = (
                    "Use listSkillFiles, getSkillFileContent, addSkillFile, "
                    "removeSkillFile to manage bundled files."
                )
            data["ac_tools"] = (
                "Use instantiateACTemplate to fill an AC template with concrete "
                "parameters and get structured acceptance criteria text."
            )
            data["preview_tools"] = (
                "Use previewSkill to render a full markdown preview of the current "
                "skill including frontmatter metadata, body content, and file counts."
            )

            return ContextPayload(
                context_type="skill",
                context_id=context_id,
                title=skill.get("name", ""),
                summary=skill.get("description", ""),
                data=data,
            )

    return ContextPayload(context_type="skill", context_id=context_id, title="(not found)")


async def _resolve_task(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Resolve task context — description, deps, guidelines, knowledge."""
    if not project:
        return ContextPayload(context_type="task", context_id=context_id, title="(project required)")

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    tasks = tracker.get("tasks", [])

    task = None
    for t in tasks:
        if t.get("id") == context_id:
            task = t
            break

    if task is None:
        return ContextPayload(context_type="task", context_id=context_id, title="(not found)")

    # Load related entities
    related: list[dict[str, Any]] = []

    # Dependencies
    for dep_id in task.get("depends_on", []):
        for t in tasks:
            if t.get("id") == dep_id:
                related.append({
                    "type": "task",
                    "id": dep_id,
                    "title": t.get("name", ""),
                    "status": t.get("status", ""),
                })
                break

    # Guidelines by scopes (always include "general")
    scopes = set(task.get("scopes", [])) | {"general"}
    if scopes:
        try:
            guidelines_data = await asyncio.to_thread(storage.load_data, project, "guidelines")
            for g in guidelines_data.get("guidelines", []):
                if g.get("scope") in scopes and g.get("status", "ACTIVE") == "ACTIVE":
                    related.append({
                        "type": "guideline",
                        "id": g.get("id", ""),
                        "title": g.get("title", ""),
                        "weight": g.get("weight", ""),
                    })
        except Exception:
            pass

    return ContextPayload(
        context_type="task",
        context_id=context_id,
        title=task.get("name", ""),
        summary=task.get("description", ""),
        data={
            "instruction": _truncate(task.get("instruction", ""), 2000),
            "status": task.get("status", ""),
            "type": task.get("type", ""),
            "acceptance_criteria": task.get("acceptance_criteria", []),
            "scopes": scopes,
        },
        related=related,
    )


async def _resolve_objective(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Resolve objective context — KRs, linked ideas."""
    if not project:
        return ContextPayload(context_type="objective", context_id=context_id, title="(project required)")

    obj_data = await asyncio.to_thread(storage.load_data, project, "objectives")
    objectives = obj_data.get("objectives", [])

    obj = None
    for o in objectives:
        if o.get("id") == context_id:
            obj = o
            break

    if obj is None:
        return ContextPayload(context_type="objective", context_id=context_id, title="(not found)")

    # Find linked ideas
    related: list[dict[str, Any]] = []
    try:
        ideas_data = await asyncio.to_thread(storage.load_data, project, "ideas")
        for idea in ideas_data.get("ideas", []):
            akr = idea.get("advances_key_results", [])
            if any(kr.startswith(context_id) for kr in akr):
                related.append({
                    "type": "idea",
                    "id": idea.get("id", ""),
                    "title": idea.get("title", ""),
                    "status": idea.get("status", ""),
                })
    except Exception:
        pass

    return ContextPayload(
        context_type="objective",
        context_id=context_id,
        title=obj.get("title", ""),
        summary=obj.get("description", ""),
        data={
            "status": obj.get("status", ""),
            "key_results": obj.get("key_results", []),
            "appetite": obj.get("appetite", ""),
            "assumptions": obj.get("assumptions", []),
        },
        related=related,
    )


async def _resolve_idea(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Resolve idea context — children, decisions, relations."""
    if not project:
        return ContextPayload(context_type="idea", context_id=context_id, title="(project required)")

    ideas_data = await asyncio.to_thread(storage.load_data, project, "ideas")
    ideas = ideas_data.get("ideas", [])

    idea = None
    for i in ideas:
        if i.get("id") == context_id:
            idea = i
            break

    if idea is None:
        return ContextPayload(context_type="idea", context_id=context_id, title="(not found)")

    # Find children
    related: list[dict[str, Any]] = []
    for i in ideas:
        if i.get("parent_id") == context_id:
            related.append({
                "type": "idea",
                "id": i.get("id", ""),
                "title": i.get("title", ""),
                "status": i.get("status", ""),
            })

    # Find decisions linked to this idea
    try:
        decisions_data = await asyncio.to_thread(storage.load_data, project, "decisions")
        for d in decisions_data.get("decisions", []):
            if d.get("linked_entity_id") == context_id:
                related.append({
                    "type": "decision",
                    "id": d.get("id", ""),
                    "title": d.get("title", ""),
                    "status": d.get("status", ""),
                })
    except Exception:
        pass

    return ContextPayload(
        context_type="idea",
        context_id=context_id,
        title=idea.get("title", ""),
        summary=idea.get("description", ""),
        data={
            "status": idea.get("status", ""),
            "category": idea.get("category", ""),
            "advances_key_results": idea.get("advances_key_results", []),
            "scopes": idea.get("scopes", []),
        },
        related=related,
    )


async def _resolve_knowledge(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Resolve knowledge context — content, versions, links."""
    if not project:
        return ContextPayload(context_type="knowledge", context_id=context_id, title="(project required)")

    k_data = await asyncio.to_thread(storage.load_data, project, "knowledge")
    items = k_data.get("knowledge", [])

    item = None
    for k in items:
        if k.get("id") == context_id:
            item = k
            break

    if item is None:
        return ContextPayload(context_type="knowledge", context_id=context_id, title="(not found)")

    return ContextPayload(
        context_type="knowledge",
        context_id=context_id,
        title=item.get("title", ""),
        summary=item.get("description", ""),
        data={
            "status": item.get("status", ""),
            "category": item.get("category", ""),
            "content": _truncate(item.get("content", ""), MAX_CONTENT_LENGTH),
            "scope": item.get("scope", ""),
            "links": item.get("links", []),
        },
    )


async def _resolve_global(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Resolve global context — used when no specific entity is selected."""
    return ContextPayload(
        context_type="global",
        context_id="",
        title="Forge Assistant",
        system_prompt=(
            "You are the Forge AI assistant for structured software development.\n\n"
            "## Entity Model\n"
            "Objective (O-NNN) → Idea (I-NNN) → Task (T-NNN) → Decision (D-NNN) / Change (C-NNN) → Lesson (L-NNN)\n"
            "Supporting: Guideline (G-NNN), Knowledge (K-NNN), Research (R-NNN)\n"
            "- Objectives have Key Results (KR). Ideas advance KRs.\n"
            "- Tasks inherit scopes from origin idea/objective. Guidelines load by scope.\n"
            "- Decisions record choices. Changes record file modifications.\n\n"
            "## Workflow Stages\n"
            "1. **Define** — createObjective (title, key_results, scopes)\n"
            "2. **Propose** — createIdea (title, advances_key_results, scopes)\n"
            "3. **Assess** — createDecision type=exploration/risk\n"
            "4. **Plan** — createTask (name, depends_on, scopes, origin)\n"
            "5. **Execute** — updateTask (status), recordChange, createDecision type=implementation\n"
            "6. **Verify** — completeTask, createGuideline (derived standards)\n"
            "7. **Learn** — createLesson, updateObjective (KR progress)\n\n"
            "## Tools by Category\n"
            "**Query**: searchEntities, getEntity, listEntities, getProject\n"
            "**Objectives**: createObjective, updateObjective\n"
            "**Ideas**: createIdea, updateIdea\n"
            "**Planning**: draftPlan, showDraft, approvePlan\n"
            "**Tasks**: createTask, updateTask, completeTask\n"
            "**Decisions**: createDecision, updateDecision\n"
            "**Knowledge**: createKnowledge, updateKnowledge\n"
            "**Guidelines**: createGuideline, updateGuideline\n"
            "**Lessons**: createLesson\n"
            "**Changes**: recordChange\n"
            "**Skills**: updateSkillContent, updateSkillMetadata, runSkillLint, "
            "addSkillFile, removeSkillFile, listSkillFiles, getSkillFileContent, previewSkill\n\n"
            "## Rules\n"
            "- Use tools to act, don't just describe what to do.\n"
            "- Respect MUST guidelines strictly. Follow SHOULD unless documented reason.\n"
            "- Record decisions for non-trivial choices (architecture, trade-offs).\n"
            "- When creating tasks, set origin to the source idea/objective ID."
        ),
    )


async def _resolve_generic(
    storage: Any, context_type: str, context_id: str, project: str,
) -> ContextPayload:
    """Fallback resolver — tries to load entity from standard storage locations."""
    # Map context_type to storage key
    type_map = {
        "decision": ("decisions", "decisions"),
        "guideline": ("guidelines", "guidelines"),
        "lesson": ("lessons", "lessons"),
        "change": ("changes", "changes"),
        "ac_template": ("ac_templates", "ac_templates"),
    }

    mapping = type_map.get(context_type)
    if mapping is None:
        logger.warning("Unknown context_type for generic resolver: %s", context_type)
        storage_key, list_key = context_type, context_type
    else:
        storage_key, list_key = mapping

    if not context_id:
        # No specific entity — return generic context for this type
        return ContextPayload(
            context_type=context_type,
            context_id="",
            title=f"{context_type} context",
        )

    try:
        if project:
            data = await asyncio.to_thread(storage.load_data, project, storage_key)
        else:
            data = await asyncio.to_thread(storage.load_global, storage_key)
    except Exception:
        return ContextPayload(context_type=context_type, context_id=context_id, title="(not found)")

    items = data.get(list_key, [])
    for item in items:
        if item.get("id") == context_id:
            title = item.get("title", item.get("name", ""))
            return ContextPayload(
                context_type=context_type,
                context_id=context_id,
                title=title,
                summary=item.get("description", ""),
                data={
                    k: _truncate(v, MAX_CONTENT_LENGTH) if isinstance(v, str) else v
                    for k, v in item.items()
                    if k not in ("id", "title", "name", "description")
                },
            )

    return ContextPayload(context_type=context_type, context_id=context_id, title="(not found)")


# Resolver dispatch map
_RESOLVERS = {
    "global": _resolve_global,
    "skill": _resolve_skill,
    "task": _resolve_task,
    "objective": _resolve_objective,
    "idea": _resolve_idea,
    "knowledge": _resolve_knowledge,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length with ellipsis."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def _truncate_dict(data: dict[str, Any], max_str_length: int = 500) -> str:
    """Convert dict to compact string, truncating long values."""
    import json
    try:
        text = json.dumps(data, ensure_ascii=False, default=str)
        return _truncate(text, max_str_length)
    except (TypeError, ValueError):
        return str(data)[:max_str_length]

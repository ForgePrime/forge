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
    ) -> ContextPayload:
        """Resolve context by type and id.

        Args:
            context_type: Entity type (skill, task, objective, idea, etc.)
            context_id: Entity ID (SK-001, T-003, etc.)
            project: Project slug (required for project-scoped entities).

        Returns:
            ContextPayload with entity data for system prompt.
        """
        resolver = _RESOLVERS.get(context_type, _resolve_generic)
        try:
            return await resolver(self._storage, context_type, context_id, project)
        except Exception as e:
            logger.warning("Context resolution failed for %s %s: %s", context_type, context_id, e)
            return ContextPayload(
                context_type=context_type,
                context_id=context_id,
                title=f"(failed to load: {type(e).__name__})",
            )


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

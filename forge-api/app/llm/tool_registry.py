"""LLM Tool Registry — defines and manages tools available to LLM agents.

Tools are JSON Schema-defined functions that map to Forge API operations.
The registry resolves which tools are available based on context type
and permissions.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from core.llm.provider import ToolDefinition

from app.llm.permissions import PermissionSet


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

@dataclass
class ToolDef:
    """A tool definition with metadata for permission checking."""

    name: str
    description: str
    parameters: dict  # JSON Schema
    required_permission: tuple[str, str] | None = None  # (module, action)
    context_types: list[str] = field(default_factory=lambda: ["global"])
    handler: Callable[..., Awaitable[dict]] | None = None

    def to_llm_definition(self) -> ToolDefinition:
        """Convert to core.llm.provider.ToolDefinition for LLM calls."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Manages tools available to LLM agents.

    Tools are registered with context type filters. At runtime,
    get_tools() returns only tools applicable to the current context
    and permitted by the permission engine.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool

    def get_tools(
        self,
        context_type: str = "global",
        permissions: dict[str, dict[str, bool]] | None = None,
    ) -> list[ToolDef]:
        """Return tools available for a context type, filtered by permissions.

        Args:
            context_type: The entity context ("global", "skill", "task", etc.)
            permissions: Module permission map {module: {read, write, delete}}.
                         If None, all tools are returned.
        """
        result = []
        for tool in self._tools.values():
            # Filter by context type
            if "global" not in tool.context_types and context_type not in tool.context_types:
                continue

            # Filter by permissions
            if permissions is not None and tool.required_permission is not None:
                module, action = tool.required_permission
                module_perms = permissions.get(module, {})
                if not module_perms.get(action, False):
                    continue

            result.append(tool)
        return result

    def get_tool(self, name: str) -> ToolDef | None:
        """Get a single tool by name."""
        return self._tools.get(name)

    async def execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        storage: Any,
        context: dict[str, Any] | None = None,
        permission_set: PermissionSet | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: The tool name to execute.
            args: Tool input arguments.
            storage: The storage adapter.
            context: Optional execution context (project, entity info, etc.)
            permission_set: Optional PermissionSet for permission checking.

        Returns:
            Structured result dict.

        Raises:
            ValueError: If tool not found.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        if tool.handler is None:
            raise ValueError(f"Tool {tool_name} has no handler")

        # Permission check for tools that require it
        if tool.required_permission is not None and permission_set is not None:
            module, action = tool.required_permission
            if not permission_set.check(module, action):
                from app.llm.permissions import PermissionEngine
                return PermissionEngine.deny_response(module, action)

        return await tool.handler(args=args, storage=storage, context=context or {})

    def get_llm_definitions(
        self,
        context_type: str = "global",
        permissions: dict[str, dict[str, bool]] | None = None,
    ) -> list[ToolDefinition]:
        """Get ToolDefinition list for LLM provider calls."""
        return [t.to_llm_definition() for t in self.get_tools(context_type, permissions)]


# ---------------------------------------------------------------------------
# Tool handlers — wrap existing Forge API logic
# ---------------------------------------------------------------------------

async def _handle_search_entities(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Search entities by type and query string."""
    entity_type = args.get("entity_type", "tasks")
    query = args.get("query", "").lower()
    project = args.get("project") or context.get("project")
    filters = args.get("filters", {})

    # Map entity types to their storage entity and list key
    entity_map = {
        "tasks": ("tracker", "tasks"),
        "decisions": ("decisions", "decisions"),
        "guidelines": ("guidelines", "guidelines"),
        "ideas": ("ideas", "ideas"),
        "knowledge": ("knowledge", "knowledge"),
        "objectives": ("objectives", "objectives"),
        "changes": ("changes", "changes"),
        "lessons": ("lessons", "lessons"),
        "skills": (None, "skills"),  # global entity
    }

    if entity_type not in entity_map:
        return {"error": f"Unknown entity type: {entity_type}", "results": []}

    storage_key, list_key = entity_map[entity_type]

    if storage_key is None:
        # Global entity (skills)
        data = await asyncio.to_thread(storage.load_global, entity_type)
    else:
        if not project:
            return {"error": "project is required for project-scoped entities", "results": []}
        data = await asyncio.to_thread(storage.load_data, project, storage_key)

    items = data.get(list_key, [])

    # Apply text search
    if query:
        items = [
            item for item in items
            if query in str(item.get("name", "")).lower()
            or query in str(item.get("title", "")).lower()
            or query in str(item.get("description", "")).lower()
            or query in str(item.get("id", "")).lower()
        ]

    # Apply filters
    for key, value in filters.items():
        items = [item for item in items if item.get(key) == value]

    # Limit results
    items = items[:20]

    return {"entity_type": entity_type, "results": items, "count": len(items)}


async def _handle_get_entity(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get a single entity by type and ID."""
    entity_type = args.get("entity_type", "tasks")
    entity_id = args.get("entity_id", "")
    project = args.get("project") or context.get("project")

    entity_map = {
        "tasks": ("tracker", "tasks"),
        "decisions": ("decisions", "decisions"),
        "guidelines": ("guidelines", "guidelines"),
        "ideas": ("ideas", "ideas"),
        "knowledge": ("knowledge", "knowledge"),
        "objectives": ("objectives", "objectives"),
        "changes": ("changes", "changes"),
        "lessons": ("lessons", "lessons"),
        "skills": (None, "skills"),
    }

    if entity_type not in entity_map:
        return {"error": f"Unknown entity type: {entity_type}"}

    storage_key, list_key = entity_map[entity_type]

    if storage_key is None:
        data = await asyncio.to_thread(storage.load_global, entity_type)
    else:
        if not project:
            return {"error": "project is required for project-scoped entities"}
        data = await asyncio.to_thread(storage.load_data, project, storage_key)

    items = data.get(list_key, [])
    for item in items:
        if item.get("id") == entity_id:
            return {"entity": item}

    return {"error": f"{entity_type} {entity_id} not found"}


async def _handle_list_entities(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """List entities of a given type with optional filters."""
    entity_type = args.get("entity_type", "tasks")
    project = args.get("project") or context.get("project")
    filters = args.get("filters", {})

    entity_map = {
        "tasks": ("tracker", "tasks"),
        "decisions": ("decisions", "decisions"),
        "guidelines": ("guidelines", "guidelines"),
        "ideas": ("ideas", "ideas"),
        "knowledge": ("knowledge", "knowledge"),
        "objectives": ("objectives", "objectives"),
        "changes": ("changes", "changes"),
        "lessons": ("lessons", "lessons"),
        "skills": (None, "skills"),
    }

    if entity_type not in entity_map:
        return {"error": f"Unknown entity type: {entity_type}", "items": []}

    storage_key, list_key = entity_map[entity_type]

    if storage_key is None:
        data = await asyncio.to_thread(storage.load_global, entity_type)
    else:
        if not project:
            return {"error": "project is required for project-scoped entities", "items": []}
        data = await asyncio.to_thread(storage.load_data, project, storage_key)

    items = data.get(list_key, [])

    # Apply filters
    for key, value in filters.items():
        items = [item for item in items if item.get(key) == value]

    return {"entity_type": entity_type, "items": items, "count": len(items)}


async def _handle_get_project(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get project overview — tasks summary, status counts."""
    slug = args.get("slug") or context.get("project")
    if not slug:
        return {"error": "slug is required"}

    try:
        tracker = await asyncio.to_thread(storage.load_data, slug, "tracker")
    except Exception:
        return {"error": f"Project '{slug}' not found"}

    tasks = tracker.get("tasks", [])
    status_counts: dict[str, int] = {}
    for task in tasks:
        status = task.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "project": slug,
        "goal": tracker.get("goal", ""),
        "task_count": len(tasks),
        "status_counts": status_counts,
    }


# ---------------------------------------------------------------------------
# Skill-specific tool handlers
# ---------------------------------------------------------------------------

async def _handle_update_skill_content(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Update a skill's content (the SKILL.md body)."""
    from app.routers._helpers import _get_lock

    skill_id = args.get("skill_id") or context.get("entity_id")
    content = args.get("content", "")

    if not skill_id:
        return {"error": "skill_id is required"}

    async with _get_lock("_global", "skills"):
        data = await asyncio.to_thread(storage.load_global, "skills")
        skills = data.get("skills", [])

        for skill in skills:
            if skill.get("id") == skill_id:
                skill["content"] = content
                await asyncio.to_thread(storage.save_global, "skills", data)
                return {"updated": True, "skill_id": skill_id}

    return {"error": f"Skill {skill_id} not found"}


async def _handle_update_skill_metadata(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Update a skill's metadata (category, tags, scopes)."""
    from app.routers._helpers import _get_lock

    skill_id = args.get("skill_id") or context.get("entity_id")
    if not skill_id:
        return {"error": "skill_id is required"}

    async with _get_lock("_global", "skills"):
        data = await asyncio.to_thread(storage.load_global, "skills")
        skills = data.get("skills", [])

        for skill in skills:
            if skill.get("id") == skill_id:
                if "category" in args and args["category"] is not None:
                    skill["category"] = args["category"]
                if "tags" in args and args["tags"] is not None:
                    skill["tags"] = args["tags"]
                if "scopes" in args and args["scopes"] is not None:
                    skill["scopes"] = args["scopes"]
                await asyncio.to_thread(storage.save_global, "skills", data)
                return {"updated": True, "skill_id": skill_id, "skill": skill}

    return {"error": f"Skill {skill_id} not found"}


async def _handle_run_skill_lint(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Run TESLint on a skill."""
    skill_id = args.get("skill_id") or context.get("entity_id")
    if not skill_id:
        return {"error": "skill_id is required"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    skill = None
    for s in skills:
        if s.get("id") == skill_id:
            skill = s
            break

    if skill is None:
        return {"error": f"Skill {skill_id} not found"}

    content = skill.get("content", "")
    if not content:
        return {"error": "Skill has no content to lint", "skill_id": skill_id}

    try:
        from app.services.teslint import run_teslint
        skill_name = skill.get("name", skill_id)
        teslint_config = skill.get("teslint_config")
        result = await asyncio.to_thread(run_teslint, skill_name, content, teslint_config)
        return {
            "skill_id": skill_id,
            "success": result.success,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "findings": [
                {"rule": f.rule, "severity": f.severity, "message": f.message, "line": f.line}
                for f in (result.findings or [])
            ],
            "error": result.error_message,
        }
    except Exception as e:
        return {"error": f"Lint failed: {e}", "skill_id": skill_id}


async def _handle_get_other_skill(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get another skill's content (read-only reference)."""
    skill_id = args.get("skill_id", "")
    if not skill_id:
        return {"error": "skill_id is required"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == skill_id:
            return {
                "skill_id": skill_id,
                "name": skill.get("name", ""),
                "category": skill.get("category", ""),
                "content": skill.get("content", ""),
                "tags": skill.get("tags", []),
            }

    return {"error": f"Skill {skill_id} not found"}


# ---------------------------------------------------------------------------
# Default registry factory
# ---------------------------------------------------------------------------

def create_default_registry() -> ToolRegistry:
    """Create a ToolRegistry with all built-in tools registered."""
    registry = ToolRegistry()

    # --- Global tools (always available) ---

    registry.register(ToolDef(
        name="searchEntities",
        description="Search Forge entities (tasks, decisions, guidelines, skills, etc.) by text query and optional filters.",
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["tasks", "decisions", "guidelines", "ideas", "knowledge", "objectives", "changes", "lessons", "skills"],
                    "description": "The type of entity to search.",
                },
                "query": {
                    "type": "string",
                    "description": "Text to search for in name, title, description, or ID.",
                },
                "project": {
                    "type": "string",
                    "description": "Project slug (required for project-scoped entities, not needed for skills).",
                },
                "filters": {
                    "type": "object",
                    "description": "Key-value filters to apply (e.g., {\"status\": \"TODO\"}).",
                    "additionalProperties": True,
                },
            },
            "required": ["entity_type"],
        },
        context_types=["global"],
        required_permission=None,  # read-only, no permission needed
        handler=_handle_search_entities,
    ))

    registry.register(ToolDef(
        name="getEntity",
        description="Get a single Forge entity by type and ID.",
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["tasks", "decisions", "guidelines", "ideas", "knowledge", "objectives", "changes", "lessons", "skills"],
                    "description": "The type of entity to retrieve.",
                },
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID (e.g., T-001, D-003, SK-012).",
                },
                "project": {
                    "type": "string",
                    "description": "Project slug (required for project-scoped entities).",
                },
            },
            "required": ["entity_type", "entity_id"],
        },
        context_types=["global"],
        required_permission=None,
        handler=_handle_get_entity,
    ))

    registry.register(ToolDef(
        name="listEntities",
        description="List all entities of a given type with optional filters.",
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["tasks", "decisions", "guidelines", "ideas", "knowledge", "objectives", "changes", "lessons", "skills"],
                    "description": "The type of entity to list.",
                },
                "project": {
                    "type": "string",
                    "description": "Project slug (required for project-scoped entities).",
                },
                "filters": {
                    "type": "object",
                    "description": "Key-value filters (e.g., {\"status\": \"ACTIVE\"}).",
                    "additionalProperties": True,
                },
            },
            "required": ["entity_type"],
        },
        context_types=["global"],
        required_permission=None,
        handler=_handle_list_entities,
    ))

    registry.register(ToolDef(
        name="getProject",
        description="Get project overview — goal, task counts, status breakdown.",
        parameters={
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "The project slug.",
                },
            },
            "required": ["slug"],
        },
        context_types=["global"],
        required_permission=None,
        handler=_handle_get_project,
    ))

    # --- Skill-specific tools ---

    registry.register(ToolDef(
        name="updateSkillContent",
        description="Update a skill's content (the SKILL.md body). Use this to modify how a skill works.",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID (e.g., SK-001). If omitted, uses the current skill context.",
                },
                "content": {
                    "type": "string",
                    "description": "The new SKILL.md content.",
                },
            },
            "required": ["content"],
        },
        context_types=["skill"],
        required_permission=("skills", "write"),
        handler=_handle_update_skill_content,
    ))

    registry.register(ToolDef(
        name="updateSkillMetadata",
        description="Update a skill's metadata — category, tags, or scopes.",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID. If omitted, uses the current skill context.",
                },
                "category": {
                    "type": "string",
                    "enum": ["workflow", "analysis", "generation", "integration", "utility"],
                    "description": "New category.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags list.",
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New scopes list.",
                },
            },
        },
        context_types=["skill"],
        required_permission=("skills", "write"),
        handler=_handle_update_skill_metadata,
    ))

    registry.register(ToolDef(
        name="runSkillLint",
        description="Run TESLint on a skill to check for quality issues.",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID to lint. If omitted, uses the current skill context.",
                },
            },
        },
        context_types=["skill"],
        required_permission=("skills", "read"),
        handler=_handle_run_skill_lint,
    ))

    registry.register(ToolDef(
        name="getOtherSkill",
        description="Read another skill's content for reference (read-only).",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID to read.",
                },
            },
            "required": ["skill_id"],
        },
        context_types=["skill"],
        required_permission=("skills", "read"),
        handler=_handle_get_other_skill,
    ))

    return registry

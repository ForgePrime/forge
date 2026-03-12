"""LLM Tool Registry — defines and manages tools available to LLM agents.

Tools are JSON Schema-defined functions that map to Forge API operations.
The registry resolves which tools are available based on context type
and permissions.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from core.llm.provider import ToolDefinition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entity type → storage mapping (single source of truth)
# ---------------------------------------------------------------------------

_ENTITY_MAP: dict[str, tuple[str | None, str]] = {
    "tasks": ("tracker", "tasks"),
    "decisions": ("decisions", "decisions"),
    "guidelines": ("guidelines", "guidelines"),
    "ideas": ("ideas", "ideas"),
    "knowledge": ("knowledge", "knowledge"),
    "objectives": ("objectives", "objectives"),
    "changes": ("changes", "changes"),
    "lessons": ("lessons", "lessons"),
    "ac_templates": ("ac_templates", "ac_templates"),
    "skills": (None, "skills"),  # global entity
}

_ENTITY_TYPE_ENUM = sorted(_ENTITY_MAP.keys())

_SAFE_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def _validate_project_slug(slug: str) -> str | None:
    """Validate project slug — no path traversal. Returns error or None."""
    if not slug or not _SAFE_SLUG_RE.match(slug):
        return f"Invalid project slug: {slug!r}"
    return None


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
        context_type: str | list[str] = "global",
        permissions: dict[str, dict[str, bool]] | None = None,
        disabled_tools: list[str] | None = None,
    ) -> list[ToolDef]:
        """Return tools available for context type(s), filtered by permissions.

        Args:
            context_type: The entity context(s). A single string or list of strings.
                          When a list, returns the union of tools matching ANY type.
            permissions: Module permission map {module: {read, write, delete}}.
                         If None, all tools are returned.
            disabled_tools: Tool names to exclude from results.
        """
        # Normalize to set for efficient lookup
        if isinstance(context_type, str):
            ctx_set = {context_type}
        else:
            ctx_set = set(context_type)

        disabled = set(disabled_tools) if disabled_tools else set()

        result = []
        for tool in self._tools.values():
            # Skip disabled tools
            if tool.name in disabled:
                continue

            # Filter by context type — "global" tools always match
            if "global" not in tool.context_types and not ctx_set.intersection(tool.context_types):
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
        permissions: dict[str, dict[str, bool]] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: The tool name to execute.
            args: Tool input arguments.
            storage: The storage adapter.
            context: Optional execution context (project, entity info, etc.)
            permissions: Module permission map for defense-in-depth check.

        Returns:
            Structured result dict. On error, returns {"error": "..."}.

        Raises:
            ValueError: If tool not found or has no handler.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        if tool.handler is None:
            raise ValueError(f"Tool {tool_name} has no handler")

        # Defense-in-depth: check permissions at execution time
        if permissions is not None and tool.required_permission is not None:
            module, action = tool.required_permission
            module_perms = permissions.get(module, {})
            if not module_perms.get(action, False):
                logger.warning(
                    "Permission denied for tool %s: requires %s.%s",
                    tool_name, module, action,
                )
                return {"error": f"Permission denied: {tool_name} requires {module}.{action}"}

        try:
            return await tool.handler(args=args, storage=storage, context=context or {})
        except Exception as e:
            logger.exception("Tool %s execution failed", tool_name)
            return {"error": f"Tool execution failed: {type(e).__name__}: {e}"}

    def get_llm_definitions(
        self,
        context_type: str | list[str] = "global",
        permissions: dict[str, dict[str, bool]] | None = None,
        disabled_tools: list[str] | None = None,
    ) -> list[ToolDefinition]:
        """Get ToolDefinition list for LLM provider calls."""
        return [
            t.to_llm_definition()
            for t in self.get_tools(context_type, permissions, disabled_tools)
        ]


# ---------------------------------------------------------------------------
# Shared helpers for handlers
# ---------------------------------------------------------------------------

async def _load_entity_data(
    storage: Any,
    entity_type: str,
    project: str | None,
) -> tuple[dict, str] | dict:
    """Load entity data from storage. Returns (data, list_key) or error dict."""
    if entity_type not in _ENTITY_MAP:
        return {"error": f"Unknown entity type: {entity_type}"}

    storage_key, list_key = _ENTITY_MAP[entity_type]

    if storage_key is None:
        data = await asyncio.to_thread(storage.load_global, entity_type)
    else:
        if not project:
            return {"error": "project is required for project-scoped entities"}
        err = _validate_project_slug(project)
        if err:
            return {"error": err}
        data = await asyncio.to_thread(storage.load_data, project, storage_key)

    return data, list_key


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

    result = await _load_entity_data(storage, entity_type, project)
    if isinstance(result, dict):
        result["results"] = []
        return result
    data, list_key = result

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
    total = len(items)
    items = items[:20]

    return {"entity_type": entity_type, "results": items, "count": len(items), "total": total}


async def _handle_get_entity(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get a single entity by type and ID."""
    entity_type = args.get("entity_type", "tasks")
    entity_id = args.get("entity_id", "")
    project = args.get("project") or context.get("project")

    result = await _load_entity_data(storage, entity_type, project)
    if isinstance(result, dict):
        return result
    data, list_key = result

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

    result = await _load_entity_data(storage, entity_type, project)
    if isinstance(result, dict):
        result["items"] = []
        return result
    data, list_key = result

    items = data.get(list_key, [])

    # Apply filters
    for key, value in filters.items():
        items = [item for item in items if item.get(key) == value]

    # Limit to prevent token explosion
    total = len(items)
    items = items[:100]

    return {"entity_type": entity_type, "items": items, "count": len(items), "total": total}


async def _handle_get_project(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get project overview — tasks summary, status counts."""
    slug = args.get("slug") or context.get("project")
    if not slug:
        return {"error": "slug is required"}

    err = _validate_project_slug(slug)
    if err:
        return {"error": err}

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
    skill_id = args.get("skill_id") or context.get("entity_id")
    content = args.get("content", "")

    if not skill_id:
        return {"error": "skill_id is required"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == skill_id:
            skill["skill_md_content"] = content
            # Merge frontmatter metadata
            try:
                from app.services.skill_parser import merge_frontmatter_to_metadata
                meta = merge_frontmatter_to_metadata(content)
                if meta.get("name"):
                    skill["name"] = meta["name"]
                if meta.get("description"):
                    skill["description"] = meta["description"]
            except Exception:
                pass  # frontmatter merge is best-effort
            await asyncio.to_thread(storage.save_global, "skills", data)
            return {"updated": True, "skill_id": skill_id}

    return {"error": f"Skill {skill_id} not found"}


async def _handle_update_skill_metadata(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Update a skill's metadata (category, tags, scopes)."""
    skill_id = args.get("skill_id") or context.get("entity_id")
    if not skill_id:
        return {"error": "skill_id is required"}

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

    content = skill.get("skill_md_content", "")
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
                {"rule_id": f.rule_id, "severity": f.severity, "message": f.message, "line": f.line}
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
    skill_name = args.get("skill_id", "") or args.get("skill_name", "")
    if not skill_name:
        return {"error": "skill_id or skill_name is required"}

    # Try new file-based storage first
    try:
        from app.services.skill_storage import SkillStorageService
        skills_dir = storage.base_dir / "_global" / "skills" if hasattr(storage, "base_dir") else None
        if skills_dir and skills_dir.is_dir():
            svc = SkillStorageService(skills_dir=skills_dir)
            skill = await svc.get_skill(skill_name)
            return {
                "skill_id": skill_name,
                "name": skill.get("name", ""),
                "categories": skill.get("categories", []),
                "content": skill.get("skill_md_content", ""),
                "tags": skill.get("tags", []),
            }
    except (FileNotFoundError, Exception):
        pass

    # Fallback: old skills.json format
    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("name") == skill_name or skill.get("id") == skill_name:
            return {
                "skill_id": skill_name,
                "name": skill.get("name", ""),
                "categories": skill.get("categories", skill.get("category", "")),
                "content": skill.get("skill_md_content", ""),
                "tags": skill.get("tags", []),
            }

    return {"error": f"Skill {skill_name} not found"}


# ---------------------------------------------------------------------------
# Skill file tool handlers (multi-file support)
# ---------------------------------------------------------------------------

_ALLOWED_FILE_PREFIXES = ("scripts/", "references/", "assets/")


def _validate_skill_file_path(path: str) -> str | None:
    """Validate file path. Returns error string or None."""
    if not path:
        return "Empty file path"
    if ".." in path:
        return f"Path traversal not allowed: {path}"
    if "/" in path and not any(path.startswith(p) for p in _ALLOWED_FILE_PREFIXES):
        return f"Files must be in scripts/, references/, assets/, or at root level: {path}"
    return None


async def _handle_add_skill_file(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Add a file to a skill's bundled resources."""
    skill_id = args.get("skill_id") or context.get("entity_id")
    path = args.get("path", "")
    content = args.get("content", "")
    file_type = args.get("file_type", "other")

    if not skill_id:
        return {"error": "skill_id is required"}
    err = _validate_skill_file_path(path)
    if err:
        return {"error": err}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == skill_id:
            resources = skill.get("resources") or {}
            files = resources.get("files", [])
            # Check duplicate
            if any(f["path"] == path for f in files):
                return {"error": f"File already exists: {path}"}
            if len(files) >= 50:
                return {"error": "Maximum 50 files per skill"}
            if len(content) > 100 * 1024:
                return {"error": f"File too large (max 100KB): {path}"}
            files.append({"path": path, "content": content, "file_type": file_type})
            resources["files"] = files
            skill["resources"] = resources
            await asyncio.to_thread(storage.save_global, "skills", data)
            return {"added": True, "skill_id": skill_id, "path": path}

    return {"error": f"Skill {skill_id} not found"}


async def _handle_remove_skill_file(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Remove a file from a skill's bundled resources."""
    skill_id = args.get("skill_id") or context.get("entity_id")
    path = args.get("path", "")

    if not skill_id:
        return {"error": "skill_id is required"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == skill_id:
            resources = skill.get("resources") or {}
            files = resources.get("files", [])
            original_count = len(files)
            files = [f for f in files if f["path"] != path]
            if len(files) == original_count:
                return {"error": f"File not found: {path}"}
            resources["files"] = files
            skill["resources"] = resources
            await asyncio.to_thread(storage.save_global, "skills", data)
            return {"removed": True, "skill_id": skill_id, "path": path}

    return {"error": f"Skill {skill_id} not found"}


async def _handle_list_skill_files(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """List all files in a skill's bundled resources."""
    skill_id = args.get("skill_id") or context.get("entity_id")
    if not skill_id:
        return {"error": "skill_id is required"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == skill_id:
            resources = skill.get("resources") or {}
            files = resources.get("files", [])
            return {
                "skill_id": skill_id,
                "files": [{"path": f["path"], "file_type": f.get("file_type", "other")} for f in files],
                "count": len(files),
            }

    return {"error": f"Skill {skill_id} not found"}


async def _handle_get_skill_file_content(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get the content of a specific file in a skill."""
    skill_id = args.get("skill_id") or context.get("entity_id")
    path = args.get("path", "")

    if not skill_id:
        return {"error": "skill_id is required"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    for skill in skills:
        if skill.get("id") == skill_id:
            resources = skill.get("resources") or {}
            files = resources.get("files", [])
            for f in files:
                if f["path"] == path:
                    return {"skill_id": skill_id, "path": path, "content": f["content"], "file_type": f.get("file_type", "other")}
            return {"error": f"File not found: {path}"}

    return {"error": f"Skill {skill_id} not found"}


async def _handle_instantiate_ac_template(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Instantiate an AC template with concrete parameters.

    Loads the template, fills {placeholder} params (with defaults), increments
    usage_count, and returns structured AC: {text, from_template, params}.
    """
    template_id = args.get("template_id", "")
    params = args.get("params", {})
    project = args.get("project") or context.get("project")

    if not template_id:
        return {"error": "template_id is required"}
    if not project:
        return {"error": "project is required"}

    err = _validate_project_slug(project)
    if err:
        return {"error": err}

    data = await asyncio.to_thread(storage.load_data, project, "ac_templates")
    templates = data.get("ac_templates", [])

    template = None
    for t in templates:
        if t.get("id") == template_id:
            template = t
            break

    if template is None:
        return {"error": f"Template {template_id} not found"}

    if template.get("status") == "DEPRECATED":
        return {"error": f"Template {template_id} is DEPRECATED"}

    # Resolve params: provided values + defaults from template definition
    template_params = template.get("parameters", [])
    resolved: dict[str, Any] = {}
    missing: list[str] = []

    for p in template_params:
        name = p["name"]
        if name in params:
            resolved[name] = params[name]
        elif "default" in p:
            resolved[name] = p["default"]
        else:
            missing.append(name)

    if missing:
        return {"error": f"Missing required parameters: {', '.join(missing)}"}

    # Render template — SafeDict leaves unresolved {placeholders} as-is
    template_str = template.get("template", "")

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        text = template_str.format_map(_SafeDict({k: str(v) for k, v in resolved.items()}))
    except (ValueError, IndexError) as e:
        return {"error": f"Template rendering failed: {e}"}

    # Increment usage count and save
    template["usage_count"] = template.get("usage_count", 0) + 1
    await asyncio.to_thread(storage.save_data, project, "ac_templates", data)

    return {
        "text": text,
        "from_template": template_id,
        "params": resolved,
    }


async def _handle_preview_skill(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Preview the current skill — renders frontmatter + body as markdown.

    Returns name, description, preview_md, line_count, and file_count.
    Uses the current skill from context (entity_id).
    """
    skill_id = context.get("entity_id")
    if not skill_id:
        return {"error": "No skill in context — this tool must be used within a skill context"}

    data = await asyncio.to_thread(storage.load_global, "skills")
    skills = data.get("skills", [])

    skill = None
    for s in skills:
        if s.get("id") == skill_id:
            skill = s
            break

    if skill is None:
        return {"error": f"Skill {skill_id} not found"}

    content = skill.get("skill_md_content", "")
    name = skill.get("name", skill_id)
    description = skill.get("description", "")

    # Build preview markdown
    preview_parts: list[str] = []

    # Frontmatter section
    preview_parts.append(f"# {name}")
    if description:
        preview_parts.append(f"\n> {description}")

    # Metadata summary
    meta_lines: list[str] = []
    if skill.get("categories"):
        meta_lines.append(f"**Categories**: {', '.join(skill['categories'])}")
    if skill.get("tags"):
        meta_lines.append(f"**Tags**: {', '.join(skill['tags'])}")
    if skill.get("scopes"):
        meta_lines.append(f"**Scopes**: {', '.join(skill['scopes'])}")
    if skill.get("status"):
        meta_lines.append(f"**Status**: {skill['status']}")
    if meta_lines:
        preview_parts.append("\n" + " | ".join(meta_lines))

    # Body content
    if content:
        # Parse frontmatter to get just the body
        try:
            from app.services.frontmatter import parse_frontmatter
            fm = parse_frontmatter(content)
            body = fm.body.strip() if fm.body else content
        except Exception:
            body = content
        preview_parts.append(f"\n---\n\n{body}")

    preview_md = "\n".join(preview_parts)

    # Count lines and bundled files
    line_count = len(content.split("\n")) if content else 0
    resources = skill.get("resources") or {}
    file_count = len(resources.get("files", []))

    return {
        "name": name,
        "description": description,
        "preview_md": preview_md,
        "line_count": line_count,
        "file_count": file_count,
    }


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
                    "enum": _ENTITY_TYPE_ENUM,
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
                    "enum": _ENTITY_TYPE_ENUM,
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
        description="List all entities of a given type with optional filters. Returns max 100 items.",
        parameters={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": _ENTITY_TYPE_ENUM,
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

    # --- Skill file tools (multi-file support) ---

    registry.register(ToolDef(
        name="addSkillFile",
        description="Add a bundled file to the skill (scripts/, references/, assets/, or root level).",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID. If omitted, uses the current skill context.",
                },
                "path": {
                    "type": "string",
                    "description": "File path (e.g., 'scripts/helper.py', 'references/spec.md').",
                },
                "content": {
                    "type": "string",
                    "description": "File content.",
                },
                "file_type": {
                    "type": "string",
                    "enum": ["script", "reference", "asset", "other"],
                    "description": "Type of file.",
                },
            },
            "required": ["path", "content"],
        },
        context_types=["skill"],
        required_permission=("skills", "write"),
        handler=_handle_add_skill_file,
    ))

    registry.register(ToolDef(
        name="removeSkillFile",
        description="Remove a bundled file from the skill.",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID. If omitted, uses the current skill context.",
                },
                "path": {
                    "type": "string",
                    "description": "Path of the file to remove.",
                },
            },
            "required": ["path"],
        },
        context_types=["skill"],
        required_permission=("skills", "delete"),
        handler=_handle_remove_skill_file,
    ))

    registry.register(ToolDef(
        name="listSkillFiles",
        description="List all bundled files in the skill with their types.",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID. If omitted, uses the current skill context.",
                },
            },
        },
        context_types=["skill"],
        required_permission=("skills", "read"),
        handler=_handle_list_skill_files,
    ))

    registry.register(ToolDef(
        name="getSkillFileContent",
        description="Get the content of a specific bundled file in the skill.",
        parameters={
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "The skill ID. If omitted, uses the current skill context.",
                },
                "path": {
                    "type": "string",
                    "description": "Path of the file to read.",
                },
            },
            "required": ["path"],
        },
        context_types=["skill"],
        required_permission=("skills", "read"),
        handler=_handle_get_skill_file_content,
    ))

    # --- Skill AC template + preview tools ---

    registry.register(ToolDef(
        name="instantiateACTemplate",
        description=(
            "Instantiate an AC template with concrete parameters. "
            "Fills {placeholder} params and returns structured acceptance criteria text."
        ),
        parameters={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "The AC template ID (e.g., AC-001).",
                },
                "params": {
                    "type": "object",
                    "description": "Key-value map of parameter names to values (e.g., {\"endpoint\": \"/api/users\", \"max_ms\": \"200\"}).",
                    "additionalProperties": {"type": "string"},
                },
                "project": {
                    "type": "string",
                    "description": "Project slug. If omitted, uses the current project context.",
                },
            },
            "required": ["template_id", "params"],
        },
        context_types=["skill"],
        required_permission=("skills", "read"),
        handler=_handle_instantiate_ac_template,
    ))

    registry.register(ToolDef(
        name="previewSkill",
        description=(
            "Preview the current skill — renders frontmatter + body as a markdown preview. "
            "Returns name, description, rendered markdown, line count, and bundled file count."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        context_types=["skill"],
        required_permission=("skills", "read"),
        handler=_handle_preview_skill,
    ))

    return registry

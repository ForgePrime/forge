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
from typing import Any, Callable, Awaitable, ClassVar

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
    "research": ("research", "research"),
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
    scope: str | None = None  # Frontend scope name (e.g., "tasks", "skills")

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
                result = {"error": f"Permission denied: {tool_name} requires {module}.{action}"}
                if tool.scope:
                    result["scope_suggestion"] = tool.scope
                    result["suggestion"] = (
                        f"The '{tool.scope}' scope needs to be enabled for this action. "
                        f"Suggest the user enable it with [suggest-scope:{tool.scope}]."
                    )
                return result

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

    def get_tools_by_scope(
        self,
        scopes: list[str] | None = None,
    ) -> dict[str, list[dict[str, str]]]:
        """Return tools grouped by scope, optionally filtered by allowed scopes.

        Args:
            scopes: If provided, only return tools whose scope is in this list
                    (plus tools with no scope, grouped under 'global').

        Returns:
            Dict mapping scope name to list of {name, description} dicts.
        """
        groups: dict[str, list[dict[str, str]]] = {}
        scope_set = set(scopes) if scopes is not None else None

        for tool in self._tools.values():
            tool_scope = tool.scope or "global"
            if scope_set is not None and tool_scope != "global" and tool_scope not in scope_set:
                continue
            groups.setdefault(tool_scope, []).append({
                "name": tool.name,
                "description": tool.description,
            })

        # Sort tools within each group
        for tools in groups.values():
            tools.sort(key=lambda t: t["name"])

        return groups

    def get_tool_contract(self, tool_name: str) -> dict[str, Any] | None:
        """Return full contract for a single tool.

        Returns:
            Dict with name, description, parameters (JSON Schema),
            required_permission, scope — or None if not found.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return None
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "required_permission": (
                f"{tool.required_permission[0]}.{tool.required_permission[1]}"
                if tool.required_permission else None
            ),
            "scope": tool.scope,
            "context_types": tool.context_types,
        }

    # Scope label for generic tool expansion (entity_type → scope)
    _ENTITY_TYPE_TO_SCOPE: ClassVar[dict[str, str]] = {
        "task": "tasks",
        "decision": "decisions",
        "objective": "objectives",
        "idea": "ideas",
        "knowledge": "knowledge",
        "guideline": "guidelines",
        "lesson": "lessons",
        "change": "changes",
        "ac_template": "ac_templates",
        "research": "research",
        "skill": "skills",
        "project": "projects",
    }

    # Human labels for entity types
    _ENTITY_LABELS: ClassVar[dict[str, str]] = {
        "task": "tasks",
        "decision": "decisions",
        "objective": "objectives",
        "idea": "ideas",
        "knowledge": "knowledge",
        "guideline": "guidelines",
        "lesson": "lessons",
        "change": "changes",
        "ac_template": "AC templates",
        "research": "research",
        "skill": "skills",
        "project": "projects",
    }

    def get_contracts(
        self,
        scopes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all tool contracts, optionally filtered by scope.

        Generic tools (searchEntities, listEntities, getEntity) are expanded
        into per-scope virtual entries so that each scope shows its full
        list/search/get capabilities alongside create/update/delete.

        Args:
            scopes: If provided, only return tools whose scope is in this list
                    (global-scope tools are always included).

        Returns:
            List of contract dicts sorted by (scope, name).
        """
        scope_set = set(scopes) if scopes else None
        result: list[dict[str, Any]] = []
        generic_tools: list[ToolDef] = []

        # Collect all scopes that have at least one scoped tool
        all_scopes_with_tools: set[str] = set()
        for tool in self._tools.values():
            if tool.scope:
                all_scopes_with_tools.add(tool.scope)

        for tool in self._tools.values():
            tool_scope = tool.scope or "global"

            # Collect generic tools for expansion later
            if tool.name in ("searchEntities", "listEntities", "getEntity"):
                generic_tools.append(tool)
                continue

            # Skip meta-tools from contract listing
            if tool.name in ("listAvailableTools", "getToolContract"):
                continue

            if scope_set is not None and tool_scope != "global" and tool_scope not in scope_set:
                continue

            action = "read"
            if tool.required_permission:
                action = tool.required_permission[1]

            result.append({
                "name": tool.name,
                "description": tool.description,
                "scope": tool.scope,
                "action": action,
                "parameters": tool.parameters,
                "required_permission": (
                    f"{tool.required_permission[0]}.{tool.required_permission[1]}"
                    if tool.required_permission else None
                ),
            })

        # Expand generic tools into per-scope virtual entries
        for tool in generic_tools:
            for entity_type, scope_name in self._ENTITY_TYPE_TO_SCOPE.items():
                # Only expand into scopes that have at least one scoped tool
                if scope_name not in all_scopes_with_tools:
                    continue
                if scope_set is not None and scope_name not in scope_set:
                    continue

                label = self._ENTITY_LABELS.get(entity_type, entity_type)
                if tool.name == "searchEntities":
                    desc = f"Search {label} by text query"
                elif tool.name == "listEntities":
                    desc = f"List all {label} with optional filters"
                else:  # getEntity
                    desc = f"Get {entity_type} details by ID"

                result.append({
                    "name": tool.name,
                    "description": desc,
                    "scope": scope_name,
                    "action": "read",
                    "parameters": tool.parameters,
                    "required_permission": None,
                    "virtual": True,  # Marks this as a virtual per-scope expansion
                    "entity_type": entity_type,
                })

        return sorted(result, key=lambda c: (c["scope"] or "", c["name"]))

    def generate_app_map(
        self,
        session_scopes: list[str] | None = None,
    ) -> str:
        """Generate a compact app map showing all modules with tool counts.

        Marks enabled scopes with [x] and disabled with [ ].
        Budget: ~500 tokens (~2000 chars).

        Args:
            session_scopes: Active scopes. If None, all are marked as enabled.

        Returns:
            Markdown-formatted app map string.
        """
        scope_tools: dict[str, list[str]] = {}
        for tool in self._tools.values():
            scope = tool.scope or "global"
            scope_tools.setdefault(scope, []).append(tool.name)

        scope_set = set(session_scopes) if session_scopes is not None else None

        lines = ["## Forge App Map"]
        for scope_name in sorted(scope_tools.keys()):
            tools = sorted(scope_tools[scope_name])
            count = len(tools)
            preview = ", ".join(tools[:3])
            if count > 3:
                preview += ", ..."

            if scope_name == "global":
                marker = "+"
            elif scope_set is None:
                marker = "x"
            elif scope_name in scope_set:
                marker = "x"
            else:
                marker = " "

            lines.append(f"[{marker}] {scope_name} ({count} tools) — {preview}")

        lines.append("")
        lines.append("Use listAvailableTools() for details, getToolContract(name) for full schema.")
        return "\n".join(lines)

    def get_unavailable_scopes(
        self,
        context_type: str | list[str] = "global",
        permissions: dict[str, dict[str, bool]] | None = None,
    ) -> dict[str, list[str]]:
        """Get tools grouped by scope that are NOT available due to missing context type.

        Returns {scope_name: [tool_names]} for scopes that would unlock new tools
        if added to the active context.
        """
        if isinstance(context_type, str):
            ctx_set = {context_type}
        else:
            ctx_set = set(context_type)

        scope_tools: dict[str, list[str]] = {}
        for tool in self._tools.values():
            if not tool.scope:
                continue
            # Skip if tool IS available (global or matching context)
            if "global" in tool.context_types or ctx_set.intersection(tool.context_types):
                continue
            # Skip if permission would block it anyway
            if permissions and tool.required_permission:
                module, action = tool.required_permission
                if not permissions.get(module, {}).get(action, False):
                    continue
            scope_tools.setdefault(tool.scope, []).append(tool.name)
        return scope_tools


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
# Entity WRITE handlers — Tasks, Objectives, Ideas, Decisions, Knowledge,
#                         Guidelines, Lessons, Changes
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """ISO 8601 timestamp."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _next_id(items: list[dict], prefix: str) -> str:
    """Generate next sequential ID from a list of entities."""
    nums = []
    for item in items:
        eid = item.get("id", "")
        if eid.startswith(f"{prefix}-"):
            try:
                nums.append(int(eid.split("-")[1]))
            except (IndexError, ValueError):
                pass
    return f"{prefix}-{max(nums, default=0) + 1:03d}"


async def _handle_create_task(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new task in the pipeline."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}
    name = args.get("name")
    if not name:
        return {"error": "name is required"}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    tasks = tracker.get("tasks", [])
    new_id = _next_id(tasks, "T")

    task = {
        "id": new_id,
        "name": name,
        "description": args.get("description", ""),
        "instruction": args.get("instruction", ""),
        "status": "TODO",
        "depends_on": args.get("depends_on", []),
        "type": args.get("type", "feature"),
        "scopes": args.get("scopes", []),
        "acceptance_criteria": args.get("acceptance_criteria", []),
        "origin": args.get("origin", ""),
        "parallel": args.get("parallel", False),
        "conflicts_with": args.get("conflicts_with", []),
        "blocked_by_decisions": args.get("blocked_by_decisions", []),
        "knowledge_ids": args.get("knowledge_ids", []),
        "started_at": None,
        "completed_at": None,
        "failed_reason": None,
    }
    tasks.append(task)
    tracker["tasks"] = tasks
    await asyncio.to_thread(storage.save_data, project, "tracker", tracker)
    return {"created": True, "id": new_id, "task": task}


async def _handle_update_task(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update fields on a TODO or FAILED task."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    task_id = args.get("task_id")
    if not task_id:
        return {"error": "task_id is required"}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    tasks = tracker.get("tasks", [])

    for task in tasks:
        if task.get("id") == task_id:
            if task.get("status") not in ("TODO", "FAILED"):
                return {"error": f"Cannot update task in status {task['status']} — only TODO or FAILED tasks can be updated"}
            updatable = [
                "name", "description", "instruction", "depends_on", "type",
                "scopes", "acceptance_criteria", "origin", "parallel",
                "conflicts_with", "blocked_by_decisions", "knowledge_ids",
            ]
            changed = []
            for field in updatable:
                if field in args and args[field] is not None:
                    task[field] = args[field]
                    changed.append(field)
            if not changed:
                return {"error": "No fields to update"}
            tracker["tasks"] = tasks
            await asyncio.to_thread(storage.save_data, project, "tracker", tracker)
            return {"updated": True, "task_id": task_id, "changed_fields": changed, "task": task}
    return {"error": f"Task {task_id} not found"}


async def _handle_complete_task(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Mark a task as DONE with reasoning."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    task_id = args.get("task_id")
    if not task_id:
        return {"error": "task_id is required"}
    reasoning = args.get("reasoning", "")

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    tasks = tracker.get("tasks", [])

    for task in tasks:
        if task.get("id") == task_id:
            if task.get("status") not in ("TODO", "IN_PROGRESS", "FAILED"):
                return {"error": f"Cannot complete task in status {task['status']}"}
            task["status"] = "DONE"
            task["completed_at"] = _now_iso()
            if reasoning:
                task["completion_reasoning"] = reasoning
            tracker["tasks"] = tasks
            await asyncio.to_thread(storage.save_data, project, "tracker", tracker)
            return {"completed": True, "task_id": task_id, "status": "DONE"}
    return {"error": f"Task {task_id} not found"}


async def _handle_create_objective(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new objective with key results."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    description = args.get("description")
    if not description:
        return {"error": "description is required"}
    key_results = args.get("key_results", [])
    if not key_results:
        return {"error": "at least one key_result is required"}

    data = await asyncio.to_thread(storage.load_data, project, "objectives")
    objectives = data.get("objectives", [])
    new_id = _next_id(objectives, "O")
    now = _now_iso()

    # Assign KR IDs
    for i, kr in enumerate(key_results, 1):
        kr["id"] = f"KR-{i}"

    objective = {
        "id": new_id,
        "title": title,
        "description": description,
        "status": "ACTIVE",
        "key_results": key_results,
        "appetite": args.get("appetite", "medium"),
        "scope": args.get("scope", "project"),
        "assumptions": args.get("assumptions", []),
        "tags": args.get("tags", []),
        "scopes": args.get("scopes", []),
        "derived_guidelines": args.get("derived_guidelines", []),
        "knowledge_ids": args.get("knowledge_ids", []),
        "created": now,
        "updated": now,
    }
    objectives.append(objective)
    data["objectives"] = objectives
    await asyncio.to_thread(storage.save_data, project, "objectives", data)
    return {"created": True, "id": new_id, "objective": objective}


async def _handle_update_objective(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update an objective's status or key result progress."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    obj_id = args.get("id")
    if not obj_id:
        return {"error": "id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "objectives")
    objectives = data.get("objectives", [])

    for obj in objectives:
        if obj.get("id") == obj_id:
            changed = []
            if "status" in args and args["status"] is not None:
                obj["status"] = args["status"]
                changed.append("status")
            if "title" in args and args["title"] is not None:
                obj["title"] = args["title"]
                changed.append("title")
            if "description" in args and args["description"] is not None:
                obj["description"] = args["description"]
                changed.append("description")
            # Update key result progress
            if "key_results" in args and args["key_results"]:
                existing_krs = {kr.get("id"): kr for kr in obj.get("key_results", [])}
                for kr_update in args["key_results"]:
                    kr_id = kr_update.get("id")
                    if kr_id and kr_id in existing_krs:
                        for k, v in kr_update.items():
                            if k != "id":
                                existing_krs[kr_id][k] = v
                obj["key_results"] = list(existing_krs.values())
                changed.append("key_results")
            if not changed:
                return {"error": "No fields to update"}
            obj["updated"] = _now_iso()
            data["objectives"] = objectives
            await asyncio.to_thread(storage.save_data, project, "objectives", data)
            return {"updated": True, "id": obj_id, "changed_fields": changed, "objective": obj}
    return {"error": f"Objective {obj_id} not found"}


async def _handle_create_idea(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new idea in staging."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    description = args.get("description")
    if not description:
        return {"error": "description is required"}

    data = await asyncio.to_thread(storage.load_data, project, "ideas")
    ideas = data.get("ideas", [])
    new_id = _next_id(ideas, "I")
    now = _now_iso()

    idea = {
        "id": new_id,
        "title": title,
        "description": description,
        "status": "DRAFT",
        "category": args.get("category", "feature"),
        "priority": args.get("priority", "MEDIUM"),
        "tags": args.get("tags", []),
        "parent_id": args.get("parent_id"),
        "relations": args.get("relations", []),
        "scopes": args.get("scopes", []),
        "advances_key_results": args.get("advances_key_results", []),
        "knowledge_ids": args.get("knowledge_ids", []),
        "exploration_notes": "",
        "rejection_reason": "",
        "merged_into": "",
        "committed_at": None,
        "created": now,
        "updated": now,
    }
    ideas.append(idea)
    data["ideas"] = ideas
    await asyncio.to_thread(storage.save_data, project, "ideas", data)
    return {"created": True, "id": new_id, "idea": idea}


async def _handle_update_idea(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update an idea's fields or status."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    idea_id = args.get("id")
    if not idea_id:
        return {"error": "id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "ideas")
    ideas = data.get("ideas", [])

    for idea in ideas:
        if idea.get("id") == idea_id:
            updatable = [
                "title", "description", "status", "category", "priority",
                "tags", "scopes", "exploration_notes", "advances_key_results",
                "knowledge_ids", "rejection_reason",
            ]
            changed = []
            for field in updatable:
                if field in args and args[field] is not None:
                    idea[field] = args[field]
                    changed.append(field)
            # Append-merge relations
            if "relations" in args and args["relations"]:
                existing = idea.get("relations", [])
                for rel in args["relations"]:
                    if rel not in existing:
                        existing.append(rel)
                idea["relations"] = existing
                changed.append("relations")
            if not changed:
                return {"error": "No fields to update"}
            idea["updated"] = _now_iso()
            data["ideas"] = ideas
            await asyncio.to_thread(storage.save_data, project, "ideas", data)
            return {"updated": True, "id": idea_id, "changed_fields": changed, "idea": idea}
    return {"error": f"Idea {idea_id} not found"}


async def _handle_create_decision(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Record a new decision, exploration, or risk."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    task_id = args.get("task_id")
    if not task_id:
        return {"error": "task_id is required"}
    dec_type = args.get("type")
    if not dec_type:
        return {"error": "type is required"}
    issue = args.get("issue")
    if not issue:
        return {"error": "issue is required"}
    recommendation = args.get("recommendation")
    if not recommendation:
        return {"error": "recommendation is required"}

    data = await asyncio.to_thread(storage.load_data, project, "decisions")
    decisions = data.get("decisions", [])
    new_id = _next_id(decisions, "D")
    now = _now_iso()

    decision = {
        "id": new_id,
        "task_id": task_id,
        "type": dec_type,
        "issue": issue,
        "recommendation": recommendation,
        "reasoning": args.get("reasoning", ""),
        "alternatives": args.get("alternatives", []),
        "confidence": args.get("confidence", "MEDIUM"),
        "status": args.get("status", "OPEN"),
        "decided_by": "claude",
        "timestamp": now,
        "updated": None,
    }
    # Exploration-specific
    if dec_type == "exploration":
        for f in ("exploration_type", "findings", "options", "open_questions", "blockers", "evidence_refs"):
            if f in args:
                decision[f] = args[f]
    # Risk-specific
    if dec_type == "risk":
        for f in ("severity", "likelihood", "linked_entity_type", "linked_entity_id", "mitigation_plan"):
            if f in args:
                decision[f] = args[f]

    decisions.append(decision)
    data["decisions"] = decisions
    await asyncio.to_thread(storage.save_data, project, "decisions", data)
    return {"created": True, "id": new_id, "decision": decision}


async def _handle_update_decision(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update a decision — close, defer, mitigate, or add resolution notes."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    dec_id = args.get("id")
    if not dec_id:
        return {"error": "id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "decisions")
    decisions = data.get("decisions", [])

    for dec in decisions:
        if dec.get("id") == dec_id:
            changed = []
            updatable = [
                "status", "recommendation", "reasoning", "resolution_notes",
                "mitigation_plan", "confidence",
            ]
            for field in updatable:
                if field in args and args[field] is not None:
                    dec[field] = args[field]
                    changed.append(field)
            if not changed:
                return {"error": "No fields to update"}
            dec["updated"] = _now_iso()
            data["decisions"] = decisions
            await asyncio.to_thread(storage.save_data, project, "decisions", data)
            return {"updated": True, "id": dec_id, "changed_fields": changed, "decision": dec}
    return {"error": f"Decision {dec_id} not found"}


async def _handle_create_knowledge(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new knowledge object."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    category = args.get("category")
    if not category:
        return {"error": "category is required"}
    content = args.get("content")
    if not content:
        return {"error": "content is required"}

    data = await asyncio.to_thread(storage.load_data, project, "knowledge")
    items = data.get("knowledge", [])
    new_id = _next_id(items, "K")
    now = _now_iso()

    knowledge = {
        "id": new_id,
        "title": title,
        "category": category,
        "content": content,
        "status": "DRAFT",
        "scopes": args.get("scopes", []),
        "tags": args.get("tags", []),
        "version": 1,
        "versions": [{
            "version": 1,
            "content": content,
            "changed_by": "ai",
            "changed_at": now,
            "change_reason": "Initial creation",
        }],
        "linked_entities": args.get("linked_entities", []),
        "dependencies": args.get("dependencies", []),
        "created_by": "ai",
        "created_at": now,
        "updated_at": now,
    }
    items.append(knowledge)
    data["knowledge"] = items
    await asyncio.to_thread(storage.save_data, project, "knowledge", data)
    return {"created": True, "id": new_id, "knowledge": knowledge}


async def _handle_update_knowledge(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update a knowledge object — content, status, or metadata."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    k_id = args.get("id")
    if not k_id:
        return {"error": "id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "knowledge")
    items = data.get("knowledge", [])

    for item in items:
        if item.get("id") == k_id:
            changed = []
            now = _now_iso()
            # Content update creates new version
            if "content" in args and args["content"] is not None:
                change_reason = args.get("change_reason", "Updated via AI")
                item["content"] = args["content"]
                item["version"] = item.get("version", 1) + 1
                versions = item.get("versions", [])
                versions.append({
                    "version": item["version"],
                    "content": args["content"],
                    "changed_by": "ai",
                    "changed_at": now,
                    "change_reason": change_reason,
                })
                item["versions"] = versions
                changed.append("content")
            for field in ("title", "status", "category", "scopes", "tags"):
                if field in args and args[field] is not None:
                    item[field] = args[field]
                    changed.append(field)
            if not changed:
                return {"error": "No fields to update"}
            item["updated_at"] = now
            data["knowledge"] = items
            await asyncio.to_thread(storage.save_data, project, "knowledge", data)
            return {"updated": True, "id": k_id, "changed_fields": changed}
    return {"error": f"Knowledge {k_id} not found"}


async def _handle_create_research(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new research object."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    category = args.get("category")
    if not category:
        return {"error": "category is required"}
    summary = args.get("summary")
    if not summary:
        return {"error": "summary is required"}

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])
    new_id = _next_id(items, "R")

    research = {
        "id": new_id,
        "title": title,
        "topic": args.get("topic", title),
        "category": category,
        "summary": summary,
        "status": "DRAFT",
        "content": args.get("content", ""),
        "key_findings": args.get("key_findings", []),
        "decision_ids": args.get("decision_ids", []),
        "linked_entity_type": args.get("linked_entity_type"),
        "linked_entity_id": args.get("linked_entity_id"),
        "linked_idea_id": args.get("linked_idea_id"),
        "skill": args.get("skill"),
        "file_path": args.get("file_path"),
        "scopes": args.get("scopes", []),
        "tags": args.get("tags", []),
        "created_by": "ai",
    }

    # Auto-generate file_path if content provided
    if research["content"] and not research["file_path"]:
        slug_part = title.lower().replace(" ", "-").replace(":", "").replace("/", "-")[:60]
        skill_part = research["skill"] or "research"
        research["file_path"] = f"research/{skill_part}-{slug_part}.md"

    items.append(research)
    data["research"] = items
    await asyncio.to_thread(storage.save_data, project, "research", data)
    return {"created": True, "id": new_id, "research": research}


async def _handle_update_research(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update a research object — status, decision_ids, findings, etc."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    r_id = args.get("id")
    if not r_id:
        return {"error": "id is required"}

    valid_transitions = {
        "DRAFT": {"ACTIVE", "ARCHIVED"},
        "ACTIVE": {"SUPERSEDED", "ARCHIVED"},
        "SUPERSEDED": {"ARCHIVED"},
    }

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])

    for item in items:
        if item.get("id") == r_id:
            changed = []
            # Status transition validation
            if "status" in args and args["status"] is not None:
                current = item.get("status", "DRAFT")
                target = args["status"]
                valid = valid_transitions.get(current, set())
                if target not in valid:
                    return {
                        "error": f"Invalid status transition: {current} -> {target}. "
                        f"Valid: {', '.join(sorted(valid)) or 'none (terminal)'}"
                    }
                item["status"] = target
                changed.append("status")
            for fld in ("title", "topic", "summary", "category", "key_findings",
                        "decision_ids", "content", "file_path", "linked_idea_id",
                        "scopes", "tags"):
                if fld in args and args[fld] is not None:
                    item[fld] = args[fld]
                    changed.append(fld)
            if not changed:
                return {"error": "No fields to update"}
            data["research"] = items
            await asyncio.to_thread(storage.save_data, project, "research", data)
            return {"updated": True, "id": r_id, "changed_fields": changed}
    return {"error": f"Research {r_id} not found"}


async def _handle_list_research(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """List research objects with optional filters."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])

    status = args.get("status")
    category = args.get("category")
    entity = args.get("entity")

    if status:
        items = [r for r in items if r.get("status") == status]
    if category:
        items = [r for r in items if r.get("category") == category]
    if entity:
        items = [r for r in items if r.get("linked_entity_id") == entity or r.get("linked_idea_id") == entity]

    # Return condensed list
    result = []
    for r in items:
        result.append({
            "id": r["id"],
            "title": r.get("title", ""),
            "category": r.get("category", ""),
            "status": r.get("status", "DRAFT"),
            "summary": r.get("summary", "")[:200],
            "linked_entity_id": r.get("linked_entity_id"),
            "key_findings_count": len(r.get("key_findings", [])),
            "decision_ids": r.get("decision_ids", []),
        })
    return {"research": result, "count": len(result)}


async def _handle_get_research_context(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Get research linked to a specific entity (for LLM context assembly)."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    entity = args.get("entity")
    if not entity:
        return {"error": "entity is required (e.g., O-001, I-001)"}

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])

    matching = [
        r for r in items
        if r.get("linked_entity_id") == entity or r.get("linked_idea_id") == entity
    ]

    result = []
    for r in matching:
        result.append({
            "id": r["id"],
            "title": r.get("title", ""),
            "category": r.get("category", ""),
            "status": r.get("status", "DRAFT"),
            "summary": r.get("summary", ""),
            "key_findings": r.get("key_findings", []),
            "decision_ids": r.get("decision_ids", []),
            "file_path": r.get("file_path", ""),
            "skill": r.get("skill", ""),
        })
    return {"research": result, "count": len(result), "entity": entity}


async def _handle_create_guideline(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new guideline."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    scope = args.get("scope")
    if not scope:
        return {"error": "scope is required"}
    content = args.get("content")
    if not content:
        return {"error": "content is required"}

    data = await asyncio.to_thread(storage.load_data, project, "guidelines")
    guidelines = data.get("guidelines", [])
    new_id = _next_id(guidelines, "G")
    now = _now_iso()

    guideline = {
        "id": new_id,
        "title": title,
        "scope": scope,
        "content": content,
        "status": "ACTIVE",
        "weight": args.get("weight", "should"),
        "rationale": args.get("rationale", ""),
        "examples": args.get("examples", []),
        "tags": args.get("tags", []),
        "derived_from": args.get("derived_from", ""),
        "created": now,
        "updated": now,
    }
    guidelines.append(guideline)
    data["guidelines"] = guidelines
    await asyncio.to_thread(storage.save_data, project, "guidelines", data)
    return {"created": True, "id": new_id, "guideline": guideline}


async def _handle_update_guideline(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update a guideline's content, status, or weight."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    g_id = args.get("id")
    if not g_id:
        return {"error": "id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "guidelines")
    guidelines = data.get("guidelines", [])

    for g in guidelines:
        if g.get("id") == g_id:
            changed = []
            for field in ("title", "content", "status", "weight", "scope", "rationale"):
                if field in args and args[field] is not None:
                    g[field] = args[field]
                    changed.append(field)
            if not changed:
                return {"error": "No fields to update"}
            g["updated"] = _now_iso()
            data["guidelines"] = guidelines
            await asyncio.to_thread(storage.save_data, project, "guidelines", data)
            return {"updated": True, "id": g_id, "changed_fields": changed, "guideline": g}
    return {"error": f"Guideline {g_id} not found"}


async def _handle_create_lesson(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Record a lesson learned."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    category = args.get("category")
    if not category:
        return {"error": "category is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    detail = args.get("detail")
    if not detail:
        return {"error": "detail is required"}

    data = await asyncio.to_thread(storage.load_data, project, "lessons")
    lessons = data.get("lessons", [])
    new_id = _next_id(lessons, "L")
    now = _now_iso()

    lesson = {
        "id": new_id,
        "project": project,
        "category": category,
        "title": title,
        "detail": detail,
        "severity": args.get("severity", "important"),
        "task_id": args.get("task_id", ""),
        "decision_ids": args.get("decision_ids", []),
        "applies_to": args.get("applies_to", ""),
        "tags": args.get("tags", []),
        "timestamp": now,
    }
    lessons.append(lesson)
    data["lessons"] = lessons
    await asyncio.to_thread(storage.save_data, project, "lessons", data)
    return {"created": True, "id": new_id, "lesson": lesson}


# ---------------------------------------------------------------------------
# Research handlers
# ---------------------------------------------------------------------------

async def _handle_create_research(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Create a new research analysis object."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    title = args.get("title")
    if not title:
        return {"error": "title is required"}
    category = args.get("category")
    if not category:
        return {"error": "category is required"}

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])
    new_id = _next_id(items, "R")
    now = _now_iso()

    research = {
        "id": new_id,
        "title": title,
        "topic": args.get("topic", title),
        "category": category,
        "status": "DRAFT",
        "summary": args.get("summary", ""),
        "content": args.get("content", ""),
        "key_findings": args.get("key_findings", []),
        "linked_entity_type": args.get("linked_entity_type"),
        "linked_entity_id": args.get("linked_entity_id"),
        "linked_idea_id": args.get("linked_idea_id"),
        "decision_ids": args.get("decision_ids", []),
        "file_path": args.get("file_path"),
        "scopes": args.get("scopes", []),
        "tags": args.get("tags", []),
        "skill": args.get("skill"),
        "created_by": "ai",
        "created_at": now,
        "updated_at": now,
    }
    items.append(research)
    data["research"] = items
    await asyncio.to_thread(storage.save_data, project, "research", data)
    return {"created": True, "id": new_id, "research": research}


async def _handle_update_research(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Update a research object — status, findings, or metadata."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    r_id = args.get("id")
    if not r_id:
        return {"error": "id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])

    for item in items:
        if item.get("id") == r_id:
            changed = []
            for field in ("title", "topic", "category", "status", "summary",
                          "content", "key_findings", "decision_ids",
                          "file_path", "scopes", "tags"):
                if field in args and args[field] is not None:
                    item[field] = args[field]
                    changed.append(field)
            if not changed:
                return {"error": "No fields to update"}
            item["updated_at"] = _now_iso()
            data["research"] = items
            await asyncio.to_thread(storage.save_data, project, "research", data)
            return {"updated": True, "id": r_id, "changed_fields": changed}

    return {"error": f"Research {r_id} not found"}


async def _handle_research_context(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Get research linked to a specific entity (objective or idea)."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    entity_id = args.get("entity_id")
    if not entity_id:
        return {"error": "entity_id is required"}

    data = await asyncio.to_thread(storage.load_data, project, "research")
    items = data.get("research", [])
    matched = [
        r for r in items
        if r.get("linked_entity_id") == entity_id
        or r.get("linked_idea_id") == entity_id
    ]
    return {"research": matched, "count": len(matched), "entity": entity_id}


async def _handle_record_change(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Record a file change for audit trail."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    task_id = args.get("task_id")
    if not task_id:
        return {"error": "task_id is required"}
    file_path = args.get("file")
    if not file_path:
        return {"error": "file is required"}
    action = args.get("action")
    if not action:
        return {"error": "action is required"}
    summary = args.get("summary")
    if not summary:
        return {"error": "summary is required"}

    data = await asyncio.to_thread(storage.load_data, project, "changes")
    changes = data.get("changes", [])
    new_id = _next_id(changes, "C")
    now = _now_iso()

    change = {
        "id": new_id,
        "task_id": task_id,
        "file": file_path,
        "action": action,
        "summary": summary,
        "reasoning_trace": args.get("reasoning_trace", []),
        "decision_ids": args.get("decision_ids", []),
        "lines_added": args.get("lines_added"),
        "lines_removed": args.get("lines_removed"),
        "guidelines_checked": args.get("guidelines_checked", []),
        "timestamp": now,
    }
    changes.append(change)
    data["changes"] = changes
    await asyncio.to_thread(storage.save_data, project, "changes", data)
    return {"recorded": True, "id": new_id, "change": change}


# ---------------------------------------------------------------------------
# Planning workflow handlers (draft → show → approve)
# ---------------------------------------------------------------------------

async def _handle_draft_plan(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Store a draft plan for review before materializing into pipeline."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}

    tasks = args.get("tasks", [])
    if not tasks or not isinstance(tasks, list):
        return {"error": "tasks must be a non-empty array"}

    # Basic validation — each task needs id and name
    for i, t in enumerate(tasks):
        if not t.get("id"):
            return {"error": f"Task at index {i} missing 'id'"}
        if not t.get("name"):
            return {"error": f"Task at index {i} missing 'name'"}

    # Check for duplicate IDs within draft
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        return {"error": "Duplicate task IDs in draft"}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")

    tracker["draft_plan"] = {
        "source_idea_id": args.get("idea_id") or None,
        "source_objective_id": args.get("objective_id") or None,
        "created": _now_iso(),
        "tasks": tasks,
    }

    await asyncio.to_thread(storage.save_data, project, "tracker", tracker)

    return {
        "drafted": True,
        "task_count": len(tasks),
        "task_ids": ids,
        "source_idea_id": args.get("idea_id"),
        "source_objective_id": args.get("objective_id"),
        "message": f"Draft plan with {len(tasks)} tasks stored. Use showDraft to review, approvePlan to materialize.",
    }


async def _handle_show_draft(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Show the current draft plan."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    draft = tracker.get("draft_plan")

    if not draft or not draft.get("tasks"):
        return {"error": f"No draft plan for '{project}'"}

    return {
        "has_draft": True,
        "source_idea_id": draft.get("source_idea_id"),
        "source_objective_id": draft.get("source_objective_id"),
        "created": draft.get("created"),
        "task_count": len(draft["tasks"]),
        "tasks": draft["tasks"],
    }


async def _handle_approve_plan(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Approve draft plan — materialize tasks into pipeline."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    draft = tracker.get("draft_plan")

    if not draft or not draft.get("tasks"):
        return {"error": f"No draft plan for '{project}'"}

    draft_tasks = draft["tasks"]
    source_idea_id = draft.get("source_idea_id")
    source_objective_id = draft.get("source_objective_id")

    # Check for duplicate IDs against existing tasks
    existing_ids = {t["id"] for t in tracker.get("tasks", [])}
    for t in draft_tasks:
        if t["id"] in existing_ids:
            return {"error": f"Duplicate task ID '{t['id']}' — already exists in pipeline"}

    # Build task entries (mirrors _build_task_entry from core.pipeline)
    entries = []
    for t in draft_tasks:
        origin = t.get("origin", source_idea_id or source_objective_id or "")
        entry = {
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description", ""),
            "depends_on": t.get("depends_on", []),
            "parallel": t.get("parallel", False),
            "conflicts_with": t.get("conflicts_with", []),
            "skill": t.get("skill"),
            "instruction": t.get("instruction", ""),
            "acceptance_criteria": t.get("acceptance_criteria", []),
            "type": t.get("type", "feature"),
            "blocked_by_decisions": t.get("blocked_by_decisions", []),
            "scopes": t.get("scopes", []),
            "origin": origin,
            "knowledge_ids": t.get("knowledge_ids", []),
            "status": "TODO",
            "started_at": None,
            "completed_at": None,
            "failed_reason": None,
        }
        if t.get("test_requirements"):
            entry["test_requirements"] = t["test_requirements"]
        entries.append(entry)

    # Materialize
    tracker.setdefault("tasks", []).extend(entries)

    # Clear draft
    tracker.pop("draft_plan", None)

    await asyncio.to_thread(storage.save_data, project, "tracker", tracker)

    return {
        "approved": True,
        "materialized_count": len(entries),
        "task_ids": [e["id"] for e in entries],
        "source_idea_id": source_idea_id,
        "source_objective_id": source_objective_id,
        "message": f"Plan approved! {len(entries)} tasks added to pipeline.",
    }


# ---------------------------------------------------------------------------
# Task context handler (full execution context)
# ---------------------------------------------------------------------------

async def _handle_get_task_context(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Load full execution context for a task: guidelines, knowledge, deps, risks, business context."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}
    task_id = args.get("task_id")
    if not task_id:
        return {"error": "task_id is required"}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    tasks = tracker.get("tasks", [])

    task = None
    for t in tasks:
        if t.get("id") == task_id:
            task = t
            break
    if task is None:
        return {"error": f"Task {task_id} not found"}

    result: dict[str, Any] = {
        "task_id": task_id,
        "name": task.get("name", ""),
        "description": task.get("description", ""),
        "status": task.get("status", ""),
        "scopes": task.get("scopes", []),
        "origin": task.get("origin", ""),
        "acceptance_criteria": task.get("acceptance_criteria", []),
    }

    # 1. Scoped guidelines
    scopes = set(task.get("scopes", [])) | {"general"}
    try:
        g_data = await asyncio.to_thread(storage.load_data, project, "guidelines")
        guidelines = [
            {"id": g.get("id"), "title": g.get("title"), "weight": g.get("weight"),
             "scope": g.get("scope"), "content": g.get("content", "")[:300]}
            for g in g_data.get("guidelines", [])
            if g.get("status", "ACTIVE") == "ACTIVE" and g.get("scope") in scopes
        ]
        result["guidelines"] = guidelines
    except Exception:
        result["guidelines"] = []

    # 2. Knowledge objects
    k_ids = task.get("knowledge_ids", [])
    if k_ids:
        try:
            k_data = await asyncio.to_thread(storage.load_data, project, "knowledge")
            result["knowledge"] = [
                {"id": k.get("id"), "title": k.get("title"), "category": k.get("category"),
                 "content": k.get("content", "")[:500]}
                for k in k_data.get("knowledge", [])
                if k.get("id") in k_ids and k.get("status", "ACTIVE") != "ARCHIVED"
            ]
        except Exception:
            result["knowledge"] = []
    else:
        result["knowledge"] = []

    # 3. Completed dependencies (changes + decisions)
    deps = task.get("depends_on", [])
    dep_info: list[dict[str, Any]] = []
    if deps:
        task_map = {t.get("id"): t for t in tasks}
        try:
            changes_data = await asyncio.to_thread(storage.load_data, project, "changes")
            all_changes = changes_data.get("changes", [])
        except Exception:
            all_changes = []
        try:
            decisions_data = await asyncio.to_thread(storage.load_data, project, "decisions")
            all_decisions = decisions_data.get("decisions", [])
        except Exception:
            all_decisions = []

        for dep_id in deps:
            dep_task = task_map.get(dep_id)
            if not dep_task:
                continue
            dep_changes = [
                {"file": c.get("file"), "action": c.get("action"), "summary": c.get("summary")}
                for c in all_changes if c.get("task_id") == dep_id
            ][:10]
            dep_decisions = [
                {"id": d.get("id"), "type": d.get("type"), "issue": d.get("issue"),
                 "recommendation": d.get("recommendation"), "status": d.get("status")}
                for d in all_decisions if d.get("task_id") == dep_id
            ]
            dep_info.append({
                "id": dep_id,
                "name": dep_task.get("name", ""),
                "status": dep_task.get("status", ""),
                "changes": dep_changes,
                "decisions": dep_decisions,
            })
    result["dependencies"] = dep_info

    # 4. Active risks from origin idea/objective
    origin = task.get("origin", "")
    risks: list[dict[str, Any]] = []
    if origin:
        try:
            decisions_data = await asyncio.to_thread(storage.load_data, project, "decisions")
            all_decisions = decisions_data.get("decisions", [])
            for d in all_decisions:
                if (d.get("type") == "risk"
                        and d.get("status") not in ("CLOSED",)
                        and (d.get("task_id") == origin or d.get("linked_entity_id") == origin)):
                    risks.append({
                        "id": d.get("id"), "issue": d.get("issue"),
                        "severity": d.get("severity"), "likelihood": d.get("likelihood"),
                        "status": d.get("status"),
                        "mitigation_plan": d.get("mitigation_plan", ""),
                    })
        except Exception:
            pass
    result["risks"] = risks

    # 5. Business context from origin objective/idea
    business_ctx: dict[str, Any] = {}
    if origin and origin.startswith("O-"):
        try:
            obj_data = await asyncio.to_thread(storage.load_data, project, "objectives")
            for o in obj_data.get("objectives", []):
                if o.get("id") == origin:
                    business_ctx = {
                        "type": "objective", "id": origin,
                        "title": o.get("title", ""), "status": o.get("status", ""),
                        "key_results": o.get("key_results", []),
                    }
                    break
        except Exception:
            pass
    elif origin and origin.startswith("I-"):
        try:
            ideas_data = await asyncio.to_thread(storage.load_data, project, "ideas")
            for i in ideas_data.get("ideas", []):
                if i.get("id") == origin:
                    business_ctx = {
                        "type": "idea", "id": origin,
                        "title": i.get("title", ""), "status": i.get("status", ""),
                        "advances_key_results": i.get("advances_key_results", []),
                    }
                    # Also load the linked objective
                    akr = i.get("advances_key_results", [])
                    if akr:
                        obj_id = akr[0].split("/")[0]
                        obj_data = await asyncio.to_thread(storage.load_data, project, "objectives")
                        for o in obj_data.get("objectives", []):
                            if o.get("id") == obj_id:
                                business_ctx["objective"] = {
                                    "id": obj_id, "title": o.get("title", ""),
                                    "key_results": o.get("key_results", []),
                                }
                                break
                    break
        except Exception:
            pass
    result["business_context"] = business_ctx

    return result


# ---------------------------------------------------------------------------
# Verification tools (gates + status)
# ---------------------------------------------------------------------------

async def _handle_run_gates(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Run configured gates (tests, lint, etc.) for a task."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}
    task_id = args.get("task_id", "")

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    gates = tracker.get("gates", [])

    if not gates:
        return {"message": f"No gates configured for '{project}'", "results": [], "all_passed": True}

    results: list[dict[str, Any]] = []
    all_passed = True
    required_failed = False

    for g in gates:
        name = g.get("name", "")
        command = g.get("command", "")
        required = g.get("required", True)

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=5,  # 5s to start
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=120)
            passed = proc.returncode == 0
            output = (stderr_b or stdout_b or b"").decode("utf-8", errors="replace")[:500]
        except asyncio.TimeoutError:
            passed = False
            output = "Timed out after 120s"
        except Exception as e:
            passed = False
            output = str(e)[:500]

        if not passed:
            all_passed = False
            if required:
                required_failed = True

        results.append({
            "name": name,
            "passed": passed,
            "required": required,
            "output": output if not passed else "",
        })

    # Store results on task
    if task_id:
        for task in tracker.get("tasks", []):
            if task.get("id") == task_id:
                task["gate_results"] = {
                    "timestamp": _now_iso(),
                    "all_passed": all_passed,
                    "results": [{"name": r["name"], "passed": r["passed"]} for r in results],
                }
                break
        await asyncio.to_thread(storage.save_data, project, "tracker", tracker)

    return {
        "all_passed": all_passed,
        "required_failed": required_failed,
        "results": results,
    }


async def _handle_get_project_status(
    args: dict[str, Any], storage: Any, context: dict[str, Any],
) -> dict[str, Any]:
    """Get full project status: task counts, blocked tasks, progress summary."""
    project = args.get("project") or context.get("project")
    if not project:
        return {"error": "project is required"}
    err = _validate_project_slug(project)
    if err:
        return {"error": err}

    tracker = await asyncio.to_thread(storage.load_data, project, "tracker")
    tasks = tracker.get("tasks", [])

    # Status counts
    status_counts: dict[str, int] = {}
    for t in tasks:
        status = t.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    # Blocked tasks (deps not met or blocked by open decisions)
    done_ids = {t["id"] for t in tasks if t.get("status") == "DONE"}
    blocked: list[dict[str, str]] = []
    for t in tasks:
        if t.get("status") != "TODO":
            continue
        unmet_deps = [d for d in t.get("depends_on", []) if d not in done_ids]
        open_decisions = t.get("blocked_by_decisions", [])
        if unmet_deps or open_decisions:
            reasons = []
            if unmet_deps:
                reasons.append(f"deps: {', '.join(unmet_deps)}")
            if open_decisions:
                reasons.append(f"decisions: {', '.join(open_decisions)}")
            blocked.append({"id": t["id"], "name": t.get("name", ""), "reason": "; ".join(reasons)})

    # Draft plan info
    draft = tracker.get("draft_plan")
    has_draft = bool(draft and draft.get("tasks"))

    return {
        "project": project,
        "goal": tracker.get("goal", ""),
        "task_count": len(tasks),
        "status_counts": status_counts,
        "blocked_tasks": blocked[:20],
        "has_draft_plan": has_draft,
        "draft_task_count": len(draft["tasks"]) if has_draft else 0,
    }


# ---------------------------------------------------------------------------
# Meta-tool handlers (listAvailableTools, getToolContract)
# ---------------------------------------------------------------------------

async def _handle_list_available_tools(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """List all tools available to the current session, grouped by scope."""
    # The registry instance is injected via context by the agent loop
    registry: ToolRegistry | None = context.get("_tool_registry")
    if registry is None:
        return {"error": "Tool registry not available in context"}

    session_scopes = context.get("session_scopes")
    groups = registry.get_tools_by_scope(scopes=session_scopes)

    # Format as readable text
    lines = ["## Available Tools\n"]
    for scope_name in sorted(groups.keys()):
        tools = groups[scope_name]
        lines.append(f"### {scope_name}")
        for t in tools:
            lines.append(f"- **{t['name']}**: {t['description']}")
        lines.append("")

    return {
        "tools_by_scope": groups,
        "total_tools": sum(len(v) for v in groups.values()),
        "formatted": "\n".join(lines),
    }


async def _handle_get_tool_contract(
    args: dict[str, Any],
    storage: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get full JSON Schema and metadata for a single tool."""
    tool_name = args.get("toolName", "")
    if not tool_name:
        return {"error": "toolName is required"}

    registry: ToolRegistry | None = context.get("_tool_registry")
    if registry is None:
        return {"error": "Tool registry not available in context"}

    contract = registry.get_tool_contract(tool_name)
    if contract is None:
        return {"error": f"Tool '{tool_name}' not found"}

    # Scope enforcement: if session has scopes, check tool is accessible
    session_scopes = context.get("session_scopes")
    if session_scopes is not None and contract["scope"] and contract["scope"] not in session_scopes:
        return {
            "error": f"Tool '{tool_name}' requires the '{contract['scope']}' scope to be enabled. "
            f"Ask the user to enable it in the Scopes tab.",
        }

    return {"contract": contract}


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

    # --- Task context tool (read-only, rich execution context) ---

    registry.register(ToolDef(
        name="getTaskContext",
        description=(
            "Load full execution context for a task: scoped guidelines, knowledge objects, "
            "dependency outputs (changes + decisions), active risks, and business context from origin objective/idea."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID (e.g., T-001)."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["task_id"],
        },
        context_types=["task", "global"],
        required_permission=None,  # read-only
        handler=_handle_get_task_context,
        scope="tasks",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
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
        scope="skills",
    ))

    # --- Task tools (WRITE) ---

    registry.register(ToolDef(
        name="createTask",
        description="Create a new task in the project pipeline.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Task name in kebab-case (e.g., 'setup-database')."},
                "description": {"type": "string", "description": "What needs to be done."},
                "instruction": {"type": "string", "description": "Step-by-step how to do it."},
                "depends_on": {"type": "array", "items": {"type": "string"}, "description": "Prerequisite task IDs (e.g., ['T-001'])."},
                "type": {"type": "string", "enum": ["feature", "bug", "chore", "investigation"], "description": "Task type."},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "Guideline scopes (e.g., ['backend', 'database'])."},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "Conditions that must be true when DONE."},
                "origin": {"type": "string", "description": "Where this task came from (I-001, O-001, or free text)."},
                "project": {"type": "string", "description": "Project slug. If omitted, uses context."},
            },
            "required": ["name"],
        },
        context_types=["task", "global"],
        required_permission=("tasks", "write"),
        handler=_handle_create_task,
        scope="tasks",
    ))

    registry.register(ToolDef(
        name="updateTask",
        description="Update fields on a TODO or FAILED task.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID (e.g., T-001)."},
                "name": {"type": "string", "description": "New task name."},
                "description": {"type": "string", "description": "New description."},
                "instruction": {"type": "string", "description": "New instruction."},
                "depends_on": {"type": "array", "items": {"type": "string"}, "description": "New dependency list."},
                "type": {"type": "string", "enum": ["feature", "bug", "chore", "investigation"]},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "New scopes."},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "New acceptance criteria."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["task_id"],
        },
        context_types=["task"],
        required_permission=("tasks", "write"),
        handler=_handle_update_task,
        scope="tasks",
    ))

    registry.register(ToolDef(
        name="completeTask",
        description="Mark a task as DONE with completion reasoning.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to complete (e.g., T-001)."},
                "reasoning": {"type": "string", "description": "Why this task is considered done."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["task_id"],
        },
        context_types=["task"],
        required_permission=("tasks", "write"),
        handler=_handle_complete_task,
        scope="tasks",
    ))

    # --- Objective tools (WRITE) ---

    registry.register(ToolDef(
        name="createObjective",
        description="Create a business objective with measurable key results.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Concise objective name."},
                "description": {"type": "string", "description": "Why this matters, who benefits."},
                "key_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "metric": {"type": "string"},
                            "baseline": {"type": "number"},
                            "target": {"type": "number"},
                            "current": {"type": "number"},
                            "description": {"type": "string"},
                        },
                    },
                    "description": "Measurable outcomes. Use metric/baseline/target for numeric or description/status for qualitative.",
                },
                "appetite": {"type": "string", "enum": ["small", "medium", "large"], "description": "Effort budget."},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "Guideline scopes."},
                "assumptions": {"type": "array", "items": {"type": "string"}, "description": "Hypotheses that must hold."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["title", "description", "key_results"],
        },
        context_types=["objective", "global"],
        required_permission=("objectives", "write"),
        handler=_handle_create_objective,
        scope="objectives",
    ))

    registry.register(ToolDef(
        name="updateObjective",
        description="Update an objective's status or key result progress.",
        parameters={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Objective ID (e.g., O-001)."},
                "status": {"type": "string", "enum": ["ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"]},
                "title": {"type": "string", "description": "New title."},
                "description": {"type": "string", "description": "New description."},
                "key_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "KR ID (e.g., KR-1)."},
                            "current": {"type": "number", "description": "Current value."},
                            "status": {"type": "string"},
                        },
                        "required": ["id"],
                    },
                    "description": "Key result updates (partial — only changed fields).",
                },
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["id"],
        },
        context_types=["objective"],
        required_permission=("objectives", "write"),
        handler=_handle_update_objective,
        scope="objectives",
    ))

    # --- Idea tools (WRITE) ---

    registry.register(ToolDef(
        name="createIdea",
        description="Add a new idea to the staging area.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Concise idea name."},
                "description": {"type": "string", "description": "What to achieve and why."},
                "category": {
                    "type": "string",
                    "enum": ["feature", "improvement", "experiment", "migration", "refactor", "infrastructure", "business-opportunity", "research"],
                },
                "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                "parent_id": {"type": "string", "description": "Parent idea ID for hierarchy (e.g., I-001)."},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "Guideline scopes."},
                "advances_key_results": {
                    "type": "array", "items": {"type": "string"},
                    "description": "KR IDs this idea advances (format: O-001/KR-1).",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["title", "description"],
        },
        context_types=["idea", "global"],
        required_permission=("ideas", "write"),
        handler=_handle_create_idea,
        scope="ideas",
    ))

    registry.register(ToolDef(
        name="updateIdea",
        description="Update an idea's fields or status.",
        parameters={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Idea ID (e.g., I-001)."},
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "EXPLORING", "APPROVED", "REJECTED", "COMMITTED"],
                },
                "title": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string"},
                "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                "exploration_notes": {"type": "string", "description": "Notes from exploration/discovery."},
                "rejection_reason": {"type": "string"},
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["depends_on", "related_to", "supersedes", "duplicates"]},
                            "target_id": {"type": "string"},
                        },
                        "required": ["type", "target_id"],
                    },
                    "description": "Relations to append (not replace).",
                },
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["id"],
        },
        context_types=["idea"],
        required_permission=("ideas", "write"),
        handler=_handle_update_idea,
        scope="ideas",
    ))

    # --- Decision tools (WRITE) ---

    registry.register(ToolDef(
        name="createDecision",
        description="Record a decision, exploration finding, or risk assessment.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Related entity ID (T-001, I-001, O-001, or PLANNING/DISCOVERY/REVIEW).",
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "architecture", "implementation", "dependency", "security",
                        "performance", "testing", "naming", "convention", "constraint",
                        "business", "strategy", "other", "exploration", "risk",
                    ],
                },
                "issue": {"type": "string", "description": "The decision/question/risk being addressed."},
                "recommendation": {"type": "string", "description": "What we're choosing to do."},
                "reasoning": {"type": "string", "description": "WHY this choice."},
                "alternatives": {"type": "array", "items": {"type": "string"}, "description": "Alternatives considered."},
                "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                "status": {"type": "string", "enum": ["OPEN", "CLOSED", "DEFERRED"]},
                "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"], "description": "For risk type."},
                "likelihood": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"], "description": "For risk type."},
                "mitigation_plan": {"type": "string", "description": "For risk type."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["task_id", "type", "issue", "recommendation"],
        },
        context_types=["decision", "global"],
        required_permission=("decisions", "write"),
        handler=_handle_create_decision,
        scope="decisions",
    ))

    registry.register(ToolDef(
        name="updateDecision",
        description="Update a decision — close, defer, mitigate, or add notes.",
        parameters={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Decision ID (e.g., D-001)."},
                "status": {
                    "type": "string",
                    "enum": ["OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"],
                },
                "recommendation": {"type": "string"},
                "reasoning": {"type": "string"},
                "resolution_notes": {"type": "string", "description": "How it was resolved."},
                "mitigation_plan": {"type": "string"},
                "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["id"],
        },
        context_types=["decision"],
        required_permission=("decisions", "write"),
        handler=_handle_update_decision,
        scope="decisions",
    ))

    # --- Knowledge tools (WRITE) ---

    registry.register(ToolDef(
        name="createKnowledge",
        description="Create a knowledge object (domain rules, patterns, technical context).",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Concise title."},
                "category": {
                    "type": "string",
                    "enum": [
                        "domain-rules", "api-reference", "architecture", "business-context",
                        "technical-context", "code-patterns", "integration", "infrastructure",
                    ],
                },
                "content": {"type": "string", "description": "The knowledge content."},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "Areas this applies to."},
                "tags": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["title", "category", "content"],
        },
        context_types=["knowledge", "global"],
        required_permission=("knowledge", "write"),
        handler=_handle_create_knowledge,
        scope="knowledge",
    ))

    registry.register(ToolDef(
        name="updateKnowledge",
        description="Update a knowledge object — content (creates new version), status, or metadata.",
        parameters={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Knowledge ID (e.g., K-001)."},
                "content": {"type": "string", "description": "New content (creates a new version)."},
                "change_reason": {"type": "string", "description": "Why the content is being changed."},
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "ACTIVE", "REVIEW_NEEDED", "DEPRECATED", "ARCHIVED"],
                },
                "title": {"type": "string"},
                "category": {"type": "string"},
                "scopes": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["id"],
        },
        context_types=["knowledge"],
        required_permission=("knowledge", "write"),
        handler=_handle_update_knowledge,
        scope="knowledge",
    ))

    # --- Guideline tools (WRITE) ---

    registry.register(ToolDef(
        name="createGuideline",
        description="Create a project guideline (standard, convention, rule).",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Concise guideline name."},
                "scope": {"type": "string", "description": "Area this applies to (backend, frontend, testing, etc.)."},
                "content": {"type": "string", "description": "The guideline text."},
                "weight": {"type": "string", "enum": ["must", "should", "may"], "description": "Priority weight."},
                "rationale": {"type": "string", "description": "Why this guideline exists."},
                "derived_from": {"type": "string", "description": "Objective ID if derived (e.g., O-001)."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["title", "scope", "content"],
        },
        context_types=["guideline", "global"],
        required_permission=("guidelines", "write"),
        handler=_handle_create_guideline,
        scope="guidelines",
    ))

    registry.register(ToolDef(
        name="updateGuideline",
        description="Update a guideline's content, status, or weight.",
        parameters={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Guideline ID (e.g., G-001)."},
                "content": {"type": "string", "description": "New guideline text."},
                "status": {"type": "string", "enum": ["ACTIVE", "DEPRECATED"]},
                "weight": {"type": "string", "enum": ["must", "should", "may"]},
                "title": {"type": "string"},
                "scope": {"type": "string"},
                "rationale": {"type": "string"},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["id"],
        },
        context_types=["guideline"],
        required_permission=("guidelines", "write"),
        handler=_handle_update_guideline,
        scope="guidelines",
    ))

    # --- Lesson tools (WRITE) ---

    registry.register(ToolDef(
        name="createLesson",
        description="Record a lesson learned from project execution.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "pattern-discovered", "mistake-avoided", "decision-validated",
                        "decision-reversed", "tool-insight", "architecture-lesson",
                        "process-improvement", "market-insight",
                    ],
                },
                "title": {"type": "string", "description": "Concise actionable title."},
                "detail": {"type": "string", "description": "Explain WHY this matters."},
                "severity": {"type": "string", "enum": ["critical", "important", "minor"]},
                "task_id": {"type": "string", "description": "Related task ID."},
                "decision_ids": {"type": "array", "items": {"type": "string"}, "description": "Related decision IDs."},
                "tags": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["category", "title", "detail"],
        },
        context_types=["lesson", "global"],
        required_permission=("lessons", "write"),
        handler=_handle_create_lesson,
        scope="lessons",
    ))

    # --- Change tools (WRITE) ---

    registry.register(ToolDef(
        name="recordChange",
        description="Record a file change for the audit trail.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Related task ID (e.g., T-001)."},
                "file": {"type": "string", "description": "Relative file path from project root."},
                "action": {"type": "string", "enum": ["create", "edit", "delete", "rename", "move"]},
                "summary": {"type": "string", "description": "What was changed and why."},
                "reasoning_trace": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "detail": {"type": "string"},
                        },
                    },
                    "description": "Step-by-step reasoning for the change.",
                },
                "decision_ids": {"type": "array", "items": {"type": "string"}, "description": "Decision IDs that led to this change."},
                "guidelines_checked": {"type": "array", "items": {"type": "string"}, "description": "Guideline IDs verified."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["task_id", "file", "action", "summary"],
        },
        context_types=["change", "global"],
        required_permission=("changes", "write"),
        handler=_handle_record_change,
        scope="changes",
    ))

    # --- Planning workflow tools (WRITE) ---

    registry.register(ToolDef(
        name="draftPlan",
        description=(
            "Create a draft plan — decompose an objective or idea into a task graph for review. "
            "Draft is NOT yet in the pipeline; use showDraft to preview and approvePlan to materialize."
        ),
        parameters={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Task ID (e.g., T-201)."},
                            "name": {"type": "string", "description": "Task name in kebab-case."},
                            "description": {"type": "string", "description": "What needs to be done."},
                            "instruction": {"type": "string", "description": "Step-by-step how to do it."},
                            "depends_on": {"type": "array", "items": {"type": "string"}, "description": "Prerequisite task IDs."},
                            "type": {"type": "string", "enum": ["feature", "bug", "chore", "investigation"]},
                            "scopes": {"type": "array", "items": {"type": "string"}, "description": "Guideline scopes."},
                            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                            "origin": {"type": "string", "description": "Source (I-001, O-001)."},
                            "knowledge_ids": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "name"],
                    },
                    "description": "Array of task definitions for the plan.",
                },
                "objective_id": {"type": "string", "description": "Source objective ID (e.g., O-001) for traceability."},
                "idea_id": {"type": "string", "description": "Source idea ID (e.g., I-001) for traceability."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["tasks"],
        },
        context_types=["task", "global"],
        required_permission=("tasks", "write"),
        handler=_handle_draft_plan,
        scope="tasks",
    ))

    registry.register(ToolDef(
        name="showDraft",
        description="Preview the current draft plan — shows all tasks before they are materialized into the pipeline.",
        parameters={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project slug."},
            },
        },
        context_types=["task", "global"],
        required_permission=None,  # read-only
        handler=_handle_show_draft,
        scope="tasks",
    ))

    registry.register(ToolDef(
        name="approvePlan",
        description=(
            "Approve the current draft plan — materializes all draft tasks into the pipeline as TODO tasks. "
            "This is irreversible; the draft is cleared after approval."
        ),
        parameters={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project slug."},
            },
        },
        context_types=["task", "global"],
        required_permission=("tasks", "write"),
        handler=_handle_approve_plan,
        scope="tasks",
    ))

    # --- Verification tools ---

    registry.register(ToolDef(
        name="runGates",
        description=(
            "Run configured gates (tests, lint, secret scanning, etc.) for a task. "
            "Returns pass/fail per gate with error output snippets on failure."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to run gates for (results stored on task)."},
                "project": {"type": "string", "description": "Project slug."},
            },
        },
        context_types=["task", "global"],
        required_permission=("tasks", "write"),
        handler=_handle_run_gates,
        scope="tasks",
    ))

    registry.register(ToolDef(
        name="getProjectStatus",
        description=(
            "Get full pipeline status: task counts by status, blocked tasks with reasons, "
            "project goal, and draft plan info."
        ),
        parameters={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project slug."},
            },
        },
        context_types=["global"],
        required_permission=None,  # read-only
        handler=_handle_get_project_status,
    ))

    # --- Meta-tools (always available, no scope) ---

    registry.register(ToolDef(
        name="listAvailableTools",
        description=(
            "List all tools available in your current session, grouped by scope/module. "
            "Use this to discover what actions you can take. "
            "Returns tool names and descriptions, not full schemas."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        context_types=["global"],
        required_permission=None,
        handler=_handle_list_available_tools,
    ))

    registry.register(ToolDef(
        name="getToolContract",
        description=(
            "Get the full JSON Schema, description, required permissions, and scope "
            "for a specific tool. Use this before calling an unfamiliar tool to understand "
            "its exact parameters and requirements."
        ),
        parameters={
            "type": "object",
            "properties": {
                "toolName": {
                    "type": "string",
                    "description": "The exact tool name to get the contract for (e.g., 'createTask', 'searchEntities').",
                },
            },
            "required": ["toolName"],
        },
        context_types=["global"],
        required_permission=None,
        handler=_handle_get_tool_contract,
    ))

    # --- Research tools (WRITE) ---

    registry.register(ToolDef(
        name="createResearch",
        description="Create a research object with findings, linked entities, and optional full content.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Research title."},
                "topic": {"type": "string", "description": "Research topic."},
                "category": {
                    "type": "string",
                    "enum": ["architecture", "business", "domain", "feasibility", "risk", "technical"],
                    "description": "Research category.",
                },
                "summary": {"type": "string", "description": "Brief summary of findings."},
                "content": {"type": "string", "description": "Full analysis content (markdown)."},
                "key_findings": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Bullet-point key findings.",
                },
                "linked_entity_type": {
                    "type": "string", "enum": ["objective", "idea"],
                    "description": "Type of linked entity.",
                },
                "linked_entity_id": {"type": "string", "description": "Entity ID (e.g., O-001, I-001)."},
                "linked_idea_id": {"type": "string", "description": "Secondary idea link."},
                "decision_ids": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Decision IDs from this research.",
                },
                "skill": {"type": "string", "description": "Skill that produced this research."},
                "scopes": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["title", "category", "summary"],
        },
        context_types=["research", "global"],
        required_permission=("research", "write"),
        handler=_handle_create_research,
        scope="research",
    ))

    registry.register(ToolDef(
        name="updateResearch",
        description="Update a research object — status, decision_ids, key_findings, etc.",
        parameters={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Research ID (e.g., R-001)."},
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"],
                    "description": "New status (must follow valid transitions).",
                },
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "key_findings": {"type": "array", "items": {"type": "string"}},
                "decision_ids": {"type": "array", "items": {"type": "string"}},
                "content": {"type": "string"},
                "scopes": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["id"],
        },
        context_types=["research"],
        required_permission=("research", "write"),
        handler=_handle_update_research,
        scope="research",
    ))

    registry.register(ToolDef(
        name="listResearch",
        description="List research objects with optional status/category/entity filters.",
        parameters={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"]},
                "category": {
                    "type": "string",
                    "enum": ["architecture", "business", "domain", "feasibility", "risk", "technical"],
                },
                "entity": {"type": "string", "description": "Filter by linked entity ID."},
                "project": {"type": "string", "description": "Project slug."},
            },
        },
        context_types=["research", "global"],
        required_permission=("research", "read"),
        handler=_handle_list_research,
        scope="research",
    ))

    registry.register(ToolDef(
        name="getResearchContext",
        description="Get research linked to a specific entity for LLM context (summary + findings + decisions).",
        parameters={
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Entity ID (e.g., O-001, I-001)."},
                "project": {"type": "string", "description": "Project slug."},
            },
            "required": ["entity"],
        },
        context_types=["research", "global"],
        required_permission=("research", "read"),
        handler=_handle_get_research_context,
        scope="research",
    ))

    return registry

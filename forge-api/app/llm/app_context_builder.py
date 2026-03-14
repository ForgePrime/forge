"""App Context Builder — generates SKILL-format system prompt for LLM.

Replaces the old _build_base_prompt() + generate_app_map() with a comprehensive
context block that tells the LLM what Forge is, how to discover tools,
what pages exist, and how to handle common workflows.

Budget: ~1500-2000 tokens (~6000-8000 chars).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.page_registry import PageRegistry
    from app.llm.tool_registry import ToolRegistry


class AppContextBuilder:
    """Build the App Context section of the LLM system prompt."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        page_registry: PageRegistry,
        custom_text: str = "",
    ) -> None:
        self._tool_registry = tool_registry
        self._page_registry = page_registry
        self._custom_text = custom_text

    def build(
        self,
        active_scopes: list[str] | None = None,
        project_slug: str | None = None,
    ) -> str:
        """Build the full App Context string in SKILL format."""
        sections = [
            self._identity_section(),
            self._modules_section(active_scopes),
            self._tool_discovery_section(),
            self._page_catalog_section(),
            self._workflow_examples_section(),
            self._scope_awareness_section(active_scopes, project_slug),
            self._error_handling_section(),
            self._rules_section(),
            self._custom_context_section(),
        ]
        return "\n\n".join(s for s in sections if s)

    # -- Sections ----------------------------------------------------------

    def _identity_section(self) -> str:
        return (
            "# Forge AI Assistant\n\n"
            "You are the Forge AI assistant — a structured software development partner "
            "with direct access to project management tools for planning, tracking, "
            "deciding, executing, and validating code changes.\n\n"
            "Forge orchestrates: Objectives → Ideas → Discovery → Planning → Execution → Verification → Compound Learning."
        )

    def _modules_section(self, active_scopes: list[str] | None) -> str:
        """Generate module table showing scope status and tool counts."""
        scope_tools: dict[str, list[str]] = {}
        scope_descriptions: dict[str, str] = {}

        for tool in self._tool_registry._tools.values():
            scope = tool.scope or "global"
            scope_tools.setdefault(scope, []).append(tool.name)
            # Use first tool's description prefix as scope description
            if scope not in scope_descriptions and tool.description:
                scope_descriptions[scope] = tool.description.split(".")[0]

        scope_set = set(active_scopes) if active_scopes is not None else None

        # Module descriptions (static, more meaningful than tool descriptions)
        module_desc = {
            "tasks": "Pipeline task management — create, track, complete, context",
            "decisions": "Record decisions, explorations, risks with reasoning",
            "objectives": "Business goals with measurable key results",
            "ideas": "Idea staging area with hierarchy and relations",
            "knowledge": "Domain knowledge objects and patterns",
            "guidelines": "Coding standards and conventions",
            "lessons": "Compound learning from project execution",
            "changes": "Change audit log with reasoning trace",
            "skills": "Skill registry — view, edit, lint, manage files",
            "ac_templates": "Reusable acceptance criteria templates",
            "projects": "Project management — list, create, overview",
            "research": "Structured research analysis objects",
            "planning": "Draft and approve task plans",
            "verification": "Run gates, project status checks",
            "dashboard": "Cross-project overview",
            "global": "Search, browse, meta-tools (always available)",
        }

        lines = ["## Modules"]
        for scope_name in sorted(scope_tools.keys()):
            count = len(scope_tools[scope_name])
            desc = module_desc.get(scope_name, scope_descriptions.get(scope_name, ""))

            if scope_name == "global":
                marker = "+"
            elif scope_set is None:
                marker = "x"
            elif scope_name in scope_set:
                marker = "x"
            else:
                marker = " "

            status = "active" if marker in ("x", "+") else "inactive"
            lines.append(f"[{marker}] **{scope_name}** ({count} tools) — {desc}")

        return "\n".join(lines)

    def _tool_discovery_section(self) -> str:
        return (
            "## Tool Discovery\n\n"
            "You have tools organized by module scope. To explore:\n"
            "1. `listAvailableTools()` — see all tools in your active scopes, grouped by module\n"
            "2. `getToolContract(toolName)` — get full JSON Schema with parameters, types, and requirements\n\n"
            "Always check the contract before calling an unfamiliar tool. "
            "Example: `getToolContract(\"createTask\")` returns the exact parameters needed."
        )

    def _page_catalog_section(self) -> str:
        """Generate page catalog from the page registry."""
        catalog_text = self._page_registry.get_catalog_text()
        if not catalog_text:
            return ""
        return (
            "## Pages\n\n"
            "Users navigate these pages. The current page is described in the Page Context section below.\n\n"
            f"{catalog_text}"
        )

    def _workflow_examples_section(self) -> str:
        return (
            "## Common Workflows\n\n"
            "**Find and view an entity:**\n"
            "`searchEntities(query, entity_type)` → `getEntity(entity_type, entity_id)`\n\n"
            "**Create a task with context:**\n"
            "1. `getProjectStatus(project)` — understand current project state\n"
            "2. `getToolContract(\"createTask\")` — check required parameters\n"
            "3. `createTask(name, type, description, scopes, project)`\n\n"
            "**Record a decision:**\n"
            "`createDecision(task_id, type, issue, recommendation, reasoning, project)`\n\n"
            "**Browse a module:**\n"
            "`listEntities(entity_type, filters, project)` — list with optional status/type filters\n\n"
            "**Update KR progress:**\n"
            "`updateObjective(id, key_results=[{id, current}], project)`\n\n"
            "**Discovery workflow** (requires research + decisions scopes):\n"
            "When user asks to 'discover', 'explore', or 'assess' a topic/idea:\n"
            "1. `createResearch(title, category, summary, key_findings, linked_entity_id, project)` — create R-NNN\n"
            "2. `createDecision(type=exploration, issue, recommendation, reasoning, project)` — D-NNN for options/findings\n"
            "3. `createDecision(type=risk, issue, recommendation, severity, likelihood, project)` — D-NNN for risks\n"
            "4. `updateResearch(id=R-NNN, decision_ids=[D-001, D-002], status=ACTIVE)` — link decisions to research\n"
            "This mirrors `/discover` from Forge CLI. Output summary with findings + risks + recommendations.\n\n"
            "**Compound learning** (requires lessons scope):\n"
            "When user asks to 'extract lessons', 'compound', or 'what did we learn':\n"
            "1. Review completed tasks: `listEntities(entity_type=task, status=DONE)` + their decisions\n"
            "2. Identify patterns: recurring issues, validated decisions, process improvements\n"
            "3. `createLesson(category, title, detail, severity, task_id, decision_ids)` — for each pattern\n"
            "4. Suggest promotion: `promoteLesson(id, target=guideline|knowledge, scope, weight)` for critical lessons\n"
            "Categories: pattern-discovered, mistake-avoided, decision-validated, decision-reversed, "
            "tool-insight, architecture-lesson, process-improvement, market-insight.\n"
            "Severity maps to guideline weight: critical→must, important→should, minor→may."
        )

    def _scope_awareness_section(
        self,
        active_scopes: list[str] | None,
        project_slug: str | None = None,
    ) -> str:
        if active_scopes:
            scopes_str = ", ".join(active_scopes)
            line = f"Active scopes: **{scopes_str}** ({len(active_scopes)} active)"
        else:
            line = "No scopes active — no tools available."

        project_line = ""
        if project_slug:
            project_line = f"\nActive project: **{project_slug}** — use this as the `project` parameter for project-scoped tools."

        return (
            f"## Scope Awareness\n\n"
            f"{line}{project_line}\n"
            "Only tools in active scopes are available. If a tool is rejected, "
            "tell the user which scope to enable and include `[suggest-scope:SCOPENAME]` "
            "in your response so the UI shows a clickable button."
        )

    def _error_handling_section(self) -> str:
        return (
            "## Error Handling\n\n"
            "- **Permission denied** → explain which scope is needed, suggest enabling it\n"
            "- **Entity not found** → verify the ID and project slug, try searching\n"
            "- **Validation error** → check the contract with `getToolContract(toolName)`\n"
            "- **Scope not active** → use `[suggest-scope:SCOPENAME]` to help user enable it"
        )

    def _rules_section(self) -> str:
        return (
            "## Rules\n\n"
            "- Act, don't describe. Use tool calls to perform actions.\n"
            "- Respect MUST guidelines strictly. Follow SHOULD unless documented reason not to.\n"
            "- For non-trivial choices, record a decision with `createDecision`.\n"
            "- Be concise. Lead with actions, explain only when needed.\n"
            "- Always provide the `project` parameter for project-scoped tools."
        )

    def _custom_context_section(self) -> str:
        """Include user's custom App Context text from settings."""
        text = (self._custom_text or "").strip()
        if not text:
            return ""
        return f"## Custom Instructions\n\n{text}"

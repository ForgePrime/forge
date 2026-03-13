"""Page registry — in-memory catalog of all Forge pages for App Context.

Seeded at startup with known pages from the frontend codebase.
Updated dynamically when frontend pages mount and call POST /llm/pages/register.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PageEntry:
    """A registered page in the Forge app."""

    id: str
    title: str
    description: str
    route: str
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Static seed data — mirrors all useAIPage() calls in the frontend.
# Titles/descriptions are generic (dynamic values like counts are updated by frontend).
_SEED_PAGES: list[tuple[str, str, str, str]] = [
    # (id, title, description, route)

    # Global pages
    ("dashboard", "Dashboard", "Project overview and navigation hub", "/"),
    ("projects", "Projects", "List and create Forge projects", "/projects"),
    ("sessions", "Sessions", "LLM chat session history", "/sessions"),
    ("session-detail", "Session Detail", "View a single chat session", "/sessions/{id}"),
    ("llm-settings", "LLM Settings", "AI providers, feature flags, permissions", "/settings/llm"),

    # Skills (global, not project-scoped)
    ("skills", "Skills", "Skill registry with git sync", "/skills"),
    ("skill-detail", "Skill Detail", "View and edit a skill", "/skills/{name}"),
    ("new-skill", "New Skill", "Create a new skill", "/skills/new"),

    # Project dashboard & settings
    ("project-dashboard", "Project Dashboard", "Project overview with objectives, pipeline, decisions", "/projects/{slug}"),
    ("project-settings", "Project Settings", "Configuration, gates, guideline scopes", "/projects/{slug}/settings"),

    # Tasks
    ("tasks", "Tasks", "Pipeline task list with status, dependencies, execution", "/projects/{slug}/tasks"),
    ("task-detail", "Task Detail", "Full task view with acceptance criteria and context", "/projects/{slug}/tasks/{id}"),
    ("board", "Task Board", "Kanban/status board view of tasks", "/projects/{slug}/board"),
    ("execution", "Task Execution", "Task execution view", "/projects/{slug}/execution/{taskId}"),
    ("task-context", "Task Context", "Context preview for task execution", "/projects/{slug}/execution/context/{taskId}"),

    # Objectives
    ("objectives", "Objectives", "Business goals with measurable key results", "/projects/{slug}/objectives"),
    ("objective-detail", "Objective Detail", "Objective with KR progress and coverage", "/projects/{slug}/objectives/{id}"),

    # Ideas
    ("ideas", "Ideas", "Idea staging area with hierarchy and relations", "/projects/{slug}/ideas"),
    ("idea-detail", "Idea Detail", "Idea with relations, exploration status", "/projects/{slug}/ideas/{id}"),

    # Decisions
    ("decisions", "Decisions", "Decision log — decisions, explorations, risks", "/projects/{slug}/decisions"),
    ("decision-detail", "Decision Detail", "Decision with reasoning and alternatives", "/projects/{slug}/decisions/{id}"),

    # Knowledge
    ("knowledge", "Knowledge", "Domain knowledge objects and patterns", "/projects/{slug}/knowledge"),
    ("knowledge-detail", "Knowledge Detail", "Knowledge with version history", "/projects/{slug}/knowledge/{id}"),

    # Guidelines
    ("guidelines", "Guidelines", "Coding standards and conventions", "/projects/{slug}/guidelines"),
    ("guideline-detail", "Guideline Detail", "Guideline with rationale and scope", "/projects/{slug}/guidelines/{id}"),

    # Other project modules
    ("lessons", "Lessons", "Compound learning and lessons from execution", "/projects/{slug}/lessons"),
    ("changes", "Changes", "Change audit log with reasoning trace", "/projects/{slug}/changes"),
    ("ac-templates", "AC Templates", "Reusable acceptance criteria templates", "/projects/{slug}/ac-templates"),
    ("debug", "Debug Monitor", "WebSocket and event debug monitor", "/projects/{slug}/debug"),
]


class PageRegistry:
    """In-memory registry of all Forge pages.

    Seeded with known pages at startup. Updated by frontend on page mount.
    Used by AppContextBuilder to generate page catalog for LLM context.
    """

    def __init__(self) -> None:
        self._pages: dict[str, PageEntry] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Seed with all known pages from the frontend codebase."""
        for page_id, title, description, route in _SEED_PAGES:
            self._pages[page_id] = PageEntry(
                id=page_id,
                title=title,
                description=description,
                route=route,
            )

    def register(self, page_id: str, title: str, description: str, route: str) -> None:
        """Register or update a page entry."""
        self._pages[page_id] = PageEntry(
            id=page_id,
            title=title,
            description=description,
            route=route,
            last_seen=datetime.now(timezone.utc).isoformat(),
        )

    def get_all(self) -> list[dict]:
        """Return all registered pages as dicts."""
        return [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "route": p.route,
                "last_seen": p.last_seen,
            }
            for p in sorted(self._pages.values(), key=lambda p: p.route)
        ]

    def get_catalog_text(self) -> str:
        """Generate compact page catalog for SKILL context injection.

        Groups pages by category (global, project) for readability.
        Budget: ~300 tokens.
        """
        global_pages = []
        project_pages = []

        for p in sorted(self._pages.values(), key=lambda p: p.route):
            line = f"- **{p.title}** (`{p.route}`) — {p.description}"
            if "{slug}" in p.route:
                project_pages.append(line)
            else:
                global_pages.append(line)

        lines: list[str] = []
        if global_pages:
            lines.append("**Global:**")
            lines.extend(global_pages)
        if project_pages:
            if global_pages:
                lines.append("")
            lines.append("**Project pages** (under `/projects/{slug}/`):")
            lines.extend(project_pages)

        return "\n".join(lines)

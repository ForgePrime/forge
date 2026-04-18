"""Page context — describes the current page to the AI sidebar.

Each route populates `request.state.page_ctx` with a PageContext.
base.html renders it as JSON inside `<script id="forge-page-ctx">`.
The AI chat endpoint reads it back and injects into the prompt.
"""
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class CapabilityAction:
    """An action available on this page — used in the capability contract."""
    id: str
    label: str
    description: str
    method: str               # GET / POST / PATCH / DELETE
    endpoint: str             # e.g. /api/v1/projects/{slug}/tasks/{external_id}/retry
    params: list[str] = field(default_factory=list)   # e.g. ["external_id*", "reason"]
    requires_role: str = "viewer"   # viewer / editor / owner
    available: bool = True          # False → grey'd out with reason
    unavailable_reason: str | None = None


@dataclass
class Suggestion:
    """A contextual suggestion chip shown in the sidebar."""
    id: str
    label: str
    slash_command: str | None = None    # pre-fills the chat input with this


@dataclass
class PageContext:
    """What the AI sidebar knows about the current page."""
    page_id: str                              # stable id, e.g. "project-view", "task-report"
    title: str                                # human title, e.g. "Project: warehouseflow"
    description: str = ""                      # brief hint for LLM
    route: str = ""                           # actual URL path
    entity_type: str | None = None            # "project" | "task" | "objective" | None
    entity_id: str | None = None              # slug / external_id
    visible_data: dict[str, Any] = field(default_factory=dict)   # small counters, status, etc.
    actions: list[CapabilityAction] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "description": self.description,
            "route": self.route,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "visible_data": self.visible_data,
            "actions": [asdict(a) for a in self.actions],
            "suggestions": [asdict(s) for s in self.suggestions],
        }


# ---------- Page builders ----------
# Each builds a PageContext + associated capability actions + suggestions.

def _project_list_context(route: str, visible_data: dict) -> PageContext:
    return PageContext(
        page_id="project-list",
        title="Projects",
        description="List of projects in the current organization.",
        route=route,
        visible_data=visible_data,
        actions=[
            CapabilityAction(
                id="create_project", label="Create project",
                description="Create a new project as an initiative.",
                method="POST", endpoint="/ui/projects",
                params=["slug*", "name*", "goal"],
                requires_role="editor",
            ),
        ],
        suggestions=[
            Suggestion("s1", "How do I start a new initiative?"),
            Suggestion("s2", "What does each trust-debt counter mean?"),
        ],
    )


def _project_view_context(route: str, slug: str, visible_data: dict) -> PageContext:
    acts = [
        CapabilityAction(
            id="ingest_docs", label="Ingest documents",
            description="Upload knowledge sources to the project.",
            method="POST", endpoint=f"/ui/projects/{slug}/ingest",
            params=["files[]*"], requires_role="editor",
        ),
        CapabilityAction(
            id="analyze", label="Run analysis",
            description="Claude extracts objectives + KRs + ambiguities from KB.",
            method="POST", endpoint=f"/ui/projects/{slug}/analyze",
            requires_role="editor",
            available=visible_data.get("source_docs", 0) > 0,
            unavailable_reason=None if visible_data.get("source_docs", 0) > 0 else "Upload at least one document first.",
        ),
        CapabilityAction(
            id="plan", label="Plan objective",
            description="Decompose an objective into develop tasks.",
            method="POST", endpoint=f"/ui/projects/{slug}/plan",
            params=["objective_external_id*"],
            requires_role="editor",
            available=visible_data.get("objectives_total", 0) > 0,
            unavailable_reason=None if visible_data.get("objectives_total", 0) > 0 else "Run analysis first to create objectives.",
        ),
        CapabilityAction(
            id="orchestrate", label="Start orchestrate run",
            description="Execute planned tasks (Phase A/B/C verification).",
            method="POST", endpoint=f"/ui/projects/{slug}/orchestrate",
            params=["max_tasks", "skip_infra"],
            requires_role="editor",
            available=visible_data.get("tasks_total", 0) > 0,
            unavailable_reason=None if visible_data.get("tasks_total", 0) > 0 else "Plan tasks first.",
        ),
        CapabilityAction(
            id="retry_task", label="Retry a task",
            description="Reset a FAILED/DONE task back to TODO.",
            method="POST", endpoint=f"/api/v1/projects/{slug}/tasks/{{external_id}}/retry",
            params=["external_id*"], requires_role="editor",
        ),
    ]
    sugg = [
        Suggestion("pv1", "What's the next step in the pipeline?"),
        Suggestion("pv2", "Which tasks are not yet verified?"),
        Suggestion("pv3", "Summarize unresolved ambiguities."),
        Suggestion("pv4", "Find LLM-invented AC (no source attribution)."),
    ]
    return PageContext(
        page_id="project-view",
        title=f"Project: {slug}",
        description="Project page with pipeline stepper + tabs (objectives, tasks, findings, etc.).",
        route=route,
        entity_type="project", entity_id=slug,
        visible_data=visible_data,
        actions=acts,
        suggestions=sugg,
    )


def _task_report_context(route: str, slug: str, external_id: str, visible_data: dict) -> PageContext:
    base = f"/ui/projects/{slug}/tasks/{external_id}"
    api  = f"/api/v1/projects/{slug}/tasks/{external_id}"
    acts = [
        # ---- task-level mutations ----
        CapabilityAction(
            id="edit_task", label="Edit task fields",
            description="Patch task fields: name, description, instruction, type, ceremony_level, status.",
            method="PATCH", endpoint=base,
            params=["name", "description", "instruction", "type", "status"],
            requires_role="editor",
        ),
        CapabilityAction(
            id="retry_task", label="Retry / re-execute task",
            description="Reset this task to TODO so it picks up in next orchestrate run. Keeps history.",
            method="POST", endpoint=f"{api}/retry", requires_role="editor",
        ),
        # ---- AC ----
        CapabilityAction(
            id="add_ac", label="Add acceptance criterion",
            description="Append a new AC to this task. Body: {text*, scenario_type?, verification?, test_path?, command?}.",
            method="POST", endpoint=f"{base}/ac",
            params=["text*", "verification(test|command|manual)", "test_path", "command", "scenario_type"],
            requires_role="editor",
        ),
        CapabilityAction(
            id="edit_ac", label="Edit acceptance criterion",
            description="Patch one AC by position.",
            method="PATCH", endpoint=f"{base}/ac/{{position}}",
            params=["position*", "text", "verification", "test_path", "command"],
            requires_role="editor",
        ),
        CapabilityAction(
            id="delete_ac", label="Delete acceptance criterion",
            description="Remove an AC by position.",
            method="DELETE", endpoint=f"{base}/ac/{{position}}",
            params=["position*"], requires_role="editor",
        ),
        # ---- comments ----
        CapabilityAction(
            id="list_comments", label="List comments",
            description="Get the comment thread for this task.",
            method="GET", endpoint=f"{base}/comments", requires_role="viewer",
        ),
        CapabilityAction(
            id="add_comment", label="Add comment",
            description="Post a comment on this task.",
            method="POST", endpoint=f"{base}/comments",
            params=["body*"], requires_role="editor",
        ),
        # ---- inspect ----
        CapabilityAction(
            id="get_report", label="Fetch full report (JSON)",
            description="Re-read the deliverable: AC, tests, findings, challenger, diff, cost — same data this page shows.",
            method="GET", endpoint=f"{api}/report", requires_role="viewer",
        ),
        CapabilityAction(
            id="get_row", label="Fetch task row (HTMX fragment)",
            description="Render the task row HTML — used by HTMX to refresh after edits.",
            method="GET", endpoint=f"{base}/row", requires_role="viewer",
        ),
    ]
    sugg = [
        Suggestion("tr-summary", "Summarise the deliverable in one sentence."),
        Suggestion("tr-not-checked", "What did the challenger refuse to verify?"),
        Suggestion("tr-unsourced", "Which acceptance criteria have no source attribution?"),
        Suggestion("tr-not-exec", "List scenarios that were NOT executed.", slash_command="/list-not-executed"),
        Suggestion("tr-cost",  "Cost forensic drill-down for this task.", slash_command=f"/cost-drill @{external_id}"),
        Suggestion("tr-trace", "Reverse-trace this task to objective + KR.", slash_command=f"/reverse-trace @{external_id}"),
        Suggestion("tr-findings", "Convert open findings to follow-up tasks."),
    ]
    return PageContext(
        page_id="task-report",
        title=f"Task: {external_id} in {slug}",
        description=("Task deliverable detail. Visible: deliverable summary (status, tests "
                     "passed/total, challenger verdict, findings, AC unsourced count), "
                     "requirements covered, objective + KR, AC with verification mode, "
                     "auto-extracted findings + decisions, challenger per-claim verdicts, "
                     "diff (files changed + lines), cost breakdown."),
        route=route,
        entity_type="task", entity_id=external_id,
        visible_data=visible_data,
        actions=acts,
        suggestions=sugg,
    )


def _login_context(route: str) -> PageContext:
    return PageContext(
        page_id="login",
        title="Login to Forge",
        description="Authentication page.",
        route=route,
        visible_data={},
        actions=[],
        suggestions=[],   # no suggestions for anonymous users
    )


def _generic_context(route: str, page_id: str = "unknown") -> PageContext:
    return PageContext(page_id=page_id, title="Forge", route=route)


def build_page_context(request, *, entity_type: str | None = None,
                       entity_id: str | None = None,
                       visible_data: dict | None = None) -> PageContext:
    """Factory: infer page context from request path + optional overrides.

    Routes attach the context by calling this helper and storing it on request.state.
    base.html reads from request.state.page_ctx.
    """
    path = request.url.path
    visible_data = visible_data or {}

    if path in ("/ui/", "/ui/projects", "/"):
        return _project_list_context(path, visible_data)
    if path == "/ui/login" or path == "/ui/signup":
        return _login_context(path)
    if path.startswith("/ui/projects/") and "/tasks/" in path:
        # /ui/projects/{slug}/tasks/{external}
        parts = path.rstrip("/").split("/")
        try:
            slug = parts[3]; ext = parts[5]
            return _task_report_context(path, slug, ext, visible_data)
        except IndexError:
            pass
    if path.startswith("/ui/projects/"):
        parts = path.rstrip("/").split("/")
        slug = parts[3] if len(parts) > 3 else ""
        return _project_view_context(path, slug, visible_data)

    return _generic_context(path)

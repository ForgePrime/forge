"""
ForgeClient — unified client for standalone (JSON) and platform (API) modes.

Provides a single interface for all Forge operations regardless of backend.
In standalone mode, delegates to JSONFileStorage and core module functions.
In API mode, delegates to HTTP calls against forge-api REST endpoints.

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 8.3
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ForgeConfig:
    """Forge client configuration.

    Attributes:
        mode: Operating mode — 'standalone', 'local', or 'remote'.
        data_dir: Path to forge_output/ for standalone mode.
        api_url: Base URL for API (local/remote modes).
        api_key: API key for authentication (local/remote modes).
    """
    mode: str = "standalone"
    data_dir: str = "forge_output"
    api_url: str = "http://localhost:8000"
    api_key: str = ""


def load_config(config_path: str | None = None) -> ForgeConfig:
    """Load Forge configuration from TOML file.

    Searches for config in order:
    1. Explicit path (if provided)
    2. ~/.forge/config.toml
    3. Falls back to standalone mode with default data_dir.

    Args:
        config_path: Explicit path to config file.

    Returns:
        ForgeConfig instance.
    """
    if config_path is None:
        config_path = os.path.join(Path.home(), ".forge", "config.toml")

    if not os.path.exists(config_path):
        return ForgeConfig()

    try:
        # Use tomllib (Python 3.11+) or tomli fallback
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                # No TOML parser available — use defaults
                return ForgeConfig()

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        mode_section = data.get("mode", {})
        mode = mode_section.get("type", "standalone")

        standalone = data.get("standalone", {})
        api_section = data.get("api", {})

        return ForgeConfig(
            mode=mode,
            data_dir=standalone.get("data_dir", "forge_output"),
            api_url=api_section.get("url", "http://localhost:8000"),
            api_key=api_section.get("key", os.environ.get("FORGE_API_KEY", "")),
        )
    except Exception:
        return ForgeConfig()


# ---------------------------------------------------------------------------
# Backend Protocol
# ---------------------------------------------------------------------------

class ForgeBackend:
    """Base class for Forge backends. Defines the operations interface."""

    def list_projects(self) -> list[str]:
        raise NotImplementedError

    def get_project_status(self, project: str) -> dict:
        raise NotImplementedError

    # -- Pipeline operations --

    def init_project(self, project: str, goal: str) -> dict:
        raise NotImplementedError

    def add_tasks(self, project: str, tasks: list[dict]) -> list[dict]:
        raise NotImplementedError

    def get_next_task(self, project: str, agent: str | None = None) -> dict | None:
        raise NotImplementedError

    def complete_task(self, project: str, task_id: str,
                      agent: str | None = None,
                      reasoning: str = "") -> dict:
        raise NotImplementedError

    def fail_task(self, project: str, task_id: str, reason: str) -> dict:
        raise NotImplementedError

    def update_task(self, project: str, data: dict) -> dict:
        raise NotImplementedError

    def remove_task(self, project: str, task_id: str) -> bool:
        raise NotImplementedError

    def get_task_context(self, project: str, task_id: str) -> dict:
        raise NotImplementedError

    def get_project_config(self, project: str) -> dict:
        raise NotImplementedError

    def set_project_config(self, project: str, config: dict) -> None:
        raise NotImplementedError

    # -- Decision operations --

    def add_decisions(self, project: str, decisions: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_decisions(self, project: str, status: str | None = None,
                       task_id: str | None = None) -> list[dict]:
        raise NotImplementedError

    def update_decisions(self, project: str, updates: list[dict]) -> list[dict]:
        raise NotImplementedError

    # -- Change operations --

    def record_changes(self, project: str, changes: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_changes(self, project: str,
                     task_id: str | None = None) -> list[dict]:
        raise NotImplementedError

    def auto_changes(self, project: str, task_id: str,
                     reasoning: str = "") -> list[dict]:
        raise NotImplementedError

    # -- Knowledge operations --

    def add_knowledge(self, project: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_knowledge(self, project: str, status: str | None = None,
                       category: str | None = None) -> list[dict]:
        raise NotImplementedError

    def update_knowledge(self, project: str, updates: list[dict]) -> list[dict]:
        raise NotImplementedError

    def link_knowledge(self, project: str, links: list[dict]) -> list[dict]:
        raise NotImplementedError

    def knowledge_impact(self, project: str, knowledge_id: str) -> dict:
        raise NotImplementedError

    # -- Guideline operations --

    def add_guidelines(self, project: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_guidelines(self, project: str, scope: str | None = None,
                        weight: str | None = None) -> list[dict]:
        raise NotImplementedError

    def update_guidelines(self, project: str, updates: list[dict]) -> list[dict]:
        raise NotImplementedError

    def get_guideline_context(self, project: str,
                              scopes: list[str] | None = None) -> str:
        raise NotImplementedError

    # -- Objective operations --

    def add_objectives(self, project: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_objectives(self, project: str,
                        status: str | None = None) -> list[dict]:
        raise NotImplementedError

    def update_objectives(self, project: str, updates: list[dict]) -> list[dict]:
        raise NotImplementedError

    # -- Idea operations --

    def add_ideas(self, project: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_ideas(self, project: str, status: str | None = None) -> list[dict]:
        raise NotImplementedError

    def update_ideas(self, project: str, updates: list[dict]) -> list[dict]:
        raise NotImplementedError

    def commit_idea(self, project: str, idea_id: str) -> dict:
        raise NotImplementedError

    # -- Lesson operations --

    def add_lessons(self, project: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_lessons(self, project: str) -> list[dict]:
        raise NotImplementedError

    def promote_lesson(self, project: str, lesson_id: str,
                       target: str = "guideline", **kwargs: Any) -> dict:
        raise NotImplementedError

    # -- AC Template operations --

    def add_ac_templates(self, project: str, items: list[dict]) -> list[dict]:
        raise NotImplementedError

    def read_ac_templates(self, project: str,
                          category: str | None = None) -> list[dict]:
        raise NotImplementedError

    def instantiate_ac_template(self, project: str, template_id: str,
                                params: dict) -> str:
        raise NotImplementedError

    # -- Gate operations --

    def configure_gates(self, project: str, gates: list[dict]) -> None:
        raise NotImplementedError

    def check_gates(self, project: str,
                    task_id: str | None = None) -> list[dict]:
        raise NotImplementedError

    # -- Context assembly --

    def assemble_context(self, project: str, task_id: str,
                         contract: Any = None) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# JSON Backend (standalone mode)
# ---------------------------------------------------------------------------

class JSONBackend(ForgeBackend):
    """Backend using local JSON files via StorageAdapter.

    Wraps the existing core module functions for standalone operation.
    This is the default backend when no API is configured.
    """

    def __init__(self, data_dir: str = "forge_output") -> None:
        from core.storage import JSONFileStorage
        self.storage = JSONFileStorage(base_dir=data_dir)
        self.data_dir = data_dir

    def list_projects(self) -> list[str]:
        return self.storage.list_projects()

    def get_project_status(self, project: str) -> dict:
        if not self.storage.exists(project, "tracker"):
            return {"error": f"No tracker for project '{project}'"}
        tracker = self.storage.load_data(project, "tracker")
        tasks = tracker.get("tasks", [])
        status_counts: dict[str, int] = {}
        for t in tasks:
            s = t.get("status", "TODO")
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "project": project,
            "goal": tracker.get("goal", ""),
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "config": tracker.get("config", {}),
        }

    # -- Pipeline --

    def init_project(self, project: str, goal: str) -> dict:
        from core.storage import now_iso
        tracker = {
            "project": project,
            "goal": goal,
            "created": now_iso(),
            "updated": now_iso(),
            "tasks": [],
        }
        self.storage.save_data(project, "tracker", tracker)
        return tracker

    def add_tasks(self, project: str, tasks: list[dict]) -> list[dict]:
        tracker = self.storage.load_data(project, "tracker")
        existing_ids = {t["id"] for t in tracker.get("tasks", [])}

        entries = []
        for t in tasks:
            if not t.get("id") or not t.get("name"):
                raise ValueError(f"Task must have 'id' and 'name': {t}")
            if t["id"] in existing_ids:
                raise ValueError(f"Duplicate task ID: {t['id']}")
            entries.append(self._build_task_entry(t))
            existing_ids.add(t["id"])

        tracker.setdefault("tasks", []).extend(entries)
        self.storage.save_data(project, "tracker", tracker)
        return entries

    @staticmethod
    def _build_task_entry(t: dict, source_idea_id: str = "") -> dict:
        """Build a task entry dict. Mirrors pipeline._build_task_entry."""
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
            "origin": t.get("origin", source_idea_id or ""),
            "knowledge_ids": t.get("knowledge_ids", []),
            "status": "TODO",
            "started_at": None,
            "completed_at": None,
            "failed_reason": None,
        }
        if t.get("test_requirements"):
            entry["test_requirements"] = t["test_requirements"]
        if source_idea_id and not entry["origin"]:
            entry["origin"] = source_idea_id
        return entry

    def get_next_task(self, project: str, agent: str | None = None) -> dict | None:
        """Find and claim the next available task (sets IN_PROGRESS)."""
        from core.storage import now_iso
        tracker = self.storage.load_data(project, "tracker")
        tasks = tracker.get("tasks", [])
        done_ids = {t["id"] for t in tasks
                    if t.get("status") in ("DONE", "SKIPPED")}
        active_ids = {t["id"] for t in tasks
                      if t.get("status") in ("CLAIMING", "IN_PROGRESS")}

        for task in tasks:
            if task.get("status") != "TODO":
                continue
            # Check dependencies
            deps = set(task.get("depends_on", []))
            if deps and not deps.issubset(done_ids):
                continue
            # Check conflicts
            conflicts = set(task.get("conflicts_with", []))
            if conflicts & active_ids:
                continue
            # Check decision blocks
            blocked_by = task.get("blocked_by_decisions", [])
            if blocked_by:
                dec_data = self.storage.load_data(project, "decisions")
                open_blocking = [d for d in dec_data.get("decisions", [])
                                 if d["id"] in blocked_by
                                 and d.get("status") != "CLOSED"]
                if open_blocking:
                    continue
            # Claim the task
            task["status"] = "IN_PROGRESS"
            task["started_at"] = now_iso()
            if agent:
                task["agent"] = agent
            self.storage.save_data(project, "tracker", tracker)
            return task
        return None

    def complete_task(self, project: str, task_id: str,
                      agent: str | None = None,
                      reasoning: str = "") -> dict:
        from core.storage import now_iso
        tracker = self.storage.load_data(project, "tracker")
        for task in tracker.get("tasks", []):
            if task["id"] == task_id:
                if task.get("status") != "IN_PROGRESS":
                    return {"error": f"Task {task_id} is {task.get('status')}, not IN_PROGRESS"}
                task["status"] = "DONE"
                task["completed_at"] = now_iso()
                self.storage.save_data(project, "tracker", tracker)
                return task
        return {"error": f"Task {task_id} not found"}

    def fail_task(self, project: str, task_id: str, reason: str) -> dict:
        from core.storage import now_iso
        tracker = self.storage.load_data(project, "tracker")
        for task in tracker.get("tasks", []):
            if task["id"] == task_id:
                if task.get("status") not in ("TODO", "IN_PROGRESS", "CLAIMING"):
                    return {"error": f"Task {task_id} is {task.get('status')}, cannot fail"}
                task["status"] = "FAILED"
                task["failed_reason"] = reason
                task["completed_at"] = now_iso()
                self.storage.save_data(project, "tracker", tracker)
                return task
        return {"error": f"Task {task_id} not found"}

    _UPDATABLE_TASK_FIELDS = {
        "name", "description", "instruction", "depends_on",
        "conflicts_with", "skill", "acceptance_criteria",
        "type", "blocked_by_decisions", "scopes", "origin",
        "knowledge_ids", "test_requirements",
    }

    def update_task(self, project: str, data: dict) -> dict:
        tracker = self.storage.load_data(project, "tracker")
        task_id = data.get("id")
        for task in tracker.get("tasks", []):
            if task["id"] == task_id:
                if task.get("status") in ("IN_PROGRESS", "DONE"):
                    return {"error": f"Cannot update task {task_id} — status is {task['status']}"}
                for k, v in data.items():
                    if k in self._UPDATABLE_TASK_FIELDS:
                        task[k] = v
                self.storage.save_data(project, "tracker", tracker)
                return task
        return {"error": f"Task {task_id} not found"}

    def remove_task(self, project: str, task_id: str) -> bool:
        tracker = self.storage.load_data(project, "tracker")
        tasks = tracker.get("tasks", [])
        # Only remove TODO tasks with no dependents
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task or task.get("status") != "TODO":
            return False
        dependents = [t for t in tasks if task_id in t.get("depends_on", [])]
        if dependents:
            return False
        tracker["tasks"] = [t for t in tasks if t["id"] != task_id]
        self.storage.save_data(project, "tracker", tracker)
        return True

    def get_task_context(self, project: str, task_id: str) -> dict:
        """Assemble context using ContextAssembler."""
        return self.assemble_context(project, task_id)

    def get_project_config(self, project: str) -> dict:
        tracker = self.storage.load_data(project, "tracker")
        return tracker.get("config", {})

    def set_project_config(self, project: str, config: dict) -> None:
        tracker = self.storage.load_data(project, "tracker")
        tracker["config"] = config
        self.storage.save_data(project, "tracker", tracker)

    # -- Decisions --

    def add_decisions(self, project: str, decisions: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "decisions")
        dec_list = data.setdefault("decisions", [])
        existing_ids = {d["id"] for d in dec_list}
        max_num = 0
        for d_id in existing_ids:
            try:
                max_num = max(max_num, int(d_id.split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for d in decisions:
            max_num += 1
            new_id = d.get("id", f"D-{max_num:03d}")
            if new_id in existing_ids:
                continue  # Skip duplicates
            entry = {
                "id": new_id,
                "task_id": d.get("task_id", ""),
                "type": d.get("type", "implementation"),
                "issue": d.get("issue", ""),
                "recommendation": d.get("recommendation", ""),
                "reasoning": d.get("reasoning", ""),
                "alternatives": d.get("alternatives", []),
                "confidence": d.get("confidence", "MEDIUM"),
                "status": d.get("status", "OPEN"),
                "decided_by": d.get("decided_by", ""),
                "created": now_iso(),
            }
            existing_ids.add(new_id)
            dec_list.append(entry)
            entries.append(entry)

        data["open_count"] = sum(1 for d in dec_list
                                 if d.get("status") == "OPEN")
        self.storage.save_data(project, "decisions", data)
        return entries

    def read_decisions(self, project: str, status: str | None = None,
                       task_id: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "decisions")
        decisions = data.get("decisions", [])
        if status:
            decisions = [d for d in decisions if d.get("status") == status]
        if task_id:
            decisions = [d for d in decisions if d.get("task_id") == task_id]
        return decisions

    def update_decisions(self, project: str, updates: list[dict]) -> list[dict]:
        data = self.storage.load_data(project, "decisions")
        updated = []
        for upd in updates:
            d_id = upd.get("id")
            for d in data.get("decisions", []):
                if d["id"] == d_id:
                    for k, v in upd.items():
                        if k != "id":
                            d[k] = v
                    updated.append(d)
                    break
        data["open_count"] = sum(1 for d in data.get("decisions", [])
                                 if d.get("status") == "OPEN")
        self.storage.save_data(project, "decisions", data)
        return updated

    # -- Changes --

    def record_changes(self, project: str, changes: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "changes")
        change_list = data.setdefault("changes", [])
        max_num = 0
        for c in change_list:
            try:
                max_num = max(max_num, int(c["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for c in changes:
            max_num += 1
            entry = {
                "id": c.get("id", f"C-{max_num:03d}"),
                "task_id": c.get("task_id", ""),
                "file": c.get("file", ""),
                "action": c.get("action", "edit"),
                "summary": c.get("summary", ""),
                "reasoning_trace": c.get("reasoning_trace", []),
                "decision_ids": c.get("decision_ids", []),
                "guidelines_checked": c.get("guidelines_checked", []),
                "lines_added": c.get("lines_added", 0),
                "lines_removed": c.get("lines_removed", 0),
                "recorded_at": now_iso(),
            }
            change_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "changes", data)
        return entries

    def read_changes(self, project: str,
                     task_id: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "changes")
        changes = data.get("changes", [])
        if task_id:
            changes = [c for c in changes if c.get("task_id") == task_id]
        return changes

    def auto_changes(self, project: str, task_id: str,
                     reasoning: str = "") -> list[dict]:
        # Delegates to git diff detection — requires subprocess
        return []  # Implemented via core.changes.cmd_diff / cmd_auto

    # -- Knowledge --

    def add_knowledge(self, project: str, items: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "knowledge")
        k_list = data.setdefault("knowledge", [])
        max_num = 0
        for k in k_list:
            try:
                max_num = max(max_num, int(k["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for item in items:
            max_num += 1
            entry = {
                "id": item.get("id", f"K-{max_num:03d}"),
                "title": item["title"],
                "category": item["category"],
                "content": item.get("content", ""),
                "status": "ACTIVE",
                "version": 1,
                "scopes": item.get("scopes", []),
                "tags": item.get("tags", []),
                "linked_entities": item.get("linked_entities", []),
                "created": now_iso(),
                "updated": now_iso(),
            }
            k_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "knowledge", data)
        return entries

    def read_knowledge(self, project: str, status: str | None = None,
                       category: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "knowledge")
        items = data.get("knowledge", [])
        if status:
            items = [k for k in items if k.get("status") == status]
        if category:
            items = [k for k in items if k.get("category") == category]
        return items

    def update_knowledge(self, project: str, updates: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "knowledge")
        updated = []
        for upd in updates:
            k_id = upd.get("id")
            for k in data.get("knowledge", []):
                if k["id"] == k_id:
                    for key, val in upd.items():
                        if key != "id":
                            k[key] = val
                    k["updated"] = now_iso()
                    k["version"] = k.get("version", 1) + 1
                    updated.append(k)
                    break
        self.storage.save_data(project, "knowledge", data)
        return updated

    def link_knowledge(self, project: str, links: list[dict]) -> list[dict]:
        data = self.storage.load_data(project, "knowledge")
        linked = []
        for link in links:
            k_id = link.get("knowledge_id")
            for k in data.get("knowledge", []):
                if k["id"] == k_id:
                    le = {
                        "entity_type": link["entity_type"],
                        "entity_id": link["entity_id"],
                        "relation": link.get("relation", "context"),
                    }
                    existing = k.setdefault("linked_entities", [])
                    # Idempotent: skip if same link already exists
                    already = any(
                        e.get("entity_type") == le["entity_type"]
                        and e.get("entity_id") == le["entity_id"]
                        for e in existing
                    )
                    if not already:
                        existing.append(le)
                    linked.append(le)
                    break
        self.storage.save_data(project, "knowledge", data)
        return linked

    def knowledge_impact(self, project: str, knowledge_id: str) -> dict:
        """Find entities linked to this knowledge object."""
        data = self.storage.load_data(project, "knowledge")
        for k in data.get("knowledge", []):
            if k["id"] == knowledge_id:
                return {
                    "knowledge_id": knowledge_id,
                    "linked_entities": k.get("linked_entities", []),
                }
        return {"knowledge_id": knowledge_id, "linked_entities": []}

    # -- Guidelines --

    def add_guidelines(self, project: str, items: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "guidelines")
        g_list = data.setdefault("guidelines", [])
        max_num = 0
        for g in g_list:
            try:
                max_num = max(max_num, int(g["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for item in items:
            max_num += 1
            entry = {
                "id": item.get("id", f"G-{max_num:03d}"),
                "title": item["title"],
                "scope": item["scope"],
                "content": item["content"],
                "rationale": item.get("rationale", ""),
                "examples": item.get("examples", []),
                "tags": item.get("tags", []),
                "weight": item.get("weight", "should"),
                "status": "ACTIVE",
                "created": now_iso(),
            }
            g_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "guidelines", data)
        return entries

    def read_guidelines(self, project: str, scope: str | None = None,
                        weight: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "guidelines")
        items = data.get("guidelines", [])
        if scope:
            items = [g for g in items if g.get("scope") == scope]
        if weight:
            items = [g for g in items if g.get("weight") == weight]
        return items

    def update_guidelines(self, project: str, updates: list[dict]) -> list[dict]:
        data = self.storage.load_data(project, "guidelines")
        updated = []
        for upd in updates:
            g_id = upd.get("id")
            for g in data.get("guidelines", []):
                if g["id"] == g_id:
                    for k, v in upd.items():
                        if k != "id":
                            g[k] = v
                    updated.append(g)
                    break
        self.storage.save_data(project, "guidelines", data)
        return updated

    def get_guideline_context(self, project: str,
                              scopes: list[str] | None = None) -> str:
        data = self.storage.load_data(project, "guidelines")
        guidelines = [g for g in data.get("guidelines", [])
                      if g.get("status") == "ACTIVE"]
        if scopes:
            guidelines = [g for g in guidelines
                          if g.get("scope") in scopes
                          or g.get("scope") == "general"]
        lines = []
        for g in guidelines:
            weight = g.get("weight", "should").upper()
            lines.append(f"[{weight}] {g['id']} [{g.get('scope', '')}]: {g.get('content', '')}")
        return "\n".join(lines)

    # -- Objectives --

    def add_objectives(self, project: str, items: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "objectives")
        o_list = data.setdefault("objectives", [])
        max_num = 0
        for o in o_list:
            try:
                max_num = max(max_num, int(o["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for item in items:
            max_num += 1
            entry = {
                "id": item.get("id", f"O-{max_num:03d}"),
                "title": item["title"],
                "description": item["description"],
                "key_results": item.get("key_results", []),
                "appetite": item.get("appetite", "medium"),
                "scope": item.get("scope", "project"),
                "status": "ACTIVE",
                "created": now_iso(),
            }
            o_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "objectives", data)
        return entries

    def read_objectives(self, project: str,
                        status: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "objectives")
        items = data.get("objectives", [])
        if status:
            items = [o for o in items if o.get("status") == status]
        return items

    def update_objectives(self, project: str, updates: list[dict]) -> list[dict]:
        data = self.storage.load_data(project, "objectives")
        updated = []
        for upd in updates:
            o_id = upd.get("id")
            for o in data.get("objectives", []):
                if o["id"] == o_id:
                    for k, v in upd.items():
                        if k != "id":
                            o[k] = v
                    updated.append(o)
                    break
        self.storage.save_data(project, "objectives", data)
        return updated

    # -- Ideas --

    def add_ideas(self, project: str, items: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "ideas")
        i_list = data.setdefault("ideas", [])
        max_num = 0
        for i in i_list:
            try:
                max_num = max(max_num, int(i["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for item in items:
            max_num += 1
            entry = {
                "id": item.get("id", f"I-{max_num:03d}"),
                "title": item["title"],
                "description": item.get("description", ""),
                "category": item.get("category", "feature"),
                "status": "DRAFT",
                "created": now_iso(),
            }
            i_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "ideas", data)
        return entries

    def read_ideas(self, project: str, status: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "ideas")
        items = data.get("ideas", [])
        if status:
            items = [i for i in items if i.get("status") == status]
        return items

    def update_ideas(self, project: str, updates: list[dict]) -> list[dict]:
        data = self.storage.load_data(project, "ideas")
        updated = []
        for upd in updates:
            i_id = upd.get("id")
            for i in data.get("ideas", []):
                if i["id"] == i_id:
                    for k, v in upd.items():
                        if k != "id":
                            i[k] = v
                    updated.append(i)
                    break
        self.storage.save_data(project, "ideas", data)
        return updated

    def commit_idea(self, project: str, idea_id: str) -> dict:
        data = self.storage.load_data(project, "ideas")
        for i in data.get("ideas", []):
            if i["id"] == idea_id:
                i["status"] = "COMMITTED"
                self.storage.save_data(project, "ideas", data)
                return i
        return {"error": f"Idea {idea_id} not found"}

    # -- Lessons --

    def add_lessons(self, project: str, items: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "lessons")
        l_list = data.setdefault("lessons", [])
        max_num = 0
        for l in l_list:
            try:
                max_num = max(max_num, int(l["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for item in items:
            max_num += 1
            entry = {
                "id": item.get("id", f"L-{max_num:03d}"),
                "category": item.get("category", "pattern-discovered"),
                "title": item["title"],
                "detail": item.get("detail", ""),
                "severity": item.get("severity", "minor"),
                "tags": item.get("tags", []),
                "project": project,
                "timestamp": now_iso(),
            }
            l_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "lessons", data)
        return entries

    def read_lessons(self, project: str) -> list[dict]:
        data = self.storage.load_data(project, "lessons")
        return data.get("lessons", [])

    def promote_lesson(self, project: str, lesson_id: str,
                       target: str = "guideline", **kwargs: Any) -> dict:
        data = self.storage.load_data(project, "lessons")
        for l in data.get("lessons", []):
            if l["id"] == lesson_id:
                if target == "guideline":
                    l["promoted_to_guideline"] = True
                elif target == "knowledge":
                    l["promoted_to_knowledge"] = True
                self.storage.save_data(project, "lessons", data)
                return l
        return {"error": f"Lesson {lesson_id} not found"}

    # -- AC Templates --

    def add_ac_templates(self, project: str, items: list[dict]) -> list[dict]:
        from core.storage import now_iso
        data = self.storage.load_data(project, "ac_templates")
        ac_list = data.setdefault("ac_templates", [])
        max_num = 0
        for a in ac_list:
            try:
                max_num = max(max_num, int(a["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass

        entries = []
        for item in items:
            max_num += 1
            entry = {
                "id": item.get("id", f"AC-{max_num:03d}"),
                "title": item["title"],
                "template": item["template"],
                "category": item.get("category", "general"),
                "parameters": item.get("parameters", {}),
                "status": "ACTIVE",
                "created": now_iso(),
            }
            ac_list.append(entry)
            entries.append(entry)

        self.storage.save_data(project, "ac_templates", data)
        return entries

    def read_ac_templates(self, project: str,
                          category: str | None = None) -> list[dict]:
        data = self.storage.load_data(project, "ac_templates")
        items = data.get("ac_templates", [])
        if category:
            items = [a for a in items if a.get("category") == category]
        return items

    def instantiate_ac_template(self, project: str, template_id: str,
                                params: dict) -> str:
        data = self.storage.load_data(project, "ac_templates")
        for tpl in data.get("ac_templates", []):
            if tpl["id"] == template_id:
                text = tpl.get("template", "")
                for key, val in params.items():
                    text = text.replace(f"{{{key}}}", str(val))
                return text
        return ""

    # -- Gates --

    def configure_gates(self, project: str, gates: list[dict]) -> None:
        tracker = self.storage.load_data(project, "tracker")
        tracker["gates"] = gates
        self.storage.save_data(project, "tracker", tracker)

    def check_gates(self, project: str,
                    task_id: str | None = None) -> list[dict]:
        # Gate checking requires subprocess execution — return config only
        tracker = self.storage.load_data(project, "tracker")
        return tracker.get("gates", [])

    # -- Context assembly --

    def assemble_context(self, project: str, task_id: str,
                         contract: Any = None) -> dict:
        from core.llm.context import ContextAssembler
        assembler = ContextAssembler(self.storage)
        ctx = assembler.assemble(project, task_id, contract=contract)
        return {
            "sections": ctx.sections,
            "total_tokens": ctx.total_tokens,
            "truncated_sections": ctx.truncated_sections,
            "warnings": ctx.warnings,
            "rendered": assembler.render(ctx),
        }


# ---------------------------------------------------------------------------
# API Backend (platform mode — stub for T-020)
# ---------------------------------------------------------------------------

class APIBackend(ForgeBackend):
    """Backend using forge-api REST endpoints.

    Stub implementation — all methods raise NotImplementedError.
    Full implementation in T-020 (cli-remote-mode).
    """

    def __init__(self, api_url: str, api_key: str = "") -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}

    def _url(self, path: str) -> str:
        return f"{self.api_url}/api/v1{path}"

    def __getattr__(self, name: str) -> Any:
        """All unimplemented methods raise NotImplementedError."""
        def _not_implemented(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError(
                f"APIBackend.{name}() not yet implemented. "
                f"Install forge-api and use T-020 to enable remote mode."
            )
        return _not_implemented


# ---------------------------------------------------------------------------
# ForgeClient — public interface
# ---------------------------------------------------------------------------

class ForgeClient:
    """Unified client for all Forge operations.

    Automatically selects backend based on configuration:
    - standalone: JSONBackend (direct JSON file access)
    - local/remote: APIBackend (HTTP calls to forge-api)

    Usage::

        client = ForgeClient()  # auto-detect from config
        projects = client.list_projects()

        client = ForgeClient(ForgeConfig(mode="standalone", data_dir="./forge_output"))
        status = client.get_project_status("my-project")
    """

    def __init__(self, config: ForgeConfig | None = None) -> None:
        if config is None:
            config = load_config()
        self.config = config

        if config.mode == "standalone":
            self.backend: ForgeBackend = JSONBackend(data_dir=config.data_dir)
        else:
            self.backend = APIBackend(
                api_url=config.api_url,
                api_key=config.api_key,
            )

    @property
    def storage(self) -> Any:
        """Access underlying StorageAdapter (standalone mode only)."""
        if isinstance(self.backend, JSONBackend):
            return self.backend.storage
        raise AttributeError(
            "Direct storage access not available in API mode. "
            "Use client methods instead."
        )

    # Delegate all operations to backend
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the backend."""
        if name == "backend":
            raise AttributeError("ForgeClient not fully initialized")
        return getattr(self.backend, name)

"""Tasks router — CRUD + next (claim) + complete + context assembly."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    check_project_exists,
    emit_event,
    find_item,
    find_item_or_404,
    load_entity,
    load_global_entity,
    next_id,
    save_entity,
    save_global_entity,
)

router = APIRouter(prefix="/projects/{slug}/tasks", tags=["tasks"])

CLAIM_WAIT_SECONDS = 1.0


class TaskCreate(BaseModel):
    name: str
    description: str = ""
    instruction: str = ""
    type: str = "feature"
    depends_on: list[str] = []
    blocked_by_decisions: list[str] = []
    conflicts_with: list[str] = []
    acceptance_criteria: list = []
    scopes: list[str] = []
    parallel: bool = False
    skill: str | None = None
    skill_id: str | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    instruction: str | None = None
    status: str | None = None
    failed_reason: str | None = None
    blocked_by_decisions: list[str] | None = None


class TaskComplete(BaseModel):
    reasoning: str = ""


@router.get("")
async def list_tasks(
    slug: str,
    status: str | None = None,
    storage=Depends(get_storage),
):
    await check_project_exists(storage, slug)
    tracker = await load_entity(storage, slug, "tracker")
    tasks = tracker.get("tasks", [])
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    return {"tasks": tasks, "count": len(tasks)}


@router.post("", status_code=201)
async def add_tasks(slug: str, body: list[TaskCreate], storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        tasks = tracker.get("tasks", [])
        added = []
        linked_skill_ids: list[str] = []
        for item in body:
            task_id = next_id(tasks, "T")
            task = {
                "id": task_id,
                "name": item.name,
                "description": item.description,
                "instruction": item.instruction,
                "type": item.type,
                "status": "TODO",
                "depends_on": item.depends_on,
                "blocked_by_decisions": item.blocked_by_decisions,
                "conflicts_with": item.conflicts_with,
                "acceptance_criteria": item.acceptance_criteria,
                "scopes": item.scopes,
                "parallel": item.parallel,
                "skill": item.skill,
                "skill_id": item.skill_id,
            }
            tasks.append(task)
            added.append(task_id)
            if item.skill_id:
                linked_skill_ids.append(item.skill_id)
        tracker["tasks"] = tasks
        await save_entity(storage, slug, "tracker", tracker)

    # Increment usage_count for linked skills
    if linked_skill_ids:
        async with _get_lock("_global", "skills"):
            skills_data = await load_global_entity(storage, "skills")
            if "skills" in skills_data:
                for skill in skills_data["skills"]:
                    if skill.get("id") in linked_skill_ids:
                        skill["usage_count"] = skill.get("usage_count", 0) + linked_skill_ids.count(skill["id"])
                await save_global_entity(storage, "skills", skills_data)

    return {"added": added, "total": len(tasks)}


@router.get("/{task_id}")
async def get_task(slug: str, task_id: str, storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    tracker = await load_entity(storage, slug, "tracker")
    return find_item_or_404(tracker.get("tasks", []), task_id, "Task")


@router.patch("/{task_id}")
async def update_task(request: Request, slug: str, task_id: str, body: TaskUpdate, storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        task = find_item_or_404(tracker.get("tasks", []), task_id, "Task")
        old_status = task.get("status")
        updates = body.model_dump(exclude_none=True)
        for k, v in updates.items():
            task[k] = v
        await save_entity(storage, slug, "tracker", tracker)
    if "status" in updates and updates["status"] != old_status:
        await emit_event(request, slug, "task.status_changed", {
            "task_id": task_id, "old_status": old_status, "new_status": updates["status"],
        })
    return task


@router.delete("/{task_id}")
async def remove_task(slug: str, task_id: str, storage=Depends(get_storage)):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        tasks = tracker.get("tasks", [])
        task = find_item_or_404(tasks, task_id, "Task")
        if task.get("status") != "TODO":
            raise HTTPException(422, f"Can only remove TODO tasks, '{task_id}' is {task.get('status')}")
        # Check no other task depends on this
        for t in tasks:
            if task_id in t.get("depends_on", []):
                raise HTTPException(422, f"Task {t['id']} depends on {task_id}")
        tasks.remove(task)
        tracker["tasks"] = tasks
        await save_entity(storage, slug, "tracker", tracker)
    return {"removed": task_id}


@router.post("/next")
async def claim_next_task(
    request: Request,
    slug: str,
    agent: str | None = Query(None),
    storage=Depends(get_storage),
):
    """Claim the next available task (two-phase claim)."""
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        tasks = tracker.get("tasks", [])

        # Reset stale CLAIMING tasks (stuck from crashed/restarted server)
        import time
        _CLAIM_TIMEOUT = 30  # seconds
        now_ts = time.time()
        stale_reset = False
        for t in tasks:
            if t.get("status") == "CLAIMING":
                claimed_at = t.get("claimed_at", 0)
                if now_ts - claimed_at > _CLAIM_TIMEOUT:
                    t["status"] = "TODO"
                    t.pop("agent", None)
                    t.pop("claimed_at", None)
                    stale_reset = True
        if stale_reset:
            await save_entity(storage, slug, "tracker", tracker)

        done_ids = {t["id"] for t in tasks if t.get("status") == "DONE"}
        active_ids = {t["id"] for t in tasks if t.get("status") in ("IN_PROGRESS", "CLAIMING")}
        active_conflicts = set()
        for t in tasks:
            if t["id"] in active_ids:
                active_conflicts.update(t.get("conflicts_with", []))

        # Load decisions for blocked_by_decisions check (F-05)
        # Include all resolved statuses, not just CLOSED
        _RESOLVED_STATUSES = {"CLOSED", "DEFERRED", "MITIGATED", "ACCEPTED"}
        dec_data = await load_entity(storage, slug, "decisions")
        closed_decisions = {d["id"] for d in dec_data.get("decisions", []) if d.get("status") in _RESOLVED_STATUSES}

        claimed_id = None
        for task in tasks:
            if task.get("status") != "TODO":
                continue
            deps = set(task.get("depends_on", []))
            if not deps.issubset(done_ids):
                continue
            if task["id"] in active_conflicts:
                continue
            # Check blocked_by_decisions
            blocked = set(task.get("blocked_by_decisions", []))
            if blocked and not blocked.issubset(closed_decisions):
                continue

            # Phase 1: CLAIMING (only one task)
            task["status"] = "CLAIMING"
            task["claimed_at"] = time.time()
            if agent:
                task["agent"] = agent
            await save_entity(storage, slug, "tracker", tracker)
            claimed_id = task["id"]
            break

    if claimed_id is None:
        raise HTTPException(404, "No available tasks")

    # Wait for claim period
    await asyncio.sleep(CLAIM_WAIT_SECONDS)

    # Phase 2: verify and promote
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        tasks = tracker.get("tasks", [])
        task = find_item_or_404(tasks, claimed_id, "Task")

        if task.get("status") != "CLAIMING":
            raise HTTPException(409, f"Task {claimed_id} was claimed by another agent")
        if agent and task.get("agent") != agent:
            raise HTTPException(409, f"Task {claimed_id} was claimed by another agent")

        task["status"] = "IN_PROGRESS"
        task.pop("claimed_at", None)  # clean up temporary field
        await save_entity(storage, slug, "tracker", tracker)
        await emit_event(request, slug, "task.status_changed", {
            "task_id": claimed_id, "old_status": "TODO", "new_status": "IN_PROGRESS",
            "agent": agent,
        })
        return task


@router.post("/{task_id}/complete")
async def complete_task(
    request: Request,
    slug: str,
    task_id: str,
    body: TaskComplete | None = None,
    storage=Depends(get_storage),
):
    await check_project_exists(storage, slug)
    async with _get_lock(slug, "tracker"):
        tracker = await load_entity(storage, slug, "tracker")
        task = find_item_or_404(tracker.get("tasks", []), task_id, "Task")
        old_status = task.get("status")
        if old_status not in ("IN_PROGRESS", "CLAIMING"):
            raise HTTPException(422, f"Task must be IN_PROGRESS, is {old_status}")
        task["status"] = "DONE"
        await save_entity(storage, slug, "tracker", tracker)
    await emit_event(request, slug, "task.status_changed", {
        "task_id": task_id, "old_status": old_status, "new_status": "DONE",
    })
    return task


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4) if text else 0


def _make_section(name: str, header: str, content: str, max_tokens: int = 0) -> dict:
    """Build a context section with token estimate and optional truncation."""
    token_estimate = _estimate_tokens(content)
    was_truncated = False
    if max_tokens > 0 and token_estimate > max_tokens:
        # Truncate to approximate char limit
        char_limit = max_tokens * 4
        content = content[:char_limit] + "\n... [truncated]"
        token_estimate = max_tokens
        was_truncated = True
    return {
        "name": name,
        "header": header,
        "content": content,
        "token_estimate": token_estimate,
        "was_truncated": was_truncated,
    }


@router.get("/{task_id}/context")
async def get_task_context(slug: str, task_id: str, storage=Depends(get_storage)):
    """Assemble rich context for task execution — standalone context view."""
    await check_project_exists(storage, slug)
    tracker = await load_entity(storage, slug, "tracker")
    task = find_item_or_404(tracker.get("tasks", []), task_id, "Task")

    sections: list[dict] = []

    # --- Section 1: Task brief ---
    task_lines = [
        f"ID: {task.get('id', '')}",
        f"Name: {task.get('name', '')}",
        f"Type: {task.get('type', 'feature')}",
        f"Status: {task.get('status', 'TODO')}",
        "",
        "Description:",
        task.get("description", "(none)"),
    ]
    if task.get("instruction"):
        task_lines += ["", "Instruction:", task["instruction"]]
    if task.get("acceptance_criteria"):
        task_lines += ["", "Acceptance Criteria:"]
        for i, ac in enumerate(task["acceptance_criteria"], 1):
            task_lines.append(f"  {i}. {ac}")
    if task.get("scopes"):
        task_lines.append(f"\nScopes: {', '.join(task['scopes'])}")
    sections.append(_make_section("task", "Task Brief", "\n".join(task_lines)))

    # --- Section 2: Dependencies ---
    dep_ids = task.get("depends_on", [])
    if dep_ids:
        dep_lines = []
        for dep_id in dep_ids:
            dep = next((t for t in tracker.get("tasks", []) if t["id"] == dep_id), None)
            if dep:
                dep_lines.append(f"[{dep['id']}] {dep.get('name', '')} — {dep.get('status', '?')}")
                if dep.get("description"):
                    dep_lines.append(f"  {dep['description'][:200]}")
                dep_lines.append("")
        sections.append(_make_section("dependencies", "Dependencies", "\n".join(dep_lines)))

    # --- Section 3: Related decisions ---
    try:
        dec_data = await load_entity(storage, slug, "decisions")
        decisions = dec_data.get("decisions", [])
        # Include decisions linked to this task or blocking it
        blocked_dec_ids = set(task.get("blocked_by_decisions", []))
        relevant = [d for d in decisions if d.get("task_id") == task_id or d.get("id") in blocked_dec_ids]
        if relevant:
            dec_lines = []
            for d in relevant:
                dec_lines.append(f"[{d['id']}] {d.get('status', '?')} — {d.get('issue', '')}")
                if d.get("recommendation"):
                    dec_lines.append(f"  Recommendation: {d['recommendation'][:300]}")
                dec_lines.append("")
            sections.append(_make_section("decisions", "Related Decisions", "\n".join(dec_lines)))
    except Exception:
        pass

    # --- Section 4: Applicable guidelines ---
    try:
        gl_data = await load_entity(storage, slug, "guidelines")
        guidelines = gl_data.get("guidelines", [])
        task_scopes = set(task.get("scopes", []))
        applicable = [
            g for g in guidelines
            if g.get("status") == "ACTIVE" and (
                not task_scopes or g.get("scope", "") in task_scopes
                or g.get("scope", "") == "global"
            )
        ]
        if applicable:
            gl_lines = []
            for g in applicable:
                weight = g.get("weight", "should").upper()
                gl_lines.append(f"[{weight}] {g.get('title', '')} (scope: {g.get('scope', 'global')})")
                gl_lines.append(f"  {g.get('content', '')[:300]}")
                gl_lines.append("")
            sections.append(_make_section("guidelines", "Applicable Guidelines", "\n".join(gl_lines)))
    except Exception:
        pass

    # --- Section 5: Related knowledge ---
    try:
        kn_data = await load_entity(storage, slug, "knowledge")
        knowledge_items = kn_data.get("knowledge", [])
        task_scopes = set(task.get("scopes", []))
        relevant_kn = [
            k for k in knowledge_items
            if k.get("status") == "ACTIVE" and (
                not task_scopes or set(k.get("scopes", [])).intersection(task_scopes)
            )
        ]
        if relevant_kn:
            kn_lines = []
            for k in relevant_kn[:10]:  # Cap at 10
                kn_lines.append(f"[{k['id']}] {k.get('title', '')} ({k.get('category', '')})")
                content_preview = k.get("content", "")[:500]
                kn_lines.append(f"  {content_preview}")
                kn_lines.append("")
            sections.append(_make_section(
                "knowledge", "Related Knowledge", "\n".join(kn_lines), max_tokens=4000))
    except Exception:
        pass

    # --- Section 6: Recent changes from dependencies ---
    try:
        ch_data = await load_entity(storage, slug, "changes")
        changes = ch_data.get("changes", [])
        dep_changes = [c for c in changes if c.get("task_id") in dep_ids]
        if dep_changes:
            ch_lines = []
            for c in dep_changes[-20:]:  # Last 20
                ch_lines.append(
                    f"[{c.get('task_id', '?')}] {c.get('action', '?')} {c.get('file', '?')} — {c.get('summary', '')}")
            sections.append(_make_section("changes", "Changes from Dependencies", "\n".join(ch_lines)))
    except Exception:
        pass

    total_tokens = sum(s["token_estimate"] for s in sections)

    return {
        "task": task,
        "sections": sections,
        "total_token_estimate": total_tokens,
        "scopes": task.get("scopes", []),
    }

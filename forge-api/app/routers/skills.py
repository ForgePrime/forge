"""Skills router — CRUD for global platform skills (no project slug)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    emit_event,
    find_item_or_404,
    load_entity,
    next_id,
    save_entity,
)
from app.services.teslint import run_teslint

router = APIRouter(prefix="/skills", tags=["skills"])

# ---------------------------------------------------------------------------
# Storage key — skills are global (no project slug)
# ---------------------------------------------------------------------------
_GLOBAL = "__global__"
_ENTITY = "skills"

VALID_CATEGORIES = [
    "workflow", "analysis", "generation", "validation",
    "integration", "refactoring", "testing", "deployment",
    "documentation", "custom",
]
VALID_STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SkillCreate(BaseModel):
    name: str
    description: str = ""
    category: Literal[
        "workflow", "analysis", "generation", "validation",
        "integration", "refactoring", "testing", "deployment",
        "documentation", "custom",
    ] = "custom"
    skill_md_content: str | None = None
    evals_json: list[dict] = []
    resources: dict = {}
    teslint_config: dict | None = None
    tags: list[str] = []
    scopes: list[str] = []
    created_by: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: Literal[
        "workflow", "analysis", "generation", "validation",
        "integration", "refactoring", "testing", "deployment",
        "documentation", "custom",
    ] | None = None
    status: Literal["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"] | None = None
    skill_md_content: str | None = None
    evals_json: list[dict] | None = None
    resources: dict | None = None
    teslint_config: dict | None = None
    tags: list[str] | None = None
    scopes: list[str] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_data(data: dict) -> dict:
    """Ensure skills data has proper structure."""
    if "skills" not in data:
        data["skills"] = []
    return data


def _matches_filter(skill: dict, **filters) -> bool:
    """Check if skill matches all given filters."""
    for key, value in filters.items():
        if value is None:
            continue
        if key == "search":
            q = value.lower()
            if q not in skill.get("name", "").lower() and q not in skill.get("description", "").lower():
                return False
        elif key == "tags":
            skill_tags = set(skill.get("tags", []))
            if not skill_tags.intersection(value):
                return False
        elif key == "scopes":
            skill_scopes = set(skill.get("scopes", []))
            if not skill_scopes.intersection(value):
                return False
        elif key in ("category", "status"):
            if skill.get(key) != value:
                return False
    return True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_skills(
    category: str | None = Query(None),
    status: str | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tag filter"),
    scopes: str | None = Query(None, description="Comma-separated scope filter"),
    search: str | None = Query(None, description="Search name/description"),
    storage=Depends(get_storage),
):
    """List all skills with optional filters."""
    data = await load_entity(storage, _GLOBAL, _ENTITY)
    data = _ensure_data(data)
    skills = data["skills"]

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    scope_list = [s.strip() for s in scopes.split(",")] if scopes else None

    filtered = [
        s for s in skills
        if _matches_filter(s, category=category, status=status,
                           tags=tag_list, scopes=scope_list, search=search)
    ]

    return {"skills": filtered, "count": len(filtered)}


@router.post("", status_code=201)
async def create_skills(
    body: list[SkillCreate],
    request: Request,
    storage=Depends(get_storage),
):
    """Batch create skills. Returns generated IDs."""
    if not body:
        raise HTTPException(422, "At least one skill is required")

    added = []
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skills = data["skills"]

        for item in body:
            skill_id = next_id(skills, "S")
            now = _now_iso()
            skill = {
                "id": skill_id,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "status": "DRAFT",
                "skill_md_content": item.skill_md_content,
                "evals_json": item.evals_json,
                "resources": item.resources,
                "teslint_config": item.teslint_config,
                "tags": item.tags,
                "scopes": item.scopes,
                "promoted_with_warnings": False,
                "promotion_history": [],
                "usage_count": 0,
                "created_by": item.created_by,
                "created_at": now,
                "updated_at": now,
            }
            skills.append(skill)
            added.append(skill_id)

        await save_entity(storage, _GLOBAL, _ENTITY, data)

    for sid in added:
        await emit_event(request, _GLOBAL, "skill.created", {"id": sid})

    return {"added": added, "total": len(data["skills"])}


@router.get("/{skill_id}")
async def get_skill(skill_id: str, storage=Depends(get_storage)):
    """Get a single skill by ID."""
    data = await load_entity(storage, _GLOBAL, _ENTITY)
    data = _ensure_data(data)
    skill = find_item_or_404(data["skills"], skill_id, "Skill")
    return skill


@router.patch("/{skill_id}")
async def update_skill(
    skill_id: str,
    body: SkillUpdate,
    request: Request,
    storage=Depends(get_storage),
):
    """Update a skill. Status transitions validated."""
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        updates = body.model_dump(exclude_none=True)
        if not updates:
            return skill

        # Status transition validation
        # NOTE: DRAFT→ACTIVE is NOT allowed via PATCH — use POST /skills/{id}/promote
        # which enforces gates (valid SKILL.md, evals, TESLint). See G-015, T-082.
        if "status" in updates:
            new_status = updates["status"]
            current = skill.get("status", "DRAFT")
            valid_transitions = {
                "DRAFT": {"DEPRECATED"},
                "ACTIVE": {"DEPRECATED"},
                "DEPRECATED": {"ARCHIVED", "ACTIVE"},
                "ARCHIVED": set(),
            }
            if new_status not in valid_transitions.get(current, set()):
                raise HTTPException(
                    422,
                    f"Cannot transition from {current} to {new_status}. "
                    f"Valid: {valid_transitions.get(current, set())}",
                )

        for key, value in updates.items():
            skill[key] = value
        skill["updated_at"] = _now_iso()

        await save_entity(storage, _GLOBAL, _ENTITY, data)

    await emit_event(request, _GLOBAL, "skill.updated", {"id": skill_id})
    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    request: Request,
    storage=Depends(get_storage),
):
    """Delete a skill. Blocked if used by IN_PROGRESS tasks."""
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        # Check usage: scan all projects for IN_PROGRESS tasks referencing this skill
        # For now, check usage_count as a guard
        if skill.get("status") == "ACTIVE" and skill.get("usage_count", 0) > 0:
            raise HTTPException(
                409,
                f"Cannot delete ACTIVE skill '{skill_id}' with {skill['usage_count']} tasks using it. "
                "Set status to DEPRECATED first.",
            )

        data["skills"] = [s for s in data["skills"] if s.get("id") != skill_id]
        await save_entity(storage, _GLOBAL, _ENTITY, data)

    await emit_event(request, _GLOBAL, "skill.deleted", {"id": skill_id})
    return {"removed": skill_id}


# ---------------------------------------------------------------------------
# Lint endpoint
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/lint")
async def lint_skill(
    skill_id: str,
    storage=Depends(get_storage),
):
    """Run TESLint on a skill's SKILL.md content. Returns findings."""
    data = await load_entity(storage, _GLOBAL, _ENTITY)
    data = _ensure_data(data)
    skill = find_item_or_404(data["skills"], skill_id, "Skill")

    content = skill.get("skill_md_content")
    if not content:
        raise HTTPException(422, f"Skill '{skill_id}' has no SKILL.md content to lint")

    import asyncio
    result = await asyncio.to_thread(
        run_teslint,
        skill.get("name", skill_id),
        content,
        skill.get("teslint_config"),
    )

    findings = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "message": f.message,
            "line": f.line,
            "column": f.column,
        }
        for f in result.findings
    ]

    return {
        "skill_id": skill_id,
        "success": result.success,
        "passed": result.passed,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "info_count": result.info_count,
        "findings": findings,
        "error_message": result.error_message,
    }


# ---------------------------------------------------------------------------
# Promote endpoint — DRAFT → ACTIVE with 3-gate validation
# ---------------------------------------------------------------------------

class PromoteRequest(BaseModel):
    force: bool = False


@router.post("/{skill_id}/promote")
async def promote_skill(
    skill_id: str,
    body: PromoteRequest,
    request: Request,
    storage=Depends(get_storage),
):
    """Promote a skill from DRAFT to ACTIVE.

    Three gates:
    1. SKILL.md has YAML frontmatter with name + description
    2. evals_json has at least 1 entry
    3. TESLint passes with 0 errors

    If all pass: DRAFT → ACTIVE.
    If TESLint fails and force=True: DRAFT → ACTIVE + promoted_with_warnings=True.
    """
    async with _get_lock(_GLOBAL, _ENTITY):
        data = await load_entity(storage, _GLOBAL, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        if skill.get("status") != "DRAFT":
            raise HTTPException(
                422,
                f"Only DRAFT skills can be promoted. Current status: {skill.get('status')}",
            )

        # --- Gate 1: SKILL.md frontmatter ---
        gate_results = []
        content = skill.get("skill_md_content", "") or ""

        has_frontmatter = content.strip().startswith("---")
        has_name = bool(skill.get("name"))
        has_description = bool(skill.get("description"))
        gate1_passed = has_frontmatter and has_name and has_description
        gate_results.append({
            "gate": "frontmatter",
            "passed": gate1_passed,
            "detail": (
                "SKILL.md has valid frontmatter with name and description"
                if gate1_passed
                else "Missing: "
                + (", ".join(filter(None, [
                    "YAML frontmatter (---)" if not has_frontmatter else None,
                    "name" if not has_name else None,
                    "description" if not has_description else None,
                ])))
            ),
        })

        # --- Gate 2: Evals ---
        evals = skill.get("evals_json", [])
        gate2_passed = len(evals) >= 1
        gate_results.append({
            "gate": "evals",
            "passed": gate2_passed,
            "detail": (
                f"{len(evals)} eval(s) defined"
                if gate2_passed
                else "At least 1 eval test case required"
            ),
        })

        # --- Gate 3: TESLint ---
        gate3_passed = False
        teslint_error_count = 0
        teslint_warning_count = 0
        if content.strip():
            import asyncio
            lint_result = await asyncio.to_thread(
                run_teslint,
                skill.get("name", skill_id),
                content,
                skill.get("teslint_config"),
            )
            gate3_passed = lint_result.passed
            teslint_error_count = lint_result.error_count
            teslint_warning_count = lint_result.warning_count

            if not lint_result.success and lint_result.error_message:
                gate_results.append({
                    "gate": "teslint",
                    "passed": False,
                    "detail": f"TESLint error: {lint_result.error_message}",
                })
            else:
                gate_results.append({
                    "gate": "teslint",
                    "passed": gate3_passed,
                    "detail": (
                        f"TESLint passed ({teslint_warning_count} warnings)"
                        if gate3_passed
                        else f"TESLint found {teslint_error_count} error(s), {teslint_warning_count} warning(s)"
                    ),
                })
        else:
            gate_results.append({
                "gate": "teslint",
                "passed": False,
                "detail": "No SKILL.md content to lint",
            })

        # --- Decision ---
        all_passed = gate1_passed and gate2_passed and gate3_passed
        can_promote = all_passed or (gate1_passed and gate2_passed and body.force)

        if not can_promote:
            failed = [g for g in gate_results if not g["passed"]]
            msg = "Promotion blocked. Failed gates: " + "; ".join(
                f"{g['gate']}: {g['detail']}" for g in failed
            )
            if not body.force and not gate3_passed and gate1_passed and gate2_passed:
                msg += ". Use force=true to override TESLint errors."
            raise HTTPException(422, msg)

        # Promote
        now = _now_iso()
        skill["status"] = "ACTIVE"
        skill["promoted_with_warnings"] = not all_passed  # True if force-promoted
        skill["updated_at"] = now

        # Append promotion history
        history_entry = {
            "promoted_at": now,
            "error_count": teslint_error_count,
            "warning_count": teslint_warning_count,
            "forced": body.force and not all_passed,
            "gates": gate_results,
        }
        if "promotion_history" not in skill:
            skill["promotion_history"] = []
        skill["promotion_history"].append(history_entry)

        await save_entity(storage, _GLOBAL, _ENTITY, data)

    await emit_event(request, _GLOBAL, "skill.promoted", {"id": skill_id})

    return {
        "skill_id": skill_id,
        "status": "ACTIVE",
        "promoted_with_warnings": skill["promoted_with_warnings"],
        "gates": gate_results,
    }

"""Skills router — CRUD + lint + promote + generate + import/export + categories."""

from __future__ import annotations

import asyncio
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

from app.dependencies import get_storage
from app.routers._helpers import (
    _get_lock,
    emit_event,
    find_item_or_404,
    load_global_entity,
    next_id,
    save_global_entity,
)
from app.services.frontmatter import (
    generate_frontmatter,
    merge_frontmatter_to_metadata,
    parse_frontmatter,
)
from app.services.teslint import check_teslint_available, run_teslint

router = APIRouter(prefix="/skills", tags=["skills"])

# ---------------------------------------------------------------------------
# Storage key — skills are global, stored in _global/skills.json
# ---------------------------------------------------------------------------
_ENTITY = "skills"
_LOCK_NS = "_global"  # Lock namespace (not a file path)

DEFAULT_CATEGORIES = [
    "workflow", "analysis", "generation", "validation",
    "integration", "refactoring", "testing", "deployment",
    "documentation", "custom",
]
VALID_STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]

DEFAULT_CATEGORY_COLORS: dict[str, str] = {
    "workflow": "blue",
    "analysis": "purple",
    "generation": "green",
    "validation": "yellow",
    "integration": "cyan",
    "refactoring": "orange",
    "testing": "red",
    "deployment": "indigo",
    "documentation": "gray",
    "custom": "slate",
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SkillCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "custom"
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
    category: str | None = None
    status: Literal["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"] | None = None
    skill_md_content: str | None = None
    evals_json: list[dict] | None = None
    resources: dict | None = None
    teslint_config: dict | None = None
    tags: list[str] | None = None
    scopes: list[str] | None = None


class SkillImportRequest(BaseModel):
    content: str
    filename: str | None = None
    category: str | None = None


class SkillGenerateRequest(BaseModel):
    description: str
    category: str | None = None
    examples: list[str] = []
    style_hints: str | None = None


class BulkExportRequest(BaseModel):
    skill_ids: list[str] | None = None
    format: Literal["json", "zip"] = "zip"


class CategoryCreate(BaseModel):
    key: str
    label: str
    color: str = "slate"


class PromoteRequest(BaseModel):
    force: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_data(data: dict) -> dict:
    """Ensure skills data has proper structure."""
    if "skills" not in data:
        data["skills"] = []
    if "config" not in data:
        data["config"] = {}
    if "custom_categories" not in data.get("config", {}):
        data.setdefault("config", {})["custom_categories"] = []
    return data


def _get_all_categories(data: dict) -> list[dict]:
    """Return all categories (defaults + custom) with colors."""
    categories = []
    for key in DEFAULT_CATEGORIES:
        categories.append({
            "key": key,
            "label": key.capitalize(),
            "color": DEFAULT_CATEGORY_COLORS.get(key, "slate"),
            "is_default": True,
        })
    for cat in data.get("config", {}).get("custom_categories", []):
        categories.append({
            "key": cat["key"],
            "label": cat.get("label", cat["key"].capitalize()),
            "color": cat.get("color", "slate"),
            "is_default": False,
        })
    return categories


def _valid_category_keys(data: dict) -> set[str]:
    """Return set of valid category keys (defaults + custom)."""
    keys = set(DEFAULT_CATEGORIES)
    for cat in data.get("config", {}).get("custom_categories", []):
        keys.add(cat["key"])
    return keys


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


async def _check_skill_in_use(storage, skill_id: str) -> list[dict]:
    """Scan all projects for IN_PROGRESS tasks referencing this skill."""
    from app.routers._helpers import load_entity
    in_use = []
    try:
        projects = await asyncio.to_thread(storage.list_projects)
        for proj in projects:
            try:
                tracker = await load_entity(storage, proj, "tracker")
                for task in tracker.get("tasks", []):
                    if task.get("status") != "IN_PROGRESS":
                        continue
                    if task.get("skill_id") == skill_id:
                        in_use.append({
                            "project": proj,
                            "task_id": task.get("id"),
                            "task_name": task.get("name"),
                        })
            except Exception:
                continue
    except Exception:
        pass
    return in_use


# ---------------------------------------------------------------------------
# Fixed-path endpoints (MUST be before parameterized /{skill_id} routes)
# ---------------------------------------------------------------------------

@router.get("/health")
async def skills_health():
    """Health check for skills subsystem including TESLint availability."""
    teslint_status = await asyncio.to_thread(check_teslint_available)
    return {"status": "ok", "teslint": teslint_status}


@router.post("/lint-all")
async def lint_all_skills(
    status: str | None = Query(None),
    category: str | None = Query(None),
    storage=Depends(get_storage),
):
    """Run TESLint on all skills (or filtered). Returns results matrix."""
    data = await load_global_entity(storage, _ENTITY)
    data = _ensure_data(data)
    skills = data["skills"]

    if status:
        skills = [s for s in skills if s.get("status") == status]
    if category:
        skills = [s for s in skills if s.get("category") == category]

    lintable = [s for s in skills if s.get("skill_md_content")]

    sem = asyncio.Semaphore(4)

    async def _lint_one(skill: dict) -> dict:
        async with sem:
            result = await asyncio.to_thread(
                run_teslint,
                skill.get("name", skill["id"]),
                skill["skill_md_content"],
                skill.get("teslint_config"),
            )
            return {
                "skill_id": skill["id"],
                "skill_name": skill.get("name", ""),
                "status": skill.get("status", "DRAFT"),
                "passed": result.passed,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "error_message": result.error_message,
            }

    results = await asyncio.gather(*[_lint_one(s) for s in lintable])

    return {
        "results": list(results),
        "total": len(lintable),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
    }


@router.post("/import", status_code=201)
async def import_skill(
    body: SkillImportRequest,
    request: Request,
    storage=Depends(get_storage),
):
    """Import a skill from raw SKILL.md content."""
    fm = parse_frontmatter(body.content)

    name = fm.name or body.filename or "Imported Skill"
    description = fm.description or ""
    category = body.category or "custom"

    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)
        skills = data["skills"]

        skill_id = next_id(skills, "S")
        now = _now_iso()
        skill = {
            "id": skill_id,
            "name": name,
            "description": description,
            "category": category,
            "status": "DRAFT",
            "skill_md_content": body.content,
            "evals_json": [],
            "resources": {},
            "teslint_config": None,
            "tags": [],
            "scopes": [],
            "promoted_with_warnings": False,
            "promotion_history": [],
            "usage_count": 0,
            "created_by": "import",
            "created_at": now,
            "updated_at": now,
        }
        skills.append(skill)
        await save_global_entity(storage, _ENTITY, data)

    await emit_event(request, _LOCK_NS, "skill.created", {"id": skill_id})
    return {"skill_id": skill_id, "name": name, "parsed_frontmatter": fm.raw}


@router.post("/export-bulk")
async def export_bulk(body: BulkExportRequest, storage=Depends(get_storage)):
    """Export multiple skills as JSON or ZIP of .md files."""
    data = await load_global_entity(storage, _ENTITY)
    data = _ensure_data(data)
    skills = data["skills"]

    if body.skill_ids:
        skills = [s for s in skills if s.get("id") in body.skill_ids]

    if body.format == "json":
        return {"skills": skills, "count": len(skills)}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for skill in skills:
            content = skill.get("skill_md_content") or ""
            if not content:
                content = generate_frontmatter(
                    name=skill.get("name", skill["id"]),
                    description=skill.get("description", ""),
                ) + f"\n\n# {skill.get('name', skill['id'])}\n"
            safe_name = skill.get("name", skill["id"]).replace(" ", "-").replace("/", "_")
            zf.writestr(f"{safe_name}.SKILL.md", content)

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="skills-export.zip"'},
    )


@router.post("/generate")
async def generate_skill(body: SkillGenerateRequest):
    """Generate SKILL.md content from description (mock mode)."""
    desc = body.description.strip()
    words = desc.split()
    name = "-".join(words[:3]).lower().replace(",", "").replace(".", "")
    if len(name) > 40:
        name = name[:40]
    title = " ".join(words[:5]).title()
    id_upper = name.upper().replace("-", "_")

    content = _SKILL_TEMPLATE.format(
        name=name,
        id_upper=id_upper,
        description=desc,
        title=title,
        purpose=desc[:80].lower(),
        core_instruction=desc,
    )

    fm = parse_frontmatter(content)

    return {
        "skill_md_content": content,
        "parsed_metadata": {
            "name": fm.name,
            "description": fm.description,
            "version": fm.version,
            "allowed_tools": fm.allowed_tools,
        },
    }


@router.get("/categories")
async def list_categories(storage=Depends(get_storage)):
    """List all skill categories with colors."""
    data = await load_global_entity(storage, _ENTITY)
    data = _ensure_data(data)
    return {"categories": _get_all_categories(data)}


@router.post("/categories", status_code=201)
async def add_category(body: CategoryCreate, storage=Depends(get_storage)):
    """Add a custom skill category."""
    if body.key in DEFAULT_CATEGORIES:
        raise HTTPException(422, f"Category '{body.key}' is a default and cannot be re-added")

    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)
        custom = data["config"]["custom_categories"]

        if any(c["key"] == body.key for c in custom):
            raise HTTPException(422, f"Category '{body.key}' already exists")

        custom.append({"key": body.key, "label": body.label, "color": body.color})
        await save_global_entity(storage, _ENTITY, data)

    return {"added": body.key, "categories": _get_all_categories(data)}


@router.delete("/categories/{key}")
async def remove_category(key: str, storage=Depends(get_storage)):
    """Remove a custom category. Default categories cannot be removed."""
    if key in DEFAULT_CATEGORIES:
        raise HTTPException(422, f"Cannot remove default category '{key}'")

    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)

        using = [s for s in data["skills"] if s.get("category") == key]
        if using:
            raise HTTPException(
                409,
                f"Cannot remove category '{key}' — used by {len(using)} skill(s)",
            )

        custom = data["config"]["custom_categories"]
        data["config"]["custom_categories"] = [c for c in custom if c["key"] != key]
        await save_global_entity(storage, _ENTITY, data)

    return {"removed": key}


# ---------------------------------------------------------------------------
# CRUD endpoints
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
    data = await load_global_entity(storage, _ENTITY)
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
    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)
        skills = data["skills"]

        for item in body:
            name = item.name
            description = item.description
            if item.skill_md_content:
                meta = merge_frontmatter_to_metadata(item.skill_md_content)
                if not name and meta.get("name"):
                    name = meta["name"]
                if not description and meta.get("description"):
                    description = meta["description"]

            skill_id = next_id(skills, "S")
            now = _now_iso()
            skill = {
                "id": skill_id,
                "name": name,
                "description": description,
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

        await save_global_entity(storage, _ENTITY, data)

    for sid in added:
        await emit_event(request, _LOCK_NS, "skill.created", {"id": sid})

    return {"added": added, "total": len(data["skills"])}


# ---------------------------------------------------------------------------
# Parameterized endpoints (/{skill_id} — AFTER all fixed paths)
# ---------------------------------------------------------------------------

@router.get("/{skill_id}")
async def get_skill(skill_id: str, storage=Depends(get_storage)):
    """Get a single skill by ID."""
    data = await load_global_entity(storage, _ENTITY)
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
    """Update a skill. Auto-parses frontmatter when content changes."""
    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        updates = body.model_dump(exclude_none=True)
        if not updates:
            return skill

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

        if "skill_md_content" in updates and updates["skill_md_content"]:
            meta = merge_frontmatter_to_metadata(updates["skill_md_content"])
            if meta.get("name") and "name" not in updates:
                updates["name"] = meta["name"]
            if meta.get("description") and "description" not in updates:
                updates["description"] = meta["description"]

        for key, value in updates.items():
            skill[key] = value
        skill["updated_at"] = _now_iso()

        await save_global_entity(storage, _ENTITY, data)

    await emit_event(request, _LOCK_NS, "skill.updated", {"id": skill_id})
    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    request: Request,
    storage=Depends(get_storage),
):
    """Delete a skill. Blocked if used by IN_PROGRESS tasks."""
    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)
        find_item_or_404(data["skills"], skill_id, "Skill")

        in_use = await _check_skill_in_use(storage, skill_id)
        if in_use:
            task_list = ", ".join(f"{u['project']}/{u['task_id']}" for u in in_use)
            raise HTTPException(
                409,
                f"Cannot delete skill '{skill_id}' — used by IN_PROGRESS tasks: {task_list}",
            )

        data["skills"] = [s for s in data["skills"] if s.get("id") != skill_id]
        await save_global_entity(storage, _ENTITY, data)

    await emit_event(request, _LOCK_NS, "skill.deleted", {"id": skill_id})
    return {"removed": skill_id}


# ---------------------------------------------------------------------------
# Lint endpoint (per-skill)
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/lint")
async def lint_skill(skill_id: str, storage=Depends(get_storage)):
    """Run TESLint on a skill's SKILL.md content."""
    data = await load_global_entity(storage, _ENTITY)
    data = _ensure_data(data)
    skill = find_item_or_404(data["skills"], skill_id, "Skill")

    content = skill.get("skill_md_content")
    if not content:
        raise HTTPException(422, f"Skill '{skill_id}' has no SKILL.md content to lint")

    result = await asyncio.to_thread(
        run_teslint, skill.get("name", skill_id), content, skill.get("teslint_config"),
    )

    findings = [
        {"rule_id": f.rule_id, "severity": f.severity, "message": f.message,
         "line": f.line, "column": f.column}
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
# Promote endpoint
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/promote")
async def promote_skill(
    skill_id: str,
    body: PromoteRequest,
    request: Request,
    storage=Depends(get_storage),
):
    """Promote DRAFT → ACTIVE with 3-gate validation."""
    async with _get_lock(_LOCK_NS, _ENTITY):
        data = await load_global_entity(storage, _ENTITY)
        data = _ensure_data(data)
        skill = find_item_or_404(data["skills"], skill_id, "Skill")

        if skill.get("status") != "DRAFT":
            raise HTTPException(422, f"Only DRAFT skills can be promoted. Current: {skill.get('status')}")

        content = skill.get("skill_md_content", "") or ""
        gate_results = []

        fm = parse_frontmatter(content)
        gate1_passed = fm.valid and bool(skill.get("name")) and bool(skill.get("description"))
        gate_results.append({
            "gate": "frontmatter",
            "passed": gate1_passed,
            "detail": (
                "Valid SKILL.md frontmatter with name and description"
                if gate1_passed
                else "Missing: " + ", ".join(fm.errors or ["name or description"])
            ),
        })

        evals = skill.get("evals_json", [])
        gate2_passed = len(evals) >= 1
        gate_results.append({
            "gate": "evals",
            "passed": gate2_passed,
            "detail": f"{len(evals)} eval(s) defined" if gate2_passed else "At least 1 eval required",
        })

        gate3_passed = False
        teslint_error_count = 0
        teslint_warning_count = 0
        if content.strip():
            lint_result = await asyncio.to_thread(
                run_teslint, skill.get("name", skill_id), content, skill.get("teslint_config"),
            )
            gate3_passed = lint_result.passed
            teslint_error_count = lint_result.error_count
            teslint_warning_count = lint_result.warning_count
            gate_results.append({
                "gate": "teslint",
                "passed": gate3_passed,
                "detail": (
                    f"TESLint passed ({teslint_warning_count} warnings)"
                    if gate3_passed
                    else lint_result.error_message or f"TESLint: {teslint_error_count} error(s)"
                ),
            })
        else:
            gate_results.append({"gate": "teslint", "passed": False, "detail": "No content to lint"})

        all_passed = gate1_passed and gate2_passed and gate3_passed
        can_promote = all_passed or (gate1_passed and gate2_passed and body.force)

        if not can_promote:
            failed = [g for g in gate_results if not g["passed"]]
            msg = "Promotion blocked: " + "; ".join(f"{g['gate']}: {g['detail']}" for g in failed)
            if not body.force and not gate3_passed and gate1_passed and gate2_passed:
                msg += ". Use force=true to override TESLint."
            raise HTTPException(422, msg)

        now = _now_iso()
        skill["status"] = "ACTIVE"
        skill["promoted_with_warnings"] = not all_passed
        skill["updated_at"] = now
        skill.setdefault("promotion_history", []).append({
            "promoted_at": now,
            "error_count": teslint_error_count,
            "warning_count": teslint_warning_count,
            "forced": body.force and not all_passed,
            "gates": gate_results,
        })

        await save_global_entity(storage, _ENTITY, data)

    await emit_event(request, _LOCK_NS, "skill.promoted", {"id": skill_id})
    return {
        "skill_id": skill_id,
        "status": "ACTIVE",
        "promoted_with_warnings": skill["promoted_with_warnings"],
        "gates": gate_results,
    }


# ---------------------------------------------------------------------------
# Export (per-skill, parameterized)
# ---------------------------------------------------------------------------

@router.get("/{skill_id}/export")
async def export_skill(skill_id: str, storage=Depends(get_storage)):
    """Export a skill as a downloadable .md file."""
    data = await load_global_entity(storage, _ENTITY)
    data = _ensure_data(data)
    skill = find_item_or_404(data["skills"], skill_id, "Skill")

    content = skill.get("skill_md_content") or ""
    if not content:
        content = generate_frontmatter(
            name=skill.get("name", skill_id),
            description=skill.get("description", ""),
        ) + f"\n\n# {skill.get('name', skill_id)}\n"

    safe_name = skill.get("name", skill_id).replace(" ", "-").replace("/", "_")
    filename = f"{safe_name}.SKILL.md"

    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Generate template (LLM / mock)
# ---------------------------------------------------------------------------

_SKILL_TEMPLATE = """---
name: {name}
id: SKILL-{id_upper}
version: "1.0.0"
description: >
  {description}
allowed-tools: [Read, Glob, Grep, Bash]
---

# {title}

{description}

## What This Adds (Beyond Native Capability)

- Structured, repeatable procedure for {purpose}
- Explicit success criteria and verification steps
- Scope transparency — states what is NOT covered

## Procedure

### Step 1: Gather Context

Read relevant files and understand the current state.

### Step 2: Execute Core Task

{core_instruction}

### Step 3: Validate Results

Verify that the output meets the success criteria.

## Output Format

Present results in a structured format with clear sections.

## Success Criteria

- [ ] Core task completed successfully
- [ ] Output follows the specified format
- [ ] No unintended side effects

## Rules

- Always verify before reporting completion
- Document any assumptions made
- Flag uncertainties explicitly

## Scope Transparency

This skill does NOT:
- Handle edge cases beyond the described scope
- Make architectural decisions without user input
- Modify files outside the specified scope
"""



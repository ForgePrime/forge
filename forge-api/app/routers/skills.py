"""Skills router — CRUD + lint + promote + generate + import/export + categories + git sync.

Refactored to use file-based SkillStorageService (per-skill directories)
instead of monolithic skills.json.  Routing by skill name (slug) instead of ID.
"""

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

from app.dependencies import get_skill_storage, get_git_sync, get_storage
from app.routers._helpers import emit_event
from app.services.frontmatter import (
    generate_frontmatter,
    merge_frontmatter_to_metadata,
    parse_frontmatter,
)
from app.services.agentskills_validator import (
    validate_skill_name,
    validate_skill_description,
    validate_skill_structure,
)
from app.services.teslint import check_teslint_available, run_teslint
from app.services.skill_storage import SkillStorageService
from app.services.git_sync import GitSyncService, GitSyncNotConfigured, GitSyncError

router = APIRouter(prefix="/skills", tags=["skills"])

_WS_NS = "_global"

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
    categories: list[str] = ["custom"]
    skill_md_content: str | None = None
    evals_json: list[dict] = []
    teslint_config: dict | None = None
    tags: list[str] = []
    scopes: list[str] = []
    created_by: str | None = None


class SkillUpdate(BaseModel):
    description: str | None = None
    categories: list[str] | None = None
    status: Literal["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"] | None = None
    skill_md_content: str | None = None
    evals_json: list[dict] | None = None
    teslint_config: dict | None = None
    tags: list[str] | None = None
    scopes: list[str] | None = None
    sync: bool | None = None


class SkillImportRequest(BaseModel):
    content: str
    filename: str | None = None
    categories: list[str] | None = None


class SkillGenerateRequest(BaseModel):
    description: str
    categories: list[str] | None = None
    examples: list[str] = []
    style_hints: str | None = None


class BulkExportRequest(BaseModel):
    names: list[str] | None = None
    format: Literal["json", "zip"] = "zip"


class CategoryCreate(BaseModel):
    key: str
    label: str
    color: str = "slate"


class PromoteRequest(BaseModel):
    force: bool = False


class FileMoveRequest(BaseModel):
    old_path: str
    new_path: str


class GitPushRequest(BaseModel):
    message: str = "Sync skills"


class SkillsConfigUpdate(BaseModel):
    repo_url: str | None = None
    skills_dir: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_all_categories(custom_categories: list[dict] | None = None) -> list[dict]:
    """Return all categories (defaults + custom) with colors."""
    categories = []
    for key in DEFAULT_CATEGORIES:
        categories.append({
            "key": key,
            "label": key.capitalize(),
            "color": DEFAULT_CATEGORY_COLORS.get(key, "slate"),
            "is_default": True,
        })
    for cat in (custom_categories or []):
        categories.append({
            "key": cat["key"],
            "label": cat.get("label", cat["key"].capitalize()),
            "color": cat.get("color", "slate"),
            "is_default": False,
        })
    return categories


def _slugify(name: str) -> str:
    """Convert a name to a valid slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


# ---------------------------------------------------------------------------
# Fixed-path endpoints (MUST be before parameterized /{name} routes)
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
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Run TESLint on all skills (or filtered). Returns results matrix."""
    skills = await svc.list_skills(status=status, category=category)
    # Need full skill content for linting — read each
    lintable = []
    for entry in skills:
        try:
            full = await svc.get_skill(entry["name"])
            if full.get("skill_md_content"):
                lintable.append(full)
        except FileNotFoundError:
            continue

    sem = asyncio.Semaphore(4)

    async def _lint_one(skill: dict) -> dict:
        async with sem:
            result = await asyncio.to_thread(
                run_teslint,
                skill["name"],
                skill["skill_md_content"],
                skill.get("teslint_config"),
            )
            return {
                "skill_name": skill["name"],
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
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Import a skill from raw SKILL.md content."""
    fm = parse_frontmatter(body.content)

    raw_name = fm.name or body.filename or "imported-skill"
    name = _slugify(raw_name)
    description = fm.description or ""
    categories = body.categories or ["custom"]

    try:
        skill = await svc.create_skill(name, {
            "description": description,
            "categories": categories,
            "created_by": "import",
        })
    except ValueError as e:
        raise HTTPException(422, str(e))

    # Write the imported SKILL.md content
    await svc.save_skill(name, content=body.content)

    await emit_event(request, _WS_NS, "skill.created", {"name": name})
    return {"name": name, "parsed_frontmatter": fm.raw}


@router.post("/export-bulk")
async def export_bulk(
    body: BulkExportRequest,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Export multiple skills as JSON or ZIP of .md files."""
    all_skills = await svc.list_skills()
    if body.names:
        all_skills = [s for s in all_skills if s["name"] in body.names]

    if body.format == "json":
        # Fetch full content
        full_skills = []
        for entry in all_skills:
            try:
                full_skills.append(await svc.get_skill(entry["name"]))
            except FileNotFoundError:
                continue
        return {"skills": full_skills, "count": len(full_skills)}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in all_skills:
            try:
                full = await svc.get_skill(entry["name"])
                content = full.get("skill_md_content") or ""
                if not content:
                    content = generate_frontmatter(
                        name=entry["name"],
                        description=entry.get("description", ""),
                    ) + f"\n\n# {entry['name']}\n"
                zf.writestr(f"{entry['name']}.SKILL.md", content)
            except FileNotFoundError:
                continue

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
    from app.routers._helpers import load_global_entity
    data = await load_global_entity(storage, "skills")
    custom = data.get("config", {}).get("custom_categories", [])
    return {"categories": _get_all_categories(custom)}


@router.post("/categories", status_code=201)
async def add_category(body: CategoryCreate, storage=Depends(get_storage)):
    """Add a custom skill category."""
    from app.routers._helpers import load_global_entity, save_global_entity, _get_lock
    if body.key in DEFAULT_CATEGORIES:
        raise HTTPException(422, f"Category '{body.key}' is a default and cannot be re-added")

    async with _get_lock("_global", "skills"):
        data = await load_global_entity(storage, "skills")
        if "config" not in data:
            data["config"] = {}
        if "custom_categories" not in data["config"]:
            data["config"]["custom_categories"] = []
        custom = data["config"]["custom_categories"]

        if any(c["key"] == body.key for c in custom):
            raise HTTPException(422, f"Category '{body.key}' already exists")

        custom.append({"key": body.key, "label": body.label, "color": body.color})
        await save_global_entity(storage, "skills", data)

    return {"added": body.key, "categories": _get_all_categories(custom)}


@router.delete("/categories/{key}")
async def remove_category(
    key: str,
    svc: SkillStorageService = Depends(get_skill_storage),
    storage=Depends(get_storage),
):
    """Remove a custom category. Default categories cannot be removed."""
    from app.routers._helpers import load_global_entity, save_global_entity, _get_lock
    if key in DEFAULT_CATEGORIES:
        raise HTTPException(422, f"Cannot remove default category '{key}'")

    # Check if any skill uses this category
    skills = await svc.list_skills(category=key)
    if skills:
        raise HTTPException(
            409,
            f"Cannot remove category '{key}' — used by {len(skills)} skill(s)",
        )

    async with _get_lock("_global", "skills"):
        data = await load_global_entity(storage, "skills")
        custom = data.get("config", {}).get("custom_categories", [])
        data.setdefault("config", {})["custom_categories"] = [
            c for c in custom if c["key"] != key
        ]
        await save_global_entity(storage, "skills", data)

    return {"removed": key}


# ---------------------------------------------------------------------------
# Git sync endpoints (fixed paths, before /{name})
# ---------------------------------------------------------------------------

@router.get("/git/status")
async def git_status(git_svc=Depends(get_git_sync)):
    """Get git sync status for the skills repository."""
    if git_svc is None:
        return {
            "configured": False,
            "message": "FORGE_SKILLS_REPO_URL not set",
        }
    try:
        status = await git_svc.status()
        return {
            "configured": True,
            "initialized": status.initialized,
            "has_remote": status.has_remote,
            "branch": status.branch,
            "ahead": status.ahead,
            "behind": status.behind,
            "local_changes": status.local_changes,
            "last_commit": status.last_commit,
            "error": status.error,
        }
    except GitSyncError as e:
        return {"configured": True, "error": str(e)}


@router.post("/git/pull")
async def git_pull(
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
    git_svc=Depends(get_git_sync),
):
    """Pull latest skills from remote repository."""
    if git_svc is None:
        raise HTTPException(503, "Git sync not configured (FORGE_SKILLS_REPO_URL not set)")
    try:
        result = await git_svc.pull()
        await emit_event(request, _WS_NS, "skill.synced", {"action": "pull"})
        return {
            "success": result.success,
            "message": result.message,
            "files_changed": result.files_changed,
        }
    except (GitSyncError, GitSyncNotConfigured) as e:
        raise HTTPException(500, str(e))


@router.post("/git/push")
async def git_push(
    body: GitPushRequest,
    request: Request,
    git_svc=Depends(get_git_sync),
):
    """Push synced skills to remote repository."""
    if git_svc is None:
        raise HTTPException(503, "Git sync not configured (FORGE_SKILLS_REPO_URL not set)")
    try:
        result = await git_svc.push(body.message)
        await emit_event(request, _WS_NS, "skill.synced", {"action": "push"})
        return {
            "success": result.success,
            "message": result.message,
            "files_changed": result.files_changed,
        }
    except (GitSyncError, GitSyncNotConfigured) as e:
        raise HTTPException(500, str(e))


@router.post("/git/scan")
async def git_scan(
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Resync the skill index by scanning all directories."""
    entries = await svc.resync_index()
    return {"resynced": len(entries), "skills": [e["name"] for e in entries]}


@router.post("/git/init")
async def git_init(git_svc=Depends(get_git_sync)):
    """Initialize or clone the git repository for skills."""
    if git_svc is None:
        raise HTTPException(503, "Git sync not configured (FORGE_SKILLS_REPO_URL not set)")
    try:
        result = await git_svc.init_or_clone()
        return {
            "success": result.success,
            "message": result.message,
        }
    except (GitSyncError, GitSyncNotConfigured) as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------

_CONFIG_FILENAME = "skills_config.json"


def _get_config_path(storage) -> "Path":
    """Resolve skills_config.json path using storage base directory."""
    from pathlib import Path
    base = getattr(storage, "base_dir", None)
    if base:
        return Path(base) / "_global" / _CONFIG_FILENAME
    return Path("forge_output/_global") / _CONFIG_FILENAME


@router.get("/config")
async def get_skills_config(storage=Depends(get_storage)):
    """Get skills configuration (repo URL, etc.)."""
    import os

    config_path = _get_config_path(storage)
    persisted: dict = {}
    if config_path.exists():
        try:
            persisted = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "repo_url": persisted.get("repo_url", "") or os.environ.get("FORGE_SKILLS_REPO_URL", ""),
        "skills_dir": persisted.get("skills_dir", ""),
        "configured_via": "persisted" if persisted.get("repo_url") else (
            "env" if os.environ.get("FORGE_SKILLS_REPO_URL") else "none"
        ),
    }


@router.put("/config")
async def update_skills_config(
    body: SkillsConfigUpdate,
    request: Request,
    storage=Depends(get_storage),
):
    """Update skills configuration. Resets cached git sync service."""
    config_path = _get_config_path(storage)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if body.repo_url is not None:
        existing["repo_url"] = body.repo_url
    if body.skills_dir is not None:
        existing["skills_dir"] = body.skills_dir

    config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # Reset cached git_sync so next request picks up new config
    if hasattr(request.app.state, "git_sync"):
        request.app.state.git_sync = None

    return existing


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_skills(
    category: str | None = Query(None),
    status: str | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tag filter"),
    search: str | None = Query(None, description="Search name/description"),
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """List all skills with optional filters."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    skills = await svc.list_skills(
        category=category,
        status=status,
        tags=tag_list,
        search=search,
    )
    return {"skills": skills, "count": len(skills)}


@router.post("", status_code=201)
async def create_skill(
    body: SkillCreate,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Create a new skill."""
    # Validate name
    name_result = validate_skill_name(body.name)
    if not name_result.valid:
        raise HTTPException(422, f"Invalid name: {'; '.join(name_result.errors)}")
    if body.description:
        desc_result = validate_skill_description(body.description)
        if not desc_result.valid:
            raise HTTPException(422, f"Invalid description: {'; '.join(desc_result.errors)}")

    name = _slugify(body.name)
    try:
        skill = await svc.create_skill(name, {
            "description": body.description,
            "categories": body.categories,
            "tags": body.tags,
            "scopes": body.scopes,
            "evals_json": body.evals_json,
            "teslint_config": body.teslint_config,
            "created_by": body.created_by,
        })
    except ValueError as e:
        raise HTTPException(422, str(e))

    # If custom SKILL.md content provided, write it
    if body.skill_md_content:
        await svc.save_skill(name, content=body.skill_md_content)
        skill = await svc.get_skill(name)

    await emit_event(request, _WS_NS, "skill.created", {"name": name})
    return skill


# ---------------------------------------------------------------------------
# Parameterized endpoints (/{name} — AFTER all fixed paths)
# ---------------------------------------------------------------------------

@router.get("/{name}")
async def get_skill(
    name: str,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Get a single skill by name."""
    try:
        return await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")


@router.patch("/{name}")
async def update_skill(
    name: str,
    body: SkillUpdate,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Update a skill. Auto-parses frontmatter when content changes."""
    if body.description is not None:
        desc_result = validate_skill_description(body.description)
        if not desc_result.valid:
            raise HTTPException(422, f"Invalid description: {'; '.join(desc_result.errors)}")

    try:
        current = await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return current

    # Validate status transition
    if "status" in updates:
        new_status = updates["status"]
        current_status = current.get("status", "DRAFT")
        valid_transitions = {
            "DRAFT": {"DEPRECATED"},
            "ACTIVE": {"DEPRECATED"},
            "DEPRECATED": {"ARCHIVED", "ACTIVE"},
            "ARCHIVED": {"DRAFT"},
        }
        if new_status not in valid_transitions.get(current_status, set()):
            raise HTTPException(
                422,
                f"Cannot transition from {current_status} to {new_status}. "
                f"Valid: {valid_transitions.get(current_status, set())}",
            )

    # Split into config vs content updates
    content = updates.pop("skill_md_content", None)
    config_updates = {}
    config_keys = {
        "categories", "tags", "status", "scopes",
        "evals_json", "teslint_config", "sync", "description",
    }
    for key in list(updates.keys()):
        if key in config_keys:
            config_updates[key] = updates[key]

    try:
        await svc.save_skill(
            name,
            config=config_updates if config_updates else None,
            content=content,
        )
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    skill = await svc.get_skill(name)
    await emit_event(request, _WS_NS, "skill.updated", {"name": name})
    return skill


@router.delete("/{name}")
async def delete_skill(
    name: str,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
    storage=Depends(get_storage),
):
    """Delete a skill. Blocked if used by IN_PROGRESS tasks."""
    # Check usage
    in_use = await _check_skill_in_use(storage, name)
    if in_use:
        task_list = ", ".join(f"{u['project']}/{u['task_id']}" for u in in_use)
        raise HTTPException(
            409,
            f"Cannot delete skill '{name}' — used by IN_PROGRESS tasks: {task_list}",
        )

    try:
        await svc.delete_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    await emit_event(request, _WS_NS, "skill.deleted", {"name": name})
    return {"removed": name}


# ---------------------------------------------------------------------------
# Lint endpoint (per-skill)
# ---------------------------------------------------------------------------

@router.post("/{name}/lint")
async def lint_skill(
    name: str,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Run TESLint on a skill's SKILL.md content."""
    try:
        skill = await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    content = skill.get("skill_md_content")
    if not content:
        raise HTTPException(422, f"Skill '{name}' has no SKILL.md content to lint")

    result = await asyncio.to_thread(
        run_teslint, name, content, skill.get("teslint_config"),
    )

    findings = [
        {"rule_id": f.rule_id, "severity": f.severity, "message": f.message,
         "line": f.line, "column": f.column}
        for f in result.findings
    ]

    return {
        "skill_name": name,
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

@router.post("/{name}/promote")
async def promote_skill(
    name: str,
    body: PromoteRequest,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Promote DRAFT → ACTIVE with 3-gate validation."""
    try:
        skill = await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    if skill.get("status") != "DRAFT":
        raise HTTPException(422, f"Only DRAFT skills can be promoted. Current: {skill.get('status')}")

    content = skill.get("skill_md_content", "") or ""
    gate_results = []

    # Gate 0: agentskills.io compliance
    spec_result = validate_skill_structure(skill)
    gate0_passed = spec_result.valid
    gate0_detail = "agentskills.io compliant" if gate0_passed else "; ".join(spec_result.errors)
    if spec_result.warnings:
        gate0_detail += " (warnings: " + "; ".join(spec_result.warnings) + ")"
    gate_results.append({"gate": "agentskills-io", "passed": gate0_passed, "detail": gate0_detail, "required": True})

    fm = parse_frontmatter(content)
    gate1_passed = fm.valid and bool(skill.get("name")) and bool(skill.get("description"))
    gate_results.append({
        "gate": "frontmatter",
        "passed": gate1_passed,
        "required": True,
        "detail": (
            "Valid SKILL.md frontmatter with name and description"
            if gate1_passed
            else "Missing: " + ", ".join(fm.errors or ["name or description"])
        ),
    })

    # Advisory gates — failures don't block promotion
    evals = skill.get("evals_json", [])
    gate2_passed = len(evals) >= 1
    gate_results.append({
        "gate": "evals",
        "passed": gate2_passed,
        "required": False,
        "detail": f"{len(evals)} eval(s) defined" if gate2_passed else "No evals defined (optional)",
    })

    gate3_passed = False
    teslint_error_count = 0
    teslint_warning_count = 0
    if content.strip():
        lint_result = await asyncio.to_thread(
            run_teslint, name, content, skill.get("teslint_config"),
        )
        gate3_passed = lint_result.passed
        teslint_error_count = lint_result.error_count
        teslint_warning_count = lint_result.warning_count
        gate_results.append({
            "gate": "teslint",
            "passed": gate3_passed,
            "required": False,
            "detail": (
                f"TESLint passed ({teslint_warning_count} warnings)"
                if gate3_passed
                else lint_result.error_message or f"TESLint: {teslint_error_count} error(s)"
            ),
        })
    else:
        gate_results.append({"gate": "teslint", "passed": False, "required": False, "detail": "No content to lint"})

    # Only required gates block promotion (agentskills-io + frontmatter)
    required_passed = gate0_passed and gate1_passed
    all_passed = required_passed and gate2_passed and gate3_passed
    can_promote = required_passed or body.force

    if not can_promote:
        failed = [g for g in gate_results if not g["passed"] and g.get("required")]
        msg = "Promotion blocked: " + "; ".join(f"{g['gate']}: {g['detail']}" for g in failed)
        if not body.force:
            msg += ". Use force=true to override."
        raise HTTPException(422, msg)

    now = _now_iso()
    promotion_history = skill.get("promotion_history", [])
    promotion_history.append({
        "promoted_at": now,
        "error_count": teslint_error_count,
        "warning_count": teslint_warning_count,
        "forced": body.force and not all_passed,
        "gates": gate_results,
    })

    await svc.save_skill(name, config={
        "status": "ACTIVE",
        "promoted_with_warnings": not all_passed,
        "promotion_history": promotion_history,
    })

    await emit_event(request, _WS_NS, "skill.promoted", {"name": name})
    return {
        "name": name,
        "status": "ACTIVE",
        "promoted_with_warnings": not all_passed,
        "gates": gate_results,
    }


# ---------------------------------------------------------------------------
# Usage / validate / export (per-skill)
# ---------------------------------------------------------------------------

@router.get("/{name}/usage")
async def skill_usage(
    name: str,
    svc: SkillStorageService = Depends(get_skill_storage),
    storage=Depends(get_storage),
):
    """Get tasks referencing this skill across all projects."""
    try:
        await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    from app.routers._helpers import load_entity
    usage = []
    try:
        projects = await asyncio.to_thread(storage.list_projects)
        for proj in projects:
            try:
                tracker = await load_entity(storage, proj, "tracker")
                for task in tracker.get("tasks", []):
                    if task.get("skill") and name in task["skill"]:
                        usage.append({
                            "project": proj,
                            "task_id": task.get("id"),
                            "task_name": task.get("name"),
                            "status": task.get("status"),
                        })
            except Exception:
                continue
    except Exception:
        pass

    return {"name": name, "usage": usage, "count": len(usage)}


@router.post("/{name}/validate")
async def validate_skill(
    name: str,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Run agentskills.io compliance validation on a skill."""
    try:
        skill = await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    result = validate_skill_structure(skill)
    return {"name": name, **result.to_dict()}


@router.get("/{name}/export")
async def export_skill(
    name: str,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Export a skill as a downloadable .md file."""
    try:
        skill = await svc.get_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")

    content = skill.get("skill_md_content") or ""
    if not content:
        content = generate_frontmatter(name=name, description=skill.get("description", ""))
        content += f"\n\n# {name}\n"

    filename = f"{name}.SKILL.md"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Skill files CRUD (real files on disk)
# ---------------------------------------------------------------------------

@router.get("/{name}/files")
async def list_skill_files(
    name: str,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """List all bundled files for a skill."""
    try:
        files = await svc.list_files(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")
    return {"name": name, "files": files, "count": len(files)}


@router.get("/{name}/files/{file_path:path}")
async def get_skill_file(
    name: str,
    file_path: str,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Get a single file's content."""
    try:
        content = await svc.get_file(name, file_path)
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {file_path}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"name": name, "path": file_path, "content": content}


@router.put("/{name}/files/{file_path:path}")
async def save_skill_file(
    name: str,
    file_path: str,
    body: dict,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Create or update a single file."""
    content = body.get("content", "")
    try:
        await svc.save_file(name, file_path, content)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill '{name}' not found")
    except ValueError as e:
        raise HTTPException(400, str(e))

    await emit_event(request, _WS_NS, "skill.updated", {"name": name})
    return {"name": name, "path": file_path, "saved": True}


@router.delete("/{name}/files/{file_path:path}")
async def delete_skill_file(
    name: str,
    file_path: str,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Delete a single file from a skill."""
    try:
        await svc.delete_file(name, file_path)
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {file_path}")
    except ValueError as e:
        raise HTTPException(400, str(e))

    await emit_event(request, _WS_NS, "skill.updated", {"name": name})
    return {"name": name, "deleted": file_path}


@router.post("/{name}/files/move")
async def move_skill_file(
    name: str,
    body: FileMoveRequest,
    request: Request,
    svc: SkillStorageService = Depends(get_skill_storage),
):
    """Move/rename a file within a skill."""
    try:
        await svc.move_file(name, body.old_path, body.new_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    await emit_event(request, _WS_NS, "skill.updated", {"name": name})
    return {"name": name, "moved": body.old_path, "to": body.new_path}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _check_skill_in_use(storage, skill_name: str) -> list[dict]:
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
                    if task.get("skill") and skill_name in task["skill"]:
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

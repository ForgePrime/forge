"""Contracts REST API — expose Forge contract specs as structured JSON."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from core.contracts import render_contract

# ---------------------------------------------------------------------------
# Contract registry — lazy-loaded to avoid circular imports
# ---------------------------------------------------------------------------

_registry: dict[str, dict[str, dict]] | None = None


def _load_registry() -> dict[str, dict[str, dict]]:
    """Load all CONTRACTS dicts from Forge core modules."""
    global _registry
    if _registry is not None:
        return _registry

    from core.objectives import CONTRACTS as objectives_c
    from core.ideas import CONTRACTS as ideas_c
    from core.pipeline import CONTRACTS as pipeline_c
    from core.decisions import CONTRACTS as decisions_c
    from core.knowledge import CONTRACTS as knowledge_c
    from core.guidelines import CONTRACTS as guidelines_c
    from core.research import CONTRACTS as research_c
    from core.lessons import CONTRACTS as lessons_c
    from core.ac_templates import CONTRACTS as ac_templates_c
    from core.changes import CONTRACTS as changes_c
    from core.gates import CONTRACTS as gates_c

    _registry = {
        "objectives": objectives_c,
        "ideas": ideas_c,
        "pipeline": pipeline_c,
        "decisions": decisions_c,
        "knowledge": knowledge_c,
        "guidelines": guidelines_c,
        "research": research_c,
        "lessons": lessons_c,
        "ac_templates": ac_templates_c,
        "changes": changes_c,
        "gates": gates_c,
    }
    return _registry


def _type_label(t: Any) -> str:
    """Convert Python type to JSON type string."""
    labels = {
        str: "string", int: "integer", float: "number",
        bool: "boolean", list: "array", dict: "object",
    }
    return labels.get(t, "string")


def _spec_to_json(module: str, action: str, spec: dict) -> dict:
    """Convert a contract spec dict to structured JSON response."""
    types_map = spec.get("types", {})
    enums = spec.get("enums", {})

    fields = []
    for field in spec.get("required", []):
        entry: dict[str, Any] = {
            "name": field,
            "type": _type_label(types_map.get(field, str)),
            "required": True,
        }
        if field in enums:
            entry["values"] = sorted(str(v) for v in enums[field] if v is not None)
            if None in enums[field]:
                entry["nullable"] = True
        fields.append(entry)

    for field in spec.get("optional", []):
        entry = {
            "name": field,
            "type": _type_label(types_map.get(field, str)),
            "required": False,
        }
        if field in enums:
            entry["values"] = sorted(str(v) for v in enums[field] if v is not None)
            if None in enums[field]:
                entry["nullable"] = True
        fields.append(entry)

    result: dict[str, Any] = {
        "module": module,
        "action": action,
        "fields": fields,
        "invariants": spec.get("invariant_texts", []),
    }

    if spec.get("example"):
        result["example"] = spec["example"]

    if spec.get("notes"):
        result["notes"] = spec["notes"]

    # Also include the rendered markdown for LLM consumption
    result["markdown"] = render_contract(f"{module}/{action}", spec)

    return result


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("")
async def list_contracts() -> dict[str, Any]:
    """List all available contract modules and their actions."""
    registry = _load_registry()
    modules = []
    for module_name, actions_dict in sorted(registry.items()):
        modules.append({
            "module": module_name,
            "actions": sorted(actions_dict.keys()),
        })
    return {"modules": modules, "total": sum(len(m["actions"]) for m in modules)}


@router.get("/{module}/{action}")
async def get_contract(module: str, action: str) -> dict[str, Any]:
    """Get structured contract for a specific module and action."""
    registry = _load_registry()
    if module not in registry:
        raise HTTPException(404, f"Unknown module: {module}")
    actions_dict = registry[module]
    if action not in actions_dict:
        raise HTTPException(404, f"Unknown action '{action}' for module '{module}'. Available: {sorted(actions_dict.keys())}")
    spec = actions_dict[action]
    return _spec_to_json(module, action, spec)

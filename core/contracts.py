"""
Contract utilities — single source of truth for LLM output validation.

Carried forward from Skill_v1 (contract_utils.py) with minimal changes.
This module is the PROVEN foundation: one Python dict drives both
the Markdown prompt (what LLM sees) and the validation (what Python enforces).

Each contract is a Python dict with:
  required         — list of required field names
  optional         — list of optional field names
  enums            — dict mapping field name -> set of valid values
  types            — dict mapping field name -> expected Python type (default: str)
  invariants       — list of (check_fn, error_message) tuples for per-item validation
  array_invariants — list of (check_fn, error_message) tuples for whole-array validation
  invariant_texts  — list of human-readable invariant descriptions (rendered for LLM)
  example          — example JSON (list of dicts) for rendering
  notes            — additional Markdown text appended to rendered contract

Usage:
    from core.contracts import render_contract, validate_contract

    spec = { "required": [...], "enums": {...}, ... }
    md = render_contract("save-change", spec)      # -> Markdown for LLM
    errors = validate_contract(spec, data_list)     # -> list of error strings
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: dict):
    """Write JSON atomically: write to temp file, then os.replace().

    Prevents corruption from partial writes (crash, kill, power loss).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def render_contract(name: str, spec: dict) -> str:
    """Render a contract spec as Markdown for LLM consumption.

    Output has 4 sections:
    1. Field table (required/optional, types, enum values)
    2. Invariants (from invariant_texts)
    3. Output format instruction (always: raw JSON array, no prose)
    4. Example (from example list)
    """
    lines = []
    lines.append(f"## {name} Contract")
    lines.append("")
    lines.append("Input: JSON **array** of objects.")
    lines.append("")

    # Field table
    lines.append("| Field | Type | Required | Values |")
    lines.append("|-------|------|----------|--------|")

    types_map = spec.get("types", {})

    for field in spec.get("required", []):
        type_label = _type_label(types_map.get(field, str))
        values = _enum_values(spec, field)
        lines.append(f"| {field} | {type_label} | YES | {values} |")

    for field in spec.get("optional", []):
        type_label = _type_label(types_map.get(field, str))
        values = _enum_values(spec, field)
        lines.append(f"| {field} | {type_label} | no | {values} |")

    # Invariants
    inv_texts = spec.get("invariant_texts", [])
    if inv_texts:
        lines.append("")
        lines.append("### Invariants")
        for inv in inv_texts:
            lines.append(f"- {inv}")

    # Output format (always)
    lines.append("")
    lines.append("### Output Format")
    lines.append("- Output MUST be a raw JSON array only.")
    lines.append("- Do NOT wrap in ```json``` code blocks.")
    lines.append("- No markdown. No prose. No explanation.")

    # Notes
    notes = spec.get("notes", "")
    if notes:
        lines.append("")
        lines.append(notes)

    # Example
    example = spec.get("example")
    if example:
        lines.append("")
        lines.append("### Example")
        lines.append("```json")
        lines.append(json.dumps(example, indent=2, ensure_ascii=False))
        lines.append("```")

    return "\n".join(lines)


def validate_contract(spec: dict, data: Any) -> list:
    """Validate data against contract spec.

    Returns list of error strings (empty = valid).
    """
    errors = []

    if not isinstance(data, list):
        return ["Input must be a JSON array"]

    required = spec.get("required", [])
    enums = spec.get("enums", {})
    types_map = spec.get("types", {})
    invariants = spec.get("invariants", [])

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"[{i}]: must be an object")
            continue

        # Required fields
        for field in required:
            if field not in item:
                errors.append(f"[{i}]: missing required field '{field}'")
            elif item[field] is None and field in enums:
                if None not in enums[field]:
                    errors.append(f"[{i}]: '{field}' cannot be null")

        # Enum validation
        for field, valid_values in enums.items():
            if field in item and item[field] is not None:
                if item[field] not in valid_values:
                    errors.append(
                        f"[{i}]: invalid {field}='{item[field]}' "
                        f"(must be: {', '.join(str(v) for v in sorted(valid_values, key=str))})"
                    )

        # Type validation (only for non-str types)
        for field, expected_type in types_map.items():
            if field in item and item[field] is not None:
                if not isinstance(item[field], expected_type):
                    errors.append(
                        f"[{i}]: '{field}' must be {expected_type.__name__}, "
                        f"got {type(item[field]).__name__}"
                    )

        # Per-item invariants
        for check_fn, err_msg in invariants:
            try:
                if not check_fn(item, i):
                    errors.append(f"[{i}]: {err_msg}")
            except Exception as e:
                errors.append(f"[{i}]: invariant check failed: {e}")

    # Whole-array invariants
    for check_fn, err_msg in spec.get("array_invariants", []):
        try:
            if not check_fn(data):
                errors.append(err_msg)
        except Exception as e:
            errors.append(f"Array invariant check failed: {e}")

    return errors


# -- Internal helpers --

def _type_label(t) -> str:
    """Convert Python type to display label."""
    labels = {
        str: "string", int: "int", float: "number",
        bool: "boolean", list: "array", dict: "object",
    }
    return labels.get(t, "string")


def _enum_values(spec: dict, field: str) -> str:
    """Format enum values for display, or empty."""
    enums = spec.get("enums", {})
    if field in enums:
        vals = sorted(str(v) for v in enums[field] if v is not None)
        null_note = ", null" if None in enums[field] else ""
        return ", ".join(vals) + null_note
    return ""

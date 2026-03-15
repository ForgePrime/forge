"""YAML frontmatter parser for SKILL.md files.

Parses the --- delimited YAML block at the start of markdown content,
extracts structured metadata, and supports round-trip generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FrontmatterResult:
    """Result of parsing YAML frontmatter from markdown."""
    name: str | None = None
    description: str | None = None
    version: str | None = None
    skill_id: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    contract_refs: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    body: str = ""
    valid: bool = False
    errors: list[str] = field(default_factory=list)


def parse_frontmatter(content: str) -> FrontmatterResult:
    """Parse YAML frontmatter from SKILL.md content.

    Expects content starting with '---', a YAML block, then '---',
    followed by the markdown body.

    Returns FrontmatterResult with extracted fields and the body.
    """
    result = FrontmatterResult()

    if not content or not content.strip():
        result.errors.append("Empty content")
        result.body = content or ""
        return result

    stripped = content.strip()
    if not stripped.startswith("---"):
        result.errors.append("Missing YAML frontmatter (must start with ---)")
        result.body = content
        return result

    # Find closing ---
    # Skip the first line (opening ---), find next ---
    lines = content.split("\n")
    opening = -1
    closing = -1

    for i, line in enumerate(lines):
        if line.strip() == "---":
            if opening == -1:
                opening = i
            else:
                closing = i
                break

    if closing == -1:
        result.errors.append("Unclosed frontmatter (missing closing ---)")
        result.body = content
        return result

    # Extract YAML block and body
    yaml_lines = lines[opening + 1:closing]
    body_lines = lines[closing + 1:]
    result.body = "\n".join(body_lines)

    # Parse YAML manually (simple key-value, no nested objects needed)
    raw = _parse_simple_yaml(yaml_lines)
    result.raw = raw

    # Extract known fields
    result.name = _str_or_none(raw.get("name"))
    result.description = _str_or_none(raw.get("description"))
    result.version = _str_or_none(raw.get("version"))
    result.skill_id = _str_or_none(raw.get("id"))

    # allowed-tools can be a YAML list
    tools = raw.get("allowed-tools", raw.get("allowed_tools"))
    if isinstance(tools, list):
        result.allowed_tools = [str(t).strip() for t in tools]
    elif isinstance(tools, str):
        # Parse inline list: [Read, Glob, Grep]
        result.allowed_tools = _parse_inline_list(tools)

    # entity_types — which entity types this skill works with
    et = raw.get("entity-types", raw.get("entity_types"))
    if isinstance(et, list):
        result.entity_types = [str(t).strip() for t in et]
    elif isinstance(et, str):
        result.entity_types = _parse_inline_list(et)

    # contract_refs — which contracts this skill references
    cr = raw.get("contract-refs", raw.get("contract_refs"))
    if isinstance(cr, list):
        result.contract_refs = [str(t).strip() for t in cr]
    elif isinstance(cr, str):
        result.contract_refs = _parse_inline_list(cr)

    # Validate required fields
    if not result.name:
        result.errors.append("Missing required field: name")
    if not result.description:
        result.errors.append("Missing required field: description")

    result.valid = len(result.errors) == 0
    return result


def generate_frontmatter(
    name: str,
    description: str,
    version: str = "1.0.0",
    skill_id: str | None = None,
    allowed_tools: list[str] | None = None,
) -> str:
    """Generate YAML frontmatter block for a SKILL.md file."""
    lines = ["---"]
    lines.append(f"name: {name}")

    if skill_id:
        lines.append(f"id: {skill_id}")

    lines.append(f"version: \"{version}\"")

    # Use quoted string for short descriptions, > block for long ones
    if "\n" in description or len(description) > 80:
        lines.append("description: >")
        for desc_line in description.split("\n"):
            lines.append(f"  {desc_line.strip()}")
    else:
        lines.append(f"description: \"{description}\"")

    if allowed_tools:
        tools_str = ", ".join(allowed_tools)
        lines.append(f"allowed-tools: [{tools_str}]")

    lines.append("---")
    return "\n".join(lines)


def merge_frontmatter_to_metadata(content: str) -> dict:
    """Parse frontmatter and return metadata dict for skill record update.

    Returns dict with only the fields that were found in frontmatter,
    ready to merge into a skill record.
    """
    result = parse_frontmatter(content)
    meta: dict = {}

    if result.name:
        meta["name"] = result.name
    if result.description:
        meta["description"] = result.description
    if result.version:
        meta["version"] = result.version
    if result.allowed_tools:
        meta["allowed_tools"] = result.allowed_tools
    if result.entity_types:
        meta["entity_types"] = result.entity_types
    if result.contract_refs:
        meta["contract_refs"] = result.contract_refs

    return meta


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _str_or_none(val) -> str | None:
    """Convert value to string or None."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _parse_inline_list(s: str) -> list[str]:
    """Parse YAML inline list: [Read, Glob, Grep] → ['Read', 'Glob', 'Grep']."""
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return [item.strip().strip("\"'") for item in s.split(",") if item.strip()]


def _parse_simple_yaml(lines: list[str]) -> dict:
    """Parse simple YAML key-value pairs (no nested objects).

    Handles:
    - key: value
    - key: "quoted value"
    - key: [inline, list]
    - key: >
        multi-line value
    """
    result: dict = {}
    current_key: str | None = None
    current_multiline: list[str] = []
    is_multiline = False

    for line in lines:
        # Skip comments and empty lines (unless in multiline mode)
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if is_multiline:
                current_multiline.append("")
            continue

        # Check if this is a continuation of a multiline value
        if is_multiline:
            if line.startswith("  ") or line.startswith("\t"):
                current_multiline.append(stripped)
                continue
            else:
                # End of multiline — save and continue parsing
                if current_key:
                    result[current_key] = " ".join(
                        p for p in current_multiline if p
                    )
                is_multiline = False
                current_key = None
                current_multiline = []

        # Parse key: value
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_\-]*)\s*:\s*(.*)", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()

            if value == ">" or value == "|":
                # Start multiline
                current_key = key
                current_multiline = []
                is_multiline = True
            elif value.startswith("["):
                # Inline list
                result[key] = _parse_inline_list(value)
            elif value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                result[key] = value[1:-1]
            else:
                result[key] = value

    # Handle trailing multiline
    if is_multiline and current_key:
        result[current_key] = " ".join(p for p in current_multiline if p)

    return result

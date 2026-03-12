"""Built-in skill linter — validates SKILL.md quality and structure.

Replaces the external teslint subprocess with a direct Python implementation.
Checks frontmatter, markdown structure, instruction quality, and best practices.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TESLintFinding:
    """A single lint finding."""
    rule_id: str
    severity: str  # "error", "warning", "info"
    message: str
    line: int | None = None
    column: int | None = None


@dataclass
class TESLintResult:
    """Result of running lint on a skill."""
    success: bool
    findings: list[TESLintFinding] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    raw_output: str = ""
    error_message: str | None = None

    @property
    def passed(self) -> bool:
        return self.success and self.error_count == 0


# ---------------------------------------------------------------------------
# Known tools (agentskills.io compatible)
# ---------------------------------------------------------------------------

_KNOWN_TOOLS = {
    "Read", "Write", "Edit", "Glob", "Grep", "Bash",
    "WebSearch", "WebFetch", "Task", "NotebookEdit",
}

# ---------------------------------------------------------------------------
# Frontmatter parser (lightweight)
# ---------------------------------------------------------------------------

def _parse_fm(content: str) -> tuple[dict[str, str], str, int]:
    """Parse YAML frontmatter from SKILL.md.

    Returns (fields_dict, body_text, fm_end_line).
    """
    stripped = content.strip()
    if not stripped.startswith("---"):
        return {}, content, 0

    # Find closing ---
    lines = content.split("\n")
    fm_end = -1
    for i, line in enumerate(lines):
        if i == 0:
            continue
        if line.strip() == "---":
            fm_end = i
            break

    if fm_end == -1:
        return {}, content, 0

    fields: dict[str, str] = {}
    for line in lines[1:fm_end]:
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip().strip('"').strip("'")

    body = "\n".join(lines[fm_end + 1:])
    return fields, body, fm_end + 1


# ---------------------------------------------------------------------------
# Lint rules
# ---------------------------------------------------------------------------

def _check_frontmatter(content: str, findings: list[TESLintFinding]) -> dict[str, str]:
    """Check frontmatter structure and required fields."""
    stripped = content.strip()

    if not stripped.startswith("---"):
        findings.append(TESLintFinding(
            rule_id="fm-missing",
            severity="error",
            message="SKILL.md must start with YAML frontmatter (---)",
            line=1,
        ))
        return {}

    fields, body, fm_end = _parse_fm(content)

    if fm_end == 0:
        findings.append(TESLintFinding(
            rule_id="fm-unclosed",
            severity="error",
            message="Frontmatter is not closed (missing closing ---)",
            line=1,
        ))
        return {}

    if not fields:
        findings.append(TESLintFinding(
            rule_id="fm-empty",
            severity="error",
            message="Frontmatter is empty — add at least name and description",
            line=1,
        ))
        return {}

    # Required fields
    if "name" not in fields:
        findings.append(TESLintFinding(
            rule_id="fm-name-missing",
            severity="error",
            message="Frontmatter missing required field: name",
            line=2,
        ))
    elif not fields["name"]:
        findings.append(TESLintFinding(
            rule_id="fm-name-empty",
            severity="error",
            message="Frontmatter 'name' field is empty",
            line=2,
        ))

    if "description" not in fields:
        findings.append(TESLintFinding(
            rule_id="fm-desc-missing",
            severity="error",
            message="Frontmatter missing required field: description",
            line=3,
        ))
    elif not fields["description"]:
        findings.append(TESLintFinding(
            rule_id="fm-desc-empty",
            severity="error",
            message="Frontmatter 'description' field is empty",
            line=3,
        ))
    elif len(fields["description"]) < 10:
        findings.append(TESLintFinding(
            rule_id="fm-desc-short",
            severity="warning",
            message=f"Description is very short ({len(fields['description'])} chars) — aim for at least 10 characters",
            line=3,
        ))

    # Recommended fields
    if "version" not in fields:
        findings.append(TESLintFinding(
            rule_id="fm-version-missing",
            severity="info",
            message="Consider adding a 'version' field to frontmatter (e.g., version: 1.0.0)",
        ))

    # Check allowed-tools
    tools_str = fields.get("allowed-tools", fields.get("allowed_tools", ""))
    if tools_str:
        tools = [t.strip() for t in tools_str.replace(",", " ").split() if t.strip()]
        for tool in tools:
            if tool not in _KNOWN_TOOLS:
                findings.append(TESLintFinding(
                    rule_id="fm-unknown-tool",
                    severity="warning",
                    message=f"Unknown tool in allowed-tools: '{tool}'. Known: {', '.join(sorted(_KNOWN_TOOLS))}",
                ))

    return fields


def _check_body(content: str, findings: list[TESLintFinding]) -> None:
    """Check markdown body quality."""
    _, body, fm_end = _parse_fm(content)
    body_stripped = body.strip()

    if not body_stripped:
        findings.append(TESLintFinding(
            rule_id="body-empty",
            severity="error",
            message="SKILL.md has no content after frontmatter — add instructions for the AI",
            line=fm_end + 1,
        ))
        return

    lines = body.split("\n")
    body_line_count = len(lines)

    # Check minimum instruction length
    non_empty_lines = [l for l in lines if l.strip()]
    if len(non_empty_lines) < 3:
        findings.append(TESLintFinding(
            rule_id="body-too-short",
            severity="warning",
            message=f"Skill instructions are very short ({len(non_empty_lines)} lines) — provide more context for the AI",
            line=fm_end + 1,
        ))

    # Check for headings (structure)
    headings = [l for l in lines if l.strip().startswith("#")]
    if len(non_empty_lines) > 15 and not headings:
        findings.append(TESLintFinding(
            rule_id="body-no-headings",
            severity="info",
            message="Long skill instructions without markdown headings — consider adding ## sections for clarity",
            line=fm_end + 1,
        ))

    # Check for excessively long lines
    for i, line in enumerate(lines):
        if len(line) > 500:
            findings.append(TESLintFinding(
                rule_id="line-too-long",
                severity="info",
                message=f"Line is very long ({len(line)} chars) — consider wrapping for readability",
                line=fm_end + 1 + i,
            ))
            break  # Only report first one

    # Total length check
    if body_line_count > 500:
        findings.append(TESLintFinding(
            rule_id="body-too-long",
            severity="warning",
            message=f"SKILL.md body is {body_line_count} lines (recommended max 500). "
                    "Consider moving reference material to scripts/ or references/",
            line=fm_end + 1,
        ))

    # Check for TODO/FIXME/HACK markers
    for i, line in enumerate(lines):
        for marker in ("TODO", "FIXME", "HACK", "XXX"):
            if marker in line:
                findings.append(TESLintFinding(
                    rule_id="body-todo-marker",
                    severity="warning",
                    message=f"Found '{marker}' marker — resolve before promoting to ACTIVE",
                    line=fm_end + 1 + i,
                ))
                break


def _check_structure(content: str, skill_name: str, findings: list[TESLintFinding]) -> None:
    """Check skill naming and overall structure."""
    # Skill name validation
    name_re = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
    if not name_re.match(skill_name):
        findings.append(TESLintFinding(
            rule_id="name-invalid",
            severity="error",
            message=f"Skill name '{skill_name}' is not valid. Use lowercase letters, digits, and hyphens. "
                    "Must start with a letter, no consecutive/trailing hyphens.",
        ))

    if len(skill_name) > 64:
        findings.append(TESLintFinding(
            rule_id="name-too-long",
            severity="error",
            message=f"Skill name is too long ({len(skill_name)} chars, max 64)",
        ))

    # Total content size check
    content_size = len(content.encode("utf-8"))
    if content_size > 100_000:
        findings.append(TESLintFinding(
            rule_id="content-too-large",
            severity="warning",
            message=f"SKILL.md is {content_size // 1024}KB — consider splitting into smaller files",
        ))


# ---------------------------------------------------------------------------
# Main entry point (same signature as before)
# ---------------------------------------------------------------------------

def run_teslint(
    skill_name: str,
    skill_md_content: str,
    teslint_config: dict | None = None,
    timeout_seconds: int = 10,
) -> TESLintResult:
    """Run built-in linter on a SKILL.md content string.

    Args:
        skill_name: Name of the skill (directory slug).
        skill_md_content: Full content of the SKILL.md file.
        teslint_config: Reserved for future configuration.
        timeout_seconds: Unused (kept for API compatibility).

    Returns:
        TESLintResult with findings, counts, and success flag.
    """
    if not skill_md_content:
        return TESLintResult(success=True)

    findings: list[TESLintFinding] = []

    try:
        _check_frontmatter(skill_md_content, findings)
        _check_body(skill_md_content, findings)
        _check_structure(skill_md_content, skill_name, findings)
    except Exception as e:
        return TESLintResult(
            success=False,
            error_message=f"Lint error: {e}",
        )

    error_count = sum(1 for f in findings if f.severity == "error")
    warning_count = sum(1 for f in findings if f.severity == "warning")
    info_count = sum(1 for f in findings if f.severity == "info")

    return TESLintResult(
        success=True,
        findings=findings,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
    )


def check_teslint_available() -> dict:
    """Check if linter is available (always true — built-in)."""
    return {"available": True, "version": "built-in 1.0"}

"""TESLint subprocess service — lint SKILL.md files.

Creates a temporary directory with the expected .claude/skills/{name}/SKILL.md
structure, runs `python -m teslint --format json`, parses output, cleans up.

Per ADR-3 (D-023): TESLint as subprocess with temp dir. See also D-020 (path structure risk).
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TESLintFinding:
    """A single TESLint finding."""
    rule_id: str
    severity: str  # "error", "warning", "info"
    message: str
    line: int | None = None
    column: int | None = None


@dataclass
class TESLintResult:
    """Result of running TESLint on a skill."""
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


def run_teslint(
    skill_name: str,
    skill_md_content: str,
    teslint_config: dict | None = None,
    timeout_seconds: int = 10,
) -> TESLintResult:
    """Run TESLint on a SKILL.md content string.

    Creates a temp directory with the expected structure:
        /tmp/teslint-{uuid}/.claude/skills/{skill_name}/SKILL.md

    Args:
        skill_name: Name of the skill (used for directory structure).
        skill_md_content: Full content of the SKILL.md file.
        teslint_config: Optional TESLint config override (.teslintrc.json).
        timeout_seconds: Max seconds to wait for TESLint (default 10).

    Returns:
        TESLintResult with findings, counts, and success flag.
    """
    # Guard: no content to lint
    if not skill_md_content:
        return TESLintResult(success=True, raw_output="(no content to lint)")

    # Sanitize skill_name — prevent path traversal and log injection
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", skill_name)
    if not safe_name:
        safe_name = "unnamed"

    tmp_dir = None
    try:
        # Create temp dir with .claude/skills/{name}/SKILL.md structure
        tmp_dir = tempfile.mkdtemp(prefix="teslint-")
        skill_dir = Path(tmp_dir) / ".claude" / "skills" / safe_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_md_path = skill_dir / "SKILL.md"
        skill_md_path.write_text(skill_md_content, encoding="utf-8")

        # Optional: write TESLint config
        if teslint_config:
            config_path = Path(tmp_dir) / ".teslintrc.json"
            config_path.write_text(json.dumps(teslint_config), encoding="utf-8")

        # Run TESLint
        try:
            result = subprocess.run(
                ["python", "-m", "teslint", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=tmp_dir,
            )
        except FileNotFoundError:
            logger.warning("TESLint not installed (python -m teslint not found)")
            return TESLintResult(
                success=False,
                error_message="TESLint is not installed. Install with: pip install teslint",
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"TESLint timed out after {timeout_seconds}s for skill '{safe_name}'")
            return TESLintResult(
                success=False,
                error_message=f"TESLint timed out after {timeout_seconds} seconds",
            )

        # Check for "module not found" (teslint package not installed)
        if result.returncode != 0 and "No module named" in (result.stderr or ""):
            logger.warning("TESLint package not installed (python -m teslint module not found)")
            return TESLintResult(
                success=False,
                error_message="TESLint is not installed. Install with: pip install teslint",
            )

        raw_output = result.stdout or ""

        # Parse JSON output
        try:
            parsed = json.loads(raw_output)
        except (json.JSONDecodeError, ValueError):
            # TESLint may output non-JSON (e.g., error messages)
            if result.returncode != 0:
                return TESLintResult(
                    success=False,
                    raw_output=raw_output,
                    error_message=result.stderr or f"TESLint exited with code {result.returncode}",
                )
            # If exit code 0 but no JSON, assume no findings
            return TESLintResult(success=True, raw_output=raw_output)

        # Extract findings
        findings = []
        for item in (parsed if isinstance(parsed, list) else parsed.get("findings", [])):
            findings.append(TESLintFinding(
                rule_id=item.get("rule_id", item.get("rule", "unknown")),
                severity=item.get("severity", "warning"),
                message=item.get("message", ""),
                line=item.get("line"),
                column=item.get("column"),
            ))

        error_count = sum(1 for f in findings if f.severity == "error")
        warning_count = sum(1 for f in findings if f.severity == "warning")
        info_count = sum(1 for f in findings if f.severity == "info")

        # Warn if 0 findings on non-empty content (possible false pass)
        if len(findings) == 0 and len(skill_md_content.strip()) > 50:
            logger.info(
                f"TESLint returned 0 findings for skill '{safe_name}' "
                f"({len(skill_md_content)} chars) — verify scanner found the file"
            )

        return TESLintResult(
            success=True,
            findings=findings,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            raw_output=raw_output,
        )

    except Exception as e:
        logger.exception(f"Unexpected error running TESLint for skill '{safe_name}'")
        return TESLintResult(
            success=False,
            error_message=f"Unexpected error: {str(e)}",
        )
    finally:
        # Cleanup temp dir
        if tmp_dir:
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                logger.warning(f"Failed to clean up temp dir: {tmp_dir}")


def check_teslint_available() -> dict:
    """Check if TESLint CLI is available (python -m teslint)."""
    try:
        result = subprocess.run(
            ["python", "-m", "teslint", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return {"available": True, "version": result.stdout.strip()}
        if "No module named" in (result.stderr or ""):
            return {"available": False, "reason": "TESLint package not installed"}
        return {
            "available": False,
            "reason": result.stderr.strip() or f"Exit code {result.returncode}",
        }
    except FileNotFoundError:
        return {"available": False, "reason": "Python not found"}
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "Timeout checking TESLint"}

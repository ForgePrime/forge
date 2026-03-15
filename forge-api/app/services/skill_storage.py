"""File-based skill storage service.

Operates on per-skill directories under _global/skills/{name}/ instead of
a monolithic skills.json.  Each skill directory contains:
  - _config.json   — Forge metadata (categories, tags, status, sync flag, etc.)
  - SKILL.md       — skill content with YAML frontmatter (name, description, version)
  - scripts/       — executable scripts (optional)
  - references/    — reference documents (optional)
  - assets/        — images, data files (optional)

Source of truth split:
  - SKILL.md frontmatter → name, description, version, allowed-tools
  - _config.json → categories, tags, status, scopes, evals, sync, promotion_history, …
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.services.frontmatter import generate_frontmatter, parse_frontmatter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]
ALLOWED_FILE_PREFIXES = ("scripts/", "references/", "assets/")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CONFIG_FILE = "_config.json"
_SKILL_MD = "SKILL.md"
_INDEX_FILE = "_index.json"


def _default_config() -> dict:
    """Return a default _config.json skeleton."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "categories": [],
        "tags": [],
        "status": "DRAFT",
        "scopes": [],
        "evals_json": [],
        "teslint_config": None,
        "sync": False,
        "promoted_with_warnings": False,
        "promotion_history": [],
        "usage_count": 0,
        "created_by": None,
        "created_at": now,
        "updated_at": now,
    }


def _is_valid_slug(name: str) -> bool:
    """Check that *name* is a valid lowercase-hyphen slug."""
    return bool(_SLUG_RE.match(name))


def _classify_file_type(path: str) -> str:
    """Determine file_type from path prefix."""
    for prefix in ALLOWED_FILE_PREFIXES:
        if path.startswith(prefix):
            return prefix.rstrip("/")
    return "unknown"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SkillStorageService:
    """CRUD service for file-based skill storage."""

    def __init__(self, skills_dir: Path | str | None = None):
        if skills_dir is None:
            skills_dir = Path("forge_output/_global/skills")
        self.skills_dir = Path(skills_dir)
        self._locks: dict[str, asyncio.Lock] = {}
        self._index_lock = asyncio.Lock()

    # -- helpers ----------------------------------------------------------

    def _ensure_dir(self) -> None:
        """Create skills_dir if it doesn't exist."""
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def _skill_dir(self, name: str) -> Path:
        return self.skills_dir / name

    def _lock(self, name: str) -> asyncio.Lock:
        return self._locks.setdefault(name, asyncio.Lock())

    # -- index operations -------------------------------------------------

    def _index_path(self) -> Path:
        return self.skills_dir / _INDEX_FILE

    def _read_index(self) -> list[dict]:
        """Read _index.json.  Returns [] if missing or corrupt."""
        path = self._index_path()
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _write_index(self, entries: list[dict]) -> None:
        """Write _index.json atomically."""
        self._ensure_dir()
        path = self._index_path()
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp), str(path))

    def _build_index_entry(self, name: str) -> dict | None:
        """Build one index entry by reading skill directory on disk."""
        skill_dir = self._skill_dir(name)
        if not skill_dir.is_dir():
            return None
        config = self._read_config(skill_dir)
        md_content = self._read_skill_md(skill_dir)
        fm = parse_frontmatter(md_content)
        return {
            "name": name,
            "display_name": fm.name or name,
            "description": fm.description or config.get("description", ""),
            "categories": config.get("categories", []),
            "tags": config.get("tags", []),
            "status": config.get("status", "DRAFT"),
            "scopes": config.get("scopes", []),
            "sync": config.get("sync", False),
            "path": name,
            "updated_at": config.get("updated_at", ""),
        }

    async def _update_index_entry(self, name: str) -> None:
        """Add or update a single skill in the index."""
        async with self._index_lock:
            entries = self._read_index()
            new_entry = self._build_index_entry(name)
            if new_entry is None:
                return
            # Replace existing or append
            entries = [e for e in entries if e.get("name") != name]
            entries.append(new_entry)
            entries.sort(key=lambda e: e.get("name", ""))
            self._write_index(entries)

    async def _remove_index_entry(self, name: str) -> None:
        """Remove a skill from the index."""
        async with self._index_lock:
            entries = self._read_index()
            entries = [e for e in entries if e.get("name") != name]
            self._write_index(entries)

    def _read_config(self, skill_dir: Path) -> dict:
        """Read _config.json from a skill directory."""
        config_path = skill_dir / _CONFIG_FILE
        if not config_path.exists():
            return _default_config()
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_config(self, skill_dir: Path, config: dict) -> None:
        """Write _config.json atomically."""
        config_path = skill_dir / _CONFIG_FILE
        tmp = config_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp), str(config_path))

    def _read_skill_md(self, skill_dir: Path) -> str:
        """Read SKILL.md content."""
        md_path = skill_dir / _SKILL_MD
        if not md_path.exists():
            return ""
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_skill_md(self, skill_dir: Path, content: str) -> None:
        """Write SKILL.md atomically."""
        md_path = skill_dir / _SKILL_MD
        tmp = md_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(str(tmp), str(md_path))

    def _build_skill_dict(self, name: str, config: dict, md_content: str) -> dict:
        """Merge _config.json + SKILL.md frontmatter into a unified skill dict."""
        fm = parse_frontmatter(md_content)
        return {
            "name": name,  # Always the directory slug, never frontmatter name
            "display_name": fm.name or name,
            "description": fm.description or config.get("description", ""),
            "version": fm.raw.get("version", "1.0.0"),
            "allowed_tools": fm.allowed_tools,
            "entity_types": fm.entity_types,
            "contract_refs": fm.contract_refs,
            "skill_md_content": md_content,
            # From _config.json
            "categories": config.get("categories", []),
            "tags": config.get("tags", []),
            "status": config.get("status", "DRAFT"),
            "scopes": config.get("scopes", []),
            "evals_json": config.get("evals_json", []),
            "teslint_config": config.get("teslint_config"),
            "sync": config.get("sync", False),
            "promoted_with_warnings": config.get("promoted_with_warnings", False),
            "promotion_history": config.get("promotion_history", []),
            "usage_count": config.get("usage_count", 0),
            "created_by": config.get("created_by"),
            "created_at": config.get("created_at", ""),
            "updated_at": config.get("updated_at", ""),
        }

    # -- public API -------------------------------------------------------

    async def list_skills(
        self,
        *,
        category: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """List skills from the index with optional filtering.

        Falls back to a full resync if the index is empty / missing.
        """
        self._ensure_dir()
        entries = self._read_index()
        if not entries:
            entries = await self.resync_index()

        # Apply filters
        if category:
            entries = [e for e in entries if category in e.get("categories", [])]
        if tags:
            entries = [
                e for e in entries
                if any(t in e.get("tags", []) for t in tags)
            ]
        if status:
            entries = [e for e in entries if e.get("status") == status]
        if search:
            q = search.lower()
            entries = [
                e for e in entries
                if q in e.get("name", "").lower()
                or q in e.get("description", "").lower()
            ]

        return entries

    async def resync_index(self) -> list[dict]:
        """Rebuild _index.json by scanning all skill directories."""
        self._ensure_dir()
        entries: list[dict] = []
        for entry in sorted(self.skills_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith((".", "_")):
                continue
            idx_entry = self._build_index_entry(entry.name)
            if idx_entry:
                entries.append(idx_entry)
        self._write_index(entries)
        return entries

    async def get_skill(self, name: str) -> dict:
        """Get a single skill by directory name.

        Raises FileNotFoundError if the skill directory does not exist.
        """
        skill_dir = self._skill_dir(name)
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill '{name}' not found")
        config = self._read_config(skill_dir)
        md_content = self._read_skill_md(skill_dir)
        skill = self._build_skill_dict(name, config, md_content)
        skill["files"] = await self.list_files(name)
        return skill

    async def create_skill(self, name: str, initial_config: dict | None = None) -> dict:
        """Create a new skill directory with default files.

        *name* must be a valid slug (lowercase, hyphens) and unique.
        Returns the newly created skill dict.
        """
        if not _is_valid_slug(name):
            raise ValueError(
                f"Invalid skill name '{name}': must be lowercase letters, "
                "numbers, and hyphens (e.g. 'my-skill')"
            )

        if len(name) > 100:
            raise ValueError("Skill name too long (max 100 characters)")

        self._ensure_dir()
        skill_dir = self._skill_dir(name)

        async with self._lock(name):
            if skill_dir.exists():
                raise ValueError(f"Skill '{name}' already exists")
            skill_dir.mkdir(parents=True)

            # Merge initial_config over defaults
            config = _default_config()
            if initial_config:
                for key, val in initial_config.items():
                    if key in config:
                        config[key] = val

            self._write_config(skill_dir, config)

            # Auto-generate SKILL.md with minimal frontmatter
            description = initial_config.get("description", "") if initial_config else ""
            md_content = generate_frontmatter(
                name=name,
                description=description or f"Skill: {name}",
            )
            md_content += "\n\n# Instructions\n\n<!-- Write skill instructions here -->\n"
            self._write_skill_md(skill_dir, md_content)

            # Create standard subdirectories
            for sub in ("scripts", "references", "assets"):
                (skill_dir / sub).mkdir(exist_ok=True)

            # Update index
            await self._update_index_entry(name)

            return self._build_skill_dict(name, config, md_content)

    async def save_skill(
        self,
        name: str,
        config: dict | None = None,
        content: str | None = None,
    ) -> None:
        """Update a skill's _config.json and/or SKILL.md.

        Merges *config* keys into existing _config.json.
        If *content* is provided, overwrites SKILL.md entirely.
        """
        skill_dir = self._skill_dir(name)
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill '{name}' not found")

        async with self._lock(name):
            if config is not None:
                existing = self._read_config(skill_dir)
                existing.update(config)
                existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write_config(skill_dir, existing)

            if content is not None:
                self._write_skill_md(skill_dir, content)

            # Update index
            await self._update_index_entry(name)

    async def delete_skill(self, name: str) -> None:
        """Delete a skill directory entirely."""
        skill_dir = self._skill_dir(name)
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill '{name}' not found")

        async with self._lock(name):
            shutil.rmtree(skill_dir)
            # Clean up lock
            self._locks.pop(name, None)
            # Update index
            await self._remove_index_entry(name)

    # -- file operations --------------------------------------------------

    async def list_files(self, name: str) -> list[dict]:
        """List all bundled files in a skill (scripts/, references/, assets/)."""
        skill_dir = self._skill_dir(name)
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill '{name}' not found")

        files: list[dict] = []
        for prefix in ALLOWED_FILE_PREFIXES:
            folder = skill_dir / prefix.rstrip("/")
            if not folder.is_dir():
                continue
            for file_path in sorted(folder.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(skill_dir).as_posix()
                    files.append({
                        "path": rel,
                        "file_type": _classify_file_type(rel),
                        "size": file_path.stat().st_size,
                    })
        return files

    async def get_file(self, name: str, path: str) -> str:
        """Read a bundled file's content."""
        self._validate_file_path(path)
        file_path = self._skill_dir(name) / path
        if not file_path.is_file():
            raise FileNotFoundError(f"File '{path}' not found in skill '{name}'")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    async def save_file(self, name: str, path: str, content: str) -> None:
        """Write a bundled file (creates parent directories as needed)."""
        self._validate_file_path(path)
        skill_dir = self._skill_dir(name)
        if not skill_dir.is_dir():
            raise FileNotFoundError(f"Skill '{name}' not found")

        async with self._lock(name):
            file_path = skill_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = file_path.with_suffix(file_path.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(str(tmp), str(file_path))

    async def delete_file(self, name: str, path: str) -> None:
        """Delete a bundled file."""
        self._validate_file_path(path)
        file_path = self._skill_dir(name) / path
        if not file_path.is_file():
            raise FileNotFoundError(f"File '{path}' not found in skill '{name}'")

        async with self._lock(name):
            file_path.unlink()

    async def move_file(self, name: str, old_path: str, new_path: str) -> None:
        """Move/rename a file within a skill."""
        self._validate_file_path(old_path)
        self._validate_file_path(new_path)
        skill_dir = self._skill_dir(name)

        src = skill_dir / old_path
        if not src.is_file():
            raise FileNotFoundError(f"File '{old_path}' not found in skill '{name}'")

        dst = skill_dir / new_path
        if dst.exists():
            raise ValueError(f"Destination '{new_path}' already exists")

        async with self._lock(name):
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(src), str(dst))

    def _validate_file_path(self, path: str) -> None:
        """Ensure path starts with an allowed prefix and has no traversal."""
        if not any(path.startswith(p) for p in ALLOWED_FILE_PREFIXES):
            raise ValueError(
                f"File path must start with one of: {', '.join(ALLOWED_FILE_PREFIXES)}"
            )
        # Prevent directory traversal via resolved path comparison
        normalized = os.path.normpath(path)
        if ".." in normalized.split(os.sep) or ".." in normalized.split("/"):
            raise ValueError("Directory traversal is not allowed")
        # Double-check: resolved path must stay within skills_dir
        test_base = Path("/safe")
        resolved = (test_base / normalized).resolve()
        if not str(resolved).startswith(str(test_base.resolve())):
            raise ValueError("Path escapes allowed directory")

"""
Storage Adapter — abstraction layer for Forge data persistence.

Forge supports two storage modes:
- Standalone (JSON files on disk) — current default, zero-setup
- Platform (PostgreSQL via API) — Phase 2, enables Web UI/multi-user

This module defines the StorageAdapter Protocol and the JSONFileStorage
implementation. All core modules use StorageAdapter for I/O instead of
direct file access, enabling backend swapping without changing business logic.

Architecture reference: docs/FORGE-PLATFORM-V2.md Section 7.1
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Helpers (moved here as canonical location; modules will import from here)
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically: temp file + os.replace().

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


# ---------------------------------------------------------------------------
# Entity types
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    """All Forge entity types that can be stored."""
    TRACKER = "tracker"
    DECISIONS = "decisions"
    CHANGES = "changes"
    GUIDELINES = "guidelines"
    IDEAS = "ideas"
    OBJECTIVES = "objectives"
    LESSONS = "lessons"
    KNOWLEDGE = "knowledge"
    AC_TEMPLATES = "ac_templates"


# ---------------------------------------------------------------------------
# Default structures (match what each module's load_or_create returns)
# ---------------------------------------------------------------------------

def default_structure(entity: str, project: str) -> dict:
    """Return the default empty structure for a given entity type.

    These must match exactly what each core module creates when the
    JSON file doesn't exist. This is the single source of truth.
    """
    ts = now_iso()

    defaults = {
        EntityType.TRACKER: {
            "project": project,
            "goal": "",
            "created": ts,
            "updated": ts,
            "config": {},
            "tasks": [],
        },
        EntityType.DECISIONS: {
            "project": project,
            "updated": ts,
            "decisions": [],
            "open_count": 0,
        },
        EntityType.CHANGES: {
            "project": project,
            "updated": ts,
            "changes": [],
        },
        EntityType.GUIDELINES: {
            "project": project,
            "updated": ts,
            "guidelines": [],
        },
        EntityType.IDEAS: {
            "project": project,
            "updated": ts,
            "ideas": [],
        },
        EntityType.OBJECTIVES: {
            "project": project,
            "updated": ts,
            "objectives": [],
        },
        EntityType.LESSONS: {
            "project": project,
            "updated": ts,
            "lessons": [],
        },
        EntityType.KNOWLEDGE: {
            "project": project,
            "updated": ts,
            "knowledge": [],
        },
        EntityType.AC_TEMPLATES: {
            "project": project,
            "updated": ts,
            "ac_templates": [],
        },
    }

    # Accept both EntityType enum and plain string
    if isinstance(entity, str):
        try:
            key = EntityType(entity)
        except ValueError:
            raise StorageError(f"Unknown entity type: {entity}")
    else:
        key = entity
    if key not in defaults:
        raise StorageError(f"Unknown entity type: {entity}")
    return defaults[key]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class EntityNotFoundError(StorageError):
    """Raised when an entity or project does not exist."""
    pass


class StorageWriteError(StorageError):
    """Raised when a write operation fails."""
    pass


# ---------------------------------------------------------------------------
# Storage Adapter Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class StorageAdapter(Protocol):
    """Interface that all storage backends must implement.

    Phase 1 (current): CRUD operations for JSON file storage.
    Phase 2 (future):  Extended with query(), get_related(),
                       subscribe(), begin_transaction() for PostgreSQL.
    """

    def load_data(self, project: str, entity: str) -> dict:
        """Load entity data for a project.

        Args:
            project: Project slug (e.g., 'my-project')
            entity:  Entity type (e.g., 'tracker', 'decisions')

        Returns:
            Parsed dict from storage. If no data exists,
            returns the default empty structure for that entity type.
        """
        ...

    def save_data(self, project: str, entity: str, data: dict) -> None:
        """Save entity data for a project.

        Sets data['updated'] to current timestamp before writing.
        Creates project directory if it doesn't exist.

        Note: Mutates the input dict (sets 'updated' key). This matches
        existing Forge behavior where save_json() modifies data in-place.

        Args:
            project: Project slug
            entity:  Entity type
            data:    Complete entity data dict to persist
        """
        ...

    def exists(self, project: str, entity: str) -> bool:
        """Check whether entity data exists for a project.

        Args:
            project: Project slug
            entity:  Entity type

        Returns:
            True if data exists (file exists / row exists), False otherwise.
        """
        ...

    def list_projects(self) -> list[str]:
        """List all project slugs in storage.

        Returns:
            Sorted list of project slug strings.
            Excludes internal directories (_global, _objectives).
        """
        ...

    def load_global(self, entity: str) -> dict:
        """Load global entity data (not project-specific).

        For JSON storage: reads from _global/{entity}.json.
        For PostgreSQL: queries with project_id=NULL.

        Args:
            entity: Entity type (e.g., 'guidelines')

        Returns:
            Parsed dict. If no data exists, returns default empty structure.
        """
        ...

    def save_global(self, entity: str, data: dict) -> None:
        """Save global entity data (not project-specific).

        Args:
            entity: Entity type
            data:   Complete entity data dict to persist
        """
        ...


# ---------------------------------------------------------------------------
# JSON File Storage (default backend)
# ---------------------------------------------------------------------------

# Internal/special directories that are NOT projects
_INTERNAL_DIRS = {"_global", "_objectives"}


class JSONFileStorage:
    """Storage backend using JSON files on local disk.

    This is the default backend that preserves Forge v1 behavior.
    Data lives in forge_output/{project}/{entity}.json.

    Special paths:
    - _global/guidelines.json  — global guidelines (always loaded)
    - _objectives/             — cross-project objectives (future)
    """

    def __init__(self, base_dir: str = "forge_output") -> None:
        self.base_dir = Path(base_dir)

    def _path(self, project: str, entity: str) -> Path:
        """Resolve file path for a project entity."""
        return self.base_dir / project / f"{entity}.json"

    def load_data(self, project: str, entity: str) -> dict:
        """Load entity data from JSON file, or return default structure."""
        path = self._path(project, entity)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                raise StorageError(f"Failed to read {path}: {e}")
        return default_structure(entity, project)

    def save_data(self, project: str, entity: str, data: dict) -> None:
        """Save entity data to JSON file atomically."""
        data["updated"] = now_iso()
        path = self._path(project, entity)
        try:
            atomic_write_json(path, data)
        except OSError as e:
            raise StorageWriteError(f"Failed to write {path}: {e}")

    def exists(self, project: str, entity: str) -> bool:
        """Check if entity JSON file exists."""
        return self._path(project, entity).exists()

    def list_projects(self) -> list[str]:
        """List project directories under base_dir."""
        if not self.base_dir.exists():
            return []
        return sorted(
            d.name
            for d in self.base_dir.iterdir()
            if d.is_dir() and d.name not in _INTERNAL_DIRS
        )

    def load_global(self, entity: str) -> dict:
        """Load global entity data (e.g., _global/guidelines.json).

        Part of the StorageAdapter Protocol. PostgreSQL adapters implement
        this via project_id=NULL query filter.
        """
        path = self.base_dir / "_global" / f"{entity}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                raise StorageError(f"Failed to read global {path}: {e}")
        return default_structure(entity, "_global")

    def save_global(self, entity: str, data: dict) -> None:
        """Save global entity data (e.g., _global/guidelines.json)."""
        data["updated"] = now_iso()
        path = self.base_dir / "_global" / f"{entity}.json"
        try:
            atomic_write_json(path, data)
        except OSError as e:
            raise StorageWriteError(f"Failed to write global {path}: {e}")

    def __repr__(self) -> str:
        return f"JSONFileStorage(base_dir='{self.base_dir}')"

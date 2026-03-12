"""LLM Permission Engine — controls what LLM can read/write/delete per module.

Two levels: global (platform-wide) and project-level overrides.
Project permissions override global permissions when set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.llm_config import DEFAULT_PERMISSIONS, LLMModulePermission


# All known modules
MODULES = [
    "skills", "tasks", "objectives", "ideas", "knowledge",
    "guidelines", "decisions", "lessons", "projects", "ac_templates",
    "changes", "research",
]

# All known actions
ACTIONS = ("read", "write", "delete")


@dataclass
class PermissionSet:
    """Merged permission set (global + project overrides)."""

    permissions: dict[str, dict[str, bool]] = field(default_factory=dict)

    def check(self, module: str, action: str) -> bool:
        """Check if an action is allowed on a module.

        Args:
            module: Module name (e.g., "skills", "tasks").
            action: Action name ("read", "write", "delete").

        Returns:
            True if allowed, False if denied.
        """
        if action not in ACTIONS:
            return False
        module_perms = self.permissions.get(module, {})
        return module_perms.get(action, False)


class PermissionEngine:
    """Checks what LLM can read/write/delete per module.

    Loads permissions from LLM config (global) and optionally
    merges with project-level overrides.
    """

    @staticmethod
    def load_permissions(
        config: Any,
        project_permissions: dict[str, dict[str, bool]] | None = None,
    ) -> PermissionSet:
        """Build a PermissionSet from config + optional project overrides.

        Args:
            config: LLMConfig instance (has .permissions dict).
            project_permissions: Optional per-project overrides.

        Returns:
            Merged PermissionSet.
        """
        # Start from defaults
        merged: dict[str, dict[str, bool]] = {}

        # Layer 1: defaults
        for module, perms in DEFAULT_PERMISSIONS.items():
            merged[module] = dict(perms)

        # Layer 2: global config overrides
        if hasattr(config, "permissions") and config.permissions:
            for module, perm_obj in config.permissions.items():
                if isinstance(perm_obj, LLMModulePermission):
                    merged[module] = {
                        "read": perm_obj.read,
                        "write": perm_obj.write,
                        "delete": perm_obj.delete,
                    }
                elif isinstance(perm_obj, dict):
                    if module not in merged:
                        merged[module] = {"read": False, "write": False, "delete": False}
                    merged[module].update(perm_obj)

        # Layer 3: project overrides (highest priority)
        if project_permissions:
            for module, perms in project_permissions.items():
                if module not in merged:
                    merged[module] = {"read": False, "write": False, "delete": False}
                merged[module].update(perms)

        return PermissionSet(permissions=merged)

    @staticmethod
    def check(
        permission_set: PermissionSet,
        module: str,
        action: str,
    ) -> bool:
        """Check if an action is allowed.

        Args:
            permission_set: The merged permissions to check against.
            module: Module name.
            action: Action name.

        Returns:
            True if allowed.
        """
        return permission_set.check(module, action)

    @staticmethod
    def deny_response(module: str, action: str) -> dict[str, Any]:
        """Build a structured denial response for tool execution.

        Returns:
            Dict with denial details for the LLM to understand.
        """
        return {
            "denied": True,
            "module": module,
            "action": action,
            "reason": f"Permission denied: LLM cannot '{action}' on '{module}'. "
                      f"This can be changed in Settings > LLM > Permissions.",
        }

    @staticmethod
    def get_defaults() -> dict[str, dict[str, bool]]:
        """Return the default permission map."""
        return dict(DEFAULT_PERMISSIONS)

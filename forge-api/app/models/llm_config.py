"""LLM configuration models — providers, feature flags, permissions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMProviderStatus(BaseModel):
    """Status of a configured LLM provider."""

    name: str
    provider_type: str  # "anthropic" | "openai" | "ollama"
    default_model: str
    available_models: list[str] = []
    status: str = "unchecked"  # "unchecked" | "ok" | "error"
    error: str | None = None


class LLMFeatureFlags(BaseModel):
    """Per-module LLM feature toggles."""

    skills: bool = True  # Skills is the first module — enabled by default
    objectives: bool = False
    ideas: bool = False
    tasks: bool = False
    knowledge: bool = False
    guidelines: bool = False
    decisions: bool = False
    lessons: bool = False
    ac_templates: bool = False
    projects: bool = False
    changes: bool = False
    research: bool = False


class LLMModulePermission(BaseModel):
    """Read/write/delete permissions for a single module."""

    read: bool = True
    write: bool = False
    delete: bool = False


# Default permissions: read-all, write-skills-only, delete-none
DEFAULT_PERMISSIONS: dict[str, dict[str, bool]] = {
    "skills": {"read": True, "write": True, "delete": False},
    "objectives": {"read": True, "write": False, "delete": False},
    "ideas": {"read": True, "write": False, "delete": False},
    "tasks": {"read": True, "write": False, "delete": False},
    "knowledge": {"read": True, "write": False, "delete": False},
    "guidelines": {"read": True, "write": False, "delete": False},
    "decisions": {"read": True, "write": False, "delete": False},
    "lessons": {"read": True, "write": False, "delete": False},
    "ac_templates": {"read": True, "write": False, "delete": False},
    "projects": {"read": True, "write": False, "delete": False},
    "changes": {"read": True, "write": False, "delete": False},
    "research": {"read": True, "write": False, "delete": False},
}


class LLMConfig(BaseModel):
    """Global LLM configuration — stored in _global/llm_config.json."""

    default_provider: str = "anthropic"
    default_model: str | None = None  # None = use provider's default
    feature_flags: LLMFeatureFlags = Field(default_factory=LLMFeatureFlags)
    permissions: dict[str, LLMModulePermission] = Field(
        default_factory=lambda: {
            module: LLMModulePermission(**perms)
            for module, perms in DEFAULT_PERMISSIONS.items()
        }
    )
    max_tokens_per_session: int = 50_000
    max_iterations_per_turn: int = 10
    session_ttl_hours: int = 24


class LLMConfigUpdate(BaseModel):
    """Partial update for LLM config. All fields optional."""

    default_provider: str | None = None
    default_model: str | None = None
    feature_flags: dict[str, bool] | None = None
    permissions: dict[str, LLMModulePermission | dict[str, bool]] | None = None
    max_tokens_per_session: int | None = None
    max_iterations_per_turn: int | None = None
    session_ttl_hours: int | None = None

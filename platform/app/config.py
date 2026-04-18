import os
import pathlib

from pydantic_settings import BaseSettings


# Known-insecure dev defaults — MUST be overridden in production.
# Validation in _assert_production_safe() below prevents production startup with these.
_DEV_JWT_SECRET = "dev-secret-change-in-production-via-FORGE_JWT_SECRET_KEY"
_DEV_ENCRYPTION_KEY_B64 = "ZGV2LWtleS0zMi1ieXRlcy1pbnNlY3VyZS1jaGFuZ2UtbWUh"  # "dev-key-32-bytes-insecure-change-me!"

# Repo-root-relative workspace default — config.py lives at platform/app/config.py,
# so repo root = parents[2]. Resolved at import, independent of CWD.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_WORKSPACE_ROOT = str(_REPO_ROOT / "forge_output")


class Settings(BaseSettings):
    database_url: str = "postgresql://forge:forge@localhost:5432/forge_platform"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    prompt_budget_kb: int = 50
    max_delivery_attempts: int = 5
    lease_duration_minutes: int = 30
    max_lease_renewals: int = 20
    heartbeat_interval_minutes: int = 10
    # Workspace root — resolved from repo structure (CWD-independent). Override via FORGE_WORKSPACE_ROOT.
    workspace_root: str = _DEFAULT_WORKSPACE_ROOT
    claude_model: str = "sonnet"
    claude_model_challenger: str = "opus"
    claude_budget_per_task_usd: float = 5.0
    claude_budget_per_scenario_usd: float = 50.0
    claude_timeout_sec: int = 900
    orchestrator_max_retries_per_task: int = 3
    orchestrator_max_tasks: int = 50

    # --- Environment marker (for prod-safety checks) ---
    # Set FORGE_ENV=production in production deployments. Anything else treated as dev/test.
    env: str = "development"

    # --- Auth + multi-tenant (Phase 1 W1) ---
    jwt_secret_key: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 60 * 12  # 12h access token Phase 1
    # AES-GCM 32-byte key, base64-encoded. Dev default is INSECURE — override via FORGE_ENCRYPTION_KEY_B64.
    # Generate prod key: python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
    encryption_key_b64: str = _DEV_ENCRYPTION_KEY_B64
    default_org_slug: str = "default"
    default_org_name: str = "Default Organization"

    model_config = {"env_prefix": "FORGE_", "env_file": ".env"}


def _assert_production_safe(s: Settings) -> None:
    """Refuse to start production with dev secrets. Dev/test envs pass through."""
    if s.env.lower() != "production":
        return
    problems = []
    if s.jwt_secret_key == _DEV_JWT_SECRET:
        problems.append("FORGE_JWT_SECRET_KEY (dev default leaks all sessions)")
    if s.encryption_key_b64 == _DEV_ENCRYPTION_KEY_B64:
        problems.append("FORGE_ENCRYPTION_KEY_B64 (dev default leaks all encrypted org secrets)")
    if problems:
        raise RuntimeError(
            "Refusing to start production with insecure default secrets. "
            f"Override: {', '.join(problems)}"
        )


settings = Settings()
_assert_production_safe(settings)

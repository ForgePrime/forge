from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://forge:forge@localhost:5432/forge_platform"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    prompt_budget_kb: int = 50
    max_delivery_attempts: int = 5
    lease_duration_minutes: int = 30
    max_lease_renewals: int = 20
    heartbeat_interval_minutes: int = 10
    workspace_root: str = "C:/Users/lukasz.krysik/Desktop/LINGARO/AI/forge/forge_output"
    claude_model: str = "sonnet"
    claude_model_challenger: str = "opus"
    claude_budget_per_task_usd: float = 5.0
    claude_budget_per_scenario_usd: float = 50.0
    claude_timeout_sec: int = 900
    orchestrator_max_retries_per_task: int = 3
    orchestrator_max_tasks: int = 50

    # --- Auth + multi-tenant (Phase 1 W1) ---
    jwt_secret_key: str = "dev-secret-change-in-production-via-FORGE_JWT_SECRET_KEY"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 60 * 12  # 12h access token Phase 1 (Phase 2 will shorten + add refresh)
    # AES-GCM 32-byte key, base64-encoded. Dev default below IS INSECURE — override via FORGE_ENCRYPTION_KEY.
    # Generate prod key: python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
    encryption_key_b64: str = "ZGV2LWtleS0zMi1ieXRlcy1pbnNlY3VyZS1jaGFuZ2UtbWUh"  # "dev-key-32-bytes-insecure-change-me!" base64
    default_org_slug: str = "default"
    default_org_name: str = "Default Organization"

    model_config = {"env_prefix": "FORGE_", "env_file": ".env"}


settings = Settings()

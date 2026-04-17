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

    model_config = {"env_prefix": "FORGE_", "env_file": ".env"}


settings = Settings()

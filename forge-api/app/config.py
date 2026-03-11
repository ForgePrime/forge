"""Application configuration from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Forge API settings — loaded from environment or .env file."""

    # Database
    database_url: str = "postgresql://forge:forge@localhost:5432/forge_db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Auth
    api_key: str = ""  # For CLI access; empty = no auth required
    jwt_secret: str = ""  # REQUIRED in production: set FORGE_JWT_SECRET env var
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_expire_minutes: int = 60

    # LLM
    llm_config_path: str = "/config/providers.toml"

    # Storage mode: "json" (file-based) or "postgresql"
    storage_mode: str = "postgresql"
    json_data_dir: str = "forge_output"

    model_config = {"env_prefix": "FORGE_", "env_file": ".env", "extra": "ignore"}


settings = Settings()

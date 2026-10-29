from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INCIDENT_",
        env_file=".env",
        extra="ignore",
    )

    model: str = ""
    api_key: SecretStr = SecretStr("")
    base_url: str | None = None

    approval_secret: SecretStr = SecretStr("")

    mcp_url: str = "http://127.0.0.1:8000/mcp"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    runtime_directory: Path = Path("runtime")

    max_model_calls: int = Field(default=12, ge=1)
    max_tool_calls: int = Field(default=15, ge=1)
    max_recovery_attempts: int = Field(default=2, ge=1)
    no_progress_limit: int = Field(default=3, ge=2)

    active_timeout_seconds: float = Field(default=120, gt=0)
    model_timeout_seconds: float = Field(default=30, gt=0)
    tool_timeout_seconds: float = Field(default=10, gt=0)

    def signing_key(self) -> str:
        value = self.approval_secret.get_secret_value()

        if len(value) < 32:
            raise ValueError(
                "INCIDENT_APPROVAL_SECRET must contain at least 32 characters"
            )

        return value


    
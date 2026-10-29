"""Validated configuration; run commands from the project root for relative paths."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INCIDENT_", env_file=".env", extra="ignore"
    )

    mcp_url: str = "http://127.0.0.1:8000/mcp"
    scenario_directory: Path = Path("data/scenarios")
    runtime_directory: Path = Path("runtime")
    max_model_calls: int = Field(default=12, ge=1)
    max_tool_calls: int = Field(default=15, ge=1)
    max_recovery_attempts: int = Field(default=2, ge=0)
    no_progress_limit: int = Field(default=3, ge=1)
    active_timeout_seconds: float = Field(default=120, gt=0)
    model_timeout_seconds: float = Field(default=30, gt=0)
    tool_timeout_seconds: float = Field(default=10, gt=0)
    require_approval: bool = True

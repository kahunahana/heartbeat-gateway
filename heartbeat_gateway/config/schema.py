from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class LinearWatchConfig(BaseSettings):
    model_config = {"extra": "ignore"}

    project_ids: list[str] = Field(default_factory=list)
    assignee_filter: str = "any"  # "self" | "any"
    secret: str = ""


class GitHubWatchConfig(BaseSettings):
    model_config = {"extra": "ignore"}

    repos: list[str] = Field(default_factory=list)
    ci_workflows: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=lambda: ["main"])
    secret: str = ""


class PostHogWatchConfig(BaseSettings):
    model_config = {"extra": "ignore"}

    project_id: str = ""
    insight_ids: list[str] = Field(default_factory=list)
    secret: str = ""


class WatchConfig(BaseSettings):
    model_config = {"extra": "ignore"}

    linear: LinearWatchConfig = Field(default_factory=LinearWatchConfig)
    github: GitHubWatchConfig = Field(default_factory=GitHubWatchConfig)
    posthog: PostHogWatchConfig = Field(default_factory=PostHogWatchConfig)


class GatewayConfig(BaseSettings):
    model_config = {
        "env_prefix": "GATEWAY_",
        "extra": "ignore",
        "populate_by_name": True,
    }

    workspace_path: Path = Field(default_factory=lambda: Path("~/workspace").expanduser())
    soul_md_path: Path = Field(default_factory=lambda: Path("~/workspace/SOUL.md").expanduser())
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "GATEWAY_LLM_API_KEY"),
    )
    heartbeat_max_active_tasks: int = 20
    audit_log_path: Path | None = None
    watch: WatchConfig = Field(default_factory=WatchConfig)

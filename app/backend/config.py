"""Single source of configuration truth. Every setting is read from here via
Depends(get_settings) — no scattered os.environ.get() calls elsewhere."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# AWS SSM SecureString parameters can't hold an empty string, so the
# Terraform-provisioned placeholders (see deploy/terraform/secrets.tf) use
# these sentinels instead of "" until a real value is set with
# `aws ssm put-parameter --overwrite`. Without this check they'd be truthy
# and, for Langfuse specifically, trip LangfuseObservability's eager
# auth_check() and crash the whole app at startup on a fresh deploy.
_UNSET_SENTINELS = {"", "CHANGE_ME", "UNSET"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Langfuse (optional)
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Storage
    DATABASE_PATH: str = "./data/cis.db"
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    UPLOAD_DIR: str = "./data/uploads"

    # Auth
    SESSION_SECRET: str = "dev-only-change-me"

    # Pipeline thresholds
    EXTRACTION_CONFIDENCE_THRESHOLD: float = 0.6
    INSIGHT_CONFIDENCE_THRESHOLD: float = 0.65

    @property
    def langfuse_configured(self) -> bool:
        return (
            bool(self.LANGFUSE_PUBLIC_KEY) and self.LANGFUSE_PUBLIC_KEY not in _UNSET_SENTINELS
            and bool(self.LANGFUSE_SECRET_KEY) and self.LANGFUSE_SECRET_KEY not in _UNSET_SENTINELS
        )

    @property
    def openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY) and self.OPENAI_API_KEY not in _UNSET_SENTINELS


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Single source of configuration truth. Every setting is read from here via
Depends(get_settings) — no scattered os.environ.get() calls elsewhere."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()

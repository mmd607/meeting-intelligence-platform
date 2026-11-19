"""Application configuration loaded from environment variables.

Single source of truth for limits/paths so they are not hard-coded
in multiple places (see spec: MAX_AUDIO_SIZE_MB, STORAGE_PATH, ...).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    MAX_AUDIO_SIZE_MB: int = 500
    STORAGE_PATH: str = "./backend/data"
    DATABASE_URL: str = "sqlite:///./backend/data/app.db"
    TRANSCRIPTION_PROVIDER: str = "fake"
    TRANSCRIPTION_MODEL: str = "tiny"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # v0.2 Speaker Diarization
    DIARIZATION_ENABLED: bool = False
    DIARIZATION_PROVIDER: str = "fake"

    # v0.3 Semantic Analysis
    SEMANTIC_ANALYSIS_ENABLED: bool = False
    SEMANTIC_ANALYSIS_PROVIDER: str = "fake"
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"

    @property
    def max_audio_size_bytes(self) -> int:
        return self.MAX_AUDIO_SIZE_MB * 1024 * 1024

    @property
    def storage_root(self) -> Path:
        return Path(self.STORAGE_PATH)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {".wav", ".mp3", ".m4a"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

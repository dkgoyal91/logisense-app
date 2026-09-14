from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    app_name: str = 'LogiSense AI Copilot'
    debug: bool = False
    database_path: str = 'data/logisense.db'
    row_limit: int = 20
    ai_provider: str = 'fallback'
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_model: str = 'llama-3.1-8b-instant'
    gemini_model: str = 'gemini-1.5-flash'
    enable_external_ai: bool = False

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.enable_external_ai and self.ai_provider == 'groq' and self.groq_api_key)

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.enable_external_ai and self.ai_provider == 'gemini' and self.gemini_api_key)

    @property
    def active_ai_provider(self) -> str:
        if self.is_groq_configured:
            return 'groq'
        if self.is_gemini_configured:
            return 'gemini'
        return 'fallback'


settings = Settings()

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

    app_name: str = 'LogiSense Logistics Copilot'
    debug: bool = False
    database_path: str = 'data/logisense.db'
    row_limit: int = 20
    groq_api_key: str | None = None
    groq_model: str = 'openai/gpt-oss-20b'

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key != 'your_groq_api_key_here')

    @property
    def active_ai_provider(self) -> str:
        return 'groq' if self.is_groq_configured else 'unconfigured'


settings = Settings()

from __future__ import annotations

from pathlib import Path

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
    game_host_pin: str | None = None
    game_public_url: str = ''
    game_snapshot_path: str = 'data/game_snapshot.json'
    frontend_dist_path: str = '../frontend/dist'

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_api_key != 'your_groq_api_key_here')

    @property
    def active_ai_provider(self) -> str:
        return 'groq' if self.is_groq_configured else 'unconfigured'


BACKEND_DIR = Path(__file__).resolve().parent.parent


def resolve_backend_path(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else BACKEND_DIR / candidate


settings = Settings()

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "HireTrack API"
    database_url: str = "sqlite:///./hiretrack.db"
    cors_origins: str = "http://localhost:5173"
    prep_dir: Path = REPO_ROOT / "prep"
    # Demo rows are off by default so the app only ever shows your real data.
    seed_demo_data: bool = False
    remotive_url: str = "https://remotive.com/api/remote-jobs"
    # Free key from https://developer.adzuna.com — enables the Adzuna India source.
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"
    # Re-run saved job sources in the background every N hours (0 = only when you click Refresh).
    auto_refresh_hours: float = 12

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

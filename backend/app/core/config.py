from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "JobRadar"
    environment: str = "development"
    demo_mode: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = Field(default=f"sqlite:///{DATA_DIR / 'jobradar.db'}")
    upload_dir: Path = Field(default=DATA_DIR / "uploads")
    export_dir: Path = Field(default=DATA_DIR / "exports")

    llm_provider: str = "openrouter"
    llm_api_key: str = ""
    openrouter_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model_fast: str = "nvidia/nemotron-3.5-lightning:free"
    llm_model_quality: str = "nvidia/nemotron-3-super-120b-a12b:free"
    llm_model_fallback: str = "nvidia/nemotron-3.5-super-vl:free"
    llm_timeout_seconds: int = 90

    auto_submit_enabled: bool = False
    auto_submit_max_per_run: int = 5
    auto_submit_portals: str = "greenhouse,lever,ashby,workable,breezy,teamtailor"
    manual_only_portals: str = "linkedin,indeed,computrabajo,magneto,elempleo,glassdoor"
    default_cv_source: str = "tailored"
    freshness_days: int = 2

    jsearch_api_key: str = ""
    jooble_api_key: str = ""
    brave_search_api_key: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_to: str = ""
    alert_threshold: int = 85
    digest_threshold: int = 70
    digest_hour: int = 8

    enable_scheduler: bool = False
    search_interval_hours: int = 6
    timezone: str = "America/Bogota"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool((self.llm_api_key or self.openrouter_api_key).strip())

    @property
    def resolved_llm_api_key(self) -> str:
        return (self.llm_api_key or self.openrouter_api_key).strip()

    @property
    def auto_submit_portals_list(self) -> list[str]:
        return [value.strip().lower() for value in self.auto_submit_portals.split(",") if value.strip()]

    @property
    def manual_only_portals_list(self) -> list[str]:
        return [value.strip().lower() for value in self.manual_only_portals.split(",") if value.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_user.strip() and self.smtp_password.strip())

    @property
    def jsearch_configured(self) -> bool:
        return bool(self.jsearch_api_key.strip())

    @property
    def jooble_configured(self) -> bool:
        return bool(self.jooble_api_key.strip())

    @property
    def brave_configured(self) -> bool:
        return bool(self.brave_search_api_key.strip())

    def ensure_dirs(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings

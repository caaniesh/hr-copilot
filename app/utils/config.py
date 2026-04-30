from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
DEFAULT_DB_PATH = Path(tempfile.gettempdir()) / "interview_copilot" / "interview_copilot.db"
DB_PATH = Path(os.getenv("INTERVIEW_COPILOT_DB_PATH", str(DEFAULT_DB_PATH)))
if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH


def _resolve_database_url() -> str:
    """Render/Heroku Postgres URLs use postgres://; SQLAlchemy expects postgresql://."""
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return f"sqlite:///{DB_PATH.as_posix()}"
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql://", 1)
    return raw


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Technical Interview Copilot for HR"
    database_url: str = field(default_factory=_resolve_database_url)
    upload_dir: Path = UPLOAD_DIR
    export_dir: Path = EXPORT_DIR
    static_dir: Path = STATIC_DIR
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    aiml_api_url: str = os.getenv("AIML_API_URL", "")
    aiml_api_key: str = os.getenv("AIML_API_KEY", "")
    assistant_provider: str = os.getenv("ASSISTANT_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "10m")


settings = Settings()


def ensure_directories() -> None:
    for path in (DATA_DIR, settings.upload_dir, settings.export_dir, settings.static_dir, DB_PATH.parent):
        path.mkdir(parents=True, exist_ok=True)

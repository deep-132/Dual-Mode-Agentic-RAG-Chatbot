"""Centralized application settings, loaded from environment variables.

Kept as a single Pydantic settings object so every module imports one
source of truth instead of scattering `os.getenv` calls.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    # Absolute paths, not a bare ".env" -- a relative path is resolved against
    # the process's current working directory, which silently breaks whenever
    # uvicorn isn't launched from exactly one expected directory. Checking
    # both the project root (docker-compose's `env_file: .env`) and
    # backend/.env (local `uvicorn` runs from within backend/) means either
    # convention works regardless of where the command was actually run from.
    # Real environment variables (e.g. Docker's `environment:`) always win
    # over both.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Azure OpenAI ---
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o"

    # --- Data / knowledge base paths ---
    documents_dir: Path = BASE_DIR / "data" / "documents"
    orders_csv_path: Path = BASE_DIR / "data" / "orders.csv"
    index_dir: Path = BASE_DIR / "index"

    # --- RAG ---
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_top_k: int = 4

    # --- Agent behaviour ---
    # The assignment fixes "today" so date-relative questions ("last month",
    # "this year") resolve deterministically instead of drifting with wall-clock time.
    business_current_date: str = "2026-06-15"
    max_tool_iterations: int = 4
    sql_row_limit: int = 200

    # --- CORS ---
    allowed_origins: list[str] = ["http://localhost:3000"]


def require_azure_credentials(settings: "Settings") -> None:
    """Fail fast and legibly the moment something actually needs to talk to
    Azure OpenAI, rather than surfacing as an opaque `openai.APIConnectionError`
    deep in the agent loop the first time a chat request runs.

    Deliberately NOT a Settings-level validator: Settings is also constructed
    by build-time-only code (`scripts/build_index.py`, prebuilding the FAISS
    index) that never touches Azure and has no reason to require its
    credentials -- e.g. Docker build steps don't have runtime environment
    variables injected, so requiring them there breaks the image build.
    """
    missing = [
        name
        for name, value in (
            ("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key),
            ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"Missing required setting(s): {', '.join(missing)}. "
            f"Set them via environment variables, or in a .env file at "
            f"{PROJECT_ROOT / '.env'} or {BASE_DIR / '.env'}."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

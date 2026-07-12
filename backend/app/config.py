"""Centralized application settings, loaded from environment variables.

Kept as a single Pydantic settings object so every module imports one
source of truth instead of scattering `os.getenv` calls.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()

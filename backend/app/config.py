"""
config.py — Application Configuration

WHY THIS FILE EXISTS:
  Instead of calling os.getenv("GOOGLE_API_KEY") scattered everywhere,
  we use a single Settings class. This gives us:
  - Type safety (pydantic validates types automatically)
  - A single place to see ALL configuration
  - Auto-loading from .env file

HOW IT WORKS:
  pydantic-settings reads the .env file and maps variables
  to the class fields. If a required field is missing, it raises
  a clear error at startup (fail fast — not at 2am during a demo).

  The @lru_cache decorator means Settings() is only created ONCE
  and reused. Like a singleton, but Pythonic.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google API — no longer required (embeddings use local BAAI model, LLM uses Groq)
    google_api_key: str = ""

    # Groq API — newly added for lightning fast LLM generation
    groq_api_key: str

    # Primary LLM — high quality model for question generation and evaluation.
    groq_model: str = "llama-3.3-70b-versatile"

    # Fallback LLM — fast, lightweight model used automatically when the primary
    # hits a rate limit (HTTP 429). Transparent to the user — interview continues.
    groq_fallback_model: str = "llama-3.1-8b-instant"

    # SQL logging can be noisy/slower during heavy flows; keep off by default.
    sql_echo: bool = False

    # Embedding model — DO NOT change unless ChromaDB is reset first
    # (changing embedding model = vectors are incompatible = must re-ingest)
    # BAAI/bge-base-en-v1.5: 768 dims, MTEB 72.3 (better than Google Gemini 71.0)
    # Local model: no API key, no rate limits, instant retrieval, reliable.
    # Pre-downloaded in Docker for zero cold-start overhead.
    embedding_model: str = "BAAI/bge-base-en-v1.5"

    # Database — SQLite file path for local dev
    database_url: str = "sqlite:///./preplingo.db"

    # JWT authentication settings
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ChromaDB — where the vector index is persisted on disk
    vector_store_path: str = "./vector_store_data"

    # Hard timeout for LLM calls to avoid long hangs in interactive interview UX.
    llm_timeout_seconds: int = 25

    # Environment flag
    app_env: str = "development"

    class Config:
        env_file = ".env"  # Auto-loads from backend/.env


@lru_cache()
def get_settings() -> Settings:
    """
    Returns the cached Settings instance.
    Use this everywhere: from app.config import get_settings
    
    Example:
        settings = get_settings()
        api_key = settings.google_api_key
    """
    return Settings()

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
    # Google API — NOW USED ONLY FOR EMBEDDINGS (not LLM)
    google_api_key: str

    # Groq API — newly added for lightning fast LLM generation
    groq_api_key: str

    # LLM Model — We switched to Groq for speed and generous free tiers
    # "llama-3.3-70b-versatile" is the current state-of-the-art open model
    groq_model: str = "llama-3.3-70b-versatile"

    # Embedding model — DO NOT change unless ChromaDB is reset first
    # (changing embedding model = vectors are incompatible = must re-ingest)
    embedding_model: str = "models/gemini-embedding-001"

    # Database — SQLite file path for local dev
    database_url: str = "sqlite:///./preplingo.db"

    # JWT authentication settings
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ChromaDB — where the vector index is persisted on disk
    vector_store_path: str = "./vector_store_data"

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

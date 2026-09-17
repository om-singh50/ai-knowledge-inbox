import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Predictable local data directory relative to this file
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_DB_PATH = os.path.join(_BASE_DIR, "data", "knowledge.db")

class Settings(BaseSettings):
    app_name: str = "AI Knowledge Inbox API"
    debug: bool = False
    db_path: str = _DEFAULT_DB_PATH
    gemini_api_key: str = ""
    embedding_model: str = "gemini-embedding-001"
    gemini_generation_model: str = "gemini-3.6-flash"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

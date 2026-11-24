from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:5432/knowledgebase"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "nomic-embed-text"
    embed_dimensions: int = 768
    upload_dir: Path = Path("data/uploads")
    max_upload_mb: int = 20
    chunk_size: int = 900
    chunk_overlap: int = 150
    candidates: int = 20
    rerank_enabled: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rewrite_enabled: bool = False
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    log_level: str = "INFO"
    api_key: str = "change-this-local-dev-key"
    worker_poll_seconds: int = 3

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()

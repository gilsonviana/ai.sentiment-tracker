from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    app_name: str = "AI Journal"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    db_path: str = str(base_dir / "data" / "journal.db")
    chroma_path: str = str(base_dir / "data" / "chroma")

    # Models
    embedding_model: str = "all-MiniLM-L6-v2"
    roberta_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"

    # Inference
    max_entry_length: int = 5000
    chunk_size: int = 512

    # Ollama
    ollama_url: str = "http://localhost:11434"

    class Config:
        env_file = ".env"

settings = Settings()
"""Configuration management for the ESG data extraction system."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Model Configuration - Free Models from OpenRouter
    default_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    backup_models: list[str] = [
        "google/gemini-2.0-flash-exp:free",
        "qwen/qwen3-coder:free"
    ]
    
    # Database
    database_url: str = "sqlite:///./data/esg_data.db"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Processing Configuration
    max_retries: int = 3
    chunk_size: int = 2000
    chunk_overlap: int = 200
    temperature: float = 0.1
    max_tokens: int = 2000
    
    # Paths
    base_dir: Path = Path(__file__).parent
    reports_dir: Path = base_dir / "reports"
    outputs_dir: Path = base_dir / "outputs"
    data_dir: Path = base_dir / "data"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        self.reports_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()

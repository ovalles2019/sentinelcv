"""Application settings from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).parent / "data"


class Settings(BaseSettings):
    poll_interval_seconds: int = 15
    vision_provider: str = "auto"  # auto | mock | azure | rekognition | aws
    azure_vision_endpoint: str = ""
    azure_vision_key: str = ""
    azure_min_gap_seconds: float = 3.2
    # AWS Rekognition — credentials via standard AWS env vars / shared config
    aws_region: str = "us-east-1"
    aws_rekognition_min_gap_seconds: float = 1.0
    aws_rekognition_min_confidence: float = 55.0
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    cameras_path: str = str(DATA_DIR / "cameras.json")
    http_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

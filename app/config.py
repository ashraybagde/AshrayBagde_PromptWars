"""Runtime configuration, read only from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    timeout_s: float = 45.0
    max_payload_bytes: int = 64_000
    rate_limit: int = 10
    rate_window_s: int = 60


settings = Settings()

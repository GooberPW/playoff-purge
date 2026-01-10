"""Configuration management using pydantic-settings."""
import json
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Sheets
    google_sheet_id: str
    google_application_credentials: Optional[str] = None
    google_application_credentials_json: Optional[str] = None
    
    # Cache
    cache_ttl_seconds: int = 600  # 10 minutes to reduce API calls
    
    # Admin
    admin_password: str = "changeme"
    
    # App
    app_title: str = "PlayoffPurge 2025"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_credentials_path(self) -> str:
        """
        Get the path to Google credentials.
        For Render deployment, creates a temp file from JSON env var.
        For local dev, uses the file path.
        """
        # If JSON credentials provided (Render deployment)
        if self.google_application_credentials_json:
            # Create temporary credentials file
            temp_path = Path("temp_credentials.json")
            if not temp_path.exists():
                creds_data = json.loads(self.google_application_credentials_json)
                with open(temp_path, "w") as f:
                    json.dump(creds_data, f)
            return str(temp_path)
        
        # Otherwise use file path (local dev)
        if self.google_application_credentials:
            return self.google_application_credentials
        
        raise ValueError(
            "Must provide either GOOGLE_APPLICATION_CREDENTIALS or "
            "GOOGLE_APPLICATION_CREDENTIALS_JSON"
        )


# Global settings instance
settings = Settings()

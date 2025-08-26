"""Configuration management for VNBdigitaler."""

from typing import TYPE_CHECKING, ClassVar

import streamlit as st
from pydantic import Field
from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    pass


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database
    database_url: str = Field(default="", description="Database URL")

    # AI Services
    openrouter_api_key: str = Field(default="", description="OpenRouter API Key")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter Base URL",
    )

    # AI Model Configuration
    roll_out_report_find_model: str = Field(
        default="meta-llama/llama-3.2-3b-instruct:free",
        description="Model for roll-out report finding",
    )

    # Object Storage
    r2_access_key: str = Field(default="", description="Cloudflare R2 Access Key")
    r2_secret_key: str = Field(default="", description="Cloudflare R2 Secret Key")
    r2_bucket_name: str = Field(default="", description="Cloudflare R2 Bucket Name")
    r2_endpoint: str = Field(default="", description="Cloudflare R2 Endpoint")

    # Geocoding Services
    opencagedata_api_key: str = Field(default="", description="OpenCageData API Key")
    opencagedata_api_url: str = Field(
        default="https://api.opencagedata.com/geocode/v1/json",
        description="OpenCageData API URL",
    )

    # Application
    log_level: str = Field(default="INFO", description="Logging Level")
    environment: str = Field(default="development", description="Environment")

    model_config: ClassVar = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
    }

    @classmethod
    def from_streamlit_secrets(cls) -> "Settings":
        """Load settings from Streamlit secrets in production."""
        try:
            if hasattr(st, "secrets"):
                return cls(
                    database_url=st.secrets["database"]["url"],
                    openrouter_api_key=st.secrets["openrouter"]["api_key"],
                    openrouter_base_url=st.secrets["openrouter"]["base_url"],
                    roll_out_report_find_model=st.secrets.get("ai", {}).get(
                        "roll_out_report_find_model",
                        "meta-llama/llama-3.2-3b-instruct:free",
                    ),
                    r2_access_key=st.secrets["cloudflare_r2"]["access_key"],
                    r2_secret_key=st.secrets["cloudflare_r2"]["secret_key"],
                    r2_bucket_name=st.secrets["cloudflare_r2"]["bucket_name"],
                    r2_endpoint=st.secrets["cloudflare_r2"]["endpoint"],
                    log_level=st.secrets["app"]["log_level"],
                    environment=st.secrets["app"]["environment"],
                )
        except (ImportError, KeyError):
            pass
        return cls()

    def get_database_url(self) -> str:
        """Get the database URL."""
        url = self.database_url
        # Convert sync postgresql:// URLs to async postgresql+asyncpg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Fix SSL parameters for asyncpg
            url = url.replace("sslmode=require", "ssl=require")
            url = url.replace("channel_binding=require", "")
            # Clean up extra & characters
            url = url.replace("&&", "&").rstrip("&")
        return url


# Module-level settings cache
_settings_cache: Settings | None = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings_cache  # noqa: PLW0603
    if _settings_cache is None:
        # Try Streamlit secrets first, fallback to environment
        try:
            _settings_cache = Settings.from_streamlit_secrets()
        except Exception:
            _settings_cache = Settings()
    return _settings_cache


def reset_settings() -> None:
    """Reset settings cache (useful for testing)."""
    global _settings_cache  # noqa: PLW0603
    _settings_cache = None

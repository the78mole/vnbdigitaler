"""Test configuration module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.config import Settings, get_settings, reset_settings


def test_settings_from_environment():
    """Test loading settings from environment variables."""
    with patch.dict(os.environ, {
        'NEON_DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
        'OPENROUTER_API_KEY': 'test-key',
        'CLOUDFLARE_R2_ACCESS_KEY': 'test-access',
        'CLOUDFLARE_R2_SECRET_KEY': 'test-secret',
        'CLOUDFLARE_R2_BUCKET_NAME': 'test-bucket',
        'CLOUDFLARE_R2_ENDPOINT': 'https://test.r2.cloudflarestorage.com',
        'LOG_LEVEL': 'DEBUG',
        'ENVIRONMENT': 'test'
    }):
        reset_settings()
        settings = get_settings()

        assert settings.database_url == 'postgresql+asyncpg://test:test@localhost:5432/test'
        assert settings.openrouter_api_key == 'test-key'
        assert settings.r2_access_key == 'test-access'
        assert settings.log_level == 'DEBUG'
        assert settings.environment == 'test'


def test_settings_defaults():
    """Test default values for optional settings."""
    with patch.dict(os.environ, {
        'NEON_DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
        'OPENROUTER_API_KEY': 'test-key',
        'CLOUDFLARE_R2_ACCESS_KEY': 'test-access',
        'CLOUDFLARE_R2_SECRET_KEY': 'test-secret',
        'CLOUDFLARE_R2_BUCKET_NAME': 'test-bucket',
        'CLOUDFLARE_R2_ENDPOINT': 'https://test.r2.cloudflarestorage.com',
    }, clear=True):
        reset_settings()
        settings = get_settings()

        assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert settings.log_level == "INFO"
        assert settings.environment == "development"


def test_settings_from_streamlit_secrets():
    """Test loading settings from Streamlit secrets."""
    mock_secrets = {
        "database": {"url": "postgresql+asyncpg://streamlit:test@localhost:5432/streamlit"},
        "openrouter": {
            "api_key": "streamlit-key",
            "base_url": "https://openrouter.ai/api/v1"
        },
        "cloudflare_r2": {
            "access_key": "streamlit-access",
            "secret_key": "streamlit-secret",
            "bucket_name": "streamlit-bucket",
            "endpoint": "https://streamlit.r2.cloudflarestorage.com"
        },
        "app": {
            "log_level": "INFO",
            "environment": "production"
        }
    }

    mock_st = MagicMock()
    mock_st.secrets = mock_secrets

    with patch.dict('sys.modules', {'streamlit': mock_st}):
        reset_settings()
        settings = Settings.from_streamlit_secrets()

        assert settings.database_url == "postgresql+asyncpg://streamlit:test@localhost:5432/streamlit"
        assert settings.openrouter_api_key == "streamlit-key"
        assert settings.r2_access_key == "streamlit-access"
        assert settings.environment == "production"


def test_settings_singleton():
    """Test that get_settings returns the same instance."""
    reset_settings()

    with patch.dict(os.environ, {
        'NEON_DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
        'OPENROUTER_API_KEY': 'test-key',
        'CLOUDFLARE_R2_ACCESS_KEY': 'test-access',
        'CLOUDFLARE_R2_SECRET_KEY': 'test-secret',
        'CLOUDFLARE_R2_BUCKET_NAME': 'test-bucket',
        'CLOUDFLARE_R2_ENDPOINT': 'https://test.r2.cloudflarestorage.com',
    }):
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


def test_reset_settings():
    """Test that reset_settings clears the cache."""
    with patch.dict(os.environ, {
        'NEON_DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
        'OPENROUTER_API_KEY': 'test-key',
        'CLOUDFLARE_R2_ACCESS_KEY': 'test-access',
        'CLOUDFLARE_R2_SECRET_KEY': 'test-secret',
        'CLOUDFLARE_R2_BUCKET_NAME': 'test-bucket',
        'CLOUDFLARE_R2_ENDPOINT': 'https://test.r2.cloudflarestorage.com',
        'ENVIRONMENT': 'test1'
    }):
        reset_settings()
        settings1 = get_settings()
        assert settings1.environment == 'test1'

    with patch.dict(os.environ, {
        'NEON_DATABASE_URL': 'postgresql+asyncpg://test:test@localhost:5432/test',
        'OPENROUTER_API_KEY': 'test-key',
        'CLOUDFLARE_R2_ACCESS_KEY': 'test-access',
        'CLOUDFLARE_R2_SECRET_KEY': 'test-secret',
        'CLOUDFLARE_R2_BUCKET_NAME': 'test-bucket',
        'CLOUDFLARE_R2_ENDPOINT': 'https://test.r2.cloudflarestorage.com',
        'ENVIRONMENT': 'test2'
    }):
        reset_settings()
        settings2 = get_settings()
        assert settings2.environment == 'test2'

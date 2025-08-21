#!/usr/bin/env python3
"""VNBdigitaler - Database Configuration.

Simple configuration helper for database connection setup.
In production, this would use environment variables and proper secrets management.

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)


def get_database_url() -> str:
    """Get database URL from environment or return example for development.

    Priority order:
    1. NEON_DATABASE_URL (direct PostgreSQL URL)
    2. Individual DATABASE_* variables
    3. Development fallback with error message
    """
    # First try NEON_DATABASE_URL (direct PostgreSQL URL)
    neon_url = os.environ.get("NEON_DATABASE_URL")
    if neon_url:
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        if neon_url.startswith("postgresql://"):
            async_url = neon_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Convert SSL parameters for asyncpg compatibility
            async_url = async_url.replace("sslmode=require", "ssl=require")
            async_url = async_url.replace("channel_binding=require", "")
            # Clean up double & or trailing &
            async_url = async_url.replace("&&", "&").rstrip("&").rstrip("?")
            return async_url
        elif neon_url.startswith("postgresql+asyncpg://"):
            return neon_url
        else:
            print(f"⚠️  Invalid NEON_DATABASE_URL format: {neon_url}")

    # Try to get from individual environment variables
    if all(
        key in os.environ
        for key in [
            "DATABASE_HOST",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_NAME",
        ]
    ):
        host = os.environ["DATABASE_HOST"]
        port = os.environ.get("DATABASE_PORT", "5432")
        user = os.environ["DATABASE_USER"]
        password = os.environ["DATABASE_PASSWORD"]
        database = os.environ["DATABASE_NAME"]

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}?ssl=require"

    # Development fallback - you would set your Neon database URL here
    print("⚠️  No database environment variables found.")
    print("📝 Please set one of the following:")
    print("   Option 1: NEON_DATABASE_URL (complete PostgreSQL URL)")
    print("   Option 2: Individual variables:")
    print("   - DATABASE_HOST (your Neon host)")
    print("   - DATABASE_USER (your Neon user)")
    print("   - DATABASE_PASSWORD (your Neon password)")
    print("   - DATABASE_NAME (your database name)")
    print("   - DATABASE_PORT (optional, defaults to 5432)")
    print()
    print("🔧 Example for Neon:")
    print(
        "   export NEON_DATABASE_URL='postgresql://user:pass@ep-xxx.region.neon.tech/db'"  # pragma: allowlist secret
    )
    print("   or")
    print("   export DATABASE_HOST='ep-xxx-xxx.us-east-1.aws.neon.tech'")
    print("   export DATABASE_USER='your-user'")
    print("   export DATABASE_PASSWORD='your-password'")  # pragma: allowlist secret
    print("   export DATABASE_NAME='vnbdigitaler'")
    print()

    # Return example URL - user needs to replace with actual credentials
    raise ValueError("❌ Invalid database URL. Please configure proper credentials.")


def validate_database_connection(database_url: str) -> bool:
    """Validate that database URL is not the example URL."""
    example_patterns = [
        "user:password@host:port",
        "user:pass@ep-xxx",
        "localhost",
        "example.com",
    ]

    return not any(pattern in database_url for pattern in example_patterns)


if __name__ == "__main__":
    url = get_database_url()
    print(f"Database URL: {url}")

    if validate_database_connection(url):
        print("✅ Database URL looks valid")
    else:
        print("❌ Database URL needs to be configured with real credentials")

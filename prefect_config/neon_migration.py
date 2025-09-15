"""
VNB Digitaler - Neon Database Migration Helper
Hilfsfunktionen für Migration von SQLite zu Neon PostgreSQL.
"""

import os
from pathlib import Path


def get_database_url(environment: str = "development") -> str:
    """
    Bestimme Database URL basierend auf Environment.

    Args:
        environment: "development", "staging", "production"

    Returns:
        Database connection URL
    """

    # Neon PostgreSQL für Production/Staging
    if environment in ("production", "staging"):
        neon_url = os.getenv("NEON_DATABASE_URL")
        if neon_url:
            return neon_url

        # Fallback: Konstruiere aus Einzelteilen
        host = os.getenv("NEON_HOST", "ep-example-123456.us-east-1.aws.neon.tech")
        database = os.getenv("NEON_DATABASE", "vnb_digitaler")
        user = os.getenv("NEON_USER", "vnb_user")
        password = os.getenv("NEON_PASSWORD")

        if password:
            return f"postgresql+asyncpg://{user}:{password}@{host}/{database}?sslmode=require"

    # SQLite für Development
    sqlite_path = os.getenv(
        "VNB_DATABASE_URL", "sqlite+aiosqlite:///app/data/vnb_digitaler.db"
    )
    return sqlite_path


def get_migration_config() -> dict:
    """
    Konfiguration für Database Migrations.

    Returns:
        Migration-Konfiguration
    """
    return {
        "sqlite_path": "/app/data/vnb_digitaler.db",
        "backup_path": "/app/data/backups",
        "migration_table": "alembic_version",
        "batch_size": 1000,  # Für große Tabellen
        "timeout_seconds": 300,
    }


# Docker Compose Overrides für Neon
NEON_COMPOSE_OVERRIDE = """
# docker-compose.neon.yml
# Override für Production mit Neon Database

version: '3.8'

services:
  prefect-server:
    environment:
      - PREFECT_API_DATABASE_CONNECTION_URL=${NEON_DATABASE_URL}
    volumes:
      - prefect_data:/root/.prefect
      # Remove SQLite volume mount

  prefect-worker:
    environment:
      - VNB_DATABASE_URL=${NEON_DATABASE_URL}
      - VNB_ENV=production
      - VNB_DRY_RUN_MODE=false
      - VNB_ENABLE_DEBUG_LOGGING=false
    env_file:
      - .env.production
      - .env.neon  # Neon-specific environment

# Remove local volumes for production
volumes:
  prefect_data:
    driver: local
"""

# Environment Template für Neon
NEON_ENV_TEMPLATE = """
# .env.neon
# Neon PostgreSQL Configuration

# Neon Database Connection
NEON_DATABASE_URL=postgresql+asyncpg://user:password@ep-example-123456.us-east-1.aws.neon.tech/vnb_digitaler?sslmode=require  # pragma: allowlist secret
NEON_HOST=ep-example-123456.us-east-1.aws.neon.tech
NEON_DATABASE=vnb_digitaler
NEON_USER=vnb_user
NEON_PASSWORD=your_secure_password  # pragma: allowlist secret

# Production Settings
VNB_ENV=production
VNB_DATABASE_URL=${NEON_DATABASE_URL}
VNB_DATABASE_SSL_MODE=require
VNB_DATABASE_POOL_SIZE=10
VNB_DATABASE_MAX_OVERFLOW=20

# Prefect Production
PREFECT_API_DATABASE_CONNECTION_URL=${NEON_DATABASE_URL}

# Disable Development Features
VNB_DRY_RUN_MODE=false
VNB_ENABLE_DEBUG_LOGGING=false
VNB_SAVE_INTERMEDIATE_RESULTS=false
"""


def create_neon_migration_files():
    """Erstelle Neon Migration Template-Dateien."""

    # docker-compose.neon.yml
    compose_file = Path("docker-compose.neon.yml")
    compose_file.write_text(NEON_COMPOSE_OVERRIDE)

    # .env.neon template
    env_file = Path(".env.neon.template")
    env_file.write_text(NEON_ENV_TEMPLATE)

    print("✅ Neon migration files created:")
    print("   📁 docker-compose.neon.yml")
    print("   📁 .env.neon.template")
    print("")
    print("🔧 To migrate to Neon:")
    print("   1. Copy .env.neon.template to .env.neon")
    print("   2. Update Neon credentials in .env.neon")
    print(
        "   3. Run: docker-compose -f docker-compose.prefect.yml -f docker-compose.neon.yml up"
    )


if __name__ == "__main__":
    create_neon_migration_files()

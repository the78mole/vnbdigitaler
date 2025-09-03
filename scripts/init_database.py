#!/usr/bin/env python3
"""
Datenbank-Initialisierungs-Skript für PostgreSQL-Setup.

Dieses Skript initialisiert die PostgreSQL-Datenbank mit allen notwendigen
Tabellen, Indices und Extensions für die BDEW-Anwendung.
"""

import asyncio
import logging
import os
import sys
import traceback
from pathlib import Path

from sqlalchemy import text

# Füge das src-Verzeichnis zum Python-Pfad hinzu
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Setze Umgebungsvariablen vor dem Import
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/vnbdigitaler"
)
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_DB", "vnbdigitaler")

from database import DatabaseManager  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def setup_postgresql_extensions(db_manager: DatabaseManager):
    """Installiere notwendige PostgreSQL Extensions."""

    async with db_manager.get_session() as session:
        extensions = [
            "pg_trgm",  # Trigram-Ähnlichkeitssuche
            "unaccent",  # Entfernung von Akzenten/Diakritika
            "uuid-ossp",  # UUID-Generierung
        ]

        for ext in extensions:
            try:
                await session.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
                logger.info(f"✅ Extension installiert: {ext}")
            except Exception as e:
                logger.warning(
                    f"⚠️  Extension {ext} konnte nicht installiert werden: {e}"
                )

        await session.commit()


async def init_database():
    """Initialisiere die Datenbank mit allen Tabellen und Extensions."""

    logger.info("🚀 Starte Datenbank-Initialisierung...")

    try:
        # Erstelle DatabaseManager-Instanz
        db_manager = DatabaseManager()

        # Teste die Verbindung
        logger.info("🔌 Teste Datenbankverbindung...")
        if not await db_manager.test_connection():
            logger.error("❌ Datenbankverbindung fehlgeschlagen!")
            return False

        logger.info("✅ Datenbankverbindung erfolgreich!")

        # Erstelle alle Tabellen
        logger.info("📊 Erstelle Datenbank-Tabellen...")
        await db_manager.create_tables()
        logger.info("✅ Alle Tabellen erfolgreich erstellt!")

        # Installiere PostgreSQL Extensions
        logger.info("🔧 Installiere PostgreSQL Extensions...")
        await setup_postgresql_extensions(db_manager)
        logger.info("✅ Extensions erfolgreich installiert!")

        # Erstelle Performance-Indices
        logger.info("⚡ Erstelle Performance-Indices...")
        await create_performance_indices(db_manager)
        logger.info("✅ Performance-Indices erfolgreich erstellt!")

        # Zeige Datenbankstatus
        await show_database_status(db_manager)

        logger.info("🎉 Datenbank-Initialisierung erfolgreich abgeschlossen!")
        return True

    except Exception as e:
        logger.error(f"❌ Fehler bei der Datenbank-Initialisierung: {e}")
        logger.error(traceback.format_exc())
        return False


async def create_performance_indices(db_manager: DatabaseManager):
    """Erstelle zusätzliche Performance-Indices."""

    async with db_manager.get_session() as session:
        # Zusätzliche Indices für BDEW-Suche
        indices = [
            # Full-Text-Search-Index für deutsche Sprache
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_companies_fulltext_german
            ON bdew_companies
            USING gin(to_tsvector('german',
                COALESCE(company_name, '') || ' ' ||
                COALESCE(city, '') || ' ' ||
                COALESCE(federal_state, '')
            ))
            """,
            # Trigram-Index für Ähnlichkeitssuche (erfordert pg_trgm)
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_companies_trgm_name
            ON bdew_companies
            USING gin(company_name_normalized gin_trgm_ops)
            """,
            # JSONB-Index für Service-Territory-Queries
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_companies_service_territory
            ON bdew_companies
            USING gin(service_territory)
            """,
            # Geo-Index für Koordinaten-basierte Suchen
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_companies_location
            ON bdew_companies (latitude, longitude)
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """,
            # Zusammengesetzter Index für häufige Abfragen
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_companies_active_quality
            ON bdew_companies (is_active, data_quality_score DESC)
            WHERE is_active = true
            """,
            # Index für Import-Log-Queries
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_import_logs_timestamp_status
            ON bdew_import_logs (import_timestamp DESC, import_status)
            """,
            # Index für Data-History-Queries
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_data_history_company_change
            ON bdew_data_history (company_id, change_timestamp DESC)
            """,
        ]

        for index_sql in indices:
            try:
                await session.execute(text(index_sql))
                logger.info(
                    f"✅ Index erstellt: {index_sql.split('IF NOT EXISTS')[1].split('ON')[0].strip()}"
                )
            except Exception as e:
                logger.warning(f"⚠️  Index konnte nicht erstellt werden: {e}")

        await session.commit()


async def show_database_status(db_manager: DatabaseManager):
    """Zeige Datenbankstatus und -informationen."""

    async with db_manager.get_session() as session:
        # PostgreSQL-Version
        result = await session.execute(text("SELECT version()"))
        version = result.scalar()
        logger.info(f"📊 PostgreSQL Version: {version.split(',')[0]}")

        # Installierte Extensions
        result = await session.execute(
            text("SELECT extname FROM pg_extension ORDER BY extname")
        )
        extensions = [row[0] for row in result]
        logger.info(f"🔧 Installierte Extensions: {', '.join(extensions)}")

        # Tabellen-Anzahl
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
            )
        )
        table_count = result.scalar()
        logger.info(f"📊 Anzahl Tabellen: {table_count}")

        # Datenbank-Größe
        result = await session.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        )
        db_size = result.scalar()
        logger.info(f"💾 Datenbank-Größe: {db_size}")


if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
